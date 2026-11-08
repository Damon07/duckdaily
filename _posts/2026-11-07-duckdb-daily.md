---
title: "DuckDB 日报 · 2026-11-07：递归 CTE 与外部资源"
date: 2026-11-07 12:00:00 +0800
description: "USING KEY 递归 CTE 执行优化合并，STRUCT 连接裁剪与外部资源管理方案推进。"
coverage_date: "2026-11-07"
updated_at: 2026-11-08T09:06:00+08:00
---

覆盖时间：北京时间 2026 年 11 月 7 日 00:00 至 11 月 8 日 00:00（左闭右开），即 UTC 11 月 6 日 16:00 至 11 月 7 日 16:00。检查时间：北京时间 11 月 8 日 09:06。

## 今日重点

- USING KEY 递归 CTE 的结果物化优化已合并，后续内存优化与连接顺序修复仍在评审。
- 两项 STRUCT 字段连接优化提案分别针对 Parquet 裁剪和 probe 行过滤，效果仍需验证。
- 外部资源发现和批量注册的一组相互依赖提案已提出。

## 重要 PR

### 递归 CTE

- [#28078 缓存 USING KEY 递归聚合结果](https://github.com/duckdb/duckdb/pull/28078)，kryonix，**11 月 7 日 04:55 合并至 main**。在提交时物化 finalize 结果，使读取路径不必重复 finalize 和加锁。作者报告特定循环扫描负载耗时下降，但部分 BIGINT 和字符串场景的内存占用增加；这不是对所有查询的保证。
- [#28520 降低递归聚合结果内存](https://github.com/duckdb/duckdb/pull/28520)，kryonix，**20:11 新建，检查时开放**。后续提案尝试对可直接投影的聚合从状态读取结果，减少物化副本；作者报告特定基准的内存下降，尚未独立复现。
- [#28521 修复递归 CTE 连接顺序导致的内存膨胀](https://github.com/duckdb/duckdb/pull/28521)，kryonix，**20:12 新建，检查时开放**。调整计划，避免先扩张独立输入的平方级连接，再与递归 frontier 连接。作者的复现案例从 OOM 转为完成，但仍慢于其所列 1.5.6 对照；性能结论需进一步验证。

### 查询优化与存储

- [#28506 STRUCT 字段连接的 Parquet 裁剪](https://github.com/duckdb/duckdb/pull/28506)，kevintruong，**07:17 新建，检查时开放**。处理连接使用 STRUCT 字段但还要保留父 STRUCT 的情况，尝试恢复 row-group 裁剪。作者报告测试案例读取的 row group 显著减少；仍为提案。
- [#28515 自适应连接过滤](https://github.com/duckdb/duckdb/pull/28515)，kevintruong，**15:58 新建，检查时开放**。为等值连接 probe 行加入自适应 min/max 过滤。作者报告某些负载明显受益，但 PR 同时记录性能验证未完和其他场景退化，不能视为普遍加速。

### 外部资源

- [#28522 查看外部资源类型](https://github.com/duckdb/duckdb/pull/28522)，carlopi，**20:19 新建，检查时开放**。提出可作为子查询使用的 SHOW EXTERNAL RESOURCE TYPES，方便程序发现可用资源类型。
- [#28525 返回资源 provider](https://github.com/duckdb/duckdb/pull/28525)，carlopi，**21:00 新建，检查时开放**。在资源发现结果中提供 provider 名称，帮助区分资源来源。
- [#28529 统一资源操作结果并支持批量注册](https://github.com/duckdb/duckdb/pull/28529)，carlopi，**23:18 新建，检查时开放**。提议统一 REGISTER、CREATE、DESTROY 的结果结构，并引入延迟注册和从表批量注册；该提案依赖前述系列工作，尚未合并。

### Mytherin 的讨论

在 [#27890](https://github.com/duckdb/duckdb/pull/27890#discussion_r4494644184) 中，Mytherin 质疑宏重载删除的依赖设计，建议重新绑定并避免默认关闭依赖跟踪时承担不必要成本。[作者回应](https://github.com/duckdb/duckdb/pull/27890#discussion_r4494756673)指出两次操作间名称解析可能变化，并说明默认字段序列化成本；双方仍在讨论，不能说已有最终方案。当天 14 个合并 PR 的记录显示由 Mytherin 执行合并；这不意味着这些 PR 均由他编写。

## 官方文章

[DuckDB 官方博客列表](https://duckdb.org/news/)未发现标注 11 月 7 日的新文章；最新可见文章标注 11 月 5 日。RSS 因读取工具不支持 XML 未能解析，确切发布时间未获进一步核实。

## 方向观察

**推测：** 递归 CTE 的执行与内存工作，以及外部资源发现、注册接口的系列提案，显示贡献者同时关注复杂执行计划和资源管理的可用性。多项方案仍开放且有性能权衡，单日 PR 不能构成官方路线图。

## 覆盖与局限

公开 GitHub 候选、评论与评审按页读取，并以创建、合并和评论时间核对窗口；重点内容经筛选，不是对所有改动的完整代码审计。性能数字为作者报告，未独立复现。官网列表可读，RSS 未解析。除另有说明外时间均为北京时间。**合并至 main 不代表稳定版已包含这些变化。**
