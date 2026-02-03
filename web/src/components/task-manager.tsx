"use client"

import * as React from "react"
import { useState, useEffect } from "react"
import {
  Play,
  Plus,
  Trash2,
  Edit2,
  RefreshCw,
  Clock,
  CheckCircle2,
  XCircle,
  Pause,
  Eye,
  Calendar,
  FolderOpen,
  FileText,
  Zap,
  AlertCircle,
  Loader2,
  ChevronRight,
  Sparkles,
  Layers,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Switch } from "@/components/ui/switch"
import { api, StrmTask, Drive } from "@/lib/api"
import { cn } from "@/lib/utils"
import { TaskFormDialog } from "@/components/task-form-dialog"
import { TaskDetailDialog } from "@/components/task-detail-dialog"

// 相对时间格式化
function formatRelativeTime(value?: string | number): string {
  if (!value) return "从未运行"

  const date = typeof value === "string" ? new Date(value) : new Date(value * 1000)
  const timestamp = date.getTime()

  const now = Date.now()
  const diff = now - timestamp
  const seconds = Math.floor(diff / 1000)
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)
  const days = Math.floor(hours / 24)

  if (seconds < 60) return "刚刚"
  if (minutes < 60) return `${minutes} 分钟前`
  if (hours < 24) return `${hours} 小时前`
  if (days < 30) return `${days} 天前`

  return date.toLocaleDateString("zh-CN")
}

// 完整时间格式化（用于 tooltip）
function formatFullDate(value?: string | number): string {
  if (!value) return "从未运行"
  const date = typeof value === "string" ? new Date(value) : new Date(value * 1000)
  return date.toLocaleString("zh-CN")
}

