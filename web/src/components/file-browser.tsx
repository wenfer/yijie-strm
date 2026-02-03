"use client"

import * as React from "react"
import { useState, useEffect, useCallback } from "react"
import {
  Folder,
  File,
  ChevronRight,
  ChevronLeft,
  Home,
  Search,
  Play,
  RefreshCw,
  MoreHorizontal,
  Film,
  Music,
  FileText,
  Image,
  Archive,
  X,
  FolderOpen,
  HardDrive,
  FileAudio,
  FileVideo,
  FileImage,
  FileArchive,
  FileCode,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { ScrollArea } from "@/components/ui/scroll-area"
import { api, FileItem } from "@/lib/api"
import { formatBytes, cn } from "@/lib/utils"

interface BreadcrumbItem {
  id: string
  name: string
}

// 文件类型配置
interface FileTypeConfig {
  icon: React.ReactNode
  bgClass: string
  gradientClass: string
}

const getFileTypeConfig = (name: string, isFolder: boolean): FileTypeConfig => {
  if (isFolder) {
    return {
      icon: <Folder className="h-5 w-5 text-amber-600" />,
      bgClass: "bg-amber-100 dark:bg-amber-950/30",
      gradientClass: "from-amber-400 to-orange-500",
    }
  }

  const ext = name.split('.').pop()?.toLowerCase() || ''
  const videoExts = ['mp4', 'mkv', 'avi', 'mov', 'wmv', 'flv', 'webm', 'm4v', 'ts', 'rmvb', '3gp']
  const audioExts = ['mp3', 'flac', 'wav', 'aac', 'ogg', 'wma', 'm4a', 'ape', 'opus']
  const imageExts = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'svg', 'ico', 'tiff']
  const archiveExts = ['zip', 'rar', '7z', 'tar', 'gz', 'bz2', 'xz']
  const docExts = ['pdf', 'doc', 'docx', 'txt', 'md', 'xls', 'xlsx', 'ppt', 'pptx', 'csv']
  const codeExts = ['js', 'ts', 'jsx', 'tsx', 'py', 'java', 'c', 'cpp', 'go', 'rs', 'php', 'rb', 'html', 'css', 'json', 'xml']

  if (videoExts.includes(ext)) {
    return {
      icon: <Film className="h-5 w-5 text-purple-600" />,
      bgClass: "bg-purple-100 dark:bg-purple-950/30",
      gradientClass: "from-purple-400 to-violet-500",
    }
  }
  if (audioExts.includes(ext)) {
    return {
      icon: <Music className="h-5 w-5 text-emerald-600" />,
      bgClass: "bg-emerald-100 dark:bg-emerald-950/30",
      gradientClass: "from-emerald-400 to-green-500",
    }
  }
  if (imageExts.includes(ext)) {
    return {
      icon: <Image className="h-5 w-5 text-blue-600" />,
      bgClass: "bg-blue-100 dark:bg-blue-950/30",
      gradientClass: "from-blue-400 to-cyan-500",
    }
  }
  if (archiveExts.includes(ext)) {
    return {
      icon: <Archive className="h-5 w-5 text-orange-600" />,
      bgClass: "bg-orange-100 dark:bg-orange-950/30",
      gradientClass: "from-orange-400 to-red-500",
    }
  }
  if (docExts.includes(ext)) {
    return {
      icon: <FileText className="h-5 w-5 text-red-600" />,
      bgClass: "bg-red-100 dark:bg-red-950/30",
      gradientClass: "from-red-400 to-rose-500",
    }
  }
  if (codeExts.includes(ext)) {
    return {
      icon: <FileCode className="h-5 w-5 text-cyan-600" />,
      bgClass: "bg-cyan-100 dark:bg-cyan-950/30",
      gradientClass: "from-cyan-400 to-teal-500",
    }
  }

  return {
    icon: <File className="h-5 w-5 text-slate-600" />,
    bgClass: "bg-slate-100 dark:bg-slate-800",
    gradientClass: "from-slate-400 to-gray-500",
  }
}

// 文件图标组件
const FileIcon = ({ name, isFolder, className }: { name: string; isFolder: boolean; className?: string }) => {
  const config = getFileTypeConfig(name, isFolder)
  
  return (
    <div className={cn(
      "relative flex items-center justify-center w-10 h-10 rounded-xl transition-all duration-300",
      config.bgClass,
      className
    )}>
      {/* 渐变光晕效果 */}
      <div className={cn(
        "absolute inset-0 rounded-xl opacity-20 bg-gradient-to-br",
        config.gradientClass
      )} />
      {/* 图标 */}
      <div className="relative z-10 transform transition-transform duration-300 group-hover:scale-110">
        {config.icon}
      </div>
    </div>
  )
}

