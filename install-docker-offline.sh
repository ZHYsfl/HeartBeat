#!/bin/bash

# 腾讯云服务器离线Docker安装脚本
# 适用于网络受限环境

echo "🐳 开始离线安装Docker..."

# 1. 检查系统信息
echo "📊 检查系统信息..."
echo "系统版本: $(lsb_release -d)"
echo "架构: $(uname -m)"
echo "内核版本: $(uname -r)"
echo ""

# 2. 创建临时目录
TEMP_DIR="/tmp/docker-install"
mkdir -p $TEMP_DIR
cd $TEMP_DIR

# 3. 下载Docker静态二进制文件
echo "📥 下载Docker静态二进制文件..."
DOCKER_VERSION="24.0.7"
DOCKER_COMPOSE_VERSION="v2.21.0"

# 尝试多个下载源
download_docker() {
    local urls=(
        "https://download.docker.com/linux/static/stable/x86_64/docker-${DOCKER_VERSION}.tgz"
        "https://mirrors.aliyun.com/docker-ce/linux/static/stable/x86_64/docker-${DOCKER_VERSION}.tgz"
        "https://mirrors.tuna.tsinghua.edu.cn/docker-ce/linux/static/stable/x86_64/docker-${DOCKER_VERSION}.tgz"
    )
    
    for url in "${urls[@]}"; do
        echo "尝试从 $url 下载..."
        if wget --timeout=30 --tries=3 "$url" -O docker.tgz; then
            echo "✅ Docker下载成功"
            return 0
        fi
    done
    
    echo "❌ Docker下载失败，尝试使用snap安装"
    return 1
}

# 4. 尝试下载Docker
if download_docker; then
    # 解压并安装Docker
    echo "📦 解压Docker..."
    tar xzf docker.tgz
    
    echo "🔧 安装Docker二进制文件..."
    sudo cp docker/* /usr/bin/
    sudo chmod +x /usr/bin/docker*
    
    # 创建Docker服务文件
    echo "⚙️ 创建Docker服务..."
    sudo tee /etc/systemd/system/docker.service > /dev/null <<EOF
[Unit]
Description=Docker Application Container Engine
Documentation=https://docs.docker.com
After=network-online.target firewalld.service containerd.service
Wants=network-online.target
Requires=docker.socket containerd.service

[Service]
Type=notify
ExecStart=/usr/bin/dockerd -H fd:// --containerd=/run/containerd/containerd.sock
ExecReload=/bin/kill -s HUP \$MAINPID
TimeoutSec=0
RestartSec=2
Restart=always
StartLimitBurst=3
StartLimitInterval=60s
LimitNOFILE=infinity
LimitNPROC=infinity
LimitCORE=infinity
TasksMax=infinity
Delegate=yes
KillMode=process
OOMScoreAdjust=-500

[Install]
WantedBy=multi-user.target
EOF

    # 创建Docker socket文件
    sudo tee /etc/systemd/system/docker.socket > /dev/null <<EOF
[Unit]
Description=Docker Socket for the API

[Socket]
ListenStream=/var/run/docker.sock
SocketMode=0660
SocketUser=root
SocketGroup=docker

[Install]
WantedBy=sockets.target
EOF

else
    # 使用snap安装Docker（备用方案）
    echo "🔄 使用snap安装Docker..."
    if command -v snap >/dev/null 2>&1; then
        sudo snap install docker
        sudo snap start docker
    else
        echo "❌ snap不可用，尝试从本地包安装..."
        
        # 尝试安装已有的包
        if dpkg -l | grep -q docker; then
            echo "发现已安装的Docker包，尝试修复..."
            sudo dpkg --configure -a
            sudo apt --fix-broken install -y
        else
            echo "❌ 无法安装Docker，请检查网络连接或手动下载安装包"
            exit 1
        fi
    fi
fi

# 5. 创建docker组并添加用户
echo "👤 配置用户权限..."
sudo groupadd -f docker
sudo usermod -aG docker $USER

# 6. 配置Docker daemon
echo "⚡ 配置Docker daemon..."
sudo mkdir -p /etc/docker
sudo tee /etc/docker/daemon.json > /dev/null <<EOF
{
  "registry-mirrors": [
    "https://mirror.ccs.tencentyun.com",
    "https://docker.mirrors.ustc.edu.cn",
    "https://hub-mirror.c.163.com",
    "https://registry.docker-cn.com"
  ],
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "storage-driver": "overlay2",
  "data-root": "/var/lib/docker"
}
EOF

# 7. 启动Docker服务
echo "🚀 启动Docker服务..."
sudo systemctl daemon-reload
sudo systemctl enable docker
sudo systemctl start docker

# 8. 安装Docker Compose
echo "🔧 安装Docker Compose..."
download_compose() {
    local urls=(
        "https://github.com/docker/compose/releases/download/${DOCKER_COMPOSE_VERSION}/docker-compose-linux-x86_64"
        "https://mirrors.aliyun.com/docker-compose/releases/download/${DOCKER_COMPOSE_VERSION}/docker-compose-linux-x86_64"
    )
    
    for url in "${urls[@]}"; do
        echo "尝试从 $url 下载Docker Compose..."
        if wget --timeout=30 --tries=3 "$url" -O docker-compose; then
            sudo mv docker-compose /usr/local/bin/docker-compose
            sudo chmod +x /usr/local/bin/docker-compose
            sudo ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose
            echo "✅ Docker Compose安装成功"
            return 0
        fi
    done
    
    echo "⚠️ Docker Compose下载失败，使用pip安装..."
    if command -v pip3 >/dev/null 2>&1; then
        pip3 install docker-compose
    else
        echo "❌ 无法安装Docker Compose"
        return 1
    fi
}

download_compose

# 9. 验证安装
echo "✅ 验证安装..."
sleep 3

echo "Docker版本："
if docker --version; then
    echo "✅ Docker安装成功"
else
    echo "❌ Docker安装失败"
fi

echo "Docker Compose版本："
if docker-compose --version; then
    echo "✅ Docker Compose安装成功"
else
    echo "❌ Docker Compose安装失败"
fi

echo "Docker服务状态："
sudo systemctl status docker --no-pager -l

# 10. 测试Docker
echo "🧪 测试Docker..."
if sudo docker run --rm hello-world; then
    echo "✅ Docker测试成功"
else
    echo "⚠️ Docker测试失败，但服务可能正常"
fi

# 11. 清理临时文件
echo "🧹 清理临时文件..."
cd /
rm -rf $TEMP_DIR

echo ""
echo "🎉 Docker离线安装完成！"
echo ""
echo "📝 重要提示："
echo "   1. 请重新登录或运行 'newgrp docker' 以使用户组生效"
echo "   2. 如果遇到权限问题，请运行: sudo chmod 666 /var/run/docker.sock"
echo "   3. Docker镜像加速器已配置"
echo ""
echo "🔧 常用命令："
echo "   docker ps                 # 查看运行中的容器"
echo "   docker images             # 查看镜像列表"
echo "   docker-compose up -d      # 启动服务"
echo "   sudo systemctl status docker  # 查看Docker服务状态"