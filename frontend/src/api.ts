export interface FundProfile {
  code: string;
  name: string;
  fund_type: string;
  inception_date: string;
  manager: string;
  company: string;
  scale: string;
  purchase_status: string;
  redeem_status: string;
  fee_note: string;
  benchmark: string;
  investment_objective: string;
  investment_strategy: string;
  custodian: string;
  rating: string;
  data_source: string;
}

export interface NavPoint {
  date: string;
  unit_nav: number;
  accumulated_nav: number;
}

export interface DrawdownPoint {
  date: string;
  drawdown: number;
}

export interface RiskMetrics {
  observation_days: number;
  total_return: number | null;
  annualized_return: number | null;
  annualized_volatility: number | null;
  max_drawdown: number | null;
  sharpe_ratio: number | null;
  calmar_ratio: number | null;
  win_rate: number | null;
  max_drawdown_start: string | null;
  max_drawdown_trough: string | null;
  drawdown_recovery_days: number | null;
  period_returns: Record<string, number | null>;
  drawdown_series: DrawdownPoint[];
  warnings: string[];
}

export interface FundHolding {
  stock_code: string;
  stock_name: string;
  ratio: number | null;
  shares: number | null;
  market_value: number | null;
  period: string;
}

export interface IndustryAllocation {
  industry: string;
  ratio: number | null;
  market_value: number | null;
  report_date: string;
}

export interface FundFee {
  category: string;
  condition: string;
  value: string;
}

export interface RiskExplanationItem {
  key: string;
  title: string;
  level: string;
  metric_label: string;
  metric_value: number | null;
  explanation: string;
  user_meaning: string;
}

export interface UserRiskProfile {
  risk_tolerance: string;
  horizon: string;
  liquidity_need: string;
  max_loss_tolerance?: number | null;
  investment_horizon_months?: number | null;
  can_delay_use?: boolean | null;
  money_purpose?: string | null;
}

export interface RiskProfileAssessment {
  status: string;
  fit_level: string;
  profile: Record<string, unknown>;
  reasons: string[];
  risk_flags: string[];
}

export interface WorkflowTraceItem {
  stage: string;
  label: string;
  status: string;
  message: string;
  item_count?: number;
}

export interface DataQualityItem {
  section: string;
  label: string;
  status: string;
  item_count: number;
  source: string;
  note: string;
}

export interface FundCheckupReport {
  fund: FundProfile;
  conclusion: string;
  summary: string;
  metrics: RiskMetrics;
  holdings: FundHolding[];
  industry_allocation: IndustryAllocation[];
  fees: FundFee[];
  risk_explanation: RiskExplanationItem[];
  risk_profile_assessment: RiskProfileAssessment;
  risk_notes: string[];
  holding_notes: string[];
  suitable_for: string[];
  unsuitable_for: string[];
  data_notes: string[];
  data_quality: DataQualityItem[];
  workflow_trace: WorkflowTraceItem[];
  llm_commentary: string;
  compliance_warnings: string[];
  errors?: string[];
}

export interface LlmHealth {
  ok: boolean;
  model: string;
  message: string;
  request_id?: string;
  usage?: Record<string, unknown>;
}

export interface InvestorPreferenceProfile {
  investment_goal: string;
  horizon: string;
  risk_tolerance: string;
  liquidity_need: string;
  experience_level: string;
  preferred_fund_types: string[];
  notes: string[];
  max_loss_tolerance: number | null;
  investment_horizon_months: number | null;
  can_delay_use: boolean | null;
  money_purpose: string;
}

export interface FundTypeMatch {
  fund_type: string;
  reason: string;
  unsuitable_for: string;
  search_keywords: string[];
  fit_score: number;
  basis: string[];
  risk_flags: string[];
  missing_context: string[];
}

export interface FundCandidate {
  code: string;
  name: string;
  fund_type: string;
  reason: string;
  risk_notes: string[];
  data_source: string;
  next_action: string;
  observation_days: number;
  annualized_volatility: number | null;
  max_drawdown: number | null;
  basis: string[];
}

export interface FundComparisonItem {
  code: string;
  name: string;
  fund_type: string;
  data_source: string;
  is_target: boolean;
  observation_days: number;
  total_return: number | null;
  annualized_return: number | null;
  annualized_volatility: number | null;
  max_drawdown: number | null;
  sharpe_ratio: number | null;
  warnings: string[];
}

