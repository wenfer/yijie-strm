# Docker 部署文档

## 架构说明

本项目采用**前后端一体化部署**方案:

1. **前端**: Next.js 静态导出 (Static Export)
2. **后端**: FastAPI 托管前端静态文件 + API 服务
3. **镜像**: 单一 Docker 镜像，包含前后端

## 工作原理

### 构建阶段
1. **Stage 1 (前端)**: 使用 Node.js 构建 Next.js 静态文件
   - 输出目录: `web/out/`
   - 包含所有 HTML, CSS, JS 和资源文件

2. **Stage 2 (后端)**: 将前端静态文件复制到 `/app/static/`
   - FastAPI 自动检测并托管静态文件
   - 前端路由由 `index.html` 处理 (SPA)

### 运行时路由
```
访问路径               处理方式
/                     -> /app/static/index.html (前端)
/api/*                -> FastAPI 路由 (后端 API)
/stream/*             -> FastAPI 路由 (流媒体)
/docs                 -> FastAPI 文档 (Swagger)
/_next/*              -> 静态资源 (CSS/JS)
```

## 快速开始

### 1. 本地构建测试

```bash
# 构建镜像
docker build -t strm-gateway:local .

# 运行容器
docker run -d \
  -p 8115:8115 \
  -v $(pwd)/data:/data \
  strm-gateway:local

# 访问
# 前端: http://localhost:8115
# API:  http://localhost:8115/docs
```

### 2. 使用 GitHub Actions 自动构建

推送代码到 main 分支会自动触发构建:

```bash
git add .
git commit -m "Update code"
git push origin main
```

构建完成后，镜像会自动推送到: `ghcr.io/wenfer/yijie-strm`

### 3. 拉取并运行

```bash
# 拉取最新镜像
docker pull ghcr.io/wenfer/yijie-strm:latest

# 运行
docker run -d \
  --name strm-gateway \
  -p 8115:8115 \
  -v $(pwd)/data:/data \
  -v $(pwd)/cookies:/root/.strm_gateway \
  -e STRM_BASE_URL=http://your-server-ip:8115/stream \
  ghcr.io/wenfer/yijie-strm:latest
```

### 4. 使用 Docker Compose

```bash
# 编辑 docker-compose.yml 修改配置
vim docker-compose.yml

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

## 版本号说明

版本号格式: `YY.WW.N`

- `YY`: 年份后两位 (如 26 表示 2026 年)
- `WW`: 第几周 (如 05 表示第 5 周)
- `N`: 本周第几次构建 (1, 2, 3...)

示例:
- `26.05.1`: 2026年第5周第1次构建
- `26.05.2`: 2026年第5周第2次构建
- `26.06.1`: 2026年第6周第1次构建

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `GATEWAY_HOST` | `0.0.0.0` | 监听地址 |
| `GATEWAY_PORT` | `8115` | 监听端口 |
| `DB_URL` | `sqlite:///data/strm_gateway.db` | 数据库 URL |
| `STRM_BASE_URL` | - | STRM 文件基础 URL (必须配置) |
| `LOG_LEVEL` | `INFO` | 日志级别 |

## 数据持久化

需要挂载以下目录:

```bash
-v $(pwd)/data:/data                      # 数据库文件
-v $(pwd)/cookies:/root/.strm_gateway     # Cookie 文件
```

## 网络配置

### 反向代理示例 (Nginx)

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8115;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 配置 STRM_BASE_URL

```bash
# 本地访问
-e STRM_BASE_URL=http://localhost:8115/stream

# 局域网访问
-e STRM_BASE_URL=http://192.168.1.100:8115/stream

# 公网域名
-e STRM_BASE_URL=https://your-domain.com/stream
```

## 故障排查

### 前端无法加载

```bash
# 检查静态文件是否存在
docker exec -it strm-gateway ls -la /app/static

# 如果没有 static 目录，说明构建失败
# 查看构建日志
docker logs strm-gateway
```

### API 无法访问

```bash
# 检查健康状态
curl http://localhost:8115/api/system/health

# 查看日志
docker logs -f strm-gateway
```

### 数据库问题

```bash
# 检查数据库文件
ls -la data/strm_gateway.db

# 删除数据库重新初始化
rm data/strm_gateway.db
docker-compose restart
```

## 开发环境

开发时不需要 Docker，可以分别运行前后端:

```bash
# 后端
python run.py --debug

# 前端 (另一个终端)
cd web
pnpm dev
```

前端会自动代理 API 请求到后端 (见 `web/next.config.js`)。

## 更新镜像

```bash
# 停止容器
docker-compose down

# 拉取最新镜像
docker-compose pull

# 启动
docker-compose up -d
```

## 监控

```bash
# 查看容器状态
docker ps

# 查看资源使用
docker stats strm-gateway

# 查看实时日志
docker logs -f --tail 100 strm-gateway
```
