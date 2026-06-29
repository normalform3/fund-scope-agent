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

    const commonGrid = { left: 46, right: 18, top: 22, bottom: 28 };
    const commonTooltip = {
      trigger: "axis",
      backgroundColor: "rgba(33, 49, 63, 0.94)",
      borderColor: "rgba(255, 255, 255, 0.08)",
      textStyle: { color: "#f7fafb", fontSize: 12 },
      axisPointer: { lineStyle: { color: "#4ea8de", width: 1 } }
    };
    const categoryAxis = {
      type: "category",
      axisTick: { show: false },
      axisLine: { lineStyle: { color: "#d9e3e8" } },
      axisLabel: { show: false }
    };
    const valueAxis = {
      type: "value",
      scale: true,
      splitLine: { lineStyle: { color: "#e7eef1", type: "dashed" } },
      axisLabel: { color: "#64717c", fontSize: 11 }
    };

    navChart.setOption({
      grid: commonGrid,
      xAxis: { ...categoryAxis, data: dates },
      yAxis: valueAxis,
      series: [{ type: "line", data: nav, smooth: true, showSymbol: false, lineStyle: { color: "#4ea8de", width: 2.3 }, emphasis: { focus: "series" } }],
      tooltip: commonTooltip
    });
    returnChart.setOption({
      grid: commonGrid,
      xAxis: { ...categoryAxis, data: dates },
      yAxis: { ...valueAxis, axisLabel: { formatter: "{value}%", color: "#64717c", fontSize: 11 } },
      series: [{ type: "line", data: cumulativeReturn, smooth: true, showSymbol: false, areaStyle: { color: "rgba(40, 199, 183, 0.12)" }, lineStyle: { color: "#28c7b7", width: 2.3 }, emphasis: { focus: "series" } }],
      tooltip: commonTooltip
    });
    drawdownChart.setOption({
      grid: commonGrid,
      xAxis: { ...categoryAxis, data: dates },
      yAxis: { ...valueAxis, axisLabel: { formatter: "{value}%", color: "#64717c", fontSize: 11 } },
      series: [{ type: "line", data: drawdown, smooth: true, showSymbol: false, areaStyle: { color: "rgba(176, 109, 52, 0.12)" }, lineStyle: { color: "#b06d34", width: 2.3 }, emphasis: { focus: "series" } }],
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
