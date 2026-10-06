---
title: "DuckDB 日报 · 2026-10-05：并发 checkpoint 的安全边界与解析器提速"
date: 2026-10-05 12:00:00 +0800
description: "Mark 的评审拦下并发 checkpoint 提案中的数据丢失风险；PEG 提速仍在提案阶段，事务内扫描并行化和窗口优化已合并。"
coverage_date: "2026-10-05"
---

覆盖窗口：北京时间 **2026-10-05 00:00 至 2026-10-06 00:00，不含终点**，对应 UTC 10 月 4 日 16:00 至 10 月 5 日 16:00。实际核查时间：**2026-10-06 08:58—09:01（Asia/Shanghai）**。下文事件时间均为北京时间；状态以核查时为准。

## 今日速览

- **并发 checkpoint 继续扩展，但正确性先行。** Mark Raasveldt（Mytherin）在评审中发现新提案的并发竞态，作者随后收窄支持范围；相关两项提案仍未合并
- **优化覆盖解析、窗口和事务内扫描。** PEG FIRST-set 提速尚在评审；窗口属性化简、事务本地数据的扫描并行度修正已合并
- **官网新文章讲 Java 数据导入。** 从 JDBC 批量 INSERT、Appender 到 Java 表函数，重点是减少逐行开销和适配实际资源约束

