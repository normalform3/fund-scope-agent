import { computed, nextTick, onBeforeUnmount, ref, watch, type Ref } from "vue";
import * as echarts from "echarts";
import type { FundCheckupReport, NavPoint } from "../api";

export type ChartKind = "nav" | "return" | "drawdown";
export type ChartRange = "3m" | "6m" | "1y" | "3y" | "all";

export const chartRangeOptions = [
  { key: "3m", label: "3个月" },
  { key: "6m", label: "6个月" },
  { key: "1y", label: "1年" },
  { key: "3y", label: "3年" },
  { key: "all", label: "全部" }
] as const;

export function useFundCharts(args: {
  navPoints: Ref<NavPoint[]>;
  report: Ref<FundCheckupReport | null>;
  selectedChart: Ref<ChartKind>;
  selectedRange: Ref<ChartRange>;
}) {
  const navChartEl = ref<HTMLDivElement | null>(null);
  const returnChartEl = ref<HTMLDivElement | null>(null);
  const drawdownChartEl = ref<HTMLDivElement | null>(null);
  const hasChartData = computed(() => args.navPoints.value.length > 0 && Boolean(args.report.value?.metrics));
  const visibleNavPoints = computed(() => filterNavPointsByRange(args.navPoints.value, args.selectedRange.value));

  let navChart: echarts.ECharts | null = null;
  let returnChart: echarts.ECharts | null = null;
  let drawdownChart: echarts.ECharts | null = null;
  let themeObserver: MutationObserver | null = null;

  if (typeof MutationObserver !== "undefined") {
    themeObserver = new MutationObserver(() => {
      renderCharts();
      resizeCharts();
    });
    themeObserver.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
  }

  watch([args.navPoints, args.report], async () => {
    await nextTick();
    renderCharts();
  });

  watch(args.selectedChart, async () => {
    await nextTick();
    resizeCharts();
  });

  watch(args.selectedRange, async () => {
    await nextTick();
    renderCharts();
  });

  onBeforeUnmount(() => {
    disposeCharts();
  });

  function renderCharts() {
    if (!navChartEl.value || !returnChartEl.value || !drawdownChartEl.value || !hasChartData.value) {
      return;
    }

    navChart = navChart ?? echarts.init(navChartEl.value);
    returnChart = returnChart ?? echarts.init(returnChartEl.value);
    drawdownChart = drawdownChart ?? echarts.init(drawdownChartEl.value);

    const points = visibleNavPoints.value;
    const dates = points.map((point) => point.date);
    const nav = points.map((point) => point.accumulated_nav);
    const start = nav[0] || 1;
    const cumulativeReturn = nav.map((value) => Number(((value / start - 1) * 100).toFixed(2)));
    let peak = nav[0] || 1;
    const drawdown = nav.map((value) => {
      peak = Math.max(peak, value);
      return Number(((value / peak - 1) * 100).toFixed(2));
    });

    const theme = getChartTheme();
    const commonGrid = { left: 46, right: 18, top: 22, bottom: 28 };
    const commonTooltip = {
      trigger: "axis",
      backgroundColor: theme.tooltipBackground,
      borderColor: theme.tooltipBorder,
      textStyle: { color: theme.tooltipText, fontSize: 12 },
      axisPointer: { lineStyle: { color: theme.accent, width: 1 } }
    };
    const categoryAxis = {
      type: "category",
      axisTick: { show: false },
      axisLine: { lineStyle: { color: theme.axis } },
      axisLabel: { show: false }
    };
    const valueAxis = {
      type: "value",
      scale: true,
      splitLine: { lineStyle: { color: theme.splitLine, type: "dashed" } },
      axisLabel: { color: theme.mutedText, fontSize: 11 }
    };

    navChart.setOption({
      grid: commonGrid,
      xAxis: { ...categoryAxis, data: dates },
      yAxis: valueAxis,
      series: [{ type: "line", data: nav, smooth: true, showSymbol: false, lineStyle: { color: theme.accent, width: 2.3 }, emphasis: { focus: "series" } }],
      tooltip: commonTooltip
    });
    returnChart.setOption({
      grid: commonGrid,
      xAxis: { ...categoryAxis, data: dates },
      yAxis: { ...valueAxis, axisLabel: { formatter: "{value}%", color: theme.mutedText, fontSize: 11 } },
      series: [{ type: "line", data: cumulativeReturn, smooth: true, showSymbol: false, areaStyle: { color: theme.tealArea }, lineStyle: { color: theme.teal, width: 2.3 }, emphasis: { focus: "series" } }],
      tooltip: commonTooltip
    });
    drawdownChart.setOption({
      grid: commonGrid,
      xAxis: { ...categoryAxis, data: dates },
      yAxis: { ...valueAxis, axisLabel: { formatter: "{value}%", color: theme.mutedText, fontSize: 11 } },
      series: [{ type: "line", data: drawdown, smooth: true, showSymbol: false, areaStyle: { color: theme.warningArea }, lineStyle: { color: theme.warning, width: 2.3 }, emphasis: { focus: "series" } }],
      tooltip: commonTooltip
    });
  }

  function resizeCharts() {
    navChart?.resize();
    returnChart?.resize();
    drawdownChart?.resize();
  }

  function disposeCharts() {
    themeObserver?.disconnect();
    navChart?.dispose();
    returnChart?.dispose();
    drawdownChart?.dispose();
    themeObserver = null;
    navChart = null;
    returnChart = null;
    drawdownChart = null;
  }

  return {
    navChartEl,
    returnChartEl,
    drawdownChartEl,
    hasChartData,
    renderCharts,
    resizeCharts,
    disposeCharts
  };
}

function getChartTheme() {
  const style = getComputedStyle(document.documentElement);
  const read = (name: string, fallback: string) => style.getPropertyValue(name).trim() || fallback;
  const theme = document.documentElement.dataset.theme;
  return {
    accent: read("--accent", "#5c6ad2"),
    teal: read("--teal", "#18b8a7"),
    warning: read("--warning", "#b8782f"),
    axis: read("--border-strong", "rgba(34, 39, 53, 0.18)"),
    splitLine: read("--border", "rgba(34, 39, 53, 0.1)"),
    mutedText: read("--muted-text", "#68707f"),
    tooltipBackground: theme === "dark" ? "rgba(10, 11, 16, 0.96)" : "rgba(23, 25, 31, 0.95)",
    tooltipBorder: read("--border-strong", "rgba(236, 239, 247, 0.18)"),
    tooltipText: "#f7f8fb",
    tealArea: theme === "dark" ? "rgba(43, 208, 188, 0.16)" : "rgba(24, 184, 167, 0.12)",
    warningArea: theme === "dark" ? "rgba(225, 163, 91, 0.16)" : "rgba(184, 120, 47, 0.12)"
  };
}

function filterNavPointsByRange(points: NavPoint[], range: ChartRange) {
  if (range === "all" || points.length === 0) return points;
  const latest = new Date(points[points.length - 1].date);
  if (Number.isNaN(latest.getTime())) return points;
  const cutoff = new Date(latest);
  const monthsByRange = { "3m": 3, "6m": 6, "1y": 12, "3y": 36 } as const;
  cutoff.setMonth(cutoff.getMonth() - monthsByRange[range]);
  const filtered = points.filter((point) => {
    const current = new Date(point.date);
    return !Number.isNaN(current.getTime()) && current >= cutoff;
  });
  return filtered.length > 0 ? filtered : points;
}
