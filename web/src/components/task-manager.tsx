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
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { api, StrmTask, Drive } from "@/lib/api"
import { cn } from "@/lib/utils"
import { TaskFormDialog } from "@/components/task-form-dialog"
import { TaskDetailDialog } from "@/components/task-detail-dialog"

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
    }, 2000) // Poll every 2 seconds

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
      // Refresh drives list to show unauthenticated status
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
      const result = await api.executeTask(taskId)
      alert("任务已开始执行")

      // 立即刷新以显示状态变化
      await loadTasks()
    } catch (error) {
      console.error("Failed to execute task:", error)
      const errorMessage = error instanceof Error ? error.message : "执行任务失败"

      // 检查是否是 token 错误
      if (errorMessage.includes('Token') || errorMessage.includes('token') || errorMessage.includes('认证') || errorMessage.includes('authenticate')) {
        alert("认证已失效，请前往网盘管理重新扫码认证")
        // 刷新网盘列表以显示未认证状态
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

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "running":
        return <Badge variant="default" className="bg-blue-500">运行中</Badge>
      case "success":
        return <Badge variant="default" className="bg-green-500">成功</Badge>
      case "error":
        return <Badge variant="destructive">错误</Badge>
      case "idle":
      default:
        return <Badge variant="secondary">空闲</Badge>
    }
  }

  const getDriveName = (driveId: string) => {
    const drive = drives.find(d => d.drive_id === driveId)
    return drive?.name || driveId
  }

  const formatDate = (timestamp?: number) => {
    if (!timestamp) return "从未运行"
    return new Date(timestamp * 1000).toLocaleString("zh-CN")
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">任务管理</h2>
          <p className="text-sm text-muted-foreground">
            自动化 STRM 文件生成和同步
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleToggleScheduler}
          >
            {schedulerRunning ? (
              <>
                <Pause className="h-4 w-4 mr-2" />
                停止调度器
              </>
            ) : (
              <>
                <Play className="h-4 w-4 mr-2" />
                启动调度器
              </>
            )}
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={loadTasks}
            disabled={loading}
          >
            <RefreshCw className={cn("h-4 w-4 mr-2", loading && "animate-spin")} />
            刷新
          </Button>
          <Button size="sm" onClick={handleCreateTask}>
            <Plus className="h-4 w-4 mr-2" />
            创建任务
          </Button>
        </div>
      </div>

      {/* 调度器状态卡片 */}
      <Card className={cn(schedulerRunning ? "border-green-500" : "border-orange-500")}>
        <CardHeader>
          <CardTitle className="text-sm font-medium">调度器状态</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-2">
            {schedulerRunning ? (
              <>
                <CheckCircle2 className="h-5 w-5 text-green-500" />
                <span className="text-green-600">运行中</span>
              </>
            ) : (
              <>
                <XCircle className="h-5 w-5 text-orange-500" />
                <span className="text-orange-600">已停止</span>
              </>
            )}
          </div>
        </CardContent>
      </Card>

      {/* 任务列表 */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {tasks.map((task) => (
          <Card
            key={task.task_id}
            className={cn(
              "transition-all",
              task.status === "running" && "ring-2 ring-blue-500"
            )}
          >
            <CardHeader>
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <CardTitle className="text-sm">{task.task_name}</CardTitle>
                  <CardDescription className="text-xs mt-1">
                    {getDriveName(task.drive_id)}
                  </CardDescription>
                </div>
                <div className="flex gap-1">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 w-7 p-0"
                    onClick={() => handleViewTask(task)}
                  >
                    <Eye className="h-3 w-3" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 w-7 p-0"
                    onClick={() => handleEditTask(task)}
                  >
                    <Edit2 className="h-3 w-3" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 w-7 p-0 text-destructive"
                    onClick={() => handleDeleteTask(task.task_id)}
                  >
                    <Trash2 className="h-3 w-3" />
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs text-muted-foreground">状态</span>
                {getStatusBadge(task.status)}
              </div>

              {/* 显示进度条（仅在运行时） */}
              {task.status === "running" && task.total_files > 0 && (
                <div className="space-y-1">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-muted-foreground">处理进度</span>
                    <span className="font-medium">
                      {task.current_file_index} / {task.total_files}
                    </span>
                  </div>
                  <div className="w-full bg-secondary rounded-full h-2">
                    <div
                      className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                      style={{
                        width: `${(task.current_file_index / task.total_files) * 100}%`
                      }}
                    />
                  </div>
                </div>
              )}

              <div className="space-y-1 text-xs">
                <div className="flex items-center gap-2">
                  <Clock className="h-3 w-3 text-muted-foreground" />
                  <span className="text-muted-foreground">上次运行:</span>
                </div>
                <div className="text-xs pl-5">
                  {formatDate(task.last_run_time)}
                </div>
              </div>

              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">总运行次数</span>
                <span className="font-medium">{task.total_runs}</span>
              </div>

              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">生成文件数</span>
                <span className="font-medium">{task.total_files_generated}</span>
              </div>

              <div className="flex gap-2 pt-2">
                {task.schedule_enabled && (
                  <Badge variant="outline" className="text-xs">
                    <Calendar className="h-3 w-3 mr-1" />
                    定时
                  </Badge>
                )}
                {task.watch_enabled && (
                  <Badge variant="outline" className="text-xs">
                    <Eye className="h-3 w-3 mr-1" />
                    监听
                  </Badge>
                )}
              </div>

              <Button
                variant="outline"
                size="sm"
                className="w-full"
                onClick={() => handleExecuteTask(task.task_id)}
                disabled={task.status === "running"}
              >
                <Play className="h-3 w-3 mr-1" />
                {task.status === "running" ? "执行中..." : "立即执行"}
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>

      {tasks.length === 0 && !loading && (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Clock className="h-12 w-12 text-muted-foreground mb-4" />
            <p className="text-muted-foreground mb-4">还没有创建任务</p>
            <Button onClick={handleCreateTask}>
              <Plus className="h-4 w-4 mr-2" />
              创建第一个任务
            </Button>
          </CardContent>
        </Card>
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
