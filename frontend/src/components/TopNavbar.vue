<template>
  <nav class="top-navbar">
    <div class="navbar-container">
      <!-- Left: Logo & Brand -->
      <div class="navbar-left">
        <div class="brand">
          <div class="brand-icon">
            <el-icon :size="24"><DataAnalysis /></el-icon>
          </div>
          <span class="brand-name">评论分析平台</span>
        </div>
      </div>

      <!-- Center: Navigation Menu -->
      <div class="navbar-center" v-if="!isMobile">
        <router-link
          v-for="item in menuItems"
          :key="item.path"
          :to="item.path"
          class="nav-item"
          :class="{ 'is-active': isActive(item.path) }"
        >
          <el-icon :size="20">
            <component :is="item.icon" />
          </el-icon>
          <span class="nav-label">{{ item.label }}</span>
        </router-link>
      </div>

      <!-- Right: Status, Time, User -->
      <div class="navbar-right">
        <!-- System Status -->
        <div class="status-indicator" v-if="!isMobile">
          <span class="status-dot pulse"></span>
          <span class="status-text">系统正常</span>
        </div>

        <!-- Real-time Clock -->
        <div class="clock" v-if="!isMobile">
          <el-icon :size="16"><Clock /></el-icon>
          <span>{{ currentTime }}</span>
        </div>

        <!-- User Dropdown -->
        <el-dropdown trigger="click" @command="handleCommand">
          <div class="user-avatar">
            <div class="avatar-circle">
              {{ userInitials }}
            </div>
            <span class="user-name" v-if="!isMobile">{{ userName }}</span>
            <el-icon :size="14"><ArrowDown /></el-icon>
          </div>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="profile">
                <el-icon><User /></el-icon>
                个人资料
              </el-dropdown-item>
              <el-dropdown-item command="settings">
                <el-icon><Setting /></el-icon>
                系统设置
              </el-dropdown-item>
              <el-dropdown-item divided command="logout">
                <el-icon><SwitchButton /></el-icon>
                退出登录
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>

        <!-- Mobile Menu Toggle -->
        <button class="mobile-menu-btn" v-if="isMobile" @click="toggleMobileMenu">
          <el-icon :size="24"><Menu /></el-icon>
        </button>
      </div>
    </div>

    <!-- Mobile Drawer Menu -->
    <el-drawer
      v-model="mobileMenuOpen"
      direction="rtl"
      :size="280"
      :show-close="false"
    >
      <template #header>
        <div class="mobile-drawer-header">
          <div class="brand">
            <div class="brand-icon">
              <el-icon :size="24"><DataAnalysis /></el-icon>
            </div>
            <span class="brand-name">评论分析平台</span>
          </div>
        </div>
      </template>
      <div class="mobile-menu">
        <router-link
          v-for="item in menuItems"
          :key="item.path"
          :to="item.path"
          class="mobile-nav-item"
          :class="{ 'is-active': isActive(item.path) }"
          @click="mobileMenuOpen = false"
        >
          <el-icon :size="20">
            <component :is="item.icon" />
          </el-icon>
          <span class="nav-label">{{ item.label }}</span>
        </router-link>
      </div>
    </el-drawer>
  </nav>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/store/auth'
import {
  DataAnalysis,
  Box,
  Upload,
  ChatLineRound,
  List,
  Document,
  Clock,
  User,
  Setting,
  SwitchButton,
  ArrowDown,
  Menu
} from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

// Menu Items
const menuItems = [
  { path: '/dashboard', label: '分析总览', icon: DataAnalysis },
  { path: '/products', label: '商品管理', icon: Box },
  { path: '/import', label: '数据导入', icon: Upload },
  { path: '/reviews', label: '评论管理', icon: ChatLineRound },
  { path: '/tasks', label: '任务管理', icon: List },
  { path: '/reports', label: '分析报告', icon: Document }
]

// Mobile state
const isMobile = ref(false)
const mobileMenuOpen = ref(false)

// Current time
const currentTime = ref('')

// User info
const userName = computed(() => authStore.user?.username || '用户')
const userInitials = computed(() => {
  const name = userName.value
  return name.substring(0, 2).toUpperCase()
})

// Check if route is active
const isActive = (path) => {
  return route.path.startsWith(path)
}

