<template>
  <div class="page-container">
    <!-- Page Header -->
    <PageHeader
      title="分析总览"
      description="监控当前商品评论体量、情绪结构与高频问题"
    >
      <template #actions>
        <el-select
          v-model="selectedProduct"
          placeholder="请选择商品"
          style="width: 200px; margin-right: 12px;"
          @change="handleProductChange"
        >
          <el-option
            v-for="product in products"
            :key="product.id"
            :label="product.name"
            :value="product.id"
          />
        </el-select>
        <el-button type="primary" @click="loadSummary">刷新数据</el-button>
      </template>
    </PageHeader>

    <!-- Stats Cards -->
    <section class="stats-grid fade-in-delay-1">
      <StatCard
        label="评论总数"
        :value="summary.total_reviews || 0"
        description="当前样本规模"
        :icon="ChatLineRound"
        accent-color="#3b82f6"
      />
      <StatCard
        label="正向率"
        :value="getPercentage('positive')"
        description="可转化反馈占比"
        :icon="Select"
        accent-color="#10b981"
        format="percentage"
        value-class="text-pos"
      />
      <StatCard
        label="中性率"
        :value="getPercentage('neutral')"
        description="待观察反馈占比"
        :icon="Remove"
        accent-color="#f59e0b"
        format="percentage"
        value-class="text-neu"
      />
      <StatCard
        label="负向率"
        :value="getPercentage('negative')"
        description="需处理问题占比"
        :icon="CloseBold"
        accent-color="#ef4444"
        format="percentage"
        value-class="text-neg"
      />
    </section>

    <!-- Charts Row 1 -->
    <section class="charts-row fade-in-delay-2">
      <div class="chart-box">
        <el-card class="chart-card">
          <template #header>
            <div class="card-header">
              <span class="card-title">情感分布</span>
            </div>
          </template>
          <v-chart :option="sentimentChartOption" class="chart-view" autoresize />
        </el-card>
      </div>

      <div class="chart-box">
        <el-card class="chart-card">
          <template #header>
            <div class="card-header">
              <span class="card-title">功能点提及 Top 10</span>
            </div>
          </template>
          <v-chart :option="aspectChartOption" class="chart-view" autoresize />
        </el-card>
      </div>
    </section>

    <!-- Charts Row 2 -->
    <section class="charts-row fade-in-delay-3">
      <div class="chart-box">
        <el-card class="chart-card">
          <template #header>
            <div class="card-header">
              <span class="card-title">负面问题 Top 10</span>
            </div>
          </template>
          <v-chart :option="issueChartOption" class="chart-view" autoresize />
        </el-card>
      </div>

      <div class="chart-box">
        <el-card class="chart-card">
          <template #header>
            <div class="card-header">
              <span class="card-title">关键词词云</span>
            </div>
          </template>
          <v-chart :option="wordCloudChartOption" class="chart-view word-cloud-view" autoresize />
        </el-card>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { PieChart, BarChart } from 'echarts/charts'
import { TitleComponent, TooltipComponent, LegendComponent, GridComponent } from 'echarts/components'
import 'echarts-wordcloud'
import VChart from 'vue-echarts'
import { getProducts } from '@/api/products'
import { getAnalysisSummary } from '@/api/analysis'
import { ElMessage } from 'element-plus'
import { ChatLineRound, Select, Remove, CloseBold } from '@element-plus/icons-vue'
import PageHeader from '@/components/PageHeader.vue'
import StatCard from '@/components/StatCard.vue'

use([CanvasRenderer, PieChart, BarChart, TitleComponent, TooltipComponent, LegendComponent, GridComponent])

const products = ref([])
const selectedProduct = ref(null)

const summary = reactive({
  total_reviews: 0,
  sentiment_distribution: {},
  top_aspects: [],
  top_issues: []
})

const aspectPalette = ['#2563eb', '#0891b2', '#16a34a', '#ca8a04', '#7c3aed', '#0ea5e9', '#f97316', '#14b8a6', '#6366f1', '#d946ef']
const issuePalette = ['#dc2626', '#ef4444', '#f97316', '#f59e0b', '#d97706', '#e11d48', '#be123c', '#9f1239', '#fb7185', '#f43f5e']
const wordCloudPalette = ['#f3c24f', '#0ea5a6', '#e94975', '#1086b8', '#15c39a', '#0f2f4a', '#8247e5', '#f59e0b']

