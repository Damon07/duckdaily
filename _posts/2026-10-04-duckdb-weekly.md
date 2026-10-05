---
title: "DuckDB 周报 · 2026-09-28—2026-10-04：1.5.6 发布与 2.0 接口重构"
date: 2026-10-04 12:00:00 +0800
description: "稳定版修复落地；Mark 推进多文件读取器共用接口，Arrow 结果、类型表示与存储并发继续演进。"
coverage_date: "2026-10-04"
permalink: /weekly/2026/10/04/
---

覆盖窗口：北京时间 **2026-09-28 00:00 至 2026-10-05 00:00，不含终点**，即 9 月 28 日至 10 月 4 日完整自然周。实际来源核查：**2026-10-05 11:18—11:24（Asia/Shanghai）**。下文时间均为北京时间，状态以核查时为准。

## 本周速览

- **已发布：DuckDB 1.5.6。** 稳定线集中交付查询正确性、崩溃和存储恢复修复
- **已合并至 2.0 开发分支：多文件读取与结果输出接口进一步统一。** Mark Raasveldt（Mytherin）的两项 PR 尤其值得跟踪；新增多文件 C API 仍明确标记为 unstable
- **性能与可靠性一起推进。** Arrow 并行转换、类型对象缩小、聚合内存优化都有实质变化，但也存在兼容迁移、内存上限与并发修复等约束

这里的“已合并”不等于“已发布”。除单独标明的 1.5.6 发布内容外，下述开发 PR 均不能据此认定已经包含在稳定版中。

## 1. 稳定版：1.5.6 正式交付，2.0 Windows 性能仍属预览

