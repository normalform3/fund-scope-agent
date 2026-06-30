# Compliance

FundScope Agent is a research reference tool. It must not act as a fund sales or trading advisory system.

## Prohibited Phrases

- 必买
- 稳赚
- 保证收益
- 强烈推荐买入
- 未来一定上涨
- 一定会涨
- 无风险
- 保本保收益
- 建议买入
- 建议卖出

## Allowed Conclusions

- 适合关注
- 适合长期观察
- 仅适合高风险用户
- 不适合当前用户
- 数据不足，暂不评价

## Required Disclaimer

```text
仅供研究参考，不构成投资建议。基金有风险，投资需谨慎。
```

## Output Rules

- If data is insufficient, use `数据不足，暂不评价`.
- If a fund has high volatility or deep drawdown, say which risk signal triggered the warning.
- Do not rank a fund as best unless the ranking is backed by explicit same-category data.
- Do not imply future certainty from past performance.
- Do not direct users to buy, sell, redeem, subscribe, or hold.
- Discovery output must use candidate language such as `候选观察` or `可进一步研究`.
- Discovery output must not say a candidate is the best or most suitable fund for the user.
- A discovery candidate must link to further checkup analysis instead of acting as a final investment decision.

## Implementation

Compliance logic lives in `backend/app/compliance/checker.py`.

Any future LLM report generation must run through `enforce_report_compliance` before returning to the user.

Fund discovery also sanitizes generated profile, type-match, and candidate wording before returning from `POST /api/fund-discovery`.
