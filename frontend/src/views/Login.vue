<template>
  <div class="login-root">
    <div class="bg-grid"></div>
    <div class="bg-orb orb-1"></div>
    <div class="bg-orb orb-2"></div>
    <div class="bg-orb orb-3"></div>

    <div class="login-container">
      <section class="login-left" aria-hidden="true">
        <div class="brand-content">
          <div class="brand-icon">
            <svg width="40" height="40" viewBox="0 0 40 40" fill="none">
              <rect width="40" height="40" rx="8" fill="rgba(255,255,255,0.2)" />
              <path d="M8 28 L20 12 L32 28" stroke="#ffffff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" fill="none" />
              <path d="M14 22 L20 14 L26 22" stroke="#F59E0B" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none" opacity="0.9" />
            </svg>
          </div>
          <h1 class="brand-name">ECommerce Insight</h1>
          <p class="brand-tagline">电商评论智能分析平台</p>

          <div class="feature-list">
            <div class="feature-item" v-for="item in features" :key="item.text">
              <div class="feature-dot" :style="{ background: item.color }"></div>
              <span>{{ item.text }}</span>
            </div>
          </div>

          <div class="stat-row">
            <div class="mini-stat" v-for="stat in miniStats" :key="stat.label">
              <div class="mini-stat-value" :style="{ color: stat.color }">{{ stat.value }}</div>
              <div class="mini-stat-label">{{ stat.label }}</div>
            </div>
          </div>
        </div>
      </section>

      <section class="login-right">
        <div class="login-form-wrap">
          <div class="form-header">
            <h2>欢迎回来</h2>
            <p>登录后进入评论分析工作台</p>
          </div>

          <el-form
            ref="formRef"
            :model="form"
            :rules="rules"
            class="login-form"
            @submit.prevent="handleSubmit"
          >
            <div class="field-group">
              <label class="field-label">用户名</label>
              <el-form-item prop="username">
                <el-input
                  v-model="form.username"
                  placeholder="输入用户名"
                  size="large"
                  :prefix-icon="User"
                  autocomplete="username"
                  clearable
                />
              </el-form-item>
            </div>

            <div class="field-group">
              <label class="field-label">密码</label>
              <el-form-item prop="password">
                <el-input
                  v-model="form.password"
                  placeholder="输入密码"
                  size="large"
                  :prefix-icon="Lock"
                  type="password"
                  autocomplete="current-password"
                  show-password
                  @keyup.enter="handleSubmit"
                />
              </el-form-item>
            </div>

            <el-button
              type="primary"
              native-type="submit"
              size="large"
              :loading="loading"
              class="login-btn"
              @click="handleSubmit"
            >
              <span v-if="!loading">登录系统</span>
              <span v-else>验证中...</span>
            </el-button>
          </el-form>

          <div class="login-footer">
            <span>默认账户</span>
            <span class="hint-badge">admin / admin123</span>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/store/auth'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'

const router = useRouter()
const authStore = useAuthStore()

const formRef = ref()
const loading = ref(false)

const form = reactive({
  username: '',
  password: ''
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

const features = [
  { text: '批量评论导入与清洗', color: '#38bdf8' },
  { text: '情绪识别与趋势追踪', color: '#818cf8' },
  { text: '功能点与问题自动挖掘', color: '#34d399' },
  { text: '报告沉淀与复盘下载', color: '#fbbf24' }
]

const miniStats = [
  { value: '实时', label: '数据处理', color: '#34d399' },
  { value: '4+', label: '核心模块', color: '#38bdf8' },
  { value: '稳定', label: '链路状态', color: '#818cf8' }
]

const handleSubmit = async () => {
  if (!formRef.value || loading.value) return

  await formRef.value.validate(async (valid) => {
    if (!valid) return

    loading.value = true
    try {
      await authStore.login(form)
      ElMessage.success('登录成功')
      router.push('/')
    } catch (error) {
      ElMessage.error('登录失败，请检查用户名和密码')
    } finally {
      loading.value = false
    }
  })
}
</script>

<style scoped>
.login-root {
  min-height: 100vh;
  background: #f1f5f9;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
  padding: 18px;
}

.bg-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(56, 189, 248, 0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(56, 189, 248, 0.03) 1px, transparent 1px);
  background-size: 40px 40px;
  mask-image: radial-gradient(ellipse 80% 80% at 50% 50%, black 40%, transparent 100%);
}

.bg-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  pointer-events: none;
}