const getSentimentBucket = (type) => {
  const bucket = summary.sentiment_distribution?.[type]
  if (typeof bucket === 'number') {
    return { count: bucket, percentage: summary.total_reviews ? (bucket / summary.total_reviews) * 100 : 0 }
  }
  return {
    count: bucket?.count || 0,
    percentage: bucket?.percentage || 0
  }
}

const getPercentage = (type) => {
  return getSentimentBucket(type).percentage.toFixed(1)
}

const commonAxisStyle = {
  axisLabel: {
    color: '#475569'
  },
  axisLine: {
    lineStyle: {
      color: '#cbd5e1'
    }
  },
  splitLine: {
    lineStyle: {
      color: '#e2e8f0',
      type: 'dashed'
    }
  }
}

const sentimentChartOption = computed(() => ({
  tooltip: {
    trigger: 'item',
    formatter: '{b}: {c} ({d}%)'
  },
  legend: {
    bottom: 0,
    itemWidth: 10,
    itemHeight: 10,
    textStyle: {
      color: '#64748b'
    }
  },
  series: [
    {
      type: 'pie',
      radius: ['44%', '70%'],
      center: ['50%', '45%'],
      itemStyle: {
        borderRadius: 7,
        borderColor: '#ffffff',
        borderWidth: 2
      },
      label: {
        show: false
      },
      emphasis: {
        label: {
          show: true,
          fontSize: 13,
          fontWeight: 700,
          color: '#0f172a'
        }
      },
      data: [
        {
          value: getSentimentBucket('positive').count,
          name: '正向',
          itemStyle: { color: '#16a34a' }
        },
        {
          value: getSentimentBucket('neutral').count,
          name: '中性',
          itemStyle: { color: '#ca8a04' }
        },
        {
          value: getSentimentBucket('negative').count,
          name: '负向',
          itemStyle: { color: '#dc2626' }
        }
      ]
    }
  ]
}))

const aspectChartOption = computed(() => ({
  tooltip: {
    trigger: 'axis',
    axisPointer: {
      type: 'shadow'
    }
  },
  grid: {
    left: '3%',
    right: '4%',
    bottom: '2%',
    top: '3%',
    containLabel: true
  },
  xAxis: {
    type: 'value',
    ...commonAxisStyle
  },
  yAxis: {
    type: 'category',
    axisLabel: {
      color: '#334155'
    },
    axisTick: {
      show: false
    },
    data: summary.top_aspects.map(item => item.aspect).reverse()
  },
  series: [
    {
      type: 'bar',
      barWidth: 12,
      data: summary.top_aspects.map(item => item.count).reverse(),
      itemStyle: {
        borderRadius: [0, 6, 6, 0],
        color: (params) => aspectPalette[params.dataIndex % aspectPalette.length]
      }
    }
  ]
}))

const issueChartOption = computed(() => ({
  tooltip: {
    trigger: 'axis',
    axisPointer: {
      type: 'shadow'
    }
  },
  grid: {
    left: '3%',
    right: '4%',
    bottom: '2%',
    top: '2%',
    containLabel: true
  },
  xAxis: {
    type: 'value',
    ...commonAxisStyle
  },
  yAxis: {
    type: 'category',
    axisLabel: {
      color: '#334155'
    },
    axisTick: {
      show: false
    },
    data: summary.top_issues.map(item => item.keyword).reverse()
  },
  series: [
    {
      type: 'bar',
      barWidth: 12,
      data: summary.top_issues.map(item => item.frequency).reverse(),
      itemStyle: {
        borderRadius: [0, 6, 6, 0],
        color: (params) => issuePalette[params.dataIndex % issuePalette.length]
      }
    }
  ]
}))

const wordCloudItems = computed(() => {
  let source = summary.top_issues
    .map(item => ({
      word: item.keyword,
      weight: Number(item.frequency || 0)
    }))
    .filter(item => item.word && item.weight > 0)

  if (!source.length) {
    source = summary.top_aspects
      .map(item => ({
        word: item.aspect,
        weight: Number(item.count || 0)
      }))
      .filter(item => item.word && item.weight > 0)
  }

  if (!source.length) {
    return []
  }

  const maxWeight = Math.max(...source.map(item => item.weight), 1)
  const minWeight = Math.min(...source.map(item => item.weight), maxWeight)

  return source
    .sort((a, b) => b.weight - a.weight)
    .slice(0, 24)
    .map((item) => {
      const ratio = maxWeight === minWeight ? 1 : (item.weight - minWeight) / (maxWeight - minWeight)
      return {
        word: item.word,
        weight: item.weight,
        ratio,
        value: Math.round(26 + ratio * 146)
      }
    })
})

