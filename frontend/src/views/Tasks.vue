<template>
  <div class="page-container page-container--narrow">
    <div class="page-header page-block block-delay-1 tasks-head">
      <div>
        <h1 class="page-title">任务管理</h1>
        <p class="page-description">统一管理分析任务，支持创建、取消、重试和详情查看。</p>
      </div>
      <el-button type="primary" @click="openCreateDialog">
        <el-icon><Plus /></el-icon>
        新建任务
      </el-button>
    </div>

    <section class="page-toolbar page-block block-delay-1">
      <div class="toolbar-row">
        <div class="toolbar-left">
          <el-select
            v-model="filters.product_id"
            placeholder="按商品筛选"
            clearable
            class="filter-select"
            @change="handleSearch"
          >
            <el-option
              v-for="product in products"
              :key="product.id"
              :label="product.name"
              :value="product.id"
            />
          </el-select>

          <el-select
            v-model="filters.status"
            placeholder="按状态筛选"
            clearable
            class="status-select"
            @change="handleSearch"
          >
            <el-option label="待处理" value="pending" />
            <el-option label="运行中" value="running" />
            <el-option label="已完成" value="completed" />
            <el-option label="失败" value="failed" />
            <el-option label="已取消" value="canceled" />
          </el-select>

          <el-button @click="handleSearch">查询</el-button>
          <el-button @click="handleReset">重置</el-button>
        </div>

      </div>
    </section>

    <section class="table-surface page-block block-delay-2">
      <div class="surface-head">
        <div>
          <h3 class="surface-title">任务列表</h3>
          <p class="surface-subtitle">列表仅保留核心信息，更多字段请查看详情。</p>
        </div>
      </div>

      <div ref="tableScrollRef" class="table-scroll-x">
        <el-table
          :data="runs"
          v-loading="loading"
          class="wide-table"
        >
          <el-table-column prop="id" label="任务ID" width="100">
            <template #default="{ row }">
              <span class="mono-num">#{{ row.id }}</span>
            </template>
          </el-table-column>

          <el-table-column label="商品" min-width="180">
            <template #default="{ row }">
              {{ getProductName(row.product_id) }}
            </template>
          </el-table-column>

          <el-table-column label="模型" min-width="180">
            <template #default="{ row }">
              <div class="model-cell">
                <div>{{ row.model_name }}</div>
                <div class="model-version">{{ row.model_version }}</div>
              </div>
            </template>
          </el-table-column>

          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="getTaskStatusType(row.status)">
                {{ getTaskStatusText(row.status) }}
              </el-tag>
            </template>
          </el-table-column>

          <el-table-column label="开始时间" width="176">
            <template #default="{ row }">
              <span class="mono-num small">{{ getDisplayTime(row) }}</span>
            </template>
          </el-table-column>

          <el-table-column label="操作" width="360" align="right">
            <template #default="{ row }">
              <div class="action-btns">
                <button class="act-btn act-btn--ghost" type="button" @click="openDetail(row)">详情</button>
                <button
                  class="act-btn act-btn--del"
                  type="button"
                  :disabled="!isTaskCancelable(row.status)"
                  @click="handleCancel(row)"
                >
                  取消
                </button>
                <button
                  class="act-btn act-btn--edit"
                  type="button"
                  :disabled="!isTaskRetryable(row.status)"
                  @click="handleRetry(row)"
                >
                  重试
                </button>
                <button
                  class="act-btn act-btn--primary"
                  type="button"
                  :disabled="row.status !== 'completed' || isGeneratingReport(row.id)"
                  @click="handleGenerateReport(row)"
                >
                  {{ isGeneratingReport(row.id) ? '生成中' : '报告' }}
                </button>
                <button
                  class="act-btn act-btn--ghost"
                  type="button"
                  :disabled="row.status !== 'completed'"
                  @click="viewResult(row.id)"
                >
                  结果
                </button>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.per_page"
        :total="pagination.total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        class="table-pagination"
        @current-change="loadRuns"
        @size-change="handlePageSizeChange"
      />
    </section>

    <el-dialog v-model="createDialogVisible" title="新建分析任务" width="560px">
      <el-form :model="createForm" label-width="90px">
        <el-form-item label="商品" required>
          <el-select
            v-model="createForm.product_id"
            placeholder="请选择商品"
            style="width: 100%"
            @change="handleCreateProductChange"
          >
            <el-option
              v-for="product in products"
              :key="product.id"
              :label="product.name"
              :value="product.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="批次">
          <el-select
            v-model="createForm.batch_id"
            placeholder="可选：仅分析指定批次"
            clearable
            style="width: 100%"
          >
            <el-option
              v-for="batch in createBatches"
              :key="batch.id"
              :label="`#${batch.id} ${batch.file_name || ''}`"
              :value="batch.id"
            />
          </el-select>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="handleCreateTask">创建任务</el-button>
      </template>
    </el-dialog>

    <el-drawer
      v-model="detailVisible"
      title="任务详情"
      size="45%"
      :with-header="true"
    >
      <div v-if="currentRun" class="detail-stack">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="任务ID">
            #{{ currentRun.id }}
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            {{ getTaskStatusText(currentRun.status) }}
          </el-descriptions-item>
          <el-descriptions-item label="商品">
            {{ getProductName(currentRun.product_id) }}
          </el-descriptions-item>
          <el-descriptions-item label="批次">
            {{ currentRun.batch_id ? `#${currentRun.batch_id}` : '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="模型名称">
            {{ currentRun.model_name || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="模型版本">
            {{ currentRun.model_version || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="创建时间">
            {{ formatDate(currentRun.created_at) }}
          </el-descriptions-item>
          <el-descriptions-item label="开始时间">
            {{ formatDate(currentRun.started_at) }}
          </el-descriptions-item>
          <el-descriptions-item label="完成时间" :span="2">
            {{ formatDate(currentRun.finished_at) }}
          </el-descriptions-item>
        </el-descriptions>

        <section class="detail-block">
          <h4 class="detail-title">错误信息</h4>
          <p class="detail-text">{{ currentRun.error_message || '无' }}</p>
        </section>

        <section class="detail-block" v-if="currentRun.config_json">
          <h4 class="detail-title">任务配置</h4>
          <pre class="config-json">{{ JSON.stringify(currentRun.config_json, null, 2) }}</pre>
        </section>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { nextTick, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { getProducts } from '@/api/products'
import { getBatches } from '@/api/reviews'
import {
  getAnalysisRuns,
  getAnalysisRun,
  createAnalysisRun,
  cancelAnalysisRun,
  retryAnalysisRun
} from '@/api/analysis'
import { createReport } from '@/api/reports'
import {
  getTaskStatusType,
  getTaskStatusText,
  isTaskCancelable,
  isTaskRetryable
} from '@/utils/taskStatus'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const creating = ref(false)
const runs = ref([])
const products = ref([])
const createBatches = ref([])

const createDialogVisible = ref(false)
const detailVisible = ref(false)
const currentRun = ref(null)
const tableScrollRef = ref(null)
const reportingRunIds = ref([])

const filters = reactive({
  product_id: null,
  status: ''
})

const pagination = reactive({
  page: 1,
  per_page: 20,
  total: 0
})

const createForm = reactive({
  product_id: null,
  batch_id: null
})

const extractErrorMessage = (error, fallback) => {
  return error?.response?.data?.error || fallback
}

const loadProducts = async () => {
  try {
    const res = await getProducts({ per_page: 200 })
    products.value = res.products || []
  } catch (error) {
    ElMessage.error('加载商品列表失败')
  }
}

const loadRuns = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      per_page: pagination.per_page,
      product_id: filters.product_id || undefined,
      status: filters.status || undefined
    }
    const res = await getAnalysisRuns(params)
    runs.value = res.runs || []
    pagination.total = res.total || 0
    await nextTick()
    if (tableScrollRef.value) {
      tableScrollRef.value.scrollLeft = 0
    }
  } catch (error) {
    ElMessage.error(extractErrorMessage(error, '加载任务列表失败'))
  } finally {
    loading.value = false
  }
}

const loadCreateBatches = async () => {
  if (!createForm.product_id) {
    createBatches.value = []
    createForm.batch_id = null
    return
  }

  try {
    const res = await getBatches({
      product_id: createForm.product_id,
      per_page: 200
    })
    createBatches.value = res.batches || []
  } catch (error) {
    ElMessage.error('加载批次失败')
  }
}

const handleSearch = () => {
  pagination.page = 1
  loadRuns()
}

const handleReset = () => {
  filters.product_id = null
  filters.status = ''
  pagination.page = 1
  loadRuns()
}

const handlePageSizeChange = () => {
  pagination.page = 1
  loadRuns()
}

const openCreateDialog = async () => {
  createForm.product_id = filters.product_id || null
  createForm.batch_id = null
  createDialogVisible.value = true
  await loadCreateBatches()
}

const handleCreateProductChange = () => {
  createForm.batch_id = null
  loadCreateBatches()
}

const handleCreateTask = async () => {
  if (!createForm.product_id) {
    ElMessage.warning('请选择商品')
    return
  }

  creating.value = true
  try {
    await createAnalysisRun({
      product_id: createForm.product_id,
      batch_id: createForm.batch_id || undefined
    })
    ElMessage.success('任务创建成功')
    createDialogVisible.value = false
    handleSearch()
  } catch (error) {
    ElMessage.error(extractErrorMessage(error, '创建任务失败'))
  } finally {
    creating.value = false
  }
}

const handleCancel = (row) => {
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
      loadRuns()
      if (currentRun.value?.id === row.id) {
        openDetail(row)
      }
    } catch (error) {
      ElMessage.error(extractErrorMessage(error, '取消任务失败'))
    }
  })
}

const handleRetry = (row) => {
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
      loadRuns()
    } catch (error) {
      ElMessage.error(extractErrorMessage(error, '重试任务失败'))
    }
  })
}

