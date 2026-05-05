"""
╔══════════════════════════════════════════════════════════════════════════╗
║  REPLICA SYMMETRY BREAKING  |  SPIN GLASS ENERGY LANDSCAPE OF MARKETS  ║
║  animate.py  —  MODULE 4: SMOOTH ANIMATED GIF  (120 frames)             ║
║                                                                          ║
║  Three-phase animation  (120 frames @ 10fps = 12 second loop)           ║
║  ─────────────────────────────────────────────────────────────           ║
║  PHASE 1  REVEAL   (frames  0–39, 40 frames)                            ║
║    Surface sweeps in through time left-to-right as the spin glass       ║
║    is "cooled" from paramagnetic → RSB. Camera rises from elev=5        ║
║    to elev=28 with quintic easing so the 3D depth reveals gradually.    ║
║    q_EA ridge draws in live. Parisi breakpoint m*(t) traces in cyan.    ║
║                                                                          ║
║  PHASE 2  HOLD & BREATHE  (frames 40–59, 20 frames)                    ║
║    Full surface visible. Camera gently breathes (±3° sine oscillation). ║
║    HUD shows all live statistics glowing. Stress regime peaks pulse.    ║
║                                                                          ║
║  PHASE 3  ORBIT  (frames 60–119, 60 frames)                            ║
║    Smooth 360° azimuth rotation around the full surface.                ║
║    Elevation rises and falls sinusoidally — viewer sees every angle:    ║
║    the staircase structure from the side, the rugged peaks from above,  ║
║    the floor shadow from below, the complete spin glass landscape.       ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.colors import Normalize
from mpl_toolkits.mplot3d import Axes3D
import imageio
import io
import os
from datetime import datetime

from config import THEME, CMAP_RSB, CMAP_COMPLEXITY, CONFIG, SECTORS, SECTOR_COLORS


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}]  ANIM  |  {msg}")


# ═══════════════════════════════════════════════════════════════════════
# EASING FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════

def _ease_cubic(t):
    """Smooth-step cubic. Zero derivative at both endpoints."""
    return t * t * (3.0 - 2.0 * t)


def _ease_quintic(t):
    """6th-order smooth-step. Even smoother — feels cinematic."""
    return t * t * t * (t * (6.0 * t - 15.0) + 10.0)


def _ease_sine(t):
    """Sine easing — natural, organic feel for camera breathing."""
    return 0.5 * (1.0 - np.cos(np.pi * t))


# ═══════════════════════════════════════════════════════════════════════
# MINI PANEL HELPERS  (right side — static across orbit phase)
# ═══════════════════════════════════════════════════════════════════════

def _style_mini(ax, title=""):
    ax.set_facecolor(THEME["PANEL_BG"])
    for sp in ax.spines.values():
        sp.set_color(THEME["SPINE"]); sp.set_linewidth(0.4)
    ax.tick_params(colors=THEME["TEXT_DIM"], labelsize=7,
                   direction="in", length=2)
    ax.yaxis.grid(True, color=THEME["GRID"], lw=0.25, alpha=0.5)
    ax.xaxis.grid(True, color=THEME["GRID"], lw=0.25, alpha=0.5)
    if title:
        ax.set_title(title, color=THEME["TEXT_DIM"],
                     fontsize=7.5, fontfamily=THEME["FONT"],
                     pad=3, loc="left")


def _draw_mini_qea(ax, engine_bundle, t_cutoff):
    """q_EA trace up to t_cutoff, with stress shading."""
    q_ea  = engine_bundle["q_ea_trace"][:t_cutoff]
    phase = engine_bundle["phase"][:t_cutoff]
    xs    = np.arange(len(q_ea))
    N_t_full = engine_bundle["N_t"]

    in_rsb = False; s0 = 0
    for i in range(len(phase)):
        if phase[i] == 1 and not in_rsb:
            s0 = i; in_rsb = True
        elif phase[i] == 0 and in_rsb:
            ax.axvspan(s0, i, color=THEME["MAGENTA"], alpha=0.10)
            in_rsb = False
    if in_rsb:
        ax.axvspan(s0, len(phase), color=THEME["MAGENTA"], alpha=0.10)

    ax.fill_between(xs, q_ea, alpha=0.18, color=THEME["ORANGE"])
    ax.plot(xs, q_ea, color=THEME["ORANGE"], lw=1.6, zorder=4)
    ax.axhline(0, color=THEME["SPINE"], lw=0.6, ls="--", alpha=0.5)
    ax.set_xlim(0, N_t_full)
    ax.set_ylim(-0.02, engine_bundle["q_ea_trace"].max() * 1.15)
    _style_mini(ax, title=r"$q_{EA}(t)$  ORDER PARAMETER")
    ax.set_xlabel("time", color=THEME["TEXT_DIM"],
                  fontsize=7, fontfamily=THEME["FONT"])


def _draw_mini_beta(ax, engine_bundle, t_cutoff):
    """β·J trace up to t_cutoff."""
    beta_J = engine_bundle["beta_J_trace"][:t_cutoff]
    xs     = np.arange(len(beta_J))
    N_t_full = engine_bundle["N_t"]

    ax.fill_between(xs, beta_J, alpha=0.14, color=THEME["YELLOW"])
    ax.plot(xs, beta_J, color=THEME["YELLOW"], lw=1.6, zorder=4)
    ax.axhline(1.0, color=THEME["CYAN"], lw=1.0, ls="--", alpha=0.80)
    ax.fill_between(xs, beta_J, 1.0,
                    where=beta_J > 1.0,
                    color=THEME["MAGENTA"], alpha=0.12)
    ax.set_xlim(0, N_t_full)
    ax.set_ylim(0, engine_bundle["beta_J_trace"].max() * 1.12)
    _style_mini(ax, title=r"$\beta \cdot J$  (>1 = RSB)")
    ax.set_xlabel("time", color=THEME["TEXT_DIM"],
                  fontsize=7, fontfamily=THEME["FONT"])


# ═══════════════════════════════════════════════════════════════════════
# SINGLE FRAME RENDERER
# ═══════════════════════════════════════════════════════════════════════

def _render_frame(engine_bundle, data_bundle, mesh,
                  azim, elev, t_cutoff,
                  phase_label, global_progress):
    """Render one GIF frame. Returns H×W×4 numpy RGBA array."""

    X, Y, Z  = mesh["X"], mesh["Y"], mesh["Z"]
    N_x, N_t = mesh["N_x"], mesh["N_t"]
    z_min, z_max = mesh["z_min"], mesh["z_max"]
    norm = Normalize(vmin=z_min, vmax=max(z_max, 1e-6))

    fig = plt.figure(figsize=(16.0, 9.0),
                     dpi=CONFIG["GIF_DPI"],
                     facecolor=THEME["BG"])

    gs = gridspec.GridSpec(
        2, 2,
        width_ratios=[2.7, 1],
        left=0.04, right=0.97,
        top=0.87, bottom=0.055,
        hspace=0.42, wspace=0.06,
    )
    ax3d = fig.add_subplot(gs[:, 0], projection="3d")
    ax_q = fig.add_subplot(gs[0, 1])
    ax_b = fig.add_subplot(gs[1, 1])

    tc = max(2, min(t_cutoff, N_t))
    Xs = X[:, :tc]; Ys = Y[:, :tc]; Zs = Z[:, :tc]

    # ── 3-D panes
    pane = (0.02, 0.02, 0.02, 1.0)
    ax3d.xaxis.set_pane_color(pane)
    ax3d.yaxis.set_pane_color(pane)
    ax3d.zaxis.set_pane_color(pane)
    for axis in (ax3d.xaxis, ax3d.yaxis, ax3d.zaxis):
        axis._axinfo["grid"]["color"]     = (0.12, 0.12, 0.12, 0.6)
        axis._axinfo["grid"]["linewidth"] = 0.4
    ax3d.set_facecolor(THEME["BG"])
    ax3d.view_init(elev=elev, azim=azim)
    ax3d.set_box_aspect([1.4, 2.0, 0.80])
    ax3d.tick_params(colors=THEME["TEXT_DIM"], labelsize=6)

    # ── Main surface
    ax3d.plot_surface(
        Xs, Ys, Zs,
        cmap=CMAP_RSB, norm=norm,
        alpha=0.91,
        rstride=1, cstride=1,
        edgecolor=(1.0, 0.08, 0.58, 0.09),
        linewidth=0.20,
        antialiased=True,
        zorder=2,
    )

    # ── Floor shadow
    z_floor = z_min - 0.16 * (z_max - z_min)
    ax3d.contourf(Xs, Ys, Zs,
                  zdir="z", offset=z_floor,
                  cmap=CMAP_RSB, norm=norm,
                  alpha=0.26, levels=14, zorder=1)

    # ── q_EA ridge  (orange glow)
    q_ea = engine_bundle["q_ea_trace"][:tc]
    x_ea = np.ones(tc)
    y_ea = np.arange(tc)
    ax3d.plot(x_ea, y_ea, q_ea,
              color=THEME["ORANGE"], lw=5.0, alpha=0.13,
              solid_capstyle="round", zorder=11)
    ax3d.plot(x_ea, y_ea, q_ea,
              color=THEME["ORANGE"], lw=1.9, alpha=0.95,
              solid_capstyle="round", zorder=12)
    if tc > 1:
        ax3d.scatter([1.0], [tc-1], [q_ea[-1]],
                     s=36, color=THEME["YELLOW"],
                     edgecolors="white", lw=0.6, zorder=16)

    # ── m*(t) Parisi breakpoint  (cyan)
    m_star = engine_bundle["m_star_trace"][:tc]
    z_mstar = np.array([
        float(Z[int(np.clip(m_star[j], 0, 0.999) * (N_x-1)), j])
        for j in range(tc)
    ])
    ax3d.plot(m_star, np.arange(tc), z_mstar,
              color=THEME["CYAN"], lw=2.0, alpha=0.85,
              solid_capstyle="round", zorder=13)

    # ── Axes labels
    ax3d.set_xlabel(r"Parisi  $x$",
                    fontsize=8, color=THEME["TEXT_DIM"],
                    labelpad=6, fontfamily=THEME["FONT"])
    ax3d.set_ylabel("TIME",
                    fontsize=8, color=THEME["TEXT_DIM"],
                    labelpad=6, fontfamily=THEME["FONT"])
    ax3d.set_zlabel(r"$q(x,t)$",
                    fontsize=9, color=THEME["TEXT_DIM"],
                    labelpad=8, fontfamily=THEME["FONT"])
    ax3d.set_xticks([0.0, 0.5, 1.0])
    ax3d.set_xticklabels(["0", "½", "1"],
                          fontsize=6.5, color=THEME["TEXT_DIM"])

    # ── HUD text overlays
    q_live    = q_ea[-1] if len(q_ea) else 0.0
    bj_live   = engine_bundle["beta_J_trace"][tc-1] if tc > 0 else 0.0
    comp_live = engine_bundle["complexity"][tc-1]    if tc > 0 else 0.0

    # Phase label — top-left
    phase_col = {
        "REVEAL":  THEME["CYAN"],
        "HOLD":    THEME["GREEN"],
        "ORBIT":   THEME["PURPLE"],
    }.get(phase_label.split()[0], THEME["ORANGE"])

    ax3d.text2D(0.02, 0.97,
                phase_label,
                transform=ax3d.transAxes,
                fontsize=10, color=phase_col,
                fontfamily=THEME["FONT"], fontweight="bold", va="top")

    ax3d.text2D(0.02, 0.90,
                f"q_EA = {q_live:.4f}    β·J = {bj_live:.3f}",
                transform=ax3d.transAxes,
                fontsize=8, color=THEME["YELLOW"],
                fontfamily=THEME["FONT"], va="top")

    phase_str = "RSB  (rugged)" if bj_live > 1.0 else "PARAMAGNETIC"
    phase_col2 = THEME["MAGENTA"] if bj_live > 1.0 else THEME["CYAN"]
    ax3d.text2D(0.98, 0.97,
                f"Phase: {phase_str}    Complexity Σ = {comp_live:.4f}",
                transform=ax3d.transAxes,
                fontsize=8, color=phase_col2,
                fontfamily=THEME["FONT"], ha="right", va="top")

    # ── Right panels
    _draw_mini_qea(ax_q, engine_bundle, tc)
    _draw_mini_beta(ax_b, engine_bundle, tc)

    # ── Title block
    fig.text(0.50, 0.950,
             "REPLICA SYMMETRY BREAKING  |  SPIN GLASS LANDSCAPE OF MARKETS",
             ha="center", fontsize=14, fontweight="bold",
             color=THEME["ORANGE"], fontfamily=THEME["FONT"])
    fig.text(0.50, 0.924,
             r"$q(x,t)$ = Parisi order parameter     "
             r"$H = -\sum_{i<j} J_{ij} S_i S_j$     "
             r"$J_{ij} = \rho_{ij}/\sqrt{N}$",
             ha="center", fontsize=9,
             color=THEME["TEXT_DIM"], fontfamily=THEME["FONT"])

    # ── Global progress bar with labelled phase markers
    bar = fig.add_axes([0.04, 0.018, 0.93, 0.012])
    bar.set_facecolor(THEME["PANEL_BG"])
    bar.set_xlim(0, 1); bar.set_ylim(0, 1)
    bar.set_xticks([]); bar.set_yticks([])
    for sp in bar.spines.values():
        sp.set_color(THEME["SPINE"]); sp.set_linewidth(0.3)

    bar.barh(0.5, 1.0, height=0.9,
             color=THEME["GRID"], left=0, align="center")
    bar.barh(0.5, global_progress, height=0.9,
             color=THEME["PURPLE"], left=0, align="center", alpha=0.75)

    # Phase markers on bar
    for frac, lbl, col in [
        (0.00, "START",  THEME["TEXT_DIM"]),
        (0.33, "FULL",   THEME["CYAN"]),
        (0.50, "HOLD",   THEME["GREEN"]),
        (1.00, "END",    THEME["TEXT_DIM"]),
    ]:
        bar.axvline(frac, color=col, lw=0.9, alpha=0.7)
        bar.text(frac, -0.7, lbl, ha="center", va="top",
                 fontsize=5.5, color=col,
                 fontfamily=THEME["FONT"])

    # Watermark
    fig.text(0.985, 0.048, THEME["WATERMARK"],
             ha="right", va="bottom", fontsize=8,
             color=THEME["TEXT_DIM"], fontfamily=THEME["FONT"], alpha=0.6)

    # ── Capture to numpy array
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=CONFIG["GIF_DPI"],
                facecolor=THEME["BG"])
    plt.close(fig)
    buf.seek(0)
    return np.array(imageio.v3.imread(buf))


# ═══════════════════════════════════════════════════════════════════════
# ANIMATION SCHEDULE BUILDER
# ═══════════════════════════════════════════════════════════════════════

def _build_schedule(N_t,
                    reveal_frames=40,
                    hold_frames=20,
                    orbit_frames=60):
    """
    Build the full per-frame parameter list.

    Phase 1 REVEAL : surface sweeps in, camera rises
    Phase 2 HOLD   : full surface, gentle breathing
    Phase 3 ORBIT  : smooth 360° rotation
    """
    total    = reveal_frames + hold_frames + orbit_frames
    schedule = []

    # ── PHASE 1: REVEAL (quintic easing for surface, sine for camera)
    for i in range(reveal_frames):
        raw      = i / (reveal_frames - 1)
        eased    = _ease_quintic(raw)
        tc       = max(2, int(eased * N_t))
        elev     = 5.0  + 23.0 * _ease_sine(raw)    # 5° → 28°
        azim     = -55.0 + 10.0 * raw                # gentle drift
        schedule.append(dict(
            phase="REVEAL",
            t_cutoff=tc, azim=azim, elev=elev,
            global_progress=i / (total - 1),
        ))

    # ── PHASE 2: HOLD (camera breathes on a sine wave)
    for i in range(hold_frames):
        raw  = i / max(hold_frames - 1, 1)
        azim = -45.0 + 5.0 * np.sin(2.0 * np.pi * raw)
        elev = 28.0  + 3.0 * np.sin(np.pi * raw)
        schedule.append(dict(
            phase="HOLD  (full RSB landscape)",
            t_cutoff=N_t, azim=azim, elev=elev,
            global_progress=(reveal_frames + i) / (total - 1),
        ))

    # ── PHASE 3: ORBIT (full 360° smooth rotation)
    for i in range(orbit_frames):
        raw  = i / max(orbit_frames - 1, 1)
        azim = -45.0 + 360.0 * raw
        elev = 28.0  + 18.0 * np.sin(np.pi * raw * 1.5)
        elev = np.clip(elev, 5.0, 60.0)
        schedule.append(dict(
            phase=f"ORBIT  {(azim % 360):.0f}°",
            t_cutoff=N_t, azim=azim, elev=elev,
            global_progress=(reveal_frames + hold_frames + i) / (total - 1),
        ))

    return schedule


# ═══════════════════════════════════════════════════════════════════════
# MASTER RENDER
# ═══════════════════════════════════════════════════════════════════════

def render_animation(data_bundle, engine_bundle, mesh,
                     out_path=CONFIG["ANIM_GIF"],
                     reveal_frames=40,
                     hold_frames=20,
                     orbit_frames=60):
    """
    Render the full smooth RSB spin glass animation.

    Default: 40 + 20 + 60 = 120 frames @ 10 fps = 12 second loop.
    """
    N_t      = mesh["N_t"]
    schedule = _build_schedule(N_t, reveal_frames, hold_frames, orbit_frames)
    total    = len(schedule)

    log(f"Schedule: {total} frames  "
        f"(reveal={reveal_frames}, hold={hold_frames}, orbit={orbit_frames})")

    frames = []

    for fi, entry in enumerate(schedule):
        if fi % 6 == 0:
            log(f"  Frame {fi+1:3d}/{total}  "
                f"[{entry['phase']}  "
                f"azim={entry['azim']:.1f}°  elev={entry['elev']:.1f}°  "
                f"t={entry['t_cutoff']}/{N_t}]")

        frame = _render_frame(
            engine_bundle   = engine_bundle,
            data_bundle     = data_bundle,
            mesh            = mesh,
            azim            = entry["azim"],
            elev            = entry["elev"],
            t_cutoff        = entry["t_cutoff"],
            phase_label     = entry["phase"],
            global_progress = entry["global_progress"],
        )
        frames.append(frame)

    log(f"Writing GIF  [{total} frames @ {CONFIG['GIF_FPS']} fps] ...")
    imageio.mimsave(
        out_path, frames,
        format="GIF",
        duration=1.0 / CONFIG["GIF_FPS"],
        loop=0,
    )
    mb = os.path.getsize(out_path) / 1e6
    log(f"GIF saved -> {out_path}  ({mb:.1f} MB,  {total} frames)")