"use client"

import * as React from "react"
import { useState, useEffect } from "react"
import { motion, AnimatePresence } from "framer-motion"
import {
  Clock,
  FileText,
  Database,
  Activity,
  AlertCircle,
  Play,
  Pause,
  CheckCircle,
  XCircle,
  Folder,
  HardDrive,
  Settings,
  RefreshCw,
  FileVideo,
  BarChart3,
  Calendar,
  Timer,
  ChevronRight,
} from "lucide-react"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { cn } from "@/lib/utils"
import { api, StrmTask, TaskStatistics, TaskLog, StrmRecord } from "@/lib/api"

interface TaskDetailDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  task: StrmTask | null
}

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.05 }
  }
}

const itemVariants = {
  hidden: { opacity: 0, y: 10 },
  visible: { opacity: 1, y: 0 }
}

function StatCard({ 
  title, 
  value, 
  icon: Icon, 
  color = "blue",
  subtitle,
  trend,
  delay = 0 
}: { 
  title: string
  value: string | number
  icon: React.ElementType
  color?: "blue" | "green" | "amber" | "purple" | "red"
  subtitle?: string
  trend?: { value: number; positive: boolean }
  delay?: number
}) {
  const colorClasses = {
    blue: "from-blue-500/20 to-blue-600/10 text-blue-600 dark:text-blue-400",
    green: "from-green-500/20 to-green-600/10 text-green-600 dark:text-green-400",
    amber: "from-amber-500/20 to-amber-600/10 text-amber-600 dark:text-amber-400",
    purple: "from-purple-500/20 to-purple-600/10 text-purple-600 dark:text-purple-400",
    red: "from-red-500/20 to-red-600/10 text-red-600 dark:text-red-400",
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay }}
    >
      <Card className="overflow-hidden border-0 shadow-lg bg-gradient-to-br from-card to-card/50">
        <CardContent className="p-5">
          <div className="flex items-start justify-between">
            <div className="space-y-1">
              <p className="text-sm text-muted-foreground">{title}</p>
              <p className="text-3xl font-bold tracking-tight">{value}</p>
              {subtitle && <p className="text-xs text-muted-foreground">{subtitle}</p>}
              {trend && (
                <div className={cn("flex items-center gap-1 text-xs", trend.positive ? "text-green-600" : "text-red-600")}>
                  {trend.positive ? "↑" : "↓"} {Math.abs(trend.value)}%
                </div>
              )}
            </div>
            <div className={cn("p-3 rounded-xl bg-gradient-to-br", colorClasses[color])}>
              <Icon className="h-5 w-5" />
            </div>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  )
}

function StatusBadge({ status }: { status: string }) {
  const configs: Record<string, { icon: React.ElementType; color: string; label: string }> = {
    running: { icon: Play, color: "bg-blue-500", label: "运行中" },
    paused: { icon: Pause, color: "bg-amber-500", label: "已暂停" },
    success: { icon: CheckCircle, color: "bg-green-500", label: "成功" },
    error: { icon: XCircle, color: "bg-red-500", label: "错误" },
    idle: { icon: Activity, color: "bg-gray-500", label: "空闲" },
  }
  
  const config = configs[status] || configs.idle
  const Icon = config.icon
  
  return (
    <Badge className={cn("gap-1.5 px-2.5 py-1 text-white border-0", config.color)}>
      <Icon className="h-3.5 w-3.5" />
      {config.label}
    </Badge>
  )
}

