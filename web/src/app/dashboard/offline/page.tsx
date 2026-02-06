"use client"

import { useState, useEffect, useCallback } from "react"
import {
  Download,
  Plus,
  Trash2,
  RefreshCw,
  Play,
  Pause,
  FolderOpen,
  HardDrive,
  Link,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Loader2,
  MoreVertical,
  ExternalLink,
} from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
} from "@/components/ui/dialog"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  getOfflineList,
  addOfflineUrl,
  removeOfflineTasks,
  clearOfflineTasks,
  restartOfflineTask,
  getOfflineQuota,
  getOfflineCount,
  getOfflineDownloadPath,
  listDrives,
  type OfflineTask,
  type Drive,
  type OfflineQuotaInfo,
  type OfflineTaskCount,
} from "@/lib/api"
import { cn } from "@/lib/utils"

// 任务状态映射
const statusMap: Record<number, { label: string; color: string; bgColor: string; icon: any }> = {
  0: { label: "等待中", color: "text-yellow-500", bgColor: "bg-yellow-500/10", icon: Pause },
  1: { label: "下载中", color: "text-blue-500", bgColor: "bg-blue-500/10", icon: Download },
  2: { label: "已完成", color: "text-green-500", bgColor: "bg-green-500/10", icon: CheckCircle2 },
  [-1]: { label: "失败", color: "text-red-500", bgColor: "bg-red-500/10", icon: XCircle },
  3: { label: "未知", color: "text-gray-500", bgColor: "bg-gray-500/10", icon: AlertCircle },
}

