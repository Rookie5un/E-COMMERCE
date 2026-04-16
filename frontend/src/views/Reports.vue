<template>
  <div class="page-container">
    <div class="page-header page-block block-delay-1 reports-head">
      <div>
        <h1 class="page-title">分析报告</h1>
        <p class="page-description">查看历史报告摘要，并下载 PDF 归档。</p>
      </div>
      <button class="act-btn act-btn--ghost" type="button" @click="loadReports">
        刷新列表
      </button>
    </div>

    <section class="stats-grid page-block block-delay-2">
      <article class="stat-card" style="--card-accent: #2563eb">
        <div class="s-label">报告数量</div>
        <div class="s-value">{{ pagination.total }}</div>
        <div class="s-desc">当前系统报告总数</div>
      </article>
      <article class="stat-card" style="--card-accent: #16a34a">
        <div class="s-label">平均正向率</div>
        <div class="s-value text-pos">{{ averagePositiveRate }}%</div>
        <div class="s-desc">当前页统计</div>
      </article>
      <article class="stat-card" style="--card-accent: #dc2626">
        <div class="s-label">高风险报告</div>
        <div class="s-value text-neg">{{ riskReportCount }}</div>
        <div class="s-desc">负向率 ≥ 30%</div>
      </article>
      <article class="stat-card" style="--card-accent: #0891b2">
        <div class="s-label">可下载 PDF</div>
        <div class="s-value">{{ downloadableCount }}</div>
        <div class="s-desc">已生成归档文件</div>
      </article>
    </section>

    <section class="table-surface page-block block-delay-3">
      <div class="surface-head">
        <div>
          <h3 class="surface-title">报告列表</h3>
          <p class="surface-subtitle">按批次汇总评论分析结果。</p>
        </div>
      </div>

      <el-table :data="reports" v-loading="loading">
        <el-table-column label="报告标题" min-width="260">
          <template #default="{ row }">
            <div class="report-title-cell">
              <div class="report-icon">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <polyline points="14,2 14,8 20,8" />
                </svg>
              </div>
              <div>
                <div class="report-name">{{ row.title }}</div>
                <div class="report-time">{{ formatDate(row.created_at) }}</div>
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="评论总数" width="100" align="right">
          <template #default="{ row }">
            <span class="mono-num">{{ row.summary_json?.total_reviews || 0 }}</span>
          </template>
        </el-table-column>

        <el-table-column label="情感分布" width="240">
          <template #default="{ row }">
            <div class="sentiment-pills">
              <span class="badge badge-pos">正 {{ getSentimentCountByRow(row, 'positive') }}</span>
              <span class="badge badge-neu">中 {{ getSentimentCountByRow(row, 'neutral') }}</span>
              <span class="badge badge-neg">负 {{ getSentimentCountByRow(row, 'negative') }}</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="正向率" width="90" align="right">
          <template #default="{ row }">
            <span class="positive-text mono-num">{{ getPositiveRate(row) }}%</span>
          </template>
        </el-table-column>

        <el-table-column label="负向率" width="90" align="right">
          <template #default="{ row }">
            <span class="danger-text mono-num">{{ getNegativeRate(row) }}%</span>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="200" align="right" fixed="right">
          <template #default="{ row }">
            <div class="action-btns">
              <button class="act-btn act-btn--ghost" type="button" @click="viewReport(row)">详情</button>
              <button
                class="act-btn act-btn--primary"
                type="button"
                :disabled="!row.pdf_path"
                @click="downloadReport(row.id)"
              >
                下载
              </button>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.per_page"
        :total="pagination.total"
        layout="total, prev, pager, next"
        class="table-pagination"
        @current-change="loadReports"
      />
    </section>

    <el-dialog v-model="dialogVisible" title="报告详情" width="940px" top="4vh">
      <div v-if="currentReport" class="report-detail-stack">
        <section class="detail-block">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="报告标题" :span="2">
              {{ currentReport.title }}
            </el-descriptions-item>
            <el-descriptions-item label="评论总数">
              {{ currentReport.summary_json?.total_reviews || 0 }}
            </el-descriptions-item>
            <el-descriptions-item label="生成时间">
              {{ formatDate(currentReport.created_at) }}
            </el-descriptions-item>
          </el-descriptions>
        </section>

        <section class="detail-block">
          <h3 class="detail-title">情感分布</h3>
          <div class="report-kpi-grid">
            <article class="data-kpi-item">
              <p class="data-kpi-label">正向</p>
              <p class="data-kpi-value positive-text">{{ getSentimentCount('positive') }}</p>
              <p class="data-kpi-note">{{ getPositiveRate(currentReport) }}%</p>
            </article>
            <article class="data-kpi-item">
              <p class="data-kpi-label">中性</p>
              <p class="data-kpi-value info-text">{{ getSentimentCount('neutral') }}</p>
              <p class="data-kpi-note">{{ getNeutralRate(currentReport) }}%</p>
            </article>
            <article class="data-kpi-item">
              <p class="data-kpi-label">负向</p>
              <p class="data-kpi-value danger-text">{{ getSentimentCount('negative') }}</p>
              <p class="data-kpi-note">{{ getNegativeRate(currentReport) }}%</p>
            </article>
          </div>
        </section>

        <section class="detail-block">
          <h3 class="detail-title">功能点 Top 10</h3>
          <el-table :data="currentReport.summary_json?.top_aspects || []" max-height="280">
            <el-table-column prop="aspect" label="功能点" />
            <el-table-column prop="count" label="提及次数" width="120" />
            <el-table-column label="正向率" width="120">
              <template #default="{ row }">
                <span class="positive-text">{{ row.positive_rate }}%</span>
              </template>
            </el-table-column>
          </el-table>
        </section>

        <section class="detail-block">
          <h3 class="detail-title">负面问题 Top 10</h3>
          <el-table :data="currentReport.summary_json?.top_issues || []" max-height="280">
            <el-table-column prop="keyword" label="问题关键词" />
            <el-table-column prop="frequency" label="出现频次" width="120" />
            <el-table-column prop="score" label="权重得分" width="120">
              <template #default="{ row }">
                {{ Number(row.score || 0).toFixed(2) }}
              </template>
            </el-table-column>
          </el-table>
        </section>

        <section class="detail-block">
          <h3 class="detail-title">问题词云</h3>
          <div v-if="reportWordCloudItems.length" class="word-cloud-board">
            <span
              v-for="item in reportWordCloudItems"
              :key="item.key"
              class="cloud-word"
              :style="getWordCloudStyle(item)"
            >
              {{ item.keyword }}
            </span>
          </div>
          <div v-else class="cloud-empty">暂无词云数据</div>
        </section>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { getReports, getReport, downloadReport as apiDownloadReport } from '@/api/reports'
