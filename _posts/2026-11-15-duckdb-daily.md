---
title: "DuckDB 日报 · 2026-11-15：检查点失败处理与字典编码列表"
date: 2026-11-15 12:00:00 +0800
description: "检查点失败处理、字典编码列表比较和 ALTER TYPE 各有新修复提案；流式窗口补上共享 CTE 的提前停止回归。"
coverage_date: "2026-11-15"
---

覆盖窗口：北京时间 2026-11-15 00:00 至 2026-11-16 00:00（不含终点），即 UTC 2026-11-14 16:00 至 2026-11-15 16:00。核查时间：北京时间 2026-11-16 08:58:14。

## 今日速览

- 新提案让内存库检查点在压缩任务失败时正确清理，避免错误处理期间崩溃。
- 新提案修正字典编码列表的元素比较，以及永久删除的旧值导致 `ALTER TYPE` 失败的问题。
- 流式窗口融合补上共享 CTE 的提前停止回归；窗口内未检索到 PR 合并。

## 重要 PR

时间均为北京时间。以下 PR 核查时均为开放、未合并，没有据此确认进入任何稳定版。

- [#28847 检查点任务失败时先清理待刷写状态](https://github.com/duckdb/duckdb/pull/28847) · **gulugulubing** · 13:47 新建。内存库的检查点任务因内存不足退出时，共享管理器可能仍持有已释放分段的引用。提案调整失败清理顺序并保护并发访问，让这条路径报告原始内存错误，而不是在后续刷写时崩溃。
- [#28849 修正字典编码列表的比较](https://github.com/duckdb/duckdb/pull/28849) · **jmestwa-coder** · 13:55 新建。拟让 `list_has_any` 和 `list_has_all` 按实际子元素位置读取比较键，避免对某些字典编码的 Arrow 列比较错误元素或越界；附相应回归测试。
- [#28840 ALTER TYPE 不再被永久删除的值挡住](https://github.com/duckdb/duckdb/pull/28840) · **git-sudo-404** · 03:17 新建。拟以 NULL 占位保留已永久删除行的物理位置，但不再尝试转换其旧值；仍可能被旧快照看到或仍能回滚的行不走此路径。这使列类型变更不会因已经不可见的历史数据而失败，同时保留 MVCC 语义。
- [#28845 让预处理执行结果报告底层语句类型](https://github.com/duckdb/duckdb/pull/28845) · **jraymakers** · 11:53 新建。拟让 C/C++ 调用者重新看到 `INSERT` 等真实语句类型，而非统一的 `EXECUTE`，便于区分正常结果集与受影响行数；SQL `EXECUTE` 的结果类型也会一并变化。
- [#28784 流式窗口融合](https://github.com/duckdb/duckdb/pull/28784) · **hawkfish** · 10:56 [更新实现](https://github.com/duckdb/duckdb/commit/e22e4827be9593f706c88ae2c33b4a089680855e)。把可能提前停止的窗口算子标记出来，并新增共享物化 CTE 的回归用例，约束一个消费者提前停止时另一个消费者仍能读到所需行。
- [#28837 跳过 WAL 时约束快照可见性](https://github.com/duckdb/duckdb/pull/28837) · **zaidrain06** · 04:10 [补充提交](https://github.com/duckdb/duckdb/commit/2ceb4561fb250e4e76e31f65f756cfc5d0c75477)。在外部快照可见性之外，再把追加行的清理限制在尚未完成检查点的提交之前，不因同一边界推迟更新清理。这是开放修复提案的后续，不是新增 WAL 复制功能。

## 官方博客与发布

[官网新闻](https://duckdb.org/news/)及 [Atom](https://duckdb.org/feed.xml)未见窗口内新文，最新仍是 11 月 12 日的 [Local Analytics Doesn’t Need a Database Server](https://duckdb.org/2026/11/12/local-analytics-without-a-database-server)。[官方 Releases](https://github.com/duckdb/duckdb/releases/latest)核查时最新稳定版仍为 2.0.0。

## 方向观察（推测）

[#28847](https://github.com/duckdb/duckdb/pull/28847) 和 [#28837](https://github.com/duckdb/duckdb/pull/28837) 分别收紧检查点失败后的对象生命周期，以及持久化前的可见与清理边界。两者提示：检查点的正确性不仅关乎磁盘写入，还关乎谁能读取或释放相关状态。它们仍在评审中，不代表官方路线图或补丁版承诺。

## 覆盖与限制

[DuckDB PR](https://github.com/duckdb/duckdb/pulls)按 UTC 窗口检索到 5 条新建、0 条合并、9 条最近更新时间在窗内的候选，类别可重叠；回查详情、部分讨论和提交。后续活动可能覆盖最近更新时间，不能据此穷举所有评审事件。测试为 PR 中报告或提交的覆盖，未独立运行。