// Update time
const updateTime = () => {
  const now = new Date()
  const hours = String(now.getHours()).padStart(2, '0')
  const minutes = String(now.getMinutes()).padStart(2, '0')
  const seconds = String(now.getSeconds()).padStart(2, '0')
  currentTime.value = `${hours}:${minutes}:${seconds}`
}

// Handle responsive
const handleResize = () => {
  isMobile.value = window.innerWidth <= 1024
}

// Toggle mobile menu
const toggleMobileMenu = () => {
  mobileMenuOpen.value = !mobileMenuOpen.value
}

// Handle dropdown commands
const handleCommand = (command) => {
  switch (command) {
    case 'profile':
      // Handle profile
      break
    case 'settings':
      // Handle settings
      break
    case 'logout':
      authStore.logout()
      router.push('/login')
      break
  }
}

let timeInterval = null

onMounted(() => {
  updateTime()
  timeInterval = setInterval(updateTime, 1000)
  handleResize()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  if (timeInterval) {
    clearInterval(timeInterval)
  }
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped lang="scss">
.top-navbar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: var(--navbar-height);
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--gray-200);
  z-index: var(--z-fixed);
  transition: all var(--transition-base);
}

.navbar-container {
  max-width: 100%;
  height: 100%;
  padding: 0 var(--space-8);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-6);
}

// ============================================
// Left: Brand
// ============================================
.navbar-left {
  flex-shrink: 0;
  width: 180px;
}

.brand {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  cursor: pointer;
  transition: all var(--transition-base);

  &:hover {
    opacity: 0.8;
  }
}

.brand-icon {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%);
  border-radius: var(--radius-md);
  color: var(--white-pure);
}

.brand-name {
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
  color: var(--gray-900);
}

// ============================================
// Center: Navigation
// ============================================
.navbar-center {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
}

.nav-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-md);
  color: var(--gray-600);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  text-decoration: none;
  transition: all var(--transition-base);
  position: relative;

  &:hover {
    color: var(--primary-blue);
    background: rgba(59, 130, 246, 0.05);
  }

  &.is-active {
    color: var(--primary-blue);
    background: rgba(59, 130, 246, 0.1);

    &::after {
      content: '';
      position: absolute;
      bottom: -1px;
      left: var(--space-4);
      right: var(--space-4);
      height: 3px;
      background: var(--primary-blue-light);
      border-radius: 2px 2px 0 0;
    }
  }

  .nav-label {
    white-space: nowrap;
  }
}

// ============================================
// Right: Status, Time, User
// ============================================
.navbar-right {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: var(--space-6);
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  background: rgba(16, 185, 129, 0.1);
  border-radius: var(--radius-full);
}

.status-dot {
  width: 8px;
  height: 8px;
  background: var(--success);
  border-radius: 50%;

  &.pulse {
    animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
  }
}

.status-text {
  font-size: var(--text-xs);
  color: var(--success);
  font-weight: var(--font-medium);
}

.clock {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  background: var(--gray-50);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--gray-700);
  font-family: var(--font-mono);
}

.user-avatar {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-base);

  &:hover {
    background: var(--gray-50);
  }
}

.avatar-circle {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%);
  border-radius: 50%;
  color: var(--white-pure);
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
}

.user-name {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--gray-700);
}

.mobile-menu-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border: none;
  background: transparent;
  color: var(--gray-700);
  cursor: pointer;
  border-radius: var(--radius-md);
  transition: all var(--transition-base);

  &:hover {
    background: var(--gray-100);
  }
}

// ============================================
// Mobile Drawer
// ============================================
.mobile-drawer-header {
  padding: var(--space-4) 0;
}

.mobile-menu {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-4) 0;
}

.mobile-nav-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-4);
  border-radius: var(--radius-md);
  color: var(--gray-600);
  font-size: var(--text-base);
  font-weight: var(--font-medium);
  text-decoration: none;
  transition: all var(--transition-base);

  &:hover {
    color: var(--primary-blue);
    background: rgba(59, 130, 246, 0.05);
  }

  &.is-active {
    color: var(--primary-blue);
    background: rgba(59, 130, 246, 0.1);
    font-weight: var(--font-semibold);
  }
}

// ============================================
// Responsive
// ============================================
@media (max-width: 1024px) {
  .navbar-container {
    padding: 0 var(--space-4);
  }

  .navbar-left {
    width: auto;
  }

  .brand-name {
    display: none;
  }
}

@media (max-width: 768px) {
  .navbar-container {
    padding: 0 var(--space-4);
  }
}
</style>