export interface FundComparisonRankingItem {
  rank: number;
  code: string;
  name: string;
  value: number | null;
}

export interface FundComparisonRanking {
  direction: string;
  count: number;
  items: FundComparisonRankingItem[];
}

export interface FundComparisonResponse {
  watchlist: {
    codes: string[];
    persistence: string;
    note: string;
  };
  items: FundComparisonItem[];
  rankings: Record<string, FundComparisonRanking>;
  data_notes: string[];
  compliance_warnings: string[];
}

export interface PeerComparisonRank {
  rank: number | null;
  count: number;
  percentile: number | null;
  direction: string;
  note: string;
}

export interface PeerComparisonResponse {
  target: FundProfile;
  category: {
    fund_type: string;
    bucket: string;
    matching_rule: string;
  };
  items: FundComparisonItem[];
  ranks: Record<string, PeerComparisonRank>;
  data_notes: string[];
  compliance_warnings: string[];
}

export interface FundDiscoveryResponse {
  stage: string;
  profile: InvestorPreferenceProfile;
  fund_type_matches: FundTypeMatch[];
  candidates: FundCandidate[];
  clarifying_questions: string[];
  summary: string;
  llm_explanation: string;
  llm_used: boolean;
  decision_basis: string[];
  data_notes: string[];
  compliance_warnings: string[];
}

export interface FundDiscoveryRequest {
  goal_text: string;
  answers: Record<string, string>;
  include_candidates?: boolean;
  selected_fund_type?: string;
  refinement_text?: string;
}

export async function searchFunds(query: string): Promise<FundProfile[]> {
  const response = await fetch(`/api/funds/search?q=${encodeURIComponent(query)}`);
  if (!response.ok) {
    throw new Error("基金搜索失败");
  }
  const payload = await response.json();
  return payload.items;
}

export async function createFundCheckup(code: string, riskProfile?: UserRiskProfile): Promise<FundCheckupReport> {
  const response = await fetch("/api/reports/fund-checkup", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code, ...(riskProfile ? { risk_profile: riskProfile } : {}) })
  });
  if (!response.ok) {
    throw new Error("体检报告生成失败");
  }
  const payload = await response.json();
  if (!payload.fund || !payload.metrics) {
    throw new Error(payload.summary || "体检报告结构不完整");
  }
  return payload;
}

export async function discoverFunds(request: FundDiscoveryRequest): Promise<FundDiscoveryResponse> {
  const response = await fetch("/api/fund-discovery", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request)
  });
  if (!response.ok) {
    throw new Error("候选基金筛选失败");
  }
  const payload = await response.json();
  if (!payload.profile || !Array.isArray(payload.fund_type_matches) || !Array.isArray(payload.candidates)) {
    throw new Error("候选基金响应结构不完整");
  }
  return payload;
}

export async function fetchPeerComparison(code: string): Promise<PeerComparisonResponse> {
  const response = await fetch(`/api/funds/${encodeURIComponent(code)}/peer-comparison`);
  if (!response.ok) {
    throw new Error("同类比较获取失败");
  }
  const payload = await response.json();
  if (!payload.target || !payload.category || !Array.isArray(payload.items) || !payload.ranks) {
    throw new Error("同类比较响应结构不完整");
  }
  return payload;
}

export async function compareFunds(codes: string[]): Promise<FundComparisonResponse> {
  const response = await fetch("/api/funds/compare", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ codes })
  });
  if (!response.ok) {
    throw new Error("候选基金比较失败");
  }
  const payload = await response.json();
  if (!payload.watchlist || !Array.isArray(payload.items) || !payload.rankings) {
    throw new Error("候选基金比较响应结构不完整");
  }
  return payload;
}

export async function fetchNav(code: string): Promise<NavPoint[]> {
  const response = await fetch(`/api/funds/${encodeURIComponent(code)}/nav`);
  if (!response.ok) {
    throw new Error("净值数据获取失败");
  }
  const payload = await response.json();
  return payload.items;
}

export async function testLlmConnection(): Promise<LlmHealth> {
  const response = await fetch("/api/llm/health");
  if (!response.ok) {
    throw new Error("模型服务连接测试失败");
  }
  return response.json();
}
