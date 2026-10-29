---
title: "DuckDB 日报 · 2026-10-28：事务可见性修复、绑定器重构与执行热路径优化"
date: 2026-10-28 12:00:00 +0800
description: "批量写入事务隔离修复、函数重载绑定统一、扩展预绑定钩子，以及扫描、聚合和文件格式兼容性进展。"
coverage_date: "2026-10-28"
---

## 范围与速览

- **覆盖北京时间 2026-10-28 00:00–2026-10-29 00:00，不含终点**；对应 UTC 2026-10-27 16:00–2026-10-28 16:00。
- **实际检查时间：2026-10-29 09:04 +0800**。下文时间均为北京时间。“已合并”仅指开发分支，不代表稳定版已经包含修复；窗口外的后续状态另行注明。

今日重点：

1. 批量插入的事务可见性、提交失败回滚，以及 JSON/Parquet 精度和兼容性问题得到修复。
2. 函数重载选择与绑定结果统一；扩展获得绑定前钩子；部分块管理走向统一接口。
3. 扫描、过滤、解析和写出多个热路径继续优化；另有紧凑向量写 Parquet、JSON 多文件内存与模式变更写入方案待合并。

## 正确性与兼容性：优先看这些已合并修复

### 批量插入：提交前不可见，失败后清理残留

