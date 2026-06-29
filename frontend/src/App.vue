<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from "vue";
import * as echarts from "echarts";
import {
  AlertTriangle,
  BarChart3,
  ClipboardCheck,
  FileText,
  Gauge,
  Loader2,
  Search,
  ShieldCheck
} from "@lucide/vue";
import { createFundCheckup, fetchNav, searchFunds, type FundCheckupReport, type NavPoint } from "./api";

const query = ref("110011");
const searchResults = ref<FundCheckupReport["fund"][]>([]);
const report = ref<FundCheckupReport | null>(null);
const navPoints = ref<NavPoint[]>([]);
const loading = ref(false);
const error = ref("");
const selectedTab = ref<"report" | "metrics" | "notes">("report");

const navChartEl = ref<HTMLDivElement | null>(null);
const returnChartEl = ref<HTMLDivElement | null>(null);
const drawdownChartEl = ref<HTMLDivElement | null>(null);
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

onMounted(() => {
  runCheckup();
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
  try {
    const found = await searchFunds(code);
    searchResults.value = found;
    const selectedCode = found[0]?.code ?? code;
    report.value = await createFundCheckup(selectedCode);
    navPoints.value = await fetchNav(selectedCode);
    query.value = selectedCode;
  } catch (currentError) {
    error.value = currentError instanceof Error ? currentError.message : "请求失败";
  } finally {
    loading.value = false;
  }
}

function renderCharts() {
  if (!navChartEl.value || !returnChartEl.value || !drawdownChartEl.value || !navPoints.value.length || !report.value) {
    return;
  }
  navChart = navChart ?? echarts.init(navChartEl.value);
  returnChart = returnChart ?? echarts.init(returnChartEl.value);
  drawdownChart = drawdownChart ?? echarts.init(drawdownChartEl.value);

  const dates = navPoints.value.map((point) => point.date);
  const nav = navPoints.value.map((point) => point.accumulated_nav);
  const start = nav[0] || 1;
  const cumulativeReturn = nav.map((value) => Number(((value / start - 1) * 100).toFixed(2)));
  const drawdown = report.value.metrics.drawdown_series.map((point) => Number((point.drawdown * 100).toFixed(2)));

  const commonGrid = { left: 42, right: 18, top: 24, bottom: 28 };
  navChart.setOption({
    grid: commonGrid,
    xAxis: { type: "category", data: dates, axisLabel: { show: false } },
    yAxis: { type: "value", scale: true },
    series: [{ type: "line", data: nav, smooth: true, showSymbol: false, lineStyle: { color: "#0f766e", width: 2 } }],
    tooltip: { trigger: "axis" }
  });
  returnChart.setOption({
    grid: commonGrid,
    xAxis: { type: "category", data: dates, axisLabel: { show: false } },
    yAxis: { type: "value", axisLabel: { formatter: "{value}%" } },
    series: [{ type: "line", data: cumulativeReturn, smooth: true, showSymbol: false, areaStyle: { color: "rgba(15, 118, 110, 0.1)" }, lineStyle: { color: "#155e75", width: 2 } }],
    tooltip: { trigger: "axis" }
  });
  drawdownChart.setOption({
    grid: commonGrid,
    xAxis: { type: "category", data: dates, axisLabel: { show: false } },
    yAxis: { type: "value", axisLabel: { formatter: "{value}%" } },
    series: [{ type: "line", data: drawdown, smooth: true, showSymbol: false, areaStyle: { color: "rgba(217, 119, 6, 0.12)" }, lineStyle: { color: "#d97706", width: 2 } }],
    tooltip: { trigger: "axis" }
  });
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
      <div class="brand-mark">F</div>
      <button class="rail-button active" title="基金搜索"><Search :size="18" /></button>
      <button class="rail-button" title="体检报告"><ClipboardCheck :size="18" /></button>
      <button class="rail-button" title="风险指标"><Gauge :size="18" /></button>
      <button class="rail-button" title="合规检查"><ShieldCheck :size="18" /></button>
      <button class="rail-button" title="项目文档"><FileText :size="18" /></button>
    </aside>

    <main class="workspace">
      <header class="topbar">
        <div>
          <h1>FundScope Agent</h1>
          <p>基金研究与风险匹配助手，仅供研究参考，不构成投资建议。</p>
        </div>
        <div class="status-chip"><ShieldCheck :size="16" /> 合规口径已启用</div>
      </header>

      <section class="content-grid">
        <div class="left-pane">
          <section class="search-band">
            <div>
              <h2>单只基金体检</h2>
              <p>输入基金代码或名称，生成收益、回撤、波动和风险解释。</p>
            </div>
            <form class="search-form" @submit.prevent="runCheckup">
              <input v-model="query" aria-label="基金代码或名称" placeholder="例如 110011" />
              <button type="submit" :disabled="loading">
                <Loader2 v-if="loading" class="spin" :size="17" />
                <Search v-else :size="17" />
                生成报告
              </button>
            </form>
          </section>

          <div v-if="error" class="error-box">
            <AlertTriangle :size="18" />
            {{ error }}
          </div>

          <section v-if="report" class="profile-strip">
            <div>
              <span>基金名称</span>
              <strong>{{ report.fund.name }}</strong>
            </div>
            <div>
              <span>基金代码</span>
              <strong>{{ report.fund.code }}</strong>
            </div>
            <div>
              <span>基金类型</span>
              <strong>{{ report.fund.fund_type }}</strong>
            </div>
            <div>
              <span>基金经理</span>
              <strong>{{ report.fund.manager }}</strong>
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
              <div ref="navChartEl" class="chart-canvas"></div>
            </article>
            <article class="chart-panel">
              <h3><BarChart3 :size="17" /> 累计收益</h3>
              <div ref="returnChartEl" class="chart-canvas"></div>
            </article>
            <article class="chart-panel wide">
              <h3><BarChart3 :size="17" /> 回撤曲线</h3>
              <div ref="drawdownChartEl" class="chart-canvas"></div>
            </article>
          </section>
        </div>

        <aside class="report-pane">
          <div v-if="report" class="report-body">
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
            </div>

            <div v-if="selectedTab === 'metrics'" class="metric-table">
              <div><span>观察天数</span><strong>{{ report.metrics.observation_days }}</strong></div>
              <div><span>年化收益</span><strong>{{ formatPercent(report.metrics.annualized_return) }}</strong></div>
              <div><span>卡玛比率</span><strong>{{ formatNumber(report.metrics.calmar_ratio) }}</strong></div>
              <div><span>胜率</span><strong>{{ formatPercent(report.metrics.win_rate) }}</strong></div>
            </div>

            <div v-if="selectedTab === 'notes'" class="text-list">
              <h3>数据说明</h3>
              <p v-for="item in report.data_notes" :key="item">{{ item }}</p>
              <h3>合规提示</h3>
              <p v-for="item in report.compliance_warnings" :key="item">{{ item }}</p>
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