const buildWordCloudSeriesData = (items) => {
  const series = []

  items.forEach((item, index) => {
    const color = wordCloudPalette[index % wordCloudPalette.length]
    const baseName = item.word
    const baseValue = item.value

    series.push({
      name: baseName,
      value: baseValue,
      textStyle: {
        color
      }
    })

    const duplicateCount = index < 4 ? 3 : index < 8 ? 2 : 1
    for (let i = 0; i < duplicateCount; i += 1) {
      const downScale = 0.54 - i * 0.12
      const duplicateValue = Math.max(12, Math.round(baseValue * downScale))
      series.push({
        // 用零宽字符制造“视觉相同”的重复词，形成更饱满的词云排布
        name: `${baseName}${'\u200b'.repeat(i + 1)}${'\u200c'.repeat(index + 1)}`,
        value: duplicateValue,
        textStyle: {
          color: wordCloudPalette[(index + i + 2) % wordCloudPalette.length]
        }
      })
    }
  })

  return series.sort((a, b) => b.value - a.value)
}

const wordCloudChartOption = computed(() => {
  const rawItems = wordCloudItems.value
  const data = buildWordCloudSeriesData(rawItems)

  return {
    tooltip: {
      formatter: (params) => {
        const text = String(params.name || '').replace(/[\u200b\u200c]/g, '')
        return `${text}：${params.value}`
      }
    },
    graphic: !data.length
      ? [
          {
            type: 'text',
            left: 'center',
            top: 'middle',
            style: {
              text: '暂无词云数据',
              fill: '#94a3b8',
              fontSize: 14,
              fontWeight: 600
            }
          }
        ]
      : [],
    series: [
      {
        type: 'wordCloud',
        shape: 'circle',
        left: 'center',
        top: 'center',
        width: '98%',
        height: '96%',
        keepAspect: true,
        sizeRange: [14, 120],
        rotationRange: [-90, 90],
        rotationStep: 45,
        gridSize: 3,
        drawOutOfBound: false,
        shrinkToFit: true,
        layoutAnimation: true,
        textStyle: {
          fontFamily: '"PingFang SC","Microsoft YaHei","Source Han Sans SC",sans-serif',
          fontWeight: 'bold'
        },
        emphasis: {
          focus: 'self',
          textStyle: {
            textShadowBlur: 10,
            textShadowColor: 'rgba(15, 23, 42, 0.28)'
          }
        },
        data
      }
    ]
  }
})

const loadProducts = async () => {
  try {
    const res = await getProducts({ per_page: 100 })
    products.value = res.products
    if (products.value.length > 0) {
      selectedProduct.value = products.value[0].id
      loadSummary()
    }
  } catch (error) {
    ElMessage.error('加载商品列表失败')
  }
}

const loadSummary = async () => {
  if (!selectedProduct.value) return

  try {
    const res = await getAnalysisSummary({ product_id: selectedProduct.value })
    Object.assign(summary, res)
  } catch (error) {
    ElMessage.error('加载分析数据失败')
  }
}

const handleProductChange = () => {
  loadSummary()
}

onMounted(() => {
  loadProducts()
})
</script>

<style scoped lang="scss">
.page-container {
  animation: fade-in-up 0.4s ease-out both;
}

// Stats Grid
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: var(--space-6);
  margin-bottom: var(--space-8);
}

// Charts Layout
.charts-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
  gap: var(--space-6);
  margin-bottom: var(--space-6);
}

.chart-box {
  min-width: 0;
}

.chart-card {
  height: 100%;
  transition: all var(--transition-slow);

  &:hover {
    transform: translateY(-2px);
  }
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
}

.chart-view {
  height: 320px;
  width: 100%;
}

.word-cloud-view {
  height: 360px;
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  border-radius: var(--radius-md);
}

// Responsive
@media (max-width: 1024px) {
  .charts-row {
    grid-template-columns: 1fr;
  }

  .chart-view {
    height: 280px;
  }

  .word-cloud-view {
    height: 300px;
  }
}

@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: 1fr;
    gap: var(--space-4);
  }

  .charts-row {
    gap: var(--space-4);
  }

  .chart-view {
    height: 240px;
  }

  .word-cloud-view {
    height: 260px;
  }
}
</style>
