<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref } from "vue";
import { AlertTriangle } from "@lucide/vue";
import ChartWorkbench from "./components/ChartWorkbench.vue";
import DocumentHeader from "./components/DocumentHeader.vue";
import FundProfilePanel from "./components/FundProfilePanel.vue";
import MetricDatabase from "./components/MetricDatabase.vue";
import ProgressPanel from "./components/ProgressPanel.vue";
import ReportDocument from "./components/ReportDocument.vue";
import WorkspaceSidebar from "./components/WorkspaceSidebar.vue";
import { useReportProgress } from "./composables/useReportProgress";
import {
  createFundCheckup,
  fetchNav,
  searchFunds,
  testLlmConnection,
  type FundCheckupReport,
  type FundProfile,
  type LlmHealth,
  type NavPoint
} from "./api";

type ReportTab = "report" | "metrics" | "notes";

const query = ref("110011");
const searchResults = ref<FundCheckupReport["fund"][]>([]);
const report = ref<FundCheckupReport | null>(null);
const navPoints = ref<NavPoint[]>([]);
const loading = ref(false);
const llmTesting = ref(false);
const llmStatus = ref<LlmHealth | null>(null);
const error = ref("");
const selectedTab = ref<ReportTab>("report");
const documentHeader = ref<InstanceType<typeof DocumentHeader> | null>(null);
const reportPaneEl = ref<HTMLElement | null>(null);
const historyItems = ref<FundProfile[]>([]);

const {
  progressValue,
  progressMessage,
  progressSteps,
  resetProgress,
  setProgress,
  setProgressMessage,
  startProgressPulse,
  stopProgressPulse
} = useReportProgress();

const metricCards = computed<string[][]>(() => {
  const metrics = report.value?.metrics;
  return [
    ["累计收益", formatPercent(metrics?.total_return), "样本区间累计表现"],
    ["最大回撤", formatPercent(metrics?.max_drawdown), `${metrics?.max_drawdown_start ?? "--"} 至 ${metrics?.max_drawdown_trough ?? "--"}`],
    ["年化波动", formatPercent(metrics?.annualized_volatility), "由日收益率年化计算"],
    ["夏普比率", formatNumber(metrics?.sharpe_ratio), "默认 2% 基准利率"]
  ];
});

const hasReport = computed(() => Boolean(report.value?.fund && report.value.metrics));

onBeforeUnmount(() => {
  stopProgressPulse();
});

async function runCheckup() {
  const code = query.value.trim();
  if (!code) {
    error.value = "请输入基金代码或名称。";
    return;
  }

  loading.value = true;
  error.value = "";
  report.value = null;
  navPoints.value = [];
  resetProgress();

  try {
    setProgress("search", "active", 12, "正在匹配基金代码或名称");
    const found = await searchFunds(code);
    searchResults.value = found;
    const selectedCode = found[0]?.code ?? code;
    setProgress("search", "complete", 22, `已匹配基金 ${selectedCode}`);

    setProgress("collect", "active", 34, "正在采集 AKShare 档案、净值、持仓、行业和费率");
    startProgressPulse(78);
    report.value = await createFundCheckup(selectedCode);
    stopProgressPulse();

    setProgress("collect", "complete", 80, "真实数据采集完成");
    setProgress("report", "complete", 88, "风险指标和体检报告已生成");
    setProgress("charts", "active", 92, "正在加载图表净值数据");
    navPoints.value = await fetchNav(selectedCode);
    query.value = selectedCode;
    selectedTab.value = "report";
    addHistoryItem(report.value.fund);
    setProgress("charts", "complete", 97, "图表数据加载完成");
    setProgress("done", "complete", 100, "基金体检完成");
  } catch (currentError) {
    const message = currentError instanceof Error ? currentError.message : "请求失败";
    error.value = message;
    setProgressMessage(message);
  } finally {
    stopProgressPulse();
    loading.value = false;
  }
}

async function focusSearch() {
  await nextTick();
  documentHeader.value?.focusSearch();
}

async function runHistoryCheckup(code: string) {
  query.value = code;
  await nextTick();
  await runCheckup();
}

async function runLlmConnectionTest() {
  llmTesting.value = true;
  llmStatus.value = null;
  try {
    llmStatus.value = await testLlmConnection();
  } catch (currentError) {
    llmStatus.value = {
      ok: false,
      model: "unknown",
      message: currentError instanceof Error ? currentError.message : "模型服务连接测试失败"
    };
  } finally {
    llmTesting.value = false;
  }
}

function formatPercent(value: number | null | undefined) {
  if (typeof value !== "number") return "--";
  return `${(value * 100).toFixed(2)}%`;
}

function formatNumber(value: number | null | undefined) {
  if (typeof value !== "number") return "--";
  return value.toFixed(2);
}

function addHistoryItem(fund: FundProfile) {
  historyItems.value = [fund, ...historyItems.value.filter((item) => item.code !== fund.code)].slice(0, 8);
}
</script>

<template>
  <div class="app-shell">
    <WorkspaceSidebar
      :has-report="hasReport"
      :history-items="historyItems"
      @activate-search="focusSearch"
      @select-history="runHistoryCheckup"
    />

    <main class="workspace-canvas">
      <DocumentHeader
        ref="documentHeader"
        v-model:query="query"
        :llm-status="llmStatus"
        :llm-testing="llmTesting"
        :loading="loading"
        @submit="runCheckup"
        @test-llm="runLlmConnectionTest"
      />

      <div v-if="error" class="error-box">
        <AlertTriangle :size="18" />
        {{ error }}
      </div>

      <section class="workspace-grid">
        <div class="workspace-main">
          <ProgressPanel
            :has-report="hasReport"
            :progress-message="progressMessage"
            :progress-steps="progressSteps"
            :progress-value="progressValue"
          />

          <ChartWorkbench :nav-points="navPoints" :report="report" />

          <div ref="reportPaneEl">
            <ReportDocument
              v-model:selected-tab="selectedTab"
              :report="report"
            />
          </div>
        </div>

        <aside class="workspace-aside">
          <MetricDatabase :cards="metricCards" />
          <FundProfilePanel :fund="report?.fund ?? null" />
          <section class="page-block conclusion-summary">
            <div class="block-heading compact">
              <span>Conclusion</span>
              <strong>{{ report?.conclusion || '等待生成' }}</strong>
            </div>
            <p>{{ report?.summary || '生成报告后，这里会优先显示结论、风险提示和合规边界。' }}</p>
          </section>
        </aside>
      </section>
    </main>
  </div>
</template>
