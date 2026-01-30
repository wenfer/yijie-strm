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
      setDrives(result.drives)
    } catch (error) {
      console.error("Failed to load drives:", error)
      // 显示错误提示
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

  const currentDrive = drives.find(d => d.is_current)

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">网盘管理</h2>
          <p className="text-sm text-muted-foreground">
            管理多个 115 网盘账号
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={loadDrives}
            disabled={loading}
          >
            <RefreshCw className={cn("h-4 w-4 mr-2", loading && "animate-spin")} />
            刷新
          </Button>
          <Dialog open={addDialogOpen} onOpenChange={setAddDialogOpen}>
            <DialogTrigger asChild>
              <Button size="sm">
                <Plus className="h-4 w-4 mr-2" />
                添加网盘
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>添加 115 网盘</DialogTitle>
                <DialogDescription>
                  添加一个新的 115 网盘账号。添加后需要扫码认证。
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4 py-4">
                <div className="space-y-2">
                  <Label htmlFor="drive-name">网盘名称</Label>
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
                  />
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setAddDialogOpen(false)}>
                  取消
                </Button>
                <Button onClick={handleAddDrive} disabled={!newDriveName.trim()}>
                  添加
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {currentDrive && (
        <Card className="border-primary">
          <CardHeader>
            <CardTitle className="text-sm font-medium">当前网盘</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <HardDrive className="h-5 w-5 text-primary" />
                <div>
                  <p className="font-medium">{currentDrive.name}</p>
                  <p className="text-xs text-muted-foreground">
                    {currentDrive.is_authenticated ? (
                      <span className="text-green-600">已认证</span>
                    ) : (
                      <span className="text-orange-600">未认证</span>
                    )}
                  </p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {drives.map((drive) => (
          <Card
            key={drive.drive_id}
            className={cn(
              "transition-all",
              drive.is_current && "ring-2 ring-primary"
            )}
          >
            <CardHeader>
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-2 flex-1">
                  <HardDrive className="h-4 w-4 text-muted-foreground" />
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
                      className="h-7 text-sm"
                      autoFocus
                    />
                  ) : (
                    <CardTitle className="text-sm">{drive.name}</CardTitle>
                  )}
                </div>
                <div className="flex gap-1">
                  {editingDriveId === drive.drive_id ? (
                    <>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-7 w-7 p-0"
                        onClick={() => handleSaveEdit(drive.drive_id)}
                      >
                        <Check className="h-3 w-3" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-7 w-7 p-0"
                        onClick={handleCancelEdit}
                      >
                        <X className="h-3 w-3" />
                      </Button>
                    </>
                  ) : (
                    <>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-7 w-7 p-0"
                        onClick={() => handleStartEdit(drive)}
                      >
                        <Edit2 className="h-3 w-3" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-7 w-7 p-0 text-destructive"
                        onClick={() => handleRemoveDrive(drive.drive_id)}
                      >
                        <Trash2 className="h-3 w-3" />
                      </Button>
                    </>
                  )}
                </div>
              </div>
              <CardDescription className="text-xs">
                {drive.is_authenticated ? (
                  <span className="text-green-600">✓ 已认证</span>
                ) : (
                  <span className="text-orange-600">⚠ 未认证</span>
                )}
                {drive.is_current && (
                  <span className="ml-2 text-primary">• 当前使用</span>
                )}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex gap-2">
                {!drive.is_current && drive.is_authenticated && (
                  <Button
                    variant="outline"
                    size="sm"
                    className="flex-1"
                    onClick={() => handleSwitchDrive(drive.drive_id)}
                  >
                    切换
                  </Button>
                )}
                {!drive.is_authenticated && (
                  <Button
                    variant="outline"
                    size="sm"
                    className="flex-1"
                    onClick={() => handleStartAuth(drive)}
                  >
                    <LogIn className="h-3 w-3 mr-1" />
                    认证
                  </Button>
                )}
                {drive.is_current && drive.is_authenticated && (
                  <Button
                    variant="outline"
                    size="sm"
                    className="flex-1"
                    onClick={() => handleStartAuth(drive)}
                  >
                    <RefreshCw className="h-3 w-3 mr-1" />
                    重新认证
                  </Button>
                )}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {drives.length === 0 && !loading && (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <HardDrive className="h-12 w-12 text-muted-foreground mb-4" />
            <p className="text-muted-foreground mb-4">还没有添加网盘</p>
            <Button onClick={() => setAddDialogOpen(true)}>
              <Plus className="h-4 w-4 mr-2" />
              添加第一个网盘
            </Button>
          </CardContent>
        </Card>
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
