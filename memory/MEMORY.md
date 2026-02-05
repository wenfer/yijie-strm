# 项目记忆

## 技术栈

### 后端
- **框架**: FastAPI 0.128+, Pydantic 2.x
- **ORM**: Tortoise ORM 0.25+ (异步)
- **任务调度**: APScheduler 3.10+
- **网盘客户端**: p115client
- **FUSE**: fusepy 3.0+ (用于挂载功能)

### 前端
- **框架**: Next.js 14 (App Router)
- **UI**: React 18 + TypeScript + Tailwind CSS
- **组件**: shadcn/ui

## 重要实现细节

### FUSE 挂载功能 (2024-02-05)

#### 架构设计
- 使用 `multiprocessing.Process` 在独立进程中运行 FUSE
- 通过 `multiprocessing.Queue` 实现父子进程间通信
- 日志通过队列传递，支持实时反馈到前端

#### 关键问题与解决

1. **Cookie 解析错误**
   - 问题: `P115Client` 接收 cookie 文件路径时解析失败
   - 解决: 添加 `_load_cookies()` 方法，手动解析 `key=value; key2=value2` 格式
   - 文件: `app/providers/fuse_ops.py`

2. **Tortoise ORM 关系加载**
   - 问题: `mount.drive.id` 返回 QuerySet 而非实际值
   - 解决: `to_dict()` 改为 async 方法，自动 `fetch_related('drive')`
   - 文件: `app/models/mount.py`

3. **前端 Dialog + Select 冲突**
   - 问题: Dialog 内 Select 下拉框无法点击
   - 解决: Select 添加 `modal={false}` 和 `position="popper"`
   - 文件: `web/src/components/mount-manager.tsx`

#### Docker 支持
- 需要安装 FUSE 系统库: `libfuse2`, `fuse`
- 容器运行需要 `--privileged` 或 `--device /dev/fuse`

### API 响应格式

成功响应:
```json
{
  "success": true,
  "message": "操作成功",
  "data": {...}
}
```

挂载启动响应:
```json
{
  "success": true,
  "message": "Mount started with PID 12345",
  "pid": 12345,
  "logs": [
    {"timestamp": "...", "level": "INFO", "message": "..."}
  ]
}
```

### 多进程日志传递

```python
# 子进程发送日志
message_queue.put({"type": "log", "level": "ERROR", "message": "..."})
message_queue.put({"type": "status", "status": "failed", "error": "..."})

# 父进程收集
msg = session.message_queue.get_nowait()
if msg.get("type") == "log":
    session.add_log(...)
```

## 目录结构约定

```
app/
  api/routes/    # FastAPI 路由
  models/        # Tortoise ORM 模型
  providers/     # 网盘客户端封装
  services/      # 业务逻辑层
  tasks/         # 定时任务
web/
  src/components/  # React 组件
  src/lib/api.ts   # API 客户端
memory/          # 项目记忆文档
```

## 常用命令

```bash
# 开发启动
python run.py

# Docker 构建
docker build -t yijie-strm .
docker run --privileged -p 8115:8115 yijie-strm

# 前端开发
cd web && pnpm dev
```

## 注意事项

1. **FUSE 挂载需要特权**: 容器运行必须 `--privileged` 或 `--cap-add SYS_ADMIN --device /dev/fuse`
2. **macOS FUSE**: 需要安装 macFUSE，且第一次运行需在系统设置中允许
3. **进程管理**: FUSE 进程异常退出时，`MountSession` 会自动清理
4. **日志保留**: 每个挂载会话最多保留 1000 条日志