const isGeneratingReport = (runId) => {
  return reportingRunIds.value.includes(runId)
}

const handleGenerateReport = async (row) => {
  if (row.status !== 'completed' || isGeneratingReport(row.id)) {
    return
  }

  reportingRunIds.value = [...reportingRunIds.value, row.id]
  try {
    const res = await createReport({ run_id: row.id })
    const reportId = res?.report?.id
    ElMessage.success(reportId ? `报告生成成功（#${reportId}）` : '报告生成成功')
  } catch (error) {
    ElMessage.error(extractErrorMessage(error, '生成报告失败'))
  } finally {
    reportingRunIds.value = reportingRunIds.value.filter(id => id !== row.id)
  }
}

const viewResult = (runId) => {
  router.push(`/dashboard?run_id=${runId}`)
}

const openDetail = async (row) => {
  try {
    const detail = await getAnalysisRun(row.id)
    currentRun.value = detail
    detailVisible.value = true
  } catch (error) {
    ElMessage.error(extractErrorMessage(error, '加载任务详情失败'))
  }
}

const getProductName = (productId) => {
  const product = products.value.find(item => item.id === productId)
  return product?.name || `商品#${productId}`
}

const parseUtcDate = (dateStr) => {
  if (!dateStr) return null
  const normalized = String(dateStr).trim().replace(' ', 'T')
  const hasTimezone = /(?:Z|[+-]\d{2}:\d{2})$/.test(normalized)
  const parsed = new Date(hasTimezone ? normalized : `${normalized}Z`)
  return Number.isNaN(parsed.getTime()) ? null : parsed
}