import { ElMessage } from 'element-plus'

const loading = ref(false)
const reports = ref([])
const pagination = reactive({
  page: 1,
  per_page: 10,
  total: 0
})

const dialogVisible = ref(false)
const currentReport = ref(null)
const wordCloudPalette = ['#0f766e', '#1d4ed8', '#7c3aed', '#c2410c', '#be185d', '#0e7490', '#0369a1', '#4f46e5']

const averagePositiveRate = computed(() => {
  if (!reports.value.length) return '0.0'
  const sum = reports.value.reduce((acc, row) => acc + Number(getPositiveRate(row)), 0)
  return (sum / reports.value.length).toFixed(1)
})

const riskReportCount = computed(() => {
  return reports.value.filter(row => Number(getNegativeRate(row)) >= 30).length
})

const downloadableCount = computed(() => {
  return reports.value.filter(row => !!row.pdf_path).length
})

const reportWordCloudItems = computed(() => {
  let issues = currentReport.value?.summary_json?.top_issues || []
  if (!issues.length) {
    const aspects = currentReport.value?.summary_json?.top_aspects || []
    issues = aspects.map(item => ({
      keyword: item.aspect,
      frequency: item.count
    }))
  }
  if (!issues.length) return []

  const maxFrequency = Math.max(...issues.map(item => Number(item.frequency || 0)), 1)
  const rotations = [-8, -4, 0, 4, 8, 0]

  return issues.map((item, index) => {
    const frequency = Number(item.frequency || 0)
    const ratio = maxFrequency ? frequency / maxFrequency : 0
    return {
      key: `${item.keyword || 'word'}_${index}`,
      keyword: item.keyword || '-',
      fontSize: Math.round(14 + ratio * 20),
      rotate: rotations[index % rotations.length],
      color: wordCloudPalette[index % wordCloudPalette.length],
      opacity: (0.62 + ratio * 0.32).toFixed(2),
      paddingY: Math.round(4 + ratio * 5),
      paddingX: Math.round(8 + ratio * 10)
    }
  })
})