// 骨架屏组件
const SkeletonItem = () => (
  <div className="flex items-center gap-3 p-3 rounded-xl">
    <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-slate-200 to-slate-300 dark:from-slate-800 dark:to-slate-700 animate-pulse" />
    <div className="flex-1 space-y-2">
      <div className="h-4 w-1/3 bg-gradient-to-r from-slate-200 to-slate-300 dark:from-slate-800 dark:to-slate-700 rounded animate-pulse" />
      <div className="h-3 w-1/4 bg-gradient-to-r from-slate-200 to-slate-300 dark:from-slate-800 dark:to-slate-700 rounded animate-pulse" />
    </div>
  </div>
)

// Shimmer 加载效果
const ShimmerLoader = () => (
  <div className="space-y-2 p-4">
    {Array.from({ length: 8 }).map((_, i) => (
      <div
        key={i}
        className="relative overflow-hidden rounded-xl bg-slate-100 dark:bg-slate-800/50"
      >
        <div className="p-3">
          <SkeletonItem />
        </div>
        {/* Shimmer 动画层 */}
        <div className="absolute inset-0 -translate-x-full animate-shimmer bg-gradient-to-r from-transparent via-white/20 to-transparent dark:via-white/5" />
      </div>
    ))}
  </div>
)

// 空状态插图组件
const EmptyStateIllustration = ({ type }: { type: 'folder' | 'auth' | 'search' }) => {
  const configs = {
    folder: {
      icon: FolderOpen,
      bgGradient: "from-blue-400/20 to-cyan-400/20",
      iconColor: "text-blue-500",
      ringColor: "ring-blue-400/30",
    },
    auth: {
      icon: HardDrive,
      bgGradient: "from-amber-400/20 to-orange-400/20",
      iconColor: "text-amber-500",
      ringColor: "ring-amber-400/30",
    },
    search: {
      icon: Search,
      bgGradient: "from-purple-400/20 to-pink-400/20",
      iconColor: "text-purple-500",
      ringColor: "ring-purple-400/30",
    },
  }

  const config = configs[type]
  const Icon = config.icon

  return (
    <div className={cn(
      "relative w-24 h-24 rounded-3xl flex items-center justify-center",
      "bg-gradient-to-br",
      config.bgGradient,
      "ring-8",
      config.ringColor
    )}>
      <Icon className={cn("h-10 w-10", config.iconColor)} />
      {/* 装饰圆点 */}
      <div className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-white/50 dark:bg-white/20" />
      <div className="absolute -bottom-2 -left-2 w-6 h-6 rounded-full bg-white/30 dark:bg-white/10" />
    </div>
  )
}

