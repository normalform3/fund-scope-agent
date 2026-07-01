<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { BarChart3, Compass, Loader2, SearchCheck } from "@lucide/vue";
import {
  compareFunds,
  type FundCandidate,
  type FundComparisonResponse,
  type FundDiscoveryRequest,
  type FundDiscoveryResponse,
  type UserRiskProfile
} from "../api";

const props = defineProps<{
  discovery: FundDiscoveryResponse | null;
  loading: boolean;
}>();

const emit = defineEmits<{
  discover: [request: FundDiscoveryRequest];
  analyzeCandidate: [code: string, riskProfile: UserRiskProfile];
}>();

const goalText = ref("我是新手，希望先稳健观察一只基金，未来一年可能会用到这笔钱。");
const selectedFundType = ref("");
const refinementText = ref("希望波动小一点，费用不要太高，先作为观察对象。");
const comparison = ref<FundComparisonResponse | null>(null);
const comparisonLoading = ref(false);
const comparisonError = ref("");
const answers = ref({
  risk_tolerance: "low",
  horizon: "medium",
  liquidity_need: "medium",
  experience_level: "beginner",
  max_loss_tolerance: "0.1",
  investment_horizon_months: "12",
  can_delay_use: "false",
  money_purpose: "near_term"
});

function submitDiscovery() {
  emit("discover", {
    goal_text: goalText.value,
    answers: { ...answers.value },
    include_candidates: false
  });
}

function submitRefinement() {
  emit("discover", {
    goal_text: goalText.value,
    answers: { ...answers.value },
    include_candidates: true,
    selected_fund_type: selectedFundType.value,
    refinement_text: refinementText.value
  });
}

const typeOptions = computed(() => props.discovery?.fund_type_matches ?? []);
const candidateCodes = computed(() => (props.discovery?.candidates ?? []).map((candidate) => candidate.code));
const canCompareCandidates = computed(() => candidateCodes.value.length >= 2 && !comparisonLoading.value);

watch(
  typeOptions,
  (matches) => {
    if (matches.length && !matches.some((match) => match.fund_type === selectedFundType.value)) {
      selectedFundType.value = matches[0].fund_type;
    }
  },
  { immediate: true }
);

watch(candidateCodes, () => {
  comparison.value = null;
  comparisonError.value = "";
});

function formatRisk(value: string) {
  return { low: "保守", medium: "平衡", high: "进取" }[value] ?? value;
}

function formatHorizon(value: string) {
  return { short: "短期", medium: "中期", long: "长期" }[value] ?? value;
}

function formatPercent(value: number | null) {
  if (typeof value !== "number") return "--";
  return `${(value * 100).toFixed(2)}%`;
}

function formatMonths(value: number | null) {
  if (typeof value !== "number") return "--";
  return `${value} 个月`;
}

function formatDelay(value: boolean | null) {
  if (typeof value !== "boolean") return "--";
  return value ? "可延期" : "不方便延期";
}

function formatPurpose(value: string | null | undefined) {
  return {
    emergency: "应急备用金",
    education: "教育支出",
    retirement: "养老长期",
    idle: "闲置观察",
    near_term: "近期目标"
  }[value ?? ""] ?? "--";
}

function formatScore(value: number) {
  if (typeof value !== "number") return "--";
  return value.toFixed(0);
}

function formatMetric(value: number | null) {
  if (typeof value !== "number") return "--";
  return (value * 100).toFixed(2) + "%";
}

function formatRatio(value: number | null) {
  if (typeof value !== "number") return "--";
  return value.toFixed(2);
}

function rankingLabel(metric: string) {
  return {
    annualized_volatility: "波动控制排序",
    max_drawdown: "回撤控制排序",
    sharpe_ratio: "夏普排序"
  }[metric] ?? metric;
}

function rankingSummary(metric: string) {
  const ranking = comparison.value?.rankings[metric];
  if (!ranking || ranking.items.length === 0) return "数据不足";
  return ranking.items
    .slice(0, 3)
    .map((item) => {
      const value = metric === "sharpe_ratio" ? formatRatio(item.value) : formatMetric(item.value);
      return `第${item.rank} ${item.code}（${value}）`;
    })
    .join(" / ");
}

