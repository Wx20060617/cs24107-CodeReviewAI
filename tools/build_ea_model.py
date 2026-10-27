# -*- coding: utf-8 -*-
"""用 Enterprise Architect 的自动化接口（COM）建 CodeReviewAI 的 UML 模型，并由 EA 自己导出 7 张图。

前置：本机已安装 EA（脚本默认 EA 15 / EA_trial.exe 已在注册表注册 COM）
用法：
    python tools/build_ea_model.py            # 建 model/CodeReviewAI.eap，导出 assets/lab2/ea/*.png
    python tools/build_ea_model.py --keep     # 保留既有 eap，追加到新包

产物：
    model/CodeReviewAI.eap        EA 工程（答辩时打开这个）
    assets/lab2/ea/fig2-N-*.png   EA 导出的图（报告直接引用）
"""
import argparse
import os
import sys
import time
import traceback

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
EAP = os.path.join(ROOT, "model", "CodeReviewAI.eap")
IMG = os.path.join(ROOT, "assets", "lab2", "ea")
LOG = os.path.join(ROOT, "model", "build.log")

_log = open(LOG, "w", encoding="utf-8")


def p(*a):
    s = " ".join(str(x) for x in a)
    print(s, file=_log)
    _log.flush()


# ---------------------------------------------------------------- 建模封装
class Model:
    def __init__(self, repo):
        self.repo = repo
        self.root = repo.Models.GetAt(0)

    def pkg(self, name, parent=None):
        parent = parent or self.root
        for i in range(parent.Packages.Count):
            q = parent.Packages.GetAt(i)
            if q.Name == name:
                return q
        q = parent.Packages.AddNew(name, "Package")
        q.Update()
        return q

    def el(self, pkg, name, etype, notes="", stereotype="", attrs=None):
        e = pkg.Elements.AddNew(name, etype)
        if notes:
            e.Notes = notes
        if stereotype:
            e.Stereotype = stereotype
        e.Update()
        for a in attrs or []:
            nm, typ = (a if isinstance(a, tuple) else (a, ""))
            at = e.Attributes.AddNew(nm, typ)
            at.Update()
        try:
            e.Refresh()
        except Exception:
            pass
        return e

    def conn(self, src, dst, ctype, name="", sub=None, cmult=None, smult=None, direction=None, seqno=None):
        c = src.Connectors.AddNew(name, ctype)
        c.SupplierID = dst.ElementID
        if sub:
            c.Subtype = sub
        if direction:
            try:
                c.Direction = direction
            except Exception:
                pass
        if seqno:
            try:
                c.SequenceNo = seqno
            except Exception:
                pass
        c.Update()
        if cmult:
            c.ClientEnd.Cardinality = cmult
            c.ClientEnd.Update()
        if smult:
            c.SupplierEnd.Cardinality = smult
            c.SupplierEnd.Update()
        return c

    def diag(self, pkg, name, dtype, notes="", scale=None):
        d = pkg.Diagrams.AddNew(name, dtype)
        if notes:
            d.Notes = notes
        d.Update()
        if scale:
            try:
                d.Scale = scale
            except Exception:
                pass
        return d

    def put(self, d, e, l, t, r, b):
        do = d.DiagramObjects.AddNew(f"l={int(l)};t={int(t)};r={int(r)};b={int(b)}", "")
        do.ElementID = e.ElementID
        do.Update()
        return do

    def save(self):
        try:
            self.repo.GetProjectInterface().SaveProject()
        except Exception:
            pass
        try:
            self.repo.Models.GetAt(0).Update()
        except Exception:
            pass


def export(d, path, type_=1):
    """由 EA 导出图片；type: 0=BMP 1=PNG 2=GIF 3=JPG"""
    proj = d._diagram.repo.GetProjectInterface() if hasattr(d._diagram, "repo") else None
    return proj


