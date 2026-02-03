# 多网盘 STRM 网关 v3.0

基于 FastAPI + Tortoise ORM + p115client 构建的多网盘 STRM 文件生成和流媒体网关系统。

## 特性

- 🚀 **FastAPI 驱动**: 高性能异步 API
- 📦 **Tortoise ORM**: 现代化异步 ORM
- 📁 **STRM 生成**: 自动生成 STRM 文件供媒体服务器使用
- 🎬 **302 流媒体**: 支持 302 重定向的流媒体服务
- ⏰ **任务调度**: 基于 APScheduler 的定时任务
- 🔌 **多网盘支持**: 架构支持多种网盘（目前支持 115）

## 环境要求

- Python 3.13+
- Node.js 18+ (前端开发)


## 架构

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Next.js   │────▶│   FastAPI   │────▶│  p115client │
│   Frontend  │◀────│    API      │◀────│   115 API   │
└─────────────┘     └─────────────┘     └─────────────┘
                            │
                            ▼
                     ┌─────────────┐
                     │  Tortoise   │
                     │    ORM      │
                     └─────────────┘
```

## 许可证

MIT License

## 相关项目

- [p115client](https://github.com/ChenyangGao/p115client) - 115 网盘 Python 客户端
