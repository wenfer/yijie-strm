/**
 * 115 STRM Gateway API 客户端
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8115'

export interface ApiResponse<T = any> {
  success?: boolean
  error?: string
  status?: number
  data?: T
  [key: string]: any
}

export interface QRCodeResponse {
  success: boolean
  qrcode_url: string
  uid: string
  time: string
  sign: string
  code_verifier: string
}

export interface AuthStatusResponse {
  success: boolean
  status: number // 1=未扫描, 2=已扫描
  message: string
}

export interface AuthExchangeResponse {
  success: boolean
  message: string
  access_token: string
  expires_in: number
}

export interface HealthResponse {
  status: string
  timestamp: number
  authenticated: boolean
  token_valid: boolean
}

export interface Drive {
  drive_id: string
  name: string
  drive_type: string
  token_file: string
  created_at: number
  last_used: number
  is_authenticated: boolean
  is_current: boolean
}

export interface DrivesListResponse {
  success: boolean
  drives: Drive[]
}

export interface FileItem {
  id: string
  name: string
  size: number
  pick_code: string
  is_folder: boolean
  parent_id: string
}

export interface FileListResponse {
  cid: string
  total: number
  offset: number
  limit: number
  items: FileItem[]
}

/**
 * 通用 API 请求函数
 */
