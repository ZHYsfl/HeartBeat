#!/bin/bash

# 腾讯云Ubuntu服务器Docker安装脚本
# 适用于Ubuntu 22.04 LTS

echo "🐳 开始安装Docker和Docker Compose..."

# 1. 更新系统包
echo "📦 更新系统包..."
sudo apt update

# 2. 安装必要的依赖
echo "🔧 安装依赖包..."
sudo apt install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    software-properties-common

# 3. 添加Docker官方GPG密钥
echo "🔑 添加Docker GPG密钥..."
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# 4. 添加Docker仓库（使用腾讯云镜像）
echo "📋 添加Docker仓库..."
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://mirrors.cloud.tencent.com/docker-ce/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 5. 更新包索引
echo "🔄 更新包索引..."
sudo apt update

# 6. 安装Docker CE
echo "🐳 安装Docker CE..."
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# 7. 启动并启用Docker服务
echo "🚀 启动Docker服务..."
sudo systemctl start docker
sudo systemctl enable docker

# 8. 将当前用户添加到docker组
echo "👤 配置用户权限..."
sudo usermod -aG docker $USER

# 9. 配置Docker镜像加速器（腾讯云）
echo "⚡ 配置Docker镜像加速器..."
sudo mkdir -p /etc/docker
sudo tee /etc/docker/daemon.json > /dev/null <<EOF
{
  "registry-mirrors": [
    "https://mirror.ccs.tencentyun.com",
    "https://docker.mirrors.ustc.edu.cn",
    "https://hub-mirror.c.163.com"
  ],
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
EOF

# 10. 重启Docker服务
echo "🔄 重启Docker服务..."
sudo systemctl restart docker

# 11. 安装Docker Compose（独立版本）
echo "🔧 安装Docker Compose..."
DOCKER_COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep 'tag_name' | cut -d\" -f4)
sudo curl -L "https://github.com/docker/compose/releases/download/${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 12. 创建符号链接
sudo ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose

# 13. 验证安装
echo "✅ 验证安装..."
echo "Docker版本："
docker --version

echo "Docker Compose版本："
docker-compose --version

echo "Docker服务状态："
sudo systemctl status docker --no-pager

# 14. 测试Docker
echo "🧪 测试Docker..."
sudo docker run hello-world

echo ""
echo "🎉 Docker安装完成！"
echo ""
echo "📝 重要提示："
echo "   1. 请重新登录或运行 'newgrp docker' 以使用户组生效"
echo "   2. 现在可以不使用sudo运行docker命令"
echo "   3. Docker镜像加速器已配置为腾讯云镜像"
echo ""
echo "🔧 常用命令："
echo "   docker ps                 # 查看运行中的容器"
echo "   docker images             # 查看镜像列表"
echo "   docker-compose up -d      # 启动服务"
echo "   docker-compose logs       # 查看日志"