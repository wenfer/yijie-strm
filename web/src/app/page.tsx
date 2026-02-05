"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { getCurrentUser } from "@/lib/api"
import { Loader2 } from "lucide-react"

export default function Home() {
  const router = useRouter()
  const [checking, setChecking] = useState(true)

  useEffect(() => {
    checkAuth()
  }, [])

  const checkAuth = async () => {
    try {
      const result = await getCurrentUser()
      if (result.success && result.data?.is_authenticated) {
        router.push("/dashboard/browser")
      } else {
        router.push("/login")
      }
    } catch (err) {
      router.push("/login")
    } finally {
      setChecking(false)
    }
  }

  if (checking) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    )
  }

  return null
}
