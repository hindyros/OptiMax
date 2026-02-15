"""
OptiMATE backend architecture diagram.
Landscape 16:9 – large text filling boxes, straight arrows.
"""

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

C = {
    "bg":           "#FFFFFF",
    "input":        "#E8F4FD",  "input_edge":   "#5BA4CF",
    "preprocess":   "#FFF3E0",  "preprocess_e": "#F5A623",
    "optimus":      "#E8F5E9",  "optimus_e":    "#4CAF50",
    "optimind":     "#F3E5F5",  "optimind_e":   "#9C27B0",
    "judge":        "#FFF8E1",  "judge_e":      "#FF9800",
    "report":       "#FFEBEE",  "report_e":     "#E53935",
    "llm":          "#F5F5F5",  "llm_edge":     "#9E9E9E",
    "arrow":        "#37474F",  "text":         "#212121",
    "subtext":      "#616161",
    "step":         "#C8E6C9",  "step_e":       "#66BB6A",
    "debug":        "#FFCCBC",  "debug_e":      "#FF7043",
}

# Tight coordinate space → everything is large
FIG_W, FIG_H = 32, 18
W, H = 16, 9
fig, ax = plt.subplots(1, 1, figsize=(FIG_W, FIG_H), facecolor=C["bg"])
ax.set_xlim(0, W)
ax.set_ylim(0, H)
ax.set_aspect("equal")
ax.axis("off")
fig.subplots_adjust(left=0.003, right=0.997, top=0.997, bottom=0.003)


# ── Helpers ─────────────────────────────────────────────────────
def box(x, y, w, h, fill, edge, label, sub=None,
        fs=18, sfs=13, lw=2.2, r=0.12, zo=2, bold=True):
    p = FancyBboxPatch((x, y), w, h,
                       boxstyle=f"round,pad=0,rounding_size={r}",
                       facecolor=fill, edgecolor=edge, linewidth=lw, zorder=zo)
    ax.add_patch(p)
    cy = y + h / 2 if sub is None else y + h / 2 + 0.1
    ax.text(x + w / 2, cy, label, ha="center", va="center",
            fontsize=fs, fontweight="bold" if bold else "normal",
            color=C["text"], zorder=zo + 1)
    if sub:
        ax.text(x + w / 2, y + h / 2 - 0.13, sub, ha="center", va="center",
                fontsize=sfs, color=C["subtext"], zorder=zo + 1, style="italic")


def arr(x1, y1, x2, y2, color=C["arrow"], lw=2.2, sty="-|>",
        ls="-", zo=1):
    ax.add_patch(FancyArrowPatch(
        (x1, y1), (x2, y2), arrowstyle=sty, color=color, linewidth=lw,
        connectionstyle="arc3,rad=0", zorder=zo, linestyle=ls, mutation_scale=20))


def elbow_h(x1, y1, x2, y2, color=C["arrow"], lw=2.2, zo=1):
    ax.plot([x1, x2], [y1, y1], color=color, lw=lw, zorder=zo, solid_capstyle="round")
    arr(x2, y1, x2, y2, color=color, lw=lw, zo=zo)


def reg(x, y, w, h, fill, edge, label, fs=16, lw=2.0, alpha=0.22):
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0,rounding_size=0.18",
        facecolor=fill, edgecolor=edge, linewidth=lw, zorder=0, alpha=alpha))
    ax.text(x + 0.12, y + h - 0.17, label, ha="left", va="top",
            fontsize=fs, fontweight="bold", color=edge, zorder=1, alpha=0.95)


def tag(x, y, label, fs=13, w=1.1):
    box(x, y, w, 0.25, C["llm"], C["llm_edge"], label,
        fs=fs, lw=1.0, r=0.08, bold=False)


# ═══════════════════════════════════════════════════════════════
#  TITLE
# ═══════════════════════════════════════════════════════════════
ax.text(W / 2, H - 0.18, "OptiMATE  —  System Architecture",
        ha="center", va="center", fontsize=36, fontweight="bold", color=C["text"])
ax.text(W / 2, H - 0.5, "Dual-solver optimization pipeline with LLM-driven formulation, execution, and reporting",
        ha="center", va="center", fontsize=16, color=C["subtext"], style="italic")

# ═══════════════════════════════════════════════════════════════
#  COL 1 — INPUT + PREPROCESS  (x 0.1 – 2.6)
# ═══════════════════════════════════════════════════════════════
reg(0.1, 0.45, 2.5, 7.9, C["input"], C["input_edge"], "① User Input")

