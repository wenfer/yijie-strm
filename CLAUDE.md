# 115 STRM Gateway

115 网盘 STRM 文件管理系统，支持流媒体重定向和 STRM 文件生成。

## 项目结构

```
yijie-strm/
├── lib115/                    # Python SDK 核心库
│   ├── __init__.py           # 包入口
│   ├── config.py             # 配置管理
│   ├── auth/                 # 认证模块
│   │   └── token_manager.py  # Token 管理（扫码认证、自动刷新）
│   ├── api/                  # API 客户端
│   │   └── client.py         # 115 API 封装
│   ├── services/             # 业务服务
│   │   ├── file_service.py   # 文件服务（遍历、缓存）
│   │   └── strm_service.py   # STRM 服务（生成、同步）
│   ├── gateway/              # HTTP 网关
│   │   └── server.py         # REST API 服务
│   └── utils/                # 工具函数
│       └── helpers.py        # 辅助函数
├── web/                       # 前端项目 (Next.js + shadcn/ui)
│   ├── src/
│   │   ├── app/              # Next.js App Router
│   │   ├── components/       # React 组件
│   │   │   ├── ui/           # shadcn/ui 基础组件
│   │   │   ├── file-browser.tsx
│   │   │   ├── strm-manager.tsx
│   │   │   └── settings-panel.tsx
│   │   └── lib/              # 工具库
│   │       ├── api.ts        # API 客户端
│   │       └── utils.ts      # 工具函数
│   └── package.json
├── run_gateway.py             # 网关启动脚本
├── examples.py                # 使用示例
├── test_lib115.py             # 模块测试
└── 115client.py               # 原始 CLI 客户端
```

## 快速开始

### 后端服务

```bash
# 安装依赖
pip install requests

# 启动网关服务
python run_gateway.py --port 8115

# 首次运行需要扫码认证，Token 保存在 ~/.115_token.json
```

### 前端界面

```bash
cd web
npm install
npm run dev
# 访问 http://localhost:3000
```

## API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/stream/{pick_code}` | GET | 流媒体重定向（302） |
| `/api/list` | GET | 文件列表 |
| `/api/search` | GET | 文件搜索 |
| `/api/info` | GET | 文件信息 |
| `/api/download` | GET | 获取下载链接 |
| `/api/strm/generate` | POST | 生成 STRM 文件 |
| `/api/strm/sync` | POST | 同步 STRM 文件 |

## 使用示例

### Python SDK

```python
from lib115 import Client115, StrmService

# 列出文件
with Client115() as client:
    items, total = client.list_files('0')
    for item in items:
        print(item['fn'])

# 获取下载链接
url = client.get_download_url('pick_code_here')

# 生成 STRM 文件
strm_service = StrmService()
strm_service.generate_strm_files(
    root_cid='folder_cid',
    output_dir='/path/to/output',
    base_url='http://localhost:8115'
)
```

### HTTP API

```bash
# 列出文件
curl "http://localhost:8115/api/list?cid=0&limit=10"

# 搜索文件
curl "http://localhost:8115/api/search?keyword=movie"

# 获取下载链接
curl "http://localhost:8115/api/download?pick_code=xxx"

# 生成 STRM
curl -X POST "http://localhost:8115/api/strm/generate" \
  -H "Content-Type: application/json" \
  -d '{"cid": "xxx", "output_dir": "/path/to/strm"}'
```

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `GATEWAY_HOST` | `0.0.0.0` | 监听地址 |
| `GATEWAY_PORT` | `8115` | 监听端口 |
| `TOKEN_FILE_PATH` | `~/.115_token.json` | Token 存储路径 |
| `STRM_BASE_URL` | 空 | STRM 文件基础 URL |
| `CACHE_TTL` | `3600` | 下载链接缓存时间（秒） |

## 认证流程

1. 首次运行显示二维码
2. 使用 115 App 扫码授权
3. Token 自动保存到本地文件
4. 后续运行自动加载 Token
5. Token 过期前自动刷新

## 开发命令

```bash
# 运行测试
python test_lib115.py

# 启动后端（调试模式）
python run_gateway.py --debug

# 启动前端开发服务器
cd web && npm run dev

# 构建前端
cd web && npm run build
```

## 技术栈

- **后端**: Python 3.9+, requests
- **前端**: Next.js 14, React 18, TypeScript
- **UI**: shadcn/ui, Tailwind CSS, Radix UI
- **API**: 115 Open API (OAuth 2.0)