.orb-1 {
  width: 500px;
  height: 500px;
  background: radial-gradient(circle, rgba(37, 99, 235, 0.08) 0%, transparent 70%);
  top: -100px;
  left: -100px;
  animation: orb-float 8s ease-in-out infinite;
}

.orb-2 {
  width: 390px;
  height: 390px;
  background: radial-gradient(circle, rgba(124, 58, 237, 0.07) 0%, transparent 70%);
  bottom: -80px;
  right: -80px;
  animation: orb-float 10s ease-in-out infinite reverse;
}

.orb-3 {
  width: 290px;
  height: 290px;
  background: radial-gradient(circle, rgba(5, 150, 105, 0.06) 0%, transparent 70%);
  top: 52%;
  left: 50%;
  transform: translate(-50%, -50%);
  animation: orb-float 12s ease-in-out infinite 2s;
}

@keyframes orb-float {
  0%,
  100% {
    transform: translate(0, 0);
  }

  33% {
    transform: translate(20px, -20px);
  }

  66% {
    transform: translate(-15px, 15px);
  }
}

.login-container {
  width: min(940px, 100%);
  min-height: 560px;
  display: flex;
  border-radius: var(--radius-xl);
  border: 1px solid var(--border-default);
  background: #ffffff;
  box-shadow: 0 20px 60px rgba(15, 23, 42, 0.1), 0 4px 16px rgba(15, 23, 42, 0.06);
  overflow: hidden;
  position: relative;
  z-index: 1;
}

.login-left {
  flex: 0 0 430px;
  background: linear-gradient(135deg, #1e3a8a 0%, #1d4ed8 50%, #2563eb 100%);
  padding: 48px 42px;
  display: flex;
  align-items: center;
  position: relative;
  overflow: hidden;
}

.login-left::before {
  content: '';
  position: absolute;
  top: -80px;
  right: -80px;
  width: 300px;
  height: 300px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(255, 255, 255, 0.09) 0%, transparent 70%);
}

.brand-content {
  position: relative;
  z-index: 1;
}

.brand-icon {
  margin-bottom: 20px;
}

.brand-name {
  font-size: 28px;
  letter-spacing: -0.02em;
  font-weight: 800;
  color: #ffffff;
}

.brand-tagline {
  margin-top: 6px;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.74);
}

.feature-list {
  margin-top: 34px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.feature-item {
  display: flex;
  align-items: center;
  gap: 10px;
  color: rgba(255, 255, 255, 0.82);
  font-size: 13px;
}

.feature-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

.stat-row {
  margin-top: 32px;
  padding-top: 22px;
  display: flex;
  gap: 22px;
  border-top: 1px solid rgba(255, 255, 255, 0.2);
}

.mini-stat-value {
  font-family: 'DM Mono', monospace;
  font-size: 20px;
  line-height: 1;
  font-weight: 700;
}

.mini-stat-label {
  margin-top: 3px;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.6);
}

.login-right {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 48px 42px;
  background: #ffffff;
}

.login-form-wrap {
  width: 100%;
  max-width: 340px;
}

.form-header {
  margin-bottom: 30px;
}

.form-header h2 {
  font-size: 24px;
  font-weight: 800;
  color: var(--accent);
  letter-spacing: -0.02em;
}

.form-header p {
  margin-top: 6px;
  font-size: 13px;
  color: var(--text-secondary);
}

.field-group {
  margin-bottom: 4px;
}

.field-label {
  display: block;
  margin-bottom: 6px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.login-btn {
  width: 100%;
  min-height: 44px;
  margin-top: 8px;
  font-size: 14px !important;
  font-weight: 600 !important;
}

.login-footer {
  margin-top: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  font-size: 12px;
  color: var(--text-muted);
}

.hint-badge {
  border-radius: 99px;
  border: 1px solid var(--border-default);
  background: var(--bg-overlay);
  padding: 2px 10px;
  font-size: 11px;
  color: var(--accent);
  font-family: 'DM Mono', monospace;
}

@media (max-width: 980px) {
  .login-root {
    padding: 0;
    align-items: stretch;
  }

  .login-container {
    min-height: 100vh;
    width: 100%;
    border-radius: 0;
    border: none;
  }

  .login-left {
    display: none;
  }

  .login-right {
    padding: 24px 16px;
    background: rgba(255, 255, 255, 0.93);
    backdrop-filter: blur(8px);
  }
}
</style>
