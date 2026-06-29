<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import * as echarts from "echarts";
import {
  AlertTriangle,
  BarChart3,
  ClipboardCheck,
  FileText,
  Gauge,
  Loader2,
  Search,
  ShieldCheck,
  Wifi
} from "@lucide/vue";
import { createFundCheckup, fetchNav, searchFunds, testLlmConnection, type FundCheckupReport, type LlmHealth, type NavPoint } from "./api";

const query = ref("110011");
const searchResults = ref<FundCheckupReport["fund"][]>([]);
const report = ref<FundCheckupReport | null>(null);
const navPoints = ref<NavPoint[]>([]);
const loading = ref(false);
const llmTesting = ref(false);
const llmStatus = ref<LlmHealth | null>(null);
const error = ref("");
const selectedTab = ref<"report" | "metrics" | "notes">("report");
const activeRail = ref<"search" | "report" | "metrics" | "compliance" | "docs">("search");
const progressValue = ref(0);
const progressMessage = ref("");
const progressSteps = ref([
  { key: "search", label: "匹配基金代码", status: "pending" },
  { key: "collect", label: "采集真实数据", status: "pending" },
  { key: "report", label: "计算指标并生成报告", status: "pending" },
  { key: "charts", label: "加载图表数据", status: "pending" },
  { key: "done", label: "完成体检", status: "pending" }
]);
let progressTimer: ReturnType<typeof setInterval> | null = null;

const navChartEl = ref<HTMLDivElement | null>(null);
const returnChartEl = ref<HTMLDivElement | null>(null);
const drawdownChartEl = ref<HTMLDivElement | null>(null);
const searchInputEl = ref<HTMLInputElement | null>(null);
const reportPaneEl = ref<HTMLElement | null>(null);
let navChart: echarts.ECharts | null = null;
let returnChart: echarts.ECharts | null = null;
let drawdownChart: echarts.ECharts | null = null;

const metricCards = computed(() => {
  const metrics = report.value?.metrics;
  return [
    ["累计收益", formatPercent(metrics?.total_return), "样本区间累计表现"],
    ["最大回撤", formatPercent(metrics?.max_drawdown), `${metrics?.max_drawdown_start ?? "--"} 至 ${metrics?.max_drawdown_trough ?? "--"}`],
    ["年化波动", formatPercent(metrics?.annualized_volatility), "由日收益率年化计算"],
    ["夏普比率", formatNumber(metrics?.sharpe_ratio), "默认 2% 无风险利率"]
  ];
});
const hasChartData = computed(() => navPoints.value.length > 0 && Boolean(report.value?.metrics));

onMounted(() => {
  window.addEventListener("resize", resizeCharts);
  runCheckup();
});

onBeforeUnmount(() => {
  stopProgressPulse();
  window.removeEventListener("resize", resizeCharts);
  disposeCharts();
});

watch([navPoints, report], async () => {
  await nextTick();
  renderCharts();
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
    setProgress("charts", "complete", 97, "图表数据加载完成");
    setProgress("done", "complete", 100, "基金体检完成");
  } catch (currentError) {
    error.value = currentError instanceof Error ? currentError.message : "请求失败";
    progressMessage.value = error.value;
  } finally {
    stopProgressPulse();
    loading.value = false;
  }
}

function resetProgress() {
  progressValue.value = 0;
  progressMessage.value = "";
  progressSteps.value = progressSteps.value.map((step) => ({ ...step, status: "pending" }));
}

function setProgress(key: string, status: "pending" | "active" | "complete", value: number, message: string) {
  progressSteps.value = progressSteps.value.map((step) => {
    if (step.key === key) return { ...step, status };
    return step;
  });
  progressValue.value = Math.max(progressValue.value, value);
  progressMessage.value = message;
}

function startProgressPulse(target: number) {
  stopProgressPulse();
  progressTimer = window.setInterval(() => {
    if (progressValue.value < target) {
      progressValue.value += progressValue.value < 55 ? 2 : 0.6;
    }
  }, 650);
}

function stopProgressPulse() {
  if (progressTimer) {
    window.clearInterval(progressTimer);
    progressTimer = null;
  }
}

