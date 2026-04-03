#!/usr/bin/env python3
"""
Benchmark: Maximum Odd Binary Number
Profiles solutions across array languages and C++.
Generates a horizontal bar chart with language logos.
"""

import subprocess
import tempfile
import shutil
import statistics
import os
import sys
import re
import time
from pathlib import Path

# ─────────────────────────── Configuration ──────────────────────

N_ITERS     = 50
N_RUNS      = 5
INPUT_LEN   = 1_000
INPUT_SIZES = [100, 1_000, 10_000, 100_000]

ROOT       = Path(__file__).parent
BUILD_DIR  = ROOT / "build"
LOGOS_DIR  = ROOT / "logos"
OUTPUT_PNG = ROOT / "benchmark_results.png"


# ─────────────────────────── Helpers ────────────────────────────

def find_cmd(*names):
    for n in names:
        p = shutil.which(n)
        if p:
            return p
    return None


def parse_number(text):
    """Extract the last float from text, handling BQN ¯, J _, and TinyAPL ⏨."""
    if not text:
        return None
    text = text.replace("\u00af", "-")   # BQN high minus
    text = text.replace("\u2a28", "e")   # TinyAPL ⏨ scientific notation
    text = text.replace("\u23e8", "e")   # TinyAPL ⏨ (alternate codepoint)
    for line in reversed(text.strip().splitlines()):
        cleaned = line.strip().replace("_", "-")
        m = re.search(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", cleaned)
        if m:
            try:
                return float(m.group())
            except ValueError:
                continue
    return None


def run_cmd(cmd, *, input_text=None, env=None, timeout=120):
    try:
        r = subprocess.run(
            cmd, capture_output=True, text=True,
            input=input_text, env=env, timeout=timeout,
        )
        return r.stdout, r.stderr, r.returncode
    except subprocess.TimeoutExpired:
        return "", "timeout", -1
    except Exception as e:
        return "", str(e), -1


def write_temp(suffix, content):
    fd, path = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, "w") as f:
        f.write(content)
    return path


# ─────────────────────────── Benchmark: BQN ─────────────────────

def bench_bqn():
    interp = find_cmd("cbqn", "bqn")
    if not interp:
        return None
    script = f'\u2022Out \u2022Fmt {N_ITERS}(1\u233d\u2228)\u2022_timed {INPUT_LEN}\u294a"01"'
    out, _, rc = run_cmd([interp, "-e", script])
    return parse_number(out) if rc == 0 else None


# ─────────────────────────── Benchmark: Uiua ────────────────────

def bench_uiua():
    interp = find_cmd("uiua")
    if not interp:
        return None
    code = (
        f'S \u2190 \u21af{INPUT_LEN} "01"\n'
        f"T \u2190 now\n"
        f"\u2365(\u25cc\u21bb1\u21cc\u2346 S){N_ITERS}\n"
        f"&p \u00f7{N_ITERS} -T now\n"
    )
    path = write_temp(".ua", code)
    try:
        out, err, rc = run_cmd([interp, "run", path])
        return parse_number(out) if rc == 0 else None
    finally:
        os.unlink(path)


# ─────────────────────────── Benchmark: J ───────────────────────

def bench_j():
    interp = find_cmd("jconsole", "ijconsole")
    if not interp:
        return None
    code = (
        f"input =: {INPUT_LEN} $ '01'\n"
        f"n =: {N_ITERS}\n"
        "bench =: 3 : '1 |. \\:~ input'\n"
        "echo (6!:2 'bench\"0 i. n') % n\n"
        "exit ''\n"
    )
    path = write_temp(".ijs", code)
    try:
        out, _, rc = run_cmd([interp, path])
        return parse_number(out) if rc == 0 else None
    finally:
        os.unlink(path)


# ─────────────────────────── Benchmark: Dyalog APL ──────────────

def bench_apl():
    interp = find_cmd("dyalog")
    if not interp:
        return None
    code = (
        f"input\u2190{INPUT_LEN}\u2374'01'\n"
        f"n\u2190{N_ITERS}\n"
        "t\u21902\u2283\u2395AI\n"
        "_\u2190{(1\u233d\u2282\u2364\u2352\u235b\u2337)input}\u00a8\u2373n\n"
        "\u2395\u2190'RESULT ',(\u2355((2\u2283\u2395AI)-t)\u00f71000\u00d7n)\n"
        "\u2395OFF\n"
    )
    env = os.environ.copy()
    env["RIDE_INIT"] = "SERVE::0"
    out, _, _ = run_cmd([interp], input_text=code, env=env)
    if not out:
        return None
    for line in out.splitlines():
        if "RESULT" in line:
            return parse_number(line.split("RESULT")[-1])
    return None


