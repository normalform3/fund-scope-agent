<script setup lang="ts">
import type { ProgressStep } from "../composables/useReportProgress";

defineProps<{
  hasReport: boolean;
  progressMessage: string;
  progressSteps: ProgressStep[];
  progressValue: number;
}>();
</script>

<template>
  <section class="page-block progress-block">
    <div class="block-heading">
      <span>Analysis Status</span>
      <strong>{{ progressMessage || (hasReport ? '基金体检完成' : '等待输入基金代码') }}</strong>
    </div>
    <div class="progress-track">
      <div class="progress-fill" :style="{ width: `${progressValue}%` }"></div>
    </div>
    <div class="progress-steps">
      <span v-for="step in progressSteps" :key="step.key" :class="step.status">
        {{ step.label }}
      </span>
    </div>
  </section>
</template>
