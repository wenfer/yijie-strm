# 115 STRM Gateway

支持多网盘的通用 STRM 网关系统

包含next.js实现的前端项目，前端项目位于web/



## 核心架构

### 2.1 分层架构

```
 # REST API 服务
 # 业务服务
 # 核心抽象层
 # 网盘适配器
 # 第三方 API
```

### 2.2 新的目录结构

```
lib/                              # 重命名（去除 115 专属性）
├── core/                         # 核心抽象层
│   ├── __init__.py
│   ├── provider.py              # CloudStorageProvider 接口
│   ├── auth.py                  # AuthProvider 接口、TokenWatcher
│   ├── models.py                # 统一数据模型
│   └── exceptions.py            # 异常定义
│
├── providers/                    # 网盘适配器
│   ├── __init__.py
│   ├── factory.py               # Provider 工厂
│   ├── base.py                  # BaseProvider（通用辅助）
│   │
│   ├── drive_115/               # 115 网盘适配器
│   │   ├── __init__.py
│   │   ├── provider.py          # Provider115（实现接口）
│   │   ├── auth.py              # Auth115（OAuth 实现）
│   │   ├── client.py            # 原 api/client.py（115 API 封装）
│   │   ├── config.py            # 115 特定配置
│   │   └── models.py            # 115 数据模型转换器
│   │
│   └── drive_aliyun/            # 阿里云盘适配器（示例）
│       ├── __init__.py
│       ├── provider.py
│       └── auth.py
│
├── services/                     # 业务服务层（通用化）
│   ├── file_service.py          # 文件服务（通过 Provider 接口）
│   ├── strm_service.py          # STRM 服务
│   ├── drive_service.py         # 网盘管理（支持多类型）
│   ├── task_service.py          # 任务管理
│   ├── scheduler_service.py     # 任务调度
│   └── event_service.py         # 事件监听（重命名）
│
├── db/                           # 数据访问层（保持不变）
│   ├── base.py
│   ├── sqlite_db.py
│   ├── mysql_db.py
│   └── factory.py
│
├── gateway/                      # HTTP 网关（保持不变）
│   └── server.py
│
├── utils/                        # 工具函数
│   └── helpers.py
│
├── config.py                     # 全局配置
└── __init__.py                   # 包入口
```

## 三、核心抽象设计

### 3.1 CloudStorageProvider 接口

**职责**：定义所有云存储提供商必须实现的操作

**核心方法**：

```python
class CloudStorageProvider(ABC):
    # 认证
    def authenticate() -> AuthToken
    def get_drive_info() -> DriveInfo

    # 文件操作
    def list_files(folder_id, limit, offset) -> (List[FileItem], total)
    def get_file_info(file_id) -> FileItem
    def search_files(keyword, folder_id) -> List[FileItem]
    def get_download_url(file_id) -> DownloadInfo

    # 文件管理（可选）
    def create_folder(parent_id, name) -> FileItem
    def rename(file_id, new_name) -> FileItem
    def move(file_id, target_folder_id) -> FileItem
    def delete(file_id) -> bool

    # 事件监听（可选）
    def supports_events() -> bool
    def get_events(from_event_id, limit) -> List[FileEvent]
```

### 3.2 AuthProvider 接口

**职责**：定义统一的认证流程

**核心方法**：

```python
class AuthProvider(ABC):
    # 二维码认证
    def get_qrcode() -> QRCodeAuth
    def check_qrcode_status(session_id) -> int
    def exchange_token(session_id, **kwargs) -> AuthToken

    # 令牌管理
    def refresh_token(token) -> AuthToken
    def save_token(token, file_path)
    def load_token(file_path) -> AuthToken
    def validate_token(token) -> bool

    # 智能刷新
    def auto_refresh_token(file_path) -> AuthToken
```

### 3.3 统一数据模型

**核心模型**：

- `FileItem`: 统一文件表示
  - `id`: 文件 ID（通用）
  - `download_id`: 下载标识符（如 115 的 pick_code）
  - `name`, `type`, `size`, `parent_id`
  - `raw_data`: 保存原始数据

- `FileEvent`: 文件变更事件
  - `event_id`, `event_type`, `file_id`, `timestamp`

- `AuthToken`: 认证令牌
  - `access_token`, `refresh_token`, `expires_at`

- `DriveInfo`: 网盘信息
  - `drive_id`, `drive_type`, `name`, `user_id`

