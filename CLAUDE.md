# 115 STRM Gateway

115 网盘 STRM 文件管理系统，支持流媒体重定向、STRM 文件生成和自动化任务管理。

## 项目结构

```
yijie-strm/
├── lib115/                    # Python SDK 核心库
│   ├── __init__.py           # 包入口
│   ├── config.py             # 配置管理
│   ├── auth/                 # 认证模块
│   │   └── token_manager.py  # Token 管理（扫码认证、自动刷新）
│   ├── api/                  # API 客户端
│   │   └── client.py         # 115 API 封装（含事件 API）
│   ├── db/                   # 数据库模块
│   │   ├── base.py           # 数据库接口基类
│   │   ├── sqlite_db.py      # SQLite 实现
│   │   ├── mysql_db.py       # MySQL 实现
│   │   ├── factory.py        # 数据库工厂
│   │   └── migrations.py     # 数据库迁移工具
│   ├── services/             # 业务服务
│   │   ├── file_service.py   # 文件服务（遍历、缓存）
│   │   ├── strm_service.py   # STRM 服务（生成、同步）
│   │   ├── drive_service.py  # 网盘管理服务（多账号支持）
│   │   ├── task_service.py   # 任务管理服务（CRUD、记录、日志）
│   │   ├── scheduler_service.py  # 任务调度服务（定时、事件监听）
│   │   └── event_monitor.py  # 事件监听服务（基于 115 事件 API）
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
│   │   │   ├── drive-manager.tsx  # 网盘管理界面
│   │   │   ├── task-manager.tsx   # 任务管理界面（包含 STRM 操作）
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

# 可选：安装 MySQL 支持（如果使用 MySQL 数据库）
pip install pymysql

# 启动网关服务（无需预先认证）
python run_gateway.py --port 8115

# 服务启动后，通过前端界面或 API 进行认证
```

### 前端界面

```bash
cd web
npm install
npm run dev
# 访问 http://localhost:3000
# 首次使用需要通过界面添加 115 网盘连接并扫码认证
```

## API 端点

### 基础服务

| 端点 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/stream/{pick_code}` | GET | 流媒体重定向（302） |

### 认证管理

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/auth/qrcode` | GET | 获取认证二维码 |
| `/api/auth/status` | GET | 检查认证状态 |
| `/api/auth/exchange` | POST | 交换 Token |

### 网盘管理

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/drives` | GET | 获取网盘列表 |
| `/api/drives` | POST | 添加网盘 |
| `/api/drives/remove` | POST | 删除网盘 |
| `/api/drives/switch` | POST | 切换当前网盘 |
| `/api/drives/update` | POST | 更新网盘信息 |

### 文件操作

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/list` | GET | 文件列表 |
| `/api/search` | GET | 文件搜索 |
| `/api/info` | GET | 文件信息 |
| `/api/download` | GET | 获取下载链接 |

### 任务管理

**注意**: STRM 文件的生成和同步现在通过任务管理系统完成。创建任务后可以手动执行（一次性操作）或启用调度器（自动化操作）。

**文件监听**: 系统支持基于 115 事件 API 的实时文件监听，无需轮询即可检测文件变化。当启用 `watch_enabled` 时，系统会监听上传、移动、删除、重命名等文件系统事件，并自动触发 STRM 同步。

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/tasks` | GET | 获取任务列表 |
| `/api/tasks` | POST | 创建任务 |
| `/api/tasks/{task_id}` | GET | 获取任务详情 |
| `/api/tasks/{task_id}` | PUT | 更新任务 |
| `/api/tasks/{task_id}/delete` | POST | 删除任务 |
| `/api/tasks/{task_id}/execute` | POST | 手动执行任务 |
| `/api/tasks/{task_id}/status` | GET | 获取任务状态 |
| `/api/tasks/{task_id}/statistics` | GET | 获取任务统计 |
| `/api/tasks/{task_id}/logs` | GET | 获取任务日志 |
| `/api/tasks/{task_id}/records` | GET | 获取 STRM 记录 |

### 调度器管理

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/scheduler/status` | GET | 获取调度器状态 |
| `/api/scheduler/start` | POST | 启动调度器 |
| `/api/scheduler/stop` | POST | 停止调度器 |

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

#### 认证和文件操作

```bash
# 获取认证二维码
curl "http://localhost:8115/api/auth/qrcode"

# 检查认证状态
curl "http://localhost:8115/api/auth/status?uid=xxx&time=xxx&sign=xxx"

# 交换 Token
curl -X POST "http://localhost:8115/api/auth/exchange" \
  -H "Content-Type: application/json" \
  -d '{"uid": "xxx", "code_verifier": "xxx"}'

# 列出文件
curl "http://localhost:8115/api/list?cid=0&limit=10"

# 搜索文件
curl "http://localhost:8115/api/search?keyword=movie"

# 获取下载链接
curl "http://localhost:8115/api/download?pick_code=xxx"
```

