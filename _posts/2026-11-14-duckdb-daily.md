---
title: "DuckDB 日报 · 2026-11-14：多键连接过滤与 WAL 持久性"
date: 2026-11-14 12:00:00 +0800
description: "多键哈希连接可按列生成运行时过滤器，跨行组的 UPDATE RETURNING 修复合入主线；两项 WAL 正确性修复仍待合并。"
coverage_date: "2026-11-14"
---

覆盖窗口：北京时间 2026-11-14 00:00 至 2026-11-15 00:00（不含终点），即 UTC 2026-11-13 16:00 至 2026-11-14 16:00。核查时间：北京时间 2026-11-15 09:05:53。

## 今日速览

- 多键哈希连接可按列过滤；部分聚合也改进了成本估算，避免在连接下方做无效工作。
- 修复跨行组时 `UPDATE … RETURNING` 静默少返回行的问题。
- 两项 WAL 提案分别涉及检查点前的快照可见性和旧版重放兼容；仍未合并。

## 重要 PR

以下时刻均为北京时间。主线合并不等于已经进入稳定版。

### 已合入主线

- [#28726 多键哈希连接按列构建运行时过滤器](https://github.com/duckdb/duckdb/pull/28726) · **Richard-Durkee** · 04:45 合并。适合小构建端的多键连接现在可对各键列分别生成 Bloom 或前缀范围过滤，不只依赖 min/max。只要任一键列足够有选择性，扫描就可提前排除不匹配的行；这些过滤不能代替多键连接本身的匹配检查。
- [#28766 按完整分组键集评估部分聚合](https://github.com/duckdb/duckdb/pull/28766) · **lnkuiper** · 03:32 合并。分别估算连接两侧完整分组键的基数及缩减后的连接成本，避免低基数连接键掩盖近乎唯一的额外分组列，误选几乎不减行的预聚合。
- [#28742 跨行组追加保留原输入批次](https://github.com/duckdb/duckdb/pull/28742) · **DinosL** · 03:13 合并。改用局部切片承载溢入下一行组的剩余数据，避免重写型 `UPDATE` 实际更新了多行却通过 `RETURNING` 少返回行。
- [#28804 补齐 Parquet VARIANT 纳秒带时区时间戳编码](https://github.com/duckdb/duckdb/pull/28804) · **ThijsDreef** · 04:22 合并。非分列（unshredded）VARIANT 编码器补上此前缺失的类型分支，使这类值可以写入 Parquet，并扩充类型测试。

### 新提案和实质评审

- [#28833 恢复旧存储版本的 WAL 头兼容](https://github.com/duckdb/duckdb/pull/28833) · **sohamm20** · 07:08 新建，仍开放。拟仅在目标存储版本 ≥1.4.0 时写入两个新增 WAL 头字段；作者报告 1.3 读取旧格式目标库时曾把这类 WAL 当成损坏日志删除，可能丢失上次检查点后的提交。
- [#28837 约束跳过 WAL 提交的快照可见性](https://github.com/duckdb/duckdb/pull/28837) · **zaidrain06** · 18:32 新建，仍开放。拟在依赖自动检查点持久化的提交完成检查点前，不让并发外部快照看到该提交；提案附暂停检查点写入的测试，针对崩溃后读者已看到的数据可能消失的问题。
- [#28812 2.0 维护分支回移批次](https://github.com/duckdb/duckdb/pull/28812) · **Robinho-MR** · 仍开放。批次包含预读内存回收及多项连接过滤修复。08:39 的[自动评审](https://github.com/duckdb/duckdb/pull/28812#pullrequestreview-5900084326)报告普通外键和 `UPDATE … FROM` 计划各有一处与 2.0.0 不兼容的序列化变更；这是针对待合入批次的报告，并非已发布版本的结论。

- [#28831 避免按行组重复计算常量统计](https://github.com/duckdb/duckdb/pull/28831) · **rustyconover** · 06:26 新建，仍开放。拟缓存常量表达式的统计信息，减少 Parquet 行组裁剪中反复处理大型常量列表的开销；收益与查询形态有关。

## 官方博客与发布

[官方博客列表](https://duckdb.org/news/)未列出 11 月 14 日的新文，最新仍是 11 月 12 日的 [Local Analytics Doesn’t Need a Database Server](https://duckdb.org/2026/11/12/local-analytics-without-a-database-server)。[官方 Releases](https://github.com/duckdb/duckdb/releases/latest)核查时最新稳定版仍为 2.0.0。

## 方向观察（推测）

[#28726](https://github.com/duckdb/duckdb/pull/28726) 和 [#28766](https://github.com/duckdb/duckdb/pull/28766) 都在减少进入连接前的无效工作：前者尽早过滤，后者避免不划算的预聚合。两处收益都依赖数据分布和估算，不能据此推断普遍提速或官方路线图。两项 WAL 修复仅为开放提案，也不能据此判断下一个补丁版会纳入哪些修复。

## 覆盖与限制

[DuckDB PR](https://github.com/duckdb/duckdb/pulls)按 UTC 窗口检索到 12 条新建、7 条合并、43 条最近更新时间在窗内的候选，类别可重叠；回查重点详情和部分讨论。后续活动可能覆盖最近更新时间，不保证发现全部评审与评论。[Atom](https://duckdb.org/feed.xml)因读取入口不支持 XML 未能独立核对，博客结论以官网新闻列表为准。