async function request<T = any>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`

  // 添加超时控制
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), 10000) // 10秒超时

  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
      signal: controller.signal,
    })

    clearTimeout(timeoutId)

    if (!response.ok) {
      const error = await response.json().catch(() => ({ error: response.statusText }))
      throw new Error(error.error || `HTTP ${response.status}`)
    }

    return await response.json()
  } catch (error) {
    clearTimeout(timeoutId)
    if (error instanceof Error && error.name === 'AbortError') {
      throw new Error('请求超时，请检查后端服务是否正常运行')
    }
    console.error('API request failed:', error)
    throw error
  }
}

/**
 * 健康检查
 */
export async function checkHealth(): Promise<HealthResponse> {
  return request<HealthResponse>('/health')
}

/**
 * 获取认证二维码
 */
export async function getAuthQRCode(): Promise<QRCodeResponse> {
  return request<QRCodeResponse>('/api/auth/qrcode')
}

/**
 * 检查认证状态
 */
export async function checkAuthStatus(
  uid: string,
  time: string,
  sign: string
): Promise<AuthStatusResponse> {
  const params = new URLSearchParams({ uid, time, sign })
  return request<AuthStatusResponse>(`/api/auth/status?${params}`)
}

/**
 * 交换 Token
 */
export async function exchangeToken(
  uid: string,
  code_verifier: string,
  drive_id?: string
): Promise<AuthExchangeResponse> {
  return request<AuthExchangeResponse>('/api/auth/exchange', {
    method: 'POST',
    body: JSON.stringify({ uid, code_verifier, drive_id }),
  })
}

/**
 * 获取文件列表
 */
export async function listFiles(
  cid: string = '0',
  limit: number = 100,
  offset: number = 0
): Promise<FileListResponse> {
  const params = new URLSearchParams({
    cid,
    limit: limit.toString(),
    offset: offset.toString(),
  })
  return request<FileListResponse>(`/api/list?${params}`)
}

/**
 * 搜索文件
 */
export async function searchFiles(
  keyword: string,
  cid: string = '0',
  limit: number = 100,
  offset: number = 0
): Promise<FileListResponse> {
  const params = new URLSearchParams({
    keyword,
    cid,
    limit: limit.toString(),
    offset: offset.toString(),
  })
  return request<FileListResponse>(`/api/search?${params}`)
}

/**
 * 获取下载链接
 */
export async function getDownloadUrl(pick_code: string): Promise<{ pick_code: string; url: string }> {
  const params = new URLSearchParams({ pick_code })
  return request(`/api/download?${params}`)
}

/**
 * 获取流媒体 URL（用于播放）
 */
export function getStreamUrl(pick_code: string): string {
  return `${API_BASE_URL}/stream/${pick_code}`
}


/**
 * 获取网盘列表
 */
export async function listDrives(): Promise<DrivesListResponse> {
  return request<DrivesListResponse>('/api/drives')
}

/**
 * 添加网盘
 */
export async function addDrive(name: string, drive_type: string = '115'): Promise<{ success: boolean; drive: Drive }> {
  return request('/api/drives', {
    method: 'POST',
    body: JSON.stringify({ name, drive_type }),
  })
}

/**
 * 删除网盘
 */
export async function removeDrive(drive_id: string): Promise<{ success: boolean; message: string }> {
  return request('/api/drives/remove', {
    method: 'POST',
    body: JSON.stringify({ drive_id }),
  })
}

/**
 * 切换当前网盘
 */
export async function switchDrive(drive_id: string): Promise<{ success: boolean; message: string }> {
  return request('/api/drives/switch', {
    method: 'POST',
    body: JSON.stringify({ drive_id }),
  })
}

/**
 * 更新网盘信息
 */
export async function updateDrive(drive_id: string, name: string): Promise<{ success: boolean; message: string }> {
  return request('/api/drives/update', {
    method: 'POST',
    body: JSON.stringify({ drive_id, name }),
  })
}

/**
 * 任务管理类型定义
 */
export interface StrmTask {
  task_id: string
  task_name: string
  drive_id: string
  source_cid: string
  output_dir: string
  base_url?: string
  include_video: boolean
  include_audio: boolean
  custom_extensions?: string[]
  schedule_enabled: boolean
  schedule_type?: string
  schedule_config?: Record<string, any>
  watch_enabled: boolean
  watch_interval: number
  delete_orphans: boolean
  preserve_structure: boolean
  overwrite_strm: boolean
  status: string
  last_run_time?: number
  last_run_status?: string
  last_run_message?: string
  next_run_time?: number
  total_runs: number
  total_files_generated: number
  total_files: number
  current_file_index: number
  created_at: number
  updated_at: number
}

export interface TaskStatistics {
  task_id: string
  task_name: string
  status: string
  total_runs: number
  total_files_generated: number
  active_records: number
  last_run_time?: number
  last_run_status?: string
  last_run_message?: string
  last_log?: TaskLog
}

export interface TaskLog {
  log_id: string
  task_id: string
  start_time: number
  end_time?: number
  duration?: number
  status: string
  message?: string
  error_trace?: string
  files_scanned: number
  files_added: number
  files_updated: number
  files_deleted: number
  files_skipped: number
}

export interface StrmRecord {
  record_id: string
  task_id: string
  file_id: string
  pick_code: string
  file_name: string
  file_size?: number
  file_path?: string
  strm_path: string
  strm_content: string
  status: string
  created_at: number
  updated_at: number
}

export interface SchedulerStatus {
  running: boolean
  scheduled_tasks: number
  running_tasks: number
  watch_tasks: number
}

/**
 * 获取任务列表
 */
export async function listTasks(drive_id?: string): Promise<{ success: boolean; tasks: StrmTask[] }> {
  const params = drive_id ? new URLSearchParams({ drive_id }) : ''
  return request(`/api/tasks${params ? '?' + params : ''}`)
}

/**
 * 创建任务
 */
export async function createTask(taskData: Partial<StrmTask>): Promise<{ success: boolean; task: StrmTask }> {
  return request('/api/tasks', {
    method: 'POST',
    body: JSON.stringify(taskData),
  })
}

/**
 * 获取任务详情
 */
export async function getTask(task_id: string): Promise<{ success: boolean; task: StrmTask }> {
  return request(`/api/tasks/${task_id}`)
}

/**
 * 更新任务
 */
export async function updateTask(task_id: string, updates: Partial<StrmTask>): Promise<{ success: boolean; message: string }> {
  return request(`/api/tasks/${task_id}`, {
    method: 'POST',
    body: JSON.stringify(updates),
  })
}

/**
 * 删除任务
 */
export async function deleteTask(task_id: string): Promise<{ success: boolean; message: string }> {
  return request(`/api/tasks/${task_id}/delete`, {
    method: 'POST',
  })
}

/**
 * 手动执行任务
 */
export async function executeTask(task_id: string, force: boolean = false): Promise<{ success: boolean; message: string }> {
  return request(`/api/tasks/${task_id}/execute`, {
    method: 'POST',
    body: JSON.stringify({ force }),
  })
}

/**
 * 获取任务状态
 */
export async function getTaskStatus(task_id: string): Promise<{ success: boolean; status: string; last_run_time?: number; last_run_status?: string; last_run_message?: string; next_run_time?: number }> {
  return request(`/api/tasks/${task_id}/status`)
}

/**
 * 获取任务统计
 */
export async function getTaskStatistics(task_id: string): Promise<{ success: boolean; statistics: TaskStatistics }> {
  return request(`/api/tasks/${task_id}/statistics`)
}

/**
 * 获取任务日志
 */
export async function getTaskLogs(task_id: string, limit: number = 50): Promise<{ success: boolean; logs: TaskLog[] }> {
  const params = new URLSearchParams({ limit: limit.toString() })
  return request(`/api/tasks/${task_id}/logs?${params}`)
}

/**
 * 获取任务的 STRM 记录
 */
export async function getTaskRecords(task_id: string): Promise<{ success: boolean; records: StrmRecord[] }> {
  return request(`/api/tasks/${task_id}/records`)
}

/**
 * 获取调度器状态
 */
export async function getSchedulerStatus(): Promise<{ success: boolean; scheduler: SchedulerStatus }> {
  return request('/api/scheduler/status')
}

/**
 * 启动调度器
 */
export async function startScheduler(): Promise<{ success: boolean; message: string }> {
  return request('/api/scheduler/start', {
    method: 'POST',
  })
}

/**
 * 停止调度器
 */
export async function stopScheduler(): Promise<{ success: boolean; message: string }> {
  return request('/api/scheduler/stop', {
    method: 'POST',
  })
}

/**
 * API 命名空间对象（用于兼容旧的导入方式）
 */
export const api = {
  health: checkHealth,
  checkHealth,
  getAuthQRCode,
  checkAuthStatus,
  exchangeToken,
  listFiles,
  search: searchFiles,
  getDownloadUrl,
  getStreamUrl,
  listDrives,
  addDrive,
  removeDrive,
  switchDrive,
  updateDrive,
  listTasks,
  createTask,
  getTask,
  updateTask,
  deleteTask,
  executeTask,
  getTaskStatus,
  getTaskStatistics,
  getTaskLogs,
  getTaskRecords,
  getSchedulerStatus,
  startScheduler,
  stopScheduler,
}

export default api