box(0.25, 7.3, 2.2, 0.6, C["input"], C["input_edge"],
    "Problem Description", "desc.txt", fs=14, sfs=11)
box(0.25, 6.45, 2.2, 0.6, C["input"], C["input_edge"],
    "Data Files", ".csv (optional)", fs=14, sfs=11)
arr(1.35, 6.45, 1.35, 6.15, color=C["input_edge"])
box(0.25, 5.65, 2.2, 0.5, "#E3F2FD", "#90CAF9",
    "data_upload/", fs=14, bold=False, lw=1.4)
arr(1.35, 7.3, 1.35, 6.15, color=C["input_edge"])
arr(1.35, 5.65, 1.35, 5.4, color=C["input_edge"])
box(0.25, 4.85, 2.2, 0.55, "#E3F2FD", "#90CAF9",
    "raw_input/", fs=14, bold=False, lw=1.4)

# Pre-processing divider
ax.plot([0.2, 2.5], [4.6, 4.6], color=C["preprocess_e"],
        lw=1.2, ls="--", alpha=0.5, zorder=1)
ax.text(1.35, 4.4, "② Pre-Processing", ha="center", va="center",
        fontsize=13, fontweight="bold", color=C["preprocess_e"])

box(0.25, 3.6, 2.2, 0.5, C["preprocess"], C["preprocess_e"],
    "CSV Column Mapping", fs=13, lw=1.5)
box(0.25, 2.9, 2.2, 0.5, C["preprocess"], C["preprocess_e"],
    "Supplement Extract", fs=13, lw=1.5)
box(0.25, 2.2, 2.2, 0.5, C["preprocess"], C["preprocess_e"],
    "Merge & Validate", fs=13, lw=1.5)

arr(1.35, 3.6, 1.35, 3.4, color=C["preprocess_e"])
arr(1.35, 2.9, 1.35, 2.7, color=C["preprocess_e"])
arr(1.35, 4.85, 1.35, 4.65, color=C["preprocess_e"])

box(0.25, 1.6, 2.2, 0.38, "#FFF8E1", "#FFB74D",
    "Text-Only Fallback", fs=12, bold=False, lw=1.0)
arr(1.35, 2.2, 1.35, 1.98, color="#FFB74D", ls="--", lw=1.2)

tag(0.45, 1.15, "Claude Opus 4")

box(0.25, 0.5, 2.2, 0.55, "#FFF3E0", C["preprocess_e"],
    "model_input/", fs=16)
arr(1.35, 1.6, 1.35, 1.05, color=C["preprocess_e"])

# ═══════════════════════════════════════════════════════════════
#  COL 2 — DUAL SOLVERS  (x 2.9 – 9.6)
# ═══════════════════════════════════════════════════════════════
MID = 2.8
arr(2.45, 0.78, MID, 0.78, color=C["arrow"], lw=2.8, sty="-")
ax.plot([MID, MID], [0.78, 5.2], color=C["arrow"], lw=2.8, zorder=1,
        solid_capstyle="round")
arr(MID, 5.2, 3.1, 5.2, color=C["optimus_e"], lw=2.8)
arr(MID, 0.78, 3.1, 0.78, color=C["optimind_e"], lw=2.8)

ax.text(MID, 3.0, "Parallel\nExecution", ha="center", va="center",
        fontsize=13, fontweight="bold", color=C["arrow"], rotation=90,
        bbox=dict(boxstyle="round,pad=0.1", facecolor="white",
                  edgecolor="none", alpha=0.9))

# ─── OptiMUS (top) ─────────────────────────────────────────────
reg(2.95, 4.05, 6.65, 4.2, C["optimus"], C["optimus_e"],
    "③a  OptiMUS — Multi-Step Pipeline", fs=15)

# Row 1: Steps 1, 2-3, 4-5
r1 = [("1", "Parameter\nExtraction"),
      ("2–3", "Objective &\nConstraints"),
      ("4–5", "Math.\nFormulation")]
for i, (n, lab) in enumerate(r1):
    x = 3.15 + i * 2.1
    box(x, 6.85, 0.7, 0.65, C["step"], C["step_e"], n, fs=16, lw=1.5)
    box(x + 0.8, 6.85, 1.2, 0.65, C["optimus"], C["optimus_e"], lab, fs=12, lw=1.5)
    if i > 0:
        arr(x - 0.1, 7.18, x, 7.18, color=C["optimus_e"], lw=1.5)

ax.text(3.3, 7.6, "∥", fontsize=14, color=C["optimus_e"], fontweight="bold")

