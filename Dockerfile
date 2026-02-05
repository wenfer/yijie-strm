# Multi-Cloud STRM Gateway v3.0 Docker Image
# 多阶段构建: 前端 + 后端

# ============ Stage 1: 构建前端 ============
FROM node:22-alpine AS frontend-builder

WORKDIR /build

# 复制前端依赖文件
COPY web/package.json web/pnpm-lock.yaml ./

# 安装 pnpm 和依赖
RUN npm install -g pnpm && \
    pnpm install --frozen-lockfile

# 复制前端源代码
COPY web/ ./

# 构建前端 (静态导出)
# 需要配置 Next.js 支持静态导出
RUN pnpm build

# ============ Stage 2: 后端运行时 ============
FROM python:3.13-slim

LABEL org.opencontainers.image.source=https://github.com/wenfer/yijie-strm
LABEL org.opencontainers.image.description="Multi-Cloud STRM Gateway - Support for multiple cloud storage providers"
LABEL org.opencontainers.image.licenses=MIT

# 设置工作目录
WORKDIR /app

# 安装系统依赖 (包括 FUSE 支持)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    fuse3 \
    libfuse-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY app/ ./app/
COPY run.py .

# 从前端构建阶段复制静态文件
COPY --from=frontend-builder /build/out ./static

# 创建数据目录
RUN mkdir -p /data

# 暴露端口
EXPOSE 8115

# 设置环境变量
ENV GATEWAY_HOST=0.0.0.0 \
    GATEWAY_PORT=8115 \
    DB_URL=sqlite:///data/strm_gateway.db \
    PYTHONUNBUFFERED=1

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8115/api/system/health')"

# 启动命令
CMD ["python", "run.py"]
