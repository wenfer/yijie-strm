# 多网盘 STRM 网关 v3.0

支持多网盘的通用 STRM 网关系统，基于 FastAPI + Tortoise ORM + p115client 构建。

包含 Next.js 实现的前端项目，前端项目位于 `web/` 目录。

## 环境要求

- **Python**: 3.13+
- **Node.js**: 22+ (前端开发)

## 核心架构

### 分层架构

```
# FastAPI 路由层
# 业务服务层
# Provider 层 (p115client)
# 第三方 API (115 网盘)
```

### 新目录结构

```
app/                              # FastAPI 应用主目录
├── __init__.py
├── main.py                      # FastAPI 应用入口
├── core/                        # 核心模块
│   ├── __init__.py
│   ├── config.py                # Pydantic Settings 配置
│   ├── exceptions.py            # 异常定义
│   └── security.py              # 安全认证工具
├── models/                      # Tortoise ORM 数据模型
│   ├── __init__.py
│   ├── drive.py                 # 网盘模型
│   └── task.py                  # 任务模型
├── api/                         # API 路由
│   ├── __init__.py
│   ├── schemas.py               # Pydantic 数据模型
│   ├── deps.py                  # 依赖注入
│   └── routes/                  # 路由模块
│       ├── __init__.py
│       ├── auth.py              # 认证路由
│       ├── drive.py             # 网盘管理路由
│       ├── file.py              # 文件操作路由
│       ├── task.py              # 任务管理路由
│       ├── stream.py            # 流媒体路由
│       └── system.py            # 系统路由
├── providers/                   # 网盘 Provider
│   ├── __init__.py
│   └── p115.py                  # p115client 封装
├── services/                    # 业务服务层
│   ├── __init__.py
│   ├── drive_service.py         # 网盘服务
│   ├── file_service.py          # 文件服务
│   ├── strm_service.py          # STRM 生成服务
│   └── task_service.py          # 任务服务
└── tasks/                       # 任务调度
    ├── __init__.py
    ├── scheduler.py             # APScheduler 调度器
    └── executor.py              # 任务执行器

web/                              # Next.js 前端项目
├── app/                         # App Router
├── components/                  # React 组件
├── lib/                         # 工具函数
└── package.json

docs/                             # p115client 文档
├── example/                     # 使用示例
└── reference/                   # API 参考

lib/                              # 旧版本代码 (废弃)
```

## 技术栈

### 后端
- **框架**: FastAPI 0.110+
- **ORM**: Tortoise ORM 0.20+
- **网盘客户端**: p115client
- **任务调度**: APScheduler 3.10+
- **配置**: Pydantic Settings
- **数据库**: SQLite (默认) / MySQL / PostgreSQL
- **登录认证**: 简单的 session/cookie 方式

### 前端
- **框架**: Next.js 14
- **UI**: React 18 + TypeScript
- **样式**: Tailwind CSS + shadcn/ui

## 快速开始

### 1. 安装依赖

```bash
# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 启动服务

```bash
# 默认配置启动
python run.py

# 指定端口
python run.py --port 8080

# 调试模式
python run.py --debug
```

### 3. 访问 API 文档

启动后访问: http://localhost:8115/docs

## API 端点

### 系统
| 端点 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 服务信息 |
| `/api/system/health` | GET | 健康检查 |
| `/api/system/info` | GET | 系统信息 |

### 认证
| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/auth/qrcode` | GET | 获取二维码 |
| `/api/auth/status` | GET | 检查认证状态 |
| `/api/auth/exchange` | POST | 交换 Token |
| `/api/auth/logout/{drive_id}` | POST | 退出登录（115网盘） |
| `/api/auth/login` | POST | 用户登录（表单提交） |
| `/api/auth/logout` | POST | 用户退出登录 |
| `/api/auth/me` | GET | 获取当前用户信息 |

### 网盘管理
| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/drives` | GET | 获取网盘列表 |
| `/api/drives` | POST | 创建网盘 |
| `/api/drives/current` | GET | 获取当前网盘 |
| `/api/drives/{drive_id}/switch` | POST | 切换当前网盘 |
| `/api/drives/{drive_id}/update` | POST | 更新网盘 |
| `/api/drives/{drive_id}` | DELETE | 删除网盘 |
| `/api/drives/{drive_id}/status` | GET | 获取认证状态 |
| `/api/drives/remove` | POST | 删除网盘（兼容旧版） |
| `/api/drives/switch` | POST | 切换网盘（兼容旧版） |
| `/api/drives/update` | POST | 更新网盘（兼容旧版） |

### 文件操作
| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/files/list?cid=0` | GET | 文件列表 |
| `/api/list` | GET | 文件列表（兼容旧版） |
| `/api/files/search` | GET | 搜索文件 |
| `/api/search` | GET | 搜索文件（兼容旧版） |
| `/api/files/info/{file_id}` | GET | 文件信息 |
| `/api/files/tree` | GET | 目录树 |
| `/api/download` | GET | 获取下载链接（兼容旧版） |

