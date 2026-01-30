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
  Download,
  RefreshCw,
  MoreHorizontal,
  Film,
  Music,
  FileText,
  Image,
  Archive,
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

const getFileIcon = (name: string, isFolder: boolean) => {
  if (isFolder) return <Folder className="h-5 w-5 text-yellow-500" />

  const ext = name.split('.').pop()?.toLowerCase() || ''
  const videoExts = ['mp4', 'mkv', 'avi', 'mov', 'wmv', 'flv', 'webm', 'm4v', 'ts', 'rmvb']
  const audioExts = ['mp3', 'flac', 'wav', 'aac', 'ogg', 'wma', 'm4a', 'ape']
  const imageExts = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'svg']
  const archiveExts = ['zip', 'rar', '7z', 'tar', 'gz']
  const docExts = ['pdf', 'doc', 'docx', 'txt', 'md', 'xls', 'xlsx', 'ppt', 'pptx']

  if (videoExts.includes(ext)) return <Film className="h-5 w-5 text-purple-500" />
  if (audioExts.includes(ext)) return <Music className="h-5 w-5 text-green-500" />
  if (imageExts.includes(ext)) return <Image className="h-5 w-5 text-blue-500" />
  if (archiveExts.includes(ext)) return <Archive className="h-5 w-5 text-orange-500" />
  if (docExts.includes(ext)) return <FileText className="h-5 w-5 text-red-500" />

  return <File className="h-5 w-5 text-gray-500" />
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
    if (!item.is_folder) return
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
        <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground mb-4" />
        <p className="text-muted-foreground">正在检查认证状态...</p>
      </div>
    )
  }

  // 显示未认证的空状态
  if (authenticated === false) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-8 text-center">
        <Folder className="h-16 w-16 text-muted-foreground mb-4" />
        <h3 className="text-lg font-semibold mb-2">未连接网盘</h3>
        <p className="text-muted-foreground mb-6 max-w-md">
          请先在"网盘管理"中添加并认证您的 115 网盘账号，然后即可浏览文件。
        </p>
        <Button onClick={checkAuthentication} variant="outline">
          <RefreshCw className="h-4 w-4 mr-2" />
          重新检查
        </Button>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full -m-6">
      {/* Header */}
      <div className="flex items-center gap-2 p-4 border-b">
        <Button
          variant="ghost"
          size="icon"
          onClick={goBack}
          disabled={breadcrumbs.length <= 1}
        >
          <ChevronLeft className="h-4 w-4" />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          onClick={() => navigateToBreadcrumb(0)}
        >
          <Home className="h-4 w-4" />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          onClick={() => loadFiles(currentCid, offset)}
        >
          <RefreshCw className={cn("h-4 w-4", loading && "animate-spin")} />
        </Button>

        {/* Breadcrumbs */}
        <div className="flex items-center gap-1 flex-1 overflow-x-auto">
          {breadcrumbs.map((crumb, index) => (
            <React.Fragment key={crumb.id}>
              {index > 0 && <ChevronRight className="h-4 w-4 text-muted-foreground flex-shrink-0" />}
              <Button
                variant="ghost"
                size="sm"
                className="flex-shrink-0"
                onClick={() => navigateToBreadcrumb(index)}
              >
                {crumb.name}
              </Button>
            </React.Fragment>
          ))}
        </div>

        {/* Search */}
        <form onSubmit={handleSearch} className="flex items-center gap-2">
          <Input
            placeholder="搜索文件..."
            value={searchKeyword}
            onChange={(e) => setSearchKeyword(e.target.value)}
            className="w-48"
          />
          <Button type="submit" size="icon" variant="ghost">
            <Search className="h-4 w-4" />
          </Button>
        </form>
      </div>

      {/* Search indicator */}
      {isSearchMode && (
        <div className="flex items-center gap-2 px-4 py-2 bg-muted">
          <span className="text-sm text-muted-foreground">
            搜索结果: "{searchKeyword}" ({total} 个结果)
          </span>
          <Button variant="ghost" size="sm" onClick={clearSearch}>
            清除搜索
          </Button>
        </div>
      )}

      {/* File List */}
      <ScrollArea className="flex-1">
        <div className="p-4">
          {loading && items.length === 0 ? (
            <div className="flex items-center justify-center h-32">
              <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : items.length === 0 ? (
            <div className="flex items-center justify-center h-32 text-muted-foreground">
              暂无文件
            </div>
          ) : (
            <div className="space-y-1">
              {items.map((item) => (
                <div
                  key={item.id}
                  className={cn(
                    "flex items-center gap-3 p-3 rounded-lg hover:bg-muted/50 transition-colors",
                    item.is_folder && "cursor-pointer"
                  )}
                  onClick={() => item.is_folder && navigateToFolder(item)}
                >
                  {getFileIcon(item.name, item.is_folder)}
                  <div className="flex-1 min-w-0">
                    <div className="font-medium truncate">{item.name}</div>
                    {!item.is_folder && item.size && (
                      <div className="text-sm text-muted-foreground">
                        {formatBytes(item.size)}
                      </div>
                    )}
                  </div>
                  {!item.is_folder && item.pick_code && (
                    <div className="flex items-center gap-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={(e) => {
                          e.stopPropagation()
                          playFile(item)
                        }}
                      >
                        <Play className="h-4 w-4" />
                      </Button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </ScrollArea>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between p-4 border-t">
          <div className="text-sm text-muted-foreground">
            共 {total} 项，第 {currentPage} / {totalPages} 页
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={offset === 0}
              onClick={() => loadFiles(currentCid, Math.max(0, offset - limit))}
            >
              上一页
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={offset + limit >= total}
              onClick={() => loadFiles(currentCid, offset + limit)}
            >
              下一页
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
