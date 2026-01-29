"use client"

import * as React from "react"
import { useState } from "react"
import {
  FileVideo,
  FolderSync,
  Play,
  Settings,
  RefreshCw,
  CheckCircle,
  XCircle,
  Loader2,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { api } from "@/lib/api"

interface GenerateResult {
  success: boolean
  count?: number
  error?: string
}

interface SyncResult {
  success: boolean
  added?: number
  updated?: number
  deleted?: number
  error?: string
}

export function StrmManager() {
  // Generate STRM state
  const [generateCid, setGenerateCid] = useState("")
  const [outputDir, setOutputDir] = useState("")
  const [baseUrl, setBaseUrl] = useState("")
  const [includeAudio, setIncludeAudio] = useState(false)
  const [preserveStructure, setPreserveStructure] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [generateResult, setGenerateResult] = useState<GenerateResult | null>(null)

  // Sync STRM state
  const [syncCid, setSyncCid] = useState("")
  const [strmDir, setStrmDir] = useState("")
  const [syncBaseUrl, setSyncBaseUrl] = useState("")
  const [deleteOrphans, setDeleteOrphans] = useState(false)
  const [syncing, setSyncing] = useState(false)
  const [syncResult, setSyncResult] = useState<SyncResult | null>(null)

  // Index stats
  const [indexStats, setIndexStats] = useState<{ total_items: number } | null>(null)

  const handleGenerate = async () => {
    if (!generateCid || !outputDir) return

    setGenerating(true)
    setGenerateResult(null)

    try {
      const result = await api.generateStrm({
        cid: generateCid,
        output_dir: outputDir,
        base_url: baseUrl || undefined,
        include_audio: includeAudio,
        preserve_structure: preserveStructure,
      })
      setGenerateResult({ success: true, count: result.count })
    } catch (error) {
      setGenerateResult({
        success: false,
        error: error instanceof Error ? error.message : "生成失败",
      })
    } finally {
      setGenerating(false)
    }
  }

  const handleSync = async () => {
    if (!syncCid || !strmDir) return

    setSyncing(true)
    setSyncResult(null)

    try {
      const result = await api.syncStrm({
        cid: syncCid,
        strm_dir: strmDir,
        base_url: syncBaseUrl || undefined,
        delete_orphans: deleteOrphans,
      })
      setSyncResult({
        success: true,
        added: result.added,
        updated: result.updated,
        deleted: result.deleted,
      })
    } catch (error) {
      setSyncResult({
        success: false,
        error: error instanceof Error ? error.message : "同步失败",
      })
    } finally {
      setSyncing(false)
    }
  }

  const loadIndexStats = async () => {
    try {
      const stats = await api.getStrmIndex()
      setIndexStats(stats)
    } catch (error) {
      console.error("Failed to load index stats:", error)
    }
  }

  React.useEffect(() => {
    loadIndexStats()
  }, [])

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">STRM 管理</h2>
          <p className="text-muted-foreground">生成和管理 STRM 文件</p>
        </div>
        {indexStats && (
          <div className="text-sm text-muted-foreground">
            索引文件数: {indexStats.total_items}
          </div>
        )}
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {/* Generate STRM Card */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileVideo className="h-5 w-5" />
              生成 STRM 文件
            </CardTitle>
            <CardDescription>
              为指定目录生成 STRM 文件，用于流媒体播放
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="generate-cid">源目录 CID</Label>
              <Input
                id="generate-cid"
                placeholder="输入 115 网盘目录 CID"
                value={generateCid}
                onChange={(e) => setGenerateCid(e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="output-dir">输出目录</Label>
              <Input
                id="output-dir"
                placeholder="本地输出目录路径"
                value={outputDir}
                onChange={(e) => setOutputDir(e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="base-url">基础 URL (可选)</Label>
              <Input
                id="base-url"
                placeholder="http://localhost:8115"
                value={baseUrl}
                onChange={(e) => setBaseUrl(e.target.value)}
              />
            </div>

            <div className="flex items-center justify-between">
              <Label htmlFor="include-audio">包含音频文件</Label>
              <Switch
                id="include-audio"
                checked={includeAudio}
                onCheckedChange={setIncludeAudio}
              />
            </div>

            <div className="flex items-center justify-between">
              <Label htmlFor="preserve-structure">保持目录结构</Label>
              <Switch
                id="preserve-structure"
                checked={preserveStructure}
                onCheckedChange={setPreserveStructure}
              />
            </div>

            <Button
              className="w-full"
              onClick={handleGenerate}
              disabled={generating || !generateCid || !outputDir}
            >
              {generating ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  生成中...
                </>
              ) : (
                <>
                  <Play className="mr-2 h-4 w-4" />
                  开始生成
                </>
              )}
            </Button>

            {generateResult && (
              <div
                className={`flex items-center gap-2 p-3 rounded-lg ${
                  generateResult.success
                    ? "bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-400"
                    : "bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-400"
                }`}
              >
                {generateResult.success ? (
                  <>
                    <CheckCircle className="h-4 w-4" />
                    <span>成功生成 {generateResult.count} 个 STRM 文件</span>
                  </>
                ) : (
                  <>
                    <XCircle className="h-4 w-4" />
                    <span>{generateResult.error}</span>
                  </>
                )}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Sync STRM Card */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FolderSync className="h-5 w-5" />
              同步 STRM 文件
            </CardTitle>
            <CardDescription>
              增量同步 STRM 文件，更新新增和删除的文件
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="sync-cid">源目录 CID</Label>
              <Input
                id="sync-cid"
                placeholder="输入 115 网盘目录 CID"
                value={syncCid}
                onChange={(e) => setSyncCid(e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="strm-dir">STRM 目录</Label>
              <Input
                id="strm-dir"
                placeholder="现有 STRM 文件目录"
                value={strmDir}
                onChange={(e) => setStrmDir(e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="sync-base-url">基础 URL (可选)</Label>
              <Input
                id="sync-base-url"
                placeholder="http://localhost:8115"
                value={syncBaseUrl}
                onChange={(e) => setSyncBaseUrl(e.target.value)}
              />
            </div>

            <div className="flex items-center justify-between">
              <Label htmlFor="delete-orphans">删除孤立文件</Label>
              <Switch
                id="delete-orphans"
                checked={deleteOrphans}
                onCheckedChange={setDeleteOrphans}
              />
            </div>

            <Button
              className="w-full"
              onClick={handleSync}
              disabled={syncing || !syncCid || !strmDir}
            >
              {syncing ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  同步中...
                </>
              ) : (
                <>
                  <RefreshCw className="mr-2 h-4 w-4" />
                  开始同步
                </>
              )}
            </Button>

            {syncResult && (
              <div
                className={`flex items-center gap-2 p-3 rounded-lg ${
                  syncResult.success
                    ? "bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-400"
                    : "bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-400"
                }`}
              >
                {syncResult.success ? (
                  <>
                    <CheckCircle className="h-4 w-4" />
                    <span>
                      新增: {syncResult.added} | 更新: {syncResult.updated} | 删除: {syncResult.deleted}
                    </span>
                  </>
                ) : (
                  <>
                    <XCircle className="h-4 w-4" />
                    <span>{syncResult.error}</span>
                  </>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions */}
      <Card>
        <CardHeader>
          <CardTitle>预设目录</CardTitle>
          <CardDescription>快速为常用目录生成 STRM 文件</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-3 lg:grid-cols-5">
            {[
              { name: "剧集", cid: "3177795036869964618" },
              { name: "电影", cid: "3177794855273378210" },
              { name: "纪录片", cid: "3112736229787318869" },
              { name: "综艺节目", cid: "3112736070923860587" },
              { name: "其他文件", cid: "3112736324528257038" },
            ].map((preset) => (
              <Button
                key={preset.cid}
                variant="outline"
                className="h-auto py-4 flex-col"
                onClick={() => {
                  setGenerateCid(preset.cid)
                }}
              >
                <FileVideo className="h-6 w-6 mb-2" />
                <span>{preset.name}</span>
              </Button>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
