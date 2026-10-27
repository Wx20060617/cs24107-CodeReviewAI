# -*- coding: utf-8 -*-
"""实验二 需求获取阶段的仓库实测脚本（表 2-16 的 M1/M2/M3/M5）。

只用标准库，不依赖任何第三方包。输出可直接贴进 docs/00-调研记录.md。

用法：
    python tools/measure_repo.py --repo D:/path/to/repo
    python tools/measure_repo.py --repo D:/path/to/repo --commits 40
    python tools/measure_repo.py --repo D:/path/to/repo --skip-pylint

对应关系：
    M1 Python 语料行数 / pylint 告警总数
    M2 告警按 message-id 首字母与类别分组（风格 / 复杂度 / 正确性 / 安全）
    M3 最近 N 个 commit 的 diff 规模（文件数、增删行数）的中位数
    M5 全量扫描耗时（pylint 单次运行墙钟时间）
"""
import argparse
import json
import os
import re
import shutil
import statistics
import subprocess
import sys
import time

STYLE = {"C", "R"}          # convention / refactor -> 风格与复杂度
CORRECT = {"W", "E", "F"}   # warning / error / fatal -> 正确性
SECURITY_SYMBOLS = (
    "exec", "eval", "pickle", "subprocess", "shell", "hardcoded", "password",
    "secret", "token", "sql", "tempfile", "yaml.load", "assert",
)


def walk_files(root, exts, skip_dirs=("node_modules", ".git", ".venv", "venv", "__pycache__", "dist", "build")):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip_dirs]
        for fn in filenames:
            if fn.endswith(exts):
                yield os.path.join(dirpath, fn)


def count_loc(files):
    total, blank, comment = 0, 0, 0
    for f in files:
        try:
            with open(f, encoding="utf-8", errors="ignore") as fh:
                for ln in fh:
                    total += 1
                    s = ln.strip()
                    if not s:
                        blank += 1
                    elif s.startswith("#") or s.startswith("//"):
                        comment += 1
        except OSError:
            pass
    return total, blank, comment


def run_pylint(root):
    exe = shutil.which("pylint")
    if not exe:
        return None, "未找到 pylint（pip install pylint 后重试）"
    t0 = time.time()
    proc = subprocess.run([exe, root, "--output-format=json", "--recursive=y", "--exit-zero"],
                          capture_output=True, text=True, encoding="utf-8", errors="ignore")
    cost = time.time() - t0
    try:
        data = json.loads(proc.stdout or "[]")
    except json.JSONDecodeError:
        return None, "pylint 输出不是合法 JSON：" + (proc.stderr or "")[:200]
    return {"items": data, "seconds": round(cost, 1)}, None


def categorize(items):
    buckets = {"风格": 0, "正确性": 0, "安全（疑似）": 0}
    for it in items:
        mid = (it.get("message-id") or "C0000")[0].upper()
        sym = (it.get("symbol") or "") + " " + (it.get("message") or "").lower()
        if any(k in sym for k in SECURITY_SYMBOLS):
            buckets["安全（疑似）"] += 1
        elif mid in STYLE:
            buckets["风格"] += 1
        elif mid in CORRECT:
            buckets["正确性"] += 1
    return buckets


def git_diff_stats(root, n):
    try:
        out = subprocess.run(
            ["git", "-C", root, "log", f"-{n}", "--pretty=format:%H", "--shortstat"],
            capture_output=True, text=True, encoding="utf-8", errors="ignore").stdout
    except FileNotFoundError:
        return None
    files, lines = [], []
    for ln in out.splitlines():
        m = re.search(r"(\d+) files? changed", ln)
        if m:
            files.append(int(m.group(1)))
            lines.append(sum(int(x) for x in re.findall(r"(\d+) (?:insertions?|deletions?)", ln)))
    if not files:
        return None
    return {
        "n": len(files),
        "files_median": statistics.median(files),
        "files_max": max(files),
        "lines_median": statistics.median(lines),
        "lines_max": max(lines),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, help="被测仓库根目录")
    ap.add_argument("--commits", type=int, default=40)
    ap.add_argument("--skip-pylint", action="store_true")
    a = ap.parse_args()
    root = os.path.abspath(a.repo)
    if not os.path.isdir(root):
        sys.exit("目录不存在：" + root)

    py = list(walk_files(root, (".py",)))
    ts = list(walk_files(root, (".ts", ".tsx", ".js", ".jsx")))
    py_loc = count_loc(py)
    ts_loc = count_loc(ts)

    print("## 语料规模\n")
    print("| 语言 | 文件数 | 总行数 | 空行 | 注释行 |")
    print("|------|-------:|-------:|-----:|-------:|")
    print(f"| Python | {len(py)} | {py_loc[0]} | {py_loc[1]} | {py_loc[2]} |")
    print(f"| TS/JS | {len(ts)} | {ts_loc[0]} | {ts_loc[1]} | {ts_loc[2]} |")

    if not a.skip_pylint and py:
        res, err = run_pylint(root)
        if err:
            print("\n> pylint：" + err)
        else:
            items = res["items"]
            bk = categorize(items)
            total = len(items) or 1
            print("\n## M1/M2/M5　pylint 结果\n")
            print(f"- 告警总数：**{len(items)}**（语料 {py_loc[0]} 行，平均 {len(items)/max(py_loc[0],1)*1000:.1f} 条/千行）")
            print(f"- 全量扫描耗时：**{res['seconds']} s**")
            print("\n| 类别 | 条数 | 占比 |")
            print("|------|-----:|-----:|")
            for k, v in bk.items():
                print(f"| {k} | {v} | {v/total*100:.1f}% |")
            print("\n> 高权重类别 = 正确性 + 安全，占比 "
                  f"{(bk['正确性']+bk['安全（疑似）'])/total*100:.1f}% —— 表 2-16 M2 的默认权重表据此设定。")

    d = git_diff_stats(root, a.commits)
    if d:
        print(f"\n## M3　最近 {d['n']} 个 commit 的 diff 规模\n")
        print(f"- 变更文件数：中位 **{d['files_median']:.0f}**，最大 {d['files_max']}")
        print(f"- 变更行数：中位 **{d['lines_median']:.0f}**，最大 {d['lines_max']}")
        print("\n> 若中位文件数 ≤5 且行数 ≤150，说明 `--diff` 增量模式足以覆盖日常提交（F1/F7 的依据）。")
    else:
        print("\n> 未取到 git 记录（非 git 仓库或无提交）。")


if __name__ == "__main__":
    main()
