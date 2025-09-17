#!/bin/bash

# 心跳打卡应用部署脚本
# 使用方法: ./deploy.sh [dev|prod]

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_message() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查Docker是否安装
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker 未安装，请先安装 Docker"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose 未安装，请先安装 Docker Compose"
        exit 1
    fi
}

# 检查环境变量文件
check_env_file() {
    if [ "$1" = "prod" ]; then
        if [ ! -f ".env.production" ]; then
            print_error "生产环境配置文件 .env.production 不存在"
            print_warning "请复制 .env.example 为 .env.production 并配置相应的值"
            exit 1
        fi
        cp .env.production .env
    else
        if [ ! -f ".env" ]; then
            print_warning ".env 文件不存在，使用默认配置"
            cp .env.example .env
        fi
    fi
}

# 生成密钥
generate_secret_key() {
    if [ -f "secret_key_gen.py" ]; then
        print_message "生成新的密钥..."
        python secret_key_gen.py
    else
        print_warning "secret_key_gen.py 不存在，请手动设置 SECRET_KEY"
    fi
}

# 创建必要的目录
create_directories() {
    print_message "创建必要的目录..."
    mkdir -p static/uploads
    mkdir -p nginx/ssl
}

# 构建和启动服务
deploy_services() {
    local env=$1
    
    print_message "停止现有服务..."
    docker-compose down
    
    print_message "构建镜像..."
    docker-compose build --no-cache
    
    if [ "$env" = "prod" ]; then
        print_message "启动生产环境服务..."
        docker-compose --profile production up -d
    else
        print_message "启动开发环境服务..."
        docker-compose up -d backend frontend
    fi
}

# 检查服务状态
check_services() {
    print_message "检查服务状态..."
    sleep 5
    
    if docker-compose ps | grep -q "Up"; then
        print_message "服务启动成功！"
        docker-compose ps
        
        print_message "服务访问地址："
        echo "前端: http://localhost"
        echo "后端API: http://localhost:8000"
        
        if [ "$1" = "prod" ]; then
            echo "生产环境: https://your-domain.com"
        fi
    else
        print_error "服务启动失败，请检查日志："
        docker-compose logs
        exit 1
    fi
}

# SSL证书提醒
ssl_reminder() {
    if [ "$1" = "prod" ]; then
        print_warning "生产环境部署提醒："
        echo "1. 请将SSL证书放置在 nginx/ssl/ 目录下"
        echo "2. 证书文件名应为: cert.pem 和 key.pem"
        echo "3. 修改 nginx/nginx.conf 中的域名配置"
        echo "4. 修改 .env.production 中的域名配置"
    fi
}

# 主函数
main() {
    local env=${1:-dev}
    
    print_message "开始部署心跳打卡应用 (环境: $env)"
    
    # 检查依赖
    check_docker
    
    # 检查环境配置
    check_env_file $env
    
    # 生成密钥
    if [ "$env" = "prod" ]; then
        generate_secret_key
    fi
    
    # 创建目录
    create_directories
    
    # 部署服务
    deploy_services $env
    
    # 检查服务
    check_services $env
    
    # SSL提醒
    ssl_reminder $env
    
    print_message "部署完成！"
}

# 显示帮助信息
show_help() {
    echo "心跳打卡应用部署脚本"
    echo ""
    echo "使用方法:"
    echo "  ./deploy.sh [dev|prod]"
    echo ""
    echo "参数:"
    echo "  dev   - 开发环境部署 (默认)"
    echo "  prod  - 生产环境部署"
    echo ""
    echo "示例:"
    echo "  ./deploy.sh dev   # 部署开发环境"
    echo "  ./deploy.sh prod  # 部署生产环境"
}

# 处理命令行参数
case "$1" in
    -h|--help)
        show_help
        exit 0
        ;;
    dev|prod|"")
        main $1
        ;;
    *)
        print_error "无效的参数: $1"
        show_help
        exit 1
        ;;
esac