"use client"

import * as React from "react"
import { useState, useEffect } from "react"
import { Clock, FileText, Database, Activity, AlertCircle } from "lucide-react"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Badge } from "@/components/ui/badge"
import { api, StrmTask, TaskStatistics, TaskLog, StrmRecord } from "@/lib/api"
import { cn } from "@/lib/utils"

interface TaskDetailDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  task: StrmTask | null
}

export function TaskDetailDialog({ open, onOpenChange, task }: TaskDetailDialogProps) {
  const [statistics, setStatistics] = useState<TaskStatistics | null>(null)
  const [logs, setLogs] = useState<TaskLog[]>([])
  const [records, setRecords] = useState<StrmRecord[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (open && task) {
      loadTaskDetails()
    }
  }, [open, task])

  const loadTaskDetails = async () => {
    if (!task) return

    setLoading(true)
    try {
      const [statsResult, logsResult, recordsResult] = await Promise.all([
        api.getTaskStatistics(task.task_id),
        api.getTaskLogs(task.task_id, 50),
        api.getTaskRecords(task.task_id),
      ])

      setStatistics(statsResult.statistics)
      setLogs(logsResult.logs)
      setRecords(recordsResult.records)
    } catch (error) {
      console.error("Failed to load task details:", error)
    } finally {
      setLoading(false)
    }
  }

  const formatDate = (timestamp?: number) => {
    if (!timestamp) return "N/A"
    return new Date(timestamp * 1000).toLocaleString("zh-CN")
  }

  const formatDuration = (seconds?: number) => {
    if (!seconds) return "N/A"
    if (seconds < 60) return `${seconds.toFixed(1)}秒`
    if (seconds < 3600) return `${(seconds / 60).toFixed(1)}分钟`
    return `${(seconds / 3600).toFixed(1)}小时`
  }

  const formatFileSize = (bytes?: number) => {
    if (!bytes) return "N/A"
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`
  }

  if (!task) return null

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh]">
        <DialogHeader>
          <DialogTitle>{task.task_name}</DialogTitle>
        </DialogHeader>

        <Tabs defaultValue="overview" className="w-full">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="overview">概览</TabsTrigger>
            <TabsTrigger value="logs">日志</TabsTrigger>
            <TabsTrigger value="records">记录</TabsTrigger>
            <TabsTrigger value="config">配置</TabsTrigger>
          </TabsList>

          {/* 概览标签 */}
          <TabsContent value="overview" className="space-y-4">
            <ScrollArea className="h-[500px] pr-4">
              {statistics && (
                <div className="space-y-4">
                  {/* 统计卡片 */}
                  <div className="grid grid-cols-2 gap-4">
                    <Card>
                      <CardHeader className="pb-3">
                        <CardTitle className="text-sm font-medium">总运行次数</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="text-2xl font-bold">{statistics.total_runs}</div>
                      </CardContent>
                    </Card>

                    <Card>
                      <CardHeader className="pb-3">
                        <CardTitle className="text-sm font-medium">生成文件数</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="text-2xl font-bold">{statistics.total_files_generated}</div>
                      </CardContent>
                    </Card>

                    <Card>
                      <CardHeader className="pb-3">
                        <CardTitle className="text-sm font-medium">活跃记录数</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="text-2xl font-bold">{statistics.active_records}</div>
                      </CardContent>
                    </Card>

                    <Card>
                      <CardHeader className="pb-3">
                        <CardTitle className="text-sm font-medium">当前状态</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <Badge variant={statistics.status === "running" ? "default" : "secondary"}>
                          {statistics.status}
                        </Badge>
                      </CardContent>
                    </Card>
                  </div>

                  {/* 最近执行信息 */}
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-sm font-medium">最近执行</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-2">
                      <div className="flex justify-between text-sm">
                        <span className="text-muted-foreground">执行时间</span>
                        <span>{formatDate(statistics.last_run_time)}</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-muted-foreground">执行状态</span>
                        <Badge variant={statistics.last_run_status === "success" ? "default" : "destructive"}>
                          {statistics.last_run_status || "N/A"}
                        </Badge>
                      </div>
                      {statistics.last_run_message && (
                        <div className="text-sm">
                          <span className="text-muted-foreground">消息: </span>
                          <span>{statistics.last_run_message}</span>
                        </div>
                      )}
                    </CardContent>
                  </Card>

                  {/* 最近日志 */}
                  {statistics.last_log && (
                    <Card>
                      <CardHeader>
                        <CardTitle className="text-sm font-medium">最近日志</CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-2">
                        <div className="grid grid-cols-2 gap-2 text-sm">
                          <div>
                            <span className="text-muted-foreground">扫描: </span>
                            <span className="font-medium">{statistics.last_log.files_scanned}</span>
                          </div>
                          <div>
                            <span className="text-muted-foreground">新增: </span>
                            <span className="font-medium text-green-600">{statistics.last_log.files_added}</span>
                          </div>
                          <div>
                            <span className="text-muted-foreground">更新: </span>
                            <span className="font-medium text-blue-600">{statistics.last_log.files_updated}</span>
                          </div>
                          <div>
                            <span className="text-muted-foreground">删除: </span>
                            <span className="font-medium text-red-600">{statistics.last_log.files_deleted}</span>
                          </div>
                          <div>
                            <span className="text-muted-foreground">跳过: </span>
                            <span className="font-medium">{statistics.last_log.files_skipped}</span>
                          </div>
                          <div>
                            <span className="text-muted-foreground">耗时: </span>
                            <span className="font-medium">{formatDuration(statistics.last_log.duration)}</span>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  )}
                </div>
              )}
            </ScrollArea>
          </TabsContent>

          {/* 日志标签 */}
          <TabsContent value="logs" className="space-y-4">
            <ScrollArea className="h-[500px] pr-4">
              {logs.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                  <FileText className="h-12 w-12 mb-4" />
                  <p>暂无执行日志</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {logs.map((log) => (
                    <Card key={log.log_id} className={cn(log.status === "error" && "border-red-500")}>
                      <CardHeader className="pb-3">
                        <div className="flex items-center justify-between">
                          <CardTitle className="text-sm font-medium">
                            {formatDate(log.start_time)}
                          </CardTitle>
                          <Badge variant={log.status === "success" ? "default" : "destructive"}>
                            {log.status}
                          </Badge>
                        </div>
                        {log.message && (
                          <CardDescription className="text-xs">{log.message}</CardDescription>
                        )}
                      </CardHeader>
                      <CardContent>
                        <div className="grid grid-cols-3 gap-2 text-xs">
                          <div>
                            <span className="text-muted-foreground">扫描: </span>
                            <span className="font-medium">{log.files_scanned}</span>
                          </div>
                          <div>
                            <span className="text-muted-foreground">新增: </span>
                            <span className="font-medium text-green-600">+{log.files_added}</span>
                          </div>
                          <div>
                            <span className="text-muted-foreground">更新: </span>
                            <span className="font-medium text-blue-600">~{log.files_updated}</span>
                          </div>
                          <div>
                            <span className="text-muted-foreground">删除: </span>
                            <span className="font-medium text-red-600">-{log.files_deleted}</span>
                          </div>
                          <div>
                            <span className="text-muted-foreground">跳过: </span>
                            <span className="font-medium">{log.files_skipped}</span>
                          </div>
                          <div>
                            <span className="text-muted-foreground">耗时: </span>
                            <span className="font-medium">{formatDuration(log.duration)}</span>
                          </div>
                        </div>
                        {log.error_trace && (
                          <div className="mt-3 p-2 bg-red-50 dark:bg-red-950 rounded text-xs">
                            <pre className="whitespace-pre-wrap text-red-600 dark:text-red-400">
                              {log.error_trace}
                            </pre>
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  ))}
                </div>
              )}
            </ScrollArea>
          </TabsContent>

          {/* 记录标签 */}
          <TabsContent value="records" className="space-y-4">
            <ScrollArea className="h-[500px] pr-4">
              {records.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                  <Database className="h-12 w-12 mb-4" />
                  <p>暂无 STRM 记录</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {records.map((record) => (
                    <Card key={record.record_id}>
                      <CardHeader className="pb-3">
                        <CardTitle className="text-sm font-medium">{record.file_name}</CardTitle>
                        <CardDescription className="text-xs">
                          {record.file_path}
                        </CardDescription>
                      </CardHeader>
                      <CardContent className="space-y-2">
                        <div className="text-xs space-y-1">
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">文件大小</span>
                            <span>{formatFileSize(record.file_size)}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Pick Code</span>
                            <code className="text-xs bg-muted px-1 rounded">{record.pick_code}</code>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">STRM 路径</span>
                            <span className="truncate max-w-[300px]" title={record.strm_path}>
                              {record.strm_path}
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">创建时间</span>
                            <span>{formatDate(record.created_at)}</span>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              )}
            </ScrollArea>
          </TabsContent>

          {/* 配置标签 */}
          <TabsContent value="config" className="space-y-4">
            <ScrollArea className="h-[500px] pr-4">
              <div className="space-y-4">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm font-medium">基本配置</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">源目录 CID</span>
                      <code className="text-xs bg-muted px-1 rounded">{task.source_cid}</code>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">输出目录</span>
                      <span className="truncate max-w-[300px]" title={task.output_dir}>
                        {task.output_dir}
                      </span>
                    </div>
                    {task.base_url && (
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">基础 URL</span>
                        <span>{task.base_url}</span>
                      </div>
                    )}
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm font-medium">文件过滤</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">包含视频</span>
                      <Badge variant={task.include_video ? "default" : "secondary"}>
                        {task.include_video ? "是" : "否"}
                      </Badge>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">包含音频</span>
                      <Badge variant={task.include_audio ? "default" : "secondary"}>
                        {task.include_audio ? "是" : "否"}
                      </Badge>
                    </div>
                    {task.custom_extensions && task.custom_extensions.length > 0 && (
                      <div>
                        <span className="text-muted-foreground">自定义扩展名</span>
                        <div className="flex flex-wrap gap-1 mt-1">
                          {task.custom_extensions.map((ext, i) => (
                            <Badge key={i} variant="outline" className="text-xs">
                              {ext}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    )}
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm font-medium">调度配置</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">定时调度</span>
                      <Badge variant={task.schedule_enabled ? "default" : "secondary"}>
                        {task.schedule_enabled ? "启用" : "禁用"}
                      </Badge>
                    </div>
                    {task.schedule_enabled && (
                      <>
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">调度类型</span>
                          <span>{task.schedule_type === "interval" ? "间隔执行" : "定时执行"}</span>
                        </div>
                        {task.schedule_config && (
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">配置</span>
                            <span>
                              {task.schedule_type === "interval"
                                ? `每 ${task.schedule_config.interval} ${task.schedule_config.unit}`
                                : `每天 ${task.schedule_config.time}`}
                            </span>
                          </div>
                        )}
                      </>
                    )}
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm font-medium">监听配置</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">文件监听</span>
                      <Badge variant={task.watch_enabled ? "default" : "secondary"}>
                        {task.watch_enabled ? "启用" : "禁用"}
                      </Badge>
                    </div>
                    {task.watch_enabled && (
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">检查间隔</span>
                        <span>{task.watch_interval} 秒</span>
                      </div>
                    )}
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm font-medium">同步选项</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">删除孤立文件</span>
                      <Badge variant={task.delete_orphans ? "default" : "secondary"}>
                        {task.delete_orphans ? "是" : "否"}
                      </Badge>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">保持目录结构</span>
                      <Badge variant={task.preserve_structure ? "default" : "secondary"}>
                        {task.preserve_structure ? "是" : "否"}
                      </Badge>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </ScrollArea>
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  )
}