“已合并”不等于稳定版已包含。核查[官方发布记录](https://github.com/duckdb/duckdb/releases)时最新正式版仍为 9 月 28 日发布的 1.5.6；以下开发进展不能据此认定已正式发布。

## 重要 PR

### 1. Mark 的重点评审：并发 checkpoint 不能牺牲已提交数据

[PR #26456 — Let DDL that keeps table storage, and sequences, run alongside checkpoints](https://github.com/duckdb/duckdb/pull/26456)，作者 **ywelsch**，10 月 5 日 **15:56 新建**，目前 **open**，目标分支 main。

提案让不替换表存储的 DDL、nextval/setval 与 checkpoint 并行，缓解长事务阻塞 checkpoint、WAL 持续增长的问题。**20:23，Mytherin 的[评审](https://github.com/duckdb/duckdb/pull/26456#issuecomment-5994374368)指出提案原实现中 SET NOT NULL 与 checkpoint/并发插入的竞态，可导致崩溃或丢失已提交批次。22:13，[作者确认复现并提交修正](https://github.com/duckdb/duckdb/pull/26456#issuecomment-5996257607)，将 SET NOT NULL 排除在并发支持之外。**

这是**待合并提案中发现的问题**，不是本文确认的稳定版缺陷。Mark 在这里是评审者，不能写成该 PR 的作者。

同一作者的 [#26478 — Let checkpoints run alongside UPDATE transactions](https://github.com/duckdb/duckdb/pull/26478) 于 **20:22 新建**，目前 **open**、目标 main。它进一步处理更新版本可见性、旧快照、NULL 值及统计信息交接，目标是允许 UPDATE 事务与 checkpoint 共存。两项工作都值得观察，但尚不能作为可直接使用的新能力。

### 2. PEG FIRST-set 剪枝：作者报告解析时间中位数约减半

[PR #26451 — PEG matcher: skip sub-matchers that cannot start at the current token (FIRST set)](https://github.com/duckdb/duckdb/pull/26451)，作者 **carlopi**，**13:17 新建**，目前 **open**，目标 v2.0-cyanoptera。

预先计算匹配器可能接受的起始 token，跳过必然失败的子匹配，减少解析栈工作。作者报告测试语料的单语句解析时间中位数从 **65.7 μs 降至 29.8 μs，约 2.2 倍提速**，并在 317,769 个输入上核对语句及错误输出一致。这是**作者的解析器微基准，未独立复测**，不代表 SQL 端到端执行统一提速，也尚未合并。

### 3. 已合并：窗口化简与事务内表扫描并行化

- [#26298 — Window Attribute Reductions](https://github.com/duckdb/duckdb/pull/26298)，**hawkfish**；**14:21 merged → main**。利用唯一键和函数依赖删去窗口 PARTITION BY / ORDER BY 中的冗余表达式，减少不必要的分区和排序属性；PR 未提供可泛化的性能数字
- [#26383 — Count transaction-local rows when sizing a table scan](https://github.com/duckdb/duckdb/pull/26383)，**ywelsch**；**16:14 由 Mytherin 合并 → v2.0-cyanoptera**。扫描线程数以前只看已提交行，事务中新建的 staging 表可能因此单线程扫描；现在将事务本地行计入估算。它直接回应 dbt 增量物化中的性能问题

两项 PR 都是较早创建、**当天合并**，不是当天新建。

### 4. 延迟唯一约束：有实质评审，尚未落地

[#26423 — 延迟 PRIMARY KEY / UNIQUE 约束](https://github.com/duckdb/duckdb/pull/26423)，作者 **artjomPlaunov**，此前创建，目前 **open**。提案允许事务内部暂时违反唯一性、在 COMMIT 前修复；主键 NOT NULL 仍即时检查，延迟键也有外键引用和 ON CONFLICT 限制。

**18:39，Mytherin 的[评审](https://github.com/duckdb/duckdb/pull/26423#pullrequestreview-5413197393)提出约束检查模式及命名调整，作者于 20:37 回应。**这是设计与接口层面的推进；评审状态为 COMMENTED，不能写成已批准、已合并或正式支持。

### 5. 正确性与扩展兼容性：三个已合并的小切口

- [#26440 — 共用子计划优化器修复](https://github.com/duckdb/duckdb/pull/26440)，**alonfaraj**；**21:55 由 Mytherin 合并 → v2.0-cyanoptera**。嵌套重复子计划转成 CTE 时重新检查可用列，跳过不安全转换，避免优化器崩溃
- [#25592 — checkpoint 保留负零符号](https://github.com/duckdb/duckdb/pull/25592)，**asxvi**；**22:38 merged → v2.0-cyanoptera**。避免把混合 -0.0 / +0.0 的浮点段误判为常量，修复 checkpoint 后符号丢失
- [#26412 — 无 bind data 时的 read-ahead 支持](https://github.com/duckdb/duckdb/pull/26412)，**Tishj**；**18:04 merged → v2.0-cyanoptera**。为 Iceberg 等扩展的预读路径提供兼容支持

## 官方新博客

[Importing Data using Java Table Functions](https://duckdb.org/2026/10/05/import-data-with-java.html)，官网署名 **Guest Author、Geertjan Wielenga、Alex Kasko**，发布日期 **2026-10-05**；[官方 feed](https://duckdb.org/feed.xml)记录为 UTC 00:00，即北京时间 08:00，落在本期窗口内。

文章以 MongoDB 分析数据导入为例，对比 JDBC 批量 INSERT、Java Appender 与 Java 表函数。表函数让 DuckDB 按数据块拉取数据，减少逐行插入开销，并能配合并行扫描；但示例的并行导入需要不保留插入顺序，排序、中间副本与磁盘空间也会影响最终方案。实践价值在于：Java 团队可以沿用自己的数据源代码构建导入管道，**应在自己的数据与资源约束下比较方案，不能把案例计时当成通用保证**。这是应用案例文章，不是当天发布新版本的公告。

## 方向观察（推测）

这些 PR 共同呈现两条主线：一是补齐性能边角，让新解析器、窗口优化及事务内扫描减少多余工作；二是拓宽 checkpoint 的并发范围，但通过版本可见性和压力测试守住正确性。Mark 对 #26456 的评审尤其说明，支持更多并发操作仍受明确的安全边界约束。

这只是对本期公开活动的归纳，**不是官方路线图**。解析器提速和并发 checkpoint 都还有未合并提案；不同 PR 也面向不同分支，不能推断它们会在同一正式版本交付。

## 覆盖与限制

- 检索官方 duckdb/duckdb PR 的 updated-since 候选，读取两页共 147 项（包含窗口之后的更新，以避免漏掉旧 PR 的后续活动），搜索返回 incomplete_results=false；按创建、合并、讨论时间筛选本期事件
- 核对重点 PR 的详情、24 个窗口内合并及 33 个 Mytherin 参与候选的讨论时间线；这不是对全部 PR 每条提交和行内评论的穷尽审计。没有发现本次检索范围内 Mytherin 本人新建的 PR，本文按评审和合并贡献呈现
- 官网新闻列表、原文、Atom feed 均已读取。部分网页读取工具无法解析 feed/原文后，改用公开站点直接读取完成核实；未将读取失败当成“没有更新”
- PR 当前正文可能含窗口结束后的编辑；纳入本期的具体事件已按时间戳核对。性能数字只保留作者明确报告的数据，未运行基准或验证全部修复