async function activateRail(target: "search" | "report" | "metrics" | "compliance" | "docs") {
  activeRail.value = target;
  if (target === "search") {
    await nextTick();
    searchInputEl.value?.focus();
    searchInputEl.value?.scrollIntoView({ behavior: "smooth", block: "center" });
    return;
  }
  if (target === "report") selectedTab.value = "report";
  if (target === "metrics") selectedTab.value = "metrics";
  if (target === "compliance" || target === "docs") selectedTab.value = "notes";
  await nextTick();
  reportPaneEl.value?.scrollIntoView({ behavior: "smooth", block: "start" });
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

function renderCharts() {
  if (!navChartEl.value || !returnChartEl.value || !drawdownChartEl.value || !hasChartData.value || !report.value?.metrics) {
    return;
  }
  navChart = navChart ?? echarts.init(navChartEl.value);
  returnChart = returnChart ?? echarts.init(returnChartEl.value);
  drawdownChart = drawdownChart ?? echarts.init(drawdownChartEl.value);

  const dates = navPoints.value.map((point) => point.date);
  const nav = navPoints.value.map((point) => point.accumulated_nav);
  const start = nav[0] || 1;
  const cumulativeReturn = nav.map((value) => Number(((value / start - 1) * 100).toFixed(2)));
  const drawdownDates = report.value.metrics.drawdown_series.map((point) => point.date);
  const drawdown = report.value.metrics.drawdown_series.map((point) => Number((point.drawdown * 100).toFixed(2)));

  const commonGrid = { left: 46, right: 20, top: 22, bottom: 30 };
  const commonTooltip = {
    trigger: "axis",
    backgroundColor: "rgba(15, 23, 21, 0.92)",
    borderColor: "rgba(255, 255, 255, 0.08)",
    textStyle: { color: "#f8faf8", fontSize: 12 },
    axisPointer: { lineStyle: { color: "#0f766e", width: 1 } }
  };
  const categoryAxis = {
    type: "category",
    axisTick: { show: false },
    axisLine: { lineStyle: { color: "#d7dfdc" } },
    axisLabel: { show: false }
  };
  const valueAxis = {
    type: "value",
    scale: true,
    splitLine: { lineStyle: { color: "#e8eeeb", type: "dashed" } },
    axisLabel: { color: "#697773", fontSize: 11 }
  };
  navChart.setOption({
    grid: commonGrid,
    xAxis: { ...categoryAxis, data: dates },
    yAxis: valueAxis,
    series: [{ type: "line", data: nav, smooth: true, showSymbol: false, lineStyle: { color: "#0f766e", width: 2.4 }, emphasis: { focus: "series" } }],
    tooltip: commonTooltip
  });
  returnChart.setOption({
    grid: commonGrid,
    xAxis: { ...categoryAxis, data: dates },
    yAxis: { ...valueAxis, axisLabel: { formatter: "{value}%", color: "#697773", fontSize: 11 } },
    series: [{ type: "line", data: cumulativeReturn, smooth: true, showSymbol: false, areaStyle: { color: "rgba(15, 118, 110, 0.12)" }, lineStyle: { color: "#155e75", width: 2.4 }, emphasis: { focus: "series" } }],
    tooltip: commonTooltip
  });
  drawdownChart.setOption({
    grid: commonGrid,
    xAxis: { ...categoryAxis, data: drawdownDates },
    yAxis: { ...valueAxis, axisLabel: { formatter: "{value}%", color: "#697773", fontSize: 11 } },
    series: [{ type: "line", data: drawdown, smooth: true, showSymbol: false, areaStyle: { color: "rgba(180, 83, 9, 0.13)" }, lineStyle: { color: "#b45309", width: 2.4 }, emphasis: { focus: "series" } }],
    tooltip: commonTooltip
  });
}

function resizeCharts() {
  navChart?.resize();
  returnChart?.resize();
  drawdownChart?.resize();
}

function disposeCharts() {
  navChart?.dispose();
  returnChart?.dispose();
  drawdownChart?.dispose();
  navChart = null;
  returnChart = null;
  drawdownChart = null;
}

function formatPercent(value: number | null | undefined) {
  if (typeof value !== "number") return "--";
  return `${(value * 100).toFixed(2)}%`;
}

function formatNumber(value: number | null | undefined) {
  if (typeof value !== "number") return "--";
  return value.toFixed(2);
}
</script>

<template>
  <div class="app-shell">
    <aside class="rail">
      <div class="brand-mark">FS</div>
      <button :class="['rail-button', { active: activeRail === 'search' }]" title="基金搜索" @click="activateRail('search')"><Search :size="18" /></button>
      <button :class="['rail-button', { active: activeRail === 'report' }]" title="体检报告" @click="activateRail('report')"><ClipboardCheck :size="18" /></button>
      <button :class="['rail-button', { active: activeRail === 'metrics' }]" title="风险指标" @click="activateRail('metrics')"><Gauge :size="18" /></button>
      <button :class="['rail-button', { active: activeRail === 'compliance' }]" title="合规检查" @click="activateRail('compliance')"><ShieldCheck :size="18" /></button>
      <button :class="['rail-button', { active: activeRail === 'docs' }]" title="项目文档" @click="activateRail('docs')"><FileText :size="18" /></button>
    </aside>

    <main class="workspace">
      <header class="topbar">
        <div class="topbar-title">
          <span class="eyebrow">Fund Research Terminal</span>
          <h1>FundScope Agent</h1>
          <p>基金研究与风险匹配助手，仅供研究参考，不构成投资建议。</p>
        </div>
        <div class="top-actions">
          <button class="service-test-button" type="button" :disabled="llmTesting" @click="runLlmConnectionTest">
            <Loader2 v-if="llmTesting" class="spin" :size="16" />
            <Wifi v-else :size="16" />
            测试模型连接
          </button>
          <div class="status-chip"><ShieldCheck :size="16" /> 合规口径已启用</div>
        </div>
      </header>

      <div v-if="llmStatus" :class="['service-status', llmStatus.ok ? 'ok' : 'failed']">
        <strong>{{ llmStatus.ok ? '模型服务可用' : '模型服务不可用' }}</strong>
        <span>{{ llmStatus.model }} · {{ llmStatus.message }}</span>
      </div>

      <section class="content-grid">
        <div class="left-pane">
          <section class="search-band">
            <div class="search-copy">
              <span class="section-label">Single Fund Checkup</span>
              <h2>单只基金体检</h2>
              <p>收益 · 回撤 · 波动 · 持仓 · 合规提示</p>
            </div>
            <form class="search-form" @submit.prevent="runCheckup">
              <input ref="searchInputEl" v-model="query" aria-label="基金代码或名称" placeholder="例如 110011" />
              <button type="submit" :disabled="loading">
                <Loader2 v-if="loading" class="spin" :size="17" />
                <Search v-else :size="17" />
                生成报告
              </button>
            </form>
          </section>

          <section v-if="loading || progressValue > 0" class="progress-panel">
            <div class="progress-header">
              <strong>{{ progressMessage || '准备生成基金体检报告' }}</strong>
              <span>{{ Math.round(progressValue) }}%</span>
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

          <div v-if="error" class="error-box">
            <AlertTriangle :size="18" />
            {{ error }}
          </div>

          <section v-if="report?.fund" class="profile-strip">
            <div class="profile-heading">
              <span>基金档案摘要</span>
              <strong>{{ report.fund.name }}</strong>
            </div>
            <div>
              <span>代码</span>
              <strong>{{ report.fund.code }}</strong>
            </div>
            <div>
              <span>类型</span>
              <strong>{{ report.fund.fund_type }}</strong>
            </div>
            <div>
              <span>经理</span>
              <strong>{{ report.fund.manager }}</strong>
            </div>
            <div>
              <span>数据源</span>
              <strong>{{ report.fund.data_source || 'unknown' }}</strong>
            </div>
          </section>

          <section class="metrics-grid">
            <article v-for="card in metricCards" :key="card[0]" class="metric-card">
              <span>{{ card[0] }}</span>
              <strong>{{ card[1] }}</strong>
              <p>{{ card[2] }}</p>
            </article>
          </section>

          <section class="chart-grid">
            <article class="chart-panel">
              <h3><BarChart3 :size="17" /> 净值走势</h3>
              <div v-show="hasChartData" ref="navChartEl" class="chart-canvas"></div>
              <div v-if="!hasChartData" class="chart-empty">等待净值数据</div>
            </article>
            <article class="chart-panel">
              <h3><BarChart3 :size="17" /> 累计收益</h3>
              <div v-show="hasChartData" ref="returnChartEl" class="chart-canvas"></div>
              <div v-if="!hasChartData" class="chart-empty">等待收益曲线</div>
            </article>
            <article class="chart-panel wide">
              <h3><BarChart3 :size="17" /> 回撤曲线</h3>
              <div v-show="hasChartData" ref="drawdownChartEl" class="chart-canvas"></div>
              <div v-if="!hasChartData" class="chart-empty">等待回撤序列</div>
            </article>
          </section>
        </div>

        <aside ref="reportPaneEl" class="report-pane">
          <div v-if="report?.fund && report.metrics" class="report-body">
            <div class="conclusion">
              <span>体检结论</span>
              <strong>{{ report.conclusion }}</strong>
            </div>
            <p class="summary">{{ report.summary }}</p>

            <nav class="tabs" aria-label="报告视图">
              <button :class="{ selected: selectedTab === 'report' }" @click="selectedTab = 'report'">解释</button>
              <button :class="{ selected: selectedTab === 'metrics' }" @click="selectedTab = 'metrics'">指标</button>
              <button :class="{ selected: selectedTab === 'notes' }" @click="selectedTab = 'notes'">提示</button>
            </nav>

            <div v-if="selectedTab === 'report'" class="text-list">
              <h3>主要风险</h3>
              <p v-for="item in report.risk_notes" :key="item">{{ item }}</p>
              <h3>适合人群</h3>
              <p v-for="item in report.suitable_for" :key="item">{{ item }}</p>
              <h3>不适合人群</h3>
              <p v-for="item in report.unsuitable_for" :key="item">{{ item }}</p>
              <h3>持仓与行业</h3>
              <p v-for="item in report.holding_notes ?? []" :key="item">{{ item }}</p>
            </div>

            <div v-if="selectedTab === 'metrics'" class="metric-table">
              <div><span>观察天数</span><strong>{{ report.metrics.observation_days }}</strong></div>
              <div><span>年化收益</span><strong>{{ formatPercent(report.metrics.annualized_return) }}</strong></div>
              <div><span>卡玛比率</span><strong>{{ formatNumber(report.metrics.calmar_ratio) }}</strong></div>
              <div><span>胜率</span><strong>{{ formatPercent(report.metrics.win_rate) }}</strong></div>
            </div>

            <div v-if="selectedTab === 'notes'" class="text-list">
              <div v-if="activeRail === 'docs'" class="docs-hint">
                <strong>维护文档</strong>
                <span>README、AGENTS、PRD、ARCHITECTURE、API 和 PROJECT_STATUS 已在仓库 docs 中维护。</span>
              </div>
              <h3>前十大持仓</h3>
              <div class="compact-table" v-if="report.holdings?.length">
                <div v-for="item in report.holdings.slice(0, 10)" :key="`${item.stock_code}-${item.stock_name}`">
                  <span>{{ item.stock_name }}</span>
                  <strong>{{ item.ratio == null ? '--' : `${item.ratio.toFixed(2)}%` }}</strong>
                </div>
              </div>
              <p v-else>暂未取得真实持仓数据。</p>

              <h3>行业配置</h3>
              <div class="compact-table" v-if="report.industry_allocation?.length">
                <div v-for="item in report.industry_allocation.slice(0, 8)" :key="item.industry">
                  <span>{{ item.industry }}</span>
                  <strong>{{ item.ratio == null ? '--' : `${item.ratio.toFixed(2)}%` }}</strong>
                </div>
              </div>
              <p v-else>暂未取得真实行业配置数据。</p>

              <h3>费率与交易规则</h3>
              <div class="compact-table" v-if="report.fees?.length">
                <div v-for="item in report.fees.slice(0, 8)" :key="`${item.category}-${item.condition}-${item.value}`">
                  <span>{{ item.category }} · {{ item.condition }}</span>
                  <strong>{{ item.value }}</strong>
                </div>
              </div>
              <p v-else>暂未取得真实费率数据。</p>

              <h3>数据说明</h3>
              <p v-for="item in report.data_notes ?? []" :key="item">{{ item }}</p>
              <h3>合规提示</h3>
              <p v-for="item in report.compliance_warnings ?? []" :key="item">{{ item }}</p>
            </div>
          </div>

          <div v-else class="empty-state">
            <ClipboardCheck :size="28" />
            <strong>等待生成基金体检报告</strong>
            <span>报告将以结构化 JSON 为来源，前端只负责渲染。</span>
          </div>
        </aside>
      </section>
    </main>
  </div>
</template>
