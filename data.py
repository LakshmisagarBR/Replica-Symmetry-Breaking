"""
╔══════════════════════════════════════════════════════════════════════════╗
║  REPLICA SYMMETRY BREAKING  |  SPIN GLASS ENERGY LANDSCAPE OF MARKETS  ║
║  data.py  —  MODULE 1: DATA                                              ║
║                                                                          ║
║  Generates 504-day synthetic S&P 500 returns with:                      ║
║    • Cholesky-correlated sector block correlation structure               ║
║    • GARCH(1,1) volatility clustering per stock                          ║
║    • Three embedded market stress regimes that drive RSB transitions     ║
║    • Calibrated to 2022-2024 S&P 500 realized parameters                ║
║                                                                          ║
║  The stress regimes are critical: during calm markets the spin glass     ║
║  is in the paramagnetic phase (q=0, simple landscape). During stress,   ║
║  the effective temperature drops and replica symmetry breaks —           ║
║  the portfolio energy landscape becomes rugged and multi-modal.          ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import numpy as np
import pandas as pd
from datetime import datetime
from config import TICKERS, TICKER_SECTOR, SECTORS, CONFIG


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}]  DATA  |  {msg}")


# ── Sector-level inter-correlation block (6×6, calibrated to S&P 500 2022–2024)
_SECTOR_CORR = np.array([
    # TECH   FIN    HLT    ENR    CON    IND
    [1.00,  0.52,  0.38,  0.22,  0.61,  0.48],
    [0.52,  1.00,  0.34,  0.30,  0.44,  0.50],
    [0.38,  0.34,  1.00,  0.18,  0.35,  0.33],
    [0.22,  0.30,  0.18,  1.00,  0.25,  0.32],
    [0.61,  0.44,  0.35,  0.25,  1.00,  0.45],
    [0.48,  0.50,  0.33,  0.32,  0.45,  1.00],
])
_SECTOR_LIST = list(SECTORS.keys())
_SECTOR_IDX  = {s: i for i, s in enumerate(_SECTOR_LIST)}

# Annualised base volatility per sector
_SECTOR_VOL = {
    "TECHNOLOGY":  0.32, "FINANCIALS": 0.26,
    "HEALTHCARE":  0.22, "ENERGY":     0.34,
    "CONSUMER":    0.28, "INDUSTRIALS":0.24,
}

# Per-ticker idiosyncratic spread (additive to sector vol)
_TICKER_SPREAD = {
    "AAPL":-0.04,"MSFT":-0.06,"NVDA": 0.14,"GOOGL":-0.02,"META": 0.08,
    "JPM": -0.03,"BAC":  0.04,"GS":   0.06,"MS":   0.05, "C":   0.07,
    "JNJ": -0.06,"UNH":  0.02,"PFE":  0.06,"ABBV": 0.04, "MRK":-0.02,
    "XOM": -0.04,"CVX": -0.03,"COP":  0.06,"SLB":  0.12, "EOG": 0.09,
    "AMZN": 0.08,"TSLA": 0.22,"HD":  -0.04,"MCD": -0.08, "NKE": 0.03,
    "GE":   0.06,"CAT":  0.04,"BA":   0.12,"RTX": -0.02, "HON":-0.03,
}

# GARCH(1,1) parameters — calibrated to S&P 500
_OMEGA = 4e-6
_ALPHA = 0.09
_BETA  = 0.88


def _build_corr_matrix():
    """Build the full 30×30 Cholesky-valid correlation matrix."""
    N   = len(TICKERS)
    rng = np.random.default_rng(CONFIG["SEED"])
    rho = np.eye(N)

    for i, ti in enumerate(TICKERS):
        for j, tj in enumerate(TICKERS):
            if i >= j:
                continue
            si  = TICKER_SECTOR[ti]
            sj  = TICKER_SECTOR[tj]
            base = (0.68 if si == sj
                    else _SECTOR_CORR[_SECTOR_IDX[si], _SECTOR_IDX[sj]])
            noise      = 0.06 * (rng.random() - 0.5)
            rho[i, j]  = rho[j, i] = np.clip(base + noise, -0.9, 0.95)

    # Project to nearest positive-definite matrix
    ev, evec = np.linalg.eigh(rho)
    ev       = np.maximum(ev, 1e-8)
    rho      = evec @ np.diag(ev) @ evec.T
    d        = np.sqrt(np.diag(rho))
    rho      = rho / np.outer(d, d)
    np.fill_diagonal(rho, 1.0)
    return rho


def _garch_path(T, base_vol, rng, stress_regimes=None):
    """
    Simulate GARCH(1,1) conditional volatility path.

    stress_regimes: list of (start, end, multiplier) tuples.
    Each multiplier amplifies volatility in that window, driving
    the spin glass below its critical temperature and triggering RSB.
    """
    h     = np.full(T, base_vol ** 2)
    eps   = rng.standard_normal(T)

    for t in range(1, T):
        innov  = h[t-1]**0.5 * eps[t-1]
        h[t]   = _OMEGA + _ALPHA * innov**2 + _BETA * h[t-1]
        h[t]   = np.clip(h[t], 1e-9, (0.30)**2 / 252)

    sigma = np.sqrt(h)

    # Inject three stress regimes — these are the RSB phase transitions
    if stress_regimes:
        for start, end, mult in stress_regimes:
            sigma[start:end] *= mult

    return sigma


def fetch_all():
    """
    Generate calibrated synthetic S&P 500 market data.

    Three embedded stress regimes force the spin glass through
    a phase transition from paramagnetic (q=0) to RSB (q>0):
        Regime 1: days  80–110  (mild correction,   mult=2.5)
        Regime 2: days 230–280  (sharp drawdown,    mult=4.0)
        Regime 3: days 380–420  (flash crash spike, mult=5.5)

    Returns dict with keys:
        returns    — pd.DataFrame  (T × N)
        dates      — pd.DatetimeIndex
        vol_proxy  — np.ndarray  (T,)  cross-sectional realized vol
        tickers    — list[str]
    """
    rng = np.random.default_rng(CONFIG["SEED"])
    T   = CONFIG["T_DAYS"]
    N   = len(TICKERS)

    log(f"Building calibrated synthetic returns  [{N} stocks × {T} days] ...")

    # ── Correlation structure
    rho = _build_corr_matrix()
    L   = np.linalg.cholesky(rho)   # Cholesky factor for correlated draws

    # ── Three RSB-triggering stress regimes
    stress = [(80, 110, 2.5), (230, 280, 4.0), (380, 420, 5.5)]

    # ── Per-ticker GARCH volatility paths  [T × N]
    base_vols   = np.array([
        (_SECTOR_VOL[TICKER_SECTOR[t]] + _TICKER_SPREAD.get(t, 0.0)) / np.sqrt(252)
        for t in TICKERS
    ])
    daily_sigma = np.column_stack([
        _garch_path(T, base_vols[i], rng, stress)
        for i in range(N)
    ])

    # ── Correlated Gaussian innovations
    Z      = rng.standard_normal((T, N))
    Z_corr = Z @ L.T          # shape (T, N)

    # ── Annualised drifts per sector
    _DRIFT = {
        "TECHNOLOGY": 0.18, "FINANCIALS": 0.10,
        "HEALTHCARE": 0.08, "ENERGY":     0.12,
        "CONSUMER":   0.14, "INDUSTRIALS":0.09,
    }
    mu_daily = np.array([_DRIFT[TICKER_SECTOR[t]] / 252 for t in TICKERS])

    # ── Log returns:  r_t = (μ - σ²/2)dt + σ·dW
    log_rets = (mu_daily - 0.5 * daily_sigma**2) + daily_sigma * Z_corr

    # ── Date index (2 trading years ending 2024-12-31)
    dates   = pd.bdate_range(end="2024-12-31", periods=T)
    returns = pd.DataFrame(log_rets, index=dates, columns=TICKERS)

    # ── Cross-sectional realized vol proxy (annualised)
    rv_roll   = (returns**2).rolling(21, min_periods=5).mean()
    vol_proxy = np.sqrt(rv_roll.mean(axis=1).values * 252)
    vol_proxy = np.nan_to_num(vol_proxy, nan=np.nanmean(vol_proxy))

    log(f"Returns  shape={returns.shape}  "
        f"[{dates[0].date()} -> {dates[-1].date()}]")
    log(f"Vol proxy  min={vol_proxy.min():.3f}  "
        f"max={vol_proxy.max():.3f}  mean={vol_proxy.mean():.3f}")
    log(f"Stress regimes injected at days: {[(s,e) for s,e,_ in stress]}")

    return {
        "returns":   returns,
        "dates":     dates,
        "vol_proxy": vol_proxy,
        "tickers":   TICKERS,
        "stress":    stress,
    }