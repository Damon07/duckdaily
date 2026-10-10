---
title: "DuckDB 日报 · 2026-10-09：v2.0 回归修复、checkpoint 正确性与 CLI Agent Mode"
date: 2026-10-09 12:00:00 +0800
description: "C API v2 文件元数据、查询回归和 checkpoint 并发修复已合并；嵌套 VARIANT 写入仍在提案阶段，官方介绍 CLI Agent Mode。"
coverage_date: "2026-10-09"
---

覆盖窗口：北京时间 **2026-10-09 00:00 至 2026-10-10 00:00，左闭右开**（UTC 10 月 8 日 16:00 至 10 月 9 日 16:00）。实际核查时间：**2026-10-10 09:03—09:06（Asia/Shanghai）**。下文 PR 事件时间均为北京时间，状态以核查时为准。

## 今日速览

- **v2.0 性能与正确性继续收敛。** 热循环、表过滤和聚合哈希表调整已合并；join order 的后续修复仍 open
- **checkpoint 的并发边界有多项修复。** 涵盖虚假校验和错误、块空间泄漏和重复键报错时机；WAL 重放后的索引保护另有新提案
- **扩展读写接口与 Agent 使用体验同步推进。** Mytherin 的单文件读取元数据接口已合并；官方新文介绍 CLI Agent Mode，但不能把它理解为稳定版新发布

