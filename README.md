# FundScope Agent

FundScope Agent 是一个面向普通投资者的基金研究与风险匹配助手。V1 聚焦单只基金体检：用户输入基金代码或名称，系统生成结构化报告，解释历史收益、最大回撤、波动率、夏普比率、适合人群和主要风险。

本项目不做买入/卖出指令，不承诺收益，不预测基金未来一定上涨。所有输出仅供研究参考，不构成投资建议。

## Features

- 基金搜索、档案、历史净值数据入口。
- Python 确定性计算累计收益、年化收益、年化波动率、最大回撤、夏普比率、卡玛比率、胜率。
- 结构化基金体检报告 JSON。
- 合规检查：拦截“必买、稳赚、保证收益、强烈推荐买入、未来一定上涨”等表述。
- Vue 3 工作台：基金输入、指标卡片、净值曲线、累计收益曲线、回撤曲线、右侧报告面板。
- SQLite 缓存，减少重复请求外部数据源。
- 离线示例数据，便于简历展示和本地演示。

## Tech Stack

- Backend: FastAPI, Python, SQLite
- Metrics: Python standard library, optional Pandas / NumPy for later expansion
- Data: AKShare adapter, sample fallback provider, Tushare reserved
- Agent workflow: LangGraph-compatible workflow wrapper
- Frontend: Vue 3, Vite, ECharts, lucide-vue-next

## Quick Start

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pytest
uvicorn app.main:app --app-dir backend --reload
```

The default data provider is offline sample data so local demos do not depend on live data availability. To try AKShare:

```bash
FUNDSCOPE_DATA_PROVIDER=akshare uvicorn app.main:app --app-dir backend --reload
```

In another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173`.

## API

- `GET /api/health`
- `GET /api/funds/search?q=110011`
- `GET /api/funds/{code}/profile`
- `GET /api/funds/{code}/nav`
- `POST /api/reports/fund-checkup`

Example:

```bash
curl -X POST http://127.0.0.1:8000/api/reports/fund-checkup \
  -H "Content-Type: application/json" \
  -d '{"code":"110011"}'
```

## Data Source Notice

Development uses AKShare-compatible adapters and sample fallback data. The default provider is `sample`; set `FUNDSCOPE_DATA_PROVIDER=akshare` to try live AKShare data. AKShare data is suitable for academic research and learning projects, not commercial use. If this project is commercialized, replace the data source with licensed fund data and update `docs/DATA_SOURCES.md`.

## Disclaimer

FundScope Agent is a research and education tool. It does not provide investment advisory, fund sales, trading execution, or guaranteed return claims. Fund investment involves risk; users should make independent decisions and consult qualified professionals when needed.
# fund-scope-agent
