---
title: "DuckDB 日报 · 2026-11-18：原生扫描引入 NUMA 亲和，2.0 维护分支修复错算"
date: 2026-11-18 12:00:00 +0800
description: "原生表扫描就近调度，溢写哈希连接扩展多键运行时过滤；2.0 维护分支修复共享 CTE 中的计数错误。"
coverage_date: "2026-11-18"
---

覆盖窗口：北京时间 2026-11-18 00:00 至 2026-11-19 00:00（左闭右开；UTC 11-17 16:00 至 11-18 16:00）。实际核查时间：北京时间 2026-11-19 09:06 左右。

## 今日速览

- 原生表扫描优先把可运行任务交给靠近缓存块的 worker，负载不均时仍允许工作窃取。
- 复合键哈希连接溢写后也能构建逐键运行时过滤器；Bloom 过滤器的清零可以并行完成。
- 2.0 维护分支修复了共享 CTE 与两个 LEFT JOIN 组合下的错算；尚未验证 2.0.1 正式发布。

## 重要 PR

- [#28865 · 原生扫描的 NUMA 亲和调度](https://github.com/duckdb/duckdb/pull/28865)（lnkuiper，窗口内合并至主线）：已就绪的原生扫描任务优先分配给靠近缓存块的 worker，并复用扫描状态。此机制独立于异步预读；作者的双 NUMA 节点热跑结果有升有降，不能外推到 Parquet 或所有负载。
- [#28789 · 多键哈希连接溢写时逐键构建过滤器](https://github.com/duckdb/duckdb/pull/28789)（h4nsmuller，窗口内合并至主线）：满足现有启用条件的复合等值键连接，即使 build side 放不进内存，也能使用逐键 Bloom 或前缀范围过滤器，而不只依靠 min/max。[#29012](https://github.com/duckdb/duckdb/pull/29012)（lnkuiper，同日合并至主线）则复用前缀范围过滤器的构建缓冲区，并并行清零 Bloom 过滤器，减少大过滤器的初始化开销。
- [#29019 · 回移运行时过滤器的行映射修复](https://github.com/duckdb/duckdb/pull/29019)（lnkuiper，窗口内合并至 2.0 维护分支）：过滤结果与输入共用选择向量时，避免覆盖后续仍需使用的行索引。共享 CTE、两个 LEFT JOIN 的回归中，一组计数曾从 5 错成 1；[原报告](https://github.com/duckdb/duckdb/issues/29014)使用的是开发构建，不是已发布的 2.0.1。[官方日历](https://duckdb.org/release_calendar)暂列 11 月 19 日，核查时 GitHub Release 和 PyPI 均未验证到正式版本。
- [#28876 · 简化部分关联 COUNT 子查询](https://github.com/duckdb/duckdb/pull/28876) 与 [#28796 · 简化只依赖左侧行的 lateral UNNEST](https://github.com/duckdb/duckdb/pull/28796)（均为 h4nsmuller，窗口内合并至主线）：前者让符合条件的外侧直接连接分组聚合，后者把合资格的展开改为逐行 UNNEST。两者都能避免为这些形态走通用的 CTE 物化、去重及回连路径，并不覆盖任意关联子查询。
- [#28905 · 将更多聚合状态纳入内存限额](https://github.com/duckdb/duckdb/pull/28905)（DinosL，窗口内合并至主线）：把 histogram、mode、entropy、approx_top_k 的相关分组状态纳入 `memory_limit` 记账，窗口执行也更早释放不用的批次结果。
- [#28987 · 修复无穷日期和时间戳的统计极值](https://github.com/duckdb/duckdb/pull/28987)（dentiny，窗口内合并至主线）：按行组统计直接回答 MIN/MAX 时，遇到全部为正无穷或负无穷的列，不应返回表中没有的有限日期或时间戳。
- [#29015 · 收紧 ORDER BY + LIMIT/OFFSET 的行组裁剪](https://github.com/duckdb/duckdb/pull/29015)（mustafahasankhan，窗口内新建，核查时开放）：提议只通过确认保持行数的算子传递裁剪依据，避免在 UNNEST、非常量 OFFSET 或百分比 LIMIT 等情形提前跳过仍可能需要的行组。
- [#28979 · 为嵌套 Parquet 列预取叶子列块](https://github.com/duckdb/duckdb/pull/28979)（mustafahasankhan，窗口内新建，核查时开放）：针对 STRUCT、LIST 等没有自身列块的父读取器，计划改为登记实际叶子读取范围，减少部分列转入串行按需读取。过滤成本估算留给独立提案。

## 官方博客

[官网列表](https://duckdb.org/news/)与[官方 Atom 订阅源](https://www.duckdb.org/feed.xml)均未发现覆盖窗口内发布的文章；最新一篇仍是 11 月 17 日的 Hugging Face 工作坊复盘。

## 方向观察（推测）

本日主线同时在减少不必要的计算和数据搬运：能省去中间物化的关联查询走专门路径，必须执行的扫描和哈希连接则着重改善数据局部性和过滤时机。这一判断来自上述几项已合并改动，不是官方路线图，也不意味着所有查询都会加速。

## 覆盖与限制

按同一 UTC 窗口查 GitHub 的新建、合并和更新结果，更新结果读至第二页；入选条目再核对原始时间戳、状态和改动。按更新时间的检索不能穷尽后来又被更新的讨论。未独立复现作者基准；合并至主线或维护分支均不等于正式发布。