export function TaskManager() {
  const [tasks, setTasks] = useState<StrmTask[]>([])
  const [drives, setDrives] = useState<Drive[]>([])
  const [loading, setLoading] = useState(false)
  const [formDialogOpen, setFormDialogOpen] = useState(false)
  const [detailDialogOpen, setDetailDialogOpen] = useState(false)
  const [editingTask, setEditingTask] = useState<StrmTask | null>(null)
  const [selectedTask, setSelectedTask] = useState<StrmTask | null>(null)
  const [schedulerRunning, setSchedulerRunning] = useState(false)

  useEffect(() => {
    loadTasks()
    loadDrives()
    loadSchedulerStatus()
  }, [])

  // Poll for task status when any task is running
  useEffect(() => {
    const runningTasks = tasks.filter(t => t.status === 'running')
    if (runningTasks.length === 0) return

    const interval = setInterval(() => {
      loadTasks()
    }, 2000)

    return () => clearInterval(interval)
  }, [tasks])

  // Check for authentication errors in task status
  useEffect(() => {
    const errorTasks = tasks.filter(t =>
      t.status === 'error' &&
      t.last_run_message &&
      (t.last_run_message.includes('Token') ||
       t.last_run_message.includes('token') ||
       t.last_run_message.includes('authenticate') ||
       t.last_run_message.includes('认证'))
    )

    if (errorTasks.length > 0) {
      loadDrives()
    }
  }, [tasks])

  const loadTasks = async () => {
    setLoading(true)
    try {
      const result = await api.listTasks()
      setTasks(result.tasks)
    } catch (error) {
      console.error("Failed to load tasks:", error)
      const errorMessage = error instanceof Error ? error.message : "加载任务列表失败"
      alert(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  const loadDrives = async () => {
    try {
      const result = await api.listDrives()
      setDrives(result.drives)
    } catch (error) {
      console.error("Failed to load drives:", error)
    }
  }

  const loadSchedulerStatus = async () => {
    try {
      const result = await api.getSchedulerStatus()
      setSchedulerRunning(result.scheduler.running)
    } catch (error) {
      console.error("Failed to load scheduler status:", error)
    }
  }

  const handleCreateTask = () => {
    setEditingTask(null)
    setFormDialogOpen(true)
  }

  const handleEditTask = (task: StrmTask) => {
    setEditingTask(task)
    setFormDialogOpen(true)
  }

  const handleViewTask = (task: StrmTask) => {
    setSelectedTask(task)
    setDetailDialogOpen(true)
  }

  const handleDeleteTask = async (taskId: string) => {
    if (!confirm("确定要删除这个任务吗？所有相关的 STRM 记录和日志也会被删除。")) return

    try {
      await api.deleteTask(taskId)
      await loadTasks()
    } catch (error) {
      console.error("Failed to delete task:", error)
      alert("删除任务失败")
    }
  }

  const handleExecuteTask = async (taskId: string) => {
    try {
      await api.executeTask(taskId)
      alert("任务已开始执行")
      await loadTasks()
    } catch (error) {
      console.error("Failed to execute task:", error)
      const errorMessage = error instanceof Error ? error.message : "执行任务失败"

      if (errorMessage.includes('Token') || errorMessage.includes('token') || errorMessage.includes('认证') || errorMessage.includes('authenticate')) {
        alert("认证已失效，请前往网盘管理重新扫码认证")
        await loadDrives()
      } else {
        alert(errorMessage)
      }

      await loadTasks()
    }
  }

  const handleToggleScheduler = async () => {
    try {
      if (schedulerRunning) {
        await api.stopScheduler()
        setSchedulerRunning(false)
      } else {
        await api.startScheduler()
        setSchedulerRunning(true)
      }
    } catch (error) {
      console.error("Failed to toggle scheduler:", error)
      alert("调度器操作失败")
    }
  }

  const handleFormSuccess = async () => {
    await loadTasks()
  }

  const getDriveName = (driveId: string) => {
    const drive = drives.find(d => d.drive_id === driveId)
    return drive?.name || driveId
  }

  // 状态配置
  const statusConfig = {
    running: {
      label: "运行中",
      color: "blue",
      icon: Loader2,
      gradient: "from-blue-500/10 via-cyan-500/5 to-transparent",
      borderColor: "border-l-blue-500",
      glowColor: "shadow-blue-500/20",
      badgeClass: "bg-blue-500/10 text-blue-600 border-blue-500/20",
    },
    success: {
      label: "成功",
      color: "green",
      icon: CheckCircle2,
      gradient: "from-green-500/10 via-emerald-500/5 to-transparent",
      borderColor: "border-l-green-500",
      glowColor: "shadow-green-500/20",
      badgeClass: "bg-green-500/10 text-green-600 border-green-500/20",
    },
    error: {
      label: "错误",
      color: "red",
      icon: AlertCircle,
      gradient: "from-red-500/10 via-rose-500/5 to-transparent",
      borderColor: "border-l-red-500",
      glowColor: "shadow-red-500/20",
      badgeClass: "bg-red-500/10 text-red-600 border-red-500/20",
    },
    idle: {
      label: "空闲",
      color: "gray",
      icon: Clock,
      gradient: "from-slate-500/5 via-gray-500/5 to-transparent",
      borderColor: "border-l-slate-400",
      glowColor: "shadow-slate-500/10",
      badgeClass: "bg-slate-500/10 text-slate-600 border-slate-500/20",
    },
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">任务管理</h2>
          <p className="text-sm text-muted-foreground mt-1">
            自动化 STRM 文件生成和同步
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={loadTasks}
            disabled={loading}
            className="gap-2"
          >
            <RefreshCw className={cn("h-4 w-4", loading && "animate-spin")} />
            刷新
          </Button>
          <Button size="sm" onClick={handleCreateTask} className="gap-2">
            <Plus className="h-4 w-4" />
            创建任务
          </Button>
        </div>
      </div>

      {/* 调度器状态卡片 */}
      <div className={cn(
        "relative overflow-hidden rounded-2xl border p-6 transition-all duration-500",
        "bg-gradient-to-br",
        schedulerRunning 
          ? "from-green-500/5 via-emerald-500/5 to-teal-500/5 border-green-500/30" 
          : "from-orange-500/5 via-amber-500/5 to-yellow-500/5 border-orange-500/30"
      )}>
        {/* 背景发光效果 */}
        <div className={cn(
          "absolute -right-20 -top-20 h-40 w-40 rounded-full blur-3xl transition-opacity duration-500",
          schedulerRunning ? "bg-green-500/20 opacity-100" : "bg-orange-500/20 opacity-100"
        )} />
        
        <div className="relative flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="flex items-center gap-4">
            {/* 状态指示器 */}
            <div className={cn(
              "relative flex h-12 w-12 items-center justify-center rounded-xl transition-all duration-500",
              schedulerRunning 
                ? "bg-green-500/10 shadow-lg shadow-green-500/25" 
                : "bg-orange-500/10 shadow-lg shadow-orange-500/25"
            )}>
              {schedulerRunning ? (
                <>
                  <CheckCircle2 className="h-6 w-6 text-green-600" />
                  {/* 脉冲动画 */}
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-xl bg-green-400/30 opacity-75" />
                </>
              ) : (
                <Pause className="h-6 w-6 text-orange-600" />
              )}
            </div>
            
            <div>
              <h3 className="font-semibold text-lg">调度器状态</h3>
              <div className="flex items-center gap-2 mt-0.5">
                <span className={cn(
                  "text-sm font-medium",
                  schedulerRunning ? "text-green-600" : "text-orange-600"
                )}>
                  {schedulerRunning ? "运行中" : "已停止"}
                </span>
                <span className="text-muted-foreground text-sm">
                  · {tasks.filter(t => t.schedule_enabled).length} 个定时任务
                </span>
              </div>
            </div>
          </div>

          {/* 开关控制 */}
          <div className="flex items-center gap-3">
            <span className="text-sm text-muted-foreground">
              {schedulerRunning ? "关闭调度器" : "启动调度器"}
            </span>
            <Switch
              checked={schedulerRunning}
              onCheckedChange={handleToggleScheduler}
              className={cn(
                "data-[state=checked]:bg-green-500",
                schedulerRunning && "shadow-lg shadow-green-500/30"
              )}
            />
          </div>
        </div>
      </div>

      {/* 任务列表 */}
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {tasks.map((task) => {
          const config = statusConfig[task.status as keyof typeof statusConfig] || statusConfig.idle
          const StatusIcon = config.icon
          const progress = task.total_files > 0 
            ? Math.round((task.current_file_index / task.total_files) * 100) 
            : 0

          return (
            <div
              key={task.id}
              className={cn(
                "group relative overflow-hidden rounded-xl border bg-white/50 backdrop-blur-sm transition-all duration-300",
                "hover:shadow-lg hover:-translate-y-0.5",
                "dark:bg-slate-900/50",
                config.borderColor,
                "border-l-4",
                config.glowColor,
                task.status === "running" && "shadow-lg ring-1 ring-blue-500/20"
              )}
            >
              {/* 渐变背景 */}
              <div className={cn(
                "absolute inset-0 bg-gradient-to-br opacity-50 transition-opacity",
                config.gradient
              )} />

              <div className="relative p-5">
                {/* 卡片头部 */}
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <FolderOpen className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                      <h3 className="font-semibold text-sm truncate">{task.name}</h3>
                    </div>
                    <p className="text-xs text-muted-foreground mt-1 truncate pl-6">
                      {getDriveName(task.drive_id)}
                    </p>
                  </div>

                  {/* 操作按钮组 - 悬浮显示 */}
                  <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7 text-muted-foreground hover:text-foreground"
                      onClick={() => handleViewTask(task)}
                    >
                      <Eye className="h-3.5 w-3.5" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7 text-muted-foreground hover:text-foreground"
                      onClick={() => handleEditTask(task)}
                    >
                      <Edit2 className="h-3.5 w-3.5" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7 text-muted-foreground hover:text-destructive"
                      onClick={() => handleDeleteTask(task.id)}
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                </div>

                {/* 状态徽章 */}
                <div className="mt-4 flex items-center gap-2">
                  <div className={cn(
                    "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border",
                    config.badgeClass
                  )}>
                    <StatusIcon className={cn("h-3.5 w-3.5", task.status === "running" && "animate-spin")} />
                    {config.label}
                  </div>

                  {task.schedule_enabled && (
                    <Badge variant="outline" className="text-xs gap-1 px-2 py-0.5">
                      <Calendar className="h-3 w-3" />
                      定时
                    </Badge>
                  )}
                  {task.watch_enabled && (
                    <Badge variant="outline" className="text-xs gap-1 px-2 py-0.5">
                      <Zap className="h-3 w-3" />
                      监听
                    </Badge>
                  )}
                </div>

                {/* 进度条 - 仅在运行时显示 */}
                {task.status === "running" && task.total_files > 0 && (
                  <div className="mt-4 space-y-2">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-muted-foreground">处理进度</span>
                      <span className="font-medium text-blue-600">{progress}%</span>
                    </div>
                    <div className="relative h-2 bg-slate-200/50 dark:bg-slate-700/50 rounded-full overflow-hidden">
                      {/* 渐变进度条 */}
                      <div
                        className="absolute inset-y-0 left-0 bg-gradient-to-r from-blue-500 via-cyan-400 to-blue-500 rounded-full transition-all duration-500"
                        style={{ width: `${progress}%` }}
                      >
                        {/* 流动光效 */}
                        <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/40 to-transparent animate-flow-shine" />
                      </div>
                    </div>
                    <div className="text-xs text-muted-foreground text-right">
                      {task.current_file_index} / {task.total_files}
                    </div>
                  </div>
                )}

                {/* 信息网格 */}
                <div className="mt-4 grid grid-cols-2 gap-3">
                  <div className="flex items-center gap-2 text-xs">
                    <Clock className="h-3.5 w-3.5 text-muted-foreground" />
                    <span className="text-muted-foreground" title={formatFullDate(task.last_run_time)}>
                      {formatRelativeTime(task.last_run_time)}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 text-xs">
                    <Layers className="h-3.5 w-3.5 text-muted-foreground" />
                    <span className="text-muted-foreground">运行 {task.total_runs} 次</span>
                  </div>
                  <div className="flex items-center gap-2 text-xs col-span-2">
                    <FileText className="h-3.5 w-3.5 text-muted-foreground" />
                    <span className="text-muted-foreground">已生成 {task.total_files_generated} 个文件</span>
                  </div>
                </div>

                {/* 执行按钮 */}
                <Button
                  variant={task.status === "running" ? "outline" : "default"}
                  size="sm"
                  className={cn(
                    "w-full mt-4 gap-2 transition-all",
                    task.status === "running" && "opacity-50 cursor-not-allowed"
                  )}
                  onClick={() => handleExecuteTask(task.id)}
                  disabled={task.status === "running"}
                >
                  {task.status === "running" ? (
                    <>
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      执行中...
                    </>
                  ) : (
                    <>
                      <Play className="h-3.5 w-3.5" />
                      立即执行
                    </>
                  )}
                </Button>
              </div>
            </div>
          )
        })}
      </div>

      {/* 空状态 */}
      {tasks.length === 0 && !loading && (
        <div className="relative overflow-hidden rounded-2xl border border-dashed p-12">
          {/* 背景装饰 */}
          <div className="absolute inset-0 bg-gradient-to-br from-slate-50/50 via-white to-slate-50/50 dark:from-slate-900/50 dark:via-slate-900 dark:to-slate-900/50" />
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-64 h-64 bg-blue-500/5 rounded-full blur-3xl" />
          <div className="absolute top-1/3 right-1/4 w-32 h-32 bg-purple-500/5 rounded-full blur-2xl" />
          
          <div className="relative flex flex-col items-center justify-center text-center">
            <div className="relative">
              <div className="flex h-20 w-20 items-center justify-center rounded-2xl bg-gradient-to-br from-slate-100 to-slate-200 dark:from-slate-800 dark:to-slate-700 shadow-lg">
                <Sparkles className="h-10 w-10 text-slate-400" />
              </div>
              <div className="absolute -bottom-1 -right-1 flex h-8 w-8 items-center justify-center rounded-full bg-blue-500 shadow-lg shadow-blue-500/30">
                <Plus className="h-5 w-5 text-white" />
              </div>
            </div>
            
            <h3 className="mt-6 text-lg font-semibold text-slate-900 dark:text-slate-100">
              开始创建你的第一个任务
            </h3>
            <p className="mt-2 text-sm text-muted-foreground max-w-sm">
              创建任务来自动化生成 STRM 文件，支持定时同步和实时监听网盘变化
            </p>
            
            <Button onClick={handleCreateTask} className="mt-6 gap-2">
              <Plus className="h-4 w-4" />
              创建第一个任务
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}

      <TaskFormDialog
        open={formDialogOpen}
        onOpenChange={setFormDialogOpen}
        task={editingTask}
        drives={drives}
        onSuccess={handleFormSuccess}
      />

      <TaskDetailDialog
        open={detailDialogOpen}
        onOpenChange={setDetailDialogOpen}
        task={selectedTask}
      />
    </div>
  )
}
