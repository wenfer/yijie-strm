"use client"

import * as React from "react"
import { useState, useEffect } from "react"
import {
  HardDrive,
  Plus,
  Trash2,
  Play,
  Square,
  FolderOpen,
  RefreshCw,
  AlertCircle,
  Database,
  ArrowRight,
  Settings,
  MoreVertical,
  Terminal,
  X,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { api, Mount, Drive } from "@/lib/api"
import { cn } from "@/lib/utils"
import { LocalDirPicker } from "@/components/local-dir-picker"
import { FolderPicker } from "@/components/folder-picker"

export function MountManager() {
  const [mounts, setMounts] = useState<Mount[]>([])
  const [drives, setDrives] = useState<Drive[]>([])
  const [loading, setLoading] = useState(false)

  // Create Dialog State
  const [createDialogOpen, setCreateDialogOpen] = useState(false)
  const [selectedDriveId, setSelectedDriveId] = useState("")
  const [mountPoint, setMountPoint] = useState("")
  const [allowOther, setAllowOther] = useState(false)
  const [readOnly, setReadOnly] = useState(true)
  const [dirPickerOpen, setDirPickerOpen] = useState(false)

  // Remote Folder State
  const [rootCid, setRootCid] = useState("0")
  const [rootPath, setRootPath] = useState("根目录")
  const [folderPickerOpen, setFolderPickerOpen] = useState(false)

  // Log Dialog State
  const [logDialogOpen, setLogDialogOpen] = useState(false)
  const [currentLogs, setCurrentLogs] = useState<{timestamp: string, level: string, message: string}[]>([])
  const [currentMountId, setCurrentMountId] = useState<string>("")
  const [isLoadingLogs, setIsLoadingLogs] = useState(false)
  const [logError, setLogError] = useState<string | null>(null)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    setLoading(true)
    try {
      const [mountsRes, drivesRes] = await Promise.all([
        api.listMounts(),
        api.listDrives()
      ])
      setMounts(mountsRes || [])
      setDrives(drivesRes?.drives || [])
    } catch (error) {
      console.error("Failed to load data:", error)
    } finally {
      setLoading(false)
    }
  }

  const handleCreateMount = async () => {
    if (!selectedDriveId || !mountPoint) return

    try {
      await api.createMount({
        drive_id: selectedDriveId,
        mount_point: mountPoint,
        mount_config: {
          allow_other: allowOther,
          read_only: readOnly,
          root_cid: rootCid,
          root_path: rootPath
        }
      })
      setCreateDialogOpen(false)
      // Reset form
      setSelectedDriveId("")
      setMountPoint("")
      setAllowOther(false)
      setReadOnly(true)
      setRootCid("0")
      setRootPath("根目录")
      await loadData()
    } catch (error) {
      console.error("Failed to create mount:", error)
      alert("创建挂载失败: " + (error instanceof Error ? error.message : String(error)))
    }
  }

  const handleStartMount = async (id: string) => {
    setLogError(null)
    setCurrentLogs([])
    setCurrentMountId(id)
    setIsLoadingLogs(true)
    setLogDialogOpen(true)

    try {
      const result = await api.startMount(id)
      setCurrentLogs(result.logs || [])

      if (result.success) {
        // 启动成功，延迟后关闭日志窗口
        setTimeout(() => {
          setLogDialogOpen(false)
          loadData()
        }, 1500)
      } else {
        // 启动失败
        setLogError(result.message || "启动失败")
      }
    } catch (error: any) {
      console.error("Failed to start mount:", error)
      // 从错误响应中提取日志
      const errorDetail = error?.response?.data?.detail
      if (errorDetail && typeof errorDetail === 'object') {
        setCurrentLogs(errorDetail.logs || [])
        setLogError(errorDetail.message || "启动挂载失败")
      } else {
        setLogError("启动挂载失败: " + (error instanceof Error ? error.message : String(error)))
      }
    } finally {
      setIsLoadingLogs(false)
    }
  }

  const handleViewLogs = async (id: string) => {
    setCurrentMountId(id)
    setLogError(null)
    setIsLoadingLogs(true)
    setLogDialogOpen(true)

    try {
      const logs = await api.getMountLogs(id, 100)
      setCurrentLogs(logs.logs || [])
    } catch (error) {
      console.error("Failed to load logs:", error)
      setLogError("加载日志失败")
    } finally {
      setIsLoadingLogs(false)
    }
  }

  const refreshLogs = async () => {
    if (!currentMountId) return
    setIsLoadingLogs(true)
    try {
      const logs = await api.getMountLogs(currentMountId, 100)
      setCurrentLogs(logs.logs || [])
    } catch (error) {
      console.error("Failed to refresh logs:", error)
    } finally {
      setIsLoadingLogs(false)
    }
  }

  const handleStopMount = async (id: string) => {
    try {
      await api.stopMount(id)
      await loadData()
    } catch (error) {
      console.error("Failed to stop mount:", error)
      alert("停止挂载失败: " + (error instanceof Error ? error.message : String(error)))
    }
  }

  const handleDeleteMount = async (id: string) => {
    if (!confirm("确定要删除此挂载配置吗？如果正在运行将会被停止。")) return

    try {
      await api.deleteMount(id)
      await loadData()
    } catch (error) {
      console.error("Failed to delete mount:", error)
      alert("删除挂载失败: " + (error instanceof Error ? error.message : String(error)))
    }
  }

  const getDriveName = (driveId: string) => {
    const drive = drives.find(d => d.drive_id === driveId || d.drive_id === "115_" + driveId)
    return drive ? drive.name : driveId
  }

  return (
    <div className="space-y-6">
      {/* Header Section */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-orange-600/90 via-amber-600/90 to-yellow-600/90 p-6 text-white shadow-xl">
        <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZyBmaWxsPSJub25lIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiPjxnIGZpbGw9IiNmZmZmZmYiIGZpbGwtb3BhY2l0eT0iMC4xIj48Y2lyY2xlIGN4PSIzMCIgY3k9IjMwIiByPSIyIi8+PC9nPjwvZz48L3N2Zz4=')] opacity-50" />
        <div className="relative flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-white/20 backdrop-blur-sm">
                <HardDrive className="h-5 w-5" />
              </div>
              <div>
                <h2 className="text-2xl font-bold tracking-tight">挂载管理</h2>
                <p className="text-sm text-white/80">
                  将网盘挂载为本地磁盘 (FUSE)
                </p>
              </div>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <Button
              variant="secondary"
              size="sm"
              onClick={loadData}
              disabled={loading}
              className="bg-white/20 text-white hover:bg-white/30 backdrop-blur-sm border-0"
            >
              <RefreshCw className={cn("h-4 w-4 mr-2", loading && "animate-spin")} />
              刷新
            </Button>
            <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
              <DialogTrigger asChild>
                <Button
                  size="sm"
                  className="bg-white text-orange-600 hover:bg-white/90 shadow-lg"
                >
                  <Plus className="h-4 w-4 mr-2" />
                  新建挂载
                </Button>
              </DialogTrigger>
              <DialogContent
                className="sm:max-w-md border-0 shadow-2xl"
                onPointerDownOutside={(e) => {
                  // 防止 Select 下拉菜单点击时关闭 Dialog
                  const target = e.target as HTMLElement;
                  if (target.closest('[data-radix-popper-content-wrapper]') ||
                      target.closest('[data-radix-select-viewport]')) {
                    e.preventDefault();
                  }
                }}
              >
                <div className="absolute inset-0 rounded-lg bg-gradient-to-br from-orange-500/5 via-amber-500/5 to-yellow-500/5 pointer-events-none" />
                <DialogHeader className="relative">
                  <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-orange-500 to-amber-600 shadow-lg">
                    <HardDrive className="h-7 w-7 text-white" />
                  </div>
                  <DialogTitle className="text-center text-xl">新建挂载点</DialogTitle>
                  <DialogDescription className="text-center">
                    配置一个新的 FUSE 挂载点，将网盘映射到本地目录。
                  </DialogDescription>
                </DialogHeader>
                <div className="relative space-y-5 py-4">
                  <div className="space-y-2">
                    <Label>选择网盘</Label>
                    <Select value={selectedDriveId} onValueChange={setSelectedDriveId}>
                      <SelectTrigger>
                        <SelectValue placeholder="请选择要挂载的网盘" />
                      </SelectTrigger>
                      <SelectContent position="popper" className="z-50">
                        {drives.map(drive => (
                          <SelectItem key={drive.drive_id} value={drive.drive_id}>
                            {drive.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label>网盘目录</Label>
                    <div className="flex gap-2">
                      <Input
                        value={rootPath}
                        readOnly
                        placeholder="根目录"
                        className="bg-muted/50"
                      />
                      <Button
                        variant="outline"
                        size="icon"
                        onClick={() => {
                          if (!selectedDriveId) {
                            alert("请先选择网盘")
                            return
                          }
                          setFolderPickerOpen(true)
                        }}
                        className="shrink-0"
                      >
                        <FolderOpen className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label>本地挂载路径</Label>
                    <div className="flex gap-2">
                      <Input
                        value={mountPoint}
                        onChange={(e) => setMountPoint(e.target.value)}
                        placeholder="/mnt/115"
                      />
                      <Button
                        variant="outline"
                        size="icon"
                        onClick={() => setDirPickerOpen(true)}
                        className="shrink-0"
                      >
                        <FolderOpen className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>

                  <div className="flex items-center justify-between rounded-lg border p-3 shadow-sm">
                    <div className="space-y-0.5">
                      <Label className="text-base">允许其他用户 (allow_other)</Label>
                      <p className="text-xs text-muted-foreground">
                        允许非 root 用户访问挂载点 (需配置 user_allow_other)
                      </p>
                    </div>
                    <Switch
                      checked={allowOther}
                      onCheckedChange={setAllowOther}
                    />
                  </div>
                </div>
                <DialogFooter className="relative gap-2 sm:gap-0">
                  <Button
                    variant="outline"
                    onClick={() => setCreateDialogOpen(false)}
                    className="flex-1 sm:flex-none"
                  >
                    取消
                  </Button>
                  <Button
                    onClick={handleCreateMount}
                    disabled={!selectedDriveId || !mountPoint}
                    className="flex-1 sm:flex-none bg-gradient-to-r from-orange-600 to-amber-600 hover:from-orange-700 hover:to-amber-700"
                  >
                    创建挂载
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>
        </div>
      </div>

      {/* Mount List */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {mounts.map((mount) => (
          <div
            key={mount.id}
            className={cn(
              "group relative overflow-hidden rounded-2xl transition-all duration-300",
              "bg-white dark:bg-gray-900 shadow-md hover:shadow-xl hover:-translate-y-1",
              mount.is_mounted && "ring-2 ring-green-500/20"
            )}
          >
            {/* Status Bar */}
            <div className={cn(
              "absolute top-0 left-0 right-0 h-1",
              mount.is_mounted
                ? "bg-gradient-to-r from-green-400 to-emerald-500"
                : "bg-gray-200 dark:bg-gray-700"
            )} />

            <div className="relative p-5">
              <div className="mb-4 flex items-start justify-between">
                <div className="flex items-center gap-3 min-w-0">
                  <div className={cn(
                    "flex h-10 w-10 shrink-0 items-center justify-center rounded-xl",
                    mount.is_mounted
                      ? "bg-green-100 text-green-600 dark:bg-green-900/30 dark:text-green-400"
                      : "bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400"
                  )}>
                    <HardDrive className="h-5 w-5" />
                  </div>
                  <div className="min-w-0">
                    <h4 className="truncate font-semibold text-gray-900 dark:text-gray-100">
                      {getDriveName(mount.drive_id)}
                    </h4>
                    <p className="truncate text-xs text-muted-foreground" title={mount.mount_point}>
                      {mount.mount_point}
                    </p>
                    {mount.mount_config?.root_path && (
                      <p className="truncate text-xs text-muted-foreground mt-0.5" title={mount.mount_config.root_path}>
                         根目录: {mount.mount_config.root_path}
                      </p>
                    )}
                  </div>
                </div>

                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="ghost" size="icon" className="h-8 w-8 text-gray-500">
                      <MoreVertical className="h-4 w-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem
                      className="text-red-600 focus:text-red-600"
                      onClick={() => handleDeleteMount(mount.id)}
                    >
                      <Trash2 className="mr-2 h-4 w-4" />
                      删除配置
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>

              {/* Status Indicator */}
              <div className="mb-4 flex items-center gap-2 text-sm">
                <div className={cn(
                  "flex h-2 w-2 rounded-full",
                  mount.is_mounted ? "bg-green-500 animate-pulse" : "bg-gray-300 dark:bg-gray-600"
                )} />
                <span className={cn(
                  "font-medium",
                  mount.is_mounted ? "text-green-600 dark:text-green-400" : "text-gray-500"
                )}>
                  {mount.is_mounted ? "已挂载" : "未挂载"}
                </span>
              </div>

              {/* Config Tags */}
              <div className="mb-4 flex flex-wrap gap-2">
                {mount.mount_config.allow_other && (
                  <span className="inline-flex items-center rounded-md bg-blue-50 px-2 py-1 text-xs font-medium text-blue-700 ring-1 ring-inset ring-blue-700/10 dark:bg-blue-400/10 dark:text-blue-400 dark:ring-blue-400/30">
                    allow_other
                  </span>
                )}
              </div>

              {/* Actions */}
              <div className="flex gap-2">
                {mount.is_mounted ? (
                  <Button
                    variant="outline"
                    className="w-full border-red-200 bg-red-50 text-red-700 hover:bg-red-100 hover:text-red-800 dark:border-red-900/50 dark:bg-red-950/50 dark:text-red-400 dark:hover:bg-red-900/50"
                    onClick={() => handleStopMount(mount.id)}
                  >
                    <Square className="mr-2 h-4 w-4 fill-current" />
                    停止挂载
                  </Button>
                ) : (
                  <Button
                    variant="outline"
                    className="w-full border-green-200 bg-green-50 text-green-700 hover:bg-green-100 hover:text-green-800 dark:border-green-900/50 dark:bg-green-950/50 dark:text-green-400 dark:hover:bg-green-900/50"
                    onClick={() => handleStartMount(mount.id)}
                  >
                    <Play className="mr-2 h-4 w-4 fill-current" />
                    启动挂载
                  </Button>
                )}
                <Button
                  variant="outline"
                  size="icon"
                  onClick={() => handleViewLogs(mount.id)}
                  title="查看日志"
                >
                  <Terminal className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </div>
        ))}

        {/* Empty State */}
        {mounts.length === 0 && !loading && (
          <div className="col-span-full flex flex-col items-center justify-center rounded-2xl border border-dashed border-gray-300 bg-gray-50/50 py-12 dark:border-gray-700 dark:bg-gray-900/50">
            <div className="mb-4 rounded-full bg-gray-100 p-3 dark:bg-gray-800">
              <HardDrive className="h-6 w-6 text-gray-400" />
            </div>
            <h3 className="mb-1 text-lg font-semibold text-gray-900 dark:text-gray-100">
              暂无挂载配置
            </h3>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              创建一个新的挂载点将网盘映射到本地
            </p>
          </div>
        )}
      </div>

      <LocalDirPicker
        open={dirPickerOpen}
        onOpenChange={setDirPickerOpen}
        onSelect={setMountPoint}
      />

      <FolderPicker
        open={folderPickerOpen}
        onOpenChange={setFolderPickerOpen}
        onSelect={(cid, path) => {
            setRootCid(cid)
            setRootPath(path)
        }}
        driveId={selectedDriveId}
      />

      {/* Log Dialog */}
      <Dialog open={logDialogOpen} onOpenChange={setLogDialogOpen}>
        <DialogContent className="sm:max-w-2xl max-h-[80vh] flex flex-col">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Terminal className="h-5 w-5" />
              挂载日志
            </DialogTitle>
            <DialogDescription>
              {isLoadingLogs ? "正在加载..." : logError ? "启动失败" : "启动成功"}
            </DialogDescription>
          </DialogHeader>

          {/* Log Content */}
          <div className="flex-1 overflow-hidden flex flex-col min-h-[300px]">
            {logError && (
              <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md text-red-700 text-sm">
                <div className="flex items-center gap-2 font-medium mb-1">
                  <AlertCircle className="h-4 w-4" />
                  错误
                </div>
                {logError}
              </div>
            )}

            <div className="flex-1 overflow-auto bg-gray-950 rounded-md p-4 font-mono text-xs">
              {currentLogs.length === 0 ? (
                <div className="text-gray-500 text-center py-8">
                  {isLoadingLogs ? "等待日志..." : "暂无日志"}
                </div>
              ) : (
                <div className="space-y-1">
                  {currentLogs.map((log, index) => (
                    <div
                      key={index}
                      className={cn(
                        "flex gap-3",
                        log.level === "ERROR" && "text-red-400",
                        log.level === "WARNING" && "text-yellow-400",
                        log.level === "INFO" && "text-green-400",
                        log.level !== "ERROR" && log.level !== "WARNING" && log.level !== "INFO" && "text-gray-300"
                      )}
                    >
                      <span className="text-gray-600 shrink-0">
                        {new Date(log.timestamp).toLocaleTimeString()}
                      </span>
                      <span className="shrink-0 w-12">{log.level}</span>
                      <span className="break-all">{log.message}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          <DialogFooter className="gap-2">
            <Button
              variant="outline"
              onClick={refreshLogs}
              disabled={isLoadingLogs}
              className="gap-2"
            >
              <RefreshCw className={cn("h-4 w-4", isLoadingLogs && "animate-spin")} />
              刷新日志
            </Button>
            <Button
              variant="outline"
              onClick={() => setLogDialogOpen(false)}
            >
              <X className="mr-2 h-4 w-4" />
              关闭
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
