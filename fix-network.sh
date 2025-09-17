#!/bin/bash

# 腾讯云服务器网络修复脚本
# 解决DNS和镜像源连接问题

echo "🔧 开始修复腾讯云服务器网络问题..."

# 1. 修复DNS配置
echo "📡 配置DNS服务器..."
sudo tee /etc/systemd/resolved.conf > /dev/null <<EOF
[Resolve]
DNS=119.29.29.29 223.5.5.5 8.8.8.8
FallbackDNS=114.114.114.114 1.1.1.1
EOF

# 重启DNS服务
sudo systemctl restart systemd-resolved

# 2. 配置腾讯云内网镜像源
echo "🔄 配置腾讯云内网镜像源..."
sudo cp /etc/apt/sources.list /etc/apt/sources.list.backup

sudo tee /etc/apt/sources.list > /dev/null <<EOF
# 腾讯云内网镜像源 - 更快更稳定
deb http://mirrors.tencentyun.com/ubuntu/ jammy main restricted universe multiverse
deb http://mirrors.tencentyun.com/ubuntu/ jammy-updates main restricted universe multiverse
deb http://mirrors.tencentyun.com/ubuntu/ jammy-backports main restricted universe multiverse
deb http://mirrors.tencentyun.com/ubuntu/ jammy-security main restricted universe multiverse

# 备用公网镜像源
# deb http://mirrors.cloud.tencent.com/ubuntu/ jammy main restricted universe multiverse
# deb http://mirrors.cloud.tencent.com/ubuntu/ jammy-updates main restricted universe multiverse
# deb http://mirrors.cloud.tencent.com/ubuntu/ jammy-backports main restricted universe multiverse
# deb http://mirrors.cloud.tencent.com/ubuntu/ jammy-security main restricted universe multiverse
EOF

# 3. 清理并更新包缓存
echo "🧹 清理包缓存..."
sudo apt clean
sudo apt autoclean

# 4. 测试网络连接
echo "🌐 测试网络连接..."
echo "测试DNS解析..."
nslookup baidu.com

echo "测试ping连接..."
ping -c 3 119.29.29.29

echo "测试镜像源连接..."
curl -I http://mirrors.tencentyun.com/ubuntu/

# 5. 更新包列表
echo "📦 更新包列表..."
sudo apt update

echo "✅ 网络修复完成！"
echo "💡 如果仍有问题，请检查："
echo "   1. 安全组是否开放了必要端口"
echo "   2. 服务器是否有公网IP"
echo "   3. 防火墙设置是否正确"