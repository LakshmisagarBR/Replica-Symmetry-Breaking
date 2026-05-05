"""
╔═══════════════════════════════════════════════════════════════════════                                                                    ═══╗
║  REPLICA SYMMETRY BREAKING  |  SPIN GLASS ENERGY LANDSCAPE OF MARKETS  ║
║  config.py  —  global constants, Bloomberg Dark theme, colormaps         ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
from matplotlib.colors import LinearSegmentedColormap

# ═══════════════════════════════════════════════════════════════════════
# STOCK UNIVERSE  —  30 S&P 500 stocks, 6 sectors × 5 stocks
# ═══════════════════════════════════════════════════════════════════════
SECTORS = {
    "TECHNOLOGY":  ["AAPL", "MSFT", "NVDA", "GOOGL", "META"],
    "FINANCIALS":  ["JPM",  "BAC",  "GS",   "MS",    "C"   ],
    "HEALTHCARE":  ["JNJ",  "UNH",  "PFE",  "ABBV",  "MRK" ],
    "ENERGY":      ["XOM",  "CVX",  "COP",  "SLB",   "EOG" ],
    "CONSUMER":    ["AMZN", "TSLA", "HD",   "MCD",   "NKE" ],
    "INDUSTRIALS": ["GE",   "CAT",  "BA",   "RTX",   "HON" ],
}

TICKERS = [t for tickers in SECTORS.values() for t in tickers]

TICKER_SECTOR = {t: s for s, tickers in SECTORS.items() for t in tickers}

SECTOR_COLORS = {
    "TECHNOLOGY":  "#00f2ff",
    "FINANCIALS":  "#ff9500",
    "HEALTHCARE":  "#00ff41",
    "ENERGY":      "#ffd400",
    "CONSUMER":    "#ff1493",
    "INDUSTRIALS": "#bb66ff",
}

# ═══════════════════════════════════════════════════════════════════════
# BLOOMBERG DARK THEME  —  full quant finance spec
# ═══════════════════════════════════════════════════════════════════════
THEME = {
    "BG":         "#000000",
    "PANEL_BG":   "#0a0a0a",
    "GRID":       "#1a1a1a",
    "SPINE":      "#333333",
    "TEXT":       "#ffffff",
    "TEXT_DIM":   "#aaaaaa",
    "ORANGE":     "#ff9500",
    "ORANGE_HOT": "#ff6b00",
    "CYAN":       "#00f2ff",
    "YELLOW":     "#ffd400",
    "GREEN":      "#00ff41",
    "RED":        "#ff3050",
    "MAGENTA":    "#ff1493",
    "PINK":       "#ff2a9e",
    "BLUE":       "#00bfff",
    "PURPLE":     "#bb66ff",
    "FONT":       "DejaVu Sans",
    "WATERMARK":  "@Laksh",
}

# ═══════════════════════════════════════════════════════════════════════
# REPLICA SYMMETRY BREAKING COLORMAP
#
# The Parisi order parameter q(x) ranges from 0 to q_EA.
# Colour encodes the "ruggedness" of the portfolio energy landscape:
#
#   q ≈ 0.00  →  deep void purple-black  (paramagnetic, one optimum)
#   q ≈ 0.15  →  deep blue               (weak RSB, shallow basins)
#   q ≈ 0.35  →  magenta                 (1-RSB, multiple trapped states)
#   q ≈ 0.60  →  orange-hot              (deep RSB, rugged landscape)
#   q ≈ 0.85  →  orange                  (approaching full RSB, crisis)
#   q = 1.00  →  blazing yellow-white    (full RSB, maximum ruggedness)
# ═══════════════════════════════════════════════════════════════════════
CMAP_RSB = LinearSegmentedColormap.from_list(
    "rsb_parisi",
    [
        "#000000",   # 0.00 — void black        paramagnetic
        "#0d001a",   # 0.08 — near-void purple
        "#1a0040",   # 0.18 — deep indigo
        "#3a006f",   # 0.30 — rich purple
        "#7b00b4",   # 0.42 — violet
        "#ff1493",   # 0.55 — magenta           1-RSB onset
        "#ff6b00",   # 0.70 — orange-hot        deep RSB
        "#ff9500",   # 0.82 — orange            near-crisis
        "#ffd400",   # 0.92 — yellow            pre-crisis
        "#ffffff",   # 1.00 — white-hot         full RSB / crisis
    ],
    N=512,
)

# Complexity score colormap (number of metastable states)
CMAP_COMPLEXITY = LinearSegmentedColormap.from_list(
    "complexity",
    ["#000000", "#00bfff", "#00f2ff", "#ffffff"],
    N=256,
)

# ═══════════════════════════════════════════════════════════════════════
# PIPELINE CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════
CONFIG = {
    # ── Data
    "T_DAYS":        504,      # 2 trading years
    "SEED":          42,

    # ── Engine
    "CORR_WINDOW":   60,       # rolling correlation window (days)
    "N_X":           60,       # Parisi x-axis resolution (number of x points)
    "SUBSAMPLE":     80,       # time-points on 3D surface
    "GAUSS_ORDER":   64,       # Gauss-Hermite quadrature order for SK self-consistency
    "MAX_ITER":      300,      # fixed-point iteration max
    "DAMPING":       0.25,     # damped iteration factor

    # ── Output
    "OUT_DIR":       "outputs",
    "STATIC_PNG":    "outputs/rsb_spin_glass.png",
    "ANIM_GIF":      "outputs/rsb_animation.gif",
    "DPI":           100,
    "FIG_SIZE":      (19.2, 10.8),

    # ── Animation
    "GIF_DPI":       80,
    "GIF_FPS":       10,
}

os.makedirs(CONFIG["OUT_DIR"], exist_ok=True)