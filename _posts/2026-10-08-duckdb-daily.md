---
title: "DuckDB 日报 · 2026-10-08：类型绑定拆分、PEG 迁移与并发正确性"
date: 2026-10-08 12:00:00 +0800
description: "Mytherin 的类型解析与绑定拆分已合并；嵌套统计、PEG 优化、ADBC Arrow 和 checkpoint 并发 DDL 同步推进，外部访问控制仍有新提案。"
coverage_date: "2026-10-08"
---

覆盖窗口：北京时间 **2026-10-08 00:00 至 2026-10-09 00:00，左闭右开**，对应 UTC 10 月 7 日 16:00 至 10 月 8 日 16:00。实际核查时间：**2026-10-09 09:04—09:07（Asia/Shanghai）**。以下事件时间均为北京时间；状态以本轮核查为准，窗口后的合并另行标明。

## 今日速览

- **函数绑定职责更清楚。** Mytherin 的 `resolve_types` / `bind` 拆分已合并，并向 C API v2 暴露类型解析回调
- **PEG 迁移兼顾性能与回退。** FIRST 集剪枝、legacy_parser 扩展已经合并；更进一步的解析优化和深度防护仍在提案阶段
- **统计、数据交换与并发边界继续补齐。** 嵌套 `RETURN_STATS`、ADBC Arrow 结果、部分 DDL 与 checkpoint 并行，以及 HTTP 日志脱敏均有窗口内合并