const loadReports = async () => {
  loading.value = true
  try {
    const res = await getReports({
      page: pagination.page,
      per_page: pagination.per_page
    })
    reports.value = res.reports
    pagination.total = res.total
  } catch (error) {
    ElMessage.error('加载报告列表失败')
  } finally {
    loading.value = false
  }
}

const viewReport = async (report) => {
  try {
    const res = await getReport(report.id)
    currentReport.value = res
    dialogVisible.value = true
  } catch (error) {
    ElMessage.error('加载报告详情失败')
  }
}

const downloadReport = async (reportId) => {
  try {
    const blob = await apiDownloadReport(reportId)
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `report_${reportId}.pdf`
    link.click()
    window.URL.revokeObjectURL(url)
    ElMessage.success('下载成功')
  } catch (error) {
    ElMessage.error('下载失败')
  }
}

const getSentimentBucket = (report, type) => {
  const dist = report?.summary_json?.sentiment_distribution
  const bucket = dist?.[type]
  const total = report?.summary_json?.total_reviews || 0

  if (typeof bucket === 'number') {
    return {
      count: bucket,
      percentage: total ? (bucket / total) * 100 : 0
    }
  }

  return {
    count: bucket?.count || 0,
    percentage: bucket?.percentage || 0
  }
}

const getSentimentCount = (type) => {
  return getSentimentBucket(currentReport.value, type).count
}

const getSentimentCountByRow = (row, type) => {
  return getSentimentBucket(row, type).count
}

const getPositiveRate = (report) => {
  return getSentimentBucket(report, 'positive').percentage.toFixed(1)
}

const getNeutralRate = (report) => {
  return getSentimentBucket(report, 'neutral').percentage.toFixed(1)
}

const getNegativeRate = (report) => {
  return getSentimentBucket(report, 'negative').percentage.toFixed(1)
}

const getWordCloudStyle = (item) => {
  return {
    fontSize: `${item.fontSize}px`,
    transform: `rotate(${item.rotate}deg)`,
    color: item.color,
    opacity: item.opacity,
    padding: `${item.paddingY}px ${item.paddingX}px`,
    fontWeight: item.fontSize >= 28 ? 700 : 600
  }
}

const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

onMounted(() => {
  loadReports()
})
</script>

<style scoped>
.reports-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.report-title-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}

.report-icon {
  width: 30px;
  height: 30px;
  border-radius: var(--radius-sm);
  background: var(--accent-dim);
  border: 1px solid rgba(37, 99, 235, 0.24);
  color: var(--accent);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.report-name {
  font-size: 13px;
  color: var(--text-primary);
  font-weight: 600;
}

.report-time {
  margin-top: 2px;
  font-size: 11px;
  color: var(--text-muted);
  font-family: 'DM Mono', monospace;
}

.sentiment-pills {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.mono-num {
  font-family: 'DM Mono', monospace;
  font-size: 12px;
}

.action-btns {
  display: flex;
  justify-content: flex-end;
  gap: 6px;
}

.table-pagination {
  margin-top: 12px;
  justify-content: flex-end;
}

.report-detail-stack {
  display: grid;
  gap: 14px;
}

.detail-block {
  display: grid;
  gap: 8px;
}

.detail-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--text-primary);
}

.report-kpi-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.word-cloud-board {
  min-height: 120px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px 12px;
  padding: 14px;
  border-radius: var(--radius-sm);
  border: 1px dashed var(--border-default);
  background:
    radial-gradient(circle at 14% 24%, rgba(37, 99, 235, 0.09), transparent 36%),
    radial-gradient(circle at 82% 78%, rgba(14, 116, 144, 0.1), transparent 36%),
    #f8fafc;
}

.cloud-word {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
  letter-spacing: 0.01em;
  border-radius: 999px;
  border: 1px solid rgba(148, 163, 184, 0.24);
  background: rgba(255, 255, 255, 0.84);
  box-shadow: 0 3px 12px rgba(15, 23, 42, 0.06);
}

.cloud-empty {
  border-radius: var(--radius-sm);
  border: 1px dashed var(--border-default);
  padding: 14px;
  color: var(--text-muted);
  font-size: 13px;
  background: #f8fafc;
}

@media (max-width: 900px) {
  .reports-head {
    flex-direction: column;
    align-items: stretch;
  }

  .reports-head .act-btn {
    width: 100%;
  }
}

@media (max-width: 768px) {
  .report-kpi-grid {
    grid-template-columns: 1fr;
  }

  .action-btns {
    justify-content: flex-start;
  }
}
</style>
