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

export interface FundCheckupReport {
  fund: FundProfile;
  conclusion: string;
  summary: string;
  metrics: RiskMetrics;
  holdings: FundHolding[];
  industry_allocation: IndustryAllocation[];
  fees: FundFee[];
  risk_notes: string[];
  holding_notes: string[];
  suitable_for: string[];
  unsuitable_for: string[];
  data_notes: string[];
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

export async function searchFunds(query: string): Promise<FundProfile[]> {
  const response = await fetch(`/api/funds/search?q=${encodeURIComponent(query)}`);
  if (!response.ok) {
    throw new Error("基金搜索失败");
  }
  const payload = await response.json();
  return payload.items;
}

export async function createFundCheckup(code: string): Promise<FundCheckupReport> {
  const response = await fetch("/api/reports/fund-checkup", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code })
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
