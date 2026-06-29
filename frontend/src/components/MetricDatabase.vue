<script setup lang="ts">
defineProps<{
  cards: string[][];
}>();
</script>

<template>
  <section class="page-block metric-database">
    <div class="block-heading compact">
      <span>Risk Metrics</span>
      <strong>指标数据库</strong>
    </div>
    <div class="metric-rows">
      <article v-for="card in cards" :key="card[0]" class="metric-row">
        <div>
          <span>{{ card[0] }}</span>
          <p>{{ card[2] }}</p>
        </div>
        <strong>{{ card[1] }}</strong>
      </article>
    </div>
  </section>
</template>
