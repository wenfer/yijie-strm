"use client"

import * as React from "react"
import { useState, useEffect } from "react"
import { FolderOpen } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { ScrollArea } from "@/components/ui/scroll-area"
import { api, StrmTask, Drive } from "@/lib/api"
import { FolderPicker } from "@/components/folder-picker"

interface TaskFormDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  task?: StrmTask | null
  drives: Drive[]
  onSuccess: () => void
}

export function TaskFormDialog({ open, onOpenChange, task, drives, onSuccess }: TaskFormDialogProps) {
  const [loading, setLoading] = useState(false)
  const [folderPickerOpen, setFolderPickerOpen] = useState(false)
  const [folderPath, setFolderPath] = useState("")
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
      // 编辑模式：填充现有任务数据
      setFormData({
        task_name: task.task_name,
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
      setFolderPath("") // 编辑模式下不显示路径，只显示 CID
    } else {
      // 创建模式：使用默认值
      const currentDrive = drives.find(d => d.is_current)
      setFormData(prev => ({
        ...prev,
        drive_id: currentDrive?.drive_id || drives[0]?.drive_id || "",
      }))
      setFolderPath("")
    }
  }, [task, drives, open])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)

    try {
      const taskData: any = {
        task_name: formData.task_name,
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
        await api.updateTask(task.task_id, taskData)
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
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh]">
        <DialogHeader>
          <DialogTitle>{task ? "编辑任务" : "创建任务"}</DialogTitle>
          <DialogDescription>
            配置 STRM 文件自动生成和同步任务
          </DialogDescription>
        </DialogHeader>

        <ScrollArea className="max-h-[60vh] pr-4">
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* 基本信息 */}
            <div className="space-y-4">
              <h3 className="text-sm font-medium">基本信息</h3>

              <div className="space-y-2">
                <Label htmlFor="task_name">任务名称 *</Label>
                <Input
                  id="task_name"
                  value={formData.task_name}
                  onChange={(e) => setFormData({ ...formData, task_name: e.target.value })}
                  placeholder="例如：电影库同步"
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="drive_id">网盘 *</Label>
                <select
                  id="drive_id"
                  value={formData.drive_id}
                  onChange={(e) => setFormData({ ...formData, drive_id: e.target.value })}
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                  required
                >
                  <option value="">选择网盘</option>
                  {drives.map(drive => (
                    <option key={drive.drive_id} value={drive.drive_id}>
                      {drive.name} {drive.is_current ? "(当前)" : ""}
                    </option>
                  ))}
                </select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="source_cid">源目录 *</Label>
                <div className="flex gap-2">
                  <Input
                    id="source_cid"
                    value={formData.source_cid}
                    onChange={(e) => setFormData({ ...formData, source_cid: e.target.value })}
                    placeholder="点击右侧按钮选择文件夹"
                    required
                    readOnly
                    className="flex-1"
                  />
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => setFolderPickerOpen(true)}
                    disabled={!formData.drive_id}
                  >
                    <FolderOpen className="h-4 w-4" />
                  </Button>
                </div>
                {folderPath && (
                  <p className="text-xs text-muted-foreground">
                    已选择: {folderPath}
                  </p>
                )}
                {!folderPath && formData.source_cid && (
                  <p className="text-xs text-muted-foreground">
                    CID: {formData.source_cid}
                  </p>
                )}
                {!formData.drive_id && (
                  <p className="text-xs text-orange-500">
                    请先选择网盘
                  </p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="output_dir">输出目录 *</Label>
                <Input
                  id="output_dir"
                  value={formData.output_dir}
                  onChange={(e) => setFormData({ ...formData, output_dir: e.target.value })}
                  placeholder="例如：/volume1/media/movies"
                  required
                />
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

            {/* 文件过滤 */}
            <div className="space-y-4">
              <h3 className="text-sm font-medium">文件过滤</h3>

              <div className="flex items-center justify-between">
                <Label htmlFor="include_video">包含视频文件</Label>
                <Switch
                  id="include_video"
                  checked={formData.include_video}
                  onCheckedChange={(checked) => setFormData({ ...formData, include_video: checked })}
                />
              </div>

              <div className="flex items-center justify-between">
                <Label htmlFor="include_audio">包含音频文件</Label>
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

            {/* 定时调度 */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-medium">定时调度</h3>
                <Switch
                  checked={formData.schedule_enabled}
                  onCheckedChange={(checked) => setFormData({ ...formData, schedule_enabled: checked })}
                />
              </div>

              {formData.schedule_enabled && (
                <>
                  <div className="space-y-2">
                    <Label htmlFor="schedule_type">调度类型</Label>
                    <select
                      id="schedule_type"
                      value={formData.schedule_type}
                      onChange={(e) => setFormData({ ...formData, schedule_type: e.target.value })}
                      className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                    >
                      <option value="interval">间隔执行</option>
                      <option value="cron">定时执行</option>
                    </select>
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
                        <select
                          id="schedule_unit"
                          value={formData.schedule_unit}
                          onChange={(e) => setFormData({ ...formData, schedule_unit: e.target.value })}
                          className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                        >
                          <option value="seconds">秒</option>
                          <option value="minutes">分钟</option>
                          <option value="hours">小时</option>
                          <option value="days">天</option>
                        </select>
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
                </>
              )}
            </div>

            {/* 文件监听 */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-medium">文件监听（事件驱动）</h3>
                  <p className="text-xs text-muted-foreground mt-1">
                    基于 115 事件 API 实时监听文件变化，无需轮询
                  </p>
                </div>
                <Switch
                  checked={formData.watch_enabled}
                  onCheckedChange={(checked) => setFormData({ ...formData, watch_enabled: checked })}
                />
              </div>

              {formData.watch_enabled && (
                <div className="space-y-2">
                  <Label htmlFor="watch_interval">事件检查间隔（秒）</Label>
                  <Input
                    id="watch_interval"
                    type="number"
                    value={formData.watch_interval}
                    onChange={(e) => setFormData({ ...formData, watch_interval: parseInt(e.target.value) })}
                    min="300"
                  />
                  <p className="text-xs text-muted-foreground">
                    检查新事件的间隔时间。系统会自动检测上传、移动、删除等文件变化。建议设置 1800-3600 秒（30 分钟到 1 小时）
                  </p>
                </div>
              )}
            </div>

            {/* 同步选项 */}
            <div className="space-y-4">
              <h3 className="text-sm font-medium">同步选项</h3>

              <div className="flex items-center justify-between">
                <div>
                  <Label htmlFor="delete_orphans">删除孤立文件</Label>
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

              <div className="flex items-center justify-between">
                <div>
                  <Label htmlFor="preserve_structure">保持目录结构</Label>
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

              <div className="flex items-center justify-between">
                <div>
                  <Label htmlFor="overwrite_strm">覆盖已存在的 STRM 文件</Label>
                  <p className="text-xs text-muted-foreground">
                    启用后每次执行都会重新生成所有 STRM 文件；禁用时仅在文件不存在时生成
                  </p>
                </div>
                <Switch
                  id="overwrite_strm"
                  checked={formData.overwrite_strm}
                  onCheckedChange={(checked) => setFormData({ ...formData, overwrite_strm: checked })}
                />
              </div>
            </div>
          </form>
        </ScrollArea>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            取消
          </Button>
          <Button onClick={handleSubmit} disabled={loading}>
            {loading ? "保存中..." : task ? "更新" : "创建"}
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
