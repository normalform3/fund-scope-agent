<script setup lang="ts">
import type { FundProfile } from "../api";

defineProps<{
  fund: FundProfile | null;
}>();
</script>

<template>
  <section class="page-block profile-panel">
    <div class="block-heading compact">
      <span>Fund Profile</span>
      <strong>{{ fund?.name || '基金档案' }}</strong>
    </div>

    <div v-if="fund" class="profile-grid">
      <div>
        <span>代码</span>
        <strong>{{ fund.code }}</strong>
      </div>
      <div>
        <span>类型</span>
        <strong>{{ fund.fund_type }}</strong>
      </div>
      <div>
        <span>经理</span>
        <strong>{{ fund.manager }}</strong>
      </div>
      <div>
        <span>基金公司</span>
        <strong>{{ fund.company }}</strong>
      </div>
      <div>
        <span>规模</span>
        <strong>{{ fund.scale }}</strong>
      </div>
      <div>
        <span>数据源</span>
        <strong>{{ fund.data_source || 'unknown' }}</strong>
      </div>
    </div>

    <div v-else class="panel-empty">生成报告后显示基金档案。</div>
  </section>
</template>