const formatDate = (dateStr) => {
  const date = parseUtcDate(dateStr)
  if (!date) return '-'
  return date.toLocaleString('zh-CN', { hour12: false })
}

const getDisplayTime = (row) => {
  return formatDate(row.started_at || row.created_at)
}

onMounted(async () => {
  const initialProductId = Number(route.query.product_id)
  if (Number.isInteger(initialProductId) && initialProductId > 0) {
    filters.product_id = initialProductId
  }

  await loadProducts()
  loadRuns()
})
</script>

<style scoped>
.tasks-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.page-container--narrow {
  max-width: 1320px;
}

.filter-select {
  width: min(240px, 100%);
}

.status-select {
  width: min(160px, 100%);
}

.toolbar-left {
  flex: 1;
}

.mono-num {
  font-family: 'DM Mono', monospace;
  font-size: 12px;
}

.mono-num.small {
  font-size: 11px;
}

.model-cell {
  display: grid;
  gap: 2px;
}

.model-version {
  font-size: 11px;
  color: var(--text-muted);
}

.action-btns {
  display: flex;
  justify-content: flex-end;
  gap: 6px;
}

.table-scroll-x {
  width: 100%;
  overflow-x: visible;
}

.wide-table {
  width: 100%;
}

.table-pagination {
  margin-top: 12px;
  justify-content: flex-end;
}

.detail-stack {
  display: grid;
  gap: 12px;
}

.detail-block {
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  background: var(--bg-overlay);
  padding: 12px;
}

.detail-title {
  margin-bottom: 8px;
  font-size: 13px;
  font-weight: 700;
  color: var(--text-primary);
}

.detail-text {
  margin: 0;
  color: var(--text-secondary);
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
}

.config-json {
  margin: 0;
  font-size: 12px;
  line-height: 1.6;
  color: var(--text-secondary);
  background: #ffffff;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  padding: 10px;
  overflow-x: auto;
}

@media (max-width: 980px) {
  .tasks-head {
    flex-direction: column;
    align-items: stretch;
  }

  .tasks-head :deep(.el-button) {
    width: 100%;
  }

  .action-btns {
    flex-wrap: wrap;
    justify-content: flex-start;
  }
}
</style>
