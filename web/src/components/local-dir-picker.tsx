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
import { Separator } from "@/components/ui/separator"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { cn } from "@/lib/utils"
import { api, LocalDirItem } from "@/lib/api"

interface LocalDirPickerProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSelect: (path: string) => void
}

interface BreadcrumbItem {
  path: string
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

function pathToBreadcrumbs(currentPath: string): BreadcrumbItem[] {
  const parts = currentPath.split("/").filter(Boolean)
  const crumbs: BreadcrumbItem[] = [{ path: "/", name: "/" }]
  for (let i = 0; i < parts.length; i++) {
    crumbs.push({
      path: "/" + parts.slice(0, i + 1).join("/"),
      name: parts[i],
    })
  }
  return crumbs
}

export function LocalDirPicker({ open, onOpenChange, onSelect }: LocalDirPickerProps) {
  const [loading, setLoading] = useState(false)
  const [dirs, setDirs] = useState<LocalDirItem[]>([])
  const [currentPath, setCurrentPath] = useState("/")
  const [parentPath, setParentPath] = useState<string | null>(null)
  const [selectedPath, setSelectedPath] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState("")
  const [error, setError] = useState<string | null>(null)

  const loadDirs = useCallback(async (path: string) => {
    setLoading(true)
    setError(null)
    try {
      const result = await api.listLocalDirs(path)
      if (!result.success) {
        setError(result.data?.toString() || "加载目录失败")
        setDirs([])
        return
      }
      setDirs(result.data.directories)
      setCurrentPath(result.data.current_path)
      setParentPath(result.data.parent_path)
    } catch (error) {
      console.error("Failed to load directories:", error)
      setError("加载目录失败，请重试")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (open) {
      setSelectedPath(null)
      setSearchQuery("")
      setError(null)
      loadDirs("/")
    }
  }, [open, loadDirs])

  const handleDirClick = (dir: LocalDirItem) => {
    loadDirs(dir.path)
    setSelectedPath(dir.path)
  }

  const handleGoBack = () => {
    if (parentPath) {
      loadDirs(parentPath)
      setSelectedPath(parentPath)
    }
  }

  const handleBreadcrumbClick = (crumb: BreadcrumbItem) => {
    loadDirs(crumb.path)
    setSelectedPath(crumb.path)
  }

  const handleSelect = () => {
    const path = selectedPath || currentPath
    onSelect(path)
    onOpenChange(false)
  }

  const filteredDirs = dirs.filter(dir =>
    dir.name.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const breadcrumbs = pathToBreadcrumbs(currentPath)

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[85vh] overflow-hidden rounded-2xl border-0 shadow-2xl bg-white/95 dark:bg-gray-900/95 backdrop-blur-xl">
        {/* 顶部装饰条 */}
        <div className="absolute top-0 left-0 right-0 h-1.5 bg-gradient-to-r from-emerald-500 via-teal-500 to-cyan-500" />

        <DialogHeader className="pt-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-600 text-white shadow-lg">
              <FolderOpen className="h-5 w-5" />
            </div>
            <div>
              <DialogTitle className="text-xl font-semibold tracking-tight">选择输出目录</DialogTitle>
              <DialogDescription className="text-sm text-muted-foreground mt-0.5">
                浏览服务器本地目录并选择 STRM 文件输出路径
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
                  disabled={!parentPath}
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
              <React.Fragment key={item.path}>
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
                  onClick={() => handleBreadcrumbClick(item)}
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
            placeholder="搜索当前目录..."
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

        {/* 目录列表 */}
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
              <p className="text-sm text-muted-foreground">正在加载目录...</p>
            </div>
          ) : error ? (
            <div className="flex flex-col items-center justify-center h-full gap-3">
              <div className="p-4 rounded-full bg-red-100 dark:bg-red-900/30">
                <AlertCircle className="h-8 w-8 text-red-600 dark:text-red-400" />
              </div>
              <p className="text-sm text-red-500">{error}</p>
              <Button variant="outline" size="sm" onClick={() => loadDirs(currentPath)} className="gap-2">
                <RefreshCw className="h-4 w-4" />
                重试
              </Button>
            </div>
          ) : filteredDirs.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
              {searchQuery ? (
                <>
                  <Search className="h-12 w-12 mb-3 opacity-50" />
                  <p className="font-medium">未找到匹配的目录</p>
                  <p className="text-sm mt-1">尝试使用其他关键词搜索</p>
                </>
              ) : (
                <>
                  <div className="p-4 rounded-full bg-muted mb-3">
                    <FolderOpen className="h-8 w-8 opacity-50" />
                  </div>
                  <p className="font-medium">此目录为空</p>
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
                {filteredDirs.map((dir) => (
                  <motion.button
                    key={dir.path}
                    variants={itemVariants}
                    initial="hidden"
                    animate="visible"
                    exit={{ opacity: 0, x: -10 }}
                    whileHover={{ scale: 1.01, x: 2 }}
                    whileTap={{ scale: 0.99 }}
                    onClick={() => handleDirClick(dir)}
                    className={cn(
                      "w-full flex items-center gap-3 p-3 rounded-xl text-left transition-all duration-200",
                      selectedPath === dir.path
                        ? "bg-gradient-to-r from-emerald-500/20 to-teal-500/10 border border-emerald-500/30 shadow-sm"
                        : "hover:bg-muted/80 hover:shadow-sm"
                    )}
                  >
                    <div className={cn(
                      "p-2 rounded-lg transition-colors",
                      selectedPath === dir.path
                        ? "bg-emerald-500 text-white"
                        : "bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400"
                    )}>
                      <Folder className="h-5 w-5" />
                    </div>

                    <div className="flex-1 min-w-0">
                      <p className={cn(
                        "font-medium truncate",
                        selectedPath === dir.path && "text-emerald-700 dark:text-emerald-300"
                      )}>
                        {dir.name}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        文件夹
                      </p>
                    </div>

                    <div className="flex items-center gap-2">
                      {selectedPath === dir.path && (
                        <motion.div
                          initial={{ scale: 0 }}
                          animate={{ scale: 1 }}
                          className="p-1 rounded-full bg-emerald-500 text-white"
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
          className="p-3 rounded-xl bg-gradient-to-r from-emerald-50 to-teal-50 dark:from-emerald-950/30 dark:to-teal-950/20 border border-emerald-200 dark:border-emerald-800"
        >
          <div className="flex items-center gap-2">
            <HardDrive className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
            <span className="text-sm text-muted-foreground">当前选择:</span>
            <span className="text-sm font-medium text-emerald-700 dark:text-emerald-300 truncate">
              {selectedPath || currentPath}
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
            className="gap-2 bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-600 hover:to-teal-700 shadow-md"
          >
            <Check className="h-4 w-4" />
            选择此目录
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