[Keep bulk insert rows invisible until commit and revert failed appends during commit · #27764](https://github.com/duckdb/duckdb/pull/27764) — **Robinho-MR；16:39 合并**。

批量/并行插入不再让新行以未版本化的插入标识提前暴露，而是保留插入事务 ID，避免提交过程中破坏快照隔离。提交追加失败时，清理部分写入的行、索引及新行组等状态，防止失败事务留下不一致的内存状态。它同时涉及“其他事务何时能看见数据”和“失败能否恢复”，比单纯加速写入更基础。

### JSON DECIMAL 与 Parquet 互操作

- [JSON: read a DECIMAL column from the number's text, not through a double · #27577](https://github.com/duckdb/duckdb/pull/27577) — **xiaoxuandev；06:13 合并**。目标含 DECIMAL 时直接从 JSON 数字文本转换，避免先过 double 丢失有效数字或改变舍入；其他类型仍保持原有转换语义。
- [Fix encrypted Parquet DataPageV2, interval bloom filters and union_by_name BLOB · #27766](https://github.com/duckdb/duckdb/pull/27766) — **Robinho-MR；06:54 合并**。修正加密 DataPageV2 页面读取、边界 interval 的 Bloom filter 兼容性，以及 union_by_name 将 VARCHAR 合并为 BLOB 时误解释转义序列的问题。意义分别是跨实现可读性、避免错误过滤及字节内容保真。

### 聚合状态与边界

- [Issue #27801: Sorted Aggregate Batching · #27978](https://github.com/duckdb/duckdb/pull/27978) — **hawkfish；15:07 合并**。分批完成有序聚合，确保每批组编号处于 16 位编号边界内，避免大量分组时溢出；补充窗口分位数等测试。
- [Preserve thread caps at the sink and aggregate states across repeated finalization · #27770](https://github.com/duckdb/duckdb/pull/27770) — **kryonix；18:41 合并**。sink 的线程上限不再覆盖更严格的上游限制；MinMaxN 和 BIGNUM 的结果输出不再破坏仍可能继续更新的聚合状态，修复递归 USING KEY 等重复 finalize 场景。

## 绑定器、扩展与存储接口

- [Unify function overload selection and improve function binding errors · #27703](https://github.com/duckdb/duckdb/pull/27703) — **Maxxen；07:45 合并**。统一保存选中的函数定义、类型推导结果和参数映射，供后续绑定复用；将模板推导纳入重载选择，允许候选失败后继续尝试，并改进命名参数、默认参数和候选失败的错误信息。这是减少多条绑定路径不一致的结构性改动。
- [Add A Pre-Bind Hook To PlannerExtension · #27872](https://github.com/duckdb/duckdb/pull/27872) — **Richard-Durkee；04:33 合并**。新增绑定 SQLStatement 前的扩展回调，为 Iceberg 等扩展预先加载远端元数据提供入口；**不是核心已实现通用目录批量预取**。Mark Raasveldt（Mytherin）在此前的[设计讨论](https://github.com/duckdb/duckdb/pull/27872#issuecomment-6415467210)指出直接遍历解析树处理 CTE/视图的局限，建议先将相关逻辑放入扩展钩子；该评论发生于 10 月 26 日，今日进展是最终钩子合并。
- [Unify PartialBlock management · #27305](https://github.com/duckdb/duckdb/pull/27305) — **sebastiaan-dev；22:30 合并**。以 BlockPackable 接口统一部分块分配、登记和落盘位置回调，替代索引、检查点等专用分支。它简化了块打包管理，但**本次并未实现将列段与索引缓冲区混装进同一块**。

## 执行与数据管线：减少重复工作

- [More hot loop optimisations · #27960](https://github.com/duckdb/duckdb/pull/27960) — **lnkuiper；13:45 合并**。涉及大 Bloom filter 探测预取、按 validity word 选择 NULL、字符串搜索、压缩回调和窗口 segment tree 叶节点批处理等多处热路径。没有据此推导所有查询的统一加速比例。
- [Read-ahead: prune row groups a late Top-N boundary excludes… · #27227](https://github.com/duckdb/duckdb/pull/27227) — **h4nsmuller；17:37 合并**。对已准备的原生行组在解码前再次检查晚到的 Top-N 边界，并完善 Parquet 动态过滤识别及 read-ahead 预算日志。收益主要是少解码、少下游处理；已经发出的预读 I/O 并不会被追回。
- [Merge OR Select Results Instead Of Sorting Them · #27974](https://github.com/duckdb/duckdb/pull/27974) — **Richard-Durkee；18:24 合并**。合并已排序的 OR 条件选择结果，代替拼接后整体排序；必要时仍对嵌套 AND 的结果排序，减少过滤过程的额外工作。
- [StatisticsPropagator: Convert COMPARE_(NOT_)DISTINCT_FROM to COMPARE_(NOT)EQUAL · #27945](https://github.com/duckdb/duckdb/pull/27945) — **lnkuiper；02:37 合并**。仅在非空统计与具体上下文证明安全时，将空值安全比较简化为普通比较；并非无条件改写，MARK join 等场景保留保护。
- [Parser performance 5/N · #27874](https://github.com/duckdb/duckdb/pull/27874) — **Dtenwolde；23:10 合并**。预处理可折叠列表组、内联部分选择路径并减少解析框架/分配开销，针对解析阶段优化；不能把解析器微基准提升等同于整条 SQL 的执行加速。
- [Size partitioned COPY batches from the written columns · #27943](https://github.com/duckdb/duckdb/pull/27943) — **kryonix；23:51 合并**。按照实际写出列估算分区 COPY 批次大小，排除未写出的分区键及不应计入的开销，避免批次过早刷新。

## 当日提出、仍需观察

以下是提案，不当作已发布功能：

- [Write constant and dictionary vectors to Parquet without flattening · #27990](https://github.com/duckdb/duckdb/pull/27990) — **kryonix；14:59 新建，检查时开放**。让普通标量列写出路径利用 constant/dictionary 向量，减少物化和重复字典探测；部分特殊类型与准备阶段仍走平坦路径。
- [Fix OOM in read_json with union_by_name over many files · #28005](https://github.com/duckdb/duckdb/pull/28005) — **DinosL；17:28 新建，检查时开放**。模式采样结束后释放读缓冲区，针对大量文件各自保留默认 32 MiB 缓冲区造成的内存压力。
- [Use optimistic and parallel writes for ADD COLUMN and ALTER TYPE · #27989](https://github.com/duckdb/duckdb/pull/27989) — **ywelsch；14:41 新建，检查时开放**。尝试按行组进行乐观落盘和并行处理，并配套回滚清理与冲突检查；不能只按作者基准断言所有模式变更都会加速。
- [Better cardinality estimation for SEMI/ANTI joins and GROUP BY · #28013](https://github.com/duckdb/duckdb/pull/28013) — **lnkuiper；18:58 新建**。利用当前值域改善相关基数估算。**覆盖日结束时尚未合并；检查时已于 10 月 29 日 00:08 合并，属于窗口外后续状态**，不计入 28 日已合并条目。

## 官网文章与正式发布

[官网新闻列表](https://duckdb.org/news/)中未发现日期为 10 月 28 日的新文章；列表最新文章为 **10 月 26 日**的 *Gems of DuckDB 2.0.0*，不重复算作本日新文。

[官方发布记录](https://github.com/duckdb/duckdb/releases)核对到最新正式版为 **10 月 21 日发布的 v2.0.0**；上述合并不能据此宣称已进入稳定版。

## 基于证据的方向观察（推断）

函数绑定结果复用、部分块接口统一和扩展预绑定钩子，显示本日合并在减少内部重复逻辑并为扩展提供明确接入点；这是根据代码变更做出的推断，不是官方路线图。热循环、OR 选择合并、晚到边界过滤及 COPY 批次估算共同指向减少重复计算和无效数据处理；同时，事务可见性及格式修复说明正确性仍是不可跳过的一条主线。开放 PR 的方案与性能结论仍可能随审查改变。

## 核实方法与覆盖局限

通过 GitHub 公开 API 分两页读取自窗口起点以来更新的 **154 条 PR 候选**（搜索未标记结果不完整），并独立查询窗口内 **30 条合并记录**；按创建/合并实际时间筛选，避免以检查时的 updated_at 误判事件日期。对本文重点 PR 读取详情与最终文件差异；对 pre-bind 设计背景另读讨论。优先关注 Mytherin 及其他核心贡献者，同时按影响选取其他作者工作，不将仅标签、机器人或无实质内容的更新凑入日报。

本稿是重要事项筛选，不是全部 PR 清单，也未遍历全部候选的所有评论，因此可能遗漏仅发生于讨论中的实质进展。官网新闻页可读，但 RSS 在网页读取端失败、独立 HTTP 请求返回 403，博客结论限于可核实的新闻列表；没有把读取失败当作零更新。未在本次任务重跑 PR 测试或复现作者性能基准。
