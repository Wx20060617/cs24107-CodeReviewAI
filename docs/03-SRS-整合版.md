# 软件需求规格说明书（SRS）

**项目**：AI 代码审查助手（CodeReviewAI）
**组别**：cs24107　**班级**：计科 242
**版本**：v1.0　**日期**：2026-11-04
**整合范围**：A 代码解析、B 审查规则、C CLI 与 Web、D 报告与趋势、E IDE 插件、F AI 审查
**与初稿的关系**：本稿在 `docs/02-SRS-初稿.md` 的基础上，把五个模块的需求统一编号、
统一验收标准句式，并补齐外部接口、数据与非功能需求，作为小组统一的需求基线。

---

## 1 引言

### 1.1 目的

本文定义 CodeReviewAI 的完整功能需求、外部接口需求、数据需求与非功能需求，作为设计、编码、测试与验收的共同依据。读者为组内五名成员、指导教师与组间互评方。

### 1.2 范围

本产品是一个面向中小研发团队的代码审查工具：接收一次代码提交（全量或增量），解析出语法结构，按可配置规则集与 AI 模型双重检查，产出缺陷清单、质量分数与趋势报告。产品提供 CLI、HTTP API、Web 页面与 IDE 插件四个入口。

不包含：代码托管（复用 Gitee/GitHub）、缺陷自动修复的自动合入、多租户计费。

### 1.3 术语

| 术语 | 含义 |
|---|---|
| 扫描 Scan | 对一次提交执行全部检查的过程，是计分与报告的最小单位 |
| 规则 Rule | 一条"什么写法算问题"的声明，含类别、严重度、权重、匹配方式 |
| 缺陷 Finding | 一次规则或 AI 命中的结果，含文件、行号、代码片段 |
| 规则包 Rule Pack | 可整体安装的规则集合，带版本号 |
| 去重组 dedup_group | 同一意图下的多条规则归并键，同一行只报一次 |
| 增量扫描 | 只检查相对基线提交新增或修改的行 |

### 1.4 参考

1. GB/T 8567—2006 计算机软件文档编制规范
2. OMG UML 2.5.1 Specification
3. RFC 9110 HTTP Semantics
4. PostgreSQL 16 Documentation
5. OWASP Top 10 (2021)
6. CWE/SANS Top 25

---

## 2 总体描述

### 2.1 产品定位

开发者提交代码后 90 秒内拿到一份"体检报告"：哪里有问题、多严重、总分多少、比上次好还是差。定位介于"纯静态分析工具"与"人工代码评审"之间——机器负责确定性的红线与规模化的初筛，人负责判断设计取舍。

### 2.2 用户类与角色

| 角色 | 关注点 | 主要入口 |
|---|---|---|
| 开发者 | 我的这次提交有没有问题、怎么改 | CLI、IDE 插件 |
| 团队负责人 | 整体质量趋势、谁在退步 | Web 报告页、趋势图 |
| 规则维护者 | 规则准不准、误报多不多 | 规则管理接口、YAML 仓库 |
| 评审者（组间互评） | 结论可复现、可核对 | Web 报告页、历史对比 |

### 2.3 运行环境

- 服务端：Linux / Windows，Python 3.11+，PostgreSQL 16，Redis 7
- 客户端：CLI（跨平台）、浏览器（Chrome/Edge 最近两个大版本）、VS Code 1.80+
- 外部依赖：DeepSeek API（可降级）、Git 托管平台的 Webhook

### 2.4 约束与假设

- C1 源码包不引入第三方运行时依赖（课程要求），Semgrep/tree-sitter 按可选依赖处理
- C2 首次扫描全量代码不超过 5 分钟，增量扫描不超过 90 秒
- C3 代码不得离开内网，除非团队显式开启 AI 审查
- A1 假设被审代码可通过 Git 获取，且能取到 base/head 两个提交
- A2 假设团队规模 3~30 人，单仓库 ≤ 50 万行

---

## 3 功能需求

需求编号规则：`FR-<模块>-<序号>`。每条需求给用户故事与 EARS 验收标准，验收标准是可执行的判定条件。

### 3.1 FR-A 代码解析（负责人：王奕超）

**FR-A-01 增量差异提取**

> 作为开发者，我只想看到本次提交引入的问题，不想被历史遗留问题淹没。