function LogCard({ log, index }: { log: TaskLog; index: number }) {
  const isError = log.status === "error"
  const isSuccess = log.status === "success"
  
  return (
    <motion.div
      variants={itemVariants}
      initial="hidden"
      animate="visible"
      transition={{ delay: index * 0.05 }}
    >
      <Card className={cn(
        "overflow-hidden border-0 shadow-md transition-all duration-200 hover:shadow-lg",
        isError ? "bg-red-50/50 dark:bg-red-950/20" : "bg-card/50"
      )}>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className={cn(
                "p-2 rounded-lg",
                isSuccess ? "bg-green-100 dark:bg-green-900/30" : isError ? "bg-red-100 dark:bg-red-900/30" : "bg-blue-100 dark:bg-blue-900/30"
              )}>
                {isSuccess ? (
                  <CheckCircle className="h-4 w-4 text-green-600 dark:text-green-400" />
                ) : isError ? (
                  <XCircle className="h-4 w-4 text-red-600 dark:text-red-400" />
                ) : (
                  <Clock className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                )}
              </div>
              <div>
                <CardTitle className="text-sm font-medium">
                  {log.start_time ? new Date(log.start_time).toLocaleString("zh-CN") : "N/A"}
                </CardTitle>
                {log.message && (
                  <CardDescription className="text-xs mt-0.5">{log.message}</CardDescription>
                )}
              </div>
            </div>
            <StatusBadge status={log.status} />
          </div>
        </CardHeader>
        <CardContent className="pt-0">
          <div className="grid grid-cols-3 gap-3">
            <StatItem label="扫描" value={log.files_scanned} />
            <StatItem label="新增" value={log.files_added} color="green" prefix="+" />
            <StatItem label="更新" value={log.files_updated} color="blue" prefix="~" />
            <StatItem label="删除" value={log.files_deleted} color="red" prefix="-" />
            <StatItem label="跳过" value={log.files_skipped} />
            <StatItem label="耗时" value={formatDuration(log.duration)} />
          </div>
          {log.error_trace && (
            <div className="mt-3 p-3 bg-red-100/50 dark:bg-red-900/30 rounded-lg border border-red-200 dark:border-red-800">
              <pre className="text-xs text-red-700 dark:text-red-300 whitespace-pre-wrap">
                {log.error_trace}
              </pre>
            </div>
          )}
        </CardContent>
      </Card>
    </motion.div>
  )
}

function StatItem({ label, value, color, prefix = "" }: { label: string; value: number | string; color?: string; prefix?: string }) {
  const colorClasses: Record<string, string> = {
    green: "text-green-600 dark:text-green-400",
    blue: "text-blue-600 dark:text-blue-400",
    red: "text-red-600 dark:text-red-400",
  }
  
  return (
    <div className="text-center p-2 rounded-lg bg-muted/50">
      <p className="text-xs text-muted-foreground mb-1">{label}</p>
      <p className={cn("text-sm font-semibold", color && colorClasses[color])}>
        {prefix}{value}
      </p>
    </div>
  )
}

function EmptyState({ icon: Icon, title, description }: { icon: React.ElementType; title: string; description: string }) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="flex flex-col items-center justify-center py-16 text-muted-foreground"
    >
      <div className="p-4 rounded-full bg-muted/50 mb-4">
        <Icon className="h-8 w-8" />
      </div>
      <p className="font-medium text-foreground">{title}</p>
      <p className="text-sm mt-1">{description}</p>
    </motion.div>
  )
}

function LoadingState() {
  return (
    <div className="flex flex-col items-center justify-center py-16">
      <motion.div
        animate={{ rotate: 360 }}
        transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
        className="relative"
      >
        <div className="absolute inset-0 bg-primary/20 rounded-full animate-ping" />
        <RefreshCw className="h-8 w-8 text-primary relative" />
      </motion.div>
      <p className="text-sm text-muted-foreground mt-4">正在加载...</p>
    </div>
  )
}

function formatDuration(seconds?: number) {
  if (!seconds) return "N/A"
  if (seconds < 60) return `${seconds.toFixed(1)}秒`
  if (seconds < 3600) return `${(seconds / 60).toFixed(1)}分钟`
  return `${(seconds / 3600).toFixed(1)}小时`
}

