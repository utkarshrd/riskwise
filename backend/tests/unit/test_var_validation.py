from pathlib import Path

import pandas as pd
import pytest
from backend.app.services.market_risk.engine import Holding, MarketRiskEngine
from backend.app.services.var_validation.engine import VaRValidationEngine


def test_rolling_var_validation_execution():
    val_engine = VaRValidationEngine()
    holdings = [
        Holding(symbol="SPY", weight=0.7),
        Holding(symbol="MSFT", weight=0.3)
    ]
    res = val_engine.run_rolling_backtest(
        holdings=holdings,
        confidence_level=0.95,
        lookback_window=100
    )

    assert res.forecast_count > 300
    assert res.exception_count >= 0
    assert 0.0 <= res.exception_rate <= 1.0
    assert res.expected_exception_rate == 0.05
    assert res.n_obs > 400
    assert res.window == 100
    assert res.confidence == 0.95
    assert res.exceptions == res.exception_count
    assert abs(res.expected_exceptions - round(res.forecast_count * 0.05, 2)) < 0.1

    # Basel Traffic-Light Zone
    assert res.basel_zone in ["GREEN", "YELLOW", "RED"]
    assert 0.0 <= res.basel_zone_cumulative_prob <= 1.0

    # Kupiec POF Test
    assert res.kupiec_lr_stat is not None
    assert res.kupiec_p_value is not None
    assert isinstance(res.kupiec_test_passed, bool)

    # Christoffersen Independence Test
    if res.exception_count > 0:
        assert res.christoffersen_lr_stat is not None
        assert res.christoffersen_p_value is not None

    assert len(res.validation_points) == res.forecast_count
    p0 = res.validation_points[0]
    assert p0.date is not None
    assert isinstance(p0.is_exception, bool)


def test_rolling_var_insufficient_history():
    val_engine = VaRValidationEngine()
    holdings = [Holding(symbol="SPY", weight=1.0)]
    with pytest.raises(ValueError, match="Insufficient historical data"):
        val_engine.run_rolling_backtest(
            holdings=holdings,
            lookback_window=1000
        )


def test_var_no_lookahead_guarantee(tmp_path: Path):
    """
    Explicit no-lookahead test:
    Proves that the VaR forecast at step t uses strictly preceding data [t-lookback:t],
    and produces bit-for-bit identical forecasts whether future data exists or not.
    """
    dates_full = pd.date_range("2024-01-01", periods=150, freq="D")
    # Deterministic price series: smooth growth then sharp drop in future
    prices_full = [100.0 * (1.001 ** i) for i in range(120)] + [50.0] * 30

    df_full = pd.DataFrame({
        "date": dates_full.strftime("%Y-%m-%d"),
        "close": prices_full,
        "adj_close": prices_full,
        "volume": [1000] * 150
    })

    dir_full = tmp_path / "full"
    dir_full.mkdir()
    df_full.to_csv(dir_full / "TEST_ASSET.csv", index=False)

    # Truncated series: only the first 120 days (before the sharp drop)
    df_trunc = df_full.iloc[:120].copy()
    dir_trunc = tmp_path / "trunc"
    dir_trunc.mkdir()
    df_trunc.to_csv(dir_trunc / "TEST_ASSET.csv", index=False)

    risk_full = MarketRiskEngine(snapshots_dir=dir_full)
    risk_trunc = MarketRiskEngine(snapshots_dir=dir_trunc)

    val_full = VaRValidationEngine(risk_engine=risk_full)
    val_trunc = VaRValidationEngine(risk_engine=risk_trunc)

    holdings = [Holding(symbol="TEST_ASSET", weight=1.0)]

    res_full = val_full.run_rolling_backtest(holdings=holdings, lookback_window=60)
    res_trunc = val_trunc.run_rolling_backtest(holdings=holdings, lookback_window=60)

    # The truncated run has fewer forecast points
    assert len(res_trunc.validation_points) < len(res_full.validation_points)

    # For every date present in the truncated run, forecast VaR must be EXACTLY IDENTICAL
    # to the forecast in the full run (zero lookahead leakage from future days 121-150)
    for i, pt_trunc in enumerate(res_trunc.validation_points):
        pt_full = res_full.validation_points[i]
        assert pt_trunc.date == pt_full.date
        assert pt_trunc.forecast_var == pt_full.forecast_var, (
            f"Lookahead detected at {pt_trunc.date}: truncated={pt_trunc.forecast_var}, full={pt_full.forecast_var}"
        )
        assert pt_trunc.realized_loss == pt_full.realized_loss
        assert pt_trunc.is_exception == pt_full.is_exception


