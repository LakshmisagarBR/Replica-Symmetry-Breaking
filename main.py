"""
╔══════════════════════════════════════════════════════════════════════════╗
║  REPLICA SYMMETRY BREAKING  |  SPIN GLASS ENERGY LANDSCAPE OF MARKETS  ║
║  main.py  —  MASTER PIPELINE ORCHESTRATOR                                ║
║                                                                          ║
║  Run:   python main.py                                                   ║
║                                                                          ║
║  Outputs                                                                 ║
║  ───────                                                                 ║
║  outputs/rsb_spin_glass.png   — 1920×1080 static Bloomberg Dark image   ║
║  outputs/rsb_animation.gif    — 120-frame smooth animated GIF            ║
║                                                                          ║
║  Pipeline                                                                ║
║  ────────                                                                ║
║  MODULE 1  data.py    → calibrated synthetic S&P 500 returns (GARCH)    ║
║  MODULE 2  engine.py  → SK spin glass + Parisi RSB surface q(x,t)       ║
║  MODULE 3  visual.py  → static 1920×1080 PNG (4-panel dashboard)        ║
║  MODULE 4  animate.py → 120-frame GIF (reveal → hold → 360° orbit)      ║
║                                                                          ║
║  Switch to real yfinance data:                                           ║
║  Replace fetch_all() in data.py with the yfinance implementation.        ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import time
from datetime import datetime

from config  import CONFIG
from data    import fetch_all
from engine  import compute_rsb_surface, build_surface_mesh
from visual  import render_static
from animate import render_animation


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}]  MAIN  |  {msg}")


def banner(text):
    line = "═" * 72
    print(f"\n{line}\n  {text}\n{line}\n")


def main():
    t0 = time.time()

    banner("MODULE 1  ──  DATA  (calibrated GARCH | 30 S&P 500 stocks | 2Y)")
    data_bundle = fetch_all()

    banner("MODULE 2  ──  ENGINE  (SK spin glass | Parisi RSB order parameter)")
    engine_bundle = compute_rsb_surface(data_bundle)
    mesh          = build_surface_mesh(engine_bundle)

    banner("MODULE 3  ──  VISUAL  (static 1920×1080 PNG)")
    render_static(data_bundle, engine_bundle, mesh,
                  out_path=CONFIG["STATIC_PNG"])

    banner("MODULE 4  ──  ANIMATION  (120-frame smooth GIF)")
    render_animation(
        data_bundle, engine_bundle, mesh,
        out_path=CONFIG["ANIM_GIF"],
        reveal_frames=40,
        hold_frames=20,
        orbit_frames=60,
    )

    elapsed = time.time() - t0
    banner(f"DONE  ──  total time = {elapsed/60:.1f} min")
    log(f"Static  ->  {CONFIG['STATIC_PNG']}")
    log(f"GIF     ->  {CONFIG['ANIM_GIF']}")


if __name__ == "__main__":
    main()