export default function OfflineDownloadPage() {
  const [tasks, setTasks] = useState<OfflineTask[]>([])
  const [loading, setLoading] = useState(true)
  const [drives, setDrives] = useState<Drive[]>([])
  const [selectedDrive, setSelectedDrive] = useState<string>("")
  const [quota, setQuota] = useState<OfflineQuotaInfo | null>(null)
  const [count, setCount] = useState<OfflineTaskCount | null>(null)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const perPage = 20

  // 添加任务对话框
  const [addDialogOpen, setAddDialogOpen] = useState(false)
  const [newUrl, setNewUrl] = useState("")
  const [adding, setAdding] = useState(false)

  // 刷新中状态
  const [refreshing, setRefreshing] = useState(false)

  // 获取网盘列表
  const fetchDrives = useCallback(async () => {
    try {
      const res = await listDrives()
      if (res.success) {
        setDrives(res.drives)
        // 选择当前网盘
        const current = res.drives.find((d) => d.is_current)
        if (current) {
          setSelectedDrive(current.drive_id)
        } else if (res.drives.length > 0) {
          setSelectedDrive(res.drives[0].drive_id)
        }
      }
    } catch (err) {
      console.error("Failed to fetch drives:", err)
    }
  }, [])

  // 获取任务列表
  const fetchTasks = useCallback(async () => {
    if (!selectedDrive) return
    setLoading(true)
    try {
      const res = await getOfflineList(page, perPage, selectedDrive)
      if (res.success) {
        setTasks(res.tasks)
        setTotal(res.total)
      }
    } catch (err) {
      console.error("Failed to fetch tasks:", err)
    } finally {
      setLoading(false)
    }
  }, [selectedDrive, page])

  // 获取配额信息
  const fetchQuota = useCallback(async () => {
    if (!selectedDrive) return
    try {
      const res = await getOfflineQuota(selectedDrive)
      if (res.success) {
        setQuota(res.data)
      }
    } catch (err) {
      console.error("Failed to fetch quota:", err)
    }
  }, [selectedDrive])

  // 获取任务统计
  const fetchCount = useCallback(async () => {
    if (!selectedDrive) return
    try {
      const res = await getOfflineCount(selectedDrive)
      if (res.success) {
        setCount(res.data)
      }
    } catch (err) {
      console.error("Failed to fetch count:", err)
    }
  }, [selectedDrive])

  // 刷新所有数据
  const refreshAll = useCallback(async () => {
    setRefreshing(true)
    await Promise.all([fetchTasks(), fetchQuota(), fetchCount()])
    setRefreshing(false)
  }, [fetchTasks, fetchQuota, fetchCount])

  // 初始加载
  useEffect(() => {
    fetchDrives()
  }, [fetchDrives])

  // 当网盘改变时重新加载数据
  useEffect(() => {
    if (selectedDrive) {
      refreshAll()
    }
  }, [selectedDrive, page])

  // 自动刷新（每 10 秒）
  useEffect(() => {
    if (!selectedDrive) return
    const interval = setInterval(() => {
      refreshAll()
    }, 10000)
    return () => clearInterval(interval)
  }, [selectedDrive, refreshAll])

  // 添加任务
  const handleAddTask = async () => {
    if (!newUrl.trim() || !selectedDrive) return
    setAdding(true)
    try {
      const res = await addOfflineUrl(newUrl.trim(), undefined, selectedDrive)
      if (res.success) {
        setNewUrl("")
        setAddDialogOpen(false)
        refreshAll()
      } else {
        alert(res.message || "添加任务失败")
      }
    } catch (err: any) {
      alert(err.message || "添加任务失败")
    } finally {
      setAdding(false)
    }
  }

  // 删除任务
  const handleDeleteTask = async (infoHash: string) => {
    if (!confirm("确定要删除这个任务吗？")) return
    try {
      const res = await removeOfflineTasks([infoHash], selectedDrive)
      if (res.success) {
        refreshAll()
      } else {
        alert(res.message || "删除任务失败")
      }
    } catch (err: any) {
      alert(err.message || "删除任务失败")
    }
  }

  // 清空已完成任务
  const handleClearCompleted = async () => {
    if (!confirm("确定要清空已完成的任务吗？")) return
    try {
      const res = await clearOfflineTasks(0, selectedDrive)
      if (res.success) {
        refreshAll()
      } else {
        alert(res.message || "清空任务失败")
      }
    } catch (err: any) {
      alert(err.message || "清空任务失败")
    }
  }

  // 重启任务
  const handleRestartTask = async (infoHash: string) => {
    try {
      const res = await restartOfflineTask(infoHash, selectedDrive)
      if (res.success) {
        refreshAll()
      } else {
        alert(res.message || "重启任务失败")
      }
    } catch (err: any) {
      alert(err.message || "重启任务失败")
    }
  }

  // 计算配额使用百分比
  const quotaPercent = quota && quota.total > 0 ? (quota.used / quota.total) * 100 : 0

  return (
    <div className="space-y-6">
      {/* 头部工具栏 */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-4">
          <Select value={selectedDrive} onValueChange={setSelectedDrive}>
            <SelectTrigger className="w-[200px]">
              <HardDrive className="h-4 w-4 mr-2" />
              <SelectValue placeholder="选择网盘" />
            </SelectTrigger>
            <SelectContent>
              {drives.map((drive) => (
                <SelectItem key={drive.drive_id} value={drive.drive_id}>
                  {drive.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Button variant="outline" size="icon" onClick={refreshAll} disabled={refreshing}>
            <RefreshCw className={cn("h-4 w-4", refreshing && "animate-spin")} />
          </Button>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={handleClearCompleted}>
            <Trash2 className="h-4 w-4 mr-2" />
            清空已完成
          </Button>

          <Dialog open={addDialogOpen} onOpenChange={setAddDialogOpen}>
            <DialogTrigger asChild>
              <Button>
                <Plus className="h-4 w-4 mr-2" />
                添加任务
              </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-[500px]">
              <DialogHeader>
                <DialogTitle>添加云下载任务</DialogTitle>
                <DialogDescription>
                  支持 HTTP/HTTPS、磁力链(magnet:)、电驴(ed2k:) 等链接
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4 py-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">下载链接</label>
                  <Input
                    placeholder="请输入下载链接..."
                    value={newUrl}
                    onChange={(e) => setNewUrl(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleAddTask()}
                  />
                </div>
                <div className="text-xs text-muted-foreground space-y-1">
                  <p>支持的链接格式：</p>
                  <ul className="list-disc list-inside space-y-0.5">
                    <li>HTTP/HTTPS: https://example.com/file.zip</li>
                    <li>磁力链: magnet:?xt=urn:btih:...</li>
                    <li>电驴: ed2k://|file|...</li>
                  </ul>
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setAddDialogOpen(false)}>
                  取消
                </Button>
                <Button onClick={handleAddTask} disabled={!newUrl.trim() || adding}>
                  {adding && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                  添加
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* 统计卡片 */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">总任务数</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{count?.total || 0}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">下载中</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-500">{count?.downloading || 0}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">已完成</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-500">{count?.completed || 0}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">失败</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-500">{count?.failed || 0}</div>
          </CardContent>
        </Card>
      </div>

      {/* 配额信息 */}
      {quota && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">存储配额</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span>已使用 {quota.used_formatted}</span>
                <span>总配额 {quota.total_formatted}</span>
              </div>
              <Progress value={quotaPercent} className="h-2" />
              <div className="text-xs text-muted-foreground">
                剩余 {quota.remaining_formatted}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 任务列表 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Download className="h-5 w-5" />
            下载任务
          </CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : tasks.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              <Download className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>暂无下载任务</p>
              <p className="text-sm mt-1">点击右上角"添加任务"开始下载</p>
            </div>
          ) : (
            <div className="space-y-4">
              {tasks.map((task) => {
                const status = statusMap[task.status] || statusMap[3]
                const StatusIcon = status.icon

                return (
                  <div
                    key={task.info_hash}
                    className="flex items-center gap-4 p-4 rounded-lg border bg-card hover:bg-accent/50 transition-colors"
                  >
                    {/* 状态图标 */}
                    <div
                      className={cn(
                        "flex items-center justify-center w-10 h-10 rounded-lg shrink-0",
                        status.bgColor
                      )}
                    >
                      <StatusIcon className={cn("h-5 w-5", status.color)} />
                    </div>

                    {/* 任务信息 */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <p className="font-medium truncate">{task.name || "未命名任务"}</p>
                        <Badge variant="secondary" className={cn("text-xs", status.color, status.bgColor)}>
                          {status.label}
                        </Badge>
                      </div>

                      {/* 进度条 */}
                      {task.status === 1 && (
                        <div className="space-y-1 mb-2">
                          <Progress value={task.progress} className="h-1.5" />
                          <div className="flex justify-between text-xs text-muted-foreground">
                            <span>{task.progress.toFixed(1)}%</span>
                            <span>{task.speed_formatted}</span>
                          </div>
                        </div>
                      )}

                      {/* 文件大小和时间 */}
                      <div className="flex items-center gap-4 text-xs text-muted-foreground">
                        <span>{task.size_formatted}</span>
                        <span>创建于 {task.create_time_formatted}</span>
                        {task.url && (
                          <span className="truncate max-w-[200px]" title={task.url}>
                            {task.url}
                          </span>
                        )}
                      </div>
                    </div>

                    {/* 操作按钮 */}
                    <div className="flex items-center gap-1 shrink-0">
                      {task.status === -1 && (
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleRestartTask(task.info_hash)}
                          title="重新下载"
                        >
                          <RefreshCw className="h-4 w-4" />
                        </Button>
                      )}

                      {task.save_cid && (
                        <Button
                          variant="ghost"
                          size="icon"
                          asChild
                          title="打开文件夹"
                        >
                          <a href={`/dashboard/browser?cid=${task.save_cid}`}>
                            <FolderOpen className="h-4 w-4" />
                          </a>
                        </Button>
                      )}

                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="icon">
                            <MoreVertical className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          {task.url && (
                            <DropdownMenuItem onClick={() => navigator.clipboard.writeText(task.url!)}>
                              <Link className="h-4 w-4 mr-2" />
                              复制链接
                            </DropdownMenuItem>
                          )}
                          <DropdownMenuSeparator />
                          <DropdownMenuItem
                            className="text-red-600"
                            onClick={() => handleDeleteTask(task.info_hash)}
                          >
                            <Trash2 className="h-4 w-4 mr-2" />
                            删除任务
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </div>
                  </div>
                )
              })}
            </div>
          )}

          {/* 分页 */}
          {total > perPage && (
            <div className="flex items-center justify-center gap-2 mt-6">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
              >
                上一页
              </Button>
              <span className="text-sm text-muted-foreground">
                第 {page} 页 / 共 {Math.ceil(total / perPage)} 页
              </span>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((p) => p + 1)}
                disabled={page >= Math.ceil(total / perPage)}
              >
                下一页
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