- WHEN 给定 base 与 head 两个提交，THE SYSTEM SHALL 产出变更文件列表，含新增行号集合。
- IF 提交为首次推送（无 base），THEN THE SYSTEM SHALL 退化为全量扫描并在报告中标注。
- WHILE 文件为二进制或超过 2 MB，THE SYSTEM SHALL 跳过解析并在结果中记录跳过原因。

**FR-A-02 多语言语法解析**

> 作为规则维护者，我需要拿到统一的语法结构，以便规则不必关心源语言差异。

- THE SYSTEM SHALL 至少支持 Python、Java、TypeScript、Go 四种语言的解析。
- WHEN 解析成功，THE SYSTEM SHALL 产出统一的 `ParsedFile`（路径、语言、源码、新增行、语法树）。
- IF 源文件存在语法错误，THEN THE SYSTEM SHALL 标记 `parse_error=true` 并继续处理其余文件，不得中断扫描。

**FR-A-03 解析缓存**

- WHEN 文件内容哈希未变化，THE SYSTEM SHALL 复用上次解析结果，不重复解析。
- IF 缓存不可用，THEN THE SYSTEM SHALL 降级为直接解析，扫描结果不受影响。

### 3.2 FR-B 审查规则（负责人：王翔）

**FR-B-01 规则以声明式文件定义**

> 作为规则维护者，我希望用 YAML 声明一条规则，以便新增检查项时不必改引擎代码。

- WHEN 规则文件写入 `rules/<lang>/` 并执行同步，THE SYSTEM SHALL 在 5 秒内完成校验并返回结论。
- IF 缺少 `key`/`name`/`category`/`severity`/`weight`/`lang`/`executor` 任一字段，THEN THE SYSTEM SHALL 返回 40002 并给出 `jsonPath`。
- IF `key` 不符合 `^[A-Z]{2}-[A-Z]{3}-\d{3}$`，THEN THE SYSTEM SHALL 拒绝入库并提示期望格式。
- WHEN 同一 `key` 以更高 `version` 写入，THE SYSTEM SHALL 保留旧版本行，仅新版本 `is_current=true`。
- WHERE 规则已被缺陷记录引用，THE SYSTEM SHALL 禁止物理删除，只允许 `enabled=false`。

**FR-B-02 四种匹配方式可替换**

> 作为引擎维护者，我希望匹配方式按规则声明的 `executor` 选取，新增方式不改引擎。

- THE SYSTEM SHALL 支持 `REGEX`、`AST_QUERY`、`SEMGREP`、`PLUGIN` 四种执行器，四者对引擎暴露同一接口 `execute(rule, file)`。
- WHEN 服务启动，IF 任一执行器未注册，THEN THE SYSTEM SHALL 立即启动失败，而不是在该规则被调用时才报错。
- WHEN 规则声明的 `executor` 未注册，THE SYSTEM SHALL 返回 50300 并跳过该规则，其余规则照常执行。
- WHILE 执行单条规则，THE SYSTEM SHALL 在 5 秒后超时中止并记录 `timeout` 审计事件。

**FR-B-03 规则预筛选**

- THE SYSTEM SHALL 按固定顺序执行五道过滤：语言 → 路径 glob → 严重度阈值 → 忽略注解 → 配额。
- WHEN 规则语言与本次全部文件均不匹配，THE SYSTEM SHALL 跳过该规则且不产生 IO。
- IF 文件路径命中规则的 `exclude` glob，THEN THE SYSTEM SHALL 不对该文件应用该规则。
- WHEN 目标行或上一行存在 `# noqa: <rule_key>`，THE SYSTEM SHALL 不产出该规则的缺陷。

**FR-B-04 缺陷去重与评分**

- THE SYSTEM SHALL 以 `sha256(rule_key + file_path + line + code_hash)` 生成去重键，同一缺陷只落一行。
- WHEN 同一去重组命中同一行，THE SYSTEM SHALL 只上报权重最高的一条。
- WHEN 同一规则累计扣分超过 `weight × 3`，THE SYSTEM SHALL 封顶为 `weight × 3`。
- WHEN 同一类别累计扣分超过 25，THE SYSTEM SHALL 封顶为 25。
- THE SYSTEM SHALL 以 `100 - 扣分之和` 计总分，按 ≥90/≥80/≥70/≥60 映射 A/B/C/D，其余为 E。

### 3.3 FR-C CLI 与 Web（负责人：王强军）

**FR-C-01 命令行入口**

> 作为开发者，我希望在仓库根目录一条命令完成扫描。

