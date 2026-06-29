<script setup lang="ts">
import { ClipboardCheck } from "@lucide/vue";
import type { FundCheckupReport } from "../api";

defineProps<{
  report: FundCheckupReport | null;
  selectedTab: "report" | "metrics" | "notes";
}>();

defineEmits<{
  "update:selectedTab": ["report" | "metrics" | "notes"];
}>();

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
  <section class="report-document">
    <div v-if="report?.fund && report.metrics" class="report-page">
      <div class="report-cover">
        <span class="document-kicker">Single Fund Checkup</span>
        <h2>{{ report.fund.name }}</h2>
        <p>{{ report.summary }}</p>
      </div>

      <div class="conclusion-callout">
        <span>体检结论</span>
        <strong>{{ report.conclusion }}</strong>
      </div>

      <nav class="tabs" aria-label="报告视图">
        <button :class="{ selected: selectedTab === 'report' }" type="button" @click="$emit('update:selectedTab', 'report')">解释</button>
        <button :class="{ selected: selectedTab === 'metrics' }" type="button" @click="$emit('update:selectedTab', 'metrics')">指标</button>
        <button :class="{ selected: selectedTab === 'notes' }" type="button" @click="$emit('update:selectedTab', 'notes')">提示</button>
      </nav>

      <div v-if="selectedTab === 'report'" class="notion-list">
        <h3>主要风险</h3>
        <p v-for="item in report.risk_notes" :key="item">{{ item }}</p>
        <h3>适合人群</h3>
        <p v-for="item in report.suitable_for" :key="item">{{ item }}</p>
        <h3>不适合人群</h3>
        <p v-for="item in report.unsuitable_for" :key="item">{{ item }}</p>
        <h3>持仓与行业</h3>
        <p v-for="item in report.holding_notes ?? []" :key="item">{{ item }}</p>
      </div>

      <div v-if="selectedTab === 'metrics'" class="database-table">
        <div><span>观察天数</span><strong>{{ report.metrics.observation_days }}</strong></div>
        <div><span>年化收益</span><strong>{{ formatPercent(report.metrics.annualized_return) }}</strong></div>
        <div><span>卡玛比率</span><strong>{{ formatNumber(report.metrics.calmar_ratio) }}</strong></div>
        <div><span>胜率</span><strong>{{ formatPercent(report.metrics.win_rate) }}</strong></div>
        <div><span>夏普比率</span><strong>{{ formatNumber(report.metrics.sharpe_ratio) }}</strong></div>
        <div><span>最大回撤</span><strong>{{ formatPercent(report.metrics.max_drawdown) }}</strong></div>
      </div>

      <div v-if="selectedTab === 'notes'" class="notion-list">
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
  </section>
</template>
