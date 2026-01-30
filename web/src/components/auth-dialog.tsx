"use client"

import * as React from "react"
import { useState, useEffect } from "react"
import { QRCodeSVG } from "qrcode.react"
import { Loader2, CheckCircle, XCircle } from "lucide-react"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { api } from "@/lib/api"

interface AuthDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  driveId?: string
  driveName?: string
  onSuccess?: () => void
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

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>
            {driveName ? `认证 ${driveName}` : "115 网盘认证"}
          </DialogTitle>
          <DialogDescription>
            请使用 115 App 扫描二维码完成认证
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col items-center justify-center py-6 space-y-4">
          {status === "loading" && (
            <div className="flex flex-col items-center gap-4">
              <Loader2 className="h-12 w-12 animate-spin text-primary" />
              <p className="text-sm text-muted-foreground">正在获取二维码...</p>
            </div>
          )}

          {status === "qrcode" && qrcodeUrl && (
            <div className="flex flex-col items-center gap-4">
              <div className="p-4 bg-white rounded-lg">
                <QRCodeSVG value={qrcodeUrl} size={200} />
              </div>
              <p className="text-sm text-muted-foreground">请使用 115 App 扫描二维码</p>
            </div>
          )}

          {status === "scanning" && (
            <div className="flex flex-col items-center gap-4">
              <Loader2 className="h-12 w-12 animate-spin text-primary" />
              <p className="text-sm text-muted-foreground">正在完成认证...</p>
            </div>
          )}

          {status === "success" && (
            <div className="flex flex-col items-center gap-4">
              <CheckCircle className="h-12 w-12 text-green-500" />
              <p className="text-sm font-medium">认证成功！</p>
            </div>
          )}

          {status === "error" && (
            <div className="flex flex-col items-center gap-4">
              <XCircle className="h-12 w-12 text-red-500" />
              <p className="text-sm text-red-500">{errorMessage}</p>
              <button
                onClick={startAuth}
                className="text-sm text-primary hover:underline"
              >
                重新获取二维码
              </button>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
