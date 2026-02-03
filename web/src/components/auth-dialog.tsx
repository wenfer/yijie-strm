"use client"

import * as React from "react"
import { useState, useEffect } from "react"
import { QRCodeSVG } from "qrcode.react"
import { motion, AnimatePresence } from "framer-motion"
import { Loader2, CheckCircle, XCircle, RefreshCw, Shield, Smartphone } from "lucide-react"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { api } from "@/lib/api"

interface AuthDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  driveId?: string
  driveName?: string
  onSuccess?: () => void
}

const statusConfig = {
  loading: {
    icon: Loader2,
    title: "正在准备",
    description: "正在获取认证二维码，请稍候...",
    color: "text-primary",
    bgColor: "bg-primary/10",
    animate: true,
  },
  qrcode: {
    icon: Smartphone,
    title: "扫码认证",
    description: "请使用 115 App 扫描二维码完成认证",
    color: "text-blue-500",
    bgColor: "bg-blue-500/10",
    animate: false,
  },
  scanning: {
    icon: Loader2,
    title: "正在认证",
    description: "扫码成功，正在完成认证流程...",
    color: "text-amber-500",
    bgColor: "bg-amber-500/10",
    animate: true,
  },
  success: {
    icon: CheckCircle,
    title: "认证成功",
    description: "您的 115 网盘已成功连接",
    color: "text-green-500",
    bgColor: "bg-green-500/10",
    animate: false,
  },
  error: {
    icon: XCircle,
    title: "认证失败",
    description: "认证过程中出现问题，请重试",
    color: "text-red-500",
    bgColor: "bg-red-500/10",
    animate: false,
  },
}