### 任务管理
| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/tasks` | GET | 获取任务列表 |
| `/api/tasks` | POST | 创建任务 |
| `/api/tasks/{task_id}` | GET | 获取任务详情 |
| `/api/tasks/{task_id}` | POST | 更新任务 |
| `/api/tasks/{task_id}/delete` | POST | 删除任务 |
| `/api/tasks/{task_id}/execute` | POST | 执行任务 |
| `/api/tasks/{task_id}/status` | GET | 任务状态 |
| `/api/tasks/{task_id}/statistics` | GET | 任务统计 |
| `/api/tasks/{task_id}/logs` | GET | 任务日志 |
| `/api/tasks/{task_id}/records` | GET | STRM 记录 |

### 流媒体
| 端点 | 方法 | 说明 |
|------|------|------|
| `/stream/{pick_code}` | GET | 302 重定向到下载链接 |
| `/download/{pick_code}` | GET | 获取下载链接 (API) |

## 环境变量

配置加载优先级:
1. 命令行参数 (CLI)
2. 环境变量 (ENV)
3. 根目录 `config.yaml`
4. 默认值

`config.yaml` 采用分组结构并映射到环境变量:

```yaml
gateway:
  host: "0.0.0.0"
  port: 8115
  debug: false
  strm_base_url: ""
  enable_cors: true
  cors_origins:
    - "*"
  cache_ttl: 3600

database:
  url: "sqlite://~/.strm_gateway.db"
  generate_schemas: true
  pool_min: 1
  pool_max: 10

log:
  level: "INFO"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"

data_dir: "~/.strm_gateway"
```

### 网关配置
| 变量 | 默认值 | 说明 |
|------|--------|------|
| `GATEWAY_HOST` | `0.0.0.0` | 监听地址 |
| `GATEWAY_PORT` | `8115` | 监听端口 |
| `GATEWAY_DEBUG` | `false` | 调试模式 |
| `STRM_BASE_URL` | - | STRM 文件基础 URL |
| `ENABLE_CORS` | `true` | 启用 CORS |

### 数据库配置
| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DB_URL` | `sqlite://~/.strm_gateway.db` | 数据库 URL |
| `DB_GENERATE_SCHEMAS` | `true` | 自动创建表结构 |

数据库 URL 格式:
- SQLite: `sqlite://path/to/db.sqlite3`
- MySQL: `mysql://user:password@localhost:3306/dbname`
- PostgreSQL: `postgres://user:password@localhost:5432/dbname`

### 日志配置
| 变量 | 默认值 | 说明 |
|------|--------|------|
| `LOG_LEVEL` | `INFO` | 日志级别 |

### 安全配置
| 变量 | 默认值 | 说明 |
|------|--------|------|
| `ADMIN_USERNAME` | `admin` | 管理员用户名 |
| `ADMIN_PASSWORD` | - | 管理员密码（未配置时自动生成并打印） |

**注意**: 如果未配置 `ADMIN_PASSWORD`，启动时会自动生成一个随机密码并打印到日志中。

## 认证流程

### 账号密码登录

系统支持简单的 session/cookie 登录：

1. **登录**: `POST /api/auth/login`
   - JSON 参数: `{"username": "admin", "password": "xxx"}`
   - 成功后会自动设置 `session_id` cookie
2. **获取用户信息**: `GET /api/auth/me`
   - 需要携带 cookie
3. **退出登录**: `POST /api/auth/logout`

基于 p115client 的扫码登录模式:

1. **获取二维码**: `GET /api/auth/qrcode`
   - 返回: `{success, qrcode_url, uid, time, sign}`
2. **用户扫码**: 使用 115 手机 APP 扫描二维码
3. **检查状态**: `GET /api/auth/status?uid=xxx&time=xxx&sign=xxx`
   - 返回: `{success, status, message}`
   - status: 0=等待扫码, 1=已扫码, 2=已确认
4. **交换 Token**: `POST /api/auth/exchange`
   - 参数: `{uid, drive_id}`
   - Cookie 保存到网盘的 cookie_file 路径
