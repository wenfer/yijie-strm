/**
 * Yijie STRM Gateway API 客户端
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
  is_current: boolean
  is_authenticated?: boolean
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
  is_dir: boolean
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
  return request<HealthResponse>('/api/system/health')
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
  offset: number = 0,
  drive_id?: string
): Promise<FileListResponse> {
  const params = new URLSearchParams({
    cid,
    limit: limit.toString(),
    offset: offset.toString(),
  })
  if (drive_id) {
    params.append('drive_id', drive_id)
  }
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
export async function listDrives(): Promise<{ success: boolean; drives: Drive[] }> {
  return request('/api/drives')
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
  return request(`/api/drives/${drive_id}`, {
    method: 'DELETE',
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
  id: string
  name: string
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
  download_metadata: boolean
  status: string
  last_run_time?: string
  last_run_status?: string
  last_run_message?: string
  next_run_time?: string
  total_runs: number
  total_files_generated: number
  total_files: number
  current_file_index: number
  created_at?: string
  updated_at?: string
}

export interface TaskStatistics {
  id: string
  name: string
  status: string
  total_runs: number
  total_files_generated: number
  active_records: number
  last_run_time?: string
  last_run_status?: string
  last_run_message?: string
  last_log?: TaskLog
}

export interface TaskLog {
  id: string
  task_id: string
  start_time?: string
  end_time?: string
  duration?: number
  status: string
  message?: string
  error_trace?: string
  files_scanned: number
  files_added: number
  files_updated: number
  files_deleted: number
  files_skipped: number
  metadata_downloaded: number
  metadata_skipped: number
}

export interface StrmRecord {
  id: string
  task_id: string
  file_id: string
  pick_code?: string
  file_name: string
  file_size?: number
  file_path?: string
  strm_path: string
  strm_content: string
  status: string
  created_at?: string
  updated_at?: string
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
export async function getTask(id: string): Promise<{ success: boolean; task: StrmTask }> {
  return request(`/api/tasks/${id}`)
}

/**
 * 更新任务
 */
export async function updateTask(id: string, updates: Partial<StrmTask>): Promise<{ success: boolean; message: string }> {
  return request(`/api/tasks/${id}`, {
    method: 'POST',
    body: JSON.stringify(updates),
  })
}

/**
 * 删除任务
 */
export async function deleteTask(id: string): Promise<{ success: boolean; message: string }> {
  return request(`/api/tasks/${id}/delete`, {
    method: 'POST',
  })
}

/**
 * 手动执行任务
 */
export async function executeTask(id: string, force: boolean = false): Promise<{ success: boolean; message: string }> {
  return request(`/api/tasks/${id}/execute`, {
    method: 'POST',
    body: JSON.stringify({ force }),
  })
}

/**
 * 获取任务状态
 */
export async function getTaskStatus(id: string): Promise<{ success: boolean; status: string; last_run_time?: string; last_run_status?: string; last_run_message?: string; next_run_time?: string }> {
  return request(`/api/tasks/${id}/status`)
}

/**
 * 获取任务统计
 */
export async function getTaskStatistics(id: string): Promise<{ success: boolean; statistics: TaskStatistics }> {
  return request(`/api/tasks/${id}/statistics`)
}

/**
 * 获取任务日志
 */
export async function getTaskLogs(id: string, limit: number = 50): Promise<{ success: boolean; logs: TaskLog[] }> {
  const params = new URLSearchParams({ limit: limit.toString() })
  return request(`/api/tasks/${id}/logs?${params}`)
}

/**
 * 获取任务的 STRM 记录
 */
export async function getTaskRecords(
  task_id: string,
  keyword?: string,
  status?: string,
  limit: number = 1000,
  offset: number = 0
): Promise<{ success: boolean; records: StrmRecord[]; total: number; limit: number; offset: number }> {
  const params = new URLSearchParams({
    limit: limit.toString(),
    offset: offset.toString(),
  })
  if (keyword) params.append('keyword', keyword)
  if (status) params.append('status', status)
  return request(`/api/tasks/${task_id}/records?${params}`)
}

/**
 * 删除单个 STRM 记录
 */