export function AuthDialog({
  open,
  onOpenChange,
  driveId,
  driveName,
  onSuccess,
}: AuthDialogProps) {
  const [qrcodeUrl, setQrcodeUrl] = useState<string>("")
  const [authParams, setAuthParams] = useState<{
    uid: string
    time: string
    sign: string
    code_verifier: string
  } | null>(null)
  const [status, setStatus] = useState<"loading" | "qrcode" | "scanning" | "success" | "error">("loading")
  const [errorMessage, setErrorMessage] = useState<string>("")

  useEffect(() => {
    if (open) {
      startAuth()
    } else {
      // 重置状态
      setQrcodeUrl("")
      setAuthParams(null)
      setStatus("loading")
      setErrorMessage("")
    }
  }, [open])

  const startAuth = async () => {
    try {
      setStatus("loading")
      const result = await api.getAuthQRCode()

      if (result.success) {
        setQrcodeUrl(result.qrcode_url)
        setAuthParams({
          uid: result.uid,
          time: result.time,
          sign: result.sign,
          code_verifier: result.code_verifier,
        })
        setStatus("qrcode")

        // 开始轮询检查扫码状态
        startPolling(result.uid, result.time, result.sign, result.code_verifier)
      } else {
        setStatus("error")
        setErrorMessage("获取二维码失败")
      }
    } catch (error) {
      console.error("Failed to get QR code:", error)
      setStatus("error")
      setErrorMessage("获取二维码失败: " + (error as Error).message)
    }
  }

  const startPolling = async (uid: string, time: string, sign: string, code_verifier: string) => {
    const maxAttempts = 60 // 最多轮询 60 次（5 分钟）
    let attempts = 0

    const poll = async () => {
      if (attempts >= maxAttempts) {
        setStatus("error")
        setErrorMessage("二维码已过期，请重新获取")
        return
      }

      try {
        const result = await api.checkAuthStatus(uid, time, sign)

        if (result.success && result.status === 2) {
          // 已扫码，开始交换 token
          setStatus("scanning")
          await exchangeToken(uid, code_verifier)
        } else {
          // 继续轮询
          attempts++
          setTimeout(poll, 5000) // 每 5 秒轮询一次
        }
      } catch (error) {
        console.error("Failed to check auth status:", error)
        attempts++
        setTimeout(poll, 5000)
      }
    }

    poll()
  }

  const exchangeToken = async (uid: string, code_verifier: string) => {
    try {
      const result = await api.exchangeToken(uid, code_verifier, driveId)

      if (result.success) {
        setStatus("success")
        setTimeout(() => {
          onOpenChange(false)
          if (onSuccess) {
            onSuccess()
          }
        }, 1500)
      } else {
        setStatus("error")
        setErrorMessage("认证失败")
      }
    } catch (error) {
      console.error("Failed to exchange token:", error)
      setStatus("error")
      setErrorMessage("认证失败: " + (error as Error).message)
    }
  }

  const config = statusConfig[status]
  const StatusIcon = config.icon

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md overflow-hidden rounded-2xl border-0 shadow-2xl bg-white/95 dark:bg-gray-900/95 backdrop-blur-xl">
        {/* 顶部装饰条 */}
        <div className="absolute top-0 left-0 right-0 h-1.5 bg-gradient-to-r from-blue-500 via-purple-500 to-pink-500" />
        
        <DialogHeader className="pt-4">
          <div className="flex items-center gap-3 mb-2">
            <div className={cn("p-2.5 rounded-xl transition-colors duration-300", config.bgColor)}>
              <Shield className={cn("h-6 w-6", config.color)} />
            </div>
            <div>
              <DialogTitle className="text-xl font-semibold tracking-tight">
                {driveName ? `认证 ${driveName}` : "115 网盘认证"}
              </DialogTitle>
              <DialogDescription className="text-sm text-muted-foreground mt-0.5">
                安全连接您的云存储服务
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <div className="flex flex-col items-center justify-center py-6">
          <AnimatePresence mode="wait">
            {status === "loading" && (
              <motion.div
                key="loading"
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.9 }}
                className="flex flex-col items-center gap-6"
              >
                <div className="relative">
                  <div className="absolute inset-0 bg-primary/20 rounded-full animate-ping" />
                  <div className="relative p-6 bg-primary/10 rounded-full">
                    <Loader2 className="h-12 w-12 animate-spin text-primary" />
                  </div>
                </div>
                <div className="text-center space-y-1">
                  <p className="font-medium text-foreground">正在获取二维码...</p>
                  <p className="text-sm text-muted-foreground">请稍候片刻</p>
                </div>
              </motion.div>
            )}

            {status === "qrcode" && qrcodeUrl && (
              <motion.div
                key="qrcode"
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.9 }}
                className="flex flex-col items-center gap-5"
              >
                {/* 二维码容器 */}
                <div className="relative p-1">
                  {/* 装饰性边框 */}
                  <div className="absolute inset-0 bg-gradient-to-br from-blue-500/30 via-purple-500/30 to-pink-500/30 rounded-3xl animate-pulse" />
                  <div className="absolute -inset-0.5 bg-gradient-to-br from-blue-500 via-purple-500 to-pink-500 rounded-3xl opacity-20 blur-sm" />
                  
                  <div className="relative p-5 bg-white rounded-2xl shadow-xl">
                    <QRCodeSVG 
                      value={qrcodeUrl} 
                      size={200} 
                      level="M"
                      includeMargin={false}
                    />
                    {/* 扫描线动画 */}
                    <motion.div
                      className="absolute inset-5 bg-gradient-to-b from-transparent via-blue-400/30 to-transparent"
                      animate={{ top: [20, 180, 20] }}
                      transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
                    />
                  </div>
                </div>
                
                {/* 状态指示 */}
                <div className="flex items-center gap-2 px-4 py-2 bg-blue-50 dark:bg-blue-950/50 rounded-full">
                  <span className="relative flex h-2.5 w-2.5">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75" />
                    <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-blue-500" />
                  </span>
                  <span className="text-sm font-medium text-blue-600 dark:text-blue-400">
                    等待扫码...
                  </span>
                </div>
                
                <div className="text-center space-y-1">
                  <p className="text-sm font-medium text-foreground">请使用 115 App 扫描二维码</p>
                  <p className="text-xs text-muted-foreground">打开 115 应用 → 点击右上角扫一扫</p>
                </div>
              </motion.div>
            )}

            {status === "scanning" && (
              <motion.div
                key="scanning"
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.9 }}
                className="flex flex-col items-center gap-6"
              >
                <div className="relative">
                  <div className="absolute inset-0 bg-amber-500/20 rounded-full animate-pulse" />
                  <div className="relative p-6 bg-amber-50 dark:bg-amber-950/50 rounded-full">
                    <Loader2 className="h-12 w-12 animate-spin text-amber-500" />
                  </div>
                </div>
                <div className="text-center space-y-1">
                  <p className="font-medium text-foreground">扫码成功</p>
                  <p className="text-sm text-muted-foreground">正在完成认证，请稍候...</p>
                </div>
              </motion.div>
            )}

            {status === "success" && (
              <motion.div
                key="success"
                initial={{ opacity: 0, scale: 0.5 }}
                animate={{ opacity: 1, scale: 1 }}
                className="flex flex-col items-center gap-6"
              >
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ type: "spring", stiffness: 200, damping: 15 }}
                  className="p-6 bg-green-50 dark:bg-green-950/50 rounded-full"
                >
                  <CheckCircle className="h-16 w-16 text-green-500" />
                </motion.div>
                <div className="text-center space-y-1">
                  <p className="text-xl font-semibold text-foreground">认证成功！</p>
                  <p className="text-sm text-muted-foreground">正在关闭窗口...</p>
                </div>
              </motion.div>
            )}

            {status === "error" && (
              <motion.div
                key="error"
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                className="flex flex-col items-center gap-5"
              >
                <div className="p-6 bg-red-50 dark:bg-red-950/50 rounded-full">
                  <XCircle className="h-12 w-12 text-red-500" />
                </div>
                <div className="text-center space-y-1 max-w-[280px]">
                  <p className="font-medium text-foreground">认证遇到问题</p>
                  <p className="text-sm text-red-500">{errorMessage}</p>
                </div>
                <Button
                  onClick={startAuth}
                  variant="outline"
                  className="gap-2"
                >
                  <RefreshCw className="h-4 w-4" />
                  重新获取二维码
                </Button>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </DialogContent>
    </Dialog>
  )
}
