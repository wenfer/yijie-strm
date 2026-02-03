"use client"

import * as React from "react"
import { useState, useEffect } from "react"
import { motion } from "framer-motion"
import {
  FolderOpen,
  Save,
  X,
  HardDrive,
  FileType,
  Clock,
  Eye,
  Settings,
  AlertCircle,
  ChevronDown,
  ChevronUp,
  Folder,
  FileVideo,
  FileAudio,
  Zap,
  Check,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { cn } from "@/lib/utils"
import { api, StrmTask, Drive } from "@/lib/api"
import { FolderPicker } from "@/components/folder-picker"

interface TaskFormDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  task?: StrmTask | null
  drives: Drive[]
  onSuccess: () => void
}

interface FormSectionProps {
  title: string
  icon: React.ElementType
  description?: string
  children: React.ReactNode
  defaultOpen?: boolean
}

function FormSection({ title, icon: Icon, description, children, defaultOpen = true }: FormSectionProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen)
  
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="border rounded-xl overflow-hidden bg-card/50 backdrop-blur-sm"
    >
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between p-4 hover:bg-muted/50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-primary/10 text-primary">
            <Icon className="h-4 w-4" />
          </div>
          <div className="text-left">
            <h3 className="font-semibold text-sm">{title}</h3>
            {description && <p className="text-xs text-muted-foreground">{description}</p>}
          </div>
        </div>
        {isOpen ? <ChevronUp className="h-4 w-4 text-muted-foreground" /> : <ChevronDown className="h-4 w-4 text-muted-foreground" />}
      </button>
      
      <motion.div
        initial={false}
        animate={{ height: isOpen ? "auto" : 0, opacity: isOpen ? 1 : 0 }}
        transition={{ duration: 0.2 }}
        className="overflow-hidden"
      >
        <div className="p-4 pt-0 space-y-4">
          <Separator />
          {children}
        </div>
      </motion.div>
    </motion.div>
  )
}