- `DownloadInfo`: 下载信息
  - `url`, `expires_at`, `headers`

## 四、115 网盘适配实现

### 4.1 Provider115 实现

**位置**：`lib/providers/drive_115/provider.py`

**实现要点**：

```python
class Provider115(BaseProvider):
    provider_type = "115"

    def __init__(self, token_file: str):
        auth_provider = Auth115()
        super().__init__(auth_provider, token_file)
        self.client = Client115(self.auth_provider, token_file)

    def list_files(self, folder_id, limit, offset):
        # 调用 Client115.list_files()
        # 将 115 数据格式转换为 FileItem
        items_115 = self.client.list_files(folder_id, limit, offset)
        return [self._convert_to_file_item(item) for item in items_115]

    def get_download_url(self, file_id):
        # 115 使用 pick_code
        # FileItem.download_id 保存 pick_code
        url = self.client.get_download_url(file_id)
        return DownloadInfo(url=url)

    def _convert_to_file_item(self, item_115) -> FileItem:
        # 115 格式 -> FileItem
        return FileItem(
            id=item_115['fid'],
            name=item_115['fn'],
            type=self._map_file_type(item_115['fc']),
            size=item_115.get('fs', 0),
            parent_id=item_115['cid'],
            download_id=item_115.get('pc'),  # pick_code
            raw_data=item_115
        )
```

### 4.2 Auth115 实现

**位置**：`lib/providers/drive_115/auth.py`

**实现要点**：

```python
class Auth115(AuthProvider):
    def get_qrcode(self) -> QRCodeAuth:
        # 调用 115 OAuth 设备码 API
        # 返回二维码 URL 和会话信息
        pass

    def check_qrcode_status(self, session_id) -> int:
        # 轮询扫码状态
        pass

    def exchange_token(self, session_id, **kwargs) -> AuthToken:
        # 使用 PKCE 交换 Token
        # 将 115 Token 格式转换为 AuthToken
        pass

    def refresh_token(self, token) -> AuthToken:
        # 调用 115 刷新 API
        pass
```

### 4.3 文件映射关系

| 原文件 | 新位置 | 说明 |
|--------|--------|------|
| `lib/providers/drive_115/client.py` | 115 API 客户端 |
| `lib/providers/drive_115/auth.py` | 115 认证实现 |
| `lib/providers/drive_115/config.py` + `lib/config.py` | 分离 115 特定配置 |
| `lib/providers/drive_115/provider.py` | 集成到 Provider |

## 五、服务层

### 5.1 DriveService


```python
class DriveService:
    def add_drive(self, name: str, drive_type: str = "115"):
        # drive_type 支持 "115", "aliyun" 等
        drive = Drive(
            drive_id=f"{drive_type}_{timestamp}",
            drive_type=drive_type,  # 保存类型
            name=name,
            token_file=self._get_token_file_path(drive_id)
        )
        self.db.save_drive(drive)

    def get_provider(self, drive_id: str) -> CloudStorageProvider:
        # 通过工厂创建 Provider
        drive = self.db.get_drive(drive_id)
        return provider_factory.create(
            provider_type=drive.drive_type,
            token_file=drive.token_file
        )
```

### 5.2 StrmService

```python
class StrmService:
    def execute_task(self, task: Task):
        # 通过 DriveService 获取 Provider
        provider = self.drive_service.get_provider(task.drive_id)

        # 使用 Provider 接口（不依赖 115）
        items, _ = provider.list_files(task.source_cid)

        for item in items:
            if item.is_video:
                # 生成 STRM 文件
                strm_url = self._build_strm_url(
                    item.download_id,  # 通用字段
                    task.base_url
                )
```

### 5.3 FileService


```python
class FileService:
    def __init__(self, provider: CloudStorageProvider):
        self.provider = provider  # 依赖注入

    def traverse_folder(self, folder_id: str):
        # 使用 Provider 接口
        items, _ = self.provider.list_files(folder_id)
        # 递归遍历逻辑保持不变
```

## 六、添加新网盘的步骤

### 示例：添加阿里云盘支持

#### 步骤 1：创建 Provider 目录

```bash
mkdir -p lib/providers/drive_aliyun
```

#### 步骤 2：实现 AuthProvider

