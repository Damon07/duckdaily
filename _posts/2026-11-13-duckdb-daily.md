---
title: "DuckDB 日报 · 2026-11-13：预读内存回收、运行时过滤与故障隔离"
date: 2026-11-13 12:00:00 +0800
description: "扫描结束后及时归还预读内存，部分连接可更早获益于运行时过滤；可分离附加库的不可恢复错误不再一律拖累整个实例。"
coverage_date: "2026-11-13"
---

覆盖窗口：北京时间 2026-11-13 00:00 至 2026-11-14 00:00（不含终点），即 UTC 2026-11-12 16:00 至 2026-11-13 16:00。核查时间：北京时间 2026-11-14 09:03:57。

## 今日速览

- 扫描耗尽时立即归还预读内存预留，减少后续连接和聚合不必要的落盘。
- 小构建端的运行时过滤器可赶在目标扫描开始前生效；部分绑定器插入的数值转换不再挡住统计过滤。
- 可分离附加库发生特定不可恢复错误时，可以只隔离该库，而不是让整个实例失效。

## 重点 PR

下列合并时间均为北京时间；合入分支不等于稳定版已发布。

- **预读内存回收。** [#28687](https://github.com/duckdb/duckdb/pull/28687)，**anhphanmd**，06:12 合入 `main`。扫描耗尽时归还预留，后续算子不用等整个查询结束才拿回预算；`LIMIT` 提前停止仍在析构时归还。这是预算生命周期修复，不是替换 I/O 线程池。
- **让运行时过滤赶上扫描。** [#28768](https://github.com/duckdb/duckdb/pull/28768)，**smvv**，19:34 合入 `main`。在保留循环依赖和大小约束的前提下，允许某些已带过滤条件或用于嵌套构建的扫描等小构建端发布过滤器，减少同一执行计划的中间结果波动。[#28717](https://github.com/duckdb/duckdb/pull/28717)，**oraclechang**，00:15 合入 `main`；允许统计传播穿过安全可逆的数值转换，派生扫描过滤而不删除原连接谓词。
- **降低聚合和流式输出的资源开销。** [#28646](https://github.com/duckdb/duckdb/pull/28646)，**DinosL**，05:33 合入 `main`。针对没有落盘方案的聚合状态调整策略，避免哈希表在每个数据块反复放弃并重建状态，缓解内存增长；不保证所有低内存查询都能完成。[#28781](https://github.com/duckdb/duckdb/pull/28781)，**h4nsmuller**，18:59 合入 `main`；并行流式消费者帮忙生产时一次只处理一个数据块，尽快返回消费缓冲区，避免生产者长时间等腾空。
- **隔离可分离附加库的致命错误。** [#28650](https://github.com/duckdb/duckdb/pull/28650)，**Robinho-MR**，00:35 合入 `main`。可明确归因到单个附加库的不可恢复错误（如其 WAL 同步失败）可只使该库失效，其他库仍可用；可尝试分离并重新附加恢复。初始库、系统库和临时库不适用这种隔离。
- **NUMA 后续优化。** [#28748](https://github.com/duckdb/duckdb/pull/28748)，**lnkuiper**，03:31 合入 `main`。让 Linux 看见独立的分片虚拟内存区域，减少并发首次触页时的争用，避免影响 NUMA 放置。
- **扩展兼容。** [#28349](https://github.com/duckdb/duckdb/pull/28349)，**staticlibs**，16:14 合入 `main`，更新 PostgreSQL、MySQL 和 SQLite 扫描器；其维护分支回移另走 PR，不能按该主线合并认定稳定版已更新。

### 新提案及评审进展

- [#28815 统一普通和完美哈希连接路径](https://github.com/duckdb/duckdb/pull/28815) · **lnkuiper** · 22:44 新建、开放。拟共享输出及字典处理，给 `RIGHT_SEMI`/`RIGHT_ANTI` 增加位图查找，减少重复实现。
- [#28817 让阻塞等待遵守执行时限](https://github.com/duckdb/duckdb/pull/28817) · **JelteF** · 23:23 新建、开放。拟让 glob 展开、异步打开文件等路径及时检查 `max_execution_time`，而非只在常规执行点检查。
- [#28664 用抽样估计连接过滤选择率](https://github.com/duckdb/duckdb/pull/28664) · **oraclechang** · 仍开放。19:35，lnkuiper 在[评审](https://github.com/duckdb/duckdb/pull/28664#issuecomment-6851662820)给出替代实现，建议先限于原生存储，遇低内存时回退到启发式估计。额外规划 I/O 的成本仍需验证。
- [#28782 先过滤再物化部分字符串](https://github.com/duckdb/duckdb/pull/28782) · **YimingQiao** · 14:25 新建、仍为草稿。Mytherin 16:48 [建议](https://github.com/duckdb/duckdb/pull/28782#discussion_r4561357607)把逻辑放到未压缩字符串的 segment 层，方案位置尚未定。
- [#28784 流式窗口融合](https://github.com/duckdb/duckdb/pull/28784) · **hawkfish** · 16:44 新建、仍开放。拟在流式窗口内融合过滤和提前停止；lnkuiper [评审](https://github.com/duckdb/duckdb/pull/28784#issuecomment-6856769788)指出共享物化 CTE 可能被提早截断，属于待解决的问题。

## 官方博客与发布

[官网新闻](https://duckdb.org/news/) 与 [Atom](https://duckdb.org/feed.xml) 均未见窗口内新文；最新列表文章仍为 11 月 12 日发布的 [Local Analytics Doesn’t Need a Database Server](https://duckdb.org/2026/11/12/local-analytics-without-a-database-server)。[官方 Releases](https://github.com/duckdb/duckdb/releases) 未见窗口内新的稳定版。

## 方向观察（推测）

[#28687](https://github.com/duckdb/duckdb/pull/28687) 和 [#28781](https://github.com/duckdb/duckdb/pull/28781) 都针对资源已经就绪或可归还、却仍需等待的问题：一个让出内存配额，一个缩短结果消费者参与生产的时间片。它们提示在现有并行架构下，改善资源释放时机也能减少落盘或停顿；并不说明会改变底层 I/O 后端，更不是官方路线图。

## 覆盖与限制

通过 [DuckDB PR](https://github.com/duckdb/duckdb/pulls) 筛查窗口内新建、合并和最近更新的候选，类别重叠；回查重点详情与部分讨论。更新时间可能被后续活动覆盖，单凭时间戳不判定实质进展，评论和评审不保证全量。检索返回 48 个新建、35 个合并、86 个最近更新时间落在窗口的候选。本文为精选，不覆盖每条修复或回移。