5. **验证认证**: 通过 `fs_files` API 验证 cookie 有效性

## 任务调度

支持两种调度类型:

### 间隔调度 (interval)
```json
{
  "schedule_type": "interval",
  "schedule_config": {
    "interval": 3600,
    "unit": "seconds"
  }
}
```

### Cron 调度 (cron)
```json
{
  "schedule_type": "cron",
  "schedule_config": {
    "minute": "0",
    "hour": "2",
    "day": "*",
    "month": "*",
    "day_of_week": "*"
  }
}
```

## 开发指南

### 添加新的 Provider

1. 在 `app/providers/` 下创建新的 Provider 文件
2. 实现文件列表、搜索、下载等方法
3. 在 DriveService 中添加支持

### 添加新的 API 路由

1. 在 `app/api/routes/` 下创建路由文件
2. 定义 Pydantic 模型 (schemas.py)
3. 在 main.py 中注册路由

## 数据模型

### Drive (网盘)
- `id`: 网盘 ID（数据库主键）
- `name`: 网盘名称
- `drive_type`: 网盘类型 (115, aliyun, ...)
- `cookie_file`: Cookie 文件路径
- `is_current`: 是否为当前默认网盘
- `created_at`: 创建时间
- `last_used`: 最后使用时间

**API 响应格式** (`to_dict()`):
```json
{
  "drive_id": "115_xxx",
  "name": "我的网盘",
  "drive_type": "115",
  "token_file": "/path/to/cookie.txt",
  "is_current": true,
  "is_authenticated": true,
  "created_at": 1234567890,
  "last_used": 1234567890
}
```

### StrmTask (任务)
- `id`: 任务 ID
- `name`: 任务名称
- `drive_id`: 关联网盘 ID
- `source_cid`: 源文件夹 CID
- `output_dir`: 输出目录
- `include_video`: 包含视频文件
- `include_audio`: 包含音频文件
- `custom_extensions`: 自定义扩展名列表
- `schedule_enabled`: 是否启用调度
- `schedule_type`: 调度类型 (interval/cron)
- `schedule_config`: 调度配置
- `watch_enabled`: 启用文件监听
- `watch_interval`: 监听间隔(秒)
- `delete_orphans`: 删除孤立文件
- `preserve_structure`: 保留目录结构
- `overwrite_strm`: 覆盖已有STRM
- `status`: 任务状态 (idle/pending/running/success/error)
- `last_run_time`: 上次运行时间
- `total_runs`: 总运行次数
- `total_files_generated`: 生成文件总数

### StrmRecord (STRM 记录)
- `id`: 记录 ID
- `task_id`: 关联任务 ID
- `file_id`: 文件 ID
- `pick_code`: PickCode
- `file_name`: 文件名
- `file_size`: 文件大小
- `file_path`: 文件路径
- `strm_path`: STRM 文件路径
- `strm_content`: STRM 文件内容
- `status`: 状态 (active/deleted)
- `created_at`: 创建时间
- `updated_at`: 更新时间

### TaskLog (任务日志)
- `id`: 日志 ID
- `task_id`: 关联任务 ID
- `start_time`: 开始时间
- `end_time`: 结束时间
- `duration`: 执行时长(秒)
- `status`: 状态
- `files_scanned`: 扫描文件数
- `files_added`: 新增文件数
- `files_updated`: 更新文件数
- `files_deleted`: 删除文件数

## p115client 数据结构说明

### fs_files 返回格式
```python
{
    "state": True,           # 请求状态
    "error": "",            # 错误信息
    "data": [...],          # 文件列表（不是字典）
    "count": 6,             # 总数
    "cid": "0",             # 当前目录ID
    # ... 其他字段
}
```

### 文件项字段映射
| p115client 字段 | 含义 | 说明 |
|----------------|------|------|
| `cid` | 文件/文件夹 ID | 唯一标识 |
| `n` | 文件名 | - |
| `s` | 文件大小 | 字节 |
| `pc` | pick_code | 下载/播放用 |
| `pid` | 父目录 ID | - |
| `fc` | 文件类别 | 0=文件, 1=文件夹 |
| `sha` | SHA1 值 | 可选 |

### Cookie 文件格式
- 格式: `UID=xxx; CID=xxx; SEID=xxx; KID=xxx`
- 编码: latin-1
- 存储路径: `~/.strm_gateway/{drive_id}.txt`


## 文档更新，发现下列情况，需要及时更新此文档
1. 修改模块或者文件定义
2. 发现文档描述与实际不符
3. 删除文件或模块