export function FileBrowser() {
  const [currentCid, setCurrentCid] = useState("0")
  const [items, setItems] = useState<FileItem[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [searchKeyword, setSearchKeyword] = useState("")
  const [isSearchMode, setIsSearchMode] = useState(false)
  const [breadcrumbs, setBreadcrumbs] = useState<BreadcrumbItem[]>([
    { id: "0", name: "根目录" }
  ])
  const [offset, setOffset] = useState(0)
  const [authenticated, setAuthenticated] = useState<boolean | null>(null)
  const [checkingAuth, setCheckingAuth] = useState(true)
  const [selectedItem, setSelectedItem] = useState<string | null>(null)
  const limit = 50

  const checkAuthentication = useCallback(async () => {
    setCheckingAuth(true)
    try {
      const health = await api.health()
      setAuthenticated(health.authenticated && health.token_valid)
    } catch (error) {
      console.error("Failed to check authentication:", error)
      setAuthenticated(false)
    } finally {
      setCheckingAuth(false)
    }
  }, [])

  const loadFiles = useCallback(async (cid: string, newOffset = 0) => {
    setLoading(true)
    try {
      const response = await api.listFiles(cid, limit, newOffset)
      setItems(response.items)
      setTotal(response.total)
      setOffset(newOffset)
      setIsSearchMode(false)
    } catch (error) {
      console.error("Failed to load files:", error)
      setAuthenticated(false)
    } finally {
      setLoading(false)
    }
  }, [])

  const searchFiles = useCallback(async (keyword: string) => {
    if (!keyword.trim()) return
    setLoading(true)
    try {
      const response = await api.search(keyword, currentCid, limit, 0)
      setItems(response.items)
      setTotal(response.total)
      setOffset(0)
      setIsSearchMode(true)
    } catch (error) {
      console.error("Failed to search:", error)
    } finally {
      setLoading(false)
    }
  }, [currentCid])

  useEffect(() => {
    checkAuthentication()
  }, [checkAuthentication])

  useEffect(() => {
    if (authenticated) {
      loadFiles(currentCid)
    }
  }, [currentCid, loadFiles, authenticated])

  const navigateToFolder = (item: FileItem) => {
    if (!item.is_dir) return
    setCurrentCid(item.id)
    setBreadcrumbs(prev => [...prev, { id: item.id, name: item.name }])
    setSearchKeyword("")
  }

  const navigateToBreadcrumb = (index: number) => {
    const target = breadcrumbs[index]
    setCurrentCid(target.id)
    setBreadcrumbs(breadcrumbs.slice(0, index + 1))
    setSearchKeyword("")
    setIsSearchMode(false)
  }

  const goBack = () => {
    if (breadcrumbs.length > 1) {
      navigateToBreadcrumb(breadcrumbs.length - 2)
    }
  }

  const playFile = (item: FileItem) => {
    if (item.pick_code) {
      const url = api.getStreamUrl(item.pick_code)
      window.open(url, '_blank')
    }
  }

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    searchFiles(searchKeyword)
  }

  const clearSearch = () => {
    setSearchKeyword("")
    setIsSearchMode(false)
    loadFiles(currentCid)
  }

  const totalPages = Math.ceil(total / limit)
  const currentPage = Math.floor(offset / limit) + 1

  // 显示认证检查中的状态
  if (checkingAuth) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-8">
        <div className="relative">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-500 to-purple-600 animate-pulse" />
          <div className="absolute inset-0 flex items-center justify-center">
            <RefreshCw className="h-8 w-8 text-white animate-spin" />
          </div>
        </div>
        <p className="text-muted-foreground mt-4 font-medium">正在检查认证状态...</p>
      </div>
    )
  }

  // 显示未认证的空状态
  if (authenticated === false) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-8 text-center">
        <div className="mb-6">
          <EmptyStateIllustration type="auth" />
        </div>
        <h3 className="text-xl font-semibold mb-2 bg-gradient-to-r from-amber-600 to-orange-600 bg-clip-text text-transparent">
          未连接网盘
        </h3>
        <p className="text-muted-foreground mb-6 max-w-md">
          请先在"网盘管理"中添加并认证您的 115 网盘账号，然后即可浏览文件。
        </p>
        <Button 
          onClick={checkAuthentication} 
          variant="outline"
          className="rounded-full px-6 hover:shadow-lg hover:shadow-amber-500/20 transition-all duration-300"
        >
          <RefreshCw className="h-4 w-4 mr-2" />
          重新检查
        </Button>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full -m-6 bg-gradient-to-b from-slate-50/50 to-white dark:from-slate-950 dark:to-slate-900">
      {/* Header - 毛玻璃效果 */}
      <div className="sticky top-0 z-20 flex items-center gap-2 p-4 border-b bg-white/80 dark:bg-slate-950/80 backdrop-blur-xl">
        {/* 操作按钮组 */}
        <div className="flex items-center gap-1 p-1 rounded-xl bg-slate-100/80 dark:bg-slate-800/50">
          <Button
            variant="ghost"
            size="icon"
            onClick={goBack}
            disabled={breadcrumbs.length <= 1}
            className="h-9 w-9 rounded-lg hover:bg-white dark:hover:bg-slate-700 hover:shadow-sm transition-all duration-200 disabled:opacity-40"
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => navigateToBreadcrumb(0)}
            className="h-9 w-9 rounded-lg hover:bg-white dark:hover:bg-slate-700 hover:shadow-sm transition-all duration-200"
          >
            <Home className="h-4 w-4 text-amber-500" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => loadFiles(currentCid, offset)}
            className="h-9 w-9 rounded-lg hover:bg-white dark:hover:bg-slate-700 hover:shadow-sm transition-all duration-200"
          >
            <RefreshCw className={cn("h-4 w-4 text-blue-500", loading && "animate-spin")} />
          </Button>
        </div>

        {/* Breadcrumbs - 现代化样式 */}
        <div className="flex items-center flex-1 overflow-x-auto scrollbar-hide px-2">
          <nav className="flex items-center">
            {breadcrumbs.map((crumb, index) => {
              const isLast = index === breadcrumbs.length - 1
              return (
                <React.Fragment key={crumb.id}>
                  {index > 0 && (
                    <ChevronRight className="h-4 w-4 text-slate-300 dark:text-slate-600 flex-shrink-0 mx-1" />
                  )}
                  <Button
                    variant="ghost"
                    size="sm"
                    className={cn(
                      "h-8 px-2.5 rounded-lg flex-shrink-0 transition-all duration-200",
                      isLast 
                        ? "bg-blue-50 text-blue-700 dark:bg-blue-950/30 dark:text-blue-300 font-medium hover:bg-blue-100 dark:hover:bg-blue-900/40" 
                        : "text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-slate-900 dark:hover:text-slate-200"
                    )}
                    onClick={() => navigateToBreadcrumb(index)}
                  >
                    {index === 0 ? (
                      <span className="flex items-center gap-1.5">
                        <Home className="h-3.5 w-3.5" />
                        {crumb.name}
                      </span>
                    ) : (
                      <span className="truncate max-w-[120px]">{crumb.name}</span>
                    )}
                  </Button>
                </React.Fragment>
              )
            })}
          </nav>
        </div>

        {/* Search - 圆角设计和图标动画 */}
        <form onSubmit={handleSearch} className="flex items-center gap-2">
          <div className="relative group">
            <Search className={cn(
              "absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 transition-all duration-300",
              searchKeyword ? "text-blue-500" : "text-slate-400 group-focus-within:text-blue-500"
            )} />
            <Input
              placeholder="搜索文件..."
              value={searchKeyword}
              onChange={(e) => setSearchKeyword(e.target.value)}
              className={cn(
                "w-52 pl-10 pr-8 h-9 rounded-full border-slate-200 dark:border-slate-700",
                "bg-slate-100/80 dark:bg-slate-800/50",
                "focus:bg-white dark:focus:bg-slate-800",
                "focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500/50",
                "transition-all duration-300"
              )}
            />
            {searchKeyword && (
              <Button
                type="button"
                variant="ghost"
                size="icon"
                onClick={() => setSearchKeyword("")}
                className="absolute right-1 top-1/2 -translate-y-1/2 h-7 w-7 rounded-full hover:bg-slate-200 dark:hover:bg-slate-700"
              >
                <X className="h-3.5 w-3.5 text-slate-400" />
              </Button>
            )}
          </div>
          <Button 
            type="submit" 
            size="icon"
            disabled={!searchKeyword.trim()}
            className={cn(
              "h-9 w-9 rounded-full transition-all duration-300",
              searchKeyword.trim()
                ? "bg-blue-500 hover:bg-blue-600 text-white shadow-lg shadow-blue-500/30"
                : "bg-slate-200 dark:bg-slate-700 text-slate-400"
            )}
          >
            <Search className="h-4 w-4" />
          </Button>
        </form>
      </div>

      {/* Search indicator - 美化搜索结果提示条 */}
      {isSearchMode && (
        <div className="flex items-center justify-between px-4 py-2.5 bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-950/30 dark:to-indigo-950/20 border-b">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
            <span className="text-sm text-slate-700 dark:text-slate-300">
              搜索结果:
              <span className="font-semibold text-blue-600 dark:text-blue-400 mx-1">"{searchKeyword}"</span>
              <span className="text-slate-500 dark:text-slate-400">({total} 个结果)</span>
            </span>
          </div>
          <Button 
            variant="ghost" 
            size="sm" 
            onClick={clearSearch}
            className="h-7 px-3 rounded-full text-slate-500 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-950/30 transition-colors"
          >
            <X className="h-3.5 w-3.5 mr-1" />
            清除搜索
          </Button>
        </div>
      )}

      {/* File List */}
      <ScrollArea className="flex-1">
        <div className="p-4">
          {loading && items.length === 0 ? (
            <ShimmerLoader />
          ) : items.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16">
              <div className="mb-4">
                <EmptyStateIllustration type={isSearchMode ? 'search' : 'folder'} />
              </div>
              <h3 className="text-lg font-semibold text-slate-700 dark:text-slate-300 mb-1">
                {isSearchMode ? '未找到相关文件' : '暂无文件'}
              </h3>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                {isSearchMode 
                  ? '尝试使用其他关键词搜索' 
                  : '该文件夹为空，或文件正在加载中'}
              </p>
              {isSearchMode && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={clearSearch}
                  className="mt-4 rounded-full"
                >
                  <ChevronLeft className="h-4 w-4 mr-1" />
                  返回浏览
                </Button>
              )}
            </div>
          ) : (
            <div className="space-y-1">
              {items.map((item, index) => {
                const config = getFileTypeConfig(item.name, item.is_dir)
                return (
                  <div
                    key={item.id}
                    className={cn(
                      "group flex items-center gap-3 p-3 rounded-xl",
                      "bg-white/50 dark:bg-slate-800/30",
                      "border border-transparent hover:border-slate-200 dark:hover:border-slate-700",
                      "hover:bg-white dark:hover:bg-slate-800",
                      "hover:shadow-lg hover:shadow-slate-200/50 dark:hover:shadow-slate-900/50",
                      "transition-all duration-300",
                      item.is_dir && "cursor-pointer",
                      selectedItem === item.id && "ring-2 ring-blue-500/30 bg-blue-50/50 dark:bg-blue-950/20"
                    )}
                    style={{
                      animationDelay: `${index * 30}ms`,
                    }}
                    onClick={() => {
                      setSelectedItem(item.id)
                      if (item.is_dir) navigateToFolder(item)
                    }}
                  >
                    {/* 文件图标 */}
                    <FileIcon name={item.name} isFolder={item.is_dir} />
                    
                    {/* 文件信息 */}
                    <div className="flex-1 min-w-0">
                      <div className="font-medium truncate text-slate-900 dark:text-slate-100 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                        {item.name}
                      </div>
                      {!item.is_dir && item.size && (
                        <div className="text-sm text-slate-500 dark:text-slate-400 flex items-center gap-2">
                          <span className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300">
                            {formatBytes(item.size)}
                          </span>
                        </div>
                      )}
                    </div>

                    {/* 操作按钮 */}
                    {!item.is_dir && item.pick_code && (
                      <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={(e) => {
                            e.stopPropagation()
                            playFile(item)
                          }}
                          className={cn(
                            "h-8 w-8 rounded-lg transition-all duration-200",
                            "bg-purple-50 text-purple-600 hover:bg-purple-100",
                            "dark:bg-purple-950/30 dark:text-purple-400 dark:hover:bg-purple-900/50"
                          )}
                        >
                          <Play className="h-4 w-4" />
                        </Button>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </ScrollArea>

      {/* Pagination - 现代化页码显示 */}
      {totalPages > 1 && (
        <div className="sticky bottom-0 z-20 flex items-center justify-between p-4 border-t bg-white/80 dark:bg-slate-950/80 backdrop-blur-xl">
          <div className="text-sm text-slate-500 dark:text-slate-400">
            <span className="inline-flex items-center gap-1">
              共 <span className="font-medium text-slate-700 dark:text-slate-300">{total}</span> 项
            </span>
            <span className="mx-2 text-slate-300">|</span>
            <span className="inline-flex items-center gap-1">
              第 <span className="font-medium text-blue-600 dark:text-blue-400">{currentPage}</span> / <span className="font-medium">{totalPages}</span> 页
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={offset === 0}
              onClick={() => loadFiles(currentCid, Math.max(0, offset - limit))}
              className={cn(
                "rounded-lg transition-all duration-200",
                offset === 0 
                  ? "opacity-50 cursor-not-allowed" 
                  : "hover:bg-slate-100 dark:hover:bg-slate-800 hover:shadow-sm"
              )}
            >
              <ChevronLeft className="h-4 w-4 mr-1" />
              上一页
            </Button>
            
            {/* 页码指示器 */}
            <div className="flex items-center gap-1 px-2">
              {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                let pageNum
                if (totalPages <= 5) {
                  pageNum = i + 1
                } else if (currentPage <= 3) {
                  pageNum = i + 1
                } else if (currentPage >= totalPages - 2) {
                  pageNum = totalPages - 4 + i
                } else {
                  pageNum = currentPage - 2 + i
                }
                
                const isActive = pageNum === currentPage
                return (
                  <button
                    key={pageNum}
                    onClick={() => loadFiles(currentCid, (pageNum - 1) * limit)}
                    className={cn(
                      "w-8 h-8 rounded-lg text-sm font-medium transition-all duration-200",
                      isActive
                        ? "bg-blue-500 text-white shadow-lg shadow-blue-500/30"
                        : "text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
                    )}
                  >
                    {pageNum}
                  </button>
                )
              })}
            </div>

            <Button
              variant="outline"
              size="sm"
              disabled={offset + limit >= total}
              onClick={() => loadFiles(currentCid, offset + limit)}
              className={cn(
                "rounded-lg transition-all duration-200",
                offset + limit >= total 
                  ? "opacity-50 cursor-not-allowed" 
                  : "hover:bg-slate-100 dark:hover:bg-slate-800 hover:shadow-sm"
              )}
            >
              下一页
              <ChevronRight className="h-4 w-4 ml-1" />
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
