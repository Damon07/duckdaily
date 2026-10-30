---
title: "DuckDB 日报 · 2026-10-29：Parquet 页索引、批量回取与优化器改进"
date: 2026-10-29 12:00:00 +0800
description: "Parquet 页索引和按行号批量回取合并，连接过滤、基数估计及聚合内存管理继续优化；同时补齐宏类型声明与多项正确性边界。"
coverage_date: "2026-10-29"
---

## 覆盖时间

北京时间 **2026-10-29 00:00 至 2026-10-30 00:00**（左闭右开），对应 UTC **2026-10-28 16:00 至 2026-10-29 16:00**。实际核查时间：**2026-10-30 09:10 +0800**。

下文“本日合并”均以合并时间落入上述窗口为准；已合并不等于已进入稳定版。核查时官方最新 release 仍为 [v2.0.0（10 月 21 日发布）](https://github.com/duckdb/duckdb/releases/tag/v2.0.0)，未发现窗口内新 release。

## 今日速览

- **减少读取与重复解码**：Parquet 页索引、按 row id 批量 scan/select 回取，以及阻塞扫描的并行 I/O fallback 均合并。
- **优化器与执行器协同**：连接过滤下推、值域驱动基数估计、聚合内存预留和布尔 NULL 掩码计算都有实质改进。
- **功能边界与可靠性**：标量宏 RETURNS、TRY 标量子查询支持落地；损坏文件、类型转换、C API 与旧存储兼容性得到修补。

## 重要 PR

### 1. 存储与扫描：从少读页到少解码

- **[#27326 — Parquet: read and write the page index](https://github.com/duckdb/duckdb/pull/27326)** · **h4nsmuller** · **本日 20:57 合并**。加入 ColumnIndex/OffsetIndex 读写及页级裁剪，过滤后只预取候选页，尤其有助于读取具备页索引的外部 Parquet 文件。**读取默认开启，写入 `WRITE_PAGE_INDEX` 默认关闭、须显式启用**；启用写索引且未另设页大小时默认 1 MiB，普通写入默认不变，加密文件不写页索引。不要把它理解为所有 Parquet 写入已自动改变布局。
- **[#27383 — Fetch rows by row id through selects and scans, and remove fetch_row](https://github.com/duckdb/duckdb/pull/27383)** · **ywelsch** · **本日 17:19 合并**。按 segment 将行号组织成 scan/select 窗口，移除压缩接口逐行 `fetch_row`，避免批量删除提交和索引清理中的重复解码；同时加入字符串复制模式，保证结果不引用已经失效的扫描缓冲区。这是访问路径简化与批量操作性能改进，不只是局部微调。
- **[#27690 — Run I/O tasks of blocked scan that cannot park side by side](https://github.com/duckdb/duckdb/pull/27690)** · **h4nsmuller** · **本日 21:29 合并**。无法 park/yield 的扫描在同步等待路径也可并行执行独立 I/O task，覆盖 Parquet、多文件及表扫描；单任务仍直接执行。意义在于减少同步 fallback 将可并行 I/O 串行化的损失。

### 2. 优化与执行：更准确的计划，更少的额外工作

- **[#28059 — Improve JoinFilterPushdown](https://github.com/duckdb/duckdb/pull/28059)** · **lnkuiper** · **本日 20:41 合并**。扩展安全的连接过滤下推目标，包括分组键路径，并保留 NULL、cast 错误及算子边界语义。新增 NULL-safe 动态过滤，但该路径仍限于直接 scan/filter/projection，不能概括为任意算子都支持。
- **[#28013 — Better cardinality estimation for SEMI/ANTI joins and GROUP BY](https://github.com/duckdb/duckdb/pull/28013)** · **lnkuiper** · **本日 00:08 合并**：区分总值域与过滤后的当前值域，改善半连接、反连接和分组的基数估计；证据不足时保留 fallback。**[#28021 — Cap GROUP BY cardinality estimate by the group-key domain](https://github.com/duckdb/duckdb/pull/28021)** · **h4nsmuller** · **本日 18:06 合并**：以 min/max 或 BOOLEAN、窄整数、ENUM 等有限值域作为普通分组基数上界，并考虑 NULL 与乘积溢出。两者互补，有助于避免高估，而非保证每个查询都选到最优计划。
- **[#28065 — Improve Radix HT memory reservation](https://github.com/duckdb/duckdb/pull/28065)** · **lnkuiper** · **本日 20:09 合并**。将聚合 arena 导出阈值所需余量计入内存预留，减少明明有可用内存却过早导出聚合状态；这是 reservation 改善，不是新 spill 算法。
- **[#28046 — Compute AND/OR Validity 64 Rows At A Time For Flat Vectors](https://github.com/duckdb/duckdb/pull/28046)** · **Richard-Durkee** · **本日 21:45 合并**。flat vector 的布尔结果按 64 行批量计算 validity 位，减少含 NULL 时逐行判断；常量、字典向量保留旧路径，**不是 WHERE 过滤路径的改写**。适用于投影、聚合参数等产生布尔值的场景。

### 3. SQL 能力与正确性：明确可承诺的边界

- **[#27889 — Support RETURNS type declarations on scalar macro members](https://github.com/duckdb/duckdb/pull/27889)** · **kryonix** · **本日 23:06 合并**。标量宏每个重载成员可声明返回类型，以普通 cast 语义约束结果，并在元数据、导出导入中保留声明。持久化要求 **v2.1.0 storage version**；低版本存储会拒绝而非静默丢弃，内存和 TEMP 宏不受同一持久化门槛限制。代码中的版本门槛**不是 v2.1.0 已发布的声明**。
- **[#27386 — Support TRY over scalar subqueries by rewriting into ordinary subqueries](https://github.com/duckdb/duckdb/pull/27386)** · **kryonix** · **本日 21:14 合并**。最终实现是先按普通子查询绑定，再向逻辑计划下放 TRY，并以 `has_error` 标记保护聚合输入；不是早期讨论的全执行边界捕获。**WHERE、连接条件、聚合内部错误等仍可能传播**，窗口、部分集合与聚合形态仍有限制，因此不能写成“TRY 可吞掉任意子查询错误”。
- **[#27914 — Bind default macro bodies in their defining context](https://github.com/duckdb/duckdb/pull/27914)** · **kryonix** · **本日 18:21 合并**。限定内置默认宏体中的系统函数引用，防止调用者 search path 或同名函数改变其内部含义；不把所有用户宏改成定义时绑定。
- **[#28056 — Pair STRUCT fields by name in the cast fallibility analysis](https://github.com/duckdb/duckdb/pull/28056)** · **kryonix** · **本日 22:50 合并**。可抛错分析与实际 STRUCT 按名称配对一致，并补上 MAP 键转换后冲突的判断，避免普通转换错误误变成内部错误，以及错误的表达式重排。
- **[#28074 — Fix uint32 length overflow in DELTA_BYTE_ARRAY parquet decoder](https://github.com/duckdb/duckdb/pull/28074)** · **h4nsmuller** · **本日 22:32 合并**：扩大长度求和类型、检查单值与总长度溢出，拒绝恶意或损坏输入。**[#28037 — Validate perfect hash aggregate group ids](https://github.com/duckdb/duckdb/pull/28037)** · **HendrikLambert** · **本日 23:45 合并**：同时验证 clustered 和逐行更新所用的 group id，损坏统计不应导致越界状态访问。
- **[#28049 — CAPI Temporal Exceptions](https://github.com/duckdb/duckdb/pull/28049)** · **k9-doctor** · **本日 19:19 合并**。`duckdb_to_date` / `duckdb_to_timestamp` 对无效日期或越界时间戳采用非抛异常路径并返回 0，避免 C 调用者无法捕获的 C++ 异常终止进程。
- **[#28000 — JSON、HTTP 重试及旧读取器兼容性修复合集](https://github.com/duckdb/duckdb/pull/28000)** · **Robinho-MR** · **本日 17:52 合并**。逐行调用的 `json_each/json_tree` 可使用多线程，修复并行 NDJSON 的 BOM 处理；成功请求退还此前被限流重试消耗的配额；旧存储兼容级别下保留仍被引用的元数据后继块，防止 checkpoint 后旧读取器无法打开。**不会自动修复已有悬空指针的文件**，这些文件仍需重写相关元数据。另含 EXPLAIN 文本宽度缓存及 shell 测试隔离修复。

### 窗口内新提案，窗口后状态单列

**[#28086 — More join filter pushdown improvements](https://github.com/duckdb/duckdb/pull/28086)** · **lnkuiper**：北京时间 **10 月 29 日 23:14 新建**，继续扩展跨聚合、窗口及等价连接键的下推与扫描调度。窗口结束时尚未合并；核查时已于 **10 月 30 日 04:58 合并**，属于下一自然日，不能计入上述本日合并成果。

### 核心贡献者参与

本次筛选未发现 Mytherin 在窗口内新建的 PR，但其维护工作可从原始时间线核实：Mark Raasveldt（**Mytherin**）将 #27383、#28065、#27889、#28037 推进合并；**hannes** 推进 #27326 和 #27690。作者与合并维护者在这里分别列出，不把他人的代码贡献归给审核者。

## 官方博客

**[From Spreadsheets to DuckLake: A Data Engineer's Road to DuckDB](https://www.duckdb.org/2026/10/29/from-spreadsheets-to-ducklake)**  
官网标注发布日期 **2026-10-29**；作者 **Matt Martin、Geertjan Wielenga、Tim Cox**。

文章回顾 Matt 从 Excel、数据库到 Spark 的实践，解释为何希望用熟悉的 SQL 和更少基础设施完成分析。DuckLake 将元数据放入 SQL 数据库，是其降低湖仓管理复杂度的重要原因；文中也讨论动态 ATTACH、异步 I/O 和 Quack 的体验。这是一篇用户案例，**不是当天新增功能清单或官方路线图**。访谈中的 alpha 体验是历史语境，不改变 v2.0.0 已在 10 月 21 日发布的事实。

## 方向观察（推测）

从页级裁剪、批量回取、连接过滤和 I/O fallback 的共同变化看，项目正在持续减少“无用读取、重复解码和提前物化/导出”的成本；与此同时，TRY、cast 可抛错性及损坏数据检查强调优化不能改变错误语义。这个判断来自多项已合并改动，**不是对未来官方路线图的承诺**。页索引写入仍 opt-in、下推与 TRY 仍保留边界，也说明功能覆盖和兼容性需要继续验证。

## 来源覆盖与限制

- 已读取 [官方 PR](https://github.com/duckdb/duckdb/pulls) 的公开 API：按窗口起点起算的更新检索分页取得 **141 条候选**，并用窗口内合并检索交叉核对 **23 条**（包含 release 分支回合并），不以单独的 updated_at 判断实质进展。正文按重要性选取，非所有 PR 的流水账。
- 对重点项目回查详情、最终 changed-files diff 与相关讨论/时间线；较长的 #27326 时间线读取了第二页。没有复跑作者基准或全套测试，因此不把 PR 的局部测速推广成普遍加速承诺，也不声称逐条审计了全部候选讨论。
- [官网 news](https://duckdb.org/news/) 可读，博客日期、作者及正文由官网列表和官方域名搜索抓取交叉核实；文章直连在本环境受限。[RSS](https://duckdb.org/feed.xml) 在网页工具不支持 XML，直接请求返回 403，**未完成 RSS 全量独立核对**。这不等于“没有新博客”；本文只收录已取得正文证据的一篇。
- 发布记录另用官方 GitHub Releases 核验；功能合并、storage version 标记和稳定版发布严格区分。