[GitHub 正式发布记录](https://github.com/duckdb/duckdb/releases/tag/v1.5.6)显示，1.5.6 于 **9 月 28 日 21:35** 发布，非预发布版本。[官方公告](https://duckdb.org/2026/09/28/announcing-duckdb-156)同日上线。

值得优先检查自己的工作负载是否命中这些修复：

- 查询结果：volatile 表达式下推、Top-N 消除中的 NULL 语义、共用子计划与 UNION ALL、超长整数转 HUGEINT
- 文件与恢复：Parquet TIME_NS 和 VARIANT 处理、checkpoint 标记恢复、WAL 恢复时文件句柄处理
- 客户端与扩展：v1 C API 符号版本统一及稳定化

这些是**本周发布事件**，相关修复 PR 不一定都在本周合并，不能将发布清单当成本周新开发清单。完整条目见上述 release notes。

同一公告还展示了 Windows 上 2.0 开发版的 TPC-H SF300 测试：特定机器的热运行总耗时从 822 秒到 129 秒，并说明部分查询仍有回退。这是特定开发版本与测试条件下的官方结果，**不代表所有查询都提速六倍，也不是 2.0 正式发布**。

## 2. Mark 的主线：让不同文件读取器共享基础设施

### Parquet 接入通用多文件包装器

[PR #25987 — Move read_parquet to the multi-file table function wrapper](https://github.com/duckdb/duckdb/pull/25987)，作者 **Mytherin**，**9 月 30 日 20:31 已合并**至 `v2.0-cyanoptera`。

Parquet 的单文件读取由 `read_single_parquet_file` 承担，再通过通用包装器组成 `read_parquet`。schema 参数解析和 file_row_number 等职责进一步移入共享 MultiFileReader；CSV 和 JSON 也能使用这一 schema 入口。PR 特别交代了 DuckLake、Iceberg、Delta 自定义读取路径的兼容处理。

**为何重要：**这不只是换类名，而是在减少文件格式各自重复实现多文件语义，让通用能力和格式读取逻辑分工更清楚。

### 将这套能力开放给扩展

[PR #26254 — WIP: Support creating multi-file reader functions from the v2 C API and the C++ API](https://github.com/duckdb/duckdb/pull/26254)，作者 **Mytherin**，**10 月 2 日 23:58 已合并**至 `v2.0-cyanoptera`。标题仍有 WIP，但实际合并状态为 merged。

扩展可把单文件函数包装为支持文件列表、glob、目录和常见多文件选项的读取器；同时补上字段标识、文件元数据、批次认领以及 COPY 输出统计等接口。**新函数全部标记 unstable**，不能按稳定 ABI 承诺使用。

同方向还有 **pdet** 的 [#26322 — Expose reusable core helpers for DuckLake](https://github.com/duckdb/duckdb/pull/26322)，**10 月 2 日 23:17 已合并**至同一分支：将目录解析、表达式、嵌套类型等内部辅助功能共享出来，减少 DuckLake 复制核心实现的需要。

## 3. 执行与客户端：Arrow 进入统一结果模型

**evertlammerts** 的 [#25727 — Introduce ResultFormat](https://github.com/duckdb/duckdb/pull/25727)于 **9 月 29 日 19:43**合并；[#25801 — Replace Arrow collectors with an ArrowFormat](https://github.com/duckdb/duckdb/pull/25801)于 **10 月 1 日 20:09**合并，均进入 `v2.0-cyanoptera`。

结果格式在提交时确定。Arrow 不再保留一套旁路 collector/结果类，而由生产者工作线程完成转换，和其他结果共同使用缓冲、保留与流式消费模型。这对异步结果接口和批次有序输出很重要。

同时必须看到代价：

- v2 Arrow API 改为单独的 Arrow result handle，调用者需要适配
- batch_size 是**最大值**，并非每批保证达到的固定行数
- 生产者正在构建的 Arrow 数组不计入流式队列上限，因此 `max_streaming_buffer_size` 不能当峰值内存硬上限
- PR 明确列出 Python 客户端迁移需求；本次没有逐一验证所有客户端仓库的适配进度

**Maxxen** 的 [#26355 — Change LogicalType to be an intrusive shared pointer](https://github.com/duckdb/duckdb/pull/26355)于 **10 月 4 日 22:42**合入同一分支。作者报告 LogicalType 从 24 字节缩为 8 字节、Value 从 64 字节缩为 48 字节，并降低 v2 C API 类型句柄的包装成本；序列化保持不变。这里是对象布局数据，不是整体查询性能或数据库文件体积的降幅。

## 4. 内存、优化器与存储：既看收益，也看限制

### 文件缓存：减少过量读取，并保持内容一致

**guillesd** 的 [#26096 — Cache the byte ranges that are read instead of aligned 2 MiB blocks](https://github.com/duckdb/duckdb/pull/26096)，**9 月 29 日 20:42**合入 `v2.0-cyanoptera`。外部文件缓存由固定对齐块改为实际读取的字节区间，减少只扫描部分列时的额外传输与缓存挤出。

**carlopi** 的 [#26267 — Drop all blocks of an external file that changed](https://github.com/duckdb/duckdb/pull/26267)，**10 月 2 日 03:14**合入同一分支，检测文件变化后使该文件所有缓存块失效，避免保留旧内容。两项一起看，更能体现远程扫描既关注 I/O 效率也关注正确性。

### 高基数聚合：降低预分配，同时补齐并发安全

**h4nsmuller** 的 [#26281 — approx_quantile: let the t-digest buffers grow on demand](https://github.com/duckdb/duckdb/pull/26281)，**10 月 1 日 18:59**合并至 `v2.0-cyanoptera`，使每组 t-digest 缓冲区按实际数据增长，缓解大量小分组的内存压力。

同日 **23:25**合并的 [#26333 — never let the digest allocate at finalize time](https://github.com/duckdb/duckdb/pull/26333)修复了该变化暴露的并行 finalize 分配崩溃。两项应作为一个完整进展阅读：按需扩容有价值，但必须把分配放在安全的线程阶段，不能只报道最初的节省。

### 优化器：减少不相关的递归工作，增强计划可观察性

**kryonix** 的 [#26158 — Push join-derived key restrictions into correlation CTEs](https://github.com/duckdb/duckdb/pull/26158)，**10 月 2 日 00:03**合入 `v2.0-cyanoptera`。它把祖先 CTE 的连接键限制传入相关输入，避免内层递归计算无关键分区，同时保留原连接及重复行、NULL 语义，并带有成本和适用范围限制。

同作者的 [#26062 — Export optimized logical plans as executable SQL with EXPLAIN (SQL)](https://github.com/duckdb/duckdb/pull/26062)，**9 月 28 日 16:05**合入同一分支，让受支持的优化后逻辑计划能以 SQL 重新检查或执行。输出依赖相同目录、设置、扩展和外部环境，不是不可变执行快照，也不是覆盖所有语句的稳定序列化协议。

### Checkpoint 并发：进了 main，不能直接算作 2.0 交付

**ywelsch** 的 [#25988 — Let inserts and deletes run while a checkpoint writes their table](https://github.com/duckdb/duckdb/pull/25988)，**10 月 1 日 16:05 已合并至 main**。

它去掉表级 checkpoint 锁，使 checkpoint 写表时 INSERT/DELETE 可以继续，通过快照、新追加行组和共享版本信息协调可见性。**UPDATE 事务仍持有数据库级 checkpoint 锁**，并发能力不能泛化成所有写操作都不再受影响；合并目标也与本周大量 2.0 PR 不同。

另一项关键修复是 **dentiny** 的 [#25931 — Fix uncommitted data recovered accidentally](https://github.com/duckdb/duckdb/pull/25931)，**10 月 2 日 23:39**合入 `v2.0-cyanoptera`。WAL 重放受已刷盘边界约束，并只为已提交行组保留块使用标记，避免故障恢复带回未提交的 optimistic-write 数据。这是数据正确性工作，重要性不应被性能话题盖过。

## 5. 扩展构建：更多选择推迟到链接阶段

**carlopi** 的 [#26188 — Move extension_loader and built-in httplib as opt-in, at link-time, capabilities](https://github.com/duckdb/duckdb/pull/26188)与 [#26189 — Make selection of statically loaded extensions explicit](https://github.com/duckdb/duckdb/pull/26189)，均于 **9 月 30 日 16:32**合入 `v2.0-cyanoptera`。

动态扩展加载、内置 HTTP 能力和静态链接的扩展集合变得更明确，更多选项能在链接时组合。对嵌入式发行版、裁剪构建和离线开发有意义；这些是构建能力变化，不等于现有部署会自动改变安全策略。

## 6. 官网博客：一篇可实践的优化方法，一篇生态观察

### 10 月 2 日：字符串聚合与维度表

[Faster String Aggregations with Dimension Tables](https://duckdb.org/2026/10/02/dimension-tables)，作者 DuckDB Team。

核心方法是把重复长字符串换成窄整数键，先聚合、最后关联回标签，减少字符串散列、比较和复制。这是数据建模与查询实践，不能写成“本周引擎新增自动优化”。

它更适合反复查询、字符串重复较多的场景；短字符串、近乎唯一的列、一次性查询可能不值得改造。整数键不会减少分组总数，高基数并行聚合仍有多份线程局部状态的内存成本。应在自己的数据上测量收益。

### 9 月 29 日：Jev 与自然语言 SQL 条件

[Jev and DuckDB: Plain-English Conditions in SQL](https://duckdb.org/2026/09/29/jev)，作者 Geertjan Wielenga、Gábor Szárnyas。

文章介绍社区扩展如何把自然语言判断映射为布尔、分类和评分，再与 SQL 筛选和聚合组合。重点是扩展生态的尝试，不能当作 DuckDB 核心已经内置模型。

这些扩展会把行内容发送给第三方 API，涉及数据授权和费用；不同实现的批处理、缓存和性能数字也不能直接横比。本周报仅阅读公开材料，没有执行这些示例或调用付费 API。

## 方向观察与下周关注

**以下是基于本周证据的推测，不代表 DuckDB 官方路线图。**

1. **共享基础设施优先于格式各自实现。** Mark 的两项多文件工作、DuckLake 共享辅助功能和扩展构建调整相互呼应，说明降低扩展接入与维护成本是一个明显工程方向。反面约束是新 API 仍 unstable，不能由此推断接口已经冻结
2. **结果传输正在成为执行体系的一部分。** ResultFormat 与 Arrow 重构把异步、线程转换和消费接口连接起来。后续应观察客户端迁移以及构建中数组的内存计量，而不只看吞吐数字
3. **发布前的正确性与边界治理仍很密集。** 1.5.6 的修复交付和开发分支的聚合并发修复说明，性能改进必须连同语义和资源上限一起评估

值得继续观察：多文件 API 的稳定性承诺；Arrow 客户端适配与小结果/峰值内存；checkpoint 对 UPDATE 的后续支持及版本归属。这里列的是尚待验证的结果，不是承诺一定会在下周完成的计划。

## 覆盖与限制

- 本站核查时尚无上周日报，未拼接旧摘要；本篇直接回查公开源
- 检索 duckdb/duckdb 本周合并 PR，分页取回 **125 条**，GitHub 搜索返回 incomplete_results=false；对重点 PR 阅读正文、作者、merged_at 和目标分支，按主题筛选而非穷举所有维护提交
- 同时核查 Mytherin 的本周更新 PR，并核对官方新闻索引中的三篇周内博客及 1.5.6 正式发布记录
- 统计窗口对应 UTC 2026-09-27 16:00 至 2026-10-04 16:00（不含终点），避免把 UTC 日期直接当北京时间
- 未穷尽所有扩展仓库、讨论串和未合并提案，也未复跑作者的性能测试。未发现于本篇不等于社区没有发生
- 博客按官网标注发布日期归入周报；官网页面没有逐篇精确发布时刻，未据此臆造时间
- 来源入口：[DuckDB PR](https://github.com/duckdb/duckdb/pulls)、[官方博客](https://duckdb.org/news/)、[官方发布](https://github.com/duckdb/duckdb/releases)
