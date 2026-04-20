<template>
  <div class="page-container">
    <!-- Page Header -->
    <PageHeader
      title="数据导入"
      description="上传评论 CSV 文件并跟踪批次处理结果"
    />

    <section class="content-split fade-in-delay-1">
      <el-card class="form-card">
        <template #header>
          <div class="card-header card-header--stack">
            <span class="card-title">导入配置</span>
            <span class="card-subtitle">选择商品后上传 CSV 或手动输入评论内容</span>
          </div>
        </template>

        <el-tabs v-model="activeTab" class="import-tabs">
          <el-tab-pane label="上传文件" name="file">
            <el-form :model="form" label-width="98px" class="import-form">
              <el-form-item label="选择商品" required>
                <el-select
                  v-model="form.product_id"
                  placeholder="请选择商品"
                  class="product-select"
                >
                  <el-option
                    v-for="product in products"
                    :key="product.id"
                    :label="product.name"
                    :value="product.id"
                  />
                </el-select>
              </el-form-item>

              <el-form-item label="上传文件" required>
                <el-upload
                  ref="uploadRef"
                  :auto-upload="false"
                  :limit="1"
                  :on-change="handleFileChange"
                  :on-exceed="handleExceed"
                  accept=".csv"
                  drag
                  class="upload-area"
                >
                  <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
                  <div class="el-upload__text">
                    将 CSV 文件拖到此处，或<em>点击上传</em>
                  </div>
                  <template #tip>
                    <div class="el-upload__tip">
                      文件需包含 <code>content</code> 或 <code>评论内容</code> 列。
                    </div>
                  </template>
                </el-upload>
              </el-form-item>

              <el-form-item>
                <el-button
                  type="primary"
                  :loading="uploading"
                  :disabled="!form.product_id || !form.file"
                  @click="handleUpload"
                >
                  开始导入
                </el-button>
              </el-form-item>
            </el-form>
          </el-tab-pane>

          <el-tab-pane label="手动输入" name="manual">
            <el-form :model="manualForm" label-width="98px" class="import-form">
              <el-form-item label="选择商品" required>
                <el-select
                  v-model="manualForm.product_id"
                  placeholder="请选择商品"
                  class="product-select"
                >
                  <el-option
                    v-for="product in products"
                    :key="product.id"
                    :label="product.name"
                    :value="product.id"
                  />
                </el-select>
              </el-form-item>

              <el-form-item label="评论内容" required>
                <el-input
                  v-model="manualForm.content"
                  type="textarea"
                  :rows="8"
                  placeholder="请输入评论内容，支持多条评论，每行一条"
                  class="manual-input"
                />
                <div class="input-tip">
                  每行一条评论，系统将自动处理并分析情感倾向。
                </div>
              </el-form-item>

              <el-form-item>
                <el-button
                  type="primary"
                  :loading="manualUploading"
                  :disabled="!manualForm.product_id || !manualForm.content.trim()"
                  @click="handleManualSubmit"
                >
                  提交分析
                </el-button>
                <el-button @click="handleClearManual">清空</el-button>
              </el-form-item>
            </el-form>
          </el-tab-pane>
        </el-tabs>
      </el-card>

      <el-card class="summary-card">
        <template #header>
          <div class="card-header card-header--stack">
            <span class="card-title">导入状态</span>
            <span class="card-subtitle">快速查看最近批次处理结果</span>
          </div>
        </template>

        <div v-if="latestBatch" class="summary-grid">
          <article class="data-kpi-item data-kpi-item--total">
            <p class="data-kpi-label">总行数</p>
            <p class="data-kpi-value">{{ latestBatch.row_count || 0 }}</p>
            <p class="data-kpi-note">最近一次导入</p>
          </article>
          <article class="data-kpi-item data-kpi-item--success">
            <p class="data-kpi-label">成功</p>
            <p class="data-kpi-value text-pos">{{ latestBatch.imported_count || 0 }}</p>
            <p class="data-kpi-note">有效入库评论</p>
          </article>
          <article class="data-kpi-item data-kpi-item--duplicate">
            <p class="data-kpi-label">重复</p>
            <p class="data-kpi-value text-neu">{{ latestBatch.duplicate_count || 0 }}</p>
            <p class="data-kpi-note">已存在数据</p>
          </article>
          <article class="data-kpi-item data-kpi-item--failed">
            <p class="data-kpi-label">失败</p>
            <p class="data-kpi-value text-neg">{{ latestBatch.failed_count || 0 }}</p>
            <p class="data-kpi-note">需排查数据格式</p>
          </article>
        </div>

        <div v-else class="empty-state">
          <p>暂无导入记录，先完成一次 CSV 导入。</p>
        </div>
      </el-card>
    </section>

    <el-card class="table-card fade-in-delay-2">
      <template #header>
        <div class="card-header">
          <div>
            <span class="card-title">导入历史</span>
            <span class="card-subtitle">记录每次批次的总行数、成功率与错误量</span>
          </div>
          <el-button @click="loadBatches">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
        </div>
      </template>

      <el-table :data="batches" v-loading="loading">
        <el-table-column prop="id" label="批次ID" width="100">
          <template #default="{ row }">
            <span class="mono-num">#{{ row.id }}</span>
          </template>
        </el-table-column>

        <el-table-column label="商品名称" min-width="180">
          <template #default="{ row }">
            {{ getProductName(row.product_id) }}
          </template>
        </el-table-column>

        <el-table-column prop="file_name" label="文件名" min-width="220" />
        <el-table-column prop="row_count" label="总行数" width="100" />

        <el-table-column prop="imported_count" label="成功" width="100">
          <template #default="{ row }">
            <span class="success-text">{{ row.imported_count }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="duplicate_count" label="重复" width="100">
          <template #default="{ row }">
            <span class="warning-text">{{ row.duplicate_count }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="failed_count" label="失败" width="100">
          <template #default="{ row }">
            <span class="danger-text">{{ row.failed_count }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="created_at" label="导入时间" width="180">
          <template #default="{ row }">
            <span class="mono-num small">{{ formatDate(row.created_at) }}</span>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.per_page"
        :total="pagination.total"
        layout="total, prev, pager, next"
        class="table-pagination"
        @current-change="loadBatches"
      />
    </el-card>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { getProducts } from '@/api/products'
import { importReviews, getBatches } from '@/api/reviews'
import { ElMessage } from 'element-plus'
import { UploadFilled, Refresh } from '@element-plus/icons-vue'
import PageHeader from '@/components/PageHeader.vue'

const uploadRef = ref()
const products = ref([])
const batches = ref([])
const loading = ref(false)
const uploading = ref(false)
const manualUploading = ref(false)
const activeTab = ref('file')

const form = reactive({
  product_id: null,
  file: null
})

const manualForm = reactive({
  product_id: null,
  content: ''
})

const pagination = reactive({
  page: 1,
  per_page: 10,
  total: 0
})

const latestBatch = computed(() => batches.value[0] || null)

const loadProducts = async () => {
  try {
    const res = await getProducts({ per_page: 100 })
    products.value = res.products
  } catch (error) {
    ElMessage.error('加载商品列表失败')
  }
}

const loadBatches = async () => {
  loading.value = true
  try {
    const res = await getBatches({
      page: pagination.page,
      per_page: pagination.per_page
    })
    batches.value = res.batches
    pagination.total = res.total
  } catch (error) {
    ElMessage.error('加载导入历史失败')
  } finally {
    loading.value = false
  }
}

const handleFileChange = (file) => {
  form.file = file.raw
}

const handleExceed = () => {
  ElMessage.warning('只能上传一个文件')
}

const handleUpload = async () => {
  if (!form.product_id) {
    ElMessage.warning('请选择商品')
    return
  }
  if (!form.file) {
    ElMessage.warning('请选择文件')
    return
  }

  const formData = new FormData()
  formData.append('file', form.file)
  formData.append('product_id', form.product_id)

  uploading.value = true
  try {
    const res = await importReviews(formData)
    ElMessage.success('导入成功')
    ElMessage.info(
      `总行数: ${res.result.row_count}, 成功: ${res.result.imported_count}, 重复: ${res.result.duplicate_count}, 失败: ${res.result.failed_count}`
    )

    form.file = null
    uploadRef.value?.clearFiles()
    loadBatches()
  } catch (error) {
    ElMessage.error('导入失败')
  } finally {
    uploading.value = false
  }
}

const handleManualSubmit = async () => {
  if (!manualForm.product_id) {
    ElMessage.warning('请选择商品')
    return
  }
  if (!manualForm.content.trim()) {
    ElMessage.warning('请输入评论内容')
    return
  }

  const reviews = manualForm.content
    .split('\n')
    .map(line => line.trim())
    .filter(line => line.length > 0)

  if (reviews.length === 0) {
    ElMessage.warning('请输入有效的评论内容')
    return
  }

  manualUploading.value = true
  try {
    const res = await importReviews({
      product_id: manualForm.product_id,
      reviews: reviews
    })

    ElMessage.success(`成功提交 ${reviews.length} 条评论`)
    ElMessage.info(
      `成功: ${res.result.imported_count}, 重复: ${res.result.duplicate_count}, 失败: ${res.result.failed_count}`
    )

    manualForm.content = ''
    loadBatches()
  } catch (error) {
    ElMessage.error('提交失败')
  } finally {
    manualUploading.value = false
  }
}

const handleClearManual = () => {
  manualForm.content = ''
}

const getProductName = (productId) => {
  const product = products.value.find(item => item.id === productId)
  return product?.name || '-'
}

const getStatusType = (status) => {
  const map = {
    pending: 'info',
    processing: 'warning',
    completed: 'success',
    failed: 'danger'
  }
  return map[status] || 'info'
}

const getStatusText = (status) => {
  const map = {
    pending: '待处理',
    processing: '处理中',
    completed: '已完成',
    failed: '失败'
  }
  return map[status] || status
}

const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

onMounted(() => {
  loadProducts()
  loadBatches()
})
</script>

<style scoped lang="scss">
.page-container {
  animation: fade-in-up 0.4s ease-out both;
}

.content-split {
  display: grid;
  grid-template-columns: 1fr 1fr;
  align-items: start;
  gap: var(--space-6);
  margin-bottom: var(--space-6);
}

.card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-3);
}

.card-header--stack {
  flex-direction: column;
  justify-content: flex-start;
  gap: var(--space-1);
}

.card-title {
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
  color: var(--gray-900);
}

.card-subtitle {
  font-size: var(--text-xs);
  color: var(--gray-500);
}

@media (max-width: 1024px) {
  .content-split {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .summary-grid {
    grid-template-columns: 1fr;
  }
}
.import-form {
  display: grid;
  gap: 1px;
}

.import-tabs {
  margin-top: 16px;
}

.product-select {
  width: min(420px, 100%);
}

.upload-area {
  width: 100%;
}

.manual-input {
  width: 100%;
}

.input-tip {
  margin-top: 8px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-4);
}

.summary-grid .data-kpi-item {
  position: relative;
  overflow: hidden;
}

.summary-grid .data-kpi-item::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: var(--gray-300);
}

