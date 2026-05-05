"""
╔══════════════════════════════════════════════════════════════════════════╗
║  REPLICA SYMMETRY BREAKING  |  SPIN GLASS ENERGY LANDSCAPE OF MARKETS  ║
║  visual.py  —  MODULE 3: STATIC IMAGE RENDERER  (1920×1080)             ║
║                                                                          ║
║  Layout: Bloomberg Multi-Panel Dashboard (Type B)                        ║
║                                                                          ║
║  ┌──────────────────────────────┬────────────────────────┐              ║
║  │                              │  q_EA(t) time series   │              ║
║  │  3-D Parisi Surface q(x,t)   ├────────────────────────┤              ║
║  │  (main visualization)        │  β·J(t) temperature    │              ║
║  │                              ├────────────────────────┤              ║
║  │  Orange ridge = q_EA trace   │  Complexity Σ(t)       │              ║
║  │  Cyan ridge   = m*(t) line   ├────────────────────────┤              ║
║  │  Floor shadow = contourf     │  Phase diagram  T/T_c  │              ║
║  └──────────────────────────────┴────────────────────────┘              ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.colors import Normalize
from matplotlib.cm import ScalarMappable
from mpl_toolkits.mplot3d import Axes3D
from datetime import datetime

from config import THEME, CMAP_RSB, CMAP_COMPLEXITY, CONFIG, SECTORS, SECTOR_COLORS, TICKERS


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] VISUAL |  {msg}")


# ═══════════════════════════════════════════════════════════════════════
# HELPER: style 2-D side panel
# ═══════════════════════════════════════════════════════════════════════

def _style(ax, xlabel="", ylabel="", title=""):
    ax.set_facecolor(THEME["PANEL_BG"])
    for sp in ax.spines.values():
        sp.set_color(THEME["SPINE"]); sp.set_linewidth(0.5)
    ax.tick_params(colors=THEME["TEXT_DIM"], labelsize=8,
                   direction="in", length=3)
    ax.xaxis.grid(True, color=THEME["GRID"], lw=0.3, alpha=0.45)
    ax.yaxis.grid(True, color=THEME["GRID"], lw=0.3, alpha=0.45)
    if xlabel:
        ax.set_xlabel(xlabel, color=THEME["TEXT_DIM"],
                      fontsize=9, fontfamily=THEME["FONT"])
    if ylabel:
        ax.set_ylabel(ylabel, color=THEME["TEXT_DIM"],
                      fontsize=9, fontfamily=THEME["FONT"])
    if title:
        ax.set_title(title, color=THEME["TEXT_DIM"],
                     fontsize=8.5, fontfamily=THEME["FONT"],
                     pad=4, loc="left")


# ═══════════════════════════════════════════════════════════════════════
# 3-D PARISI SURFACE
# ═══════════════════════════════════════════════════════════════════════

def _draw_3d_surface(ax3d, mesh, engine_bundle,
                     azim=-55.0, elev=28.0, t_cutoff=None):
    """Draw the full 3-D Parisi order parameter surface q(x, t)."""
    X, Y, Z = mesh["X"], mesh["Y"], mesh["Z"]
    N_x, N_t = mesh["N_x"], mesh["N_t"]
    z_min, z_max = mesh["z_min"], mesh["z_max"]
    norm = Normalize(vmin=z_min, vmax=max(z_max, 1e-6))

    tc = N_t if t_cutoff is None else max(2, min(t_cutoff, N_t))
    Xs = X[:, :tc]; Ys = Y[:, :tc]; Zs = Z[:, :tc]

    # ── 3-D panes (near-pure black)
    pane = (0.02, 0.02, 0.02, 1.0)
    ax3d.xaxis.set_pane_color(pane)
    ax3d.yaxis.set_pane_color(pane)
    ax3d.zaxis.set_pane_color(pane)
    for axis in (ax3d.xaxis, ax3d.yaxis, ax3d.zaxis):
        axis._axinfo["grid"]["color"]     = (0.12, 0.12, 0.12, 0.6)
        axis._axinfo["grid"]["linewidth"] = 0.4
    ax3d.set_facecolor(THEME["BG"])

    # ── Main surface  (full-resolution, hot-pink wireframe)
    ax3d.plot_surface(
        Xs, Ys, Zs,
        cmap=CMAP_RSB, norm=norm,
        alpha=0.93,
        rstride=1, cstride=1,
        edgecolor=(1.0, 0.08, 0.58, 0.10),
        linewidth=0.22,
        antialiased=True,
        zorder=2,
    )

    # ── Floor contour shadow
    z_floor = z_min - 0.18 * (z_max - z_min)
    ax3d.contourf(Xs, Ys, Zs,
                  zdir="z", offset=z_floor,
                  cmap=CMAP_RSB, norm=norm,
                  alpha=0.30, levels=16, zorder=1)

    # ── q_EA ridge  (orange glow — the "maximum ruggedness" trace)
    q_ea = engine_bundle["q_ea_trace"][:tc]
    x_ea = np.ones(tc) * 1.0              # at x=1 (top edge of Parisi axis)
    y_ea = np.arange(tc)
    # Double-line glow trick
    ax3d.plot(x_ea, y_ea, q_ea,
              color=THEME["ORANGE"], lw=5.5, alpha=0.14,
              solid_capstyle="round", zorder=12)
    ax3d.plot(x_ea, y_ea, q_ea,
              color=THEME["ORANGE"], lw=2.0, alpha=0.95,
              solid_capstyle="round", zorder=13,
              label=r"$q_{EA}(t)$")
    # End-point dot
    ax3d.scatter([1.0], [tc-1], [q_ea[-1]],
                 s=40, color=THEME["YELLOW"],
                 edgecolors="white", lw=0.7, zorder=18)

    # ── m*(t) Parisi breakpoint ridge  (cyan — the phase boundary)
    m_star = engine_bundle["m_star_trace"][:tc]
    y_ms   = np.arange(tc)
    # Draw as a vertical curtain from z=0 to surface height at that x
    for j in range(0, tc, max(1, tc//20)):
        x_ms = m_star[j]
        z_ms = float(Z[int(x_ms * (N_x-1)), j]) if N_x > 1 else 0.0
        ax3d.plot([x_ms, x_ms], [j, j], [0.0, z_ms],
                  color=THEME["CYAN"], lw=0.8, alpha=0.35, zorder=8)

    # Cyan ridge at m*(t) along time axis
    z_mstar = np.array([
        float(Z[int(np.clip(m_star[j], 0, 0.999) * (N_x-1)), j])
        for j in range(tc)
    ])
    ax3d.plot(m_star, y_ms, z_mstar,
              color=THEME["CYAN"], lw=2.2, alpha=0.85,
              solid_capstyle="round", zorder=14,
              label=r"$m^*(t)$ breakpoint")

    # ── Axes styling
    ax3d.set_xlabel(r"Parisi parameter  $x$",
                    fontsize=9, color=THEME["TEXT_DIM"],
                    labelpad=10, fontfamily=THEME["FONT"])
    ax3d.set_ylabel("TIME  (rolling windows)",
                    fontsize=9, color=THEME["TEXT_DIM"],
                    labelpad=10, fontfamily=THEME["FONT"])
    ax3d.set_zlabel(r"$q(x,t)$  overlap",
                    fontsize=9, color=THEME["TEXT_DIM"],
                    labelpad=10, fontfamily=THEME["FONT"])
    ax3d.tick_params(colors=THEME["TEXT_DIM"], labelsize=7)

    # X-tick labels (Parisi parameter)
    ax3d.set_xticks([0.0, 0.25, 0.5, 0.75, 1.0])
    ax3d.set_xticklabels(["0", "¼", "½", "¾", "1"],
                          fontsize=7, color=THEME["TEXT_DIM"])

    ax3d.set_box_aspect([1.4, 2.0, 0.80])
    ax3d.view_init(elev=elev, azim=azim)


# ═══════════════════════════════════════════════════════════════════════
# SIDE PANEL 1  —  q_EA(t) Edwards-Anderson order parameter trace
# ═══════════════════════════════════════════════════════════════════════

def _draw_qea_trace(ax, engine_bundle, data_bundle):
    q_ea   = engine_bundle["q_ea_trace"]
    phase  = engine_bundle["phase"]
    N_t    = engine_bundle["N_t"]
    xs     = np.arange(N_t)

    # Shade RSB phase regions
    in_rsb = False; rsb_start = 0
    for i in range(N_t):
        if phase[i] == 1 and not in_rsb:
            rsb_start = i; in_rsb = True
        elif phase[i] == 0 and in_rsb:
            ax.axvspan(rsb_start, i,
                       color=THEME["MAGENTA"], alpha=0.08)
            in_rsb = False
    if in_rsb:
        ax.axvspan(rsb_start, N_t,
                   color=THEME["MAGENTA"], alpha=0.08)

    ax.fill_between(xs, q_ea, alpha=0.18, color=THEME["ORANGE"])
    ax.plot(xs, q_ea, color=THEME["ORANGE"], lw=1.8, zorder=4)
    ax.axhline(0, color=THEME["SPINE"], lw=0.7, ls="--", alpha=0.6)

    # Stress labels
    stress = data_bundle.get("stress", [])
    N_sub  = engine_bundle["N_t"]
    T_DAYS = data_bundle["returns"].shape[0]
    W      = CONFIG["CORR_WINDOW"]
    for s_start, s_end, _ in stress:
        # Map day indices to subsampled time indices
        frac0 = (s_start - W) / max(T_DAYS - W, 1)
        frac1 = (s_end   - W) / max(T_DAYS - W, 1)
        x0    = int(frac0 * N_sub)
        x1    = int(frac1 * N_sub)
        ax.axvspan(x0, x1, color=THEME["RED"], alpha=0.10)

    _style(ax,
           xlabel="Time (windows)",
           ylabel=r"$q_{EA}$",
           title=r"EDWARDS-ANDERSON ORDER PARAMETER  $q_{EA}(t)$")


# ═══════════════════════════════════════════════════════════════════════
# SIDE PANEL 2  —  β·J temperature ratio (phase diagram signal)
# ═══════════════════════════════════════════════════════════════════════

def _draw_beta_J(ax, engine_bundle):
    beta_J = engine_bundle["beta_J_trace"]
    xs     = np.arange(len(beta_J))

    ax.fill_between(xs, beta_J, alpha=0.15, color=THEME["YELLOW"])
    ax.plot(xs, beta_J, color=THEME["YELLOW"], lw=1.6, zorder=4)
    ax.axhline(1.0, color=THEME["CYAN"], lw=1.2, ls="--",
               alpha=0.85, label=r"$T_c = J_{rms}$")

    # Fill above T_c (RSB zone)
    ax.fill_between(xs, beta_J, 1.0,
                    where=beta_J > 1.0,
                    color=THEME["MAGENTA"], alpha=0.12,
                    label="Spin glass phase")

    leg = ax.legend(fontsize=7, facecolor=THEME["BG"],
                    edgecolor=THEME["GRID"], loc="upper left")
    for txt in leg.get_texts():
        txt.set_color(THEME["TEXT_DIM"])

    _style(ax,
           xlabel="Time (windows)",
           ylabel=r"$\beta \cdot J_{rms}$",
           title=r"INVERSE TEMPERATURE  $\beta \cdot J$  (>1 = RSB phase)")


# ═══════════════════════════════════════════════════════════════════════
# SIDE PANEL 3  —  Landscape complexity Σ(t)
# ═══════════════════════════════════════════════════════════════════════

def _draw_complexity(ax, engine_bundle):
    comp = engine_bundle["complexity"]
    xs   = np.arange(len(comp))

    # Colour bars by complexity level using RSB colormap
    norm  = Normalize(vmin=0, vmax=max(comp.max(), 1e-6))
    for i in range(len(xs) - 1):
        col = CMAP_COMPLEXITY(norm(comp[i]))
        ax.fill_between([xs[i], xs[i+1]],
                        [comp[i], comp[i+1]],
                        alpha=0.70, color=col)

    ax.plot(xs, comp, color=THEME["PURPLE"], lw=1.8, zorder=5)
    ax.scatter(xs[comp > 0.5], comp[comp > 0.5],
               s=14, color=THEME["YELLOW"],
               edgecolors="none", zorder=6, alpha=0.7)

    _style(ax,
           xlabel="Time (windows)",
           ylabel=r"$\Sigma$  (normalised)",
           title=r"LANDSCAPE COMPLEXITY  $\Sigma(t)$  (# metastable states)")


# ═══════════════════════════════════════════════════════════════════════
# SIDE PANEL 4  —  T/T_c phase portrait scatter
# ═══════════════════════════════════════════════════════════════════════

def _draw_phase_portrait(ax, engine_bundle):
    q_ea   = engine_bundle["q_ea_trace"]
    beta_J = engine_bundle["beta_J_trace"]
    comp   = engine_bundle["complexity"]
    N_t    = engine_bundle["N_t"]

    # T/T_c = 1 / beta_J
    T_ratio = 1.0 / (beta_J + 1e-9)

    norm = Normalize(vmin=0, vmax=max(comp.max(), 1e-6))
    colors = [CMAP_COMPLEXITY(norm(c)) for c in comp]

    sc = ax.scatter(T_ratio, q_ea,
                    c=comp, cmap=CMAP_COMPLEXITY,
                    s=18, edgecolors="none",
                    alpha=0.75, zorder=4)

    # Phase boundary line: q_EA = 0 at T/T_c = 1
    ax.axvline(1.0, color=THEME["CYAN"], lw=1.0, ls="--", alpha=0.7)
    ax.axhline(0.0, color=THEME["SPINE"], lw=0.7, ls="--", alpha=0.5)

    # Annotate phases
    ax.text(0.55, q_ea.max() * 0.85, "SPIN GLASS\n(RSB phase)",
            color=THEME["MAGENTA"], fontsize=7,
            fontfamily=THEME["FONT"], ha="center")
    ax.text(1.6, q_ea.max() * 0.10, "PARAMAGNETIC",
            color=THEME["TEXT_DIM"], fontsize=7,
            fontfamily=THEME["FONT"], ha="center")

    _style(ax,
           xlabel=r"$T / T_c$",
           ylabel=r"$q_{EA}$",
           title=r"PHASE PORTRAIT  $(T/T_c,\; q_{EA})$")


# ═══════════════════════════════════════════════════════════════════════
# COLORBAR
# ═══════════════════════════════════════════════════════════════════════

def _draw_colorbar(fig, mesh):
    norm = Normalize(vmin=mesh["z_min"], vmax=mesh["z_max"])
    sm   = ScalarMappable(cmap=CMAP_RSB, norm=norm)
    sm.set_array([])

    cax  = fig.add_axes([0.033, 0.13, 0.007, 0.38])
    cbar = fig.colorbar(sm, cax=cax, orientation="vertical")
    cbar.ax.tick_params(colors=THEME["TEXT_DIM"], labelsize=7)
    cbar.set_label(r"$q(x,t)$  order parameter",
                   color=THEME["TEXT_DIM"], fontsize=8,
                   fontfamily=THEME["FONT"], labelpad=6)
    cbar.ax.yaxis.label.set_color(THEME["TEXT_DIM"])
    cbar.ax.text(3.6, 0.02, "PARAMAGNETIC\n(one optimum)",
                 color=THEME["TEXT_DIM"], fontsize=6.5, va="bottom")
    cbar.ax.text(3.6, 0.98, "FULL RSB\n(rugged chaos)",
                 color=THEME["YELLOW"], fontsize=6.5, va="top")


# ═══════════════════════════════════════════════════════════════════════
# TITLE BLOCK
# ═══════════════════════════════════════════════════════════════════════

def _draw_title_block(fig, engine_bundle, data_bundle):
    q_ea   = engine_bundle["q_ea_trace"]
    beta_J = engine_bundle["beta_J_trace"]
    N_rsb  = int(engine_bundle["phase"].sum())
    N_t    = engine_bundle["N_t"]
    dates  = data_bundle["dates"]

    date_range = (f"{dates[0].strftime('%b %Y')} – "
                  f"{dates[-1].strftime('%b %Y')}")

    # Main title  (orange, ALL CAPS, 24pt bold)
    fig.text(0.50, 0.965,
             "REPLICA SYMMETRY BREAKING  |  SPIN GLASS ENERGY LANDSCAPE OF MARKETS",
             ha="center", fontsize=22, fontweight="bold",
             color=THEME["ORANGE"], fontfamily=THEME["FONT"])

    # Subtitle / equation
    fig.text(0.50, 0.937,
             r"$q(x,t) = \mathrm{Parisi\;order\;parameter}$"
             r"     $H = -\sum_{i<j} J_{ij} S_i S_j$"
             r"     $J_{ij} = \rho_{ij}/\sqrt{N}$"
             f"     Window = {CONFIG['CORR_WINDOW']}d     [{date_range}]",
             ha="center", fontsize=10.5, color=THEME["TEXT_DIM"],
             fontfamily=THEME["FONT"])

    # HUD stats  (yellow, bold, top-right)
    hud = (f"Assets = {len(TICKERS)}    "
           f"q_EA peak = {q_ea.max():.4f}    "
           f"β·J peak = {beta_J.max():.3f}    "
           f"RSB windows = {N_rsb}/{N_t}  ({100*N_rsb/N_t:.0f}%)")
    fig.text(0.97, 0.907,
             hud,
             ha="right", fontsize=10, fontweight="bold",
             color=THEME["YELLOW"], fontfamily=THEME["FONT"])

    # Phase legend
    fig.text(0.06, 0.907,
             "■ PARAMAGNETIC  (q=0)",
             color=THEME["CYAN"], fontsize=8.5,
             fontfamily=THEME["FONT"])
    fig.text(0.24, 0.907,
             "■ 1-RSB  (stepped q)",
             color=THEME["MAGENTA"], fontsize=8.5,
             fontfamily=THEME["FONT"])
    fig.text(0.40, 0.907,
             "■ FULL RSB  (curved q)",
             color=THEME["ORANGE"], fontsize=8.5,
             fontfamily=THEME["FONT"])
    fig.text(0.58, 0.907,
             "■ CRISIS  (q → 1)",
             color=THEME["YELLOW"], fontsize=8.5,
             fontfamily=THEME["FONT"])

    # Watermark
    fig.text(0.985, 0.010, THEME["WATERMARK"],
             ha="right", va="bottom", fontsize=10,
             color=THEME["TEXT_DIM"], fontfamily=THEME["FONT"], alpha=0.6)


# ═══════════════════════════════════════════════════════════════════════
# MASTER RENDER — static PNG
# ═══════════════════════════════════════════════════════════════════════

def render_static(data_bundle, engine_bundle, mesh,
                  out_path=CONFIG["STATIC_PNG"]):
    log("Rendering static image 1920×1080 ...")

    fig = plt.figure(figsize=CONFIG["FIG_SIZE"],
                     dpi=CONFIG["DPI"], facecolor=THEME["BG"])

    gs = gridspec.GridSpec(
        4, 2,
        width_ratios=[2.5, 1],
        left=0.06, right=0.97,
        top=0.88, bottom=0.05,
        hspace=0.46, wspace=0.06,
    )
    ax3d = fig.add_subplot(gs[:, 0], projection="3d")
    ax1  = fig.add_subplot(gs[0, 1])
    ax2  = fig.add_subplot(gs[1, 1])
    ax3  = fig.add_subplot(gs[2, 1])
    ax4  = fig.add_subplot(gs[3, 1])

    _draw_3d_surface(ax3d, mesh, engine_bundle)
    _draw_qea_trace(ax1, engine_bundle, data_bundle)
    _draw_beta_J(ax2, engine_bundle)
    _draw_complexity(ax3, engine_bundle)
    _draw_phase_portrait(ax4, engine_bundle)

    _draw_colorbar(fig, mesh)
    _draw_title_block(fig, engine_bundle, data_bundle)

    fig.savefig(out_path, dpi=CONFIG["DPI"],
                facecolor=THEME["BG"], bbox_inches="tight")
    plt.close(fig)
    log(f"Static image saved -> {out_path}")