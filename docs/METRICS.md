# Metrics

All metrics are calculated in Python. LLM output must not replace these calculations.

## Total Return

```text
ending accumulated NAV / starting accumulated NAV - 1
```

## Annualized Return

```text
(1 + total_return) ^ (1 / years) - 1
years = (observations - 1) / 252
```

## Daily Return

```text
current accumulated NAV / previous accumulated NAV - 1
```

## Annualized Volatility

```text
standard_deviation(daily_returns) * sqrt(252)
```

## Maximum Drawdown

```text
current accumulated NAV / historical peak accumulated NAV - 1
```

The report also stores drawdown start, trough, and recovery days when the NAV later recovers to the previous peak.

## Sharpe Ratio

```text
(annualized_return - risk_free_rate) / annualized_volatility
```

V1 default risk-free rate: `2%`.

## Calmar Ratio

```text
annualized_return / abs(max_drawdown)
```

## Win Rate

```text
positive daily return days / total daily return days
```

## Edge Cases

- Fewer than 2 valid NAV points: all major metrics return `None`.
- Non-positive accumulated NAV values are ignored.
- Fewer than 252 observations: annualized metrics are returned with a warning.
- Zero volatility: Sharpe ratio returns `None`.

