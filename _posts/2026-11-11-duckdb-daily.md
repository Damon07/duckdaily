---
title: "DuckDB 日报 · 2026-11-11：NUMA 扩展性与正确性护栏"
date: 2026-11-11 12:00:00 +0800
description: "NUMA、任务队列与聚合域优化合并，同时补齐持久化、并行聚合和外部访问边界；采样基数估计仍在讨论。"
coverage_date: "2026-11-11"
---

覆盖时间：北京时间 2026 年 11 月 11 日 00:00 至 11 月 12 日 00:00（左闭右开），即 UTC 11 月 10 日 16:00 至 11 月 11 日 16:00。实际检查时间：北京时间 2026 年 11 月 12 日 09:06。下文事件时间均为北京时间，状态为核查时状态。

## 今日速览

- NUMA、任务队列与聚合域优化继续合并，但 Windows 32 位原子读取问题提醒我们：高核收益必须与跨平台正确性一起验证。
- 缓冲区残留数据写盘、失败 COMMIT、并行聚合状态共享等修复，覆盖持久化和查询结果正确性。
- 外部访问禁用时的 ATTACH 与 CREATE SECRET 检查已合并；采样式基数估计、NUMA 分片分配器等仍是未合并提案。

## 重点 PR

### 1. NUMA 与并行执行：收益和跨架构代价一起看

