---
title: "DuckDB 日报 · 2026-11-06：统计正确性与执行优化"
date: 2026-11-06 12:00:00 +0800
description: "列表统计与压缩扫描的后续修复、表函数复用语义，以及存储和查询执行进展。"
coverage_date: "2026-11-06"
updated_at: 2026-11-07T08:59:00+08:00
---

覆盖时间：北京时间 2026 年 11 月 6 日 00:00 至 11 月 7 日 00:00（左闭右开），即 UTC 11 月 5 日 16:00 至 11 月 6 日 16:00。检查时间：北京时间 11 月 7 日 08:59。

## 今日重点

- 列表长度统计已合并，但嵌套数据的一个正确性修复未随 squash 进入主线，后续修复仍在评审。
- 表函数稳定性契约落地，明确公共子计划复用的语义边界；压缩数据选择读取也已合并，但密集读取退化仍有后续工作。
- 跨表数据与索引块打包合并；CSV 块扫描和递归 CTE trampoline 仍是提案。

## 重要 PR

### 正确性与存储

- [#28408 列表长度统计](https://github.com/duckdb/duckdb/pull/28408)，Robinho-MR，**11 月 6 日 03:39 合并至 main**。增加列表长度最小值、最大值和总长度统计，供 length 等表达式传播与常量折叠使用。需注意：[评审确认](https://github.com/duckdb/duckdb/pull/28299#issuecomment-6682129450)嵌套列表经 optimistic write 或 WAL 后统计错误的最后修复未进入 squash，可能造成错误结果或过滤丢行。[#28467](https://github.com/duckdb/duckdb/pull/28467) 当晚新建以补回修复，检查时仍开放。
- [#28406 压缩数据选择行读取](https://github.com/duckdb/duckdb/pull/28406)，Robinho-MR，**01:07 合并**。扩展 bitpacking select，减少稀疏更新和过滤扫描的解码工作。密集 DELTA_FOR 扫描有性能退化；后续 [#28465](https://github.com/duckdb/duckdb/pull/28465) 当晚新建，检查时为开放草案，评审还指出正确性及性能问题，尚不能视为解决。
- [#28312 跨表打包数据与索引](https://github.com/duckdb/duckdb/pull/28312)，sebastiaan-dev，**19:07 合并**。调整 checkpoint 发布时机，使不同表的列段和索引能共同填充存储块，提高空间利用率。代价之一是持久化 ART 内存计入 BASE_TABLE，统计分类精度下降。
- [#28419 修复 read-ahead I/O 生命周期问题](https://github.com/duckdb/duckdb/pull/28419)，Robinho-MR，**16:48 合并**。在通知完成前释放异步闭包资源，修复 CI 发现的 heap-use-after-free。
- [#28468 持久化 secret 写入错误报告](https://github.com/duckdb/duckdb/pull/28468)，Robinho-MR，**23:48 合并**。写入失败不再报成功，替换失败时保留旧 secret；标记需要回移 v2.0，但尚不能据此称稳定版已包含修复。

### 规划与执行

- [#28324 表函数稳定性契约](https://github.com/duckdb/duckdb/pull/28324)，kryonix，**19:22 合并**。为公共子计划共享明确函数稳定性，避免 INTERSECT ALL 等路径复用本应独立求值的表函数而改变结果。内置函数默认查询内一致，实时或有副作用的函数需标为 volatile；现有 C API 注册仍按 volatile 处理。
- [#28453 不可能成立的窗口过滤](https://github.com/duckdb/duckdb/pull/28453)，hawkfish，**17:01 合并**。将不可能成立的 row_number QUALIFY 条件化为空结果，避免不必要的窗口计算；范围是该类空结果优化，并非所有窗口谓词融合。
- [#28279 纳秒时间戳与 interval 算术](https://github.com/duckdb/duckdb/pull/28279)，hawkfish，**17:37 合并**。支持 TIMESTAMP_NS 和 TIMESTAMPTZ_NS 加减 interval；讨论强调不同精度的表示范围不同，类型提升需要谨慎。
- [#28331 保留 interval 常量运算差异](https://github.com/duckdb/duckdb/pull/28331)，alitrack，**17:56 合并**。阻止将 1 MONTH 与 30 DAY 这类比较规范化后相等、但日期运算行为不同的常量错误去重；普通 interval 相等语义不变。
- [#28466 CSV 64 字节块扫描](https://github.com/duckdb/duckdb/pull/28466)，PeterVanHolland，**19:48 新建，检查时开放草案**。用可移植的 64 位位图跳过普通字符，不支持的方言和边界继续走原状态机。作者报告部分基准提升及大量结果比较；这些数据尚未独立复现，功能也未发布。
- [#28461 递归 CTE trampoline](https://github.com/duckdb/duckdb/pull/28461)，kryonix，**18:30 新建，检查时开放**。提议按 selector 将递归行分派到不同分支，面向编译成 SQL 的状态机或命令式程序；仍是待评审设计。
- [#28456 DISTINCT 直接规划为聚合](https://github.com/duckdb/duckdb/pull/28456)，Robinho-MR，**16:43 新建，检查时开放草案**。尝试减少 LogicalDistinct 专用优化分支。作者当晚修复多项正确性问题，但也明确记录 DISTINCT ON 自连接重写等性能退化仍待后续处理，不能视为完成。

### Mytherin 的设计讨论

- 在 [#27890](https://github.com/duckdb/duckdb/pull/27890#discussion_r4492480376) 中，Mytherin 倾向 EXPORT/COPY FROM DATABASE 时重新运行 binder，处理导出依赖顺序；他还建议将[删除单个函数 overload](https://github.com/duckdb/duckdb/pull/27890#discussion_r4494375663) 的内部实现按 ALTER 处理。该 PR 作者为 kryonix，当日仍开放。
- 在 [#28315](https://github.com/duckdb/duckdb/pull/28315#issuecomment-6684071327) 中，他请 lnkuiper 核查聚合状态竞争修复是否损害多核优化；在 [#28431](https://github.com/duckdb/duckdb/pull/28431#issuecomment-6685229104) 中建议重新审视 UNION 的 NULL 语义。这些是评审意见，不代表已合并方案。

## 官方文章

[官方博客列表](https://duckdb.org/news/)未检索到标注 11 月 6 日的新文章。最新可见的是 11 月 5 日的 [DataGrip 跨数据库查询案例](https://www.duckdb.org/2026/11/05/jetbrains-datagrip)。官网仅显示日期；本次 RSS 读取受限，未能重新核实精确发布时间，故不将其认定为北京时间 11 月 6 日新增。

## 方向观察

**推测：** 列表统计、压缩选择读取和表函数稳定性工作显示，贡献者正同时扩展优化器可用的信息与复用能力，并处理随之出现的正确性边界。#28467 和 #28465 的开放状态也说明合并后的修复与性能权衡仍在演进；这些个别 PR 不等于官方路线图。

## 覆盖与局限

公开 GitHub 候选与评论按页读取并按事件时间筛选；重点 PR 已核对详情，但并非对全部更新逐项代码审计。性能数据来自贡献者，未独立复现。私有 issue 未读取；官方列表已检查，RSS 因格式读取限制及 HTTP 403 未完成解析。除非另有说明，时间均为北京时间。**合并至 main 不代表稳定版已包含这些变化。**
