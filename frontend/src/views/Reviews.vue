<template>
  <div class="page-container">
    <!-- Page Header -->
    <PageHeader
      title="评论管理"
      description="筛选评论、查看详情并执行软删除与恢复"
    />

    <section class="filter-section fade-in-delay-1">
      <div class="filter-group">
          <el-select
            v-model="filters.product_id"
            placeholder="按商品筛选"
            clearable
            class="filter-select"
            @change="handleProductChange"
          >
            <el-option
              v-for="product in products"
              :key="product.id"
              :label="product.name"
              :value="product.id"
            />
          </el-select>

          <el-select
            v-model="filters.batch_id"
            placeholder="按批次筛选"
            clearable
            class="filter-select"
            @change="handleSearch"
          >
            <el-option
              v-for="batch in batches"
              :key="batch.id"
              :label="`#${batch.id} ${batch.file_name || ''}`"
              :value="batch.id"
            />
          </el-select>

          <el-select
            v-model="filters.sentiment"
            placeholder="按情感筛选"
            clearable
            class="filter-select"
            @change="handleSearch"
          >
            <el-option label="好评" value="positive" />
            <el-option label="中评" value="neutral" />
            <el-option label="差评" value="negative" />
          </el-select>

          <el-select
            v-model="filters.status"
            class="status-select"
            @change="handleSearch"
          >
            <el-option label="仅有效" value="valid" />
            <el-option label="仅已删除" value="deleted" />
            <el-option label="全部" value="all" />
          </el-select>

          <el-input
            v-model="filters.keyword"
            placeholder="搜索评论内容"
            clearable
            class="keyword-input"
            @clear="handleSearch"
            @keyup.enter="handleSearch"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>

          <div class="filter-actions">
            <el-button @click="handleSearch">查询</el-button>
            <el-button @click="handleReset">重置</el-button>
          </div>
        </div>

        <div class="toolbar-right">
          <el-button
            type="danger"
            :disabled="!selectedRows.length"
            @click="handleBulkUpdate(false)"
          >
            批量删除
          </el-button>
          <el-button
            :disabled="!selectedRows.length"
            @click="handleBulkUpdate(true)"
          >
            批量恢复
          </el-button>
        </div>
    </section>

    <section class="table-surface page-block block-delay-2">
      <div class="surface-head">
        <div>
          <h3 class="surface-title">评论列表</h3>
          <p class="surface-subtitle">共 {{ pagination.total }} 条，列表仅展示核心信息，完整字段见详情。</p>
        </div>
      </div>

      <div ref="tableScrollRef" class="table-scroll-x">
        <el-table
          :data="reviews"
          v-loading="loading"
          class="wide-table"
          @selection-change="handleSelectionChange"
        >
          <el-table-column type="selection" width="48" />

          <el-table-column prop="id" label="评论ID" width="90">
            <template #default="{ row }">
              <span class="mono-num">#{{ row.id }}</span>
            </template>
          </el-table-column>

          <el-table-column label="商品" min-width="180">
            <template #default="{ row }">
              {{ getProductName(row.product_id) }}
            </template>
          </el-table-column>

          <el-table-column label="评论摘要" min-width="420" class-name="review-content-col">
            <template #default="{ row }">
              <p class="content-preview">{{ row.raw_content }}</p>
            </template>
          </el-table-column>

          <el-table-column label="情感" width="100">
            <template #default="{ row }">
              <el-tag v-if="row.sentiment" :type="getSentimentType(row.sentiment.label)" size="small">
                {{ getSentimentText(row.sentiment.label) }}
              </el-tag>
              <span v-else class="text-muted">未分析</span>
            </template>
          </el-table-column>

          <el-table-column label="状态" width="90">
            <template #default="{ row }">
              <el-tag :type="row.is_valid ? 'success' : 'info'">
                {{ row.is_valid ? '有效' : '已删除' }}
              </el-tag>
            </template>
          </el-table-column>

          <el-table-column label="操作" width="220" align="right">
            <template #default="{ row }">
              <div class="action-btns">
                <button class="act-btn act-btn--ghost" type="button" @click="openDetail(row)">详情</button>
                <button
                  v-if="row.is_valid"
                  class="act-btn act-btn--del"
                  type="button"
                  @click="handleSingleUpdate(row, false)"
                >
                  删除
                </button>
                <button
                  v-else
                  class="act-btn act-btn--edit"
                  type="button"
                  @click="handleSingleUpdate(row, true)"
                >
                  恢复
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
        @current-change="loadReviews"
        @size-change="handlePageSizeChange"
      />
    </section>

    <el-drawer
      v-model="detailVisible"
      title="评论详情"
      size="46%"
      :with-header="true"
      class="review-detail-drawer"
    >
      <div v-if="currentReview" class="detail-stack">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="评论ID">
            #{{ currentReview.id }}
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            {{ currentReview.is_valid ? '有效' : '已删除' }}
          </el-descriptions-item>
          <el-descriptions-item label="商品">
            {{ getProductName(currentReview.product_id) }}
          </el-descriptions-item>
          <el-descriptions-item label="批次">
            #{{ currentReview.batch_id }}
          </el-descriptions-item>
          <el-descriptions-item label="情感分类">
            <el-tag v-if="currentReview.sentiment" :type="getSentimentType(currentReview.sentiment.label)" size="small">
              {{ getSentimentText(currentReview.sentiment.label) }}
            </el-tag>
            <span v-else>未分析</span>
          </el-descriptions-item>
          <el-descriptions-item label="置信度">
            <span v-if="currentReview.sentiment && currentReview.sentiment.confidence">
              {{ (currentReview.sentiment.confidence * 100).toFixed(2) }}%
            </span>
            <span v-else>-</span>
          </el-descriptions-item>
          <el-descriptions-item label="评分">
            {{ currentReview.rating || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="评论时间">
            {{ formatDate(currentReview.review_time) }}
          </el-descriptions-item>
          <el-descriptions-item label="入库时间" :span="2">
            {{ formatDate(currentReview.created_at) }}
          </el-descriptions-item>
        </el-descriptions>

        <section class="detail-block">
          <h4 class="detail-title">原始评论</h4>
          <p class="detail-text">{{ currentReview.raw_content || '-' }}</p>
        </section>

        <section class="detail-block">
          <h4 class="detail-title">清洗后内容</h4>
          <p class="detail-text">{{ currentReview.cleaned_content || '-' }}</p>
        </section>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { nextTick, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import { getProducts } from '@/api/products'
import PageHeader from '@/components/PageHeader.vue'
import {
  getBatches,
  getReviews,
  setReviewValidity,
  bulkSetReviewValidity
} from '@/api/reviews'

const route = useRoute()

const loading = ref(false)
const reviews = ref([])
const products = ref([])
const batches = ref([])
const selectedRows = ref([])

const detailVisible = ref(false)
const currentReview = ref(null)
const tableScrollRef = ref(null)

const filters = reactive({
  product_id: null,
  batch_id: null,
  sentiment: null,
  status: 'valid',
  keyword: ''
})

const pagination = reactive({
  page: 1,
  per_page: 20,
  total: 0
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

const loadBatches = async () => {
  try {
    const params = { per_page: 200 }
    if (filters.product_id) {
      params.product_id = filters.product_id
    }
    const res = await getBatches(params)
    batches.value = res.batches || []
  } catch (error) {
    ElMessage.error('加载批次列表失败')
  }
}

const loadReviews = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      per_page: pagination.per_page,
      product_id: filters.product_id || undefined,
      batch_id: filters.batch_id || undefined,
      sentiment: filters.sentiment || undefined,
      status: filters.status,
      keyword: filters.keyword?.trim() || undefined
    }
    const res = await getReviews(params)
    reviews.value = res.reviews || []
    pagination.total = res.total || 0
    selectedRows.value = []
    await nextTick()
    if (tableScrollRef.value) {
      tableScrollRef.value.scrollLeft = 0
    }
  } catch (error) {
    ElMessage.error(extractErrorMessage(error, '加载评论列表失败'))
  } finally {
    loading.value = false
  }
}

const handleProductChange = async () => {
  filters.batch_id = null
  await loadBatches()
  handleSearch()
}

const handleSearch = () => {
  pagination.page = 1
  loadReviews()
}

const handleReset = async () => {
  filters.product_id = null
  filters.batch_id = null
  filters.sentiment = null
  filters.status = 'valid'
  filters.keyword = ''
  pagination.page = 1
  await loadBatches()
  loadReviews()
}

const handleSelectionChange = (rows) => {
  selectedRows.value = rows
}

const handlePageSizeChange = () => {
  pagination.page = 1
  loadReviews()
}

const handleSingleUpdate = (row, nextValidity) => {
  const actionText = nextValidity ? '恢复' : '删除'
  ElMessageBox.confirm(
    `确定要${actionText}评论 #${row.id} 吗？`,
    '提示',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: nextValidity ? 'info' : 'warning'
    }
  ).then(async () => {
    try {
      await setReviewValidity(row.id, nextValidity)
      ElMessage.success(`${actionText}成功`)
      loadReviews()
    } catch (error) {
      ElMessage.error(extractErrorMessage(error, `${actionText}失败`))
    }
  })
}

const handleBulkUpdate = (nextValidity) => {
  if (!selectedRows.value.length) {
    ElMessage.warning('请先选择评论')
    return
  }

  const actionText = nextValidity ? '恢复' : '软删除'
  ElMessageBox.confirm(
    `确定批量${actionText} ${selectedRows.value.length} 条评论吗？`,
    '提示',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: nextValidity ? 'info' : 'warning'
    }
  ).then(async () => {
    try {
      const reviewIds = selectedRows.value.map(row => row.id)
      const res = await bulkSetReviewValidity(reviewIds, nextValidity)
      ElMessage.success(`已更新 ${res.updated_count || 0} 条评论`)
      loadReviews()
    } catch (error) {
      ElMessage.error(extractErrorMessage(error, `${actionText}失败`))
    }
  })
}

