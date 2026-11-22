---
title: "DuckDB 日报 · 2026-11-21：选择性扫描减负，Parquet 连接估算两条新提案"
date: 2026-11-21 12:00:00 +0800
description: "主线减少选择性扫描的向量开销；两项待审 PR 分别改进 Parquet 多文件总行数和过滤后的连接估算。2.0.1 的 LIST 聚合内存回归已有修复提案。"
coverage_date: "2026-11-21"
---

**覆盖窗口：** 北京时间 2026-11-21 00:00 至 11-22 00:00（左闭右开；UTC 11-20 16:00 至 11-21 16:00）。实际核查：北京时间 11-22 约 09:00。

## 今日速览

- **已合入主线：** 选择性扫描减少引用计数开销，并让符合条件的小型 `IN` 和同列等值 `OR` 参与扫描内的自适应过滤。
- **仍在评审：** 一个 Parquet 提案补过滤后的连接键统计，另一个修复大小悬殊时的多文件行数估算。两者回答的不是同一个问题。
- **稳定版回归待修：** 2.0.1 在低内存下对少量整数分组执行大型 `list()` 聚合，可在落盘前耗尽内存；修复 PR 尚未合并。

## 已合入 main

- [#29076 · Reduce ownership overhead in selective scans](https://github.com/duckdb/duckdb/pull/29076)，**lnkuiper**，北京时间 00:15 合并。减少选择向量持有和向量切片的引用计数操作。符合条件的小型 `IN` 和同列等值 `OR` 可在扫描中提前过滤，同时保留原有的后续过滤。作者报告，在原生存储的 TPC-H Q19 SF704 暖态测试中，96 核从 336.0 降至 218.2 ms，192 核从 292.3 降至 136.9 ms。基线和候选版分批测试，数字反映整组改动，不代表 Parquet 加速或任何单项改动的收益。
- [#29117 · Support all encodings in encode and decode](https://github.com/duckdb/duckdb/pull/29117)，**Robinho-MR**，北京时间 01:24 合并，由 **Mytherin** 合入。显式指定编码时，`encode` 和 `decode` 支持 `system.encodings` 中注册的编码，包括 GB18030 和 Shift_JIS。适合已有历史编码的文本或字节数据转换，不是 CSV 自动识别编码。

## 新建提案与回归

- [#29173 · Improve Parquet join plans with bounded filter-conditioned statistics](https://github.com/duckdb/duckdb/pull/29173)，**hsuchenc**，北京时间 14:38 新建，**open**。在最终连接排序前，对满足预算和谓词条件的 Parquet 扫描读取必要列，计算精确的过滤后行数、近似连接键去重数（HLL），以及适用的整数范围。不同于只用行组 min/max 排除不相交范围：拟议方案实际读取数据，因此规划也有成本。作者在 1 TB TPC-DS 标准 99 题中记录到约 24 秒统计采集时间，并报告 Q78 OR 从 OOM 变为完成；标准题集总尝试时间仅降 1.20%，且每组只跑一次，不能视为通用加速。
- [#29169 · Multi-file scans: estimate files of very different sizes from their bytes](https://github.com/duckdb/duckdb/pull/29169)，**grvpuri**，北京时间 09:26 新建，**open**。文件大小悬殊时，按总文件字节数和代表文件的行密度估算，而不是把首文件行数乘以文件数；已经读到全部精确行数时仍以精确值为准。作者的分区 Parquet 样本中，`catalog_returns` 的估计由 4,202 修正为约 1,450 万，实际约 1,440 万。不过部分查询仍变慢，因为原来的低估曾抵消下游高估。
- [#29163 · v2.0.1：少量整数分组在不落盘的情况下耗尽内存](https://github.com/duckdb/duckdb/issues/29163)，**rustyconover**，04:27 报告，**open，标记已复现**；[#29175 · Fix runtime memory management for growing perfect-hash aggregates](https://github.com/duckdb/duckdb/pull/29175)，**kevintruong**，15:59 新建，**open**。报告中的 400 万行、1,000 个整数分组、`list(hash(i))` 在 64 MB 下，2.0.0 能完成，2.0.1 则 OOM。整数键范围小只意味着槽位少，不限制每组的列表长度。提案拟在内存吃紧时把支持的状态移到已有的可落盘聚合路径，并按内存缩小列表输出批次。初始计划仍可能显示 `PERFECT_HASH_GROUP_BY`；回归测试另检查运行时溢写字节和分组结果。
- [#29179 · Fix min/max is exact on nan values](https://github.com/duckdb/duckdb/pull/29179)，**dentiny**，北京时间 20:53 新建，**open**。作者示例中，文件本身没有 NaN，但开启 `parquet_can_have_nan` 后，浮点 `MAX` 返回了 NaN。提案不再把此时缺少 `nan_count` 的元数据边界当作精确的聚合答案。用于剪枝的保守边界和能直接返回给用户的聚合值是两回事。

## 官方博客

[DuckDB Engineering Blog](https://www.duckdb.org/news/) 未列出 11 月 21 日的新文章。最近的 [DuckDB 2.0.1 LTS 公告](https://www.duckdb.org/2026/11/20/announcing-duckdb-201) 日期为 11 月 20 日，不重复计入。

## 方向观察（推测）

Parquet 连接计划可能需要分两层验收：先看文件大小偏斜时总行数估得准不准，再看经过过滤后连接键还剩多少不同值。#29169 的个别查询退化以及 #29173 的额外规划开销都说明，局部估算更准不一定让整条查询更快。对照实验应分别记录各阶段估计/实际行数、规划 I/O 和 CPU、执行耗时及是否落盘；这是根据两项提案得出的测试建议，不是官方路线图。

## 覆盖与限制

按上述 UTC 窗口搜索 GitHub，返回 18 条新建、3 条合并和 47 条更新时间落在窗口内的 PR（类别重叠；更新不代表合并）。对入选条目另读详情或补丁确认状态。官方 Atom 订阅源未能独立解析，博客以官方索引核对。性能和复现结果来自 PR 或 issue 作者，未独立跑测；合入 `main` 不代表已进入稳定版。