- WHEN 执行 `cr scan`，THE SYSTEM SHALL 扫描当前仓库并输出摘要（缺陷数、分数、等级、报告链接）。
- WHEN 执行 `cr scan --base <ref>`，THE SYSTEM SHALL 只扫描相对该基线的增量。
- IF 存在 BLOCKER 级缺陷，THEN THE SYSTEM SHALL 以非零退出码结束，供 CI 判定。
- WHEN 执行 `cr rules sync`，THE SYSTEM SHALL 将 YAML 规则导入数据库并输出变更条数。

**FR-C-02 Web 报告页**

- WHEN 打开报告页，THE SYSTEM SHALL 展示总分、等级、按类别与严重度的分布、缺陷列表（文件/行号/片段/建议）。
- WHEN 点击某条缺陷，THE SYSTEM SHALL 展示前后 3 行上下文。
- IF 用户无该团队权限，THEN THE SYSTEM SHALL 返回 40300，不泄露报告内容。

**FR-C-03 统一响应体**

- THE SYSTEM SHALL 所有 HTTP 接口返回 `{code, message, data}` 三段结构。
- IF 业务校验失败，THEN THE SYSTEM SHALL 返回业务码（40001~5xxxx）并与 HTTP 状态码双轨标注。

### 3.4 FR-D 报告与趋势（负责人：王琦）

**FR-D-01 报告导出**

- WHEN 执行 `cr report --format md|pdf`，THE SYSTEM SHALL 生成含分数、缺陷清单、修复建议的报告文件。
- IF 报告中含 AI 生成的修复建议，THEN THE SYSTEM SHALL 标注来源为 AI，与规则结论区分。

**FR-D-02 趋势统计**

- WHEN 打开趋势页，THE SYSTEM SHALL 展示最近 30 次扫描的分数曲线与缺陷类别堆叠。
- WHEN 选择两个扫描做对比，THE SYSTEM SHALL 给出新增缺陷、已修复缺陷与分数变化。
- WHILE 某规则连续 3 次扫描命中率为 0，THE SYSTEM SHALL 在规则健康度中标记"疑似失效"。

### 3.5 FR-E IDE 插件（负责人：王浩）

**FR-E-01 编辑器内联诊断**

> 作为开发者，我希望问题直接标在代码行上，不用切到网页。

- WHEN 打开被扫描过的文件，THE SYSTEM SHALL 通过 LSP 诊断在对应行展示缺陷与严重度。
- WHEN 鼠标悬停诊断，THE SYSTEM SHALL 展示规则说明与修复建议。
- IF 服务不可达，THEN THE SYSTEM SHALL 静默降级，不阻塞编辑器。

**FR-E-02 单文件即时扫描**

- WHEN 保存文件，THE SYSTEM SHALL 在 3 秒内返回该文件的增量检查结果。

### 3.6 FR-F AI 审查（全组）

**FR-F-01 异步旁路**

- WHEN 规则扫描完成，THE SYSTEM SHALL 异步提交 AI 复核，不阻塞报告生成。
- IF AI 服务超时或额度耗尽，THEN THE SYSTEM SHALL 将报告标记 `ai_fallback=true` 并照常输出。
- WHEN AI 与规则命中同一位置，THE SYSTEM SHALL 合并为一条，保留规则结论为主、AI 结论为辅。

**FR-F-02 结果约束**

- THE SYSTEM SHALL 要求 AI 返回结构化结果（文件、行号、类别、建议），不接受自由文本。
- IF AI 返回的位置不在本次变更行内，THEN THE SYSTEM SHALL 丢弃该条结论。

---

## 4 外部接口需求

| 接口 | 形式 | 关键约定 |
|---|---|---|
| CLI | 命令行 | 退出码：0 通过、1 有 BLOCKER、2 参数错、3 服务不可用 |
| HTTP API | REST/JSON | 认证 Bearer Token；分页 `page/size`；限流 42900 |
| IDE | LSP over stdio | 诊断 `textDocument/publishDiagnostics` |
| CI | Webhook | Gitee/GitHub push 事件，HMAC 校验签名 |
| 存储 | PostgreSQL 16 | 11 张表，`t_oper_log` 按月分区 |

---

## 5 数据需求

