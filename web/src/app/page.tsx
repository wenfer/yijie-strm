"use client"

import { useState } from "react"
import {
  FolderOpen,
  FileVideo,
  Settings,
  Menu,
  X,
  Cloud,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { FileBrowser } from "@/components/file-browser"
import { StrmManager } from "@/components/strm-manager"
import { SettingsPanel } from "@/components/settings-panel"
import { cn } from "@/lib/utils"

export default function Home() {
  const [activeTab, setActiveTab] = useState("browser")
  const [sidebarOpen, setSidebarOpen] = useState(true)

  const navItems = [
    { id: "browser", label: "文件浏览", icon: FolderOpen },
    { id: "strm", label: "STRM 管理", icon: FileVideo },
    { id: "settings", label: "设置", icon: Settings },
  ]

  return (
    <div className="flex h-screen bg-background">
      {/* Sidebar */}
      <aside
        className={cn(
          "flex flex-col border-r bg-card transition-all duration-300",
          sidebarOpen ? "w-64" : "w-16"
        )}
      >
        {/* Logo */}
        <div className="flex items-center gap-3 p-4 border-b">
          <Cloud className="h-8 w-8 text-primary flex-shrink-0" />
          {sidebarOpen && (
            <div className="overflow-hidden">
              <h1 className="font-bold text-lg">115 STRM</h1>
              <p className="text-xs text-muted-foreground">Gateway</p>
            </div>
          )}
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-2 space-y-1">
          {navItems.map((item) => (
            <Button
              key={item.id}
              variant={activeTab === item.id ? "secondary" : "ghost"}
              className={cn(
                "w-full justify-start gap-3",
                !sidebarOpen && "justify-center px-2"
              )}
              onClick={() => setActiveTab(item.id)}
            >
              <item.icon className="h-5 w-5 flex-shrink-0" />
              {sidebarOpen && <span>{item.label}</span>}
            </Button>
          ))}
        </nav>

        {/* Toggle Button */}
        <div className="p-2 border-t">
          <Button
            variant="ghost"
            size="icon"
            className="w-full"
            onClick={() => setSidebarOpen(!sidebarOpen)}
          >
            {sidebarOpen ? (
              <X className="h-5 w-5" />
            ) : (
              <Menu className="h-5 w-5" />
            )}
          </Button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <header className="flex items-center justify-between px-6 py-4 border-b">
          <h2 className="text-xl font-semibold">
            {navItems.find((item) => item.id === activeTab)?.label}
          </h2>
        </header>

        {/* Content */}
        <div className="flex-1 overflow-auto">
          {activeTab === "browser" && <FileBrowser />}
          {activeTab === "strm" && <StrmManager />}
          {activeTab === "settings" && <SettingsPanel />}
        </div>
      </main>
    </div>
  )
}
