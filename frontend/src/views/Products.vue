<template>
  <div class="page-container">
    <!-- Page Header -->
    <PageHeader
      title="商品管理"
      description="维护商品档案、筛选列表并进入单商品分析页"
    >
      <template #actions>
        <el-button type="primary" @click="showCreateDialog">
          <el-icon><Plus /></el-icon>
          新增商品
        </el-button>
      </template>
    </PageHeader>

    <!-- Filters -->
    <section class="filter-section fade-in-delay-1">
      <div class="filter-group">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索商品名称"
          clearable
          style="width: 240px;"
          @clear="handleSearch"
          @keyup.enter="handleSearch"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>

        <el-select
          v-model="selectedCategory"
          placeholder="按品类筛选"
          clearable
          style="width: 180px;"
          @change="handleFilterChange"
        >
          <el-option
            v-for="category in PRODUCT_CATEGORIES"
            :key="category"
            :label="category"
            :value="category"
          />
        </el-select>

        <el-button @click="handleSearch">查询</el-button>
        <el-button @click="handleResetFilters">重置</el-button>
      </div>

      <div class="filter-right">
        <span class="total-count">共 {{ pagination.total }} 条</span>
      </div>
    </section>

    <!-- Table Card -->
    <el-card class="table-card fade-in-delay-2">
      <template #header>
        <div class="card-header">
          <div>
            <span class="card-title">商品列表</span>
            <span class="card-subtitle">当前页 {{ products.length }} 条数据</span>
          </div>
        </div>
      </template>

      <el-table :data="products" v-loading="loading" stripe>
        <el-table-column prop="id" label="ID" width="80">
          <template #default="{ row }">
            <span class="mono-num">#{{ row.id }}</span>
          </template>
        </el-table-column>

        <el-table-column label="商品信息" min-width="260">
          <template #default="{ row }">
            <div class="product-name-cell">
              <div class="product-avatar">{{ row.name?.[0] ?? 'P' }}</div>
              <div>
                <div class="product-name">{{ row.name }}</div>
                <div class="product-brand">{{ row.url || '未设置商品链接' }}</div>
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="品类" width="120">
          <template #default="{ row }">
            <span class="badge badge-info">{{ row.category || '-' }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="platform" label="平台" width="110">
          <template #default="{ row }">
            <span class="platform-tag">{{ row.platform || '-' }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            <span class="mono-num small">{{ formatDate(row.created_at) }}</span>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="230" align="right">
          <template #default="{ row }">
            <div class="action-btns">
              <button class="act-btn act-btn--ghost" type="button" @click="viewDetail(row.id)">详情</button>
              <button class="act-btn act-btn--edit" type="button" @click="editProduct(row)">编辑</button>
              <button class="act-btn act-btn--del" type="button" @click="handleDelete(row)">删除</button>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.per_page"
        :total="pagination.total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        class="table-pagination"
        @current-change="loadProducts"
        @size-change="loadProducts"
      />
    </el-card>

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="600px">
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="100px"
      >
        <el-form-item label="商品名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入商品名称" />
        </el-form-item>
        <el-form-item label="品类" prop="category">
          <el-select v-model="form.category" placeholder="请选择品类" style="width: 100%">
            <el-option
              v-for="category in PRODUCT_CATEGORIES"
              :key="category"
              :label="category"
              :value="category"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="平台" prop="platform">
          <el-select v-model="form.platform" placeholder="请选择平台" style="width: 100%">
            <el-option label="京东" value="京东" />
            <el-option label="淘宝" value="淘宝" />
            <el-option label="拼多多" value="拼多多" />
            <el-option label="天猫" value="天猫" />
          </el-select>
        </el-form-item>
        <el-form-item label="商品链接" prop="url">
          <el-input v-model="form.url" placeholder="请输入商品链接" />
        </el-form-item>
        <el-form-item label="备注" prop="description">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="3"
            placeholder="请输入备注信息"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { getProducts, createProduct, updateProduct, deleteProduct } from '@/api/products'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Plus } from '@element-plus/icons-vue'
import PageHeader from '@/components/PageHeader.vue'

const router = useRouter()

const loading = ref(false)
const products = ref([])
const searchKeyword = ref('')
const selectedCategory = ref('')
const pagination = reactive({
  page: 1,
  per_page: 10,
  total: 0
})

const dialogVisible = ref(false)
const dialogTitle = ref('新增商品')
const formRef = ref()
const submitting = ref(false)
const editingId = ref(null)

const form = reactive({
  name: '',
  category: '',
  platform: '',
  url: '',
  description: ''
})

const PRODUCT_CATEGORIES = [
  '手机数码',
  '电脑办公',
  '家用电器',
  '家居家装',
  '服饰鞋包',
  '食品生鲜',
  '美妆个护',
  '母婴玩具',
  '运动户外',
  '汽车用品'
]

const rules = {
  name: [{ required: true, message: '请输入商品名称', trigger: 'blur' }],
  category: [{ required: true, message: '请选择品类', trigger: 'change' }],
  platform: [{ required: true, message: '请选择平台', trigger: 'change' }]
}

const loadProducts = async () => {
  loading.value = true
  try {
    const res = await getProducts({
      page: pagination.page,
      per_page: pagination.per_page,
      keyword: searchKeyword.value.trim(),
      category: selectedCategory.value || undefined
    })
    products.value = res.products
    pagination.total = res.total
  } catch (error) {
    ElMessage.error('加载商品列表失败')
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  pagination.page = 1
  loadProducts()
}

const handleFilterChange = () => {
  pagination.page = 1
  loadProducts()
}

const handleResetFilters = () => {
  searchKeyword.value = ''
  selectedCategory.value = ''
  pagination.page = 1
  loadProducts()
}

const showCreateDialog = () => {
  dialogTitle.value = '新增商品'
  editingId.value = null
  resetForm()
  dialogVisible.value = true
}

const editProduct = (product) => {
  dialogTitle.value = '编辑商品'
  editingId.value = product.id
  Object.assign(form, {
    name: product.name,
    category: product.category,
    platform: product.platform,
    url: product.url,
    description: product.description
  })
  dialogVisible.value = true
}

const handleSubmit = async () => {
  if (!formRef.value) return

  await formRef.value.validate(async (valid) => {
    if (!valid) return

    submitting.value = true
    try {
      if (editingId.value) {
        await updateProduct(editingId.value, form)
        ElMessage.success('更新成功')
      } else {
        await createProduct(form)
        ElMessage.success('创建成功')
      }
      dialogVisible.value = false
      loadProducts()
    } catch (error) {
      ElMessage.error('操作失败')
    } finally {
      submitting.value = false
    }
  })
}

const handleDelete = (product) => {
  ElMessageBox.confirm(
    `确定要删除商品"${product.name}"吗？`,
    '提示',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(async () => {
    try {
      await deleteProduct(product.id)
      ElMessage.success('删除成功')
      loadProducts()
    } catch (error) {
      ElMessage.error('删除失败')
    }
  })
}

const viewDetail = (id) => {
  router.push(`/products/${id}`)
}

const resetForm = () => {
  Object.assign(form, {
    name: '',
    category: '',
    platform: '',
    url: '',
    description: ''
  })
  formRef.value?.clearValidate()
}

const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

onMounted(() => {
  loadProducts()
})
</script>

<style scoped lang="scss">
.page-container {
  animation: fade-in-up 0.4s ease-out both;
}

// Filter Section
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
}

.filter-right {
  flex-shrink: 0;
}

.total-count {
  font-size: var(--text-sm);
  color: var(--gray-500);
  font-family: var(--font-mono);
}

// Table Card
.table-card {
  animation: fade-in-up 0.4s ease-out 0.1s both;
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

// Table Cells
.product-name-cell {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.product-avatar {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-md);
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.1), rgba(6, 182, 212, 0.1));
  border: 1px solid var(--gray-200);
  color: var(--primary-blue);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--text-sm);
  font-weight: var(--font-bold);
  flex-shrink: 0;
}

.product-name {
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--gray-900);
}

.product-brand {
  margin-top: 2px;
  font-size: var(--text-xs);
  color: var(--gray-500);
  max-width: 300px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.platform-tag {
  font-size: var(--text-xs);
  font-family: var(--font-mono);
  color: var(--gray-600);
}

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

.table-pagination {
  margin-top: var(--space-4);
  display: flex;
  justify-content: flex-end;
}

// Responsive
@media (max-width: 1024px) {
  .filter-section {
    flex-direction: column;
    align-items: stretch;
  }

  .filter-group {
    width: 100%;
  }

  .filter-right {
    width: 100%;
    text-align: left;
  }
}

@media (max-width: 768px) {
  .filter-section {
    padding: var(--space-4);
  }

  .action-btns {
    flex-wrap: wrap;
    justify-content: flex-start;
  }
}
</style>