# ─────────────────────────── Benchmark: TinyAPL ─────────────────

def bench_tinyapl(solution_code):
    """TinyAPL: uses ⎕_Measure for native timing (returns seconds)."""
    interp = find_cmd("tinyapl")
    if not interp:
        return None
    code = (
        f"\u2395\u2190({solution_code}) \u2395_Measure {INPUT_LEN}\u2374'01'\n"
    )
    path = write_temp(".apl", code)
    try:
        out, err, rc = run_cmd([interp, path])
        combined = (out or "") + (err or "")
        if "error" in combined.lower():
            return None
        return parse_number(out)
    finally:
        os.unlink(path)


# ─────────────────────────── Benchmark: Kap ─────────────────────

def bench_kap():
    """Kap: uses time:measureTime for native timing."""
    kap_path = Path.home() / "Downloads/kap/gui/bin/kap-jvm"
    if not kap_path.exists():
        return None
    expr = (
        f"input \u2190 {INPUT_LEN}\u2374\"01\" \u25ca "
        f"time:measureTime {{ {{ 1\u233d\u2228 input }} \u00a8 \u2373{N_ITERS} }}"
    )
    out, err, rc = run_cmd([str(kap_path), "-n", "-E", expr], timeout=30)
    if rc != 0:
        return None
    for line in (out or "").splitlines():
        if "Total time:" in line:
            m = re.search(r"Total time:\s*([\d.]+)", line)
            if m:
                return float(m.group(1)) / N_ITERS
    return None


# ─────────────────────────── Benchmark: C++ ─────────────────────

_cpp_bin_cache = {}


def bench_cpp(name, func_body):
    compiler = find_cmd("g++")
    if not compiler:
        return None

    if name not in _cpp_bin_cache:
        BUILD_DIR.mkdir(exist_ok=True)
        src = (
            "#include <algorithm>\n"
            "#include <chrono>\n"
            "#include <iostream>\n"
            "#include <string>\n\n"
            "auto maximum_odd_binary(std::string s) -> std::string {\n"
            f"  {func_body}\n"
            "  return s;\n"
            "}\n\n"
            "int main() {\n"
            "  std::string input;\n"
            f"  for (int i = 0; i < {INPUT_LEN // 2}; ++i) input += \"01\";\n"
            f"  constexpr int n = {N_ITERS};\n"
            "  std::string result;\n"
            "  auto start = std::chrono::high_resolution_clock::now();\n"
            "  for (int i = 0; i < n; ++i)\n"
            "    result = maximum_odd_binary(input);\n"
            "  auto end = std::chrono::high_resolution_clock::now();\n"
            "  std::cout << std::chrono::duration<double>(end - start).count() / n\n"
            "            << '\\n';\n"
            "  if (result.empty()) return 1;\n"
            "}\n"
        )
        src_path = BUILD_DIR / f"bench_{name}.cpp"
        bin_path = BUILD_DIR / f"bench_{name}"
        src_path.write_text(src)

        for std_flag in ["-std=c++23", "-std=c++20"]:
            _, cerr, crc = run_cmd(
                [compiler, std_flag, "-O2",
                 "-o", str(bin_path), str(src_path)]
            )
            if crc == 0:
                break
        else:
            _cpp_bin_cache[name] = None
            return None
        _cpp_bin_cache[name] = str(bin_path)

    bin_path = _cpp_bin_cache[name]
    if bin_path is None:
        return None
    out, _, rc = run_cmd([bin_path])
    return parse_number(out) if rc == 0 else None


# ─────────────────────────── Logo: C++ ──────────────────────────