def test_basel_zone_boundaries_hand_calculated():
    """
    Validates Basel Committee on Banking Supervision (BCBS) traffic-light zones at N=250.
    Standard: 99% 1-day VaR evaluated across N=250 trading days (expected violation rate p = 1 - 0.99 = 0.01).
    
    Cumulative Binomial Probability formula:
      P(X <= k) = sum_{j=0}^{k} C(250, j) * (0.01)^j * (0.99)^(250 - j)
      
    Zone Definition Thresholds:
      - Green Zone:  P(X <= k) < 0.9500
      - Yellow Zone: 0.9500 <= P(X <= k) < 0.9999
      - Red Zone:    P(X <= k) >= 0.9999
      
    Hand-calculated cumulative binomial probabilities at N=250, p=0.01:
      k = 0: (0.99)^250 = 0.081059                     -> GREEN  (< 0.95)
      k = 1: 0.081059 + 250*(0.01)*(0.99)^249 = 0.285752 -> GREEN  (< 0.95)
      k = 2: 0.285752 + 31125*(0.01)^2*(0.99)^248 = 0.543169 -> GREEN (< 0.95)
      k = 3: 0.543169 + ... = 0.758117                 -> GREEN  (< 0.95)
      k = 4: ... = 0.892188                             -> GREEN  (< 0.95) [Upper boundary of Green zone: 0-4]
      k = 5: ... = 0.958817                             -> YELLOW (>= 0.95) [Lower boundary of Yellow zone: 5]
      k = 6: ... = 0.986299                             -> YELLOW (< 0.9999)
      k = 7: ... = 0.995975                             -> YELLOW (< 0.9999)
      k = 8: ... = 0.998943                             -> YELLOW (< 0.9999)
      k = 9: ... = 0.999750                             -> YELLOW (< 0.9999) [Upper boundary of Yellow zone: 5-9]
      k = 10: ... = 0.999946                            -> RED    (>= 0.9999) [Boundary of Red zone: 10+]
    """
    from scipy import stats

    n = 250
    p = 0.01  # 99% VaR -> expected exception rate is 1%

    def classify_zone(k: int) -> tuple[str, float]:
        cum_prob = float(stats.binom.cdf(k, n, p))
        if cum_prob < 0.95:
            zone = "GREEN"
        elif cum_prob < 0.9999:
            zone = "YELLOW"
        else:
            zone = "RED"
        return zone, cum_prob

    # 1. Green Zone: 0-4 exceptions (P <= 0.892188 < 0.95)
    for k in range(5):
        zone, prob = classify_zone(k)
        assert zone == "GREEN", f"Expected GREEN for k={k}, got {zone} (prob={prob})"
        assert prob < 0.95

    assert abs(classify_zone(4)[1] - 0.892188) < 1e-4

    # 2. Yellow Zone: 5-9 exceptions (0.95 <= P < 0.9999)
    for k in range(5, 10):
        zone, prob = classify_zone(k)
        assert zone == "YELLOW", f"Expected YELLOW for k={k}, got {zone} (prob={prob})"
        assert 0.95 <= prob < 0.9999

    assert abs(classify_zone(5)[1] - 0.958817) < 1e-4
    assert abs(classify_zone(9)[1] - 0.999750) < 1e-4

    # 3. Red Zone: 10+ exceptions (P >= 0.999946)
    for k in [10, 11, 15, 20]:
        zone, prob = classify_zone(k)
        assert zone == "RED", f"Expected RED for k={k}, got {zone} (prob={prob})"
        assert prob >= 0.9999

    assert abs(classify_zone(10)[1] - 0.999946) < 1e-4


