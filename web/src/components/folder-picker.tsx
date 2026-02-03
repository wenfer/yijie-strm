"use client"

import * as React from "react"
import { useState, useEffect, useCallback } from "react"
import { motion, AnimatePresence } from "framer-motion"
import {
  Folder,
  ChevronRight,
  Loader2,
  Home,
  Search,
  X,
  Check,
  FolderOpen,
  HardDrive,
  ArrowLeft,
  RefreshCw,
  AlertCircle,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { cn } from "@/lib/utils"
import { api, FileItem } from "@/lib/api"

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

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.03 }
  }
}

const itemVariants = {
  hidden: { opacity: 0, x: -10 },
  visible: { opacity: 1, x: 0 }
}

export function FolderPicker({ open, onOpenChange, onSelect, driveId }: FolderPickerProps) {
  const [loading, setLoading] = useState(false)
  const [folders, setFolders] = useState<FileItem[]>([])
  const [currentCid, setCurrentCid] = useState("0")
  const [breadcrumbs, setBreadcrumbs] = useState<BreadcrumbItem[]>([{ cid: "0", name: "根目录" }])
  const [selectedCid, setSelectedCid] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState("")
  const [error, setError] = useState<string | null>(null)

  const loadFolders = useCallback(async (cid: string) => {
    setLoading(true)
    setError(null)
    try {
      const result = await api.listFiles(cid, 1000, 0, driveId)
      // 只显示文件夹
      const folderItems = result.items.filter(item => item.is_dir)
      setFolders(folderItems)
    } catch (error) {
      console.error("Failed to load folders:", error)
      setError("加载文件夹失败，请重试")
    } finally {
      setLoading(false)
    }
  }, [driveId])

  useEffect(() => {
    if (open) {
      // 重置状态
      setCurrentCid("0")
      setBreadcrumbs([{ cid: "0", name: "根目录" }])
      setSelectedCid(null)
      setSearchQuery("")
      setError(null)
      loadFolders("0")
    }
  }, [open, driveId, loadFolders])

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

  const handleGoBack = () => {
    if (breadcrumbs.length > 1) {
      handleBreadcrumbClick(breadcrumbs.length - 2)
    }
  }

  const handleSelect = () => {
    const cid = selectedCid || currentCid
    const path = breadcrumbs.map(b => b.name).join(" / ")
    onSelect(cid, path)
    onOpenChange(false)
  }

  const filteredFolders = folders.filter(folder =>
    folder.name.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const currentFolderName = breadcrumbs[breadcrumbs.length - 1]?.name || "根目录"

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[85vh] overflow-hidden rounded-2xl border-0 shadow-2xl bg-white/95 dark:bg-gray-900/95 backdrop-blur-xl">
        {/* 顶部装饰条 */}
        <div className="absolute top-0 left-0 right-0 h-1.5 bg-gradient-to-r from-amber-500 via-orange-500 to-red-500" />
        
        <DialogHeader className="pt-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-gradient-to-br from-amber-500 to-orange-600 text-white shadow-lg">
              <FolderOpen className="h-5 w-5" />
            </div>
            <div>
              <DialogTitle className="text-xl font-semibold tracking-tight">选择文件夹</DialogTitle>
              <DialogDescription className="text-sm text-muted-foreground mt-0.5">
                浏览 115 网盘文件夹并选择源目录
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        {/* 面包屑导航 */}
        <div className="flex items-center gap-2 p-3 rounded-xl bg-muted/50 border">
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 shrink-0"
                  onClick={handleGoBack}
                  disabled={breadcrumbs.length <= 1}
                >
                  <ArrowLeft className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                <p>返回上一级</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
          
          <Separator orientation="vertical" className="h-5" />
          
          <div className="flex items-center gap-1 text-sm overflow-x-auto flex-1 scrollbar-hide">
            {breadcrumbs.map((item, index) => (
              <React.Fragment key={item.cid}>
                {index > 0 && (
                  <ChevronRight className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                )}
                <Button
                  variant="ghost"
                  size="sm"
                  className={cn(
                    "h-7 px-2 whitespace-nowrap hover:bg-background",
                    index === breadcrumbs.length - 1 
                      ? "font-semibold text-foreground bg-background shadow-sm" 
                      : "text-muted-foreground"
                  )}
                  onClick={() => handleBreadcrumbClick(index)}
                >
                  {index === 0 ? (
                    <Home className="h-4 w-4" />
                  ) : (
                    <>
                      <Folder className="h-3.5 w-3.5 mr-1" />
                      <span className="max-w-[100px] truncate">{item.name}</span>
                    </>
                  )}
                </Button>
              </React.Fragment>
            ))}
          </div>
        </div>

        {/* 搜索栏 */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="搜索当前文件夹..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10 pr-10"
          />
          {searchQuery && (
            <Button
              variant="ghost"
              size="icon"
              className="absolute right-1 top-1/2 -translate-y-1/2 h-7 w-7"
              onClick={() => setSearchQuery("")}
            >
              <X className="h-4 w-4" />
            </Button>
          )}
        </div>

        {/* 文件夹列表 */}
        <ScrollArea className="h-[320px] rounded-xl border bg-muted/30">
          {loading ? (
            <div className="flex flex-col items-center justify-center h-full gap-3">
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                className="relative"
              >
                <div className="absolute inset-0 bg-primary/20 rounded-full animate-ping" />
                <Loader2 className="h-8 w-8 text-primary relative" />
              </motion.div>
              <p className="text-sm text-muted-foreground">正在加载文件夹...</p>
            </div>
          ) : error ? (
            <div className="flex flex-col items-center justify-center h-full gap-3">
              <div className="p-4 rounded-full bg-red-100 dark:bg-red-900/30">
                <AlertCircle className="h-8 w-8 text-red-600 dark:text-red-400" />
              </div>
              <p className="text-sm text-red-500">{error}</p>
              <Button variant="outline" size="sm" onClick={() => loadFolders(currentCid)} className="gap-2">
                <RefreshCw className="h-4 w-4" />
                重试
              </Button>
            </div>
          ) : filteredFolders.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
              {searchQuery ? (
                <>
                  <Search className="h-12 w-12 mb-3 opacity-50" />
                  <p className="font-medium">未找到匹配的文件夹</p>
                  <p className="text-sm mt-1">尝试使用其他关键词搜索</p>
                </>
              ) : (
                <>
                  <div className="p-4 rounded-full bg-muted mb-3">
                    <FolderOpen className="h-8 w-8 opacity-50" />
                  </div>
                  <p className="font-medium">此文件夹为空</p>
                  <p className="text-sm mt-1">该目录下没有子文件夹</p>
                </>
              )}
            </div>
          ) : (
            <motion.div
              variants={containerVariants}
              initial="hidden"
              animate="visible"
              className="p-2 space-y-1"
            >
              <AnimatePresence>
                {filteredFolders.map((folder, index) => (
                  <motion.button
                    key={folder.id}
                    variants={itemVariants}
                    initial="hidden"
                    animate="visible"
                    exit={{ opacity: 0, x: -10 }}
                    whileHover={{ scale: 1.01, x: 2 }}
                    whileTap={{ scale: 0.99 }}
                    onClick={() => handleFolderClick(folder)}
                    className={cn(
                      "w-full flex items-center gap-3 p-3 rounded-xl text-left transition-all duration-200",
                      selectedCid === folder.id
                        ? "bg-gradient-to-r from-amber-500/20 to-orange-500/10 border border-amber-500/30 shadow-sm"
                        : "hover:bg-muted/80 hover:shadow-sm"
                    )}
                  >
                    <div className={cn(
                      "p-2 rounded-lg transition-colors",
                      selectedCid === folder.id
                        ? "bg-amber-500 text-white"
                        : "bg-amber-100 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400"
                    )}>
                      <Folder className="h-5 w-5" />
                    </div>
                    
                    <div className="flex-1 min-w-0">
                      <p className={cn(
                        "font-medium truncate",
                        selectedCid === folder.id && "text-amber-700 dark:text-amber-300"
                      )}>
                        {folder.name}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        文件夹
                      </p>
                    </div>
                    
                    <div className="flex items-center gap-2">
                      {selectedCid === folder.id && (
                        <motion.div
                          initial={{ scale: 0 }}
                          animate={{ scale: 1 }}
                          className="p-1 rounded-full bg-amber-500 text-white"
                        >
                          <Check className="h-3 w-3" />
                        </motion.div>
                      )}
                      <ChevronRight className="h-4 w-4 text-muted-foreground" />
                    </div>
                  </motion.button>
                ))}
              </AnimatePresence>
            </motion.div>
          )}
        </ScrollArea>

        {/* 当前选择 */}
        <motion.div
          layout
          className="p-3 rounded-xl bg-gradient-to-r from-amber-50 to-orange-50 dark:from-amber-950/30 dark:to-orange-950/20 border border-amber-200 dark:border-amber-800"
        >
          <div className="flex items-center gap-2">
            <HardDrive className="h-4 w-4 text-amber-600 dark:text-amber-400" />
            <span className="text-sm text-muted-foreground">当前选择:</span>
            <span className="text-sm font-medium text-amber-700 dark:text-amber-300 truncate">
              {breadcrumbs.map(b => b.name).join(" / ")}
            </span>
          </div>
        </motion.div>

        <DialogFooter className="gap-2 pt-2">
          <Button 
            variant="outline" 
            onClick={() => onOpenChange(false)}
            className="gap-2"
          >
            <X className="h-4 w-4" />
            取消
          </Button>
          <Button 
            onClick={handleSelect}
            disabled={loading}
            className="gap-2 bg-gradient-to-r from-amber-500 to-orange-600 hover:from-amber-600 hover:to-orange-700 shadow-md"
          >
            <Check className="h-4 w-4" />
            选择此文件夹
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
