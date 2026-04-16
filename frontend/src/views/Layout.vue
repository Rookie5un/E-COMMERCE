<template>
  <div class="app-shell">
    <aside v-if="!isMobile" class="sidebar" :class="{ collapsed }">
      <div class="sidebar-logo">
        <div class="logo-mark" aria-hidden="true">
          <svg width="30" height="30" viewBox="0 0 40 40" fill="none">
            <rect width="40" height="40" rx="9" fill="#2563EB" />
            <path d="M8 28 L20 12 L32 28" stroke="#ffffff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" fill="none" />
            <path d="M14 22 L20 14 L26 22" stroke="#93C5FD" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none" opacity="0.85" />
          </svg>
        </div>
        <transition name="fade">
          <div v-if="!collapsed" class="logo-text">
            <span class="logo-name">ECommerce Insight</span>
            <span class="logo-version">review analytics</span>
          </div>
        </transition>
      </div>

      <nav class="sidebar-nav">
        <router-link
          v-for="item in menuItems"
          :key="item.path"
          :to="item.path"
          class="nav-item"
          :class="{ active: activeMenu === item.path }"
        >
          <span class="nav-icon">
            <el-icon><component :is="item.icon" /></el-icon>
          </span>
          <transition name="fade">
            <span v-if="!collapsed" class="nav-label">{{ item.label }}</span>
          </transition>
        </router-link>
      </nav>

      <div class="sidebar-footer">
        <div v-if="!collapsed" class="user-card">
          <div class="user-avatar">{{ userInitial }}</div>
          <div class="user-meta">
            <div class="user-name">{{ authStore.user?.username || '用户' }}</div>
            <div class="user-role">运营工作台</div>
          </div>
          <button class="icon-btn" type="button" title="退出登录" @click="handleLogout">
            <el-icon><SwitchButton /></el-icon>
          </button>
        </div>

        <button v-else class="icon-btn full" type="button" title="退出登录" @click="handleLogout">
          <el-icon><SwitchButton /></el-icon>
        </button>

        <button
          class="collapse-btn"
          type="button"
          :title="collapsed ? '展开侧栏' : '收起侧栏'"
          @click="collapsed = !collapsed"
        >
          <el-icon>
            <Expand v-if="collapsed" />
            <Fold v-else />
          </el-icon>
        </button>
      </div>
    </aside>

    <div class="main-area">
      <header class="topbar page-block block-delay-1">
        <div class="topbar-left">
          <button v-if="isMobile" class="menu-trigger" type="button" @click="mobileNavVisible = true">
            <el-icon><Menu /></el-icon>
          </button>

          <div class="breadcrumb">
            <span class="breadcrumb-icon">
              <el-icon><component :is="currentMenu?.icon || DataAnalysis" /></el-icon>
            </span>
            <div class="breadcrumb-copy">
              <span class="breadcrumb-label">{{ pageTitle }}</span>
              <span class="breadcrumb-note">{{ pageNote }}</span>
            </div>
          </div>
        </div>

        <div class="topbar-right">
          <div class="topbar-time">{{ todayLabel }} {{ currentTime }}</div>
          <div class="topbar-status">
            <span class="status-dot"></span>
            <span>系统运行中</span>
          </div>
          <el-dropdown trigger="click" @command="handleCommand">
            <button class="user-button" type="button">
              <el-icon><User /></el-icon>
              <span>{{ authStore.user?.username || '用户' }}</span>
            </button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>

      <main ref="pageContentRef" class="page-content">
        <transition name="route-fade" mode="out-in">
          <router-view :key="route.path" />
        </transition>
      </main>
    </div>

    <el-drawer
      v-model="mobileNavVisible"
      direction="ltr"
      size="260px"
      :with-header="false"
      class="mobile-drawer"
    >
      <div class="mobile-brand">
        <p class="mobile-brand-kicker">ECommerce Insight</p>
        <h3>评论分析平台</h3>
      </div>

      <nav class="mobile-nav">
        <router-link
          v-for="item in menuItems"
          :key="item.path"
          :to="item.path"
          class="mobile-nav-item"
          :class="{ active: activeMenu === item.path }"
          @click="handleMobileMenu"
        >
          <span class="nav-icon">
            <el-icon><component :is="item.icon" /></el-icon>
          </span>
          <span>{{ item.label }}</span>
        </router-link>
      </nav>

      <button class="mobile-logout" type="button" @click="handleLogout">
        <el-icon><SwitchButton /></el-icon>
        退出登录
      </button>
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/store/auth'
import { ElMessage, ElNotification } from 'element-plus'
import { getAnalysisRuns } from '@/api/analysis'
import {
  DataAnalysis,
  Box,
  Upload,
  ChatLineRound,
  List,
  Document,
  User,
  Menu,
  Fold,
  Expand,
  SwitchButton
} from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const collapsed = ref(false)
const mobileNavVisible = ref(false)
const isMobile = ref(false)
const currentTime = ref('')
const pageContentRef = ref(null)