| 表 | 作用 | 关键约束 |
|---|---|---|
| `t_user` | 账号与角色 | `account` 唯一 |
| `t_team` | 团队 | — |
| `t_scan` | 扫描任务 | 记录 `commit_sha`、`rule_pack_version`，保证可复现 |
| `t_file_diff` | 变更文件 | `(scan_id, file_path)` 唯一 |
| `t_rule` | 规则多版本 | `(rule_key, version)` 唯一，部分唯一索引保证单一 `is_current` |
| `t_finding` | 缺陷 | `dedup_key` 唯一，同缺陷不重复落库 |
| `t_ai_review` | AI 结论 | 记录 `model`、`prompt_version`，可追溯 |
| `t_report` | 报告 | `scan_id` 唯一，`score` 与 `grade` 同事务写入 |
| `t_patch` | 修复补丁 | 与 `t_finding` 一对多 |
| `t_rule_pack` | 规则包 | `rules` 用 JSONB，GIN 索引支撑标签检索 |
| `t_oper_log` | 审计 | 按月分区，保留 180 天 |

---

## 6 非功能需求

| 编号 | 需求 | 指标 | 验证方式 |
|---|---|---|---|
| NFR-01 | 扫描时延 | 增量 P95 ≤ 90 秒（1 万行以内） | 压测脚本 |
| NFR-02 | 单文件解析 | ≤ 2 MB，P95 ≤ 3 秒 | 压测 |
| NFR-03 | 并发 | 单机同时 4 个扫描任务不互相拖垮 | 并发测试 |
| NFR-04 | 误报率 | ≤ 15%（人工标注 100 处抽样） | 标注集 |
| NFR-05 | 可复现 | 同 `commit_sha` + 同 `rule_pack_version`，两次结果完全一致 | 单测 P1 |
| NFR-06 | 安全 | 代码默认不出内网；AI 审查需显式开启 | 配置审计 |
| NFR-07 | 可用性 | 规则引擎可用性 ≥ 99%；AI 不可用不影响主流程 | 故障注入 |
| NFR-08 | 可维护 | 新增一条规则只改 YAML，不改代码 | 代码评审 |
| NFR-09 | 兼容 | Windows/Linux 均可运行；Python 3.11+ | CI 双平台 |
| NFR-10 | 数据保留 | 审计日志 180 天，报告 1 年 | 定时任务 |

---

## 7 需求追溯矩阵

| 需求 | 模块 | 负责人 | 主要测试 |
|---|---|---|---|
| FR-A-01 ~ 03 | parser | 王奕超 | 差异提取、语法错误容错、缓存命中 |
| FR-B-01 ~ 04 | rule | 王翔 | 31 例单测，覆盖率 80% |
| FR-C-01 ~ 03 | cli / web | 王强军 | 退出码、权限、响应体结构 |
| FR-D-01 ~ 02 | report | 王琦 | 报告生成、趋势聚合、规则健康度 |
| FR-E-01 ~ 02 | ide | 王浩 | 诊断发布、服务不可达降级 |
| FR-F-01 ~ 02 | ai | 全组 | 降级、合并去重、结构化校验 |
| NFR-01 ~ 10 | 全组 | — | 压测、标注集、故障注入 |

---

## 8 分工与里程碑

| 成员 | 分工 | 交付物 |
|---|---|---|
| 王奕超 | A 代码解析 | `parser` 模块、差异提取 |
| 王翔 | B 审查规则 | `rule` 模块（11 类）、规则库、31 例单测 |
| 王强军 | C CLI 与 Web | CLI、HTTP API、报告页 |
| 王琦 | D 报告与趋势 | 报告导出、趋势统计 |
| 王浩 | E IDE 插件 | LSP 适配、内联诊断 |

| 阶段 | 内容 | 完成标志 |
|---|---|---|
| 实验一 | 需求获取与 SRS | 本文评审通过 |
| 实验二 | 概要设计 | 架构图、模块划分 |
| 实验三 | 详细设计 | 类图、接口、评分模型 |
| 实验四 | 实现与测试 | 单测全绿、真实仓库试跑 |

---

## 9 未决问题

| 编号 | 问题 | 影响 | 计划 |
|---|---|---|---|
| Q-01 | 规则误报的人工反馈如何回流到权重 | 影响 NFR-04 | 实验四补标注集 |
| Q-02 | AI 审查的成本控制在什么量级 | 影响是否默认开启 | 按团队额度配置 |
| Q-03 | 多语言规则是否共享 `dedup_group` | 影响去重效果 | 按语言前缀隔离 |
| Q-04 | IDE 插件离线缓存策略 | 影响 FR-E-02 | 下版本评估 |

---

*本文由 cs24107 组整合，各模块需求由对应负责人提供，统一编号与验收标准句式。*