.summary-grid .data-kpi-item--total {
  border-color: rgba(59, 130, 246, 0.22);
  background: linear-gradient(180deg, rgba(59, 130, 246, 0.1) 0%, #ffffff 45%);
}

.summary-grid .data-kpi-item--total::before {
  background: var(--primary-blue-light);
}

.summary-grid .data-kpi-item--success {
  border-color: rgba(16, 185, 129, 0.24);
  background: linear-gradient(180deg, rgba(16, 185, 129, 0.11) 0%, #ffffff 45%);
}

.summary-grid .data-kpi-item--success::before {
  background: var(--success);
}

.summary-grid .data-kpi-item--duplicate {
  border-color: rgba(245, 158, 11, 0.25);
  background: linear-gradient(180deg, rgba(245, 158, 11, 0.11) 0%, #ffffff 45%);
}

.summary-grid .data-kpi-item--duplicate::before {
  background: var(--warning);
}

.summary-grid .data-kpi-item--failed {
  border-color: rgba(239, 68, 68, 0.25);
  background: linear-gradient(180deg, rgba(239, 68, 68, 0.1) 0%, #ffffff 45%);
}

.summary-grid .data-kpi-item--failed::before {
  background: var(--danger);
}

.mono-num {
  font-family: 'DM Mono', monospace;
  font-size: 12px;
}

.mono-num.small {
  font-size: 11px;
}

.table-pagination {
  margin-top: 12px;
  justify-content: flex-end;
}

:deep(.el-upload-dragger) {
  width: 100%;
}

:deep(code) {
  font-family: 'DM Mono', ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

@media (max-width: 980px) {
  .summary-grid {
    grid-template-columns: 1fr;
  }
}
</style>