function toNumber(value: unknown) {
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function toBoolean(value: unknown) {
  if (value === true || value === "true") return true;
  if (value === false || value === "false") return false;
  return null;
}

async function compareCandidateFunds() {
  if (!canCompareCandidates.value) return;
  comparisonLoading.value = true;
  comparisonError.value = "";
  comparison.value = null;
  try {
    comparison.value = await compareFunds(candidateCodes.value);
  } catch (error) {
    comparisonError.value = error instanceof Error ? error.message : "候选基金比较失败";
  } finally {
    comparisonLoading.value = false;
  }
}

function analyze(candidate: FundCandidate) {
  const profile = props.discovery?.profile;
  emit("analyzeCandidate", candidate.code, {
    risk_tolerance: profile?.risk_tolerance ?? answers.value.risk_tolerance,
    horizon: profile?.horizon ?? answers.value.horizon,
    liquidity_need: profile?.liquidity_need ?? answers.value.liquidity_need,
    max_loss_tolerance: profile?.max_loss_tolerance ?? toNumber(answers.value.max_loss_tolerance),
    investment_horizon_months:
      profile?.investment_horizon_months ?? toNumber(answers.value.investment_horizon_months),
    can_delay_use: profile?.can_delay_use ?? toBoolean(answers.value.can_delay_use),
    money_purpose: profile?.money_purpose ?? answers.value.money_purpose
  });
}
</script>

<template>
  <section class="page-block discovery-panel">
    <div class="discovery-header">
      <div class="block-heading">
        <span>Discovery</span>
        <strong><Compass :size="18" /> 帮我找候选基金</strong>
      </div>
      <button class="discovery-submit" type="button" :disabled="loading" @click="submitDiscovery">
        <Loader2 v-if="loading" class="spin" :size="16" />
        <SearchCheck v-else :size="16" />
        <span>{{ loading ? '分析中' : '推荐大类' }}</span>
      </button>
    </div>

    <textarea
      v-model="goalText"
      class="discovery-goal"
      rows="3"
      aria-label="投资目标描述"
      placeholder="描述你的目标、期限、能承受的波动和用钱计划"
    />

    <div class="question-grid">
      <label>
        <span>风险承受</span>
        <select v-model="answers.risk_tolerance">
          <option value="low">保守</option>
          <option value="medium">平衡</option>
          <option value="high">进取</option>
        </select>
      </label>
      <label>
        <span>资金期限</span>
        <select v-model="answers.horizon">
          <option value="short">短期</option>
          <option value="medium">中期</option>
          <option value="long">长期</option>
        </select>
      </label>
      <label>
        <span>流动性</span>
        <select v-model="answers.liquidity_need">
          <option value="high">随时可能用</option>
          <option value="medium">不确定</option>
          <option value="low">长期不用</option>
        </select>
      </label>
      <label>
        <span>经验水平</span>
        <select v-model="answers.experience_level">
          <option value="beginner">新手</option>
          <option value="some">有一点经验</option>
          <option value="experienced">比较熟悉</option>
        </select>
      </label>
      <label>
        <span>最大可承受亏损</span>
        <select v-model="answers.max_loss_tolerance">
          <option value="0.05">5% 以内</option>
          <option value="0.1">10% 左右</option>
          <option value="0.2">20% 左右</option>
          <option value="0.35">35% 左右</option>
        </select>
      </label>
      <label>
        <span>预计持有</span>
        <select v-model="answers.investment_horizon_months">
          <option value="3">3 个月</option>
          <option value="6">6 个月</option>
          <option value="12">12 个月</option>
          <option value="36">36 个月</option>
        </select>
      </label>
      <label>
        <span>到期用钱</span>
        <select v-model="answers.can_delay_use">
          <option value="false">不方便延期</option>
          <option value="true">可以延期</option>
        </select>
      </label>
      <label>
        <span>资金用途</span>
        <select v-model="answers.money_purpose">
          <option value="emergency">应急备用金</option>
          <option value="near_term">近期目标</option>
          <option value="education">教育支出</option>
          <option value="retirement">养老长期</option>
          <option value="idle">闲置观察</option>
        </select>
      </label>
    </div>

    <div v-if="discovery" class="discovery-result">
      <div class="discovery-summary">
        <strong>{{ discovery.summary }}</strong>
        <span>
          {{ formatRisk(discovery.profile.risk_tolerance) }} ·
          {{ formatHorizon(discovery.profile.horizon) }} ·
          可承受亏损 {{ formatPercent(discovery.profile.max_loss_tolerance) }} ·
          预计持有 {{ formatMonths(discovery.profile.investment_horizon_months) }} ·
          到期 {{ formatDelay(discovery.profile.can_delay_use) }} ·
          用途 {{ formatPurpose(discovery.profile.money_purpose) }} ·
          {{ discovery.profile.notes[0] || '候选仅用于进一步研究。' }}
        </span>
        <p>{{ discovery.llm_explanation }}</p>
        <div v-if="discovery.decision_basis.length" class="decision-basis">
          <span v-for="item in discovery.decision_basis" :key="item">{{ item }}</span>
        </div>
      </div>

      <div class="type-match-list">
        <button
          v-for="match in discovery.fund_type_matches"
          :key="match.fund_type"
          :class="['type-match-item', selectedFundType === match.fund_type ? 'selected' : '']"
          type="button"
          @click="selectedFundType = match.fund_type"
        >
          <div class="type-match-title">
            <strong>{{ match.fund_type }}</strong>
            <span>{{ formatScore(match.fit_score) }}</span>
          </div>
          <span>{{ match.reason }}</span>
          <div v-if="match.basis.length" class="basis-list">
            <span v-for="item in match.basis.slice(0, 3)" :key="item">{{ item }}</span>
          </div>
          <div v-if="match.risk_flags.length" class="risk-list">
            <span v-for="item in match.risk_flags.slice(0, 2)" :key="item">{{ item }}</span>
          </div>
          <div v-if="match.missing_context.length" class="context-list">
            <span v-for="item in match.missing_context.slice(0, 2)" :key="item">{{ item }}</span>
          </div>
        </button>
      </div>

      <div v-if="discovery.clarifying_questions.length" class="question-followups">
        <span v-for="question in discovery.clarifying_questions" :key="question">{{ question }}</span>
      </div>

      <div class="refinement-panel">
        <label>
          <span>进一步要求</span>
          <textarea
            v-model="refinementText"
            rows="2"
            placeholder="例如：更稳一点、偏指数、费用低、不要行业主题"
          />
        </label>
        <button class="discovery-submit" type="button" :disabled="loading || !selectedFundType" @click="submitRefinement">
          <Loader2 v-if="loading" class="spin" :size="16" />
          <SearchCheck v-else :size="16" />
          <span>{{ loading ? '细化中' : '细化候选' }}</span>
        </button>
      </div>

      <div v-if="discovery.candidates.length" class="candidate-list">
        <article v-for="candidate in discovery.candidates" :key="candidate.code" class="candidate-item">
          <div>
            <span>{{ candidate.code }} · {{ candidate.fund_type }}</span>
            <strong>{{ candidate.name }}</strong>
            <p>{{ candidate.reason }}</p>
            <small>
              最大回撤 {{ formatPercent(candidate.max_drawdown) }} ·
              年化波动 {{ formatPercent(candidate.annualized_volatility) }}
            </small>
            <div v-if="candidate.basis.length" class="candidate-basis">
              <span v-for="item in candidate.basis.slice(0, 3)" :key="item">{{ item }}</span>
            </div>
          </div>
          <button type="button" @click="analyze(candidate)">生成体检报告</button>
        </article>
      </div>

      <section v-if="discovery.candidates.length >= 2" class="candidate-comparison">
        <div class="comparison-header">
          <div>
            <strong>候选横向比较</strong>
            <span>基于历史净值确定性计算，不保存为长期观察池。</span>
          </div>
          <button class="discovery-submit" type="button" :disabled="!canCompareCandidates" @click="compareCandidateFunds">
            <Loader2 v-if="comparisonLoading" class="spin" :size="16" />
            <BarChart3 v-else :size="16" />
            <span>{{ comparisonLoading ? '比较中' : '比较候选' }}</span>
          </button>
        </div>

        <div v-if="comparisonError" class="panel-empty">{{ comparisonError }}</div>

        <div v-if="comparison" class="comparison-table">
          <div class="comparison-row comparison-row-head">
            <span>基金</span>
            <span>年化收益</span>
            <span>年化波动</span>
            <span>最大回撤</span>
            <span>夏普</span>
          </div>
          <div v-for="item in comparison.items" :key="item.code" class="comparison-row">
            <strong>{{ item.code }} · {{ item.name }}</strong>
            <span>{{ formatMetric(item.annualized_return) }}</span>
            <span>{{ formatMetric(item.annualized_volatility) }}</span>
            <span>{{ formatMetric(item.max_drawdown) }}</span>
            <span>{{ formatRatio(item.sharpe_ratio) }}</span>
          </div>
        </div>

        <div v-if="comparison" class="comparison-rankings">
          <span v-for="metric in ['annualized_volatility', 'max_drawdown', 'sharpe_ratio']" :key="metric">
            {{ rankingLabel(metric) }}：{{ rankingSummary(metric) }}
          </span>
        </div>

        <div v-if="comparison?.data_notes.length" class="discovery-notes">
          <span v-for="note in comparison.data_notes.slice(0, 3)" :key="note">{{ note }}</span>
        </div>
        <div v-if="comparison?.compliance_warnings.length" class="discovery-notes">
          <span v-for="warning in comparison.compliance_warnings" :key="warning">{{ warning }}</span>
        </div>
      </section>

      <div v-else-if="discovery.stage === 'candidate_refinement'" class="panel-empty">当前条件下没有筛出可靠候选，可以放宽期限或风险偏好后重试。</div>

      <div v-if="discovery.data_notes.length" class="discovery-notes">
        <span v-for="note in discovery.data_notes.slice(0, 3)" :key="note">{{ note }}</span>
      </div>
    </div>
  </section>
</template>
