"use client"

import * as React from "react"
import { useState, useEffect } from "react"
import {
  HardDrive,
  Plus,
  Trash2,
  Edit2,
  Check,
  X,
  RefreshCw,
  LogIn,
  Cloud,
  ShieldCheck,
  AlertCircle,
  Zap,
  Database,
  ArrowRight,
  Sparkles,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Label } from "@/components/ui/label"
import { api, Drive } from "@/lib/api"
import { cn } from "@/lib/utils"
import { AuthDialog } from "@/components/auth-dialog"

export function DriveManager() {
  const [drives, setDrives] = useState<Drive[]>([])
  const [loading, setLoading] = useState(false)
  const [addDialogOpen, setAddDialogOpen] = useState(false)
  const [newDriveName, setNewDriveName] = useState("")
  const [editingDriveId, setEditingDriveId] = useState<string | null>(null)
  const [editingName, setEditingName] = useState("")
  const [authDialogOpen, setAuthDialogOpen] = useState(false)
  const [authDrive, setAuthDrive] = useState<Drive | null>(null)

  useEffect(() => {
    loadDrives()
  }, [])

  const loadDrives = async () => {
    setLoading(true)
    try {
      const result = await api.listDrives()
      setDrives(result?.drives || [])
    } catch (error) {
      console.error("Failed to load drives:", error)
      const errorMessage = error instanceof Error ? error.message : "加载网盘列表失败"
      alert(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  const handleAddDrive = async () => {
    if (!newDriveName.trim()) return

    try {
      await api.addDrive(newDriveName.trim())
      setNewDriveName("")
      setAddDialogOpen(false)
      await loadDrives()
    } catch (error) {
      console.error("Failed to add drive:", error)
      alert("添加网盘失败")
    }
  }

  const handleRemoveDrive = async (driveId: string) => {
    if (!confirm("确定要删除这个网盘吗？Token 文件也会被删除。")) return

    try {
      await api.removeDrive(driveId)
      await loadDrives()
    } catch (error) {
      console.error("Failed to remove drive:", error)
      alert("删除网盘失败")
    }
  }

  const handleSwitchDrive = async (driveId: string) => {
    try {
      await api.switchDrive(driveId)
      await loadDrives()
    } catch (error) {
      console.error("Failed to switch drive:", error)
      alert("切换网盘失败")
    }
  }

  const handleStartEdit = (drive: Drive) => {
    setEditingDriveId(drive.drive_id)
    setEditingName(drive.name)
  }

  const handleSaveEdit = async (driveId: string) => {
    if (!editingName.trim()) return

    try {
      await api.updateDrive(driveId, editingName.trim())
      setEditingDriveId(null)
      await loadDrives()
    } catch (error) {
      console.error("Failed to update drive:", error)
      alert("更新网盘失败")
    }
  }

  const handleCancelEdit = () => {
    setEditingDriveId(null)
    setEditingName("")
  }

  const handleStartAuth = (drive: Drive) => {
    setAuthDrive(drive)
    setAuthDialogOpen(true)
  }

  const handleAuthSuccess = async () => {
    await loadDrives()
  }

  const currentDrive = drives?.find(d => d.is_current)
  const authenticatedCount = drives?.filter(d => d.is_authenticated).length || 0

  return (
    <div className="space-y-6">
      {/* Header Section with Bento Style */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-violet-600/90 via-purple-600/90 to-indigo-600/90 p-6 text-white shadow-xl">
        <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZyBmaWxsPSJub25lIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiPjxnIGZpbGw9IiNmZmZmZmYiIGZpbGwtb3BhY2l0eT0iMC4xIj48Y2lyY2xlIGN4PSIzMCIgY3k9IjMwIiByPSIyIi8+PC9nPjwvZz48L3N2Zz4=')] opacity-50" />
        <div className="relative flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-white/20 backdrop-blur-sm">
                <Database className="h-5 w-5" />
              </div>
              <div>
                <h2 className="text-2xl font-bold tracking-tight">网盘管理</h2>
                <p className="text-sm text-white/80">
                  管理多个 115 网盘账号
                </p>
              </div>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            {/* Stats Pills */}
            <div className="flex items-center gap-2 rounded-full bg-white/15 px-4 py-2 backdrop-blur-sm">
              <Cloud className="h-4 w-4 text-cyan-300" />
              <span className="text-sm font-medium">{drives.length} 个网盘</span>
            </div>
            <div className="flex items-center gap-2 rounded-full bg-white/15 px-4 py-2 backdrop-blur-sm">
              <ShieldCheck className="h-4 w-4 text-emerald-300" />
              <span className="text-sm font-medium">{authenticatedCount} 已认证</span>
            </div>
            <div className="flex gap-2">
              <Button
                variant="secondary"
                size="sm"
                onClick={loadDrives}
                disabled={loading}
                className="bg-white/20 text-white hover:bg-white/30 backdrop-blur-sm border-0"
              >
                <RefreshCw className={cn("h-4 w-4 mr-2", loading && "animate-spin")} />
                刷新
              </Button>
              <Dialog open={addDialogOpen} onOpenChange={setAddDialogOpen}>
                <DialogTrigger asChild>
                  <Button 
                    size="sm" 
                    className="bg-white text-violet-600 hover:bg-white/90 shadow-lg"
                  >
                    <Plus className="h-4 w-4 mr-2" />
                    添加网盘
                  </Button>
                </DialogTrigger>
                <DialogContent className="sm:max-w-md border-0 shadow-2xl">
                  <div className="absolute inset-0 rounded-lg bg-gradient-to-br from-violet-500/5 via-purple-500/5 to-indigo-500/5 pointer-events-none" />
                  <DialogHeader className="relative">
                    <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-violet-500 to-purple-600 shadow-lg">
                      <Plus className="h-7 w-7 text-white" />
                    </div>
                    <DialogTitle className="text-center text-xl">添加 115 网盘</DialogTitle>
                    <DialogDescription className="text-center">
                      添加一个新的 115 网盘账号。添加后需要扫码认证。
                    </DialogDescription>
                  </DialogHeader>
                  <div className="relative space-y-5 py-4">
                    <div className="space-y-2">
                      <Label htmlFor="drive-name" className="text-sm font-medium">网盘名称</Label>
                      <Input
                        id="drive-name"
                        placeholder="例如：我的115网盘"
                        value={newDriveName}
                        onChange={(e) => setNewDriveName(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") {
                            handleAddDrive()
                          }
                        }}
                        className="h-11 border-input/50 focus-visible:ring-violet-500"
                      />
                    </div>
                  </div>
                  <DialogFooter className="relative gap-2 sm:gap-0">
                    <Button 
                      variant="outline" 
                      onClick={() => setAddDialogOpen(false)}
                      className="flex-1 sm:flex-none"
                    >
                      取消
                    </Button>
                    <Button 
                      onClick={handleAddDrive} 
                      disabled={!newDriveName.trim()}
                      className="flex-1 sm:flex-none bg-gradient-to-r from-violet-600 to-purple-600 hover:from-violet-700 hover:to-purple-700"
                    >
                      添加网盘
                      <ArrowRight className="ml-2 h-4 w-4" />
                    </Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>
            </div>
          </div>
        </div>
      </div>

      {/* Current Drive Card - Featured Bento Item */}
      {currentDrive && (
        <div className="group relative overflow-hidden rounded-2xl bg-gradient-to-br from-blue-50 via-indigo-50 to-violet-50 p-1 shadow-lg dark:from-blue-950/30 dark:via-indigo-950/30 dark:to-violet-950/30">
          <div className="absolute inset-0 bg-gradient-to-r from-blue-500 via-indigo-500 to-violet-500 opacity-0 transition-opacity duration-500 group-hover:opacity-10" />
          <div className="relative rounded-xl bg-white/80 p-5 backdrop-blur-xl dark:bg-black/40">
            <div className="absolute left-0 top-0 h-full w-1 bg-gradient-to-b from-blue-500 to-violet-500" />
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="flex h-14 w-14 items-center justify-center rounded-xl bg-gradient-to-br from-blue-500 to-violet-600 shadow-lg shadow-blue-500/25">
                  <Zap className="h-7 w-7 text-white" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold uppercase tracking-wider text-blue-600 dark:text-blue-400">
                      当前使用
                    </span>
                    <span className="inline-flex h-2 w-2 animate-pulse rounded-full bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)]" />
                  </div>
                  <h3 className="text-lg font-bold text-gray-900 dark:text-gray-100">{currentDrive.name}</h3>
                  <div className="mt-1 flex items-center gap-2">
                    {currentDrive.is_authenticated ? (
                      <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-medium text-green-700 dark:bg-green-900/30 dark:text-green-400">
                        <ShieldCheck className="h-3 w-3" />
                        已认证
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 rounded-full bg-orange-100 px-2.5 py-0.5 text-xs font-medium text-orange-700 dark:bg-orange-900/30 dark:text-orange-400">
                        <AlertCircle className="h-3 w-3" />
                        未认证
                      </span>
                    )}
                  </div>
                </div>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleStartAuth(currentDrive)}
                className="border-blue-200 bg-white/50 hover:bg-blue-50 dark:border-blue-800 dark:bg-black/20 dark:hover:bg-blue-900/20"
              >
                <RefreshCw className="mr-2 h-4 w-4" />
                重新认证
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Bento Grid */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {drives.map((drive) => (
          <div
            key={drive.drive_id}
            className={cn(
              "group relative overflow-hidden rounded-2xl transition-all duration-300",
              "hover:-translate-y-1 hover:shadow-xl",
              drive.is_current 
                ? "bg-gradient-to-br from-blue-500/10 via-indigo-500/10 to-violet-500/10 ring-2 ring-blue-500/50 shadow-lg shadow-blue-500/10" 
                : "bg-white dark:bg-gray-900 shadow-md shadow-black/5 dark:shadow-black/20"
            )}
          >
            {/* Top gradient bar for current drive */}
            {drive.is_current && (
              <div className="absolute left-0 right-0 top-0 h-1 bg-gradient-to-r from-blue-500 via-indigo-500 to-violet-500" />
            )}
            
            {/* Glass effect overlay */}
            <div className="absolute inset-0 bg-gradient-to-br from-white/40 to-white/0 opacity-0 transition-opacity duration-300 group-hover:opacity-100 dark:from-white/5 dark:to-white/0" />
            
            <div className="relative p-5">
              {/* Card Header */}
              <div className="mb-4 flex items-start justify-between">
                <div className="flex items-center gap-3 flex-1 min-w-0">
                  <div className={cn(
                    "flex h-10 w-10 shrink-0 items-center justify-center rounded-xl transition-all duration-300",
                    drive.is_current
                      ? "bg-gradient-to-br from-blue-500 to-violet-600 shadow-lg shadow-blue-500/25"
                      : "bg-gradient-to-br from-gray-100 to-gray-200 dark:from-gray-800 dark:to-gray-700 group-hover:from-violet-100 group-hover:to-purple-100 dark:group-hover:from-violet-900/30 dark:group-hover:to-purple-900/30"
                  )}>
                    <HardDrive className={cn(
                      "h-5 w-5 transition-colors duration-300",
                      drive.is_current ? "text-white" : "text-gray-600 dark:text-gray-400 group-hover:text-violet-600 dark:group-hover:text-violet-400"
                    )} />
                  </div>
                  <div className="min-w-0 flex-1">
                    {editingDriveId === drive.drive_id ? (
                      <Input
                        value={editingName}
                        onChange={(e) => setEditingName(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") {
                            handleSaveEdit(drive.drive_id)
                          } else if (e.key === "Escape") {
                            handleCancelEdit()
                          }
                        }}
                        className="h-8 text-sm"
                        autoFocus
                      />
                    ) : (
                      <h4 className="truncate font-semibold text-gray-900 dark:text-gray-100">{drive.name}</h4>
                    )}
                    <div className="mt-1 flex items-center gap-2">
                      {drive.is_authenticated ? (
                        <span className="inline-flex items-center gap-1.5 text-xs font-medium text-green-600 dark:text-green-400">
                          <span className="relative flex h-2 w-2">
                            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-75" />
                            <span className="relative inline-flex h-2 w-2 rounded-full bg-green-500 shadow-[0_0_6px_rgba(34,197,94,0.6)]" />
                          </span>
                          已认证
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1.5 text-xs font-medium text-orange-600 dark:text-orange-400">
                          <span className="h-2 w-2 rounded-full bg-orange-500 shadow-[0_0_6px_rgba(249,115,22,0.6)]" />
                          未认证
                        </span>
                      )}
                      {drive.is_current && (
                        <span className="inline-flex items-center gap-1 rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700 dark:bg-blue-900/30 dark:text-blue-400">
                          <Sparkles className="h-3 w-3" />
                          当前
                        </span>
                      )}
                    </div>
                  </div>
                </div>
                <div className="flex gap-1 ml-2">
                  {editingDriveId === drive.drive_id ? (
                    <>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-8 w-8 rounded-lg p-0 text-green-600 hover:bg-green-100 dark:hover:bg-green-900/30"
                        onClick={() => handleSaveEdit(drive.drive_id)}
                      >
                        <Check className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-8 w-8 rounded-lg p-0 text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800"
                        onClick={handleCancelEdit}
                      >
                        <X className="h-4 w-4" />
                      </Button>
                    </>
                  ) : (
                    <>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-8 w-8 rounded-lg p-0 text-gray-600 hover:bg-violet-100 hover:text-violet-600 dark:text-gray-400 dark:hover:bg-violet-900/30 dark:hover:text-violet-400"
                        onClick={() => handleStartEdit(drive)}
                      >
                        <Edit2 className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-8 w-8 rounded-lg p-0 text-gray-600 hover:bg-red-100 hover:text-red-600 dark:text-gray-400 dark:hover:bg-red-900/30 dark:hover:text-red-400"
                        onClick={() => handleRemoveDrive(drive.drive_id)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </>
                  )}
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex gap-2">
                {!drive.is_current && drive.is_authenticated && (
                  <Button
                    variant="outline"
                    size="sm"
                    className="flex-1 border-gray-200 bg-white/50 hover:bg-violet-50 hover:text-violet-600 hover:border-violet-200 dark:border-gray-700 dark:bg-gray-800/50 dark:hover:bg-violet-900/20 dark:hover:border-violet-700 transition-all duration-200"
                    onClick={() => handleSwitchDrive(drive.drive_id)}
                  >
                    <Zap className="mr-1.5 h-3.5 w-3.5" />
                    切换使用
                  </Button>
                )}
                {!drive.is_authenticated && (
                  <Button
                    variant="outline"
                    size="sm"
                    className="flex-1 border-orange-200 bg-orange-50/50 text-orange-700 hover:bg-orange-100 hover:text-orange-800 dark:border-orange-800 dark:bg-orange-900/20 dark:text-orange-400 dark:hover:bg-orange-900/30"
                    onClick={() => handleStartAuth(drive)}
                  >
                    <LogIn className="mr-1.5 h-3.5 w-3.5" />
                    立即认证
                  </Button>
                )}
                {drive.is_current && drive.is_authenticated && (
                  <Button
                    variant="outline"
                    size="sm"
                    className="flex-1 border-blue-200 bg-blue-50/50 text-blue-700 hover:bg-blue-100 hover:text-blue-800 dark:border-blue-800 dark:bg-blue-900/20 dark:text-blue-400 dark:hover:bg-blue-900/30"
                    onClick={() => handleStartAuth(drive)}
                  >
                    <RefreshCw className="mr-1.5 h-3.5 w-3.5" />
                    重新认证
                  </Button>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Empty State */}
      {drives.length === 0 && !loading && (
        <div className="relative overflow-hidden rounded-2xl border border-dashed border-gray-300 bg-gradient-to-b from-gray-50/50 to-white p-12 text-center dark:border-gray-700 dark:from-gray-900/50 dark:to-gray-900">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-violet-100/50 via-transparent to-transparent dark:from-violet-900/20" />
          <div className="relative">
            <div className="mx-auto mb-6 flex h-24 w-24 items-center justify-center">
              <div className="relative">
                <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-violet-200 to-purple-200 blur-xl dark:from-violet-800 dark:to-purple-800" />
                <div className="relative flex h-20 w-20 items-center justify-center rounded-2xl bg-gradient-to-br from-violet-100 to-purple-100 shadow-lg dark:from-violet-900/50 dark:to-purple-900/50">
                  <Cloud className="h-10 w-10 text-violet-400 dark:text-violet-500" />
                </div>
                <div className="absolute -bottom-2 -right-2 flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-orange-400 to-red-400 shadow-lg">
                  <Plus className="h-5 w-5 text-white" />
                </div>
              </div>
            </div>
            <h3 className="mb-2 text-xl font-semibold text-gray-900 dark:text-gray-100">
              还没有添加网盘
            </h3>
            <p className="mb-6 text-sm text-gray-500 dark:text-gray-400 max-w-sm mx-auto">
              添加您的第一个 115 网盘账号，开始管理和切换多个网盘
            </p>
            <Button 
              onClick={() => setAddDialogOpen(true)}
              className="bg-gradient-to-r from-violet-600 to-purple-600 hover:from-violet-700 hover:to-purple-700 shadow-lg shadow-violet-500/25"
            >
              <Plus className="mr-2 h-4 w-4" />
              添加第一个网盘
            </Button>
          </div>
        </div>
      )}

      <AuthDialog
        open={authDialogOpen}
        onOpenChange={setAuthDialogOpen}
        driveId={authDrive?.drive_id}
        driveName={authDrive?.name}
        onSuccess={handleAuthSuccess}
      />
    </div>
  )
}
