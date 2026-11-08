# CodeReviewAI — AI 代码审查助手（cs24107）

[![CI 门禁](https://github.com/Wx20060617/cs24107-CodeReviewAI/actions/workflows/ci.yml/badge.svg)](https://github.com/Wx20060617/cs24107-CodeReviewAI/actions/workflows/ci.yml)

软件工程基础课程项目仓库，实验一《软件项目计划》与实验二《软件需求分析》共用。

- 组别：cs24107-CodeReviewAI · 计科 242 · 2024210600 / 王翔（组长）
- 本人角色：B-审查规则（CLI）—— 规则管理、权重分级、规则市场、AI 智能审查（F4~F6）

## 目录

```
├── .github/workflows/ci.yml       # GitHub Actions 门禁（静态检查 + 规则集 Schema + 引擎冒烟）
├── docs/02-SRS-初稿.md            # 实验二：需求分析初稿
├── docs/03-SRS-整合版.md          # 实验二：需求分析整合版
├── model/CodeReviewAI.eap         # EA 工程
├── src/cli/codereview/            # B 模块规则引擎（P2.1~P2.4）
│   ├── rule_engine.py             # 加载校验 / 匹配执行 / 权重计分 / 门禁判定
│   ├── cli.py                     # 命令行入口（--rules / --schema / --diff / --ast）
│   └── rules/                     # default.yaml 规则集 + schema.json
└── tools/                         # 建模与实测脚本
```

## 运行规则引擎

```bash
pip install -r requirements.txt
python -m src.cli.codereview.cli \
  --rules src/cli/codereview/rules/default.yaml \
  --schema src/cli/codereview/rules/schema.json \
  --diff hunks.json
```

`--diff` 为 git diff 解析后的分块 JSON，形如
`[{"file": "demo/service.py", "addedLines": [{"line": 12, "text": "eval(user_input)"}]}]`。
门禁通过（总分不超过 `gateThreshold`）时进程退出码为 0，否则为 1，可直接用于流水线卡口。

## 门禁与 CI

`.github/workflows/ci.yml` 在每次 push（`main`、`feat/**`）与每个指向 `main` 的 PR 上执行三步：

1. `ruff check src` —— 静态检查；
2. `rules/default.yaml` 过 `rules/schema.json` 的 JSON Schema 校验；
3. 生成样例 diff 复跑引擎，输出 findings 与门禁结论。

本地等价复现：

```bash
pip install -r requirements.txt ruff
ruff check src
```

## 分支与提交规范

- 主分支 `main` 受保护：改动须走 Pull Request，至少 1 人 review 后合并。
- 功能分支命名 `feat/…`、工程化改动 `ci/…`、文档改动 `docs/…`。
- 提交信息遵循 Conventional Commits（`feat:` / `fix:` / `docs:` / `ci:`）。
- 里程碑标签：`exp1-final`（实验一交付基线）。