```python
# lib/providers/drive_aliyun/auth.py
class AuthAliyun(AuthProvider):
    def get_qrcode(self) -> QRCodeAuth:
        # 调用阿里云盘认证 API
        pass

    def refresh_token(self, token) -> AuthToken:
        # 阿里云盘刷新逻辑
        pass
```

#### 步骤 3：实现 CloudStorageProvider

```python
# lib/providers/drive_aliyun/provider.py
class ProviderAliyun(BaseProvider):
    provider_type = "aliyun"

    def list_files(self, folder_id, limit, offset):
        # 调用阿里云盘 API
        # 转换为 FileItem
        pass

    def get_download_url(self, file_id):
        # 获取阿里云盘下载链接
        pass
```

#### 步骤 4：注册 Provider

```python
# lib/providers/drive_aliyun/__init__.py
from .provider import ProviderAliyun
from ..factory import provider_factory

# 注册到工厂
provider_factory.register("aliyun", ProviderAliyun)
```

#### 步骤 5：使用

```bash
# 添加阿里云盘网盘
curl -X POST "http://localhost:8115/api/drives" \
  -d '{"name": "我的阿里云盘", "drive_type": "aliyun"}'

# 后续操作与 115 网盘完全一致
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

**注意**: 所有文件操作 API 都支持可选的 `drive_id` 查询参数，用于指定操作的网盘。如果不指定，则使用当前网盘。

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/list?drive_id=xxx` | GET | 文件列表（drive_id 可选） |
| `/api/search?drive_id=xxx` | GET | 文件搜索（drive_id 可选） |
| `/api/info?drive_id=xxx` | GET | 文件信息（drive_id 可选） |
| `/api/download?drive_id=xxx` | GET | 获取下载链接（drive_id 可选） |
| `/stream/{pick_code}?drive_id=xxx` | GET | 流媒体重定向（drive_id 可选） |

### 任务管理

**注意**: STRM 文件的生成和同步现在通过任务管理系统完成。创建任务后可以手动执行（一次性操作）或启用调度器（自动化操作）。

**文件监听**: 系统支持基于 115 事件 API 的实时文件监听，无需轮询即可检测文件变化。当启用 `watch_enabled` 时，系统会监听上传、移动、删除、重命名等文件系统事件，并自动触发 STRM 同步。

**源目录选择**: Web 界面提供可视化的文件夹选择器，用户可以通过浏览网盘目录来选择源文件夹，无需手动输入 CID。选择器支持：
- 面包屑导航，快速返回上级目录
- 实时加载子文件夹
- 显示当前选择的完整路径
- 自动过滤只显示文件夹

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
    "preserve_structure": true,
    "overwrite_strm": false
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
| `STRM_BASE_URL` | 空 | STRM 文件基础 URL |
| `CACHE_TTL` | `3600` | 下载链接缓存时间（秒） |
| `DB_TYPE` | `sqlite` | 数据库类型（sqlite/mysql） |
| `DB_PATH` | `~/.115_gateway.db` | SQLite 数据库路径 |
| `DB_HOST` | `localhost` | MySQL 主机地址 |
| `DB_PORT` | `3306` | MySQL 端口 |
| `DB_NAME` | `115_gateway` | MySQL 数据库名 |
| `DB_USER` | `root` | MySQL 用户名 |
| `DB_PASSWORD` | 空 | MySQL 密码 |

