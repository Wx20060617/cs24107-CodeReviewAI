# -*- coding: utf-8 -*-
"""CodeReviewAI CLI 入口。"""
import argparse, json, sys
from . import rule_engine

def main():
    ap = argparse.ArgumentParser(prog="codereview", description="AI 代码审查助手（B 模块：规则审查）")
    ap.add_argument("--rules", default="rules/default.yaml", help="规则集 YAML 路径")
    ap.add_argument("--schema", default=None, help="规则 JSON Schema（可选校验）")
    ap.add_argument("--diff", required=True, help="git diff 输出文件（分块 hunks）")
    ap.add_argument("--ast", default=None, help="AST 上下文 JSON（可选）")
    args = ap.parse_args()

    ruleset = rule_engine.load_ruleset(args.rules, args.schema)
    with open(args.diff, encoding="utf-8") as f:
        hunks = json.load(f)
    ast_ctx = {}
    if args.ast:
        with open(args.ast, encoding="utf-8") as f:
            ast_ctx = json.load(f)

    findings = rule_engine.match(ruleset, hunks, ast_ctx)
    findings, total = rule_engine.score(findings, ruleset)
    result = rule_engine.gate(total, ruleset)
    result["findings"] = findings
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    sys.exit(0 if result["passed"] else 1)

if __name__ == "__main__":
    main()
