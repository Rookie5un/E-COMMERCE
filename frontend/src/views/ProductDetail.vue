<template>
  <div class="page-container">
    <div class="page-header page-block block-delay-1 detail-head">
      <div>
        <h1 class="page-title">商品详情</h1>
        <p class="page-description">查看商品基础信息，并发起或跟踪分析任务。</p>
      </div>
      <div class="head-actions">
        <button class="act-btn act-btn--ghost" type="button" @click="goTaskCenter">任务中心</button>
        <button class="act-btn act-btn--ghost" type="button" @click="goBack">返回列表</button>
      </div>
    </div>

    <section class="detail-surface page-block block-delay-2" v-loading="loading">
      <div class="surface-head">
        <div>
          <h3 class="surface-title">{{ product.name || '商品信息' }}</h3>
          <p class="surface-subtitle">档案信息与访问链接</p>
        </div>
        <el-button type="primary" @click="startAnalysis">
          <el-icon><DataAnalysis /></el-icon>
          开始分析
        </el-button>
      </div>

      <el-descriptions :column="3" border>
        <el-descriptions-item label="品类">{{ product.category || '-' }}</el-descriptions-item>
        <el-descriptions-item label="平台">{{ product.platform || '-' }}</el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ formatDate(product.created_at) }}</el-descriptions-item>

        <el-descriptions-item label="商品链接" :span="3">
          <el-link :href="product.url" target="_blank" type="primary" class="product-link">
            {{ product.url || '未设置商品链接' }}
          </el-link>
        </el-descriptions-item>

        <el-descriptions-item label="备注" :span="3">
          {{ product.description || '-' }}
        </el-descriptions-item>
      </el-descriptions>
    </section>

    <section class="stats-grid page-block block-delay-3">
      <article class="stat-card" style="--card-accent: #2563eb">
        <div class="s-label">任务总数</div>
        <div class="s-value">{{ analysisRuns.length }}</div>
        <div class="s-desc">历史分析任务</div>
      </article>
      <article class="stat-card" style="--card-accent: #16a34a">
        <div class="s-label">已完成</div>
        <div class="s-value text-pos">{{ completedCount }}</div>
        <div class="s-desc">可查看结果</div>
      </article>
      <article class="stat-card" style="--card-accent: #ca8a04">
        <div class="s-label">运行中</div>
        <div class="s-value text-neu">{{ runningCount }}</div>
        <div class="s-desc">等待处理完成</div>
      </article>
      <article class="stat-card" style="--card-accent: #dc2626">
        <div class="s-label">失败</div>
        <div class="s-value text-neg">{{ failedCount }}</div>
        <div class="s-desc">建议检查数据与模型</div>
      </article>
      <article class="stat-card" style="--card-accent: #64748b">
        <div class="s-label">已取消</div>
        <div class="s-value">{{ canceledCount }}</div>
        <div class="s-desc">人工终止任务</div>
      </article>
    </section>

    <section class="table-surface page-block block-delay-4">
      <div class="surface-head">
        <div>
          <h3 class="surface-title">分析任务</h3>
          <p class="surface-subtitle">查看任务状态并执行取消/重试</p>
        </div>
      </div>

      <el-table :data="analysisRuns">
        <el-table-column prop="id" label="任务ID" width="100">
          <template #default="{ row }">
            <span class="mono-num">#{{ row.id }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="model_name" label="模型" min-width="180" />

        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getTaskStatusType(row.status)">
              {{ getTaskStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="started_at" label="开始时间" width="180">
          <template #default="{ row }">
            <span class="mono-num small">{{ formatDate(row.started_at) }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="finished_at" label="完成时间" width="180">
          <template #default="{ row }">
            <span class="mono-num small">{{ formatDate(row.finished_at) }}</span>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="290" align="right">
          <template #default="{ row }">
            <div class="action-btns">
              <button
                class="act-btn act-btn--del"
                type="button"
                :disabled="!isTaskCancelable(row.status)"
                @click="cancelRun(row)"
              >
                取消
              </button>
              <button
                class="act-btn act-btn--edit"
                type="button"
                :disabled="!isTaskRetryable(row.status)"
                @click="retryRun(row)"
              >
                重试
              </button>
              <button
                class="act-btn act-btn--primary"
                type="button"
                :disabled="row.status !== 'completed'"
                @click="viewAnalysis(row.id)"
              >
                查看结果
              </button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getProduct } from '@/api/products'
import {
  getAnalysisRuns,
  createAnalysisRun,
  cancelAnalysisRun,
  retryAnalysisRun
} from '@/api/analysis'
import { ElMessage, ElMessageBox } from 'element-plus'
import { DataAnalysis } from '@element-plus/icons-vue'
import {
  getTaskStatusType,
  getTaskStatusText,
  isTaskCancelable,
  isTaskRetryable
} from '@/utils/taskStatus'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const product = ref({})
const analysisRuns = ref([])

const completedCount = computed(() => analysisRuns.value.filter(item => item.status === 'completed').length)
const runningCount = computed(() => analysisRuns.value.filter(item => item.status === 'running' || item.status === 'pending').length)
const failedCount = computed(() => analysisRuns.value.filter(item => item.status === 'failed').length)
const canceledCount = computed(() => analysisRuns.value.filter(item => item.status === 'canceled').length)

const extractErrorMessage = (error, fallback) => {
  return error?.response?.data?.error || fallback
}

const loadProduct = async () => {
  loading.value = true
  try {
    const res = await getProduct(route.params.id)
    product.value = res
  } catch (error) {
    ElMessage.error('加载商品信息失败')
  } finally {
    loading.value = false
  }
}

const loadAnalysisRuns = async () => {
  try {
    const res = await getAnalysisRuns({ product_id: route.params.id })
    analysisRuns.value = res.runs || []
  } catch (error) {
    ElMessage.error('加载分析任务失败')
  }
}

const startAnalysis = () => {
  ElMessageBox.confirm(
    '确定要开始分析该商品的评论吗？',
    '提示',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'info'
    }
  ).then(async () => {
    try {
      await createAnalysisRun({
        product_id: route.params.id
      })
      ElMessage.success('分析任务已创建')
      loadAnalysisRuns()
    } catch (error) {
      ElMessage.error(extractErrorMessage(error, '创建分析任务失败'))
    }
  })
}

const cancelRun = (row) => {
  ElMessageBox.confirm(
    `确定取消任务 #${row.id} 吗？`,
    '提示',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(async () => {
    try {
      await cancelAnalysisRun(row.id)
      ElMessage.success('任务已取消')
      loadAnalysisRuns()
    } catch (error) {
      ElMessage.error(extractErrorMessage(error, '取消任务失败'))
    }
  })
}

const retryRun = (row) => {
  ElMessageBox.confirm(
    `确定重试任务 #${row.id} 吗？`,
    '提示',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'info'
    }
  ).then(async () => {
    try {
      await retryAnalysisRun(row.id)
      ElMessage.success('重试任务已创建')
      loadAnalysisRuns()
    } catch (error) {
      ElMessage.error(extractErrorMessage(error, '重试任务失败'))
    }
  })
}

const viewAnalysis = (runId) => {
  router.push(`/dashboard?run_id=${runId}`)
}

const goBack = () => {
  router.push('/products')
}

const goTaskCenter = () => {
  router.push(`/tasks?product_id=${route.params.id}`)
}

const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

onMounted(() => {
  loadProduct()
  loadAnalysisRuns()
})
</script>

<style scoped>
.detail-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.head-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.product-link {
  word-break: break-all;
}

.mono-num {
  font-family: 'DM Mono', monospace;
  font-size: 12px;
}

.mono-num.small {
  font-size: 11px;
}

.action-btns {
  display: flex;
  justify-content: flex-end;
  gap: 6px;
}

@media (max-width: 900px) {
  .detail-head {
    flex-direction: column;
    align-items: stretch;
  }

  .head-actions {
    width: 100%;
  }

  .head-actions .act-btn {
    flex: 1;
  }

  .action-btns {
    flex-wrap: wrap;
    justify-content: flex-start;
  }
}
</style>