**注意**:
- 旧版本的 `TOKEN_FILE_PATH` 环境变量已废弃，现在每个网盘使用独立的 Token 文件（`~/.115_token_{drive_id}.json`）
- Token 文件路径由系统自动管理，存储在 drives 表中

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
7. Token 保存到该网盘的 Token 文件（`~/.115_token_{drive_id}.json`）
8. 后续访问该网盘时自动加载并验证 Token

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
     "code_verifier": "xxx",
     "drive_id": "115_1234567890"  // 可选，指定为哪个网盘认证
   }
   ```

5. 认证成功响应
   ```json
   {
     "success": true,
     "message": "认证成功",
     "drive_id": "115_1234567890",
     "access_token": "xxx",
     "expires_in": 7200
   }
   ```

6. Token 保存到该网盘的 Token 文件，后续访问该网盘时自动使用

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
  "authenticated": true,     // 当前网盘是否已认证
  "current_drive": "115_1234567890"  // 当前网盘 ID
}
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

### 多账号架构

系统采用**按需客户端池架构**，支持管理多个 115 网盘账号：

- **独立认证和存储**：每个网盘账号有独立的 Token 文件（`~/.115_token_{drive_id}.json`）
- **客户端池机制**：GatewayServer 维护一个客户端池，为每个 drive 缓存 `Client115`、`FileService` 和 `StrmService` 实例
- **按需创建和缓存**：首次访问某个网盘时创建服务实例并缓存，后续请求直接使用缓存
- **自动 Token 验证**：每次访问前验证 Token 是否有效，失效时自动清理缓存并标记为未认证
- **任务独立执行**：每个任务使用自己的 drive_id 获取对应的客户端，互不干扰
- **无缝切换**：切换当前网盘时无需重启调度器或重建客户端

### 架构优势

1. **真正的多账号隔离**：不同网盘的操作完全独立，避免相互影响
2. **性能优化**：客户端池减少了重复创建客户端的开销
3. **资源管理**：Token 失效时自动清理，避免资源泄漏
4. **灵活性**：API 支持显式指定 drive_id，也支持使用"当前网盘"概念
5. **调度器优化**：调度器为每个任务按需创建服务，无需持有全局服务实例

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

- **后端**: Python 3.9+, requests, schedule, sqlite3, pymysql (可选)
- **前端**: Next.js 14, React 18, TypeScript
- **UI**: shadcn/ui, Tailwind CSS, Radix UI
- **数据库**: SQLite (默认) / MySQL (可选)
- **API**: 115 Open API (OAuth 2.0)

## 架构设计

### 多账号客户端池架构

系统采用**客户端池（Client Pool）**架构来支持多账号管理：

#### GatewayServer 架构

```python
class GatewayServer:
    """STRM 网关服务器"""

    def __init__(self, config: AppConfig = None):
        self.config = config
        self.drive_service = DriveService(config)      # 网盘管理服务
        self.task_service = TaskService(db)            # 任务管理服务
        self.scheduler_service = SchedulerService(     # 调度服务
            task_service,
            drive_service,
            config
        )

        # 客户端池：缓存每个 drive 的服务实例
        self._client_pool: Dict[str, Dict] = {}
        self._client_pool_lock = threading.Lock()

    def get_services_for_drive(self, drive_id: str) -> Optional[Dict]:
        """
        获取指定网盘的服务实例（带缓存）

        Returns:
            {
                "client": Client115,
                "file_service": FileService,
                "strm_service": StrmService
            }
        """
        # 检查缓存
        if drive_id in self._client_pool:
            cached = self._client_pool[drive_id]
            # 验证 token 是否仍然有效
            if cached["client"].token_watcher.is_token_valid():
                return cached
            else:
                # Token 已过期，清理缓存
                cached["client"].close()
                del self._client_pool[drive_id]

        # 创建新的服务实例
        client = self.drive_service.get_client(drive_id)
        file_service = FileService(client, self.config)
        strm_service = StrmService(file_service, self.config, ...)

        # 缓存起来
        services = {"client": client, "file_service": file_service, "strm_service": strm_service}
        self._client_pool[drive_id] = services
        return services
```

#### SchedulerService 架构

```python
class SchedulerService:
    """任务调度服务"""

    def __init__(self, task_service: TaskService, drive_service=None, config=None):
        self.task_service = task_service
        self.drive_service = drive_service  # 用于获取客户端
        self.config = config

    def _get_strm_service_for_task(self, task: StrmTask):
        """为每个任务按需创建服务实例"""
        client = self.drive_service.get_client(task.drive_id)
        file_service = FileService(client, self.config)
        strm_service = StrmService(file_service, self.config, ...)
        return strm_service, client

    def _execute_task_wrapper(self, task_id: str):
        """执行任务"""
        task = self.task_service.get_task(task_id)

        # 获取该任务专用的服务实例
        strm_service, client = self._get_strm_service_for_task(task)

        try:
            # 执行任务
            result = strm_service.execute_task(task_id)
        finally:
            # 关闭客户端
            client.close()