#### 任务管理

```bash
# 创建 STRM 任务
curl -X POST "http://localhost:8115/api/tasks" \
  -H "Content-Type: application/json" \
  -d '{
    "task_name": "电影库同步",
    "drive_id": "115_1234567890",
    "source_cid": "2428417022609239936",
    "output_dir": "/volume1/media/movies",
    "base_url": "http://192.168.1.100:8115",
    "include_video": true,
    "include_audio": false,
    "schedule_enabled": true,
    "schedule_type": "interval",
    "schedule_config": {"interval": 3600, "unit": "seconds"},
    "watch_enabled": true,
    "watch_interval": 1800,
    "delete_orphans": true,
    "preserve_structure": true
  }'

# 获取任务列表
curl "http://localhost:8115/api/tasks"

# 获取任务详情
curl "http://localhost:8115/api/tasks/task_1234567890"

# 手动执行任务
curl -X POST "http://localhost:8115/api/tasks/task_1234567890/execute" \
  -H "Content-Type: application/json" \
  -d '{"force": false}'

# 获取任务统计
curl "http://localhost:8115/api/tasks/task_1234567890/statistics"

# 获取任务日志
curl "http://localhost:8115/api/tasks/task_1234567890/logs?limit=50"

# 获取 STRM 记录
curl "http://localhost:8115/api/tasks/task_1234567890/records"

# 更新任务
curl -X POST "http://localhost:8115/api/tasks/task_1234567890" \
  -H "Content-Type: application/json" \
  -d '{
    "task_name": "电影库同步（已更新）",
    "schedule_enabled": false
  }'

# 删除任务
curl -X POST "http://localhost:8115/api/tasks/task_1234567890/delete"

# 获取调度器状态
curl "http://localhost:8115/api/scheduler/status"

# 启动调度器
curl -X POST "http://localhost:8115/api/scheduler/start"

# 停止调度器
curl -X POST "http://localhost:8115/api/scheduler/stop"
```

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `GATEWAY_HOST` | `0.0.0.0` | 监听地址 |
| `GATEWAY_PORT` | `8115` | 监听端口 |
| `TOKEN_FILE_PATH` | `~/.115_token.json` | Token 存储路径 |
| `STRM_BASE_URL` | 空 | STRM 文件基础 URL |
| `CACHE_TTL` | `3600` | 下载链接缓存时间（秒） |
| `DB_TYPE` | `sqlite` | 数据库类型（sqlite/mysql） |
| `DB_PATH` | `~/.115_gateway.db` | SQLite 数据库路径 |
| `DB_HOST` | `localhost` | MySQL 主机地址 |
| `DB_PORT` | `3306` | MySQL 端口 |
| `DB_NAME` | `115_gateway` | MySQL 数据库名 |
| `DB_USER` | `root` | MySQL 用户名 |
| `DB_PASSWORD` | 空 | MySQL 密码 |

## 依赖管理

### 核心依赖

```bash
pip install requests schedule
```

### 可选依赖

```bash
# MySQL 支持
pip install pymysql
```

## 认证流程

### 服务启动流程
1. 后端服务启动时**不需要** Token，可以直接启动
2. 服务启动后处于"未认证"状态
3. 只有认证相关的 API 端点可用（`/health`, `/api/auth/*`）
4. 其他需要访问 115 网盘的端点会返回 401 错误

### Web 界面认证（推荐）
1. 访问前端界面 http://localhost:3000
2. 点击"添加 115 网盘连接"或"登录"按钮
3. 前端调用 `/api/auth/qrcode` 获取二维码
4. 显示二维码供用户扫描
5. 前端轮询 `/api/auth/status` 检查扫码状态
6. 扫码成功后调用 `/api/auth/exchange` 完成认证
7. 后端初始化 115 客户端，所有 API 端点可用
8. Token 保存到 `~/.115_token.json`，下次启动自动加载

### API 认证流程
1. 调用 `GET /api/auth/qrcode` 获取二维码 URL 和认证参数
   ```json
   {
     "success": true,
     "qrcode_url": "https://qrcodeapi.115.com/...",
     "uid": "xxx",
     "time": "xxx",
     "sign": "xxx",
     "code_verifier": "xxx"
   }
   ```

2. 显示二维码供用户扫描（使用前端 QR code 库）

3. 轮询 `GET /api/auth/status?uid=xxx&time=xxx&sign=xxx` 检查扫码状态
   ```json
   {
     "success": true,
     "status": 2,  // 1=未扫描, 2=已扫描
     "message": "已扫描"
   }
   ```

4. 扫码成功后调用 `POST /api/auth/exchange` 交换 Token
   ```json
   {
     "uid": "xxx",
     "code_verifier": "xxx"
   }
   ```

