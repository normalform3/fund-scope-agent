<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { Compass, Loader2, SearchCheck } from "@lucide/vue";
import type { FundCandidate, FundDiscoveryRequest, FundDiscoveryResponse } from "../api";

const props = defineProps<{
  discovery: FundDiscoveryResponse | null;
  loading: boolean;
}>();

const emit = defineEmits<{
  discover: [request: FundDiscoveryRequest];
  analyzeCandidate: [code: string];
}>();

const goalText = ref("我是新手，希望先稳健观察一只基金，未来一年可能会用到这笔钱。");
const selectedFundType = ref("");
const refinementText = ref("希望波动小一点，费用不要太高，先作为观察对象。");
const answers = ref({
  risk_tolerance: "low",
  horizon: "medium",
  liquidity_need: "medium",
  experience_level: "beginner"
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

watch(
  typeOptions,
  (matches) => {
    if (matches.length && !matches.some((match) => match.fund_type === selectedFundType.value)) {
      selectedFundType.value = matches[0].fund_type;
    }
  },
  { immediate: true }
);

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

function analyze(candidate: FundCandidate) {
  emit("analyzeCandidate", candidate.code);
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
    </div>

    <div v-if="discovery" class="discovery-result">
      <div class="discovery-summary">
        <strong>{{ discovery.summary }}</strong>
        <span>
          {{ formatRisk(discovery.profile.risk_tolerance) }} ·
          {{ formatHorizon(discovery.profile.horizon) }} ·
          {{ discovery.profile.notes[0] || '候选仅用于进一步研究。' }}
        </span>
      </div>

      <div class="type-match-list">
        <button
          v-for="match in discovery.fund_type_matches"
          :key="match.fund_type"
          :class="['type-match-item', selectedFundType === match.fund_type ? 'selected' : '']"
          type="button"
          @click="selectedFundType = match.fund_type"
        >
          <strong>{{ match.fund_type }}</strong>
          <span>{{ match.reason }}</span>
        </button>
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
          </div>
          <button type="button" @click="analyze(candidate)">生成体检报告</button>
        </article>
      </div>

      <div v-else-if="discovery.stage === 'candidate_refinement'" class="panel-empty">当前条件下没有筛出可靠候选，可以放宽期限或风险偏好后重试。</div>

      <div v-if="discovery.data_notes.length" class="discovery-notes">
        <span v-for="note in discovery.data_notes.slice(0, 3)" :key="note">{{ note }}</span>
      </div>
    </div>
  </section>
</template>