export function TaskFormDialog({ open, onOpenChange, task, drives, onSuccess }: TaskFormDialogProps) {
  const [loading, setLoading] = useState(false)
  const [folderPickerOpen, setFolderPickerOpen] = useState(false)
  const [folderPath, setFolderPath] = useState("")
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [formData, setFormData] = useState({
    task_name: "",
    drive_id: "",
    source_cid: "",
    output_dir: "",
    base_url: "",
    include_video: true,
    include_audio: false,
    custom_extensions: "",
    schedule_enabled: false,
    schedule_type: "interval",
    schedule_interval: 3600,
    schedule_unit: "seconds",
    schedule_time: "00:00",
    watch_enabled: false,
    watch_interval: 1800,
    delete_orphans: true,
    preserve_structure: true,
    overwrite_strm: false,
  })

  useEffect(() => {
    if (task) {
      setFormData({
        task_name: task.name,
        drive_id: task.drive_id,
        source_cid: task.source_cid,
        output_dir: task.output_dir,
        base_url: task.base_url || "",
        include_video: task.include_video,
        include_audio: task.include_audio,
        custom_extensions: task.custom_extensions?.join(", ") || "",
        schedule_enabled: task.schedule_enabled,
        schedule_type: task.schedule_type || "interval",
        schedule_interval: task.schedule_config?.interval || 3600,
        schedule_unit: task.schedule_config?.unit || "seconds",
        schedule_time: task.schedule_config?.time || "00:00",
        watch_enabled: task.watch_enabled,
        watch_interval: task.watch_interval,
        delete_orphans: task.delete_orphans,
        preserve_structure: task.preserve_structure,
        overwrite_strm: task.overwrite_strm,
      })
      setFolderPath("")
    } else {
      const currentDrive = drives.find(d => d.is_current)
      setFormData(prev => ({
        ...prev,
        drive_id: currentDrive?.drive_id || drives[0]?.drive_id || "",
      }))
      setFolderPath("")
    }
    setErrors({})
  }, [task, drives, open])

  const validateForm = () => {
    const newErrors: Record<string, string> = {}
    
    if (!formData.task_name.trim()) {
      newErrors.task_name = "请输入任务名称"
    }
    if (!formData.drive_id) {
      newErrors.drive_id = "请选择网盘"
    }
    if (!formData.source_cid.trim()) {
      newErrors.source_cid = "请选择源目录"
    }
    if (!formData.output_dir.trim()) {
      newErrors.output_dir = "请输入输出目录"
    }
    
    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!validateForm()) {
      return
    }
    
    setLoading(true)

    try {
      const taskData: any = {
        name: formData.task_name,
        drive_id: formData.drive_id,
        source_cid: formData.source_cid,
        output_dir: formData.output_dir,
        base_url: formData.base_url || undefined,
        include_video: formData.include_video,
        include_audio: formData.include_audio,
        custom_extensions: formData.custom_extensions
          ? formData.custom_extensions.split(",").map(s => s.trim()).filter(Boolean)
          : undefined,
        schedule_enabled: formData.schedule_enabled,
        schedule_type: formData.schedule_enabled ? formData.schedule_type : undefined,
        schedule_config: formData.schedule_enabled
          ? formData.schedule_type === "interval"
            ? { interval: formData.schedule_interval, unit: formData.schedule_unit }
            : { time: formData.schedule_time }
          : undefined,
        watch_enabled: formData.watch_enabled,
        watch_interval: formData.watch_interval,
        delete_orphans: formData.delete_orphans,
        preserve_structure: formData.preserve_structure,
        overwrite_strm: formData.overwrite_strm,
      }

      if (task) {
        await api.updateTask(task.id, taskData)
      } else {
        await api.createTask(taskData)
      }

      onSuccess()
      onOpenChange(false)
    } catch (error) {
      console.error("Failed to save task:", error)
      alert(task ? "更新任务失败" : "创建任务失败")
    } finally {
      setLoading(false)
    }
  }

  const handleFolderSelect = (cid: string, path: string) => {
    setFormData({ ...formData, source_cid: cid })
    setFolderPath(path)
    if (errors.source_cid) {
      setErrors({ ...errors, source_cid: "" })
    }
  }

  const inputClassName = (field: string) => cn(
    "transition-all duration-200",
    errors[field] && "border-red-500 focus-visible:ring-red-500"
  )

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-hidden rounded-2xl border-0 shadow-2xl bg-white/95 dark:bg-gray-900/95 backdrop-blur-xl">
        {/* 顶部装饰条 */}
        <div className="absolute top-0 left-0 right-0 h-1.5 bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500" />
        
        <DialogHeader className="pt-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 text-white shadow-lg">
              <Settings className="h-5 w-5" />
            </div>
            <div>
              <DialogTitle className="text-xl font-semibold tracking-tight">
                {task ? "编辑任务" : "创建任务"}
              </DialogTitle>
              <DialogDescription className="text-sm text-muted-foreground mt-0.5">
                配置 STRM 文件自动生成和同步任务
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <ScrollArea className="max-h-[calc(90vh-200px)] pr-4">
          <form onSubmit={handleSubmit} className="space-y-4 py-2">
            {/* 基本信息 */}
            <FormSection 
              title="基本信息" 
              icon={HardDrive}
              description="配置任务的核心参数"
              defaultOpen={true}
            >
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="task_name" className="flex items-center gap-1">
                    任务名称
                    <span className="text-red-500">*</span>
                  </Label>
                  <Input
                    id="task_name"
                    value={formData.task_name}
                    onChange={(e) => {
                      setFormData({ ...formData, task_name: e.target.value })
                      if (errors.task_name) setErrors({ ...errors, task_name: "" })
                    }}
                    placeholder="例如：电影库同步"
                    className={inputClassName("task_name")}
                  />
                  {errors.task_name && (
                    <p className="text-xs text-red-500 flex items-center gap-1">
                      <AlertCircle className="h-3 w-3" />
                      {errors.task_name}
                    </p>
                  )}
                </div>

                <div className="space-y-2">
                  <Label htmlFor="drive_id" className="flex items-center gap-1">
                    网盘
                    <span className="text-red-500">*</span>
                  </Label>
                  <div className="relative">
                    <select
                      id="drive_id"
                      value={formData.drive_id}
                      onChange={(e) => {
                        setFormData({ ...formData, drive_id: e.target.value })
                        if (errors.drive_id) setErrors({ ...errors, drive_id: "" })
                      }}
                      className={cn(
                        "flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 appearance-none",
                        inputClassName("drive_id")
                      )}
                    >
                      <option value="">选择网盘</option>
                      {drives.map(drive => (
                        <option key={drive.drive_id} value={drive.drive_id}>
                          {drive.name} {drive.is_current ? "(当前)" : ""}
                        </option>
                      ))}
                    </select>
                    <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
                  </div>
                  {errors.drive_id && (
                    <p className="text-xs text-red-500 flex items-center gap-1">
                      <AlertCircle className="h-3 w-3" />
                      {errors.drive_id}
                    </p>
                  )}
                </div>

                <div className="space-y-2">
                  <Label htmlFor="source_cid" className="flex items-center gap-1">
                    源目录
                    <span className="text-red-500">*</span>
                  </Label>
                  <div className="flex gap-2">
                    <div className="relative flex-1">
                      <Folder className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                      <Input
                        id="source_cid"
                        value={formData.source_cid}
                        onChange={(e) => {
                          setFormData({ ...formData, source_cid: e.target.value })
                          if (errors.source_cid) setErrors({ ...errors, source_cid: "" })
                        }}
                        placeholder="点击右侧按钮选择文件夹"
                        readOnly
                        className={cn("pl-10", inputClassName("source_cid"))}
                      />
                    </div>
                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <Button
                            type="button"
                            onClick={() => setFolderPickerOpen(true)}
                            disabled={!formData.drive_id}
                            className="gap-2 bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700 shadow-md"
                          >
                            <FolderOpen className="h-4 w-4" />
                            选择
                          </Button>
                        </TooltipTrigger>
                        {!formData.drive_id && (
                          <TooltipContent>
                            <p>请先选择网盘</p>
                          </TooltipContent>
                        )}
                      </Tooltip>
                    </TooltipProvider>
                  </div>
                  {errors.source_cid && (
                    <p className="text-xs text-red-500 flex items-center gap-1">
                      <AlertCircle className="h-3 w-3" />
                      {errors.source_cid}
                    </p>
                  )}
                  {folderPath && (
                    <motion.p 
                      initial={{ opacity: 0, y: -5 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="text-xs text-muted-foreground flex items-center gap-1"
                    >
                      <Check className="h-3 w-3 text-green-500" />
                      已选择: {folderPath}
                    </motion.p>
                  )}
                  {!folderPath && formData.source_cid && (
                    <p className="text-xs text-muted-foreground">
                      CID: {formData.source_cid}
                    </p>
                  )}
                </div>

                <div className="space-y-2">
                  <Label htmlFor="output_dir" className="flex items-center gap-1">
                    输出目录
                    <span className="text-red-500">*</span>
                  </Label>
                  <Input
                    id="output_dir"
                    value={formData.output_dir}
                    onChange={(e) => {
                      setFormData({ ...formData, output_dir: e.target.value })
                      if (errors.output_dir) setErrors({ ...errors, output_dir: "" })
                    }}
                    placeholder="例如：/volume1/media/movies"
                    className={inputClassName("output_dir")}
                  />
                  {errors.output_dir && (
                    <p className="text-xs text-red-500 flex items-center gap-1">
                      <AlertCircle className="h-3 w-3" />
                      {errors.output_dir}
                    </p>
                  )}
                  <p className="text-xs text-muted-foreground">
                    STRM 文件的保存路径
                  </p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="base_url">基础 URL</Label>
                  <Input
                    id="base_url"
                    value={formData.base_url}
                    onChange={(e) => setFormData({ ...formData, base_url: e.target.value })}
                    placeholder="例如：http://192.168.1.100:8115"
                  />
                  <p className="text-xs text-muted-foreground">
                    STRM 文件中的流媒体服务器地址
                  </p>
                </div>
              </div>
            </FormSection>

            {/* 文件过滤 */}
            <FormSection 
              title="文件过滤" 
              icon={FileType}
              description="选择要包含的文件类型"
              defaultOpen={false}
            >
              <div className="space-y-4">
                <div className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-md bg-blue-100 dark:bg-blue-900/30">
                      <FileVideo className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                    </div>
                    <div>
                      <Label htmlFor="include_video" className="font-medium cursor-pointer">包含视频文件</Label>
                      <p className="text-xs text-muted-foreground">生成视频文件的 STRM 链接</p>
                    </div>
                  </div>
                  <Switch
                    id="include_video"
                    checked={formData.include_video}
                    onCheckedChange={(checked) => setFormData({ ...formData, include_video: checked })}
                  />
                </div>

                <div className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-md bg-purple-100 dark:bg-purple-900/30">
                      <FileAudio className="h-4 w-4 text-purple-600 dark:text-purple-400" />
                    </div>
                    <div>
                      <Label htmlFor="include_audio" className="font-medium cursor-pointer">包含音频文件</Label>
                      <p className="text-xs text-muted-foreground">生成音频文件的 STRM 链接</p>
                    </div>
                  </div>
                  <Switch
                    id="include_audio"
                    checked={formData.include_audio}
                    onCheckedChange={(checked) => setFormData({ ...formData, include_audio: checked })}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="custom_extensions">自定义扩展名</Label>
                  <Input
                    id="custom_extensions"
                    value={formData.custom_extensions}
                    onChange={(e) => setFormData({ ...formData, custom_extensions: e.target.value })}
                    placeholder="例如：.mp4, .mkv, .avi"
                  />
                  <p className="text-xs text-muted-foreground">
                    用逗号分隔，留空则使用默认规则
                  </p>
                </div>
              </div>
            </FormSection>

            {/* 定时调度 */}
            <FormSection 
              title="定时调度" 
              icon={Clock}
              description="设置自动执行计划"
              defaultOpen={false}
            >
              <div className="space-y-4">
                <div className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-md bg-amber-100 dark:bg-amber-900/30">
                      <Clock className="h-4 w-4 text-amber-600 dark:text-amber-400" />
                    </div>
                    <div>
                      <span className="font-medium">启用定时调度</span>
                      <p className="text-xs text-muted-foreground">按计划自动执行任务</p>
                    </div>
                  </div>
                  <Switch
                    checked={formData.schedule_enabled}
                    onCheckedChange={(checked) => setFormData({ ...formData, schedule_enabled: checked })}
                  />
                </div>

                {formData.schedule_enabled && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: "auto" }}
                    exit={{ opacity: 0, height: 0 }}
                    className="space-y-4"
                  >
                    <div className="space-y-2">
                      <Label htmlFor="schedule_type">调度类型</Label>
                      <div className="relative">
                        <select
                          id="schedule_type"
                          value={formData.schedule_type}
                          onChange={(e) => setFormData({ ...formData, schedule_type: e.target.value })}
                          className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm appearance-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                        >
                          <option value="interval">间隔执行</option>
                          <option value="cron">定时执行</option>
                        </select>
                        <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
                      </div>
                    </div>

                    {formData.schedule_type === "interval" ? (
                      <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                          <Label htmlFor="schedule_interval">间隔</Label>
                          <Input
                            id="schedule_interval"
                            type="number"
                            value={formData.schedule_interval}
                            onChange={(e) => setFormData({ ...formData, schedule_interval: parseInt(e.target.value) })}
                            min="1"
                          />
                        </div>
                        <div className="space-y-2">
                          <Label htmlFor="schedule_unit">单位</Label>
                          <div className="relative">
                            <select
                              id="schedule_unit"
                              value={formData.schedule_unit}
                              onChange={(e) => setFormData({ ...formData, schedule_unit: e.target.value })}
                              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm appearance-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                            >
                              <option value="seconds">秒</option>
                              <option value="minutes">分钟</option>
                              <option value="hours">小时</option>
                              <option value="days">天</option>
                            </select>
                            <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
                          </div>
                        </div>
                      </div>
                    ) : (
                      <div className="space-y-2">
                        <Label htmlFor="schedule_time">执行时间</Label>
                        <Input
                          id="schedule_time"
                          type="time"
                          value={formData.schedule_time}
                          onChange={(e) => setFormData({ ...formData, schedule_time: e.target.value })}
                        />
                        <p className="text-xs text-muted-foreground">
                          每天在指定时间执行
                        </p>
                      </div>
                    )}
                  </motion.div>
                )}
              </div>
            </FormSection>

            {/* 文件监听 */}
            <FormSection 
              title="文件监听" 
              icon={Eye}
              description="基于 115 事件 API 实时监听文件变化"
              defaultOpen={false}
            >
              <div className="space-y-4">
                <div className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-md bg-green-100 dark:bg-green-900/30">
                      <Zap className="h-4 w-4 text-green-600 dark:text-green-400" />
                    </div>
                    <div>
                      <span className="font-medium">启用文件监听</span>
                      <p className="text-xs text-muted-foreground">实时响应文件变化，无需轮询</p>
                    </div>
                  </div>
                  <Switch
                    checked={formData.watch_enabled}
                    onCheckedChange={(checked) => setFormData({ ...formData, watch_enabled: checked })}
                  />
                </div>

                {formData.watch_enabled && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: "auto" }}
                    className="space-y-2"
                  >
                    <Label htmlFor="watch_interval">事件检查间隔（秒）</Label>
                    <Input
                      id="watch_interval"
                      type="number"
                      value={formData.watch_interval}
                      onChange={(e) => setFormData({ ...formData, watch_interval: parseInt(e.target.value) })}
                      min="300"
                    />
                    <p className="text-xs text-muted-foreground">
                      检查新事件的间隔时间。建议设置 1800-3600 秒（30 分钟到 1 小时）
                    </p>
                  </motion.div>
                )}
              </div>
            </FormSection>

            {/* 同步选项 */}
            <FormSection 
              title="同步选项" 
              icon={Settings}
              description="配置同步行为"
              defaultOpen={false}
            >
              <div className="space-y-4">
                <div className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
                  <div>
                    <Label htmlFor="delete_orphans" className="font-medium cursor-pointer">删除孤立文件</Label>
                    <p className="text-xs text-muted-foreground">
                      删除源文件已不存在的 STRM 文件
                    </p>
                  </div>
                  <Switch
                    id="delete_orphans"
                    checked={formData.delete_orphans}
                    onCheckedChange={(checked) => setFormData({ ...formData, delete_orphans: checked })}
                  />
                </div>

                <div className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
                  <div>
                    <Label htmlFor="preserve_structure" className="font-medium cursor-pointer">保持目录结构</Label>
                    <p className="text-xs text-muted-foreground">
                      在输出目录中保持源目录的文件夹结构
                    </p>
                  </div>
                  <Switch
                    id="preserve_structure"
                    checked={formData.preserve_structure}
                    onCheckedChange={(checked) => setFormData({ ...formData, preserve_structure: checked })}
                  />
                </div>

                <div className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
                  <div>
                    <Label htmlFor="overwrite_strm" className="font-medium cursor-pointer">覆盖已存在的 STRM 文件</Label>
                    <p className="text-xs text-muted-foreground">
                      启用后每次执行都会重新生成所有 STRM 文件
                    </p>
                  </div>
                  <Switch
                    id="overwrite_strm"
                    checked={formData.overwrite_strm}
                    onCheckedChange={(checked) => setFormData({ ...formData, overwrite_strm: checked })}
                  />
                </div>
              </div>
            </FormSection>
          </form>
        </ScrollArea>

        <DialogFooter className="gap-2 pt-4 border-t">
          <Button 
            variant="outline" 
            onClick={() => onOpenChange(false)}
            className="gap-2"
          >
            <X className="h-4 w-4" />
            取消
          </Button>
          <Button 
            onClick={handleSubmit} 
            disabled={loading}
            className="gap-2 bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700 shadow-md"
          >
            {loading ? (
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
              >
                <Save className="h-4 w-4" />
              </motion.div>
            ) : (
              <Save className="h-4 w-4" />
            )}
            {loading ? "保存中..." : task ? "更新任务" : "创建任务"}
          </Button>
        </DialogFooter>
      </DialogContent>

      <FolderPicker
        open={folderPickerOpen}
        onOpenChange={setFolderPickerOpen}
        onSelect={handleFolderSelect}
        driveId={formData.drive_id}
      />
    </Dialog>
  )
}