# Row 2: Steps 6-7, 8
r2 = [("6–7", "Code Gen\n& Assembly"),
      ("8", "Execute &\nDebug")]
for i, (n, lab) in enumerate(r2):
    x = 3.15 + i * 2.1
    box(x, 5.85, 0.7, 0.65, C["step"], C["step_e"], n, fs=16, lw=1.5)
    box(x + 0.8, 5.85, 1.2, 0.65, C["optimus"], C["optimus_e"], lab, fs=12, lw=1.5)
    if i > 0:
        arr(x - 0.1, 6.18, x, 6.18, color=C["optimus_e"], lw=1.5)

# Wrap arrow
ax.plot([9.25, 9.4], [7.18, 7.18], color=C["optimus_e"], lw=1.5, zorder=1)
ax.plot([9.4, 9.4], [7.18, 6.18], color=C["optimus_e"], lw=1.5, zorder=1)
arr(9.4, 6.18, 5.35, 6.18, color=C["optimus_e"], lw=1.5)

# Debug + LLM
box(3.15, 5.0, 3.5, 0.4, C["debug"], C["debug_e"],
    "LLM Debug ×3 retries", fs=13, bold=False, lw=1.2)
arr(4.9, 5.85, 4.9, 5.4, color=C["debug_e"], lw=1.4)
tag(6.9, 5.02, "Claude Sonnet 4", fs=12)

ax.text(8.6, 5.18, "state_1…6.json · code.py",
        ha="center", va="center", fontsize=10, color=C["subtext"], style="italic")

# Output
box(3.15, 4.25, 6.2, 0.45, C["optimus"], C["optimus_e"],
    "optimus_output/ → output_solution.txt · code.py",
    fs=13, bold=False, lw=1.5)
arr(4.9, 5.0, 4.9, 4.7, color=C["optimus_e"])

# ─── OptiMind (bottom) ─────────────────────────────────────────
reg(2.95, 0.1, 6.65, 3.7, C["optimind"], C["optimind_e"],
    "③b  OptiMind — Single-Pass Solver", fs=15)

mind = [("Read", "Build\nproblem"),
        ("Query", "OptiMind\n-SFT"),
        ("Extract", "Parse\ncode"),
        ("Patch", "Add\noutput"),
        ("Execute", "Run &\nDebug ×5")]
for i, (n, lab) in enumerate(mind):
    x = 3.1 + i * 1.26
    box(x, 2.65, 1.16, 0.4, "#E1BEE7", C["optimind_e"], n, fs=13, bold=True, lw=1.4)
    box(x, 1.95, 1.16, 0.6, C["optimind"], C["optimind_e"], lab, fs=12, lw=1.4)
    if i > 0:
        arr(x - 0.1, 2.85, x, 2.85, color=C["optimind_e"], lw=1.4)

# Debug + LLM
box(3.1, 1.15, 3.2, 0.4, C["debug"], C["debug_e"],
    "LLM Debug ×5 retries", fs=13, bold=False, lw=1.2)
arr(4.7, 1.95, 4.7, 1.55, color=C["debug_e"], lw=1.4)
tag(6.5, 1.17, "OptiMind-SFT", fs=12)
tag(7.75, 1.17, "Claude Haiku", fs=12, w=1.05)

ax.text(8.5, 0.88, "optimind_code.py",
        ha="center", va="center", fontsize=10, color=C["subtext"], style="italic")

# Output
box(3.1, 0.3, 6.25, 0.45, C["optimind"], C["optimind_e"],
    "optimind_output/ → output_solution.txt · optimind_code.py",
    fs=13, bold=False, lw=1.5)
arr(4.7, 1.15, 4.7, 0.75, color=C["optimind_e"])

# ═══════════════════════════════════════════════════════════════
#  COL 3 — JUDGE + REPORT + OUTPUT  (x 9.8 – 15.9)
# ═══════════════════════════════════════════════════════════════

# Solver outputs → Judge
JX = 9.75
elbow_h(9.35, 4.48, JX, 6.95, color=C["judge_e"], lw=2.4)
arr(JX, 6.95, 10.0, 6.95, color=C["judge_e"], lw=2.4)
elbow_h(9.35, 0.53, JX, 6.4, color=C["judge_e"], lw=2.4)
arr(JX, 6.4, 10.0, 6.4, color=C["judge_e"], lw=2.4)

# ── Judge ──
reg(9.85, 5.4, 6.0, 2.85, C["judge"], C["judge_e"],
    "④ Judge — judge.py", fs=15)

