# 心跳打卡应用 - 服务器部署指南

## 📋 目录
- [系统要求](#系统要求)
- [快速部署](#快速部署)
- [详细部署步骤](#详细部署步骤)
- [环境配置](#环境配置)
- [SSL证书配置](#ssl证书配置)
- [域名配置](#域名配置)
- [监控和维护](#监控和维护)
- [故障排除](#故障排除)

## 🖥️ 系统要求

### 最低配置
- **CPU**: 1核心
- **内存**: 1GB RAM
- **存储**: 10GB 可用空间
- **操作系统**: Ubuntu 18.04+ / CentOS 7+ / Debian 9+

### 推荐配置
- **CPU**: 2核心
- **内存**: 2GB RAM
- **存储**: 20GB 可用空间
- **网络**: 稳定的互联网连接

### 软件依赖
- Docker 20.10+
- Docker Compose 1.29+
- Git (用于代码部署)

## 🚀 快速部署

### 1. 安装Docker和Docker Compose

**Ubuntu/Debian:**
```bash
# 更新包索引
sudo apt update

# 安装Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 安装Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 将用户添加到docker组
sudo usermod -aG docker $USER
```

**CentOS/RHEL:**
```bash
# 安装Docker
sudo yum install -y yum-utils
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
sudo yum install -y docker-ce docker-ce-cli containerd.io
sudo systemctl start docker
sudo systemctl enable docker

# 安装Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### 2. 克隆项目
```bash
git clone <your-repository-url>
cd heartbeat
```

### 3. 配置环境变量
```bash
# 复制环境变量模板
cp .env.example .env.production

# 编辑生产环境配置
nano .env.production
```

### 4. 运行部署脚本
```bash
# 给脚本执行权限
chmod +x deploy.sh

# 部署生产环境
./deploy.sh prod
```

## 📝 详细部署步骤

### 1. 服务器准备

#### 1.1 创建部署用户
```bash
# 创建专用用户
sudo adduser heartbeat
sudo usermod -aG docker heartbeat
sudo su - heartbeat
```

#### 1.2 配置防火墙
```bash
# Ubuntu/Debian (ufw)
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable

# CentOS/RHEL (firewalld)
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

### 2. 项目部署

#### 2.1 下载项目代码
```bash
cd /home/heartbeat
git clone <your-repository-url> heartbeat-app
cd heartbeat-app
```

#### 2.2 配置环境变量
```bash
# 复制并编辑生产环境配置
cp .env.example .env.production

# 重要配置项：
# - SECRET_KEY: 生成强密钥
# - DOMAIN: 你的域名
# - CORS_ORIGINS: 允许的前端域名
```

#### 2.3 生成密钥
```bash
# 使用Python脚本生成密钥
python3 secret_key_gen.py

# 或手动生成
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 3. SSL证书配置

#### 3.1 使用Let's Encrypt (推荐)
```bash
# 安装Certbot
sudo apt install certbot  # Ubuntu/Debian
sudo yum install certbot   # CentOS/RHEL

# 获取证书
sudo certbot certonly --standalone -d your-domain.com

# 复制证书到项目目录
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem nginx/ssl/cert.pem
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem nginx/ssl/key.pem
sudo chown heartbeat:heartbeat nginx/ssl/*
```

#### 3.2 使用自签名证书 (仅测试)
```bash
# 创建SSL目录
mkdir -p nginx/ssl

# 生成自签名证书
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout nginx/ssl/key.pem \
    -out nginx/ssl/cert.pem \
    -subj "/C=CN/ST=State/L=City/O=Organization/CN=your-domain.com"
```

### 4. 域名配置

#### 4.1 DNS设置
在你的域名提供商处设置A记录：
```
your-domain.com     A    your-server-ip
www.your-domain.com A    your-server-ip
```

#### 4.2 修改Nginx配置
编辑 `nginx/nginx.conf`，将 `your-domain.com` 替换为你的实际域名。

### 5. 启动服务

#### 5.1 使用部署脚本
```bash
./deploy.sh prod
```

#### 5.2 手动启动
```bash
# 构建镜像
docker-compose build

# 启动服务
docker-compose --profile production up -d

# 查看状态
docker-compose ps
```

## ⚙️ 环境配置

### 开发环境
```bash
# 启动开发环境
./deploy.sh dev

# 或手动启动
docker-compose up -d backend frontend
```

### 生产环境
```bash
# 启动生产环境（包含Nginx反向代理）
./deploy.sh prod

# 或手动启动
docker-compose --profile production up -d
```

## 🔧 监控和维护

### 查看日志
```bash
# 查看所有服务日志
docker-compose logs

# 查看特定服务日志
docker-compose logs backend
docker-compose logs frontend
docker-compose logs nginx

# 实时查看日志
docker-compose logs -f
```

### 更新应用
```bash
# 拉取最新代码
git pull origin main

# 重新构建和部署
docker-compose down
docker-compose build --no-cache
docker-compose --profile production up -d
```

### 备份数据
```bash
# 备份数据库
docker-compose exec backend cp /app/a_love_story.db /app/static/backup_$(date +%Y%m%d_%H%M%S).db

# 备份上传的文件
tar -czf uploads_backup_$(date +%Y%m%d_%H%M%S).tar.gz static/uploads/
```

### 证书续期
```bash
# Let's Encrypt证书自动续期
sudo crontab -e

# 添加以下行（每月1号凌晨2点检查续期）
0 2 1 * * /usr/bin/certbot renew --quiet && docker-compose restart nginx
```

## 🔍 故障排除

### 常见问题

#### 1. 服务无法启动
```bash
# 检查Docker状态
sudo systemctl status docker

# 检查端口占用
sudo netstat -tlnp | grep :80
sudo netstat -tlnp | grep :443

# 查看详细错误日志
docker-compose logs
```

#### 2. 无法访问网站
```bash
# 检查防火墙
sudo ufw status
sudo firewall-cmd --list-all

# 检查DNS解析
nslookup your-domain.com
dig your-domain.com

# 检查SSL证书
openssl s_client -connect your-domain.com:443
```

#### 3. 数据库问题
```bash
# 进入后端容器
docker-compose exec backend bash

# 检查数据库文件
ls -la /app/a_love_story.db

# 重新初始化数据库（注意：会清空数据）
rm /app/a_love_story.db
# 重启服务让应用重新创建数据库
```

#### 4. 文件上传问题
```bash
# 检查上传目录权限
ls -la static/uploads/

# 修复权限
sudo chown -R 1000:1000 static/uploads/
sudo chmod -R 755 static/uploads/
```

### 性能优化

#### 1. 数据库优化
- 定期清理过期数据
- 考虑使用PostgreSQL替代SQLite（大量用户时）

#### 2. 静态文件优化
- 启用Nginx gzip压缩
- 配置适当的缓存策略
- 考虑使用CDN

#### 3. 容器资源限制
```yaml
# 在docker-compose.yml中添加资源限制
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
```

## 📞 技术支持

如果遇到部署问题，请：

1. 检查系统日志：`docker-compose logs`
2. 确认配置文件正确
3. 验证网络和防火墙设置
4. 检查SSL证书有效性

## 🔄 版本更新

### 更新流程
1. 备份当前数据
2. 拉取最新代码
3. 更新配置文件（如有必要）
4. 重新构建镜像
5. 重启服务
6. 验证功能正常

### 回滚操作
```bash
# 如果更新出现问题，可以快速回滚
git checkout <previous-commit>
docker-compose down
docker-compose build
docker-compose --profile production up -d
```