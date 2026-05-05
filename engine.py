"""
╔══════════════════════════════════════════════════════════════════════════╗
║  REPLICA SYMMETRY BREAKING  |  SPIN GLASS ENERGY LANDSCAPE OF MARKETS  ║
║  engine.py  —  MODULE 2: RSB ENGINE                                      ║
║                                                                          ║
║  Physical Model: Sherrington-Kirkpatrick (SK) Spin Glass                ║
║  ─────────────────────────────────────────────────────                   ║
║  The SK Hamiltonian:                                                     ║
║                                                                          ║
║      H = -Σᵢ<ⱼ  Jᵢⱼ · Sᵢ · Sⱼ                                        ║
║                                                                          ║
║  where Sᵢ ∈ {-1, +1} are "spins" (asset positions: long/short)         ║
║  and   Jᵢⱼ = ρᵢⱼ / √N  is the coupling from rolling correlation.        ║
║                                                                          ║
║  The effective temperature of the spin glass:                            ║
║                                                                          ║
║      T(t) = σ(t) / J_rms                                                ║
║                                                                          ║
║  where σ(t) = realized market vol and J_rms = rms coupling strength.    ║
║                                                                          ║
║  Phase diagram:                                                          ║
║      T > T_c  →  Paramagnetic phase:  q(x) = 0  (simple landscape)     ║
║      T < T_c  →  Spin glass phase:    q(x) > 0  (RSB, rugged)          ║
║                                                                          ║
║  Critical temperature: T_c = J_rms  (exact SK result)                   ║
║                                                                          ║
║  The Parisi Order Parameter q(x), x ∈ [0,1]:                           ║
║  ─────────────────────────────────────────────                           ║
║  Parisi (1979) showed the full RSB solution involves a function q(x)    ║
║  rather than a single scalar. Physically:                                ║
║                                                                          ║
║      q(x) = overlap between two portfolio configurations drawn           ║
║             from basins that share at least x fraction of phase space   ║
║                                                                          ║
║  Interpretation of q(x) shape:                                          ║
║      Flat q(x) = 0        →  one global optimum, simple landscape       ║
║      Step at x = m*       →  1-RSB: two levels of basins               ║
║      Continuously rising  →  Full RSB: infinitely many basin levels     ║
║                                                                          ║
║  The staircase emerges during crises — the portfolio optimization        ║
║  landscape shatters into thousands of disconnected local optima.        ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import numpy as np
from scipy.ndimage import uniform_filter1d
from datetime import datetime
from config import CONFIG, TICKERS, TICKER_SECTOR


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] ENGINE |  {msg}")


# ═══════════════════════════════════════════════════════════════════════
# 2.1  GAUSS-HERMITE QUADRATURE NODES & WEIGHTS  (pre-computed)
# ═══════════════════════════════════════════════════════════════════════

def _gh_nodes_weights(n):
    """
    Gauss-Hermite nodes and weights for ∫ f(x) exp(-x²) dx.
    We rescale to standard normal Gaussian quadrature:
        ∫ f(z) N(0,1) dz  ≈  Σ wᵢ · f(√2 · xᵢ) / √π
    """
    pts, wts = np.polynomial.hermite.hermgauss(n)
    pts = pts * np.sqrt(2.0)          # rescale to N(0,1)
    wts = wts / np.sqrt(np.pi)        # normalise
    return pts, wts


_GH_PTS, _GH_WTS = _gh_nodes_weights(CONFIG["GAUSS_ORDER"])


# ═══════════════════════════════════════════════════════════════════════
# 2.2  SK SELF-CONSISTENCY:  Solve  q = ∫ Dz tanh²(β·J·√q · z)
# ═══════════════════════════════════════════════════════════════════════

def _solve_q_ea(beta_J: float) -> float:
    """
    Solve the Edwards-Anderson order parameter for the SK model.

    Self-consistency equation:
        q = ∫ Dz  tanh²(β·J·√q · z)

    where β·J is the reduced inverse temperature.

    Parameters
    ----------
    beta_J : float  — dimensionless coupling  = J_rms / T(t)

    Returns
    -------
    q_EA   : float ∈ [0, 1]  — zero in paramagnetic phase, > 0 in spin glass
    """
    if beta_J <= 1.0:
        # Paramagnetic phase: q_EA = 0 exactly (T ≥ T_c = J_rms)
        return 0.0

    # Spin glass phase — damped fixed-point iteration
    q = min((beta_J - 1.0) / beta_J, 0.99)   # warm start near T_c

    for iteration in range(CONFIG["MAX_ITER"]):
        # ∫ N(0,1) dz  tanh²(β·J·√q · z)  via Gauss-Hermite
        arg      = beta_J * np.sqrt(max(q, 1e-12)) * _GH_PTS
        integrand = np.tanh(arg) ** 2
        q_new    = float(np.dot(_GH_WTS, integrand))

        delta = abs(q_new - q)
        # Damped update to avoid oscillation
        q = (1.0 - CONFIG["DAMPING"]) * q + CONFIG["DAMPING"] * q_new

        if delta < 1e-9:
            break

    return float(np.clip(q, 0.0, 1.0))


# ═══════════════════════════════════════════════════════════════════════
# 2.3  PARISI ORDER PARAMETER PROFILE  q(x)
# ═══════════════════════════════════════════════════════════════════════

def _parisi_profile(beta_J: float, q_EA: float, N_x: int = 60) -> np.ndarray:
    """
    Compute the Parisi order parameter function q(x) for x ∈ [0,1].

    Physical interpretation of each regime:

    Paramagnetic (T > T_c, beta_J < 1):
        q(x) = 0  for all x  — no RSB, single energy basin

    Near T_c (1 < beta_J < 1.3):
        q(x) ≈ 0 for x < m*, then rises to q_EA — weak 1-RSB onset

    Deep spin glass (beta_J >> 1):
        q(x) is a continuously rising function — full RSB
        Infinitely many ultrametrically nested basins

    The shape uses the exact near-T_c expansion and interpolates
    to the full-RSB shape for deep spin glass:

        q(x) = q_EA · [x / (m* + ε)]^(1/γ)   for x ≤ m*
        q(x) = q_EA                              for x >  m*

    where m* = 1/beta_J  (Parisi breakpoint, exact near T_c)
    and   γ  = (beta_J - 1) / beta_J  (ruggedness exponent)

    For full RSB (large beta_J), q(x) becomes a smooth, continuously
    rising curve spanning all of [0, 1].

    Parameters
    ----------
    beta_J : float  — dimensionless coupling = J_rms / T
    q_EA   : float  — Edwards-Anderson order parameter (from _solve_q_ea)
    N_x    : int    — number of x points

    Returns
    -------
    np.ndarray shape (N_x,)
    """
    x_vals = np.linspace(0.0, 1.0, N_x)

    if q_EA < 1e-9:
        return np.zeros(N_x)

    # Parisi breakpoint  m* = T / T_c = 1 / beta_J  (exact SK result)
    m_star = np.clip(1.0 / beta_J, 0.01, 0.99)

    # Ruggedness exponent: 0 near T_c (step-like), → 1 deep in glass (smooth)
    gamma  = np.clip((beta_J - 1.0) / beta_J, 0.05, 1.0)

    q_profile = np.zeros(N_x)
    for i, x in enumerate(x_vals):
        if x <= m_star:
            # Below breakpoint: power-law rise from 0 to q_EA
            ratio       = x / (m_star + 1e-12)
            q_profile[i] = q_EA * (ratio ** (1.0 / gamma))
        else:
            # Above breakpoint: plateau at q_EA
            # For full RSB, add a gentle overshoot then flatten
            excess       = (x - m_star) / (1.0 - m_star + 1e-12)
            q_profile[i] = q_EA * (1.0 + 0.08 * gamma * excess
                                   * np.exp(-3.0 * excess))
            q_profile[i] = np.clip(q_profile[i], 0.0, 1.0)

    return q_profile


# ═══════════════════════════════════════════════════════════════════════
# 2.4  LANDSCAPE COMPLEXITY  (number of metastable states)
# ═══════════════════════════════════════════════════════════════════════

def _complexity_score(beta_J: float, q_EA: float) -> float:
    """
    Compute the annealed complexity Σ (log number of metastable states).

    In the SK model, the number of metastable states scales as:
        N_states ~ exp(N · Σ)

    For the 1-RSB approximation near T_c:
        Σ ≈ ln(2) · [(beta_J² · (1-q_EA)² - 1) / 2]  (simplified)

    Returns a normalised complexity in [0, 1] for plotting.
    """
    if q_EA < 1e-9:
        return 0.0
    # Entropic cost of having multiple basins
    raw = 0.5 * (beta_J**2 * (1.0 - q_EA)**2 - 1.0)
    return float(np.clip(raw / 5.0, 0.0, 1.0))    # normalise to [0,1]


# ═══════════════════════════════════════════════════════════════════════
# 2.5  ROLLING SPIN GLASS PARAMETERS
# ═══════════════════════════════════════════════════════════════════════

def _rolling_spin_glass_params(returns_arr: np.ndarray,
                                vol_proxy: np.ndarray,
                                t: int,
                                window: int) -> tuple:
    """
    Compute SK model parameters at time t using a rolling window.

    Returns
    -------
    beta_J    : float  — dimensionless inverse temperature
    J_rms     : float  — RMS coupling strength from correlation matrix
    T_eff     : float  — effective temperature of the spin glass
    rho_mean  : float  — mean off-diagonal correlation
    """
    window_rets = returns_arr[max(0, t - window):t, :]
    if window_rets.shape[0] < 10:
        return 0.5, 0.1, 0.2, 0.3

    # Rolling correlation matrix
    C = np.corrcoef(window_rets.T)   # (N × N)
    N = C.shape[0]

    # SK coupling: J_ij = ρ_ij / √N  (standard SK normalisation)
    upper = C[np.triu_indices(N, k=1)]
    J_rms = np.sqrt(np.mean(upper**2)) / np.sqrt(N)

    # Effective temperature = realized vol (normalised to same scale as J_rms)
    T_eff = vol_proxy[t] / (np.sqrt(252) * 10.0)   # scale factor

    beta_J = J_rms / (T_eff + 1e-10)
    rho_mean = float(np.mean(upper))

    return float(beta_J), float(J_rms), float(T_eff), float(rho_mean)


# ═══════════════════════════════════════════════════════════════════════
# 2.6  FULL RSB SURFACE  q(x, t)
# ═══════════════════════════════════════════════════════════════════════

def compute_rsb_surface(data_bundle: dict) -> dict:
    """
    Compute the full 2D Parisi order parameter surface q(x, t).

    X-axis of surface : x ∈ [0,1]  (Parisi replica parameter)
    Y-axis of surface : calendar time t  (subsampled)
    Z-axis of surface : q(x, t)  (landscape overlap / ruggedness)

    Returns dict with:
        q_surface    : np.ndarray  (N_x, N_time)  — the main surface
        q_ea_trace   : np.ndarray  (N_time,)      — Edwards-Anderson q(t)
        m_star_trace : np.ndarray  (N_time,)      — Parisi breakpoint m*(t)
        beta_J_trace : np.ndarray  (N_time,)      — inverse temp β·J(t)
        complexity   : np.ndarray  (N_time,)      — landscape complexity Σ(t)
        x_vals       : np.ndarray  (N_x,)         — x-axis values
        time_idx     : np.ndarray  (N_time,)      — indices into date array
        phase        : np.ndarray  (N_time,)      — 0=paramagnetic, 1=RSB
        vol_sub      : np.ndarray  (N_time,)      — vol proxy at time points
    """
    returns    = data_bundle["returns"]
    vol_proxy  = data_bundle["vol_proxy"]
    T, N       = returns.shape
    W          = CONFIG["CORR_WINDOW"]
    N_x        = CONFIG["N_X"]
    N_sub      = CONFIG["SUBSAMPLE"]
    rets_arr   = returns.values

    # Subsampled time indices (evenly spaced over valid range)
    t_valid = np.arange(W, T)
    t_sub   = np.round(np.linspace(t_valid[0], t_valid[-1], N_sub)).astype(int)

    log(f"Computing RSB surface  [{N_x} x-points × {N_sub} time-points, "
        f"window={W}] ...")

    x_vals       = np.linspace(0.0, 1.0, N_x)
    q_surface    = np.zeros((N_x, N_sub))
    q_ea_trace   = np.zeros(N_sub)
    m_star_trace = np.zeros(N_sub)
    beta_J_trace = np.zeros(N_sub)
    complexity   = np.zeros(N_sub)
    phase        = np.zeros(N_sub, dtype=int)
    vol_sub      = vol_proxy[t_sub]

    for j, t in enumerate(t_sub):
        if j % 16 == 0:
            log(f"  time-slice {j+1}/{N_sub}  (day {t}) ...")

        beta_J, J_rms, T_eff, rho_mean = _rolling_spin_glass_params(
            rets_arr, vol_proxy, t, W
        )
        q_EA = _solve_q_ea(beta_J)

        q_surface[:, j]   = _parisi_profile(beta_J, q_EA, N_x)
        q_ea_trace[j]     = q_EA
        m_star_trace[j]   = np.clip(1.0 / (beta_J + 1e-10), 0.0, 1.0)
        beta_J_trace[j]   = beta_J
        complexity[j]     = _complexity_score(beta_J, q_EA)
        phase[j]          = 1 if q_EA > 0.01 else 0

    # Smooth surface slightly (3-point uniform filter in time axis)
    q_surface = uniform_filter1d(q_surface, size=3, axis=1, mode="nearest")

    n_rsb = int(phase.sum())
    log(f"RSB surface complete  shape={q_surface.shape}")
    log(f"  q_EA range: [{q_ea_trace.min():.4f}, {q_ea_trace.max():.4f}]")
    log(f"  β·J range:  [{beta_J_trace.min():.3f}, {beta_J_trace.max():.3f}]")
    log(f"  RSB phase:  {n_rsb}/{N_sub} time-points  "
        f"({100*n_rsb/N_sub:.0f}% in spin glass phase)")

    return {
        "q_surface":    q_surface,       # (N_x, N_time)
        "q_ea_trace":   q_ea_trace,      # (N_time,)
        "m_star_trace": m_star_trace,    # (N_time,)
        "beta_J_trace": beta_J_trace,    # (N_time,)
        "complexity":   complexity,      # (N_time,)
        "x_vals":       x_vals,          # (N_x,)
        "time_idx":     t_sub,           # (N_time,)
        "phase":        phase,           # (N_time,)  0=para, 1=RSB
        "vol_sub":      vol_sub,         # (N_time,)
        "N_x":          N_x,
        "N_t":          N_sub,
    }


# ═══════════════════════════════════════════════════════════════════════
# 2.7  SURFACE MESH  for 3-D rendering
# ═══════════════════════════════════════════════════════════════════════

def build_surface_mesh(engine_bundle: dict) -> dict:
    """
    Build X, Y, Z meshgrids for matplotlib plot_surface.

    X : Parisi x parameter  (N_x points, 0 → 1)
    Y : time               (N_time points)
    Z : q(x, t)
    """
    q   = engine_bundle["q_surface"]   # (N_x, N_t)
    N_x = engine_bundle["N_x"]
    N_t = engine_bundle["N_t"]

    x_raw = np.linspace(0.0, 1.0, N_x)
    y_raw = np.arange(N_t)

    # Meshgrid: Y=time along rows, X=Parisi-x along columns
    Y, X = np.meshgrid(y_raw, x_raw)   # both shape (N_x, N_t)
    Z    = q

    return {
        "X": X, "Y": Y, "Z": Z,
        "z_min": float(Z.min()),
        "z_max": float(max(Z.max(), 1e-6)),
        "N_x":   N_x,
        "N_t":   N_t,
    }