box(10.05, 6.55, 1.75, 1.15, C["judge"], C["judge_e"],
    "Status\nClassification",
    "optimal · feasible\ninfeasible · error",
    fs=14, sfs=10)

box(12.1, 6.55, 1.75, 1.15, C["judge"], C["judge_e"],
    "Programmatic\nFast-Path",
    "Clear winner?\n→ skip LLM", fs=14, sfs=10.5)

box(14.15, 6.55, 1.5, 1.15, C["judge"], C["judge_e"],
    "LLM\nComparison",
    "Formulation\n& Fidelity", fs=14, sfs=10)

arr(11.8, 7.12, 12.1, 7.12, color=C["judge_e"])
arr(13.85, 7.12, 14.15, 7.12, color=C["judge_e"])
tag(14.3, 6.6, "GPT-4o", w=0.85, fs=12)

# Verdict
box(11.0, 5.65, 3.8, 0.55, "#FFF8E1", C["judge_e"],
    "verdict.json", "winner · objective · reasoning",
    fs=16, sfs=11, lw=2.0)
arr(12.9, 6.55, 12.9, 6.2, color=C["judge_e"], lw=2.0)

# ── Consultant ──
reg(9.85, 2.45, 6.0, 2.7, C["report"], C["report_e"],
    "⑤ Consultant Report — consultant.py", fs=15)

arr(12.9, 5.65, 12.9, 5.15, color=C["report_e"], lw=2.8)

secs = ["Problem\nStatement", "Executive\nSummary", "Baseline\nCompar.",
        "Key\nRecomm.", "Technical\nAppendix"]
for i, s in enumerate(secs):
    sx = 10.05 + i * 1.15
    box(sx, 3.95, 1.05, 0.65, "#FFCDD2", C["report_e"], s, fs=10.5, lw=1.3, r=0.08)

# Sub-steps
box(10.05, 2.85, 2.0, 0.55, C["report"], C["report_e"],
    "Context Loading", fs=13, lw=1.3)
box(12.35, 2.85, 1.55, 0.55, C["report"], C["report_e"],
    "Gurobi Stats", fs=13, lw=1.3)
box(14.2, 2.85, 1.45, 0.55, C["report"], C["report_e"],
    "Prompt Build", fs=13, lw=1.3)

arr(12.05, 3.12, 12.35, 3.12, color=C["report_e"])
arr(13.9, 3.12, 14.2, 3.12, color=C["report_e"])
tag(14.45, 2.62, "Claude Opus 4", fs=12)

arr(12.9, 3.95, 12.9, 3.4, color=C["report_e"], lw=1.3)

# ── Final Output ──
box(10.05, 0.45, 5.6, 1.65, "#FFEBEE", C["report_e"],
    "final_output/", fs=24, lw=3.5, r=0.2)
ax.text(12.85, 0.82, "report.md  ·  verdict.json  ·  executive_summary",
        ha="center", va="center", fontsize=13, color=C["subtext"])

arr(12.9, 2.45, 12.9, 2.1, color=C["report_e"], lw=3.2)

# Archive
box(10.05, 0.05, 2.4, 0.32, "#ECEFF1", "#78909C",
    "query_history/", fs=12, lw=1.3, bold=False)
arr(11.25, 0.45, 11.25, 0.37, color="#78909C", lw=1.2, ls="--")

# ═══════════════════════════════════════════════════════════════
#  LEGEND
# ═══════════════════════════════════════════════════════════════
items = [
    (C["input"], C["input_edge"], "Input"),
    (C["preprocess"], C["preprocess_e"], "Pre-Process"),
    (C["optimus"], C["optimus_e"], "OptiMUS"),
    (C["optimind"], C["optimind_e"], "OptiMind"),
    (C["judge"], C["judge_e"], "Judge"),
    (C["report"], C["report_e"], "Report"),
    (C["llm"], C["llm_edge"], "LLM Tag"),
]
for i, (f, e, lab) in enumerate(items):
    lx = 12.7 + (i % 4) * 0.9
    ly = 0.22 if i < 4 else 0.0
    box(lx, ly, 0.2, 0.18, f, e, "", fs=1, lw=1.2, r=0.04)
    ax.text(lx + 0.27, ly + 0.09, lab, fontsize=11, va="center", color=C["text"])

# ── Save ────────────────────────────────────────────────────────
out = "/Users/hindy/Desktop/OptiMUS/backend/architecture_diagram.png"
fig.savefig(out, dpi=200, bbox_inches="tight", facecolor=C["bg"], pad_inches=0.2)
plt.close()
print(f"Saved → {out}")
