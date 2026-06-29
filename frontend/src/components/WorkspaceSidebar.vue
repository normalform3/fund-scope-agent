<script setup lang="ts">
import {
  Search,
  ShieldCheck
} from "@lucide/vue";
import type { FundProfile } from "../api";

defineProps<{
  hasReport: boolean;
  historyItems: FundProfile[];
}>();

defineEmits<{
  activateSearch: [];
  selectHistory: [code: string];
}>();
</script>

<template>
  <aside class="workspace-sidebar">
    <div class="sidebar-brand">
      <div class="brand-page">FS</div>
      <div>
        <strong>FundScope</strong>
        <span>Research Desk</span>
      </div>
    </div>

    <nav class="page-nav" aria-label="工作区导航">
      <button
        class="page-nav-item active"
        type="button"
        @click="$emit('activateSearch')"
      >
        <Search :size="16" />
        <span>基金检索</span>
      </button>
    </nav>

    <div class="sidebar-section">
      <span class="sidebar-label">History</span>
      <div v-if="historyItems.length" class="history-list">
        <button
          v-for="item in historyItems"
          :key="item.code"
          class="history-item"
          type="button"
          @click="$emit('selectHistory', item.code)"
        >
          <strong>{{ item.name }}</strong>
          <span>{{ item.code }} · {{ item.fund_type }}</span>
        </button>
      </div>
      <div v-else class="history-empty">成功生成过的基金会保存在这里。</div>
    </div>

    <div class="sidebar-section">
      <span class="sidebar-label">Workspace</span>
      <div class="sidebar-note">
        <strong>{{ hasReport ? '报告已生成' : '等待输入基金代码' }}</strong>
        <span>仅供研究参考，不构成投资建议。</span>
      </div>
    </div>

    <div class="sidebar-footer">
      <ShieldCheck :size="15" />
      <span>合规口径已启用</span>
    </div>
  </aside>
</template>
