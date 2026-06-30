<script setup lang="ts">
import {
  Compass,
  Moon,
  Search,
  ShieldCheck,
  Sun
} from "@lucide/vue";
import type { FundProfile } from "../api";

type WorkspaceView = "discovery" | "analysis";
type ThemeMode = "light" | "dark";

defineProps<{
  activeView: WorkspaceView;
  activeTheme: ThemeMode;
  hasReport: boolean;
  historyItems: FundProfile[];
}>();

defineEmits<{
  navigate: [view: WorkspaceView];
  selectHistory: [code: string];
  toggleTheme: [];
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
        :class="['page-nav-item', activeView === 'discovery' ? 'active' : '']"
        type="button"
        @click="$emit('navigate', 'discovery')"
      >
        <Compass :size="16" />
        <span>寻找基金</span>
      </button>
      <button
        :class="['page-nav-item', activeView === 'analysis' ? 'active' : '']"
        type="button"
        @click="$emit('navigate', 'analysis')"
      >
        <Search :size="16" />
        <span>基金分析</span>
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

    <div class="sidebar-section theme-section">
      <span class="sidebar-label">Appearance</span>
      <button class="theme-toggle" type="button" @click="$emit('toggleTheme')">
        <span class="theme-toggle-icon">
          <Sun v-if="activeTheme === 'dark'" :size="15" />
          <Moon v-else :size="15" />
        </span>
        <span>{{ activeTheme === 'dark' ? '切换浅色模式' : '切换深色模式' }}</span>
      </button>
    </div>

    <div class="sidebar-footer">
      <ShieldCheck :size="15" />
      <span>合规口径已启用</span>
    </div>
  </aside>
</template>