- [#28622 More NUMA improvements](https://github.com/duckdb/duckdb/pull/28622)，作者 **lnkuiper**，**01:08 合并至 main（merged）**：减少 shared ownership/refcount 开销，调整 dictionary/vector buffer 的所有权流转及 hash build 并行化。作者在 192 线程 Graviton4 上的 TPC-H SF100 实验中报告总耗时约下降 15%；这是特定机器与负载的结果，不是普遍收益。
- [#28682 修复窄指针平台的原子读取](https://github.com/duckdb/duckdb/pull/28682)，作者 **h4nsmuller**，**18:19 新建，当前 open**：前述并行 hash build 门槛降低，暴露 Windows 32 位 clang-cl 将 8 字节原子 load 拆成两次 32 位读取、导致 join 丢行的问题。提案改用 CAS 读取，仍需以 Windows 32 位 CI 验证，不能当作已经解决。
- [#28674 更新 concurrentqueue 并减少 false sharing](https://github.com/duckdb/duckdb/pull/28674)，作者 **lnkuiper**，**20:35 合并至 main（merged）**：升级至 v1.0.5 并调整 padding。作者微基准最高 2.55 倍不等于 SQL 整体提速；其 TPC-H 总体改善仅约 0.3%。
- [#28707 BlockAllocator NUMA 分片](https://github.com/duckdb/duckdb/pull/28707)，作者 **lnkuiper**，**23:58 新建，当前 open**：继续改善高核机器的内存分配局部性。作者报告特定高核 Q18 约 10% 改善，尚未合并。

### 2. 持久化：防止残留数据写盘与失败事务继续运行

以下均为 **merged 至 main**：

- [#28475 Fix buffer to disk leaks](https://github.com/duckdb/duckdb/pull/28475)，**sebastiaan-dev，00:08 合并**：清零复用缓冲区的 header padding、字符串间隙、ART/ZSTD 尾部、overflow links 及 checkpoint 未写区域。这里的“leaks”指残留字节被写入磁盘，不是内存用量泄漏。
- [#27334 COMMIT 无法完整回滚时使数据库失效](https://github.com/duckdb/duckdb/pull/27334)，**artjomPlaunov，02:39 合并**：提交在部分 flush 后失败，若不能完整 undo，就使数据库失效，防止继续使用或通过 checkpoint 将不一致状态进一步持久化。
- [#28624 持久化索引表达式重新绑定时补齐验证](https://github.com/duckdb/duckdb/pull/28624)，**HendrikLambert，00:25 合并**：采用 CREATE INDEX 级别的验证，拒绝 volatile、会话相关及 lambda 表达式，也覆盖 WAL replay 路径，避免恢复时绕过建索引约束。

### 3. 查询正确性：聚合状态与异常表达式的边界

以下均为 **merged 至 main**：

- [#28315 修复并行聚合状态共享](https://github.com/duckdb/duckdb/pull/28315)，**DinosL，18:47 合并**：复用聚合行时，跨 finalize 线程共享非线程安全 Arena 会损坏 histogram、mode、entropy 的字符串 key。修复在 GroupedAggregateHashTable::Combine 中统一初始化目标状态，并合并、销毁源状态。
- [#28573 不把可能抛错的聚合参数推到过滤 join 之前](https://github.com/duckdb/duckdb/pull/28573)，**h4nsmuller，02:20 合并**：避免在原本应被连接过滤的行上提前计算参数、产生错误。
- [#28641 限制可能抛错的 struct cast 下推](https://github.com/duckdb/duckdb/pull/28641)，**alonfaraj，02:00 合并**：避免原本会被过滤的脏值因转换提前执行而导致查询失败。

这些修复强调：优化不能仅保留正常输入的结果，还要尊重异常表达式的执行边界。

### 4. 外部输入与访问权限

- [#28654 完善 Parquet 输入校验](https://github.com/duckdb/duckdb/pull/28654)，作者 **HendrikLambert**，**17:42 合并至 main（merged）**：覆盖 boolean PLAIN 边界、DELTA_BYTE_ARRAY 类型、VARIANT null metadata 与列数校验，将相应内部错误转为数据损坏错误。**Mark Raasveldt（Mytherin）**在当日讨论中参与反馈；该 PR 的作者不是 Mytherin。
- [#28635 禁用外部访问时拒绝 ATTACH EXTERNAL RESOURCE](https://github.com/duckdb/duckdb/pull/28635)与 [#28637 禁用外部访问时拒绝 CREATE SECRET](https://github.com/duckdb/duckdb/pull/28637)，作者均为 **h4nsmuller**，分别于 **00:44、16:25 合并至 main（merged）**，补齐 `enable_external_access=false` 的入口检查。
- [#28684 远程路径与 secret scope 边界加固](https://github.com/duckdb/duckdb/pull/28684)，作者 **HendrikLambert**，**18:29 新建，当前 open**，**carlopi** 当日参与评审。涉及远程路径编码穿越及 host/bucket scope 边界，仍是未合并方案。

以上是公开 PR 中的防御性修复，不能据此推定已有安全公告或 CVE。

### 5. 优化器与宽表读取

- [#28649 改进 duplicate-eliminated domain 优化](https://github.com/duckdb/duckdb/pull/28649)，作者 **lnkuiper**，**18:04 合并至 main（merged）**：避免无谓的 CTE 物化，传播最大基数与 accumulator bounds，改善特定相关子查询、递归聚合，不代表所有查询都会加速。
- [#28638 多文件统计使用列名 hash index](https://github.com/duckdb/duckdb/pull/28638)，作者 **h4nsmuller**，**16:26 合并至 v2.0-cyanoptera（merged）**，不是 main，也不等于正式版已经发布。减少宽表 `union_by_name` Parquet 读取中按列、文件反复遍历的成本，并保留不区分大小写及首个重复列的语义。

## 值得继续观察的提案

- [#28664 通过采样估计 filter selectivity](https://github.com/duckdb/duckdb/pull/28664)，作者 **oraclechang**，**06:33 新建，当前 open**：为 join ordering 引入确定性/分层行采样，默认 2048 个样本，并限制 row group 扫描以控制冷 I/O，跳过 volatile 或会失败的表达式。作者 TPC-DS SF3000 总耗时下降 46.1%，但主要由 Q23 驱动；排除 Q23/Q78 后反而增加 0.6%。[lnkuiper 当日评审](https://github.com/duckdb/duckdb/pull/28664#issuecomment-6798065182)明确指出，更准确的估计仍可能产生更差计划，目前尚需工作才能合并。
- [#28702 修复 prepared PhysicalExecute 的属性传递](https://github.com/duckdb/duckdb/pull/28702)，作者 **nicholasjng**，**23:18 新建，当前 open**：向下查找 sources/order properties，处理单线程 Arrow result collection 及 `preserve_insertion_order=false` 时丢失 ORDER BY 属性的问题，尚未合并。

## 官方文章

核对[官网新闻列表](https://duckdb.org/news/)与[官方博客源码目录](https://github.com/duckdb/duckdb-web/tree/main/_posts)，**未发现标注发布日期为 2026-11-11 的新文章**。标注 11 月 12 日的文章不计入本期。

[官方 feed](https://duckdb.org/feed.xml)未能读取：抓取工具不支持该 XML 内容，直接请求返回 403。官网日期也没有精确发布时间，因此不能严格排除某篇文章的实际上线时刻落入本期北京时间窗口；这里报告的是已核实的官网标注日期，不把访问失败解释为零更新。

## 基于证据的方向观察

**推测：** #28622、#28674 和 #28707 显示高核扩展性继续深入到引用计数、任务队列和内存局部性；但 #28682 表明跨架构正确性验证必须同步跟进。#28649、#28664 的更积极优化，与 #28573、#28641 的异常语义护栏并行。缓冲区清零、失败 COMMIT 和 Parquet 校验则显示持久化与外部输入防御仍在推进。

这些判断只来自本期 PR 集合及公开评审，不是官方路线图。性能数据均由作者报告，收益与代价取决于机器、数据及查询形态。

## 覆盖与限制

- 仅使用公开 DuckDB 社区资料。按精确 UTC 窗口查询：updated 命中 95 项、created 命中 56 项、merged 命中 31 项；每组每页 100 项，单页完整返回且 incomplete_results=false。集合重叠，不能相加；联合去重得到 112 个候选。
- 读取 22 项以上重点 PR 的详情，并按评论创建时间核对关键讨论；文章是按重要性精选，不是所有 PR 清单。优先检查 Mytherin 及核心贡献者，同时纳入其他作者的重要工作。
- updated 检索使用当前最后更新时间，可能遗漏窗口内互动、但之后再次更新的旧 open PR。PR 正文也可能在窗口后编辑，不能视为全部历史事件的穷尽快照。
- 未运行 DuckDB、复测作者基准或逐项审计代码；未读取公开 PR 引用的内部 issue。官方 feed 的限制见上文。
- **已合并不等于稳定版已发布或可用。** main 与 v2.0-cyanoptera 的目标分支已分别注明；open 项目均为提案。