# ---------------------------------------------------------------- 各图构建
def build(m):
    # ========== 包结构 ==========
    pkg_ctx = m.pkg("00 系统上下文")
    pkg_uc = m.pkg("01 需求（用例）")
    pkg_dfd = m.pkg("02 分析（DFD 与数据字典）")
    pkg_cls = m.pkg("03 设计（类图）")
    pkg_seq = m.pkg("04 行为（顺序图）")

    # ========== 图 2-1 上下文图 ==========
    d1 = m.diag(pkg_ctx, "图 2-1 系统上下文图", "Component",
                "CodeReviewAI 与 5 个外部实体的边界；E5 大模型服务为次级参与者（可用虚线表示可缺席）")
    sys_e = m.el(pkg_ctx, "AI 代码审查助手\nCodeReviewAI（cs24107）", "Component",
                 "系统边界内：CLI + Web 前端 + IDE 插件")
    dev = m.el(pkg_ctx, "开发者", "Actor", "提交 PR 的程序员")
    git = m.el(pkg_ctx, "Git 仓库", "Component", "GitHub / Gitee / 本地")
    rule_owner = m.el(pkg_ctx, "规则维护者", "Actor", "平台 / 质量工程师")
    ci = m.el(pkg_ctx, "CI 系统", "Component", "GitHub Actions / Jenkins")
    leader = m.el(pkg_ctx, "团队 Leader", "Actor", "质量门禁负责人")
    llm = m.el(pkg_ctx, "大模型服务", "Component", "DeepSeek / 通义千问；不可用则降级")

    m.put(d1, sys_e, 330, 230, 590, 350)
    m.put(d1, dev, 70, 60, 150, 160)
    m.put(d1, git, 40, 300, 205, 356)
    m.put(d1, rule_owner, 55, 380, 135, 480)
    m.put(d1, ci, 700, 55, 890, 113)
    m.put(d1, leader, 740, 175, 820, 275)
    m.put(d1, llm, 690, 420, 890, 482)

    m.conn(dev, sys_e, "Dependency", "审查请求 / 变更范围")
    m.conn(sys_e, dev, "Dependency", "问题清单 / 修复建议")
    m.conn(git, sys_e, "Dependency", "commit diff / 文件快照")
    m.conn(rule_owner, sys_e, "Dependency", "规则 YAML / 权重")
    m.conn(sys_e, rule_owner, "Dependency", "规则命中与误报反馈")
    m.conn(ci, sys_e, "Dependency", "流水线事件")
    m.conn(sys_e, ci, "Dependency", "SARIF / 门禁结论")
    m.conn(sys_e, leader, "Dependency", "质量趋势 / 门禁统计")
    m.conn(sys_e, llm, "Dependency", "脱敏代码片段 + Prompt（无模型则跳过）")

    # ========== 图 2-2 DFD 顶层 ==========
    d2 = m.diag(pkg_dfd, "图 2-2 DFD 顶层", "Data Flow Diagram",
                "顶层只有 1 个加工；E5 为次级外部实体，虚线表示可缺席")
    p0 = m.el(pkg_dfd, "P0 代码审查系统", "Process", "CodeReviewAI 整体")
    e1 = m.el(pkg_dfd, "E1 开发者", "External")
    e2 = m.el(pkg_dfd, "E2 CI 系统", "External")
    e3 = m.el(pkg_dfd, "E3 规则维护者", "External")
    e4 = m.el(pkg_dfd, "E4 团队 Leader", "External")
    e5 = m.el(pkg_dfd, "E5 大模型服务", "External", "次级外部实体")

    m.put(d2, p0, 340, 195, 560, 303)
    m.put(d2, e1, 70, 60, 230, 112)
    m.put(d2, e3, 70, 372, 230, 424)
    m.put(d2, e2, 668, 60, 833, 112)
    m.put(d2, e4, 668, 372, 833, 424)
    m.put(d2, e5, 680, 228, 850, 280)

    m.conn(e1, p0, "DataFlow", "审查请求：仓库/分支/commit")
    m.conn(p0, e1, "DataFlow", "问题清单、修复建议、退出码")
    m.conn(e3, p0, "DataFlow", "规则 YAML、权重、门禁阈值")
    m.conn(p0, e3, "DataFlow", "规则命中统计、误报率")
    m.conn(e2, p0, "DataFlow", "流水线事件（PR / push）")
    m.conn(p0, e2, "DataFlow", "SARIF、门禁通过/拦截")
    m.conn(p0, e4, "DataFlow", "质量趋势与门禁统计")
    m.conn(p0, e5, "DataFlow", "脱敏代码片段")
    m.conn(e5, p0, "DataFlow", "结构化审查结论")

    # ========== 图 2-3 DFD 0 层 ==========
    d3 = m.diag(pkg_dfd, "图 2-3 DFD 0 层", "Data Flow Diagram",
                "P1~P5 与 D1~D5；P2 为本人模块（B-审查规则）")
    p1 = m.el(pkg_dfd, "P1 变更解析", "Process", "A 模块")
    p2 = m.el(pkg_dfd, "P2 规则执行（B 模块）", "Process", "本人负责：规则加载、匹配、加权、门禁")
    p3 = m.el(pkg_dfd, "P3 AI 审查", "Process")
    p4 = m.el(pkg_dfd, "P4 报告生成", "Process")
    p5 = m.el(pkg_dfd, "P5 结果分发", "Process")
    d_1 = m.el(pkg_dfd, "D1 代码快照与 AST", "DataStore")
    d_2 = m.el(pkg_dfd, "D2 规则库", "DataStore")
    d_3 = m.el(pkg_dfd, "D3 问题库 Finding", "DataStore")
    d_4 = m.el(pkg_dfd, "D4 报告库", "DataStore")
    d_5 = m.el(pkg_dfd, "D5 模型调用日志", "DataStore")
    x1 = m.el(pkg_dfd, "E1 开发者", "External")
    x2 = m.el(pkg_dfd, "E3 规则维护者", "External")
    x3 = m.el(pkg_dfd, "E5 大模型服务", "External")
    x4 = m.el(pkg_dfd, "E4 团队 Leader", "External")
    x5 = m.el(pkg_dfd, "E2 CI 系统", "External")

    m.put(d3, x1, 5, 45, 110, 93)
    m.put(d3, x2, 5, 180, 110, 228)
    m.put(d3, p1, 160, 40, 335, 96)
    m.put(d3, p2, 160, 175, 335, 231)
    m.put(d3, d_1, 385, 38, 550, 80)
    m.put(d3, d_2, 385, 118, 550, 160)
    m.put(d3, d_3, 385, 198, 550, 240)
    m.put(d3, d_4, 385, 278, 550, 320)
    # D5（模型调用日志）只与 P3 有关，单独放到 P3 正下方，避免横穿中间列
    m.put(d3, d_5, 590, 420, 755, 462)
    m.put(d3, p3, 590, 40, 755, 96)
    m.put(d3, p4, 590, 175, 755, 231)
    m.put(d3, p5, 590, 300, 755, 356)
    m.put(d3, x3, 795, 38, 970, 90)
    m.put(d3, x4, 795, 175, 970, 223)
    m.put(d3, x5, 795, 300, 970, 348)

    m.conn(x1, p1, "DataFlow", "审查请求")
    m.conn(p1, d_1, "DataFlow", "快照")
    m.conn(d_1, p3, "DataFlow", "代码单元")
    m.conn(p1, p2, "DataFlow", "变更块")
    m.conn(x2, p2, "DataFlow", "规则 YAML")
    m.conn(d_2, p2, "DataFlow", "规则集")
    m.conn(p2, d_3, "DataFlow", "findings")
    m.conn(d_3, p4, "DataFlow", "候选问题")
    m.conn(p3, p4, "DataFlow", "AI 结论")
    m.conn(p3, x3, "DataFlow", "Prompt")
    m.conn(x3, p3, "DataFlow", "结论")
    m.conn(p3, d_5, "DataFlow", "调用记录")
    m.conn(p4, p5, "DataFlow", "报告+门禁")
    m.conn(p4, d_4, "DataFlow", "报告数据")
    m.conn(p4, x4, "DataFlow", "趋势")
    m.conn(x5, p5, "DataFlow", "触发")
    m.conn(p5, x5, "DataFlow", "SARIF")

    # ========== 图 2-4 P2 1 层 ==========
    d4 = m.diag(pkg_dfd, "图 2-4 P2 规则执行 1 层", "Data Flow Diagram",
                "P2 的分解，父子图输入输出守恒：输入 2 条 / 输出 2 条")
    q1 = m.el(pkg_dfd, "P2.1 规则加载与校验", "Process", "YAML → JSON Schema 校验 → 内存索引")
    q2 = m.el(pkg_dfd, "P2.2 规则匹配与执行", "Process", "AST 规则查节点、正则规则查文本")
    q3 = m.el(pkg_dfd, "P2.3 权重与严重度计算", "Process", "总分 = Σ(命中数 × 权重)")
    q4 = m.el(pkg_dfd, "P2.4 门禁判定", "Process", "与 gateThreshold 比较")
    st2 = m.el(pkg_dfd, "D2 规则库", "DataStore")
    st3 = m.el(pkg_dfd, "D3 问题库", "DataStore")
    in1 = m.el(pkg_dfd, "上层 P1 输入 hunks + 上下文", "External")
    p4_up = m.el(pkg_dfd, "上层 P4 报告生成", "External")

    # 布局：左输入(D2/in1) → 中加工链(q1→q2→q3→q4 走 S 形) → 右输出(st3/p4_up)
    # 让 q2 在 q1 右下、q3 在 q2 右侧、q4 在 q3 右下，避免任何连线斜穿
    m.put(d4, st2, 20, 40, 160, 94)
    m.put(d4, in1, 20, 220, 160, 274)
    m.put(d4, q1, 230, 40, 425, 98)
    m.put(d4, q2, 230, 188, 425, 246)
    m.put(d4, q3, 510, 188, 705, 246)
    m.put(d4, q4, 510, 320, 705, 378)
    m.put(d4, st3, 742, 118, 882, 172)
    m.put(d4, p4_up, 742, 322, 882, 376)

    m.conn(st2, q1, "DataFlow", "ruleSet.yaml")
    m.conn(q1, q2, "DataFlow", "校验后的规则集 + 索引")
    m.conn(in1, q2, "DataFlow", "diff 变更块")
    m.conn(q2, q3, "DataFlow", "rawFindings")
    m.conn(q3, q4, "DataFlow", "加权 findings")
    m.conn(q3, st3, "DataFlow", "问题入库")
    m.conn(q4, p4_up, "DataFlow", "门禁结论")

    # ========== 图 2-5 用例图 ==========
    d5 = m.diag(pkg_uc, "图 2-5 用例图（11 个用例）", "Use Case",
                "4 个主要参与者 + 1 个次级参与者；UC-09 为公共用例")
    bd = m.el(pkg_uc, "CodeReviewAI 系统边界", "Boundary")
    m.put(d5, bd, 170, 30, 740, 460)

    a_dev = m.el(pkg_uc, "开发者", "Actor")
    a_rule = m.el(pkg_uc, "规则维护者", "Actor")
    a_leader = m.el(pkg_uc, "团队 Leader", "Actor")
    a_ci = m.el(pkg_uc, "CI 系统", "Actor")
    a_llm = m.el(pkg_uc, "大模型服务", "Actor", "次级参与者")

    ucs = {}
    spec = [
        ("UC-01 发起代码审查", 250, 140), ("UC-02 查看审查结果", 250, 225),
        ("UC-06 应用自动修复", 250, 310), ("UC-11 查看团队趋势", 250, 395),
        ("UC-05 AI 智能审查", 462, 140), ("UC-10 解析代码变更", 462, 225),
        ("UC-07 生成修复 Patch", 462, 310), ("UC-09 登录与鉴权", 462, 395),
        ("UC-03 维护审查规则", 652, 140), ("UC-04 配置权重与门禁", 652, 225),
        ("UC-08 订阅规则市场", 652, 310),
    ]
    for nm, cx, cy in spec:
        ucs[nm[:5]] = m.el(pkg_uc, nm, "UseCase")
        m.put(d5, ucs[nm[:5]], cx - 78, cy - 24, cx + 78, cy + 24)

    m.put(d5, a_ci, 70, 30, 120, 105)
    m.put(d5, a_dev, 70, 180, 120, 255)
    m.put(d5, a_leader, 70, 360, 120, 435)
    m.put(d5, a_rule, 790, 190, 840, 265)
    m.put(d5, a_llm, 790, 30, 840, 105)

    m.conn(a_ci, ucs["UC-01"], "Association")
    for k in ("UC-01", "UC-02", "UC-06"):
        m.conn(a_dev, ucs[k], "Association")
    m.conn(a_leader, ucs["UC-11"], "Association")
    for k in ("UC-03", "UC-04", "UC-08"):
        m.conn(a_rule, ucs[k], "Association")
    m.conn(a_llm, ucs["UC-05"], "Association")

    m.conn(ucs["UC-01"], ucs["UC-10"], "Include")
    m.conn(ucs["UC-05"], ucs["UC-01"], "Extend")
    m.conn(ucs["UC-06"], ucs["UC-07"], "Include")
    m.conn(ucs["UC-04"], ucs["UC-03"], "Include")

    # ========== 图 2-6 类图 ==========
    d6 = m.diag(pkg_cls, "图 2-6 类图（10 类 + 1 枚举）", "Logical",
                "组合菱形在整体端；ReviewReport→Finding 用聚合（趋势要跨报告复用）")
    C = {}
    C["Project"] = m.el(pkg_cls, "Project", "Class", "被审项目/仓库",
                        attrs=[("projectId", "int"), ("repoUrl", "str"), ("defaultBranch", "str")])
    C["ReviewTask"] = m.el(pkg_cls, "ReviewTask", "Class", "一次审查任务",
                           attrs=[("taskId", "str"), ("commitSha", "str"), ("trigger", "enum"), ("status", "enum")])
    C["DiffHunk"] = m.el(pkg_cls, "DiffHunk", "Class", "一个变更块",
                         attrs=[("hunkId", "str"), ("filePath", "str"), ("added", "int"), ("removed", "int")])
    C["CodeFile"] = m.el(pkg_cls, "CodeFile", "Class", "变更涉及的文件",
                         attrs=[("fileId", "str"), ("language", "str"), ("loc", "int")])
    C["AstNode"] = m.el(pkg_cls, "AstNode", "Class", "AST 节点（规则的锚点）",
                        attrs=[("nodeId", "str"), ("nodeType", "str"), ("lineSpan", "str")])
    C["RuleSet"] = m.el(pkg_cls, "RuleSet", "Class", "规则集（含门禁阈值）",
                        attrs=[("setId", "str"), ("name", "str"), ("schemaVersion", "str"), ("gateThreshold", "float")])
    C["ReviewRule"] = m.el(pkg_cls, "ReviewRule", "Class", "单条规则（本人模块核心）",
                           attrs=[("ruleId", "str"), ("category", "enum"), ("weight", "float"),
                                  ("severity", "enum"), ("cweId", "str"), ("muteUntil", "date")])
    C["Finding"] = m.el(pkg_cls, "Finding", "Class", "命中的问题；source 区分 rule/ai",
                        attrs=[("findingId", "str"), ("line", "int"), ("severity", "enum"), ("source", "enum")])
    C["Patch"] = m.el(pkg_cls, "Patch", "Class", "修复补丁",
                      attrs=[("patchId", "str"), ("diffText", "text"), ("applied", "bool")])
    C["ReviewReport"] = m.el(pkg_cls, "ReviewReport", "Class", "报告",
                             attrs=[("reportId", "str"), ("score", "float"), ("gate", "enum"), ("createdAt", "dt")])
    sev = m.el(pkg_cls, "Severity", "Enumeration", "严重度四级",
               attrs=[("BLOCKER", ""), ("CRITICAL", ""), ("MAJOR", ""), ("MINOR", ""), ("INFO", "")])

    m.put(d6, C["Project"], 250, 15, 415, 95)
    m.put(d6, C["ReviewTask"], 250, 125, 415, 225)
    m.put(d6, C["DiffHunk"], 250, 265, 415, 355)
    m.put(d6, C["CodeFile"], 250, 370, 415, 450)
    m.put(d6, C["AstNode"], 250, 486, 415, 566)
    m.put(d6, C["RuleSet"], 30, 125, 195, 215)
    m.put(d6, C["ReviewRule"], 30, 265, 195, 375)
    m.put(d6, C["Finding"], 470, 380, 635, 480)
    m.put(d6, C["Patch"], 680, 380, 830, 460)
    m.put(d6, C["ReviewReport"], 470, 125, 635, 225)
    m.put(d6, sev, 655, 486, 785, 586)

    m.conn(C["Project"], C["ReviewTask"], "Association", "", cmult="1", smult="0..*", direction="Source -> Destination")
    m.conn(C["ReviewTask"], C["DiffHunk"], "Aggregation", "组合", sub="Strong", cmult="1", smult="1..*")
    m.conn(C["DiffHunk"], C["CodeFile"], "Association", "", cmult="1", smult="1")
    m.conn(C["CodeFile"], C["AstNode"], "Aggregation", "组合", sub="Strong", cmult="1", smult="0..*")
    m.conn(C["RuleSet"], C["ReviewRule"], "Aggregation", "组合", sub="Strong", cmult="1", smult="0..*")
    # Finding 是任务运行产生的结果、可脱离任务独立入库存档 → 聚合(Weak)
    m.conn(C["ReviewTask"], C["Finding"], "Aggregation", "聚合", sub="Weak", cmult="1", smult="0..*")
    m.conn(C["Finding"], C["ReviewRule"], "Association", "命中规则", cmult="0..*", smult="0..1")
    m.conn(C["Finding"], C["Patch"], "Association", "", cmult="0..1", smult="1")
    m.conn(C["Finding"], sev, "Association", "severity", cmult="1", smult="1")
    # 报告由问题"组合"而成，问题随报告删则删 → 组合(Strong)
    m.conn(C["ReviewReport"], C["Finding"], "Aggregation", "组合", sub="Strong", cmult="1", smult="0..*")

    # ========== 图 2-7 顺序图 ==========
    d7 = m.diag(pkg_seq, "图 2-7 UC-01 + UC-05 顺序图", "Sequence",
                "含 AI 降级分支（alt/else）：超时/429/未配置 → 跳过 AI，规则结果直出，报告标 degraded=true")
    lanes = [
        ("开发者", 62), ("CLI / IDE", 178), ("Review API", 294), ("ReviewService", 410),
        ("DiffParser", 526), ("RuleEngine(B)", 642), ("AIService", 758), ("DB / LLM", 862),
    ]
    L = {}
    for nm, x in lanes:
        L[nm] = m.el(pkg_seq, nm, "Object")
        m.put(d7, L[nm], x - 52, 40, x + 52, 110)

    def msg(src, dst, text, no, ret=False):
        c = m.conn(L[src], L[dst], "Sequence", text, seqno=str(no))
        if ret:
            try:
                c.Direction = "Source -> Destination"
            except Exception:
                pass
        return c

    msg("开发者", "CLI / IDE", "1. review --diff / 右键审查", 1)
    msg("CLI / IDE", "Review API", "2. POST /api/v1/reviews", 2)
    msg("Review API", "ReviewService", "3. createTask(repoRef, sha)", 3)
    msg("ReviewService", "DiffParser", "4. parse(diff)", 4)
    msg("DiffParser", "ReviewService", "5. hunks[] + astContext", 5, True)
    msg("ReviewService", "RuleEngine(B)", "6. execute(hunks, ruleSet)", 6)
    msg("RuleEngine(B)", "ReviewService", "7. ruleFindings[]（含 weight）", 7, True)
    msg("ReviewService", "AIService", "8. [AI 开启] semanticReview(hunks)", 8)
    msg("AIService", "DB / LLM", "9. chat(prompt, 脱敏代码)", 9)
    msg("DB / LLM", "AIService", "10. JSON：问题+等级+建议", 10, True)
    msg("AIService", "ReviewService", "11. aiFindings[]（含置信度）", 11, True)
    msg("ReviewService", "DB / LLM", "12. save(findings, report)", 12)
    msg("ReviewService", "Review API", "13. 201 {reportId, gate}", 13, True)
    msg("Review API", "CLI / IDE", "14. 200 JSON / SARIF", 14, True)
    msg("CLI / IDE", "开发者", "15. 表格 + 退出码 0/1/2", 15, True)

    note = m.el(pkg_seq, "alt / else 降级", "Note",
                "alt [AI 审查开启] → 8~11\nelse [超时 / 429 / 未配置] → 跳过 AI，规则结果直出，报告 degraded=true；退出码仍按规则结果给")
    m.put(d7, note, 380, 430, 700, 520)

    return {
        "fig2-1-context": d1, "fig2-2-dfd-top": d2, "fig2-3-dfd-0": d3,
        "fig2-4-dfd-1": d4, "fig2-5-usecase": d5, "fig2-6-class": d6, "fig2-7-sequence": d7,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep", action="store_true", help="不清空既有 eap")
    a = ap.parse_args()
    os.makedirs(os.path.dirname(EAP), exist_ok=True)
    os.makedirs(IMG, exist_ok=True)

    import win32com.client as w
    p("start", time.strftime("%H:%M:%S"))
    app = w.Dispatch("EA.App")
    repo = app.Repository
    p("dispatch ok")

    if not a.keep or not os.path.exists(EAP):
        if os.path.exists(EAP):
            os.remove(EAP)
        p("CreateModel:", repo.CreateModel(0, EAP, 0), "size:", os.path.getsize(EAP))
    p("OpenFile:", repo.OpenFile(EAP))
    time.sleep(1.2)
    p("models:", repo.Models.Count)

    m = Model(repo)
    m.root.Name = "CodeReviewAI 需求分析模型（cs24107）"
    m.root.Update()
    p("root renamed")

    dias = build(m)
    m.save()
    p("build done, diagrams:", len(dias))

    proj = repo.GetProjectInterface()
    for name, d in dias.items():
        out = os.path.join(IMG, name + ".png")
        if os.path.exists(out):
            os.remove(out)
        p("export", name, "guid:", d.DiagramGUID)
        try:
            proj.PutDiagramImageToFile(d.DiagramGUID, out, 1)
            p("   ok", os.path.getsize(out) if os.path.exists(out) else "MISSING")
        except Exception as e:
            p("   FAIL", str(e)[:160])
    m.save()
    p("DONE", time.strftime("%H:%M:%S"))
    _log.close()
    os._exit(0)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        p("ERROR", traceback.format_exc()[:1500])
        _log.close()
        sys.exit(1)
