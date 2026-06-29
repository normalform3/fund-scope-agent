<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, toRefs } from "vue";
import { BarChart3 } from "@lucide/vue";
import type { FundCheckupReport, NavPoint } from "../api";
import { chartRangeOptions, useFundCharts, type ChartKind, type ChartRange } from "../composables/useFundCharts";

const props = defineProps<{
  navPoints: NavPoint[];
  report: FundCheckupReport | null;
}>();

const { navPoints, report } = toRefs(props);
const selectedChart = ref<ChartKind>("nav");
const selectedRange = ref<ChartRange>("1y");
const {
  navChartEl,
  returnChartEl,
  drawdownChartEl,
  hasChartData,
  resizeCharts
} = useFundCharts({ navPoints, report, selectedChart, selectedRange });

const chartTabs = [
  { key: "nav", label: "净值" },
  { key: "return", label: "累计收益" },
  { key: "drawdown", label: "回撤" }
] as const;

const activeChartLabel = computed(() => chartTabs.find((item) => item.key === selectedChart.value)?.label ?? "净值");

onMounted(() => {
  window.addEventListener("resize", resizeCharts);
});

onBeforeUnmount(() => {
  window.removeEventListener("resize", resizeCharts);
});

function selectChart(chart: ChartKind) {
  selectedChart.value = chart;
}

function selectRange(range: ChartRange) {
  selectedRange.value = range;
}
</script>

<template>
  <section class="page-block chart-workbench">
    <div class="chart-header">
      <div class="block-heading compact">
        <span>Chart View</span>
        <strong><BarChart3 :size="16" /> {{ activeChartLabel }}</strong>
      </div>
      <div class="chart-controls">
        <div class="segmented-control" aria-label="图表视图">
          <button
            v-for="tab in chartTabs"
            :key="tab.key"
            :class="{ selected: selectedChart === tab.key }"
            type="button"
            @click="selectChart(tab.key)"
          >
            {{ tab.label }}
          </button>
        </div>
        <div class="segmented-control range" aria-label="时间区间">
          <button
            v-for="option in chartRangeOptions"
            :key="option.key"
            :class="{ selected: selectedRange === option.key }"
            type="button"
            @click="selectRange(option.key)"
          >
            {{ option.label }}
          </button>
        </div>
      </div>
    </div>

    <div v-show="hasChartData && selectedChart === 'nav'" ref="navChartEl" class="chart-canvas"></div>
    <div v-show="hasChartData && selectedChart === 'return'" ref="returnChartEl" class="chart-canvas"></div>
    <div v-show="hasChartData && selectedChart === 'drawdown'" ref="drawdownChartEl" class="chart-canvas"></div>
    <div v-if="!hasChartData" class="chart-empty">输入基金代码并生成报告后显示净值、收益和回撤曲线</div>
  </section>
</template>
