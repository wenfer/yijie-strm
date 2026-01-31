"use client"

import * as React from "react"
import { useState, useEffect } from "react"
import { Folder, ChevronRight, Loader2, Home } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { ScrollArea } from "@/components/ui/scroll-area"
import { api, FileItem } from "@/lib/api"
import { cn } from "@/lib/utils"

interface FolderPickerProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSelect: (cid: string, path: string) => void
  driveId?: string
}

interface BreadcrumbItem {
  cid: string
  name: string
}

export function FolderPicker({ open, onOpenChange, onSelect, driveId }: FolderPickerProps) {
  const [loading, setLoading] = useState(false)
  const [folders, setFolders] = useState<FileItem[]>([])
  const [currentCid, setCurrentCid] = useState("0")
  const [breadcrumbs, setBreadcrumbs] = useState<BreadcrumbItem[]>([{ cid: "0", name: "根目录" }])
  const [selectedCid, setSelectedCid] = useState<string | null>(null)

  useEffect(() => {
    if (open) {
      // 重置状态
      setCurrentCid("0")
      setBreadcrumbs([{ cid: "0", name: "根目录" }])
      setSelectedCid(null)
      loadFolders("0")
    }
  }, [open])

  const loadFolders = async (cid: string) => {
    setLoading(true)
    try {
      const result = await api.listFiles(cid, 1000, 0)
      // 只显示文件夹
      const folderItems = result.items.filter(item => item.is_folder)
      setFolders(folderItems)
    } catch (error) {
      console.error("Failed to load folders:", error)
      alert("加载文件夹失败")
    } finally {
      setLoading(false)
    }
  }

  const handleFolderClick = (folder: FileItem) => {
    setCurrentCid(folder.id)
    setBreadcrumbs([...breadcrumbs, { cid: folder.id, name: folder.name }])
    loadFolders(folder.id)
    setSelectedCid(folder.id)
  }

  const handleBreadcrumbClick = (index: number) => {
    const newBreadcrumbs = breadcrumbs.slice(0, index + 1)
    const targetCid = newBreadcrumbs[newBreadcrumbs.length - 1].cid
    setCurrentCid(targetCid)
    setBreadcrumbs(newBreadcrumbs)
    loadFolders(targetCid)
    setSelectedCid(targetCid)
  }

  const handleSelect = () => {
    const cid = selectedCid || currentCid
    const path = breadcrumbs.map(b => b.name).join(" / ")
    onSelect(cid, path)
    onOpenChange(false)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[80vh]">
        <DialogHeader>
          <DialogTitle>选择文件夹</DialogTitle>
          <DialogDescription>
            浏览并选择 115 网盘中的文件夹作为源目录
          </DialogDescription>
        </DialogHeader>

        {/* 面包屑导航 */}
        <div className="flex items-center gap-1 text-sm overflow-x-auto pb-2">
          {breadcrumbs.map((item, index) => (
            <React.Fragment key={item.cid}>
              {index > 0 && <ChevronRight className="h-4 w-4 text-muted-foreground flex-shrink-0" />}
              <Button
                variant="ghost"
                size="sm"
                className={cn(
                  "h-7 px-2 whitespace-nowrap",
                  index === breadcrumbs.length - 1 && "font-semibold"
                )}
                onClick={() => handleBreadcrumbClick(index)}
              >
                {index === 0 ? <Home className="h-4 w-4" /> : item.name}
              </Button>
            </React.Fragment>
          ))}
        </div>

        {/* 文件夹列表 */}
        <ScrollArea className="h-[400px] border rounded-md">
          {loading ? (
            <div className="flex items-center justify-center h-full">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : folders.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
              <Folder className="h-12 w-12 mb-2" />
              <p>此文件夹为空</p>
            </div>
          ) : (
            <div className="p-2 space-y-1">
              {folders.map((folder) => (
                <button
                  key={folder.id}
                  className={cn(
                    "w-full flex items-center gap-3 p-3 rounded-md hover:bg-accent transition-colors text-left",
                    selectedCid === folder.id && "bg-accent"
                  )}
                  onClick={() => handleFolderClick(folder)}
                >
                  <Folder className="h-5 w-5 text-blue-500 flex-shrink-0" />
                  <span className="flex-1 truncate">{folder.name}</span>
                  <ChevronRight className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                </button>
              ))}
            </div>
          )}
        </ScrollArea>

        {/* 当前选择 */}
        <div className="text-sm">
          <span className="text-muted-foreground">当前选择: </span>
          <span className="font-medium">{breadcrumbs.map(b => b.name).join(" / ")}</span>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            取消
          </Button>
          <Button onClick={handleSelect}>
            选择此文件夹
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