**已合并不等于已发布。** 核查时[最新正式版仍为 v1.5.6](https://github.com/duckdb/duckdb/releases/tag/v1.5.6)，9 月 28 日发布。以下选入 PR 的目标分支均为 **v2.0-cyanoptera**。

## 重要 PR

### 1. Mytherin：单文件读取器接收完整文件打开信息

[#26584 — C API v2: pass the file to single-file functions together with its open options, and describe files through get_bind_info](https://github.com/duckdb/duckdb/pull/26584)，作者 **Mytherin**，10 月 6 日创建，本期 **04:50:04 merged**。

单文件函数现在可接收路径，或包含 filename、etag 等打开选项的结构值，复用 glob 或湖仓目录已提供的元数据，减少读取器为获取文件大小、etag 等重复请求。文件字段 ID 与键值元数据的描述移到 get_bind_info 回调。对 C/C++ 扩展作者，这是需要关注的接口迁移，不是现有稳定版 API 已经改变的声明。

### 2. lnkuiper：先修执行回归，再补 join order 估算

- [#26791 — Regression fixes](https://github.com/duckdb/duckdb/pull/26791)，作者 **lnkuiper**，本期 **14:21:32 创建、23:40:58 merged**。针对 v1.5 到 v2.0 的部分 TPC-H/TPC-DS 回归，调整热循环、表过滤和少量优化器逻辑；作者明确说它没有解决所有连接顺序回归。
- [#26812 — Join order regression fixes](https://github.com/duckdb/duckdb/pull/26812)，同作者，本期 **20:56:20 创建，仍 open**。在前一 PR 基础上改进 distinct 采样、小基数哈希构建成本、LEFT JOIN 复合键估算、运行时过滤成本，以及稠密整数 OR 条件的范围下推。作者认为更广泛的改动可能要到 v2.1；这是作者判断，不能当成已承诺的版本计划。
- [#26166 — Use telemetry-based adaptive HT growing for aggregates](https://github.com/duckdb/duckdb/pull/26166)，作者 **d-justen**，9 月 25 日创建，本期 **16:31:00 merged**。调整聚合哈希表自适应扩容逻辑，针对分组数或工作线程数变化时的时间、内存性能陡变。未独立复测，不提供通用加速比。

### 3. Tishj：嵌套读取正确性落地，嵌套 VARIANT 写入待合并

[#26777 — [MultiFileReader] Fixes to the column mapper for pushed down extract expressions](https://github.com/duckdb/duckdb/pull/26777)，作者 **Tishj**，本期 **01:57:52 创建、14:35:08 merged**。

修复嵌套字段提取下推绕过 schema 重映射的问题。列表或 map 内字段删除后重新加入等 schema 演进场景，原来可能返回空字符串而非 NULL；映射器现在按实际文件 schema 应用字段 ID、转换与默认值。随附 Parquet 回归覆盖重命名、类型拓宽、默认值及 NULL 容器。

同作者的 [#26808 — [Parquet] Enable writing VARIANT outside of the root of the schema](https://github.com/duckdb/duckdb/pull/26808) 于本期 **20:09:58 创建，仍 open**：拟支持 STRUCT、LIST、MAP 和定长 ARRAY 内的 VARIANT 导出。PR 说明嵌套遍历、转换后的整行组及大子向量可能增加临时内存，且未做前后性能基准，不能宣称无额外成本。

### 4. checkpoint：三项已合并，一项新的 WAL/索引提案

- [#26716 — Fix spurious checksum failures caused by stale block handles racing in-place metadata block rewrites](https://github.com/duckdb/duckdb/pull/26716)，作者 **kryonix**，10 月 7 日创建，本期 **07:30:58 merged**。避免旧块句柄读盘与元数据原地重写竞态造成虚假校验和失败，并防止旧句柄析构误注销新句柄。公开说明指出该案例磁盘文件本身完好，不应描述为修复所有数据库损坏。
- [#26722 — Fix storage leak on checkpoint data race](https://github.com/duckdb/duckdb/pull/26722)，作者 **dentiny**，10 月 8 日创建，本期 **02:48:40 merged**。把数据库头相关赋值放入同一临界区，避免并发分配块时记录的最大块号与空闲块信息不一致。
- [#26750 — Reject duplicate keys at insert time while a checkpoint runs](https://github.com/duckdb/duckdb/pull/26750)，作者 **ywelsch**，10 月 8 日创建，本期 **07:15:50 merged**。并发 checkpoint 中，重复键改为在 INSERT 阶段报错，不再拖到 COMMIT，避免处理语句错误的应用最终丢掉整个显式事务。原行为也不会提交重复键。上期已披露窗口后状态，本期按实际合并时间归档。
- [#26814 — Bind indexes with buffered replays before checkpoint starts, or skip it and keep the WAL](https://github.com/duckdb/duckdb/pull/26814)，作者 **artjomPlaunov**，本期 **21:07:56 创建，仍 open**。拟在 checkpoint 前绑定存在缓冲重放的索引，失败时保留 WAL，针对重启后自动 checkpoint 可能丢失索引条目的路径；尚未成为已合并修复。

### 5. hannes、hawkfish、carlopi：类型与文件路径边界

- [#26553 — Determine the return type when folding a function call with a typed NULL argument](https://github.com/duckdb/duckdb/pull/26553)，作者 **hannes**，10 月 6 日创建，本期 **06:15:05 merged**。带类型 NULL 的函数折叠先完成类型解析，避免未定型 NULL 泄漏到重载选择与 UNION ALL。仍在 bind 中决定返回类型的函数尚未全部迁移。
- [#26590 — Issue #25701: Virtual Pushdown OOB](https://github.com/duckdb/duckdb/pull/26590)，作者 **hawkfish**，10 月 7 日创建，本期 **15:16:10 merged**。补丁在解析列绑定时检查真实列索引，并排除 filename 等虚拟列，防止把它们当成类型/表达式下推候选。
- [#26559 — Fixup CopyToFile to correctly rename also for opfs://file.db](https://github.com/duckdb/duckdb/pull/26559)，作者 **carlopi**，10 月 6 日创建，本期 **01:51:20 merged**。修正 OPFS 顶层文件路径的重命名边界，对 DuckDB-Wasm 的 OPFS 支持有直接意义。
- [#26796 — [Secrets] Add missing initialization of persist_type to DEFAULT](https://github.com/duckdb/duckdb/pull/26796)，作者 **Tishj**，本期 **16:39:59 创建、22:58:37 merged**。补上持久化类型初始化，修复 DROP SECRET 等路径中的偶发错误。

### 6. 一批数据边界修复集中落地

[#26680 — Merge ready-to-merge PRs](https://github.com/duckdb/duckdb/pull/26680)，作者 **Robinho-MR**，10 月 7 日创建，本期 **07:00:25 merged**。

该整合 PR 汇集多项已待合并修复，包括反序列化类型/向量校验、Parquet DECIMAL 与 TIME 验证、fsum/favg 的 Kahan 补偿项符号、Arrow 有效性位图边界，以及 CSV 多字节分隔符支持。它体现的是一批具体边界问题的处理，不能据此宣称输入验证已全部完成；其正文明确排除了部分未就绪或目标分支不同的 PR。

## 官方博客

[Agent Mode in the DuckDB CLI](https://www.duckdb.org/2026/10/09/agent-mode)，作者 **The DuckDB team**，官方标注日期 **2026-10-09**。

文章介绍面向 AI 编程代理的 v2.0 CLI Agent Mode：紧凑 Markdown 表格、明确的截断提示、JSON 错误，以及查询早停、成本与进度信息，让代理更容易理解查询反馈。官方 TPC-H 实验中，查询输出读取 token 减少 **59%**，但总体成本和耗时未见改善；这不是通用的性能保证，也不是 v2.0 正式发布公告。

[官网源码日期调整提交](https://github.com/duckdb/duckdb-web/commit/da9154170fda3f2f17815edbc12e5193d39c86b1)在本期 **19:53:22** 将稿件日期由 10 月 8 日改为 10 月 9 日。本期按官方页面日期收录；代码提交时间不等于实际首次上线时间，精确首发时刻未核实。10 月 7 日的 view-only-mode 文章不重复列作今日新文。

## 方向观察（推测）

1. **v2.0 当前活动偏向回归收敛。** 执行热路径、连接估算、聚合扩容和 checkpoint 修复构成直接依据。但连接估算后续及 WAL 索引提案仍 open，不能推断所有回归已清零。
2. **湖仓与扩展接口更重视元数据复用和 schema 语义。** #26584、#26777 和 #26808 分别触及打开选项、字段映射与嵌套写入。后者仍未合并，且有明确的内存代价。
3. **Agent 体验开始深入 CLI 交互细节。** 官方新文聚焦输出、错误和查询进度，而非只增加自然语言入口。文中实验也没有证明总体成本或耗时下降，不能把 token 减少等同于端到端效率提升。

以上是基于公开活动的**推测性归纳，不是官方路线图**。

## 覆盖与限制

- 通过 GitHub 搜索 API 按最后更新时间检索 UTC 10 月 8 日 16:00 至 10 月 10 日 01:03，完成三页、201 个候选；API 返回 incomplete_results=false。候选中 38 项在报道窗口创建、73 项在窗口合并。这是检索快照统计，不是所有历史事件的穷尽审计。
- 重点检查 Mytherin、hannes、lnkuiper、pdet、Tishj、carlopi、hawkfish，同时纳入其他作者的重要变化。pdet 的 #25183 在北京时间 10 月 10 日 01:17 合并，已在窗口之外，未算作本期合并成果。
- 对选入 PR 核对正文、创建/合并时间、目标分支和状态；#26590 另核对公开补丁。未逐条审计所有候选的评论与提交；PR 当前说明可能包含窗口后的编辑，不以 updated_at 直接认定实质进展。
- [官方博客列表](https://duckdb.org/news/)与新文可读取；[Feed](https://duckdb.org/feed.xml)抓取因 XML 类型支持问题失败。用官网文章和公开源码交叉核验日期，未将 Feed 或文章的日期零点当成精确上线时刻。
- 未访问私人讨论，未全面覆盖独立扩展仓库，也未独立运行 DuckDB 测试或性能基准。
