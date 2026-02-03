"use client"

import { useState, useEffect } from "react"
import {
  FolderOpen,
  Settings,
  Menu,
  X,
  Cloud,
  HardDrive,
  Clock,
  Sun,
  Moon,
  ChevronRight,
  Database,
} from "lucide-react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { cn } from "@/lib/utils"

// Theme type
type Theme = "light" | "dark"

// Navigation item type
interface NavItem {
  id: string
  label: string
  href: string
  icon: React.ElementType
  color: string
  bgColor: string
  gradient: string
}

const navItems: NavItem[] = [
  {
    id: "browser",
    label: "文件浏览",
    href: "/dashboard/browser",
    icon: FolderOpen,
    color: "text-blue-500",
    bgColor: "bg-blue-500/10",
    gradient: "from-blue-500/20 to-cyan-500/20",
  },
  {
    id: "drives",
    label: "网盘管理",
    href: "/dashboard/drives",
    icon: HardDrive,
    color: "text-emerald-500",
    bgColor: "bg-emerald-500/10",
    gradient: "from-emerald-500/20 to-teal-500/20",
  },
  {
    id: "tasks",
    label: "任务管理",
    href: "/dashboard/tasks",
    icon: Clock,
    color: "text-amber-500",
    bgColor: "bg-amber-500/10",
    gradient: "from-amber-500/20 to-orange-500/20",
  },
  {
    id: "records",
    label: "记录管理",
    href: "/dashboard/records",
    icon: Database,
    color: "text-indigo-500",
    bgColor: "bg-indigo-500/10",
    gradient: "from-indigo-500/20 to-purple-500/20",
  },
  {
    id: "settings",
    label: "设置",
    href: "/dashboard/settings",
    icon: Settings,
    color: "text-purple-500",
    bgColor: "bg-purple-500/10",
    gradient: "from-purple-500/20 to-pink-500/20",
  },
]

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const pathname = usePathname()
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [theme, setTheme] = useState<Theme>("light")
  const [mounted, setMounted] = useState(false)

  // Initialize theme from localStorage
  useEffect(() => {
    setMounted(true)
    const savedTheme = localStorage.getItem("theme") as Theme
    if (savedTheme) {
      setTheme(savedTheme)
      document.documentElement.classList.toggle("dark", savedTheme === "dark")
    } else if (window.matchMedia("(prefers-color-scheme: dark)").matches) {
      setTheme("dark")
      document.documentElement.classList.add("dark")
    }
  }, [])

  // Toggle theme
  const toggleTheme = () => {
    const newTheme = theme === "light" ? "dark" : "light"
    setTheme(newTheme)
    localStorage.setItem("theme", newTheme)
    document.documentElement.classList.toggle("dark", newTheme === "dark")
  }

  const currentNavItem = navItems.find((item) => pathname?.startsWith(item.href))

  // Prevent hydration mismatch
  if (!mounted) {
    return null
  }

  return (
    <div className="flex h-screen bg-background overflow-hidden">
      {/* Sidebar */}
      <aside
        className={cn(
          "flex flex-col border-r bg-card/80 backdrop-blur-xl transition-all duration-500 ease-out",
          "shadow-[4px_0_24px_rgba(0,0,0,0.02)] dark:shadow-[4px_0_24px_rgba(0,0,0,0.2)]",
          sidebarOpen ? "w-72" : "w-20"
        )}
      >
        {/* Logo */}
        <div className="flex items-center gap-4 px-5 py-5 border-b border-border/50">
          <div
            className={cn(
              "flex items-center justify-center w-11 h-11 rounded-xl",
              "bg-gradient-to-br from-primary/20 via-primary/10 to-primary/5",
              "shadow-lg shadow-primary/10 ring-1 ring-primary/20",
              "transition-transform duration-300 hover:scale-105"
            )}
          >
            <Cloud className="h-6 w-6 text-primary" />
          </div>
          {sidebarOpen && (
            <div className="overflow-hidden animate-in fade-in slide-in-from-left-4 duration-500">
              <h1 className="font-bold text-lg tracking-tight">Yijie STRM</h1>
              <p className="text-xs text-muted-foreground font-medium">Gateway</p>
            </div>
          )}
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-4 space-y-1.5 overflow-y-auto">
          {navItems.map((item, index) => {
            const isActive = pathname?.startsWith(item.href)
            const Icon = item.icon

            return (
              <Link
                key={item.id}
                href={item.href}
                className={cn(
                  "group relative w-full flex items-center gap-3 px-3 py-3 rounded-xl",
                  "transition-all duration-300 ease-out",
                  "hover:scale-[1.02] active:scale-[0.98]",
                  isActive
                    ? cn(
                        "bg-gradient-to-r shadow-sm",
                        item.gradient,
                        "dark:shadow-lg dark:shadow-black/20"
                      )
                    : "hover:bg-accent/50 dark:hover:bg-accent/30"
                )}
                style={{
                  animationDelay: `${index * 50}ms`,
                }}
              >
                {/* Active indicator */}
                {isActive && (
                  <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-8 rounded-full bg-current opacity-60" />
                )}

                {/* Icon container */}
                <div
                  className={cn(
                    "flex items-center justify-center w-10 h-10 rounded-lg transition-all duration-300",
                    isActive
                      ? cn("bg-white/80 dark:bg-black/30 shadow-sm", item.color)
                      : cn(
                          "bg-muted/50 group-hover:bg-background",
                          "group-hover:shadow-sm",
                          item.color
                        )
                  )}
                >
                  <Icon className="h-5 w-5" />
                </div>

                {/* Label */}
                {sidebarOpen && (
                  <span
                    className={cn(
                      "font-medium text-sm transition-all duration-300",
                      isActive
                        ? "text-foreground"
                        : "text-muted-foreground group-hover:text-foreground"
                    )}
                  >
                    {item.label}
                  </span>
                )}

                {/* Active arrow */}
                {isActive && sidebarOpen && (
                  <ChevronRight className="ml-auto h-4 w-4 text-muted-foreground/50 animate-in fade-in slide-in-from-left-2" />
                )}
              </Link>
            )
          })}
        </nav>

        {/* Bottom section */}
        <div className="p-3 border-t border-border/50 space-y-2">
          {/* Theme toggle */}
          <button
            onClick={toggleTheme}
            className={cn(
              "w-full flex items-center gap-3 px-3 py-3 rounded-xl",
              "transition-all duration-300 ease-out",
              "hover:bg-accent/50 dark:hover:bg-accent/30",
              "hover:scale-[1.02] active:scale-[0.98]",
              !sidebarOpen && "justify-center px-2"
            )}
          >
            <div
              className={cn(
                "flex items-center justify-center w-10 h-10 rounded-lg",
                "bg-gradient-to-br from-orange-500/10 to-yellow-500/10",
                "dark:from-indigo-500/10 dark:to-purple-500/10",
                "transition-transform duration-500",
                theme === "dark" ? "rotate-180" : "rotate-0"
              )}
            >
              {theme === "light" ? (
                <Sun className="h-5 w-5 text-amber-500" />
              ) : (
                <Moon className="h-5 w-5 text-indigo-400" />
              )}
            </div>
            {sidebarOpen && (
              <span className="font-medium text-sm text-muted-foreground">
                {theme === "light" ? "浅色模式" : "深色模式"}
              </span>
            )}
          </button>

          {/* Sidebar toggle */}
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className={cn(
              "w-full flex items-center gap-3 px-3 py-2.5 rounded-xl",
              "bg-muted/50 hover:bg-muted",
              "transition-all duration-300 ease-out",
              "hover:scale-[1.02] active:scale-[0.98]",
              !sidebarOpen && "justify-center px-2"
            )}
          >
            <div className="flex items-center justify-center w-10 h-10 rounded-lg">
              {sidebarOpen ? (
                <X className="h-5 w-5 text-muted-foreground transition-transform duration-300" />
              ) : (
                <Menu className="h-5 w-5 text-muted-foreground transition-transform duration-300" />
              )}
            </div>
            {sidebarOpen && (
              <span className="text-sm text-muted-foreground">收起侧边栏</span>
            )}
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col overflow-hidden bg-background">
        {/* Header */}
        <header
          className={cn(
            "flex items-center justify-between px-6 py-4",
            "bg-card/60 backdrop-blur-xl border-b border-border/50",
            "sticky top-0 z-10"
          )}
        >
          {/* Left: Breadcrumb and Title */}
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Cloud className="h-4 w-4 text-primary/60" />
              <Link href="/dashboard/browser" className="hover:text-foreground transition-colors">
                首页
              </Link>
              <ChevronRight className="h-3.5 w-3.5" />
              <span className="text-foreground font-medium">
                {currentNavItem?.label}
              </span>
            </div>
          </div>

          {/* Right: Title with icon */}
          <div className="flex items-center gap-3">
            {currentNavItem && (
              <div
                className={cn(
                  "flex items-center gap-3 px-4 py-2 rounded-xl",
                  "bg-gradient-to-r from-muted/80 to-muted/40",
                  "border border-border/50 shadow-sm"
                )}
              >
                <div
                  className={cn(
                    "flex items-center justify-center w-8 h-8 rounded-lg",
                    currentNavItem.bgColor
                  )}
                >
                  <currentNavItem.icon
                    className={cn("h-4 w-4", currentNavItem.color)}
                  />
                </div>
                <h2 className="text-base font-semibold tracking-tight">
                  {currentNavItem.label}
                </h2>
              </div>
            )}
          </div>
        </header>

        {/* Content */}
        <div className="flex-1 overflow-auto p-6">
          {children}
        </div>
      </main>
    </div>
  )
}
