"use client"

import * as React from "react"
import { useState, useEffect } from "react"
import { motion } from "framer-motion"
import { Database, Loader2, AlertCircle } from "lucide-react"
import { RecordsManager } from "@/components/records-manager"
import { api, StrmTask, Drive } from "@/lib/api"

export default function RecordsPage() {
  const [tasks, setTasks] = useState<StrmTask[]>([])
  const [drives, setDrives] = useState<Drive[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const loadData = async () => {
      try {
        const [tasksResult, drivesResult] = await Promise.all([
          api.listTasks(),
          api.listDrives(),
        ])

        if (tasksResult.success) {
          setTasks(tasksResult.tasks)
        }
        if (drivesResult.success) {
          setDrives(drivesResult.drives)
        }
      } catch (err) {
        console.error("Failed to load data:", err)
        setError("加载数据失败")
      } finally {
        setLoading(false)
      }
    }

    loadData()
  }, [])

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px]">
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
        >
          <Loader2 className="h-10 w-10 text-primary" />
        </motion.div>
        <p className="text-muted-foreground mt-4">加载中...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] text-red-500">
        <AlertCircle className="h-12 w-12 mb-4" />
        <p className="text-lg font-medium">{error}</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between"
      >
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 text-white shadow-lg">
            <Database className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">STRM 记录管理</h1>
            <p className="text-sm text-muted-foreground">
              查看和管理已生成的 STRM 文件记录
            </p>
          </div>
        </div>
      </motion.div>

      {/* 记录管理组件 */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
      >
        <RecordsManager tasks={tasks} drives={drives} />
      </motion.div>
    </div>
  )
}