const menuItems = [
  { path: '/dashboard', label: '分析总览', icon: DataAnalysis },
  { path: '/products', label: '商品管理', icon: Box },
  { path: '/import', label: '数据导入', icon: Upload },
  { path: '/reviews', label: '评论管理', icon: ChatLineRound },
  { path: '/tasks', label: '任务管理', icon: List },
  { path: '/reports', label: '分析报告', icon: Document }
]

const pageNotes = {
  Dashboard: '查看当前商品口碑与问题分布。',
  Products: '维护商品档案并管理分析任务。',
  ProductDetail: '跟踪单商品分析进度和结果。',
  Import: '管理评论数据导入批次与状态。',
  Reviews: '筛选评论并执行软删除与恢复。',
  Tasks: '统一管理分析任务与重试取消。',
  Reports: '汇总报告并支持下载复盘。'
}

const activeMenu = computed(() => {
  if (route.path.startsWith('/products/')) return '/products'
  return route.path
})

const currentMenu = computed(() => menuItems.find(item => item.path === activeMenu.value))

const pageTitle = computed(() => route.meta.title || currentMenu.value?.label || '运营工作台')
const pageNote = computed(() => pageNotes[route.name] || '执行评论数据运营与分析流程。')

const todayLabel = computed(() => {
  return new Date().toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  })
})

const userInitial = computed(() => (authStore.user?.username?.[0] ?? 'U').toUpperCase())

let timer = null
let progressPollTimer = null
let progressCacheInitialized = false
const runProgressCache = new Map()
let maxSeenRunId = 0
const PROGRESS_POLL_INTERVAL = 2000

const RUN_STAGE_LABELS = {
  queued: '排队中',
  starting: '初始化',
  sentiment: '情感分析',
  aspects: '功能点提取',
  issues: '问题挖掘',
  completed: '已完成',
  failed: '失败',
  canceled: '已取消'
}