```

#### 工作流程

1. **API 请求处理**:
   - 用户发起请求（如 `/api/list?drive_id=xxx`）
   - Handler 调用 `_require_auth(drive_id)` 验证认证状态
   - Handler 调用 `server_instance.get_services_for_drive(drive_id)` 获取服务
   - 使用返回的服务实例执行操作

2. **任务调度执行**:
   - 调度器触发任务执行
   - `_execute_task_wrapper` 从任务获取 `drive_id`
   - 调用 `_get_strm_service_for_task` 创建临时服务实例
   - 执行任务后关闭客户端

3. **客户端池管理**:
   - 首次访问某个 drive 时创建并缓存服务实例
   - 后续访问直接使用缓存，提高性能
   - Token 失效时自动清理缓存
   - 服务停止时清空整个客户端池

#### 架构优势

1. **性能优化**: 客户端池避免了重复创建客户端的开销
2. **资源隔离**: 每个 drive 的客户端完全独立，互不干扰
3. **自动管理**: Token 失效时自动清理，避免资源泄漏
4. **灵活扩展**: 支持显式指定 drive_id，也支持使用"当前网盘"
5. **并发安全**: 使用锁保护客户端池的并发访问

### 服务依赖关系

```
GatewayServer
├── DriveService (数据库存储，管理多个 drive)
│   └── get_client(drive_id) -> Client115
├── TaskService (数据库存储，管理任务)
├── SchedulerService (调度任务执行)
│   ├── task_service
│   ├── drive_service (用于获取客户端)
│   └── _get_strm_service_for_task() -> (StrmService, Client115)
└── _client_pool (缓存每个 drive 的服务实例)
    └── {drive_id: {client, file_service, strm_service}}

每个任务执行时：
Task -> SchedulerService -> DriveService.get_client(drive_id) -> Client115
                          -> FileService(client)
                          -> StrmService(file_service)
                          -> execute_task()
                          -> client.close()
```



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


## 验证改动
可以通过build的方式验证改动是否能通过编译校验，但不要直接启动开发服务

## 日志格式
所有日志输出都包含文件名和行号，格式为：
```
%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s
```


## 文档更新
新增文件，或修改文件定义，或模块职责变更都需要重新更新此文档，不轻易生成新的md文档

## 改动日志

### 2026-01-31: 多账号客户端池架构改造

#### 核心改动

1. **GatewayServer 架构重构**:
   - 移除全局客户端实例（`self.client`, `self.file_service`, `self.strm_service`）
   - 新增客户端池 `_client_pool` 用于缓存每个 drive 的服务实例
   - 新增 `get_services_for_drive(drive_id)` 方法，按需获取或创建服务
   - 新增 `_get_current_drive_id()` 方法，获取当前网盘 ID
   - 修改 `_require_auth(drive_id)` 方法，支持验证指定网盘的认证状态
   - 删除 `initialize_client()` 和 `initialize_client_for_drive()` 方法
   - 更新 `stop()` 方法，新增 `clear_client_pool()` 调用

2. **SchedulerService 架构重构**:
   - 移除 `strm_service` 依赖，改为接受 `drive_service` 和 `config` 参数
   - 新增 `_get_strm_service_for_task(task)` 方法，为每个任务按需创建服务
   - 修改 `_execute_task_wrapper()` 方法，按需创建服务并在执行后关闭客户端
   - 修改 `start_watch()` 方法，直接使用 `drive_service.get_client()`

3. **API 端点更新**:
   - 所有文件操作 API 支持可选的 `drive_id` 查询参数
   - `/stream/{pick_code}?drive_id=xxx` 支持指定网盘
   - `/api/list?drive_id=xxx` 支持指定网盘
   - `/api/search?drive_id=xxx` 支持指定网盘
   - `/api/info?drive_id=xxx` 支持指定网盘
   - `/api/download?drive_id=xxx` 支持指定网盘
   - `/api/auth/exchange` 支持 `drive_id` 参数指定认证目标
   - `/health` 返回 `current_drive` 字段

#### 架构优势

1. **真正的多账号支持**: 每个网盘独立认证和操作，互不干扰
2. **性能优化**: 客户端池缓存服务实例，避免重复创建
3. **简化切换逻辑**: 切换网盘不再需要重启调度器
4. **资源管理**: Token 失效时自动清理，任务执行后及时关闭客户端
5. **容错性**: Token 过期时自动标记为未认证，不影响其他网盘

#### 兼容性说明

- 旧版本的单网盘模式仍然兼容（通过"当前网盘"概念）
- API 的 `drive_id` 参数可选，不指定时使用当前网盘
- 旧版本的 `TOKEN_FILE_PATH` 环境变量已废弃，但不影响现有 Token 文件的读取

