"use client"

import * as React from "react"
import { useState, useEffect } from "react"
import {
  Settings,
  Server,
  Database,
  Shield,
  RefreshCw,
  CheckCircle,
  XCircle,
  Loader2,
  Save,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { api } from "@/lib/api"

export function SettingsPanel() {
  const [health, setHealth] = useState<{
    status: string
    timestamp: number
    token_valid: boolean
  } | null>(null)
  const [loading, setLoading] = useState(false)

  // Settings state
  const [apiBaseUrl, setApiBaseUrl] = useState("http://localhost:8115")
  const [strmBaseUrl, setStrmBaseUrl] = useState("")
  const [cacheTtl, setCacheTtl] = useState("3600")
  const [autoRefresh, setAutoRefresh] = useState(true)

  const checkHealth = async () => {
    setLoading(true)
    try {
      const result = await api.health()
      setHealth(result)
    } catch (error) {
      setHealth(null)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    checkHealth()
    const interval = setInterval(checkHealth, 30000)
    return () => clearInterval(interval)
  }, [])

  const handleSave = () => {
    // Save to localStorage
    localStorage.setItem("settings", JSON.stringify({
      apiBaseUrl,
      strmBaseUrl,
      cacheTtl,
      autoRefresh,
    }))
    alert("设置已保存")
  }

  useEffect(() => {
    // Load from localStorage
    const saved = localStorage.getItem("settings")
    if (saved) {
      try {
        const settings = JSON.parse(saved)
        if (settings.apiBaseUrl) setApiBaseUrl(settings.apiBaseUrl)
        if (settings.strmBaseUrl) setStrmBaseUrl(settings.strmBaseUrl)
        if (settings.cacheTtl) setCacheTtl(settings.cacheTtl)
        if (settings.autoRefresh !== undefined) setAutoRefresh(settings.autoRefresh)
      } catch (e) {
        console.error("Failed to load settings:", e)
      }
    }
  }, [])

  return (
    <div className="p-6 space-y-6">
      <div>
        <h2 className="text-2xl font-bold">设置</h2>
        <p className="text-muted-foreground">配置 STRM 网关服务</p>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {/* Server Status Card */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Server className="h-5 w-5" />
              服务状态
            </CardTitle>
            <CardDescription>
              检查后端服务连接状态
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between p-4 rounded-lg bg-muted">
              <div className="flex items-center gap-3">
                {loading ? (
                  <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                ) : health ? (
                  <CheckCircle className="h-5 w-5 text-green-500" />
                ) : (
                  <XCircle className="h-5 w-5 text-red-500" />
                )}
                <div>
                  <div className="font-medium">
                    {loading ? "检查中..." : health ? "服务正常" : "服务离线"}
                  </div>
                  {health && (
                    <div className="text-sm text-muted-foreground">
                      Token: {health.token_valid ? "有效" : "无效"}
                    </div>
                  )}
                </div>
              </div>
              <Button variant="outline" size="sm" onClick={checkHealth} disabled={loading}>
                <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
              </Button>
            </div>

            {health && (
              <div className="text-sm text-muted-foreground">
                最后检查: {new Date(health.timestamp * 1000).toLocaleString()}
              </div>
            )}
          </CardContent>
        </Card>

        {/* API Settings Card */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Database className="h-5 w-5" />
              API 配置
            </CardTitle>
            <CardDescription>
              配置后端 API 连接参数
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="api-base-url">API 基础 URL</Label>
              <Input
                id="api-base-url"
                placeholder="http://localhost:8115"
                value={apiBaseUrl}
                onChange={(e) => setApiBaseUrl(e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="strm-base-url">STRM 基础 URL</Label>
              <Input
                id="strm-base-url"
                placeholder="留空则使用 API 基础 URL"
                value={strmBaseUrl}
                onChange={(e) => setStrmBaseUrl(e.target.value)}
              />
              <p className="text-xs text-muted-foreground">
                STRM 文件中使用的流媒体服务地址
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="cache-ttl">缓存时间 (秒)</Label>
              <Input
                id="cache-ttl"
                type="number"
                placeholder="3600"
                value={cacheTtl}
                onChange={(e) => setCacheTtl(e.target.value)}
              />
            </div>
          </CardContent>
        </Card>

        {/* General Settings Card */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Settings className="h-5 w-5" />
              通用设置
            </CardTitle>
            <CardDescription>
              应用程序通用配置
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <Label htmlFor="auto-refresh">自动刷新</Label>
                <p className="text-sm text-muted-foreground">
                  定期检查服务状态
                </p>
              </div>
              <Switch
                id="auto-refresh"
                checked={autoRefresh}
                onCheckedChange={setAutoRefresh}
              />
            </div>
          </CardContent>
        </Card>

        {/* About Card */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Shield className="h-5 w-5" />
              关于
            </CardTitle>
            <CardDescription>
              115 STRM Gateway
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">版本</span>
                <span>1.0.0</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">前端框架</span>
                <span>Next.js + shadcn/ui</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">后端框架</span>
                <span>Python + lib115</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Save Button */}
      <div className="flex justify-end">
        <Button onClick={handleSave}>
          <Save className="mr-2 h-4 w-4" />
          保存设置
        </Button>
      </div>
    </div>
  )
}