**已合并不等于已发布。** 核查时[最新正式版本仍为 v1.5.6](https://github.com/duckdb/duckdb/releases/tag/v1.5.6)，发布日期为 9 月 28 日。下列多数变更进入 v2.0-cyanoptera；个别进入 main，不能据此认定现有稳定版已经包含。

## 重要 PR

### 1. Mytherin：类型解析先行，bind 接收转换后的参数

[#26548 — Split up ScalarFunction::bind into resolve_types and bind](https://github.com/duckdb/duckdb/pull/26548)，作者 **Mytherin**，10 月 6 日创建，本期 **16:57 merged → v2.0-cyanoptera**。

原来的 bind 回调同时处理类型推导和执行期 FunctionData 初始化，拿到的参数可能尚未转换成函数真正接受的类型。此次拆分后，流程变为：选定重载 → resolve_types → 参数转换 → bind。它直接针对嵌套类型、NULL 字面量和预处理参数带来的绑定复杂度，并新增 C API v2 的 `scalar_function_resolve_types_callback`。

对扩展作者，重点是区分“决定输入/返回类型”和“建立执行状态”，检查回调迁移。作者提到未来希望减少自定义类型解析回调，但这仍是后续目标，不能写成已经完成的类型系统重构。

### 2. Tishj 与多文件统计：嵌套容器本身也要计数

[#26538 — [Copy] Add entries to RETURN_STATS for structs and lists](https://github.com/duckdb/duckdb/pull/26538)，作者 **Tishj**，10 月 6 日创建，本期 **15:25 merged → v2.0-cyanoptera**。

COPY 的统计返回值补上 STRUCT/LIST 自身的空值数与值数，使消费者能够区分整个结构为 NULL 和结构存在但成员为 NULL。对 Iceberg、DuckLake、Delta 等 RETURN_STATS 消费者，这也有助于正确识别 Parquet VARIANT 的拆分存储形态及下推条件。

另一项关联变化是 [#26516 — Add a column_statistics option to multi-file scans](https://github.com/duckdb/duckdb/pull/26516)，作者 **h4nsmuller**，本期 **05:14 merged → v2.0-cyanoptera**。调用者可以向多文件扫描提供列统计，格式与 RETURN_STATS 衔接，帮助优化器在不逐个读取所有文件元数据的情况下了解列分布。提供的统计优先于文件统计；**真实性由调用者负责**，行数仍由 explicit_cardinality 单独控制，不能把这一功能理解成自动获得准确统计。

### 3. carlopi：PEG 剪枝落地，旧解析器成为过渡扩展

- [#26451 — PEG matcher: skip sub-matchers that cannot start at the current token (FIRST set)](https://github.com/duckdb/duckdb/pull/26451)，作者 **carlopi**，本期 **02:24 merged → v2.0-cyanoptera**。为编译后的语法预计算可起始 token 集，跳过必定失败的子匹配，减少无效解析工作。作者报告测试语句集的中位解析耗时从 65.7 μs 降至 29.8 μs；这是**作者的解析器基准，未独立复测，也不是完整查询的加速比**。
- [#26479 — Add legacy_parser extension](https://github.com/duckdb/duckdb/pull/26479)，作者 **carlopi**，本期 **17:28 merged → v2.0-cyanoptera**。`SET enable_legacy_parser = true` 可自动加载扩展并切换旧式解析器，方便比较新旧行为、定位问题。作者明确称其为尽力兼容的过渡方案；部分新语法不支持，不能当成完整的旧版本兼容保证。

窗口内新建但仍 **open → v2.0-cyanoptera** 的后续包括：**louie-duck** 的 [#26741](https://github.com/duckdb/duckdb/pull/26741)（18:43 创建），减少规则查找及结果类型探测开销，并对选定规则加入双 token 前瞻；以及 **carlopi** 的 [#26771 — Improve parser robustness](https://github.com/duckdb/duckdb/pull/26771)（23:40 创建），整合表达式嵌套深度检查的实现与测试。它们尚未合并。

### 4. ADBC 转向 ArrowFormat，同时修正错误报告

[#26704 — Move ADBC to arrow format](https://github.com/duckdb/duckdb/pull/26704)，作者 **evertlammerts**，本期 **02:12 新建、19:03 merged → v2.0-cyanoptera**。

ADBC 以 ArrowFormat 提交语句，让结果转换能够使用工作线程；可流式执行的语句由相应的结果流承载。随同修复的行为包括取消操作被误报为内部错误、写入末尾失败却返回成功、空参数流导致崩溃，以及零行变更被报告为未知行数。

实践意义是结果传输路径更统一、调用者更可靠地收到取消和写入失败信息。PR 有作者本机测量，但这里不将特定线程数和行序条件下的结果推广为通用性能承诺。

### 5. checkpoint：允许不改变表存储的 DDL 并行

[#26456 — Let DDL that keeps table storage, and sequences, run alongside checkpoints](https://github.com/duckdb/duckdb/pull/26456)，作者 **ywelsch**，10 月 5 日创建，本期 **21:14 merged → main**。

此前使用序列或执行 DDL 的事务可能长期持有共享 checkpoint 锁，阻挡手动 checkpoint，也使自动 checkpoint 被跳过。此次放宽不改变表存储的操作，例如视图、部分 schema 操作、注释、重命名及 nextval/setval，让它们可与 checkpoint 并行。

改变表存储的 DDL、索引和触发器操作，以及 CASCADE 等仍保留限制。这里的收益是减少不必要的 checkpoint 相互阻塞，不能解释为所有 DDL 都可以无锁并发。

同作者的 [#26750 — Reject duplicate keys at insert time while a checkpoint runs](https://github.com/duckdb/duckdb/pull/26750) 于本期 **19:49 新建**；窗口结束时尚未合并，核查时已 **merged → v2.0-cyanoptera**，合并发生在 **10 月 9 日 07:15，属于窗口外**。它把并发 checkpoint 场景下的重复键错误提前到 INSERT 阶段，避免应用到 COMMIT 才发现错误、整个显式事务被回滚。作者明确指出原行为也不会提交重复键，不应夸大为修复已落盘的重复数据。

### 6. 正确性修复：exp 的浮点边界与 FILL 外推

- [#26592 — Drop the monotone annotation from exp(): libm exp is not monotone](https://github.com/duckdb/duckdb/pull/26592)，作者 **carlopi**，本期 **20:44 merged → v2.0-cyanoptera**。这是昨日提案的实质进展：移除不可靠的单调性标记，避免特定浮点库舍入行为使统计推导出错，甚至剪掉应匹配的行。它没有重新实现 exp，也不是提高数值精度的承诺。
- [#26504 — Internal #10930: Backport FILL Extrapolation](https://github.com/duckdb/duckdb/pull/26504)，作者 **hawkfish**，本期 **06:45 merged → v2.0-cyanoptera**。修正 BIGINT FILL 外推在交换端点后的插值比例，补充递减序列和正负对称性的回归测试。公开说明指出 DOUBLE 与通用插值路径原本正确，影响范围不应扩大到所有 FILL 计算。

### 7. HTTP 日志脱敏已合并，外部访问控制仍在补齐

[#26522 — Redact HTTP headers and urls in duckdb_logs](https://github.com/duckdb/duckdb/pull/26522)，作者 **HendrikLambert**，本期 **04:16 merged → v2.0-cyanoptera**。除明确允许的头字段外，HTTP 请求/响应头值以及 URL 用户名、密码、查询串和 fragment 会脱敏；关闭 redact_http_logs 可恢复原始值。对需要保存或分享日志的用户，这能降低凭据信息进入诊断材料的风险，但不代表所有日志内容都已消除敏感信息。

窗口内两个相关新提案目前仍 **open → v2.0-cyanoptera**：

- **Robinho-MR** 的 [#26742 — Check enable_external_access in the central HTTP request path](https://github.com/duckdb/duckdb/pull/26742)，**19:04 创建**：将访问检查补到直接经过 HTTPUtil 的请求，覆盖绕开文件系统路径的扩展请求。扩展安装保留自己的访问控制与显式例外
- **louie-duck** 的 [#26749 — Route the remaining local file accesses in the engine through the database's file system](https://github.com/duckdb/duckdb/pull/26749)，**19:36 创建**：把若干仍直接使用本地文件系统的操作改经数据库文件系统，使其遵守数据库访问策略。PR 也列出了尚未统一的启动期和系统调用路径

这两项是访问边界收敛的提案，不能据此声称整个引擎已经具备完整沙箱保证。

### 8. Tishj / lnkuiper：DataChunk 布局抽象有实质讨论进展

[#26159 — [Dev] Generalize the concept of a “chunk layout”](https://github.com/duckdb/duckdb/pull/26159)，作者 **Tishj**，9 月 25 日创建，核查时 **open → v2.0-cyanoptera**。

该提案试图用共享布局描述处理 DataChunk 内多组向量，减少不同算子重复手写索引和偏移换算。本期 **17:25**，Tishj [报告已在其分支 PR 中尝试替换 JoinProjectionColumns](https://github.com/duckdb/duckdb/pull/26159#issuecomment-6056828078)；**19:31**，lnkuiper [认可结构化方向并询问并入当前 PR 还是另发后续](https://github.com/duckdb/duckdb/pull/26159#issuecomment-6058897928)。

这是可核验的设计推进与原型讨论，不是已完成的主仓库重构；这里没有以 updated_at 代替实质事件。

## 官方博客：日期与上线时间需要分开

[官方博客列表](https://duckdb.org/news/)最新仍为 [A DuckDB Database with No Data in It](https://duckdb.org/2026/10/07/view-only-mode.html)，作者 **The DuckDB team**，页面标注 **2026-10-07**。它已在上期介绍，本期不重复当作标注日期为 10 月 8 日的新文章。

本轮核验发现：[官网新增文章 PR #7372](https://github.com/duckdb/duckdb-web/pull/7372) 于北京时间 **10 月 8 日 01:35:17** 合并 main，确实落在本期窗口。但代码合并不等于网站实际部署完成；[源码](https://github.com/duckdb/duckdb-web/blob/main/_posts/2026-10-07-view-only-mode.md)也没有明确的时分秒字段。**此前引用的 Feed 零点应理解为 Feed 标注时间，不能当作已核实的实际首发时刻。**

文章的实践主题是用只含视图的 DuckDB 文件分享远程数据目录，原始数据仍留在对象存储；访问者仍须拥有底层数据权限。本期未见官网标注 10 月 8 日的新篇目，实际上线时刻无法精确确认。

## 方向观察（推测）

1. **让引擎和扩展的职责边界更明确。** 类型解析与绑定拆分、ADBC ArrowFormat、DataChunk 布局讨论，都在减少重复或隐式的状态转换。依据是这些具体实现与讨论；不能据此承诺整个 C/C++ API 已稳定
2. **新解析器的推进同时包含性能与迁移成本。** FIRST 集剪枝已合并，legacy_parser 提供过渡入口，后续性能与深度防护仍在讨论。这更像持续收敛，而非“一次切换就完全兼容”
3. **正确性与可运维性仍是重要投入。** 嵌套统计、浮点剪枝、FILL、checkpoint 和日志脱敏分别补齐边界。反证与限制是：多项访问控制仍未合并，main 与 v2.0 开发分支也不等于正式发布

以上是对本期公开活动的**推测性归纳，不是官方路线图**。

## 覆盖与限制

- 通过官方 GitHub API 按更新时间倒序读取全部状态 PR，共三页 300 项，已越过窗口起点；其中 253 项的最后更新时间在起点之后。该候选集合中有 71 项窗口内创建、27 项窗口内合并。数字是本轮候选统计，不是历史事件穷尽审计
- 已重点检查 Mytherin、hannes、lnkuiper、pdet、Tishj、carlopi、hawkfish 的相关候选，同时按实质影响纳入其他作者。未发现可核实的新进展时不为某位作者凑条目
- 对选入 PR 复核正文、目标分支、创建/合并时间与当前状态；对 DataChunk 设计推进额外核对评论及其时间。未逐条审计候选集合的所有提交、评论、补丁与标签变化；PR 正文可能包含窗口后的编辑
- 窗口后合并均未计为本期合并成果。例如 #26750 单列当前状态；Mytherin #26584 的合并时间为北京时间 10 月 9 日 04:50，因此不重复记为本期合并
- 官网博客列表、文章和新增稿 PR 可访问；本轮 Feed 抓取分别遇到 XML 类型不支持与 HTTP 403，不能据此断言没有新文。博客标注日期、源码合并时间及实际上线时间已分开说明
- 未独立运行 DuckDB 测试或性能基准，作者基准已注明；未全面覆盖各扩展仓库、私有讨论或尚未公开的工作
