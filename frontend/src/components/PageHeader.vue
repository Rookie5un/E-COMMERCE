<template>
  <div class="page-header">
    <div class="header-content">
      <div class="header-main">
        <h1 class="page-title">{{ title }}</h1>
        <p class="page-description" v-if="description">{{ description }}</p>
      </div>
      <div class="header-actions" v-if="$slots.actions">
        <slot name="actions"></slot>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  title: {
    type: String,
    required: true
  },
  description: {
    type: String,
    default: ''
  }
})
</script>

<style scoped lang="scss">
.page-header {
  margin-bottom: var(--space-6);
  animation: fade-in-up 0.4s ease-out both;
}

.header-content {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-6);
}

.header-main {
  flex: 1;
}

.page-title {
  font-size: var(--text-h1);
  font-weight: var(--font-bold);
  color: var(--gray-900);
  margin: 0 0 var(--space-2) 0;
  letter-spacing: var(--tracking-tight);
}

.page-description {
  font-size: var(--text-sm);
  color: var(--gray-600);
  margin: 0;
  line-height: var(--leading-relaxed);
}

.header-actions {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

// Responsive
@media (max-width: 768px) {
  .header-content {
    flex-direction: column;
    align-items: stretch;
  }

  .page-title {
    font-size: var(--text-h2);
  }

  .header-actions {
    width: 100%;
    justify-content: flex-start;
  }
}
</style>
