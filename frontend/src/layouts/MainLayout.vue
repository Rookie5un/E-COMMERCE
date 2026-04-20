<template>
  <div class="main-layout">
    <!-- Top Navigation Bar -->
    <TopNavbar />

    <!-- Main Content Area -->
    <main class="main-content">
      <div class="content-container">
        <router-view v-slot="{ Component }">
          <transition name="page" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </div>
    </main>
  </div>
</template>

<script setup>
import TopNavbar from '@/components/TopNavbar.vue'
</script>

<style scoped lang="scss">
.main-layout {
  min-height: 100vh;
  background: var(--gray-50);
  position: relative;
}

.main-content {
  padding-top: var(--navbar-height);
  min-height: 100vh;
  background: radial-gradient(ellipse at top, rgba(59, 130, 246, 0.05), transparent 50%);
}

.content-container {
  max-width: var(--content-max-width);
  margin: 0 auto;
  padding: var(--content-padding-y) var(--content-padding-x);
}

// Page Transitions
.page-enter-active,
.page-leave-active {
  transition: all 0.3s ease;
}

.page-enter-from {
  opacity: 0;
  transform: translateY(10px);
}

.page-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

// Responsive
@media (max-width: 1024px) {
  .content-container {
    padding: var(--space-6) var(--space-4);
  }
}

@media (max-width: 768px) {
  .content-container {
    padding: var(--space-5) var(--space-4);
  }
}
</style>
