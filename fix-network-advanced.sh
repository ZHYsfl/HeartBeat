#!/bin/bash

# 腾讯云服务器高级网络修复脚本
# 解决内网IP路由和DNS问题

echo "🔧 开始高级网络修复..."

# 1. 检查当前网络状态
echo "📊 检查当前网络状态..."
echo "当前IP配置："
ip addr show
echo ""
echo "当前路由表："
ip route show
echo ""
echo "当前DNS配置："
cat /etc/resolv.conf
echo ""

# 2. 修复DNS配置（使用公网DNS）
echo "📡 配置公网DNS服务器..."
sudo tee /etc/systemd/resolved.conf > /dev/null <<EOF
[Resolve]
DNS=8.8.8.8 1.1.1.1 114.114.114.114
FallbackDNS=223.5.5.5 119.29.29.29
Domains=~.
DNSSEC=no
DNSOverTLS=no
Cache=yes
DNSStubListener=yes
EOF

# 重启DNS服务
sudo systemctl restart systemd-resolved
sudo systemctl restart systemd-networkd

# 3. 强制刷新DNS缓存
echo "🔄 刷新DNS缓存..."
sudo resolvectl flush-caches
sudo systemctl restart systemd-resolved

# 4. 配置公网镜像源（避免内网路由问题）
echo "🌐 配置公网镜像源..."
sudo cp /etc/apt/sources.list /etc/apt/sources.list.backup.$(date +%Y%m%d)

sudo tee /etc/apt/sources.list > /dev/null <<EOF
# 阿里云公网镜像源
deb http://mirrors.aliyun.com/ubuntu/ jammy main restricted universe multiverse
deb http://mirrors.aliyun.com/ubuntu/ jammy-updates main restricted universe multiverse
deb http://mirrors.aliyun.com/ubuntu/ jammy-backports main restricted universe multiverse
deb http://mirrors.aliyun.com/ubuntu/ jammy-security main restricted universe multiverse

# 备用：清华大学镜像源
# deb https://mirrors.tuna.tsinghua.edu.cn/ubuntu/ jammy main restricted universe multiverse
# deb https://mirrors.tuna.tsinghua.edu.cn/ubuntu/ jammy-updates main restricted universe multiverse
# deb https://mirrors.tuna.tsinghua.edu.cn/ubuntu/ jammy-backports main restricted universe multiverse
# deb https://mirrors.tuna.tsinghua.edu.cn/ubuntu/ jammy-security main restricted universe multiverse

# 官方源（最后备用）
# deb http://archive.ubuntu.com/ubuntu/ jammy main restricted universe multiverse
# deb http://archive.ubuntu.com/ubuntu/ jammy-updates main restricted universe multiverse
# deb http://archive.ubuntu.com/ubuntu/ jammy-backports main restricted universe multiverse
# deb http://security.ubuntu.com/ubuntu/ jammy-security main restricted universe multiverse
EOF

# 5. 检查并修复网络接口配置
echo "🔧 检查网络接口配置..."
INTERFACE=$(ip route | grep default | awk '{print $5}' | head -1)
echo "主网络接口: $INTERFACE"

# 6. 添加公网DNS到resolv.conf（临时修复）
echo "🚀 临时DNS修复..."
sudo tee /etc/resolv.conf > /dev/null <<EOF
nameserver 8.8.8.8
nameserver 1.1.1.1
nameserver 114.114.114.114
nameserver 223.5.5.5
EOF

# 7. 测试网络连接
echo "🧪 测试网络连接..."
echo "测试DNS解析："
nslookup google.com
echo ""

echo "测试ping连接："
ping -c 3 8.8.8.8
echo ""

echo "测试HTTP连接："
curl -I --connect-timeout 10 http://mirrors.aliyun.com/ubuntu/
echo ""

# 8. 清理并更新包缓存
echo "🧹 清理包缓存..."
sudo apt clean
sudo apt autoclean
sudo rm -rf /var/lib/apt/lists/*

# 9. 尝试更新包列表
echo "📦 更新包列表..."
sudo apt update

# 10. 检查防火墙状态
echo "🛡️ 检查防火墙状态..."
sudo ufw status

# 11. 显示网络诊断信息
echo ""
echo "🔍 网络诊断信息："
echo "================================"
echo "DNS服务器："
systemd-resolve --status | grep "DNS Servers" | head -5
echo ""
echo "路由表："
ip route show
echo ""
echo "网络接口状态："
ip link show
echo ""

echo "✅ 高级网络修复完成！"
echo ""
echo "💡 如果问题仍然存在，可能的原因："
echo "   1. 腾讯云安全组未开放出站HTTP/HTTPS端口"
echo "   2. VPC路由表配置问题"
echo "   3. 服务器没有公网IP或NAT网关"
echo "   4. 腾讯云内网DNS解析问题"
echo ""
echo "🔧 建议检查："
echo "   1. 腾讯云控制台 -> 安全组 -> 出站规则"
echo "   2. 腾讯云控制台 -> VPC -> 路由表"
echo "   3. 腾讯云控制台 -> 云服务器 -> 公网IP"