5. 认证成功响应
   ```json
   {
     "success": true,
     "message": "认证成功",
     "access_token": "xxx",
     "expires_in": 7200
   }
   ```

6. 后续所有 API 请求自动使用已保存的 Token

### 健康检查
使用 `/health` 端点检查服务状态和认证状态：
```bash
curl http://localhost:8115/health
```

响应：
```json
{
  "status": "ok",
  "timestamp": 1234567890,
  "authenticated": true,  // 是否已认证
  "token_valid": true     // Token 是否有效
}
```

### 命令行认证（仅限 115client.py）
- 原始 CLI 客户端 `115client.py` 仍支持命令行二维码显示
- 需要安装 `qrcode_terminal` 包（可选）
- 新的 lib115 SDK 不再依赖 qrcode_terminal

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

## 数据库配置

### 使用 SQLite（默认）

默认情况下，系统使用 SQLite 数据库，无需额外配置：

```bash
# 使用默认 SQLite 配置启动
python run_gateway.py
```

数据库文件位置：`~/.115_gateway.db`

### 使用 MySQL

如需使用 MySQL 数据库，需要先安装 MySQL 驱动：

```bash
pip install pymysql
```

然后通过环境变量配置：

```bash
export DB_TYPE=mysql
export DB_HOST=localhost
export DB_PORT=3306
export DB_NAME=115_gateway
export DB_USER=root
export DB_PASSWORD=your_password

python run_gateway.py
```

或者在启动时设置：

```bash
DB_TYPE=mysql DB_HOST=localhost DB_NAME=115_gateway DB_USER=root DB_PASSWORD=your_password python run_gateway.py
```

### 数据库表结构

系统会自动创建以下表：

#### drives 表（网盘账号）
| 字段 | 类型 | 说明 |
|------|------|------|
| drive_id | TEXT/VARCHAR(255) | 网盘 ID（主键） |
| name | TEXT/VARCHAR(255) | 网盘名称 |
| drive_type | TEXT/VARCHAR(50) | 网盘类型（默认 "115"） |
| token_file | TEXT/VARCHAR(500) | Token 文件路径 |
| created_at | REAL/DOUBLE | 创建时间（Unix 时间戳） |
| last_used | REAL/DOUBLE | 最后使用时间（Unix 时间戳） |

#### settings 表（系统设置）
| 字段 | 类型 | 说明 |
|------|------|------|
| key | TEXT/VARCHAR(255) | 设置键（主键） |
| value | TEXT | 设置值 |
| updated_at | REAL/DOUBLE | 更新时间（Unix 时间戳） |

### 数据迁移

系统会自动从旧的 JSON 文件（`~/.115_drives.json`）迁移数据到数据库：

1. 首次启动时，如果检测到 JSON 文件且数据库为空，会自动迁移
2. 迁移完成后，JSON 文件会被重命名为 `~/.115_drives.json.backup`
3. 后续启动将直接使用数据库，不再读取 JSON 文件

## 网盘管理

### 多账号支持

系统支持管理多个 115 网盘账号，每个账号独立认证和存储：

- 每个网盘账号有独立的 Token 文件
- 可以在不同账号之间快速切换
- 支持为每个账号设置自定义名称

### Web 界面管理

访问前端界面的"网盘管理"标签页，可以：

1. **添加网盘**：点击"添加网盘"按钮，输入名称后添加
2. **认证网盘**：对于未认证的网盘，点击"认证"按钮进行扫码认证
3. **切换网盘**：点击"切换"按钮切换到其他已认证的网盘
4. **编辑名称**：点击编辑图标修改网盘名称
5. **删除网盘**：点击删除图标删除网盘（会同时删除 Token 文件）

### API 管理

#### 获取网盘列表

```bash
curl http://localhost:8115/api/drives
```

响应：
```json
{
  "success": true,
  "drives": [
    {
      "drive_id": "115_1234567890",
      "name": "我的115网盘",
      "drive_type": "115",
      "token_file": "~/.115_token_115_1234567890.json",
      "created_at": 1234567890.0,
      "last_used": 1234567890.0,
      "is_authenticated": true,
      "is_current": true
    }
  ]
}
```

#### 添加网盘

```bash
curl -X POST http://localhost:8115/api/drives \
  -H "Content-Type: application/json" \
  -d '{"name": "我的115网盘"}'
```

#### 切换网盘

```bash
curl -X POST http://localhost:8115/api/drives/switch \
  -H "Content-Type: application/json" \
  -d '{"drive_id": "115_1234567890"}'
```

#### 更新网盘名称

```bash
curl -X POST http://localhost:8115/api/drives/update \
  -H "Content-Type: application/json" \
  -d '{"drive_id": "115_1234567890", "name": "新名称"}'
```

#### 删除网盘

