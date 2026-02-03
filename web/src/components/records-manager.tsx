"use client"

import * as React from "react"
import { useState, useEffect, useCallback } from "react"
import { motion, AnimatePresence } from "framer-motion"
import {
  Search,
  Trash2,
  FileText,
  FolderOpen,
  RefreshCw,
  AlertCircle,
  Check,
  X,
  ChevronDown,
  ChevronUp,
  HardDrive,
  Filter,
  FileX,
  CheckSquare,
  Square,
  ExternalLink,
  Loader2,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { cn } from "@/lib/utils"
import { api, StrmTask, StrmRecord, Drive } from "@/lib/api"

interface RecordsManagerProps {
  tasks: StrmTask[]
  drives: Drive[]
}

export function RecordsManager({ tasks, drives }: RecordsManagerProps) {
  const [selectedTaskId, setSelectedTaskId] = useState<string>("")
  const [records, setRecords] = useState<StrmRecord[]>([])
  const [filteredRecords, setFilteredRecords] = useState<StrmRecord[]>([])
  const [loading, setLoading] = useState(false)
  const [searchQuery, setSearchQuery] = useState("")
  const [statusFilter, setStatusFilter] = useState<string>("all")
  const [selectedRecords, setSelectedRecords] = useState<Set<string>>(new Set())
  const [showDeleteDialog, setShowDeleteDialog] = useState(false)
  const [deleteMode, setDeleteMode] = useState<"single" | "batch">("single")
  const [deleteTargetId, setDeleteTargetId] = useState<string>("")
  const [deleteLoading, setDeleteLoading] = useState(false)
  const [deleteWithFile, setDeleteWithFile] = useState(true)
  const [stats, setStats] = useState({ total: 0, active: 0, deleted: 0 })

  // 加载记录
  const loadRecords = useCallback(async () => {
    if (!selectedTaskId) {
      setRecords([])
      return
    }

    setLoading(true)
    try {
      const result = await api.getTaskRecords(selectedTaskId, undefined, undefined, 10000)
      if (result.success) {
        setRecords(result.records)
        setStats({
          total: result.records.length,
          active: result.records.filter(r => r.status === "active").length,
          deleted: result.records.filter(r => r.status === "deleted").length,
        })
      }
    } catch (error) {
      console.error("Failed to load records:", error)
    } finally {
      setLoading(false)
    }
  }, [selectedTaskId])

  // 初始加载
  useEffect(() => {
    loadRecords()
  }, [loadRecords])

  // 筛选记录
  useEffect(() => {
    let filtered = records

    // 状态筛选
    if (statusFilter !== "all") {
      filtered = filtered.filter(r => r.status === statusFilter)
    }

    // 搜索筛选
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase()
      filtered = filtered.filter(r =>
        r.file_name.toLowerCase().includes(query) ||
        r.file_path?.toLowerCase().includes(query) ||
        r.strm_path.toLowerCase().includes(query)
      )
    }

    setFilteredRecords(filtered)
  }, [records, searchQuery, statusFilter])

  // 选择/取消选择单个
  const toggleSelect = (recordId: string) => {
    const newSelected = new Set(selectedRecords)
    if (newSelected.has(recordId)) {
      newSelected.delete(recordId)
    } else {
      newSelected.add(recordId)
    }
    setSelectedRecords(newSelected)
  }

  // 全选/取消全选
  const toggleSelectAll = () => {
    if (selectedRecords.size === filteredRecords.length) {
      setSelectedRecords(new Set())
    } else {
      setSelectedRecords(new Set(filteredRecords.map(r => r.id)))
    }
  }

  // 打开删除对话框
  const openDeleteDialog = (mode: "single" | "batch", recordId?: string) => {
    setDeleteMode(mode)
    if (recordId) setDeleteTargetId(recordId)
    setDeleteWithFile(true)
    setShowDeleteDialog(true)
  }

  // 执行删除
  const handleDelete = async () => {
    if (!selectedTaskId) return

    setDeleteLoading(true)
    try {
      if (deleteMode === "single") {
        await api.deleteTaskRecord(selectedTaskId, deleteTargetId, deleteWithFile)
      } else {
        const recordIds = Array.from(selectedRecords)
        await api.batchDeleteTaskRecords(selectedTaskId, recordIds, deleteWithFile)
      }

      // 刷新列表
      await loadRecords()
      setSelectedRecords(new Set())
      setShowDeleteDialog(false)
    } catch (error) {
      console.error("Failed to delete records:", error)
      alert("删除失败，请重试")
    } finally {
      setDeleteLoading(false)
    }
  }

  // 格式化文件大小
  const formatSize = (bytes?: number) => {
    if (!bytes) return "-"
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    if (bytes < 1024 * 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`
    return `${(bytes / 1024 / 1024 / 1024).toFixed(2)} GB`
  }

  // 格式化时间
  const formatTime = (timestamp?: number) => {
    if (!timestamp) return "-"
    return new Date(timestamp * 1000).toLocaleString("zh-CN")
  }

  // 获取任务名称
  const getTaskName = (taskId: string) => {
    const task = tasks.find(t => t.task_id === taskId)
    return task?.task_name || taskId
  }

  const selectedTask = tasks.find(t => t.task_id === selectedTaskId)

  return (
    <div className="space-y-6">
      {/* 顶部统计卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="bg-gradient-to-br from-blue-500/10 to-cyan-500/10 border-blue-200/50">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">总记录数</p>
                <p className="text-2xl font-bold">{stats.total}</p>
              </div>
              <div className="p-3 rounded-lg bg-blue-500/20">
                <FileText className="h-5 w-5 text-blue-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-green-500/10 to-emerald-500/10 border-green-200/50">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">活跃记录</p>
                <p className="text-2xl font-bold">{stats.active}</p>
              </div>
              <div className="p-3 rounded-lg bg-green-500/20">
                <Check className="h-5 w-5 text-green-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-red-500/10 to-rose-500/10 border-red-200/50">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">已删除</p>
                <p className="text-2xl font-bold">{stats.deleted}</p>
              </div>
              <div className="p-3 rounded-lg bg-red-500/20">
                <FileX className="h-5 w-5 text-red-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-purple-500/10 to-violet-500/10 border-purple-200/50">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">选中数量</p>
                <p className="text-2xl font-bold">{selectedRecords.size}</p>
              </div>
              <div className="p-3 rounded-lg bg-purple-500/20">
                <CheckSquare className="h-5 w-5 text-purple-600" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 工具栏 */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-col md:flex-row gap-4">
            {/* 任务选择 */}
            <div className="flex-1 min-w-[200px]">
              <Select value={selectedTaskId} onValueChange={setSelectedTaskId}>
                <SelectTrigger className="w-full">
                  <HardDrive className="h-4 w-4 mr-2 text-muted-foreground" />
                  <SelectValue placeholder="选择任务" />
                </SelectTrigger>
                <SelectContent>
                  {tasks.map(task => (
                    <SelectItem key={task.task_id} value={task.task_id}>
                      {task.task_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* 搜索 */}
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="搜索文件名、路径..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>

            {/* 状态筛选 */}
            <div className="w-[140px]">
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger>
                  <Filter className="h-4 w-4 mr-2 text-muted-foreground" />
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部状态</SelectItem>
                  <SelectItem value="active">活跃</SelectItem>
                  <SelectItem value="deleted">已删除</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* 刷新 */}
            <Button
              variant="outline"
              onClick={loadRecords}
              disabled={loading || !selectedTaskId}
            >
              <RefreshCw className={cn("h-4 w-4 mr-2", loading && "animate-spin")} />
              刷新
            </Button>

            {/* 批量删除 */}
            {selectedRecords.size > 0 && (
              <Button
                variant="destructive"
                onClick={() => openDeleteDialog("batch")}
              >
                <Trash2 className="h-4 w-4 mr-2" />
                删除选中 ({selectedRecords.size})
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* 记录列表 */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg flex items-center gap-2">
              <FolderOpen className="h-5 w-5 text-primary" />
              STRM 记录列表
              {selectedTask && (
                <Badge variant="secondary">{selectedTask.task_name}</Badge>
              )}
            </CardTitle>
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <span>共 {filteredRecords.length} 条</span>
              {filteredRecords.length !== records.length && (
                <span className="text-xs">(已筛选)</span>
              )}
            </div>
          </div>
        </CardHeader>

        <CardContent className="p-0">
          {!selectedTaskId ? (
            <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
              <HardDrive className="h-12 w-12 mb-4 opacity-50" />
              <p className="text-lg font-medium">请先选择一个任务</p>
              <p className="text-sm mt-1">从上方下拉框中选择要查看的任务</p>
            </div>
          ) : loading ? (
            <div className="flex flex-col items-center justify-center py-16">
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
              >
                <Loader2 className="h-8 w-8 text-primary" />
              </motion.div>
              <p className="text-sm text-muted-foreground mt-4">加载中...</p>
            </div>
          ) : filteredRecords.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
              <FileText className="h-12 w-12 mb-4 opacity-50" />
              <p className="text-lg font-medium">没有找到记录</p>
              <p className="text-sm mt-1">
                {searchQuery || statusFilter !== "all"
                  ? "尝试调整筛选条件"
                  : "该任务暂无生成的 STRM 记录"}
              </p>
            </div>
          ) : (
            <div className="border-t">
              {/* 列表头部 */}
              <div className="flex items-center gap-3 px-4 py-3 bg-muted/50 border-b">
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-6 w-6"
                  onClick={toggleSelectAll}
                >
                  {selectedRecords.size === filteredRecords.length && filteredRecords.length > 0 ? (
                    <CheckSquare className="h-4 w-4" />
                  ) : (
                    <Square className="h-4 w-4" />
                  )}
                </Button>
                <div className="flex-1 text-sm font-medium">文件名称</div>
                <div className="w-24 text-sm font-medium text-center">大小</div>
                <div className="w-24 text-sm font-medium text-center">状态</div>
                <div className="w-32 text-sm font-medium text-center">创建时间</div>
                <div className="w-20 text-sm font-medium text-center">操作</div>
              </div>

              <ScrollArea className="h-[500px]">
                <AnimatePresence>
                  {filteredRecords.map((record, index) => (
                    <motion.div
                      key={record.id}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, x: -10 }}
                      transition={{ delay: index * 0.02 }}
                      className={cn(
                        "flex items-center gap-3 px-4 py-3 border-b hover:bg-muted/50 transition-colors",
                        selectedRecords.has(record.id) && "bg-primary/5"
                      )}
                    >
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-6 w-6 shrink-0"
                        onClick={() => toggleSelect(record.id)}
                      >
                        {selectedRecords.has(record.id) ? (
                          <CheckSquare className="h-4 w-4 text-primary" />
                        ) : (
                          <Square className="h-4 w-4" />
                        )}
                      </Button>

                      {/* 文件信息 */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <FileText className="h-4 w-4 text-muted-foreground shrink-0" />
                          <span className="font-medium truncate" title={record.file_name}>
                            {record.file_name}
                          </span>
                        </div>
                        <p className="text-xs text-muted-foreground truncate mt-1" title={record.strm_path}>
                          {record.strm_path}
                        </p>
                      </div>

                      {/* 文件大小 */}
                      <div className="w-24 text-center text-sm text-muted-foreground">
                        {formatSize(record.file_size)}
                      </div>

                      {/* 状态 */}
                      <div className="w-24 text-center">
                        <Badge
                          variant={record.status === "active" ? "default" : "secondary"}
                          className={cn(
                            record.status === "active"
                              ? "bg-green-500/10 text-green-600 hover:bg-green-500/20"
                              : "bg-gray-500/10 text-gray-600 hover:bg-gray-500/20"
                          )}
                        >
                          {record.status === "active" ? "活跃" : "已删除"}
                        </Badge>
                      </div>

                      {/* 创建时间 */}
                      <div className="w-32 text-center text-xs text-muted-foreground">
                        {formatTime(record.created_at)}
                      </div>

                      {/* 操作 */}
                      <div className="w-20 flex justify-center gap-1">
                        <TooltipProvider>
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <Button
                                variant="ghost"
                                size="icon"
                                className="h-7 w-7"
                                onClick={() => {
                                  const url = record.strm_content
                                  if (url) window.open(url, "_blank")
                                }}
                              >
                                <ExternalLink className="h-3.5 w-3.5" />
                              </Button>
                            </TooltipTrigger>
                            <TooltipContent>
                              <p>打开流媒体链接</p>
                            </TooltipContent>
                          </Tooltip>
                        </TooltipProvider>

                        <TooltipProvider>
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <Button
                                variant="ghost"
                                size="icon"
                                className="h-7 w-7 text-red-500 hover:text-red-600 hover:bg-red-50"
                                onClick={() => openDeleteDialog("single", record.id)}
                              >
                                <Trash2 className="h-3.5 w-3.5" />
                              </Button>
                            </TooltipTrigger>
                            <TooltipContent>
                              <p>删除记录</p>
                            </TooltipContent>
                          </Tooltip>
                        </TooltipProvider>
                      </div>
                    </motion.div>
                  ))}
                </AnimatePresence>
              </ScrollArea>
            </div>
          )}
        </CardContent>
      </Card>

      {/* 删除确认对话框 */}
      <Dialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-red-600">
              <AlertCircle className="h-5 w-5" />
              确认删除
            </DialogTitle>
            <DialogDescription>
              {deleteMode === "single" ? (
                <>
                  确定要删除这条记录吗？<br />
                  删除后将无法恢复。
                </>
              ) : (
                <>
                  确定要删除选中的 <strong>{selectedRecords.size}</strong> 条记录吗？<br />
                  删除后将无法恢复。
                </>
              )}
            </DialogDescription>
          </DialogHeader>

          <div className="flex items-center gap-2 py-4">
            <input
              type="checkbox"
              id="deleteWithFile"
              checked={deleteWithFile}
              onChange={(e) => setDeleteWithFile(e.target.checked)}
              className="rounded border-gray-300"
            />
            <label htmlFor="deleteWithFile" className="text-sm cursor-pointer">
              同时删除物理 STRM 文件（不勾选则只删除数据库记录）
            </label>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDeleteDialog(false)} disabled={deleteLoading}>
              <X className="h-4 w-4 mr-2" />
              取消
            </Button>
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={deleteLoading}
            >
              {deleteLoading ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Trash2 className="h-4 w-4 mr-2" />
              )}
              {deleteLoading ? "删除中..." : "确认删除"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
