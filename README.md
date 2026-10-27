# CodeReviewAI — AI 代码审查助手（cs24107）

软件工程基础 · 实验二《软件需求分析》初稿交付包。

- 组别：cs24107-CodeReviewAI · 计科 242 · 2024210600 / 王翔
- 本人角色：B-审查规则(CLI) —— 规则管理、权重分级、规则市场、AI 智能审查（F4~F6）

## 目录

```
├── docs/02-SRS-初稿.md        # 实验二报告（需求分析初稿）
├── model/CodeReviewAI.eap     # EA 15 工程（7 张图：上下文/DFD 顶层/0层/P2一层/用例/类/顺序）
├── assets/lab2/ea/            # 7 张图（EA SaveAsPDF 导出）
├── src/cli/codereview/        # B 模块规则引擎骨架（P2.1~P2.4）
│   ├── rule_engine.py
│   ├── cli.py
│   └── rules/                 # default.yaml 规则集 + schema.json
└── tools/                     # 建模与实测脚本
```

## 复现图件

```bash
python tools/build_ea_model.py    # EA 自动化建模 -> model/CodeReviewAI.eap
python tools/ea_export_pdf.py     # EA SaveAsPDF 导出 7 张图 -> assets/lab2/ea/
```

## 运行规则引擎

```bash
pip install -r requirements.txt
python -m src.cli.codereview.cli --rules src/cli/codereview/rules/default.yaml --diff hunks.json
```
