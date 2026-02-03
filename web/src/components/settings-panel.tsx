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
  Sparkles,
  Zap,
  Layers,
  Code2,
  Cpu,
  GitBranch,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Badge } from "@/components/ui/badge"
import { api } from "@/lib/api"
import { cn } from "@/lib/utils"

// ============================================
// 类型定义
// ============================================
interface HealthStatus {
  status: string
  timestamp: number
  token_valid: boolean
}

interface SettingsState {
  apiBaseUrl: string
  strmBaseUrl: string
  cacheTtl: string
  autoRefresh: boolean
}

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
// 服务状态指示器组件
// ============================================
function StatusIndicator({ 
  loading, 
  healthy, 
  tokenValid 
}: { 
  loading: boolean
  healthy: boolean
  tokenValid?: boolean
}) {
  if (loading) {
    return (
      <div className="flex flex-col items-center gap-3 p-6">
        <div className="relative">
          <div className="absolute inset-0 rounded-full bg-indigo-500/20 animate-ping-slow" />
          <div className="relative w-16 h-16 rounded-full bg-gradient-to-br from-indigo-500/20 to-purple-500/20 flex items-center justify-center">
            <Loader2 className="w-8 h-8 text-indigo-500 animate-spin" />
          </div>
        </div>
        <div className="text-center">
          <div className="text-sm font-medium text-foreground">检查中...</div>
          <div className="text-xs text-muted-foreground mt-0.5">正在连接服务</div>
        </div>
      </div>
    )
  }

  if (healthy) {
    return (
      <div className="flex flex-col items-center gap-3 p-6">
        <div className="relative">
          <div className="absolute inset-0 rounded-full bg-emerald-500/30 animate-pulse-soft" />
          <div className="relative w-16 h-16 rounded-full bg-gradient-to-br from-emerald-400 to-emerald-600 flex items-center justify-center shadow-lg shadow-emerald-500/30">
            <CheckCircle className="w-8 h-8 text-white" />
          </div>
        </div>
        <div className="text-center">
          <div className="text-sm font-medium text-emerald-600 dark:text-emerald-400">服务正常</div>
          <div className="text-xs text-muted-foreground mt-0.5">
            Token: {tokenValid ? "有效" : "无效"}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col items-center gap-3 p-6">
      <div className="relative">
        <div className="absolute inset-0 rounded-full bg-red-500/20" />
        <div className="relative w-16 h-16 rounded-full bg-gradient-to-br from-red-400 to-red-600 flex items-center justify-center shadow-lg shadow-red-500/30">
          <XCircle className="w-8 h-8 text-white" />
        </div>
      </div>
      <div className="text-center">
        <div className="text-sm font-medium text-red-600 dark:text-red-400">服务离线</div>
        <div className="text-xs text-muted-foreground mt-0.5">无法连接到后端</div>
      </div>
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
  value: string
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
  icon: Icon,
}: {
  id: string
  label: string
  description: string
  checked: boolean
  onCheckedChange: (checked: boolean) => void
  icon: React.ElementType
}) {
  return (
    <div className="flex items-center justify-between p-4 rounded-xl bg-secondary/30 border border-border/30 hover:bg-secondary/50 transition-colors">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-amber-400 to-orange-500 flex items-center justify-center shadow-md shadow-orange-500/20">
          <Icon className="w-5 h-5 text-white" />
        </div>
        <div>
          <Label htmlFor={id} className="text-sm font-semibold text-foreground/90 cursor-pointer">
            {label}
          </Label>
          <p className="text-xs text-muted-foreground mt-0.5">{description}</p>
        </div>
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
function SaveSuccessToast({ show }: { show: boolean }) {
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
        <div className="text-xs text-white/80">您的更改已成功应用</div>
      </div>
    </div>
  )
}

// ============================================
// 主设置面板组件
// ============================================
export function SettingsPanel() {
  // ========== 状态 ==========
  const [health, setHealth] = useState<HealthStatus | null>(null)
  const [loading, setLoading] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [showSuccess, setShowSuccess] = useState(false)

  const [settings, setSettings] = useState<SettingsState>({
    apiBaseUrl: "http://localhost:8115",
    strmBaseUrl: "",
    cacheTtl: "3600",
    autoRefresh: true,
  })

  // ========== 方法 ==========
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

  const handleSave = async () => {
    setIsSaving(true)
    // 模拟保存延迟
    await new Promise(resolve => setTimeout(resolve, 600))
    
    localStorage.setItem("settings", JSON.stringify(settings))
    
    setIsSaving(false)
    setShowSuccess(true)
    setTimeout(() => setShowSuccess(false), 3000)
  }

  const updateSetting = <K extends keyof SettingsState>(
    key: K, 
    value: SettingsState[K]
  ) => {
    setSettings(prev => ({ ...prev, [key]: value }))
  }

  // ========== 副作用 ==========
  useEffect(() => {
    checkHealth()
    const interval = setInterval(() => {
      if (settings.autoRefresh) {
        checkHealth()
      }
    }, 30000)
    return () => clearInterval(interval)
  }, [settings.autoRefresh])

  useEffect(() => {
    const saved = localStorage.getItem("settings")
    if (saved) {
      try {
        const parsed = JSON.parse(saved)
        setSettings(prev => ({
          ...prev,
          ...parsed,
        }))
      } catch (e) {
        console.error("Failed to load settings:", e)
      }
    }
  }, [])

  // ========== 渲染 ==========
  return (
    <div className="space-y-6 animate-slide-up">
      {/* 头部区域 - 渐变背景 */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-indigo-600 via-violet-600 to-purple-700 p-8 text-white shadow-xl shadow-indigo-500/20">
        {/* 装饰元素 */}
        <div className="absolute top-0 right-0 w-64 h-64 bg-white/10 rounded-full blur-3xl -translate-y-1/2 translate-x-1/3" />
        <div className="absolute bottom-0 left-0 w-48 h-48 bg-purple-400/20 rounded-full blur-3xl translate-y-1/3 -translate-x-1/4" />
        
        <div className="relative flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <div className="w-10 h-10 rounded-xl bg-white/20 backdrop-blur-sm flex items-center justify-center">
                <Settings className="w-5 h-5" />
              </div>
              <h2 className="text-2xl font-bold">设置</h2>
            </div>
            <p className="text-indigo-100/80 max-w-md">
              配置 STRM 网关服务参数，管理服务连接和应用程序偏好设置
            </p>
          </div>
          
          {/* 保存按钮 - 固定在头部右侧 */}
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

      {/* Bento Grid 布局 */}
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {/* 
          ============================================
          服务状态卡片
          ============================================
        */}
        <GlassCard className="flex flex-col">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <IconBackground gradient="from-emerald-400 to-teal-500">
                <Server className="w-6 h-6" />
              </IconBackground>
              <div>
                <h3 className="font-semibold text-foreground">服务状态</h3>
                <p className="text-xs text-muted-foreground">后端连接状态</p>
              </div>
            </div>
            <Button
              variant="outline"
              size="icon"
              onClick={checkHealth}
              disabled={loading}
              className="rounded-xl h-9 w-9 border-border/50 hover:bg-secondary/80"
            >
              <RefreshCw className={cn("w-4 h-4", loading && "animate-spin")} />
            </Button>
          </div>
          
          <div className="flex-1 flex items-center justify-center">
            <StatusIndicator 
              loading={loading} 
              healthy={!!health} 
              tokenValid={health?.token_valid}
            />
          </div>

          {health && (
            <div className="mt-4 pt-4 border-t border-border/30 text-center">
              <div className="text-xs text-muted-foreground">
                最后检查: {new Date(health.timestamp * 1000).toLocaleString()}
              </div>
            </div>
          )}
        </GlassCard>

        {/* 
          ============================================
          通用设置卡片
          ============================================
        */}
        <GlassCard>
          <div className="flex items-center gap-3 mb-6">
            <IconBackground gradient="from-amber-400 to-orange-500">
              <Zap className="w-6 h-6" />
            </IconBackground>
            <div>
              <h3 className="font-semibold text-foreground">通用设置</h3>
              <p className="text-xs text-muted-foreground">应用程序行为</p>
            </div>
          </div>

          <div className="space-y-3">
            <SwitchSetting
              id="auto-refresh"
              label="自动刷新"
              description="每30秒自动检查服务状态"
              checked={settings.autoRefresh}
              onCheckedChange={(checked) => updateSetting("autoRefresh", checked)}
              icon={RefreshCw}
            />
            
            <div className="p-4 rounded-xl bg-secondary/30 border border-border/30">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-400 to-cyan-500 flex items-center justify-center shadow-md shadow-cyan-500/20">
                  <Sparkles className="w-5 h-5 text-white" />
                </div>
                <div>
                  <div className="text-sm font-semibold text-foreground/90">智能缓存</div>
                  <p className="text-xs text-muted-foreground">自动缓存频繁访问的数据</p>
                </div>
              </div>
            </div>
          </div>
        </GlassCard>

        {/* 
          ============================================
          关于卡片
          ============================================
        */}
        <GlassCard>
          <div className="flex items-center gap-3 mb-6">
            <IconBackground gradient="from-pink-400 to-rose-500">
              <Shield className="w-6 h-6" />
            </IconBackground>
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <h3 className="font-semibold text-foreground">关于</h3>
                <Badge 
                  variant="secondary" 
                  className="bg-gradient-to-r from-indigo-500/10 to-purple-500/10 text-indigo-600 dark:text-indigo-400 border-0 text-[10px]"
                >
                  v1.0.0
                </Badge>
              </div>
              <p className="text-xs text-muted-foreground">Yijie STRM Gateway</p>
            </div>
          </div>

          {/* 信息网格 */}
          <div className="grid grid-cols-2 gap-3 mb-4">
            <div className="p-3 rounded-xl bg-secondary/30 border border-border/30 text-center">
              <Layers className="w-5 h-5 mx-auto mb-1.5 text-indigo-500" />
              <div className="text-xs font-medium text-foreground/80">Next.js 14</div>
            </div>
            <div className="p-3 rounded-xl bg-secondary/30 border border-border/30 text-center">
              <Code2 className="w-5 h-5 mx-auto mb-1.5 text-purple-500" />
              <div className="text-xs font-medium text-foreground/80">shadcn/ui</div>
            </div>
            <div className="p-3 rounded-xl bg-secondary/30 border border-border/30 text-center">
              <Cpu className="w-5 h-5 mx-auto mb-1.5 text-emerald-500" />
              <div className="text-xs font-medium text-foreground/80">Python</div>
            </div>
            <div className="p-3 rounded-xl bg-secondary/30 border border-border/30 text-center">
              <GitBranch className="w-5 h-5 mx-auto mb-1.5 text-amber-500" />
              <div className="text-xs font-medium text-foreground/80">lib115</div>
            </div>
          </div>

          {/* 技术栈标签 */}
          <div className="flex flex-wrap gap-1.5">
            {["React", "TypeScript", "Tailwind", "Radix UI"].map((tech) => (
              <Badge 
                key={tech}
                variant="outline" 
                className="text-[10px] px-2 py-0.5 rounded-md border-border/40 text-muted-foreground"
              >
                {tech}
              </Badge>
            ))}
          </div>
        </GlassCard>

        {/* 
          ============================================
          API 配置卡片 - 跨列
          ============================================
        */}
        <GlassCard className="md:col-span-2 lg:col-span-3">
          <div className="flex items-center gap-3 mb-6">
            <IconBackground gradient="from-blue-500 to-indigo-600">
              <Database className="w-6 h-6" />
            </IconBackground>
            <div>
              <h3 className="font-semibold text-foreground">API 配置</h3>
              <p className="text-xs text-muted-foreground">后端服务连接参数</p>
            </div>
          </div>

          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            <ModernInput
              id="api-base-url"
              label="API 基础 URL"
              value={settings.apiBaseUrl}
              onChange={(value) => updateSetting("apiBaseUrl", value)}
              placeholder="http://localhost:8115"
              description="后端 API 服务的完整地址"
            />

            <ModernInput
              id="strm-base-url"
              label="STRM 基础 URL"
              value={settings.strmBaseUrl}
              onChange={(value) => updateSetting("strmBaseUrl", value)}
              placeholder="留空则使用 API 基础 URL"
              description="STRM 文件中使用的流媒体服务地址"
            />

            <ModernInput
              id="cache-ttl"
              label="缓存时间 (秒)"
              type="number"
              value={settings.cacheTtl}
              onChange={(value) => updateSetting("cacheTtl", value)}
              placeholder="3600"
              description="API 响应缓存的有效期"
            />
          </div>
        </GlassCard>
      </div>

      {/* 保存成功提示 */}
      <SaveSuccessToast show={showSuccess} />
    </div>
  )
}
