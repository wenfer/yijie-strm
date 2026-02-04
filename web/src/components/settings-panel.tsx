"use client"

import * as React from "react"
import { useState, useEffect, useRef } from "react"
import {
  Settings,
  Server,
  Database,
  FileText,
  CheckCircle,
  Loader2,
  Save,
  Globe,
  Terminal,
  RefreshCw,
  Trash2,
  Pause,
  Play,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { api, SystemConfig } from "@/lib/api"
import { cn } from "@/lib/utils"

// ============================================
// 图标背景组件
// ============================================
function IconBackground({
  children,
  gradient = "from-indigo-500 to-purple-500",
  className
}: {
  children: React.ReactNode
  gradient?: string
  className?: string
}) {
  return (
    <div
      className={cn(
        "relative flex items-center justify-center w-12 h-12 rounded-xl",
        "bg-gradient-to-br",
        gradient,
        "shadow-lg shadow-indigo-500/25",
        className
      )}
    >
      <div className="absolute inset-0 rounded-xl bg-white/20" />
      <div className="relative text-white">{children}</div>
    </div>
  )
}

// ============================================
// 玻璃态卡片组件
// ============================================
interface GlassCardProps {
  children: React.ReactNode
  className?: string
  hover?: boolean
}

function GlassCard({ children, className, hover = true }: GlassCardProps) {
  return (
    <div
      className={cn(
        "glass-card p-6 transition-all duration-300",
        hover && "hover-lift cursor-default",
        className
      )}
    >
      {children}
    </div>
  )
}

// ============================================
// 现代化输入框组件
// ============================================
function ModernInput({
  id,
  label,
  value,
  onChange,
  placeholder,
  type = "text",
  description,
}: {
  id: string
  label: string
  value: string | number
  onChange: (value: string) => void
  placeholder?: string
  type?: string
  description?: string
}) {
  return (
    <div className="space-y-2">
      <Label
        htmlFor={id}
        className="text-sm font-semibold text-foreground/90"
      >
        {label}
      </Label>
      <Input
        id={id}
        type={type}
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className={cn(
          "h-11 px-4 rounded-xl",
          "bg-secondary/50 border-border/50",
          "transition-all duration-200",
          "placeholder:text-muted-foreground/50",
          "hover:bg-secondary hover:border-border",
          "focus:bg-background focus:border-primary/50 focus:ring-4 focus:ring-primary/10",
          "focus:shadow-[0_0_0_4px_hsl(var(--primary)/0.1)]"
        )}
      />
      {description && (
        <p className="text-xs text-muted-foreground/80 leading-relaxed">
          {description}
        </p>
      )}
    </div>
  )
}

// ============================================
// 开关设置项组件
// ============================================
function SwitchSetting({
  id,
  label,
  description,
  checked,
  onCheckedChange,
}: {
  id: string
  label: string
  description: string
  checked: boolean
  onCheckedChange: (checked: boolean) => void
}) {
  return (
    <div className="flex items-center justify-between p-4 rounded-xl bg-secondary/30 border border-border/30 hover:bg-secondary/50 transition-colors">
      <div>
        <Label htmlFor={id} className="text-sm font-semibold text-foreground/90 cursor-pointer">
          {label}
        </Label>
        <p className="text-xs text-muted-foreground mt-0.5">{description}</p>
      </div>
      <Switch
        id={id}
        checked={checked}
        onCheckedChange={onCheckedChange}
        className="data-[state=checked]:bg-gradient-to-r data-[state=checked]:from-indigo-500 data-[state=checked]:to-purple-500"
      />
    </div>
  )
}

// ============================================
// 保存成功提示组件
// ============================================
function SaveSuccessToast({ show, message }: { show: boolean, message?: string }) {
  return (
    <div
      className={cn(
        "fixed bottom-6 right-6 z-50 flex items-center gap-3 px-5 py-3 rounded-xl",
        "bg-emerald-500 text-white shadow-lg shadow-emerald-500/30",
        "transition-all duration-300",
        show
          ? "opacity-100 translate-y-0"
          : "opacity-0 translate-y-4 pointer-events-none"
      )}
    >
      <div className="w-6 h-6 rounded-full bg-white/20 flex items-center justify-center">
        <CheckCircle className="w-4 h-4" />
      </div>
      <div>
        <div className="font-medium text-sm">设置已保存</div>
        {message && <div className="text-xs text-white/80">{message}</div>}
      </div>
    </div>
  )
}

// ============================================
// 日志查看器组件
// ============================================
function LogViewer() {
  const [logs, setLogs] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const [autoRefresh, setAutoRefresh] = useState(true)
  const scrollRef = useRef<HTMLDivElement>(null)

  const fetchLogs = async () => {
    try {
      setLoading(true)
      const res = await api.getSystemLogs(500) // 获取最后500行
      if (res.success && res.data) {
        setLogs(res.data)
      }
    } catch (error) {
      console.error("Failed to fetch logs:", error)
    } finally {
      setLoading(false)
    }
  }

  // 初始加载
  useEffect(() => {
    fetchLogs()
  }, [])

  // 自动刷新
  useEffect(() => {
    let interval: NodeJS.Timeout
    if (autoRefresh) {
      interval = setInterval(fetchLogs, 5000) // 每5秒刷新一次
    }
    return () => clearInterval(interval)
  }, [autoRefresh])

  // 自动滚动到底部
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [logs])

  return (
    <div className="flex flex-col h-[600px] rounded-xl border border-border/50 bg-black/95 text-green-400 font-mono text-xs shadow-2xl overflow-hidden">
      {/* 工具栏 */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-white/10 bg-white/5">
        <div className="flex items-center gap-2">
          <Terminal className="w-4 h-4 text-green-500" />
          <span className="font-semibold text-white/80">System Logs</span>
          {loading && <Loader2 className="w-3 h-3 animate-spin text-white/50 ml-2" />}
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={cn(
              "h-7 px-2 text-xs hover:bg-white/10 hover:text-white",
              autoRefresh ? "text-green-400" : "text-white/50"
            )}
          >
            {autoRefresh ? <Pause className="w-3 h-3 mr-1" /> : <Play className="w-3 h-3 mr-1" />}
            {autoRefresh ? "Auto" : "Paused"}
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={fetchLogs}
            className="h-7 px-2 text-xs text-white/70 hover:bg-white/10 hover:text-white"
          >
            <RefreshCw className="w-3 h-3 mr-1" />
            Refresh
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setLogs([])}
            className="h-7 px-2 text-xs text-red-400/70 hover:bg-red-500/10 hover:text-red-400"
          >
            <Trash2 className="w-3 h-3 mr-1" />
            Clear
          </Button>
        </div>
      </div>

      {/* 日志内容区域 */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-auto p-4 space-y-1 scrollbar-thin scrollbar-thumb-white/20 scrollbar-track-transparent"
      >
        {logs.length === 0 ? (
          <div className="text-white/30 text-center mt-20">No logs available</div>
        ) : (
          logs.map((log, index) => (
            <div key={index} className="whitespace-pre-wrap break-all hover:bg-white/5 px-1 rounded">
              {log}
            </div>
          ))
        )}
      </div>
    </div>
  )
}

// ============================================
// 主设置面板组件
// ============================================
export function SettingsPanel() {
  // ========== 状态 ==========
  const [loading, setLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [showSuccess, setShowSuccess] = useState(false)
  const [successMessage, setSuccessMessage] = useState("")

  const [config, setConfig] = useState<SystemConfig>({
    gateway: {
      host: "0.0.0.0",
      port: 8115,
      debug: false,
      strm_base_url: "",
      cache_ttl: 3600,
      enable_cors: true
    },
    database: {
      url: "",
      generate_schemas: true,
      pool_min: 1,
      pool_max: 10
    },
    log: {
      level: "INFO",
      format: ""
    }
  })

  // ========== 方法 ==========
  const loadConfig = async () => {
    setLoading(true)
    try {
      const res = await api.getSystemConfig()
      if (res.success && res.data) {
        setConfig(res.data)
      }
    } catch (error) {
      console.error("加载配置失败:", error)
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async () => {
    setIsSaving(true)
    try {
      const res = await api.saveSystemConfig(config)
      if (res.success) {
        setSuccessMessage(res.message || "配置已更新")
        setShowSuccess(true)
        setTimeout(() => setShowSuccess(false), 5000)
      } else {
        alert(res.message || "保存失败")
      }
    } catch (error) {
      console.error("保存失败:", error)
      alert("保存配置失败")
    } finally {
      setIsSaving(false)
    }
  }

  const updateGateway = <K extends keyof SystemConfig['gateway']>(
    key: K,
    value: SystemConfig['gateway'][K]
  ) => {
    setConfig(prev => ({
      ...prev,
      gateway: { ...prev.gateway, [key]: value }
    }))
  }

  const updateDatabase = <K extends keyof SystemConfig['database']>(
    key: K,
    value: SystemConfig['database'][K]
  ) => {
    setConfig(prev => ({
      ...prev,
      database: { ...prev.database, [key]: value }
    }))
  }

  const updateLog = <K extends keyof SystemConfig['log']>(
    key: K,
    value: SystemConfig['log'][K]
  ) => {
    setConfig(prev => ({
      ...prev,
      log: { ...prev.log, [key]: value }
    }))
  }

  // ========== 副作用 ==========
  useEffect(() => {
    loadConfig()
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="w-8 h-8 animate-spin text-indigo-500" />
      </div>
    )
  }

  // ========== 渲染 ==========
  return (
    <div className="space-y-6 animate-slide-up">
      {/* 头部区域 */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-indigo-600 via-violet-600 to-purple-700 p-8 text-white shadow-xl shadow-indigo-500/20">
        <div className="absolute top-0 right-0 w-64 h-64 bg-white/10 rounded-full blur-3xl -translate-y-1/2 translate-x-1/3" />
        <div className="absolute bottom-0 left-0 w-48 h-48 bg-purple-400/20 rounded-full blur-3xl translate-y-1/3 -translate-x-1/4" />

        <div className="relative flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <div className="w-10 h-10 rounded-xl bg-white/20 backdrop-blur-sm flex items-center justify-center">
                <Settings className="w-5 h-5" />
              </div>
              <h2 className="text-2xl font-bold">系统设置</h2>
            </div>
            <p className="text-indigo-100/80 max-w-md">
              配置服务器参数。修改端口、数据库等核心配置可能需要重启服务才能生效。
            </p>
          </div>

          <Button
            onClick={handleSave}
            disabled={isSaving}
            className={cn(
              "relative overflow-hidden bg-white text-indigo-600 hover:bg-indigo-50",
              "shadow-lg shadow-black/10 hover:shadow-xl hover:shadow-black/20",
              "transition-all duration-200 min-w-[120px]",
              "active:scale-95"
            )}
          >
            <span className={cn(
              "flex items-center gap-2 transition-all duration-200",
              isSaving ? "opacity-0 translate-y-4" : "opacity-100 translate-y-0"
            )}>
              <Save className="w-4 h-4" />
              保存设置
            </span>
            {isSaving && (
              <span className="absolute inset-0 flex items-center justify-center">
                <Loader2 className="w-4 h-4 animate-spin" />
              </span>
            )}
          </Button>
        </div>
      </div>

      {/* 标签页导航 */}
      <Tabs defaultValue="gateway" className="space-y-6">
        <TabsList className="bg-secondary/30 border border-border/30 p-1 rounded-xl h-auto">
          <TabsTrigger value="gateway" className="rounded-lg data-[state=active]:bg-background data-[state=active]:shadow-sm px-4 py-2">
            <Globe className="w-4 h-4 mr-2" />
            网关服务
          </TabsTrigger>
          <TabsTrigger value="database" className="rounded-lg data-[state=active]:bg-background data-[state=active]:shadow-sm px-4 py-2">
            <Database className="w-4 h-4 mr-2" />
            数据库
          </TabsTrigger>
          <TabsTrigger value="log" className="rounded-lg data-[state=active]:bg-background data-[state=active]:shadow-sm px-4 py-2">
            <FileText className="w-4 h-4 mr-2" />
            日志系统
          </TabsTrigger>
          <TabsTrigger value="log-viewer" className="rounded-lg data-[state=active]:bg-background data-[state=active]:shadow-sm px-4 py-2">
            <Terminal className="w-4 h-4 mr-2" />
            查看日志
          </TabsTrigger>
        </TabsList>

        {/* 网关配置 */}
        <TabsContent value="gateway" className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
          <GlassCard>
            <div className="flex items-center gap-3 mb-6">
              <IconBackground gradient="from-blue-500 to-indigo-600">
                <Server className="w-6 h-6" />
              </IconBackground>
              <div>
                <h3 className="font-semibold text-foreground">网关服务配置</h3>
                <p className="text-xs text-muted-foreground">HTTP 服务与网络参数</p>
              </div>
            </div>

            <div className="grid gap-6 md:grid-cols-2">
              <ModernInput
                id="gateway-host"
                label="监听地址"
                value={config.gateway.host}
                onChange={(v) => updateGateway("host", v)}
                placeholder="0.0.0.0"
                description="通常为 0.0.0.0 以允许外部访问"
              />
              <ModernInput
                id="gateway-port"
                label="监听端口"
                type="number"
                value={config.gateway.port}
                onChange={(v) => updateGateway("port", parseInt(v) || 8115)}
                placeholder="8115"
                description="服务监听的 TCP 端口 (重启生效)"
              />
              <ModernInput
                id="strm-base-url"
                label="STRM 基础 URL"
                value={config.gateway.strm_base_url || ""}
                onChange={(v) => updateGateway("strm_base_url", v)}
                placeholder="http://192.168.1.100:8115"
                description="写入 .strm 文件中的前缀 URL。若留空则尝试自动检测。"
              />
              <ModernInput
                id="cache-ttl"
                label="链接缓存时间 (秒)"
                type="number"
                value={config.gateway.cache_ttl}
                onChange={(v) => updateGateway("cache_ttl", parseInt(v) || 3600)}
                placeholder="3600"
                description="115 下载链接的缓存有效期"
              />
            </div>

            <div className="mt-6 pt-6 border-t border-border/30 grid gap-4 md:grid-cols-2">
              <SwitchSetting
                id="debug-mode"
                label="调试模式"
                description="开启详细的错误堆栈输出"
                checked={config.gateway.debug}
                onCheckedChange={(c) => updateGateway("debug", c)}
              />
              <SwitchSetting
                id="enable-cors"
                label="启用 CORS"
                description="允许跨域资源请求"
                checked={config.gateway.enable_cors}
                onCheckedChange={(c) => updateGateway("enable_cors", c)}
              />
            </div>
          </GlassCard>
        </TabsContent>

        {/* 数据库配置 */}
        <TabsContent value="database" className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
          <GlassCard>
            <div className="flex items-center gap-3 mb-6">
              <IconBackground gradient="from-emerald-400 to-teal-500">
                <Database className="w-6 h-6" />
              </IconBackground>
              <div>
                <h3 className="font-semibold text-foreground">数据库配置</h3>
                <p className="text-xs text-muted-foreground">数据持久化存储</p>
              </div>
            </div>

            <div className="space-y-6">
              <ModernInput
                id="db-url"
                label="连接 URL"
                value={config.database.url}
                onChange={(v) => updateDatabase("url", v)}
                placeholder="sqlite://~/.strm_gateway.db"
                description="支持 SQLite, MySQL, PostgreSQL (重启生效)"
              />

              <div className="grid gap-6 md:grid-cols-2">
                 <ModernInput
                  id="pool-min"
                  label="最小连接池"
                  type="number"
                  value={config.database.pool_min}
                  onChange={(v) => updateDatabase("pool_min", parseInt(v) || 1)}
                  description="仅 MySQL/PG 有效"
                />
                <ModernInput
                  id="pool-max"
                  label="最大连接池"
                  type="number"
                  value={config.database.pool_max}
                  onChange={(v) => updateDatabase("pool_max", parseInt(v) || 10)}
                  description="仅 MySQL/PG 有效"
                />
              </div>

              <div className="pt-2">
                <SwitchSetting
                  id="generate-schemas"
                  label="自动生成表结构"
                  description="启动时自动创建或更新数据库表"
                  checked={config.database.generate_schemas}
                  onCheckedChange={(c) => updateDatabase("generate_schemas", c)}
                />
              </div>
            </div>
          </GlassCard>
        </TabsContent>

        {/* 日志配置 */}
        <TabsContent value="log" className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
          <GlassCard>
            <div className="flex items-center gap-3 mb-6">
              <IconBackground gradient="from-amber-400 to-orange-500">
                <Terminal className="w-6 h-6" />
              </IconBackground>
              <div>
                <h3 className="font-semibold text-foreground">日志系统</h3>
                <p className="text-xs text-muted-foreground">系统运行记录配置</p>
              </div>
            </div>

            <div className="grid gap-6 md:grid-cols-2">
              <div className="space-y-2">
                <Label className="text-sm font-semibold text-foreground/90">日志级别</Label>
                <Select
                  value={config.log.level}
                  onValueChange={(v) => updateLog("level", v)}
                >
                  <SelectTrigger className="h-11 rounded-xl bg-secondary/50 border-border/50">
                    <SelectValue placeholder="选择日志级别" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="DEBUG">DEBUG (调试)</SelectItem>
                    <SelectItem value="INFO">INFO (信息)</SelectItem>
                    <SelectItem value="WARNING">WARNING (警告)</SelectItem>
                    <SelectItem value="ERROR">ERROR (错误)</SelectItem>
                    <SelectItem value="CRITICAL">CRITICAL (严重)</SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground/80 leading-relaxed">
                  控制日志输出的详细程度
                </p>
              </div>

              <ModernInput
                id="log-format"
                label="日志格式"
                value={config.log.format}
                onChange={(v) => updateLog("format", v)}
                placeholder="%(asctime)s - %(name)s..."
                description="Python logging 模块格式字符串"
              />
            </div>
          </GlassCard>
        </TabsContent>

        {/* 日志查看器 */}
        <TabsContent value="log-viewer" className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
          <LogViewer />
        </TabsContent>
      </Tabs>

      {/* 保存成功提示 */}
      <SaveSuccessToast show={showSuccess} message={successMessage} />
    </div>
  )
}
