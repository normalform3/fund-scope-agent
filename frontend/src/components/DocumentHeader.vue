<script setup lang="ts">
import { ref } from "vue";
import { Loader2, Search, Wifi } from "@lucide/vue";
import type { LlmHealth } from "../api";

defineProps<{
  query: string;
  loading: boolean;
  llmStatus: LlmHealth | null;
  llmTesting: boolean;
}>();

const emit = defineEmits<{
  "update:query": [value: string];
  submit: [];
  testLlm: [];
}>();

const searchInputEl = ref<HTMLInputElement | null>(null);
const rootEl = ref<HTMLElement | null>(null);

function onInput(event: Event) {
  emit("update:query", (event.target as HTMLInputElement).value);
}

function focusSearch() {
  searchInputEl.value?.focus();
  rootEl.value?.scrollIntoView({ behavior: "smooth", block: "center" });
}

defineExpose({ focusSearch });
</script>

<template>
  <header ref="rootEl" class="document-header">
    <div class="document-kicker">Fund Analysis Workspace</div>
    <div class="document-title-row">
      <h1>FundScope Agent</h1>
      <div class="header-actions">
        <button class="header-model-test" type="button" :disabled="llmTesting" @click="$emit('testLlm')">
          <Loader2 v-if="llmTesting" class="spin" :size="15" />
          <Wifi v-else :size="15" />
          测试模型连接
        </button>
        <div v-if="llmStatus" :class="['header-model-status', llmStatus.ok ? 'ok' : 'failed']">
          <strong>{{ llmStatus.ok ? '模型可用' : '模型不可用' }}</strong>
          <span>{{ llmStatus.model }} · {{ llmStatus.message }}</span>
        </div>
        <span v-else class="document-status">MVP Workbench</span>
      </div>
    </div>
    <p>基金分析与风险体检助手。输入基金代码后生成结构化体检报告，前端只渲染真实接口返回的数据。</p>

    <form class="command-bar" @submit.prevent="$emit('submit')">
      <Search :size="18" />
      <input
        ref="searchInputEl"
        :value="query"
        aria-label="基金代码或名称"
        placeholder="搜索基金代码或名称，例如 110011"
        @input="onInput"
      />
      <button type="submit" :disabled="loading">
        <Loader2 v-if="loading" class="spin" :size="16" />
        <span>{{ loading ? '生成中' : '生成报告' }}</span>
      </button>
    </form>
  </header>
</template>