const updateTime = () => {
  currentTime.value = new Date().toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

const updateViewport = () => {
  if (typeof window === 'undefined') return
  isMobile.value = window.innerWidth <= 1080
  if (!isMobile.value) {
    mobileNavVisible.value = false
  }
}

const handleMobileMenu = () => {
  mobileNavVisible.value = false
}

const handleLogout = () => {
  authStore.logout()
  ElMessage.success('已退出登录')
  router.push('/login')
}

const handleCommand = (command) => {
  if (command === 'logout') {
    handleLogout()
  }
}

const getRunProgressKey = (run) => {
  return `${run.status || ''}:${run.progress_stage || ''}:${run.progress_updated_at || ''}`
}

const getRunNotifyType = (run) => {
  if (run.status === 'completed') return 'success'
  if (run.status === 'failed') return 'error'
  if (run.status === 'canceled') return 'warning'
  return 'info'
}

const getRunStageLabel = (run) => {
  return RUN_STAGE_LABELS[run.progress_stage] || RUN_STAGE_LABELS[run.status] || '新阶段'
}

const notifyRunProgress = (run) => {
  const stageLabel = getRunStageLabel(run)
  const baseMessage = `任务 #${run.id} 进入「${stageLabel}」阶段`
  ElNotification({
    title: '任务阶段更新',
    message: run.progress_message ? `${baseMessage}：${run.progress_message}` : baseMessage,
    position: 'top-right',
    type: getRunNotifyType(run),
    duration: 4500,
    showClose: true
  })
}

const pollRunProgress = async () => {
  if (!authStore.isAuthenticated || route.path === '/login') return

  try {
    const res = await getAnalysisRuns({ page: 1, per_page: 50 })
    const runs = res?.runs || []
    const latestIds = new Set()
    let currentMaxRunId = maxSeenRunId

    runs.forEach((run) => {
      latestIds.add(run.id)
      if (typeof run.id === 'number') {
        currentMaxRunId = Math.max(currentMaxRunId, run.id)
      }
      const nextKey = getRunProgressKey(run)
      const prevKey = runProgressCache.get(run.id)

      if (progressCacheInitialized) {
        if (prevKey && prevKey !== nextKey) {
          notifyRunProgress(run)
        } else if (!prevKey && typeof run.id === 'number' && run.id > maxSeenRunId) {
          // 新任务首次进入列表时，立即提示当前阶段
          notifyRunProgress(run)
        }
      }

      runProgressCache.set(run.id, nextKey)
    })

    Array.from(runProgressCache.keys()).forEach((runId) => {
      if (!latestIds.has(runId)) {
        runProgressCache.delete(runId)
      }
    })

    maxSeenRunId = currentMaxRunId
    progressCacheInitialized = true
  } catch (error) {
    // 忽略轮询错误，避免打断页面主流程
  }
}

const startProgressPolling = () => {
  if (progressPollTimer) return
  pollRunProgress()
  progressPollTimer = window.setInterval(pollRunProgress, PROGRESS_POLL_INTERVAL)
}

const stopProgressPolling = () => {
  if (progressPollTimer) {
    clearInterval(progressPollTimer)
    progressPollTimer = null
  }
  runProgressCache.clear()
  progressCacheInitialized = false
  maxSeenRunId = 0
}

watch(
  () => route.path,
  () => {
    mobileNavVisible.value = false
    if (authStore.isAuthenticated && !progressPollTimer) {
      startProgressPolling()
    }
  }
)

watch(
  () => authStore.isAuthenticated,
  (isAuthenticated) => {
    if (isAuthenticated) {
      startProgressPolling()
    } else {
      stopProgressPolling()
    }
  }
)

watch(
  () => route.fullPath,
  async () => {
    await nextTick()
    if (pageContentRef.value) {
      pageContentRef.value.scrollTop = 0
      pageContentRef.value.scrollLeft = 0
    }
  }
)

onMounted(() => {
  updateTime()
  updateViewport()
  timer = window.setInterval(updateTime, 1000)
  window.addEventListener('resize', updateViewport)
  if (authStore.isAuthenticated) {
    startProgressPolling()
  }
})

onBeforeUnmount(() => {
  if (timer) {
    clearInterval(timer)
  }
  stopProgressPolling()
  window.removeEventListener('resize', updateViewport)
})
</script>

<style scoped>
.app-shell {
  display: flex;
  height: 100vh;
  min-height: 100vh;
  overflow: hidden;
  background: var(--bg-base);
}

.sidebar {
  width: var(--sidebar-w);
  height: 100vh;
  flex-shrink: 0;
  border-right: 1px solid var(--border-default);
  background: var(--bg-surface);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transition: width 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.sidebar.collapsed {
  width: var(--sidebar-collapsed);
}

.sidebar-logo {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 62px;
  padding: 15px 14px;
  border-bottom: 1px solid var(--border-subtle);
  background: #ffffff;
}

.logo-text {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.logo-name {
  font-size: 14px;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.01em;
  white-space: nowrap;
}

.logo-version {
  margin-top: 1px;
  font-size: 10px;
  color: var(--accent);
  font-family: 'DM Mono', monospace;
}

.sidebar-nav {
  flex: 1;
  min-height: 0;
  padding: 10px 8px;
  overflow-y: auto;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 38px;
  margin-bottom: 3px;
  border-radius: var(--radius-sm);
  padding: 8px 12px;
  text-decoration: none;
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 500;
  transition: all 0.15s ease;
  position: relative;
  overflow: hidden;
}

.nav-item:hover {
  background: var(--bg-highlight);
  color: var(--accent);
}

.nav-item.active {
  background: var(--accent-dim);
  color: var(--accent);
  font-weight: 600;
}

.nav-item.active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 6px;
  bottom: 6px;
  width: 3px;
  border-radius: 0 3px 3px 0;
  background: var(--accent);
}

.nav-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  flex-shrink: 0;
}

.nav-label {
  white-space: nowrap;
}

.sidebar-footer {
  padding: 10px 8px;
  border-top: 1px solid var(--border-subtle);
  display: flex;
  align-items: center;
  gap: 6px;
  background: #ffffff;
}

.user-card {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 8px;
  overflow: hidden;
}

.user-avatar {
  width: 30px;
  height: 30px;
  flex-shrink: 0;
  border-radius: 8px;
  background: linear-gradient(135deg, #2563eb, #0891b2);
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  font-family: 'DM Mono', monospace;
}

.user-meta {
  flex: 1;
  overflow: hidden;
}

.user-name {
  font-size: 12px;
  color: var(--text-primary);
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.user-role {
  font-size: 10px;
  color: var(--accent);
  font-family: 'DM Mono', monospace;
}

.icon-btn,
.collapse-btn {
  border: none;
  background: none;
  color: var(--text-muted);
  width: 28px;
  height: 28px;
  border-radius: 6px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.15s ease;
}

.icon-btn:hover {
  color: var(--neg);
  background: var(--neg-dim);
}

.icon-btn.full {
  width: calc(100% - 34px);
}

.collapse-btn:hover {
  color: var(--text-primary);
  background: var(--bg-highlight);
}

.main-area {
  flex: 1;
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.topbar {
  min-height: var(--topbar-h);
  border-bottom: 1px solid var(--border-default);
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(8px);
  padding: 0 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.topbar-left {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.menu-trigger {
  border: 1px solid var(--border-default);
  background: var(--bg-surface);
  color: var(--text-primary);
  border-radius: 8px;
  width: 34px;
  height: 34px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.breadcrumb {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.breadcrumb-icon {
  width: 26px;
  height: 26px;
  border-radius: 8px;
  background: var(--accent-dim);
  color: var(--accent);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.breadcrumb-copy {
  display: grid;
  gap: 1px;
  min-width: 0;
}

.breadcrumb-label {
  font-size: 14px;
  font-weight: 700;
  color: var(--text-primary);
  white-space: nowrap;
}

.breadcrumb-note {
  font-size: 11px;
  color: var(--text-muted);
  white-space: nowrap;
}

.topbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.topbar-time {
  font-family: 'DM Mono', monospace;
  color: var(--text-muted);
  font-size: 11px;
  letter-spacing: 0.03em;
}

.topbar-status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: var(--text-muted);
  font-family: 'DM Mono', monospace;
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--pos);
  box-shadow: 0 0 6px rgba(22, 163, 74, 0.6);
  animation: pulse 2s ease-in-out infinite;
}

.user-button {
  border: 1px solid var(--border-default);
  border-radius: 999px;
  background: var(--bg-surface);
  min-height: 34px;
  padding: 0 12px;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  color: var(--text-primary);
  cursor: pointer;
}

.user-button:hover {
  border-color: var(--border-strong);
}

.page-content {
  flex: 1;
  min-width: 0;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  background: #f8fafc;
}

.mobile-brand {
  border: 1px solid var(--border-default);
  border-radius: 12px;
  background: var(--bg-overlay);
  padding: 12px;
  margin-bottom: 12px;
}

.mobile-brand-kicker {
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.16em;
  color: var(--text-muted);
}

.mobile-brand h3 {
  margin-top: 6px;
  font-size: 18px;
  line-height: 1.15;
}

.mobile-nav {
  display: grid;
  gap: 4px;
}

.mobile-nav-item {
  min-height: 40px;
  border-radius: 8px;
  padding: 8px 10px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: var(--text-secondary);
  text-decoration: none;
  font-size: 13px;
  font-weight: 500;
}

.mobile-nav-item.active {
  background: var(--accent-dim);
  color: var(--accent);
}

.mobile-logout {
  margin-top: 12px;
  width: 100%;
  min-height: 38px;
  border-radius: 8px;
  border: 1px solid rgba(220, 38, 38, 0.28);
  background: var(--neg-dim);
  color: var(--neg);
  font-size: 13px;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

@keyframes pulse {
  0%,
  100% {
    opacity: 1;
  }

  50% {
    opacity: 0.45;
  }
}

@media (max-width: 1080px) {
  .topbar {
    padding: 0 12px;
  }

  .breadcrumb-note,
  .topbar-time {
    display: none;
  }

  .topbar-right {
    gap: 8px;
  }
}

@media (max-width: 680px) {
  .topbar-status {
    display: none;
  }

  .user-button span {
    display: none;
  }

  .user-button {
    padding: 0;
    width: 34px;
    justify-content: center;
  }
}
</style>
