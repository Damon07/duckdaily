---
title: "DuckDB 日报 · 2026-11-20：2.0.1 LTS 发布，主线收紧时间过滤与连接优化"
date: 2026-11-20 12:00:00 +0800
description: "2.0.1 LTS 发布，带来 Parquet 页索引裁剪及升级注意事项；main 合并时间过滤修复、MARK join 简化和共享实例初始化改进。"
coverage_date: "2026-11-20"
---

覆盖窗口：北京时间 2026-11-20 00:00 至 2026-11-21 00:00（左闭右开，UTC 11-19 16:00 至 11-20 16:00）。实际核查：北京时间 2026-11-21 09:00 起。

## 今日速览

- **DuckDB 2.0.1 LTS 已发布**。升级前优先检查主机或桶级 `SECRET` 作用域，以及 `UPDATE … FROM` 和 `MERGE` 是否可能让多条源记录匹配同一条目标记录。
- main 修复了时间过滤重写的错误结果，并让常量部件的 `date_part` 和 `EXTRACT` 有机会下推为范围过滤。
- main 扩大了子查询可采用的连接计划，同时合并了共享数据库实例的初始化时序改进。以下 main 变更不视为 2.0.1 的发布内容。

## 重要 PR

- [#29078：修复时间过滤重写](https://github.com/duckdb/duckdb/pull/29078) · **guillesd**，包含 **mrouvroy-floe** 的修复 · 当日已合并至 main。覆盖日期截断、极端时间边界和夏令时回拨等场景；带时区时间戳的截断只在秒或更细粒度下做这项范围重写。[#29079](https://github.com/duckdb/duckdb/pull/29079)（同作者、同日合并）则把常量部件的 `date_part`／`EXTRACT` 绑定到对应的一元函数，让可安全重写的表达式参与范围剪枝，并补齐纳秒时间戳重载。
- [#28732：简化只用于过滤的 MARK join](https://github.com/duckdb/duckdb/pull/28732) · **lnkuiper** · 当日已合并至 main。可以安全改写时使用 SEMI／ANTI join，给连接排序和过滤下推更多空间；保留可见的 marker 和 NULL 语义。[#29051](https://github.com/duckdb/duckdb/pull/29051)（同作者、同日合并）让部分带关联键谓词的 `EXISTS` 直接走 semi join，并扩展复合键的聚合域成本判断。
- [#29068：共享实例初始化后再开放复用](https://github.com/duckdb/duckdb/pull/29068) · **Robinho-MR** · 当日已合并至 main。仍不稳定的 C API V2 允许同一文件的新实例完成初始化后再被其他调用方共享，并按解析后的设置比较配置；这是同一进程内的实例管理，不是跨进程共享。
- [#29053：NUMA 感知的连接 Bloom 筛选器](https://github.com/duckdb/duckdb/pull/29053) · **lnkuiper** · 当日已合并至 main。只在超过 128 个查询线程、超过 32 个分配器分片且内存预算允许时尝试为扫描保留就近副本；作者的大核机器测试既有提速也有几乎不变的查询，部分查询的内存占用上升。
- [#29105：避免无法帮助裁剪的 Parquet Bloom 读取](https://github.com/duckdb/duckdb/pull/29105) · **dentiny** · 当日新建并合并至 main。如果谓词结构决定 Bloom 筛选即使排除等值分支也无法跳过行组，就避免这次读取。它减少的是无用 I/O，和上面的连接 Bloom 筛选器不同。
- [#29133：修复多文件扫描漏读前一个文件](https://github.com/duckdb/duckdb/pull/29133) · **kryonix** · 当日新建，核查时仍 open。提案修复多个 reader 已打开时，剪掉后一个文件却误推进游标、跳过前一个合法文件的问题。作者给出了 Parquet 和 `read_duckdb` 的复现，尚不能视为已修复。

## 官方博客

[《Announcing DuckDB 2.0.1 LTS》](https://www.duckdb.org/2026/11/20/announcing-duckdb-201) · **DuckDB team** · 2026-11-20。[PyPI](https://pypi.org/project/duckdb/2.0.1/) 当日已有 2.0.1 构建。

- **升级注意事项。** 主机或桶级 `SECRET` 不再匹配仅共享名称前缀的其他目标；请检查完整主机／桶名，以及显式端口。`UPDATE … FROM` 和 `MERGE` 恢复逐条应用匹配结果；若多条源记录匹配同一目标且更新值不同，最终值可能不确定。2.0.1 也修复了 2.0.0 读取部分 1.x 文件时，过滤可能漏掉含 NULL 行的问题。
- **Parquet 页索引进入发布版。** [#27326](https://github.com/duckdb/duckdb/pull/27326) 能利用已有页索引减少行组内部的读取。[标签版测试](https://github.com/duckdb/duckdb/blob/v2.0.1/test/sql/copy/parquet/page_index/page_index_prefetch.test) 在同一文件上切换页索引并校验结果和日志读字节；强制 `whole_group` 预取仍读取整个行组。比较存储后端时，宜固定这两项设置。
- **存储与扩展。** 版本修复了 WAL 回放后自动 checkpoint 可能丢失索引条目的问题 [#26814](https://github.com/duckdb/duckdb/pull/26814)，以及回滚失败提交后重启可能丢行的问题 [#28190](https://github.com/duckdb/duckdb/pull/28190)。自定义扩展仓库新增按主机名注册 [#28719](https://github.com/duckdb/duckdb/pull/28719)。

## 方向观察（推测）

本期一边让扫描少读页和 Bloom 数据，一边收紧剪枝与计划重写的正确性边界。对基准测试最直接的启发是把「结果一致」「读了多少」「实际耗时」分开核对：页索引和预取策略足以改变同一条 SQL 的读范围，而优化器修复也可能改变返回行。这里讨论的是所选改动，不代表官方路线图，也没有独立复跑基准。

## 覆盖与限制

GitHub 搜索按上述 UTC 窗口得到新建 58 条、合并 48 条、更新 110 条，三组有重叠，仅选实质变化。检索结果和入选 PR 说明用于核查；部分 GitHub 单条 REST 接口返回 403，改用公开搜索结果、PR 页面及官方公告。官网新闻和订阅源同日仅见上述公告。日志读字节不等于网络传输或物理读盘字节。
