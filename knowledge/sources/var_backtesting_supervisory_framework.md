# Supervisory Framework for Market Risk VaR Backtesting

> **Provenance Notice:** Team-authored educational summary based on Bank for International Settlements (BCBS 22) supervisory backtesting concepts; not an official regulatory text.

## Value-at-Risk (VaR) Validation and Exception Counting
The supervisory framework for backtesting internal market risk models specifies key statistical validation principles:
1. One-Day Horizon: Backtesting compares one-day VaR forecasts (at 99% or 95% confidence) against realized daily portfolio profit/loss over a trailing observation window.
2. Exception Definition: An exception occurs when the realized trading loss on day t exceeds the forecast VaR loss threshold computed for day t.
3. Strict Temporal Separation: The model estimation window must strictly use historical data up to day t-1 prior to observing the market outcome on day t, avoiding look-ahead bias.
4. Kupiec Proportion of Failures (POF) Test: Statistical likelihood ratio test evaluating whether the observed exception frequency is consistent with the theoretical confidence level.