const openDetail = (row) => {
  currentReview.value = row
  detailVisible.value = true
}

const getProductName = (productId) => {
  const product = products.value.find(item => item.id === productId)
  return product?.name || `商品#${productId}`
}

const getSentimentType = (label) => {
  const map = {
    positive: 'success',
    neutral: 'warning',
    negative: 'danger'
  }
  return map[label] || 'info'
}

const getSentimentText = (label) => {
  const map = {
    positive: '好评',
    neutral: '中评',
    negative: '差评'
  }
  return map[label] || label
}

const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

onMounted(async () => {
  const initialProductId = Number(route.query.product_id)
  if (Number.isInteger(initialProductId) && initialProductId > 0) {
    filters.product_id = initialProductId
  }

  await loadProducts()
  await loadBatches()
  loadReviews()
})
</script>

<style scoped lang="scss">
.page-container {
  animation: fade-in-up 0.4s ease-out both;
}

.filter-section {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  margin-bottom: var(--space-6);
  padding: var(--space-5);
  background: var(--white-pure);
  border-radius: var(--radius-lg);
  border: 1px solid var(--gray-200);
}

.filter-group {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex-wrap: wrap;
  flex: 1;
}

@media (max-width: 1024px) {
  .filter-section {
    flex-direction: column;
    align-items: stretch;
  }
}
.review-filters {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: nowrap;
  overflow-x: auto;
  padding-bottom: 2px;
}

.page-container--narrow {
  max-width: 1320px;
}

.filter-select {
  width: 140px;
  flex: 0 0 auto;
}

.status-select {
  width: 100px;
  flex: 0 0 auto;
}

.keyword-input {
  width: 240px;
  flex: 0 0 auto;
}

.filter-actions {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  flex: 0 0 auto;
}

.toolbar-right {
  flex-shrink: 0;
  margin-left: auto;
}

.mono-num {
  font-family: 'DM Mono', monospace;
  font-size: 12px;
}

.mono-num.small {
  font-size: 11px;
}

.text-muted {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.content-preview {
  margin: 0;
  color: var(--text-secondary);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: normal;
  word-break: break-word;
  line-height: 1.6;
}

:deep(.review-content-col .cell) {
  white-space: normal !important;
  overflow: visible !important;
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

@media (max-width: 900px) {
  .review-filters {
    flex-wrap: wrap;
    overflow-x: visible;
  }

  .filter-select,
  .status-select,
  .keyword-input {
    width: min(220px, 100%);
  }

  .filter-actions {
    width: 100%;
    justify-content: flex-start;
  }

  .action-btns {
    flex-wrap: wrap;
    justify-content: flex-start;
  }
}
</style>
