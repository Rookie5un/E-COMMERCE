<template>
  <div class="page-container">
    <!-- Page Header -->
    <PageHeader
      title="商品详情"
      description="查看商品基础信息，并发起或跟踪分析任务"
    >
      <template #actions>
        <el-button @click="goTaskCenter">任务中心</el-button>
        <el-button @click="goBack">返回列表</el-button>
      </template>
    </PageHeader>

    <!-- Product Info Card -->
    <el-card class="info-card fade-in-delay-1" v-loading="loading">
      <template #header>
        <div class="card-header">
          <div>
            <span class="card-title">{{ product.name || '商品信息' }}</span>
            <span class="card-subtitle">档案信息与访问链接</span>
          </div>
          <el-button type="primary" @click="startAnalysis">
            <el-icon><DataAnalysis /></el-icon>
            开始分析
          </el-button>
        </div>
      </template>

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
    </el-card>

    <!-- Stats Cards -->
    <section class="stats-grid fade-in-delay-2">
      <StatCard
        label="任务总数"
        :value="analysisRuns.length"
        description="历史分析任务"
        :icon="List"
        accent-color="#3b82f6"
      />
      <StatCard
        label="已完成"
        :value="completedCount"
        description="可查看结果"
        :icon="CircleCheck"
        accent-color="#10b981"
        value-class="text-pos"
      />
      <StatCard
        label="运行中"
        :value="runningCount"
        description="等待处理完成"
        :icon="Loading"
        accent-color="#f59e0b"
        value-class="text-neu"
      />
      <StatCard
        label="失败"
        :value="failedCount"
        description="建议检查数据与模型"
        :icon="CircleClose"
        accent-color="#ef4444"
        value-class="text-neg"
      />
      <StatCard
        label="已取消"
        :value="canceledCount"
        description="人工终止任务"
        :icon="RemoveFilled"
        accent-color="#64748b"
      />
    </section>

    <!-- Tasks Table -->
    <el-card class="table-card fade-in-delay-3">
      <template #header>
        <div class="card-header">
          <div>
            <span class="card-title">分析任务</span>
            <span class="card-subtitle">查看任务状态并执行取消/重试</span>
          </div>
        </div>
      </template>

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
    </el-card>
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
import { DataAnalysis, List, CircleCheck, Loading, CircleClose, RemoveFilled } from '@element-plus/icons-vue'
import {
  getTaskStatusType,
  getTaskStatusText,
  isTaskCancelable,
  isTaskRetryable
} from '@/utils/taskStatus'
import PageHeader from '@/components/PageHeader.vue'
import StatCard from '@/components/StatCard.vue'

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

<style scoped lang="scss">
.page-container {
  animation: fade-in-up 0.4s ease-out both;
}

// Cards
.info-card,
.table-card {
  margin-bottom: var(--space-6);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.card-title {
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
  color: var(--gray-900);
  margin-right: var(--space-3);
}

.card-subtitle {
  font-size: var(--text-xs);
  color: var(--gray-500);
}

// Stats Grid
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: var(--space-6);
  margin-bottom: var(--space-6);
}

// Product Link
.product-link {
  word-break: break-all;
}

// Table Cells
.mono-num {
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  color: var(--gray-600);

  &.small {
    font-size: var(--text-xs);
  }
}

.action-btns {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
}

// Responsive
@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: 1fr;
    gap: var(--space-4);
  }

  .action-btns {
    flex-wrap: wrap;
    justify-content: flex-start;
  }
}
</style>