export async function deleteTaskRecord(
  task_id: string,
  record_id: string,
  delete_file: boolean = true
): Promise<{ success: boolean; message: string }> {
  const params = new URLSearchParams()
  if (!delete_file) params.append('delete_file', 'false')
  return request(`/api/tasks/${task_id}/records/${record_id}?${params}`, {
    method: 'DELETE',
  })
}

/**
 * 批量删除 STRM 记录
 */
export async function batchDeleteTaskRecords(
  task_id: string,
  record_ids?: string[],
  delete_files: boolean = true
): Promise<{ success: boolean; message: string; deleted_count: number }> {
  return request(`/api/tasks/${task_id}/records/batch-delete`, {
    method: 'POST',
    body: JSON.stringify({ record_ids, delete_files }),
  })
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
 * 本地目录项
 */
export interface LocalDirItem {
  name: string
  path: string
}

/**
 * 浏览服务器本地目录
 */
export async function listLocalDirs(path: string = '/'): Promise<{
  success: boolean
  data: {
    current_path: string
    parent_path: string | null
    directories: LocalDirItem[]
  }
}> {
  const params = new URLSearchParams({ path })
  return request(`/api/system/directories?${params}`)
}

/**
 * 系统配置
 */
export interface SystemConfig {
  gateway: {
    host: string
    port: number
    debug: boolean
    strm_base_url?: string
    cache_ttl: number
    enable_cors: boolean
  }
  database: {
    url: string
    generate_schemas: boolean
    pool_min: number
    pool_max: number
  }
  log: {
    level: string
    format: string
  }
}

/**
 * 获取系统配置
 */
export async function getSystemConfig(): Promise<{ success: boolean; data: SystemConfig }> {
  return request('/api/system/config')
}

/**
 * 保存系统配置
 */
export async function saveSystemConfig(config: SystemConfig): Promise<{ success: boolean; message: string }> {
  return request('/api/system/config', {
    method: 'POST',
    body: JSON.stringify(config),
  })
}

/**
 * 获取系统日志
 */
export async function getSystemLogs(lines: number = 100): Promise<{ success: boolean; data: string[] }> {
  const params = new URLSearchParams({ lines: lines.toString() })
  return request(`/api/system/logs?${params}`)
}

/**
 * 挂载配置
 */
export interface Mount {
  id: string
  drive_id: string
  mount_point: string
  mount_config: Record<string, any>
  is_mounted: boolean
  created_at: number
}

/**
 * 获取挂载列表
 */
export async function listMounts(): Promise<Mount[]> {
  return request<Mount[]>('/api/mounts')
}

/**
 * 创建挂载点
 */
export async function createMount(data: {
  drive_id: string
  mount_point: string
  mount_config?: Record<string, any>
}): Promise<Mount> {
  return request<Mount>('/api/mounts', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

/**
 * 启动挂载
 */
export async function startMount(mount_id: string): Promise<{
  success: boolean;
  message: string;
  pid?: number;
  pending?: boolean;
  logs: { timestamp: string; level: string; message: string }[];
  error?: string;
}> {
  return request(`/api/mounts/${mount_id}/mount`, {
    method: 'POST',
  })
}

/**
 * 停止挂载
 */
export async function stopMount(mount_id: string): Promise<{
  success: boolean;
  message: string;
  logs: { timestamp: string; level: string; message: string }[];
}> {
  return request(`/api/mounts/${mount_id}/unmount`, {
    method: 'POST',
  })
}

/**
 * 获取挂载日志
 */
export async function getMountLogs(mount_id: string, limit: number = 100): Promise<{
  logs: { timestamp: string; level: string; message: string }[];
}> {
  return request(`/api/mounts/${mount_id}/logs?limit=${limit}`)
}

/**
 * 删除挂载配置
 */
export async function deleteMount(mount_id: string): Promise<{ success: boolean; message: string }> {
  return request(`/api/mounts/${mount_id}`, {
    method: 'DELETE',
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
  deleteTaskRecord,
  batchDeleteTaskRecords,
  getSchedulerStatus,
  startScheduler,
  stopScheduler,
  listLocalDirs,
  getSystemConfig,
  saveSystemConfig,
  getSystemLogs,
  listMounts,
  createMount,
  startMount,
  stopMount,
  deleteMount,
  getMountLogs,
}

export default api