function formatFileSize(bytes?: number) {
  if (!bytes) return "N/A"
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`
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
        api.getTaskStatistics(task.id),
        api.getTaskLogs(task.id, 50),
        api.getTaskRecords(task.id),
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

  const formatDate = (value?: string | number) => {
    if (!value) return "N/A"
    // 处理 ISO 字符串格式或时间戳
    const date = typeof value === "string" ? new Date(value) : new Date(value * 1000)
    return date.toLocaleString("zh-CN")
  }

  if (!task) return null

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-hidden rounded-2xl border-0 shadow-2xl bg-white/95 dark:bg-gray-900/95 backdrop-blur-xl">
        {/* 顶部装饰条 */}
        <div className="absolute top-0 left-0 right-0 h-1.5 bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500" />
        
        <DialogHeader className="pt-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 text-white shadow-lg">
                <BarChart3 className="h-5 w-5" />
              </div>
              <div>
                <DialogTitle className="text-xl font-semibold tracking-tight">{task.name}</DialogTitle>
                <div className="flex items-center gap-2 mt-1">
                  <Badge variant="outline" className="text-xs">
                    <HardDrive className="h-3 w-3 mr-1" />
                    {task.drive_id}
                  </Badge>
                  {statistics && <StatusBadge status={statistics.status} />}
                </div>
              </div>
            </div>
          </div>
        </DialogHeader>

        <Tabs defaultValue="overview" className="w-full">
          <TabsList className="grid w-full grid-cols-4 bg-muted/50 p-1 rounded-xl">
            <TabsTrigger value="overview" className="rounded-lg data-[state=active]:bg-white data-[state=active]:shadow-sm">
              <Activity className="h-4 w-4 mr-2" />
              概览
            </TabsTrigger>
            <TabsTrigger value="logs" className="rounded-lg data-[state=active]:bg-white data-[state=active]:shadow-sm">
              <FileText className="h-4 w-4 mr-2" />
              日志
            </TabsTrigger>
            <TabsTrigger value="records" className="rounded-lg data-[state=active]:bg-white data-[state=active]:shadow-sm">
              <Database className="h-4 w-4 mr-2" />
              记录
            </TabsTrigger>
            <TabsTrigger value="config" className="rounded-lg data-[state=active]:bg-white data-[state=active]:shadow-sm">
              <Settings className="h-4 w-4 mr-2" />
              配置
            </TabsTrigger>
          </TabsList>

          {/* 概览标签 */}
          <TabsContent value="overview" className="mt-4">
            <ScrollArea className="h-[500px] pr-4">
              {loading ? (
                <LoadingState />
              ) : statistics ? (
                <motion.div
                  variants={containerVariants}
                  initial="hidden"
                  animate="visible"
                  className="space-y-4"
                >
                  {/* 统计卡片 */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <StatCard
                      title="总运行次数"
                      value={statistics.total_runs}
                      icon={RefreshCw}
                      color="blue"
                      delay={0}
                    />
                    <StatCard
                      title="生成文件数"
                      value={statistics.total_files_generated}
                      icon={FileVideo}
                      color="green"
                      delay={0.1}
                    />
                    <StatCard
                      title="活跃记录数"
                      value={statistics.active_records}
                      icon={Database}
                      color="purple"
                      delay={0.2}
                    />
                    <StatCard
                      title="当前状态"
                      value={statistics.status === "running" ? "运行中" : "空闲"}
                      icon={Activity}
                      color={statistics.status === "running" ? "amber" : "blue"}
                      delay={0.3}
                    />
                  </div>

                  {/* 最近执行信息 */}
                  <motion.div variants={itemVariants}>
                    <Card className="border-0 shadow-lg overflow-hidden">
                      <div className="h-1 bg-gradient-to-r from-indigo-500 to-purple-500" />
                      <CardHeader>
                        <div className="flex items-center gap-2">
                          <Calendar className="h-4 w-4 text-muted-foreground" />
                          <CardTitle className="text-sm font-medium">最近执行</CardTitle>
                        </div>
                      </CardHeader>
                      <CardContent className="space-y-3">
                        <div className="flex justify-between items-center p-3 rounded-lg bg-muted/50">
                          <span className="text-sm text-muted-foreground">执行时间</span>
                          <span className="text-sm font-medium">{formatDate(statistics.last_run_time)}</span>
                        </div>
                        <div className="flex justify-between items-center p-3 rounded-lg bg-muted/50">
                          <span className="text-sm text-muted-foreground">执行状态</span>
                          <StatusBadge status={statistics.last_run_status || "idle"} />
                        </div>
                        {statistics.last_run_message && (
                          <div className="p-3 rounded-lg bg-muted/50">
                            <span className="text-sm text-muted-foreground">消息: </span>
                            <span className="text-sm">{statistics.last_run_message}</span>
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  </motion.div>

                  {/* 最近日志 */}
                  {statistics.last_log && (
                    <motion.div variants={itemVariants}>
                      <Card className="border-0 shadow-lg overflow-hidden">
                        <div className="h-1 bg-gradient-to-r from-green-500 to-emerald-500" />
                        <CardHeader>
                          <div className="flex items-center gap-2">
                            <BarChart3 className="h-4 w-4 text-muted-foreground" />
                            <CardTitle className="text-sm font-medium">最近日志统计</CardTitle>
                          </div>
                        </CardHeader>
                        <CardContent>
                          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                            <div className="p-3 rounded-lg bg-blue-50 dark:bg-blue-950/30 text-center">
                              <p className="text-2xl font-bold text-blue-600 dark:text-blue-400">{statistics.last_log.files_scanned}</p>
                              <p className="text-xs text-muted-foreground">扫描文件</p>
                            </div>
                            <div className="p-3 rounded-lg bg-green-50 dark:bg-green-950/30 text-center">
                              <p className="text-2xl font-bold text-green-600 dark:text-green-400">+{statistics.last_log.files_added}</p>
                              <p className="text-xs text-muted-foreground">新增</p>
                            </div>
                            <div className="p-3 rounded-lg bg-purple-50 dark:bg-purple-950/30 text-center">
                              <p className="text-2xl font-bold text-purple-600 dark:text-purple-400">~{statistics.last_log.files_updated}</p>
                              <p className="text-xs text-muted-foreground">更新</p>
                            </div>
                            <div className="p-3 rounded-lg bg-red-50 dark:bg-red-950/30 text-center">
                              <p className="text-2xl font-bold text-red-600 dark:text-red-400">-{statistics.last_log.files_deleted}</p>
                              <p className="text-xs text-muted-foreground">删除</p>
                            </div>
                            <div className="p-3 rounded-lg bg-gray-50 dark:bg-gray-950/30 text-center">
                              <p className="text-2xl font-bold">{statistics.last_log.files_skipped}</p>
                              <p className="text-xs text-muted-foreground">跳过</p>
                            </div>
                            <div className="p-3 rounded-lg bg-amber-50 dark:bg-amber-950/30 text-center">
                              <p className="text-2xl font-bold text-amber-600 dark:text-amber-400">{formatDuration(statistics.last_log.duration)}</p>
                              <p className="text-xs text-muted-foreground">耗时</p>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    </motion.div>
                  )}
                </motion.div>
              ) : (
                <EmptyState icon={BarChart3} title="暂无统计数据" description="任务尚未执行或统计信息不可用" />
              )}
            </ScrollArea>
          </TabsContent>

          {/* 日志标签 */}
          <TabsContent value="logs" className="mt-4">
            <ScrollArea className="h-[500px] pr-4">
              {loading ? (
                <LoadingState />
              ) : logs.length === 0 ? (
                <EmptyState icon={FileText} title="暂无执行日志" description="任务执行后将在这里显示日志记录" />
              ) : (
                <div className="space-y-3">
                  <AnimatePresence>
                    {logs.map((log, index) => (
                      <LogCard key={log.id} log={log} index={index} />
                    ))}
                  </AnimatePresence>
                </div>
              )}
            </ScrollArea>
          </TabsContent>

          {/* 记录标签 */}
          <TabsContent value="records" className="mt-4">
            <ScrollArea className="h-[500px] pr-4">
              {loading ? (
                <LoadingState />
              ) : records.length === 0 ? (
                <EmptyState icon={Database} title="暂无 STRM 记录" description="同步文件后将在这里显示记录" />
              ) : (
                <div className="space-y-3">
                  <AnimatePresence>
                    {records.map((record, index) => (
                      <motion.div
                        key={record.id}
                        variants={itemVariants}
                        initial="hidden"
                        animate="visible"
                        transition={{ delay: index * 0.03 }}
                      >
                        <Card className="overflow-hidden border-0 shadow-md hover:shadow-lg transition-all duration-200">
                          <CardHeader className="pb-3">
                            <div className="flex items-center gap-3">
                              <div className="p-2 rounded-lg bg-indigo-100 dark:bg-indigo-900/30">
                                <FileVideo className="h-4 w-4 text-indigo-600 dark:text-indigo-400" />
                              </div>
                              <div className="flex-1 min-w-0">
                                <CardTitle className="text-sm font-medium truncate">{record.file_name}</CardTitle>
                                <CardDescription className="text-xs truncate">
                                  <Folder className="h-3 w-3 inline mr-1" />
                                  {record.file_path}
                                </CardDescription>
                              </div>
                            </div>
                          </CardHeader>
                          <CardContent className="pt-0">
                            <div className="grid grid-cols-2 gap-3 text-xs">
                              <div className="p-2 rounded-lg bg-muted/50">
                                <span className="text-muted-foreground">文件大小</span>
                                <p className="font-medium">{formatFileSize(record.file_size)}</p>
                              </div>
                              <div className="p-2 rounded-lg bg-muted/50">
                                <span className="text-muted-foreground">Pick Code</span>
                                <code className="font-medium bg-muted px-1.5 py-0.5 rounded">{record.pick_code}</code>
                              </div>
                              <div className="col-span-2 p-2 rounded-lg bg-muted/50">
                                <span className="text-muted-foreground">STRM 路径</span>
                                <p className="font-medium truncate" title={record.strm_path}>
                                  <ChevronRight className="h-3 w-3 inline mr-1" />
                                  {record.strm_path}
                                </p>
                              </div>
                              <div className="col-span-2 p-2 rounded-lg bg-muted/50">
                                <span className="text-muted-foreground">创建时间</span>
                                <p className="font-medium">{formatDate(record.created_at)}</p>
                              </div>
                            </div>
                          </CardContent>
                        </Card>
                      </motion.div>
                    ))}
                  </AnimatePresence>
                </div>
              )}
            </ScrollArea>
          </TabsContent>

          {/* 配置标签 */}
          <TabsContent value="config" className="mt-4">
            <ScrollArea className="h-[500px] pr-4">
              <motion.div
                variants={containerVariants}
                initial="hidden"
                animate="visible"
                className="space-y-4"
              >
                <motion.div variants={itemVariants}>
                  <Card className="border-0 shadow-lg overflow-hidden">
                    <div className="h-1 bg-gradient-to-r from-blue-500 to-cyan-500" />
                    <CardHeader>
                      <CardTitle className="text-sm font-medium flex items-center gap-2">
                        <Settings className="h-4 w-4" />
                        基本配置
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      <ConfigItem label="源目录 CID" value={task.source_cid} code />
                      <Separator />
                      <ConfigItem label="输出目录" value={task.output_dir} />
                      {task.base_url && (
                        <>
                          <Separator />
                          <ConfigItem label="基础 URL" value={task.base_url} />
                        </>
                      )}
                    </CardContent>
                  </Card>
                </motion.div>

                <motion.div variants={itemVariants}>
                  <Card className="border-0 shadow-lg overflow-hidden">
                    <div className="h-1 bg-gradient-to-r from-green-500 to-emerald-500" />
                    <CardHeader>
                      <CardTitle className="text-sm font-medium flex items-center gap-2">
                        <FileVideo className="h-4 w-4" />
                        文件过滤
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-muted-foreground">包含视频</span>
                        <Badge variant={task.include_video ? "default" : "secondary"}>
                          {task.include_video ? "是" : "否"}
                        </Badge>
                      </div>
                      <Separator />
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-muted-foreground">包含音频</span>
                        <Badge variant={task.include_audio ? "default" : "secondary"}>
                          {task.include_audio ? "是" : "否"}
                        </Badge>
                      </div>
                      {task.custom_extensions && task.custom_extensions.length > 0 && (
                        <>
                          <Separator />
                          <div>
                            <span className="text-sm text-muted-foreground">自定义扩展名</span>
                            <div className="flex flex-wrap gap-1 mt-2">
                              {task.custom_extensions.map((ext, i) => (
                                <Badge key={i} variant="outline" className="text-xs">
                                  {ext}
                                </Badge>
                              ))}
                            </div>
                          </div>
                        </>
                      )}
                    </CardContent>
                  </Card>
                </motion.div>

                <motion.div variants={itemVariants}>
                  <Card className="border-0 shadow-lg overflow-hidden">
                    <div className="h-1 bg-gradient-to-r from-amber-500 to-orange-500" />
                    <CardHeader>
                      <CardTitle className="text-sm font-medium flex items-center gap-2">
                        <Clock className="h-4 w-4" />
                        调度配置
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-muted-foreground">定时调度</span>
                        <Badge variant={task.schedule_enabled ? "default" : "secondary"}>
                          {task.schedule_enabled ? "启用" : "禁用"}
                        </Badge>
                      </div>
                      {task.schedule_enabled && (
                        <>
                          <Separator />
                          <ConfigItem 
                            label="调度类型" 
                            value={task.schedule_type === "interval" ? "间隔执行" : "定时执行"} 
                          />
                          {task.schedule_config && (
                            <>
                              <Separator />
                              <ConfigItem 
                                label="配置" 
                                value={
                                  task.schedule_type === "interval"
                                    ? `每 ${task.schedule_config.interval} ${task.schedule_config.unit}`
                                    : `每天 ${task.schedule_config.time}`
                                } 
                              />
                            </>
                          )}
                        </>
                      )}
                    </CardContent>
                  </Card>
                </motion.div>

                <motion.div variants={itemVariants}>
                  <Card className="border-0 shadow-lg overflow-hidden">
                    <div className="h-1 bg-gradient-to-r from-purple-500 to-pink-500" />
                    <CardHeader>
                      <CardTitle className="text-sm font-medium flex items-center gap-2">
                        <Activity className="h-4 w-4" />
                        监听配置
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-muted-foreground">文件监听</span>
                        <Badge variant={task.watch_enabled ? "default" : "secondary"}>
                          {task.watch_enabled ? "启用" : "禁用"}
                        </Badge>
                      </div>
                      {task.watch_enabled && (
                        <>
                          <Separator />
                          <ConfigItem label="检查间隔" value={`${task.watch_interval} 秒`} />
                        </>
                      )}
                    </CardContent>
                  </Card>
                </motion.div>

                <motion.div variants={itemVariants}>
                  <Card className="border-0 shadow-lg overflow-hidden">
                    <div className="h-1 bg-gradient-to-r from-indigo-500 to-purple-500" />
                    <CardHeader>
                      <CardTitle className="text-sm font-medium flex items-center gap-2">
                        <Settings className="h-4 w-4" />
                        同步选项
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-muted-foreground">删除孤立文件</span>
                        <Badge variant={task.delete_orphans ? "default" : "secondary"}>
                          {task.delete_orphans ? "是" : "否"}
                        </Badge>
                      </div>
                      <Separator />
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-muted-foreground">保持目录结构</span>
                        <Badge variant={task.preserve_structure ? "default" : "secondary"}>
                          {task.preserve_structure ? "是" : "否"}
                        </Badge>
                      </div>
                      <Separator />
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-muted-foreground">覆盖已存在的 STRM 文件</span>
                        <Badge variant={task.overwrite_strm ? "default" : "secondary"}>
                          {task.overwrite_strm ? "是" : "否"}
                        </Badge>
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>
              </motion.div>
            </ScrollArea>
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  )
}

function ConfigItem({ label, value, code }: { label: string; value: string; code?: boolean }) {
  return (
    <div className="flex justify-between items-center">
      <span className="text-sm text-muted-foreground">{label}</span>
      {code ? (
        <code className="text-xs bg-muted px-2 py-1 rounded">{value}</code>
      ) : (
        <span className="text-sm font-medium truncate max-w-[200px]" title={value}>
          {value}
        </span>
      )}
    </div>
  )
}
