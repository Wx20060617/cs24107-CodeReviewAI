"""P2 规则执行引擎（B 模块核心）。P2.1 加载校验 / P2.2 匹配执行 / P2.3 权重 / P2.4 门禁。"""
from __future__ import annotations

import re

import jsonschema
import yaml


def load_ruleset(path, schema_path=None):
    """P2.1 规则加载与校验：YAML -> JSON Schema 校验 -> 内存索引。"""
    with open(path, encoding="utf-8") as f:
        ruleset = yaml.safe_load(f)
    if schema_path:
        with open(schema_path, encoding="utf-8") as f:
            jsonschema.validate(ruleset, yaml.safe_load(f))
    ruleset["_index"] = {r["id"]: r for r in ruleset["rules"]}
    return ruleset

def match(ruleset, hunks, ast_context):
    """P2.2 规则匹配与执行：ast 规则查 AST 节点，regex 规则查 diff 新增行。"""
    findings = []
    for rule in ruleset["rules"]:
        if rule.get("disabled"):
            continue
        hits = _match_ast(rule, ast_context) if rule["type"] == "ast" else _match_regex(rule, hunks)
        for h in hits:
            findings.append({"rule_id": rule["id"], "where": h, "severity": rule["severity"]})
    return findings

def _match_ast(rule, ast_context):
    out, pat = [], rule.get("nodePattern", "")
    for node in ast_context.get("nodes", []):
        if rule.get("nodeType") and node.get("type") != rule["nodeType"]:
            continue
        if pat and re.search(pat, node.get("text", "")):
            out.append({"file": node["file"], "line": node["line"], "text": node["text"]})
    return out

def _match_regex(rule, hunks):
    out, pat = [], re.compile(rule["pattern"])
    for hunk in hunks:
        for line in hunk.get("addedLines", []):
            if pat.search(line.get("text", "")):
                out.append({"file": hunk["file"], "line": line["line"], "text": line["text"]})
    return out

def score(findings, ruleset):
    """P2.3 权重与严重度计算：总分 = Σ(命中数 × 规则权重)。"""
    idx, total = ruleset["_index"], 0.0
    for f in findings:
        w = float(idx[f["rule_id"]].get("weight", 1.0))
        f["weight"] = w
        total += w
    return findings, total

def gate(total, ruleset):
    """P2.4 门禁判定：总分与 gateThreshold 比较，给出 pass/fail。"""
    th = float(ruleset.get("gateThreshold", 100.0))
    passed = total <= th
    return {"score": total, "threshold": th, "passed": passed, "conclusion": "pass" if passed else "fail"}
