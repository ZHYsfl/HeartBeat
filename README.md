# Heartbeat - 我们的爱情故事

这是 “Heartbeat” 应用的后端，一个专为情侣设计的私密空间，用于记录他们的生活和爱情。

---

## 部署指南

本指南将提供一个详尽的步骤，指导你如何在 Linux 服务器上部署这个全栈应用。我们将使用 Gunicorn 来管理 FastAPI 后端，并使用 Nginx 作为反向代理和前端静态文件服务器。

### 环境准备

*   一台 Linux 服务器（例如，Ubuntu 20.04 或更高版本）。
*   你的域名已指向服务器的 IP 地址（可选，你也可以直接使用 IP 地址）。
*   服务器上已安装 `python3` 和 `pip`。
*   服务器上已安装 `node` 和 `npm`。
*   服务器上已安装 Nginx (`sudo apt update && sudo apt install nginx`)。

### 第一步：准备项目文件

首先，你需要将整个项目（`heartbeat` 文件夹）上传到你的服务器。你可以使用 `scp` 或 `rsync` 等工具。

```bash
# 使用 scp 的示例 (在你的本地电脑上运行)
scp -r /path/to/your/local/heartbeat your_user@your_server_ip:/path/to/server/directory
```

### 第二步：后端设置 (Gunicorn)

1.  **进入后端目录：**
    ```bash
    cd /path/to/your/project/backend
    ```

2.  **创建虚拟环境并安装依赖：**
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    ```

3.  **使用 Gunicorn 运行后端：**
    Gunicorn 是一个生产级的 WSGI HTTP 服务器，适用于 UNIX。我们将用它来运行我们的 FastAPI 应用。

    ```bash
    gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app -b 127.0.0.1:8000
    ```
    *   `-w 4`: 指定 4 个工作进程。一个比较好的初始值是 `(2 * CPU核心数) + 1`。
    *   `-k uvicorn.workers.UvicornWorker`: 使用 Uvicorn 的工作进程类来处理请求，这对于像 FastAPI 这样的 ASGI 应用是必需的。
    *   `main:app`: 告诉 Gunicorn 在 `main.py` 文件中寻找名为 `app` 的对象。
    *   `-b 127.0.0.1:8000`: 将服务绑定到本地的 8000 端口。Nginx 将会把请求转发到这个地址。

    为了在生产环境中稳定运行，你可以使用像 `systemd` 这样的进程管理器在后台运行此命令。但现在，你可以直接运行它，或者使用 `nohup`。

### 第三步：前端设置 (打包静态文件)

1.  **进入前端目录：**
    ```bash
    cd /path/to/your/project/heartbeat-frontend
    ```

2.  **安装依赖：**
    ```bash
    npm install
    ```

3.  **打包生产版本的项目：**
    这个命令会将你的 Vue 应用编译和压缩到一个 `dist` 目录中，里面包含了优化过的静态 HTML, CSS, 和 JavaScript 文件。
    ```bash
    npm run build
    ```
    运行后，你会在 `heartbeat-frontend` 文件夹内看到一个新生成的 `dist` 目录。这就是 Nginx 需要提供给用户的文件。

### 第四步：Nginx 配置

Nginx 将作为我们的“前门”。它负责提供前端的静态文件，并将所有 API 请求传递给后端的 Gunicorn 服务。

1.  **创建一个新的 Nginx 配置文件：**
    ```bash
    sudo nano /etc/nginx/sites-available/heartbeat
    ```

2.  **添加以下配置。** 请将 `your_domain.com` 替换为你的真实域名或服务器 IP 地址，并更新项目文件的路径。

    ```nginx
    server {
        listen 80;
        server_name your_domain.com www.your_domain.com; # 或者你的服务器 IP

        # 前端打包文件的根目录
        root /path/to/your/project/heartbeat-frontend/dist;
        index index.html;

        # 直接处理静态文件的请求
        location / {
            try_files $uri $uri/ /index.html;
        }

        # 处理上传的图片文件
        location /static/uploads {
            alias /path/to/your/project/static/uploads;
        }

        # 针对 API 请求的反向代理
        location /api {
            proxy_pass http://127.0.0.1:8000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
    ```

3.  **启用配置并重启 Nginx：**
    *   从 `sites-available` 创建一个符号链接到 `sites-enabled`：
        ```bash
        sudo ln -s /etc/nginx/sites-available/heartbeat /etc/nginx/sites-enabled/
        ```
    *   测试 Nginx 配置是否存在语法错误：
        ```bash
        sudo nginx -t
        ```
    *   如果测试成功，重启 Nginx 以应用更改：
        ```bash
        sudo systemctl restart nginx
        ```

### 你已成功上线！

就是这样！现在，Gunicorn 正在运行你的后端，Nginx 正在提供前端服务并代理 API 调用，你的应用应该可以通过 `http://your_domain.com` (或你的服务器 IP 地址) 访问了。

这次部署标志着我们项目的圆满完成。恭喜！