```bash
curl -X POST http://localhost:8115/api/drives/remove \
  -H "Content-Type: application/json" \
  -d '{"drive_id": "115_1234567890"}'
```

## 技术栈

- **后端**: Python 3.9+, requests, sqlite3, pymysql (可选)
- **前端**: Next.js 14, React 18, TypeScript
- **UI**: shadcn/ui, Tailwind CSS, Radix UI
- **数据库**: SQLite (默认) / MySQL (可选)
- **API**: 115 Open API (OAuth 2.0)

## 事件监听机制

### 概述

系统支持基于 115 生活事件 API 的实时文件监听，无需轮询即可检测文件变化。这是一种高效的监听方式，相比传统的定期扫描目录，具有以下优势：

- **实时性**: 文件变化后几乎立即触发同步，延迟通常在秒级
- **低开销**: 不需要频繁扫描整个目录树，减少 API 调用和网络流量
- **精确性**: 可以准确识别变化类型（上传、移动、删除、重命名等）

### 工作原理

1. **事件订阅**: 当启用 `watch_enabled` 时，系统会为每个任务创建事件监听器
2. **事件拉取**: 监听器定期调用 115 生活事件 API，获取自上次检查以来的新事件
3. **事件过滤**: 只处理与监听目录相关的文件系统变更事件（忽略浏览类事件）
4. **触发同步**: 检测到相关变化时，自动触发 STRM 文件同步

### 支持的事件类型

系统会监听以下文件系统变更事件：

| 事件类型 | 说明 | 触发同步 |
|---------|------|---------|
| `upload_file` | 上传文件 | ✓ |
| `move_file` | 移动文件 | ✓ |
| `receive_files` | 接收文件（分享） | ✓ |
| `new_folder` | 新建文件夹 | ✓ |
| `copy_folder` | 复制文件夹 | ✓ |
| `folder_rename` | 重命名文件夹 | ✓ |
| `delete_file` | 删除文件 | ✓ |
| `browse_video` | 浏览视频 | ✗ |
| `browse_audio` | 浏览音频 | ✗ |

### 配置参数

在创建或更新任务时，可以配置以下参数：

```json
{
  "watch_enabled": true,        // 是否启用事件监听
  "watch_interval": 1800        // 检查间隔（秒），建议 1800-3600
}
```

**注意事项**:
- `watch_interval` 不是轮询间隔，而是事件检查间隔。即使设置较长的间隔，系统也能检测到该间隔内的所有事件
- 建议设置 30 分钟（1800 秒）到 1 小时（3600 秒）的检查间隔，平衡实时性和 API 调用频率
- 系统会自动记录最后处理的事件 ID（`last_event_id`），确保不会遗漏或重复处理事件

### 使用示例

#### 创建启用事件监听的任务

```bash
curl -X POST "http://localhost:8115/api/tasks" \
  -H "Content-Type: application/json" \
  -d '{
    "task_name": "电影库实时同步",
    "drive_id": "115_1234567890",
    "source_cid": "2428417022609239936",
    "output_dir": "/volume1/media/movies",
    "base_url": "http://192.168.1.100:8115",
    "watch_enabled": true,
    "watch_interval": 1800,
    "schedule_enabled": false
  }'
```

#### 监听工作流程

1. 用户在 115 网盘上传新电影文件
2. 系统在下次检查时（最多 30 分钟后）检测到 `upload_file` 事件
3. 自动触发 STRM 同步任务
4. 为新文件生成 STRM 文件
5. 更新 `last_event_id`，记录已处理的事件

### 与定时调度的配合

事件监听和定时调度可以同时启用，互为补充：

- **事件监听**: 处理实时变化，快速响应新增、移动、删除等操作
- **定时调度**: 定期全量同步，确保数据一致性，处理可能遗漏的变化

推荐配置：
```json
{
  "schedule_enabled": true,
  "schedule_type": "interval",
  "schedule_config": {"interval": 24, "unit": "hours"},  // 每天全量同步一次
  "watch_enabled": true,
  "watch_interval": 1800  // 每 30 分钟检查事件
}
```

### 限制和注意事项

1. **事件 API 限制**:
   - 115 不收集"复制文件"和"文件改名"的事件（只有文件夹改名）
   - 第三方上传可能没有上传事件
   - 从回收站还原的文件没有事件，但删除事件会消失

2. **目录过滤**:
   - 当前实现只检查事件的直接父目录是否匹配
   - 对于深层嵌套的子目录，可能需要额外的 API 调用来验证

3. **性能考虑**:
   - 每个 drive 共享一个事件监听器，多个任务监听同一个 drive 时不会重复调用 API
   - 建议合理设置 `watch_interval`，避免过于频繁的 API 调用

## 文档更新
新增文件，或修改文件定义，或模块职责变更都需要重新更新此文档