def _make_cpp_logo():
    cpp_logo = LOGOS_DIR / "cpp.png"
    if cpp_logo.exists():
        return
    try:
        from PIL import Image, ImageDraw, ImageFont

        size = 128
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle(
            [4, 4, size - 4, size - 4],
            radius=20, fill="#659ad2", outline="#ffffff", width=3,
        )
        try:
            font = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 44
            )
        except Exception:
            font = ImageFont.load_default()
        draw.text(
            (size // 2, size // 2), "C++",
            fill="white", font=font, anchor="mm",
        )
        img.save(str(cpp_logo))
    except Exception:
        pass


# ─────────────────────────── Chart ──────────────────────────────

def generate_chart(results, output_path=OUTPUT_PNG):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.image as mpimg
    from matplotlib.offsetbox import OffsetImage, AnnotationBbox
    from matplotlib.font_manager import FontProperties
    import numpy as np

    _make_cpp_logo()

    BQN_FONT = Path.home() / ".local/share/fonts/BQN386.ttf"
    from matplotlib import font_manager as fm
    label_fp = None
    if BQN_FONT.exists():
        fm.fontManager.addfont(str(BQN_FONT))
        label_fp = FontProperties(fname=str(BQN_FONT))

    results.sort(key=lambda x: x["time"])
    n = len(results)
    times_us = [r["time"] * 1e6 for r in results]
    max_t = max(times_us) if times_us else 1

    BG      = "#0d1117"
    PANEL   = "#161b22"
    GRID    = "#30363d"
    TEXT    = "#e6edf3"
    SUBTEXT = "#8b949e"

    plt.rcParams.update({
        "figure.facecolor": BG,
        "axes.facecolor":   PANEL,
        "text.color":       TEXT,
        "axes.labelcolor":  TEXT,
        "xtick.color":      SUBTEXT,
        "ytick.color":      SUBTEXT,
        "font.size":        11,
    })

    fig_h = max(4.5, 0.85 * n + 2.0)
    fig, ax = plt.subplots(figsize=(14, fig_h))
    fig.subplots_adjust(left=0.36, right=0.88, top=0.86, bottom=0.10)

    y = np.arange(n)
    bars = ax.barh(
        y, times_us, height=0.55,
        color=[r["color"] for r in results],
        edgecolor="none", alpha=0.92, zorder=3,
    )

    for i, (bar, t_us) in enumerate(zip(bars, times_us)):
        if t_us < 1:
            lbl = f"{t_us * 1000:.0f} ns"
        elif t_us < 1000:
            lbl = f"{t_us:.1f} \u03bcs"
        else:
            lbl = f"{t_us / 1000:.2f} ms"
        ax.text(
            bar.get_width() + max_t * 0.015,
            bar.get_y() + bar.get_height() / 2,
            lbl, va="center", ha="left",
            fontsize=11, color=TEXT, fontweight="bold",
        )

    labels = []
    for r in results:
        b = f" ({r['bytes']}B)" if r.get("bytes") else ""
        labels.append(f"{r['name']}  {r['code']}{b}")
    ax.set_yticks(y)
    tick_kw = {}
    if label_fp:
        tick_kw["fontproperties"] = label_fp
    ax.set_yticklabels(labels, fontsize=11, **tick_kw)
    ax.invert_yaxis()
    ax.tick_params(axis="y", length=0, pad=45)

    for i, r in enumerate(results):
        logo_file = LOGOS_DIR / f"{r.get('logo', '')}.png"
        if not logo_file.exists():
            continue
        try:
            img = mpimg.imread(str(logo_file))
            zoom = 22 / img.shape[0]
            oi = OffsetImage(img, zoom=zoom)
            ab = AnnotationBbox(
                oi, (0, i),
                xybox=(-18, 0),
                xycoords=("axes fraction", "data"),
                boxcoords="offset points",
                frameon=False, pad=0,
            )
            ax.add_artist(ab)
        except Exception:
            pass

    ax.set_xlabel("Time per call (\u03bcs)", fontsize=12, labelpad=10)
    ax.set_title(
        "Maximum Odd Binary Number \u2014 Benchmark\n"
        f"Input: {INPUT_LEN}-char \"010101\u2026\"  \u00b7  "
        f"{N_ITERS:,} iters  \u00b7  median of {N_RUNS} runs",
        fontsize=14, fontweight="bold", pad=15, color="#ffffff",
    )
    for spine in ax.spines.values():
        spine.set_color(GRID)
    ax.grid(axis="x", linestyle="--", alpha=0.3, color=GRID, zorder=0)
    ax.set_xlim(0, max_t * 1.22)


    plt.savefig(
        str(output_path), dpi=150,
        bbox_inches="tight", facecolor=fig.get_facecolor(),
    )
    plt.close(fig)
    print(f"  Chart saved to {output_path}")


# ─────────────────────────── Interactive HTML ───────────────────

def generate_html(all_results, output_path):
    """Create a self-contained interactive HTML benchmark page with multi-size support."""
    import base64
    import json

    def _logo_b64(logo_key):
        for ext in (".png", ".svg"):
            p = LOGOS_DIR / f"{logo_key}{ext}"
            if p.exists():
                data = p.read_bytes()
                mime = "image/png" if ext == ".png" else "image/svg+xml"
                return f"data:{mime};base64,{base64.b64encode(data).decode()}"
        return ""

    sizes = sorted(all_results.keys())
    first_results = all_results[sizes[0]]

    sol_map = {}
    for size in sizes:
        for r in all_results[size]:
            key = r["name"] + "\x00" + r["code"]
            if key not in sol_map:
                sol_map[key] = dict(
                    name=r["name"], code=r["code"],
                    bytes=r.get("bytes"), color=r["color"],
                    logo=_logo_b64(r.get("logo", "")),
                    script=r.get("script", ""),
                    by_size={},
                )
            sol_map[key]["by_size"][str(size)] = dict(
                median_s=r["time"],
                median_display=_fmt_time(r["time"]),
                all_times_us=[round(t * 1e6, 2) for t in r.get("all_times", [])],
            )

    json_payload = dict(
        sizes=sizes,
        solutions=list(sol_map.values()),
    )

    html = f"""\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Max Odd Binary \u2014 Benchmark</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<style>
  *, *::before, *::after {{ box-sizing: border-box; }}
  body {{
    margin: 0; padding: 24px 32px;
    background: #0d1117; color: #e6edf3;
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
  }}
  h1 {{ font-size: 1.6rem; margin: 0 0 4px; }}
  .subtitle {{ color: #8b949e; font-size: 0.9rem; margin-bottom: 16px; }}

  /* Tabs */
  .tabs {{ display: flex; gap: 0; margin-bottom: 20px; }}
  .tab {{
    padding: 8px 20px; cursor: pointer; font-size: 0.9rem;
    border: 1px solid #30363d; background: transparent; color: #8b949e;
  }}
  .tab:first-child {{ border-radius: 8px 0 0 8px; }}
  .tab:last-child {{ border-radius: 0 8px 8px 0; }}
  .tab.active {{ background: #21262d; color: #e6edf3; border-color: #58a6ff; }}
  .view {{ display: none; }}
  .view.active {{ display: block; }}

  /* Controls row */
  .controls-row {{ display: flex; align-items: center; gap: 16px; flex-wrap: wrap; margin-bottom: 16px; }}
  .controls {{ display: flex; flex-wrap: wrap; gap: 8px; flex: 1; }}
  .chip {{
    display: flex; align-items: center; gap: 6px;
    padding: 5px 12px 5px 6px; border-radius: 20px;
    border: 2px solid var(--c); background: transparent;
    color: #e6edf3; cursor: pointer; font-size: 0.85rem;
    transition: background 0.15s;
    font-family: 'BQN386 Unicode', 'DejaVu Sans Mono', monospace;
  }}
  .chip:hover {{ background: color-mix(in srgb, var(--c) 25%, transparent); }}
  .chip.active {{ background: color-mix(in srgb, var(--c) 40%, transparent); }}
  .chip img {{ width: 22px; height: 22px; border-radius: 4px; }}
  .chip .check {{ width: 14px; text-align: center; font-size: 0.75rem; }}
  select {{
    padding: 6px 12px; border-radius: 8px; font-size: 0.9rem;
    background: #21262d; color: #e6edf3; border: 1px solid #30363d;
  }}

  .chart-wrap {{
    position: relative; width: 100%;
    background: #161b22; border-radius: 12px; padding: 20px;
    margin-bottom: 24px;
  }}
  table {{
    width: 100%; border-collapse: collapse;
    font-size: 0.85rem; background: #161b22; border-radius: 12px;
    overflow: hidden;
  }}
  th {{ text-align: left; padding: 10px 12px; color: #8b949e; border-bottom: 1px solid #30363d; }}
  td {{ padding: 8px 12px; border-bottom: 1px solid #21262d; }}
  .lang-cell {{ display: flex; align-items: center; gap: 8px; }}
  .lang-cell img {{ width: 20px; height: 20px; }}
  .code-cell {{ font-family: 'BQN386 Unicode', 'DejaVu Sans Mono', monospace; }}
  .time-val {{ font-weight: 600; }}
  .runs {{ color: #8b949e; font-size: 0.8rem; font-family: monospace; }}
  .script-cell {{
    font-family: 'BQN386 Unicode', 'DejaVu Sans Mono', monospace;
    font-size: 0.78rem; white-space: pre-wrap; color: #8b949e;
    max-width: 500px;
  }}
  .bar-swatch {{
    display: inline-block; width: 10px; height: 10px;
    border-radius: 2px; margin-right: 6px;
  }}
</style>
</head>
<body>

<h1>Maximum Odd Binary Number \u2014 Benchmark</h1>
<div class="subtitle">
  {N_ITERS:,} iterations &middot; median of {N_RUNS} runs &middot;
  sizes: {', '.join(f'{s:,}' for s in sizes)} chars
</div>

<div class="tabs">
  <button class="tab active" onclick="switchTab('detail')">Detail</button>
  <button class="tab" onclick="switchTab('summary')">Summary</button>
</div>

<div class="controls-row">
  <div class="controls" id="controls"></div>
  <select id="sizeSelect" onchange="onSizeChange()">
    {chr(10).join(f'    <option value="{s}"' + (' selected' if s == 1000 else '') + f'>{s:,} chars</option>' for s in sizes)}
  </select>
</div>

<!-- Detail view -->
<div class="view active" id="view-detail">
  <div class="chart-wrap">
    <canvas id="barChart"></canvas>
  </div>
  <table>
    <thead>
      <tr>
        <th>#</th><th>Language</th><th>Solution</th><th>Bytes</th>
        <th>Median</th><th>All runs (\u03bcs)</th><th>Script</th>
      </tr>
    </thead>
    <tbody id="tbody"></tbody>
  </table>
</div>

<!-- Summary view -->
<div class="view" id="view-summary">
  <div class="chart-wrap" style="height:500px">
    <canvas id="lineChart"></canvas>
  </div>
</div>

<script>
const BENCH = {json.dumps(json_payload, ensure_ascii=False)};
const SIZES = BENCH.sizes;
const SOLS  = BENCH.solutions;
const enabled = new Set(SOLS.map((_, i) => i));
let currentSize = SIZES.includes(1000) ? '1000' : String(SIZES[0]);
let barChart, lineChart;

function fmtTime(s) {{
  const us = s * 1e6;
  if (us < 1) return (us * 1000).toFixed(0) + ' ns';
  if (us < 1000) return us.toFixed(1) + ' \\u03bcs';
  return (us / 1000).toFixed(2) + ' ms';
}}

function switchTab(name) {{
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
  document.querySelector(`.tab[onclick*="${{name}}"]`).classList.add('active');
  document.getElementById('view-' + name).classList.add('active');
  if (name === 'summary') updateLineChart();
}}

function onSizeChange() {{
  currentSize = document.getElementById('sizeSelect').value;
  updateBarChart();
  updateTable();
}}

// ── Controls ──
function buildControls() {{
  const el = document.getElementById('controls');
  SOLS.forEach((d, i) => {{
    const chip = document.createElement('button');
    chip.className = 'chip active';
    chip.style.setProperty('--c', d.color);
    const bytes = d.bytes ? ` (${{d.bytes}}B)` : '';
    chip.innerHTML =
      (d.logo ? `<img src="${{d.logo}}" alt="">` : '') +
      `<span class="check">\\u2713</span>` +
      `<span>${{d.name}} ${{d.code}}${{bytes}}</span>`;
    chip.onclick = () => {{
      if (enabled.has(i)) {{ enabled.delete(i); chip.classList.remove('active'); }}
      else {{ enabled.add(i); chip.classList.add('active'); }}
      chip.querySelector('.check').textContent = enabled.has(i) ? '\\u2713' : '';
      updateBarChart(); updateTable(); updateLineChart();
    }};
    el.appendChild(chip);
  }});
}}

// ── Bar chart (detail view) ──
function buildBarChart() {{
  barChart = new Chart(document.getElementById('barChart'), {{
    type: 'bar',
    data: {{ labels: [], datasets: [{{ data: [], backgroundColor: [], borderWidth: 0 }}] }},
    options: {{
      indexAxis: 'y', responsive: true, maintainAspectRatio: false,
      plugins: {{
        legend: {{ display: false }},
        tooltip: {{ callbacks: {{ label: ctx => fmtTime(ctx.raw) }} }}
      }},
      scales: {{
        x: {{
          title: {{ display: true, text: 'Time per call', color: '#8b949e' }},
          ticks: {{ color: '#8b949e' }},
          grid: {{ color: '#30363d' }},
        }},
        y: {{
          ticks: {{ color: '#e6edf3', font: {{ family: "'BQN386 Unicode','DejaVu Sans Mono',monospace", size: 12 }} }},
          grid: {{ display: false }},
        }}
      }}
    }}
  }});
  updateBarChart();
}}

function updateBarChart() {{
  const vis = SOLS
    .map((d, i) => ({{ ...d, idx: i }}))
    .filter(d => enabled.has(d.idx) && d.by_size[currentSize])
    .sort((a, b) => a.by_size[currentSize].median_s - b.by_size[currentSize].median_s);
  const labels = vis.map(d => {{
    const b = d.bytes ? ` (${{d.bytes}}B)` : '';
    return `${{d.name}}  ${{d.code}}${{b}}`;
  }});
  const values = vis.map(d => d.by_size[currentSize].median_s * 1e6);
  const colors = vis.map(d => d.color);
  barChart.data.labels = labels;
  barChart.data.datasets[0].data = values;
  barChart.data.datasets[0].backgroundColor = colors;
  barChart.canvas.parentElement.style.height = Math.max(200, vis.length * 52 + 60) + 'px';
  barChart.resize();
  barChart.update();
}}

// ── Table (detail view) ──
function updateTable() {{
  const tbody = document.getElementById('tbody');
  const vis = SOLS
    .map((d, i) => ({{ ...d, idx: i }}))
    .filter(d => enabled.has(d.idx) && d.by_size[currentSize])
    .sort((a, b) => a.by_size[currentSize].median_s - b.by_size[currentSize].median_s);
  tbody.innerHTML = '';
  vis.forEach((d, rank) => {{
    const sd = d.by_size[currentSize];
    const tr = document.createElement('tr');
    const b = d.bytes != null ? d.bytes + 'B' : '\\u2014';
    const runs = sd.all_times_us.map(t => t.toFixed(1)).join(', ');
    const scriptHtml = d.script
      ? d.script.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
      : '';
    tr.innerHTML = `
      <td>${{rank + 1}}</td>
      <td><div class="lang-cell">
        <span class="bar-swatch" style="background:${{d.color}}"></span>
        ${{d.logo ? `<img src="${{d.logo}}" alt="">` : ''}}
        ${{d.name}}
      </div></td>
      <td class="code-cell">${{d.code}}</td>
      <td>${{b}}</td>
      <td class="time-val">${{sd.median_display}}</td>
      <td class="runs">${{runs}}</td>
      <td class="script-cell">${{scriptHtml}}</td>
    `;
    tbody.appendChild(tr);
  }});
}}

// ── Line chart (summary view) ──
function buildLineChart() {{
  lineChart = new Chart(document.getElementById('lineChart'), {{
    type: 'line',
    data: {{ labels: SIZES.map(s => s.toLocaleString()), datasets: [] }},
    options: {{
      responsive: true, maintainAspectRatio: false,
      interaction: {{ mode: 'index', intersect: false }},
      plugins: {{
        legend: {{ display: true, labels: {{ color: '#e6edf3', usePointStyle: true, padding: 16,
          font: {{ family: "'BQN386 Unicode','DejaVu Sans Mono',monospace" }} }} }},
        tooltip: {{
          callbacks: {{
            label: ctx => `${{ctx.dataset.label}}: ${{fmtTime(ctx.raw)}}`
          }}
        }}
      }},
      scales: {{
        x: {{
          title: {{ display: true, text: 'Input size (chars)', color: '#8b949e' }},
          ticks: {{ color: '#8b949e' }},
          grid: {{ color: '#30363d' }},
        }},
        y: {{
          type: 'logarithmic',
          title: {{ display: true, text: 'Time per call (seconds, log)', color: '#8b949e' }},
          ticks: {{ color: '#8b949e', callback: (v) => fmtTime(v) }},
          grid: {{ color: '#21262d' }},
        }}
      }}
    }}
  }});
}}

function updateLineChart() {{
  if (!lineChart) return;
  const datasets = [];
  SOLS.forEach((d, i) => {{
    if (!enabled.has(i)) return;
    const data = SIZES.map(s => {{
      const sd = d.by_size[String(s)];
      return sd ? sd.median_s : null;
    }});
    const bytes = d.bytes ? ` (${{d.bytes}}B)` : '';
    datasets.push({{
      label: `${{d.name}} ${{d.code}}${{bytes}}`,
      data,
      borderColor: d.color,
      backgroundColor: d.color + '33',
      pointBackgroundColor: d.color,
      pointRadius: 5,
      borderWidth: 2.5,
      tension: 0.2,
    }});
  }});
  lineChart.data.datasets = datasets;
  lineChart.update();
}}

buildControls();
buildBarChart();
updateTable();
buildLineChart();
updateLineChart();
</script>
</body>
</html>
"""
    Path(output_path).write_text(html, encoding="utf-8")
    print(f"  Interactive page saved to {output_path}")


# ─────────────────────────── Solutions ──────────────────────────

SOLUTIONS = [
    dict(
        name="BQN", code="1\u233d\u2228", bytes=3,
        color="#2b7067", logo="bqn",
        bench=bench_bqn,
        script=(
            '  \u2022Out \u2022Fmt N(1\u233d\u2228)\u2022_timed L\u294a"01"\n'
            '              ^^^^^^^^^^^^  \u2190 only this is timed\n'
            '  \u2022_timed creates the input once, then runs (1\u233d\u2228) on it N times'
        ),
    ),
    dict(
        name="Kap", code="1\u233d\u2228", bytes=3,
        color="#55a630", logo="kap",
        bench=bench_kap,
        script=(
            '  input \u2190 L\u2374"01"                          \u2190 not timed\n'
            '  time:measureTime { { 1\u233d\u2228 input } \u00a8 \u2373N }  \u2190 timed: apply fn N times'
        ),
    ),
    dict(
        name="Uiua", code="\u21bb1\u21cc\u2346", bytes=4,
        color="#ea1999", logo="uiua",
        bench=bench_uiua,
        script=(
            '  S \u2190 \u21afL "01"              \u2190 not timed\n'
            '  T \u2190 now\n'
            '  \u2365(\u25cc\u21bb1\u21cc\u2346 S)N            \u2190 timed: apply fn N times, pop result\n'
            '  &p \u00f7N -T now'
        ),
    ),
    dict(
        name="TinyAPL", code="1\u2218\u2296\u2218\u22b5", bytes=5,
        color="#9b59b6", logo="tinyapl",
        bench=lambda: bench_tinyapl("1\u2218\u2296\u2218\u22b5"),
        script=(
            '  \u2395\u2190(1\u2218\u2296\u2218\u22b5) \u2395_Measure L\u2374\'01\'\n'
            '  \u2395_Measure times F applied to the argument (1 call)'
        ),
    ),
    dict(
        name="TinyAPL", code="1\u00ab\u2296\u00bb\u22b5", bytes=5,
        color="#8e44ad", logo="tinyapl",
        bench=lambda: bench_tinyapl("1\u00ab\u2296\u00bb\u22b5"),
        script='  \u2395\u2190(1\u00ab\u2296\u00bb\u22b5) \u2395_Measure L\u2374\'01\'',
    ),
    dict(
        name="TinyAPL", code="\u2985" "1\u2296\u22b5" "\u2986", bytes=5,
        color="#7d3c98", logo="tinyapl",
        bench=lambda: bench_tinyapl("\u2985" "1\u2296\u22b5" "\u2986"),
        script='  \u2395\u2190(\u29851\u2296\u22b5\u2986) \u2395_Measure L\u2374\'01\'',
    ),
    dict(
        name="J", code="1|.\\:~", bytes=6,
        color="#2ad4ff", logo="j",
        bench=bench_j,
        script=(
            "  input =: L $ '01'                    \u2190 not timed\n"
            "  bench =: 3 : '1 |. \\:~ input'        \u2190 define fn\n"
            "  echo (6!:2 'bench\"0 i. N') % N       \u2190 timed: 6!:2 runs bench N times"
        ),
    ),
    dict(
        name="APL", code="1\u233d\u2282\u2364\u2352\u235b\u2337", bytes=7,
        color="#24a148", logo="apl",
        bench=bench_apl,
        script=(
            '  input\u2190L\u2374\'01\'                         \u2190 not timed\n'
            '  t\u21902\u2283\u2395AI\n'
            '  _\u2190{(1\u233d\u2282\u2364\u2352\u235b\u2337)input}\u00a8\u2373N        \u2190 timed: apply fn N times\n'
            '  \u2395\u2190((2\u2283\u2395AI)-t)\u00f71000\u00d7N'
        ),
    ),
    dict(
        name="C++", code="partition+rotate", bytes=None,
        color="#659ad2", logo="cpp_logo",
        bench=lambda: bench_cpp(
            "partition_rotate",
            "std::ranges::partition(s, [](auto c) { return c == '1'; });\n"
            "  std::ranges::rotate(s, std::next(s.begin()));",
        ),
        script=(
            '  // input created before timing\n'
            '  auto start = high_resolution_clock::now();\n'
            '  for (int i = 0; i < N; ++i)\n'
            '    result = maximum_odd_binary(input);  // pass-by-value copy + partition + rotate\n'
            '  auto end = high_resolution_clock::now();'
        ),
    ),
    dict(
        name="C++", code="sort+rotate", bytes=None,
        color="#4a7fb5", logo="cpp_logo",
        bench=lambda: bench_cpp(
            "sort_rotate",
            "std::ranges::sort(s, std::greater{});\n"
            "  std::ranges::rotate(s, std::next(s.begin()));",
        ),
        script=(
            '  // input created before timing\n'
            '  auto start = high_resolution_clock::now();\n'
            '  for (int i = 0; i < N; ++i)\n'
            '    result = maximum_odd_binary(input);  // pass-by-value copy + sort + rotate\n'
            '  auto end = high_resolution_clock::now();'
        ),
    ),
]


# ─────────────────────────── Main ───────────────────────────────

def _fmt_time(secs):
    us = secs * 1e6
    if us < 1:
        return f"{us * 1000:.0f} ns"
    if us < 1000:
        return f"{us:.1f} \u03bcs"
    return f"{us / 1000:.2f} ms"


def run_benchmarks_for_size(input_len, log_scripts=False):
    """Run all solutions for a given input length. Returns list of result dicts."""
    global INPUT_LEN
    INPUT_LEN = input_len
    _cpp_bin_cache.clear()

    results = []
    for sol in SOLUTIONS:
        tag = f"{sol['name']}  {sol['code']}"
        print(f"  \u25b8 {tag}")
        if log_scripts and sol.get("script"):
            print(f"    \u250c\u2500 script (N={N_ITERS}, L={INPUT_LEN}):")
            for line in sol["script"].splitlines():
                print(f"    \u2502 {line}")
            print(f"    \u2514\u2500")

        times = []
        for r_idx in range(N_RUNS):
            t = sol["bench"]()
            if t is not None and t >= 0:
                times.append(t)
                print(f"      run {r_idx + 1}/{N_RUNS}: {t * 1e6:>10.2f} \u03bcs")
            else:
                print(f"      run {r_idx + 1}/{N_RUNS}: FAILED")

        if times:
            med = statistics.median(times)
            results.append(dict(
                name=sol["name"], code=sol["code"],
                bytes=sol.get("bytes"), color=sol["color"],
                logo=sol.get("logo", ""), time=med,
                all_times=times,
                script=sol.get("script", ""),
            ))
            print(f"    \u2192 median: {_fmt_time(med)}")
        else:
            print(f"    \u2717 skipped")

    results.sort(key=lambda x: x["time"])
    return results


def main():
    print("=" * 60)
    print("  Maximum Odd Binary Number \u2014 Benchmark")
    print(f"  Sizes: {INPUT_SIZES}")
    print(f"  Iterations: {N_ITERS:,}  |  Runs: {N_RUNS} (median)")
    print("=" * 60)

    all_results = {}
    for size in INPUT_SIZES:
        print(f"\n{'─' * 60}")
        print(f"  Input size: {size:,} chars")
        print(f"{'─' * 60}")
        all_results[size] = run_benchmarks_for_size(
            size, log_scripts=(size == INPUT_SIZES[0]),
        )

    default_size = 1_000
    if default_size in all_results:
        results = all_results[default_size]
    else:
        results = next(iter(all_results.values()))

    print(f"\n{'=' * 60}")
    print(f"  Results for {default_size:,}-char input (fastest \u2192 slowest)")
    print("=" * 60)
    for i, r in enumerate(results, 1):
        b = f"({r['bytes']}B)" if r.get("bytes") else ""
        print(f"  {i:>2}. {r['name']:>10}  {r['code']:<18} {b:<6} {_fmt_time(r['time']):>10}")

    print("\nGenerating outputs...")
    generate_chart(results, ROOT / "benchmark_all.png")
    results_no_tinyapl = [r for r in results if r["name"] != "TinyAPL"]
    generate_chart(results_no_tinyapl, ROOT / "benchmark_no_tinyapl.png")
    generate_html(all_results, ROOT / "benchmark.html")


if __name__ == "__main__":
    main()