def test_christoffersen_independence_hand_calculated():
    """
    Validates Christoffersen (1998) first-order Markov test for exception independence.
    
    Test sequence: [0, 0, 1, 1, 0, 0] (T = 6 observations, 5 transitions)
    Transition counts:
      0 -> 0: n00 = 2
      0 -> 1: n01 = 1
      1 -> 0: n10 = 1
      1 -> 1: n11 = 1
      Total transitions = 5
      
    Transition probabilities:
      pi_null = (n01 + n11) / (n00 + n01 + n10 + n11) = (1 + 1) / 5 = 0.4000
      pi_01 = n01 / (n00 + n01) = 1 / (2 + 1) = 1/3 ~ 0.33333333
      pi_11 = n11 / (n10 + n11) = 1 / (1 + 1) = 1/2 = 0.50000000
      
    Hand-calculated Log-Likelihoods:
      ll_null = (n00 + n10) * ln(1 - pi_null) + (n01 + n11) * ln(pi_null)
              = 3 * ln(0.60) + 2 * ln(0.40)
              = 3 * (-0.51082562) + 2 * (-0.91629073)
              = -1.53247687 - 1.83258146 = -3.36505834
              
      ll_alt  = n00 * ln(1 - pi_01) + n01 * ln(pi_01) + n10 * ln(1 - pi_11) + n11 * ln(pi_11)
              = 2 * ln(2/3) + 1 * ln(1/3) + 1 * ln(1/2) + 1 * ln(1/2)
              = 2 * (-0.40546511) + (-1.09861229) + (-0.69314718) + (-0.69314718)
              = -0.81093022 - 1.09861229 - 1.38629436 = -3.29583687
              
    Likelihood Ratio Test Statistic:
      LR_ind = -2 * (ll_null - ll_alt)
             = -2 * (-3.36505834 - (-3.29583687))
             = -2 * (-0.06922147)
             = 0.13844294
             
    p-value from Chi-Square distribution with df=1:
      p = 1 - Chi2_cdf(0.13844294, df=1) = 0.70983388
      Since p > 0.05, null hypothesis of independence CANNOT be rejected (test passes).
    """
    import math

    from scipy import stats

    indicators = [0, 0, 1, 1, 0, 0]
    n00, n01, n10, n11 = 0, 0, 0, 0
    for i in range(len(indicators) - 1):
        prev_i = indicators[i]
        curr_i = indicators[i + 1]
        if prev_i == 0 and curr_i == 0:
            n00 += 1
        elif prev_i == 0 and curr_i == 1:
            n01 += 1
        elif prev_i == 1 and curr_i == 0:
            n10 += 1
        elif prev_i == 1 and curr_i == 1:
            n11 += 1

    assert (n00, n01, n10, n11) == (2, 1, 1, 1)

    total_transitions = n00 + n01 + n10 + n11
    pi_null = (n01 + n11) / total_transitions
    pi_01 = n01 / (n00 + n01)
    pi_11 = n11 / (n10 + n11)

    assert abs(pi_null - 0.40) < 1e-9
    assert abs(pi_01 - 1.0 / 3.0) < 1e-9
    assert abs(pi_11 - 0.50) < 1e-9

    def safe_ll(count, prob):
        return count * math.log(prob) if count > 0 and prob > 0 else 0.0

    ll_null = safe_ll(n00 + n10, 1.0 - pi_null) + safe_ll(n01 + n11, pi_null)
    ll_alt = safe_ll(n00, 1.0 - pi_01) + safe_ll(n01, pi_01) + safe_ll(n10, 1.0 - pi_11) + safe_ll(n11, pi_11)

    assert abs(ll_null - (-3.36505834)) < 1e-6
    assert abs(ll_alt - (-3.29583687)) < 1e-6

    lr_stat = -2.0 * (ll_null - ll_alt)
    assert abs(lr_stat - 0.13844294) < 1e-6

    p_val = 1.0 - stats.chi2.cdf(lr_stat, df=1)
    assert abs(p_val - 0.70983388) < 1e-6
    assert p_val >= 0.05  # Independent (passed)

    # Now verify clustered violation sequence: 5 consecutive exceptions in 20 periods
    # Highly dependent; must strongly reject independence (p < 0.001)
    clustered = [1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    c_n00, c_n01, c_n10, c_n11 = 0, 0, 0, 0
    for i in range(len(clustered) - 1):
        p_i, cur_i = clustered[i], clustered[i + 1]
        if p_i == 0 and cur_i == 0:
            c_n00 += 1
        elif p_i == 0 and cur_i == 1:
            c_n01 += 1
        elif p_i == 1 and cur_i == 0:
            c_n10 += 1
        elif p_i == 1 and cur_i == 1:
            c_n11 += 1

    assert (c_n00, c_n01, c_n10, c_n11) == (14, 0, 1, 4)
    c_total = c_n00 + c_n01 + c_n10 + c_n11
    c_pi_null = (c_n01 + c_n11) / c_total
    c_pi_01 = c_n01 / (c_n00 + c_n01) if (c_n00 + c_n01) > 0 else 0.0
    c_pi_11 = c_n11 / (c_n10 + c_n11) if (c_n10 + c_n11) > 0 else 0.0

    c_ll_null = safe_ll(c_n00 + c_n10, 1.0 - c_pi_null) + safe_ll(c_n01 + c_n11, c_pi_null)
    c_ll_alt = safe_ll(c_n00, 1.0 - c_pi_01) + safe_ll(c_n01, c_pi_01) + safe_ll(c_n10, 1.0 - c_pi_11) + safe_ll(c_n11, c_pi_11)
    c_lr_stat = -2.0 * (c_ll_null - c_ll_alt)
    c_p_val = 1.0 - stats.chi2.cdf(c_lr_stat, df=1)

    assert abs(c_lr_stat - 14.55279605) < 1e-4
    assert abs(c_p_val - 0.00013628) < 1e-5
    assert c_p_val < 0.05  # Rejects independence!

