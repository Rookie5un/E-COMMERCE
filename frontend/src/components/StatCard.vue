<template>
  <div class="stat-card hover-lift" :style="cardStyle">
    <div class="stat-accent-bar" :style="accentBarStyle"></div>
    <div class="stat-content">
      <div class="stat-icon" :style="iconStyle">
        <el-icon :size="24">
          <component :is="icon" />
        </el-icon>
      </div>
      <div class="stat-info">
        <div class="stat-label">{{ label }}</div>
        <div class="stat-value" :class="valueClass">{{ formattedValue }}</div>
        <div class="stat-description" v-if="description">{{ description }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  label: {
    type: String,
    required: true
  },
  value: {
    type: [Number, String],
    required: true
  },
  description: {
    type: String,
    default: ''
  },
  icon: {
    type: Object,
    required: true
  },
  accentColor: {
    type: String,
    default: '#3b82f6'
  },
  valueClass: {
    type: String,
    default: ''
  },
  format: {
    type: String,
    default: 'number' // 'number', 'percentage', 'currency'
  }
})

const cardStyle = computed(() => ({
  '--card-accent': props.accentColor
}))

const accentBarStyle = computed(() => ({
  background: `linear-gradient(90deg, ${props.accentColor}, ${props.accentColor}88)`
}))

const iconStyle = computed(() => ({
  background: `linear-gradient(135deg, ${props.accentColor}, ${props.accentColor}cc)`
}))

const formattedValue = computed(() => {
  const val = props.value

  if (props.format === 'percentage') {
    return typeof val === 'number' ? `${val.toFixed(1)}%` : val
  }

  if (props.format === 'currency') {
    return typeof val === 'number' ? `¥${val.toLocaleString()}` : val
  }

  // Default number format
  return typeof val === 'number' ? val.toLocaleString() : val
})
</script>

<style scoped lang="scss">
.stat-card {
  position: relative;
  background: var(--white-pure);
  border: 1px solid rgba(226, 232, 240, 0.8);
  border-radius: var(--radius-lg);
  padding: var(--space-6);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
  transition: all var(--transition-slow);
  cursor: default;

  &:hover {
    box-shadow: var(--shadow-lg);
    transform: translateY(-4px);
  }
}

.stat-accent-bar {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  border-radius: var(--radius-lg) var(--radius-lg) 0 0;
}

.stat-content {
  display: flex;
  align-items: flex-start;
  gap: var(--space-4);
}

.stat-icon {
  flex-shrink: 0;
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-md);
  color: var(--white-pure);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.stat-info {
  flex: 1;
  min-width: 0;
}

.stat-label {
  font-size: var(--text-sm);
  color: var(--gray-600);
  font-weight: var(--font-medium);
  margin-bottom: var(--space-2);
}

.stat-value {
  font-size: 32px;
  font-weight: var(--font-semibold);
  color: var(--gray-900);
  font-family: var(--font-mono);
  line-height: 1.2;
  margin-bottom: var(--space-1);

  &.text-pos {
    color: var(--success);
  }

  &.text-neu {
    color: var(--warning);
  }

  &.text-neg {
    color: var(--danger);
  }
}

.stat-description {
  font-size: var(--text-xs);
  color: var(--gray-500);
  line-height: var(--leading-relaxed);
}

// Responsive
@media (max-width: 768px) {
  .stat-card {
    padding: var(--space-5);
  }

  .stat-content {
    gap: var(--space-3);
  }

  .stat-icon {
    width: 40px;
    height: 40px;

    :deep(.el-icon) {
      font-size: 20px;
    }
  }

  .stat-value {
    font-size: 24px;
  }
}
</style>
