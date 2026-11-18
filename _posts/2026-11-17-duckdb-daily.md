---
title: "DuckDB 日报 · 2026-11-17：GEOGRAPHY 入核，优化器用上行组统计"
date: 2026-11-17 12:00:00 +0800
description: "DuckDB 主线新增球面地理类型；行组统计开始约束过滤扫描的估算，哈希连接与 lateral 子查询也有重要改动。"
coverage_date: "2026-11-17"
---

覆盖窗口：北京时间 2026-11-17 00:00 至 2026-11-18 00:00（不含终点；UTC 11-16 16:00 至 11-17 16:00）。核查时间：北京时间 2026-11-18 09:00 左右。

## 今日速览

- 核心新增 `GEOGRAPHY`，把球面语义与平面 `GEOMETRY` 区分开，并引入 v2.1.0 存储版本标识。
- 优化器开始用行组 zonemap 给过滤扫描估算设上限；普通和完美哈希连接也合并了一部分执行逻辑。
- 官网工作坊复盘示范了先用 SQL 从 210 万条评论里筛选证据，再把少量相关评论交给 LLM。

## 重要 PR

- [#28092 · 核心 GEOGRAPHY 与存储版本](https://github.com/duckdb/duckdb/pull/28092)（Maxxen，窗口内合并至主线）：新类型把边解释为球面上的弧，与按平面计算的 `GEOMETRY` 区分；范围运算和相关行组裁剪也适配球面语义。改动为 Parquet、Iceberg 等已有地理类型的格式互操作打基础，不等于所有空间函数都已支持球面计算，也不代表 v2.1.0 已发布。
- [#28793 · 用行组统计收紧过滤扫描估算](https://github.com/duckdb/duckdb/pull/28793)（h4nsmuller，窗口内合并至主线）：规划时排除确定不可能命中的行组，以其余行组的总行数限制估算，可能影响连接顺序和 build side 选择。对按时间追加的数据尤其有意义；边界行组仍按整组计，并非精确的命中行数。
- [#28815 · 统一普通和完美哈希连接的部分路径](https://github.com/duckdb/duckdb/pull/28815)（lnkuiper，窗口内合并至主线）：两条路径共享结果输出逻辑，位图查找扩展到 `RIGHT_SEMI` 和 `RIGHT_ANTI`。作者在 x86、SF10 的若干查询测到收益，不能直接外推到其他负载。
- [#28760 · 恢复 lateral 路径上的过滤下推](https://github.com/duckdb/duckdb/pull/28760)（Robinho-MR，窗口内合并至主线）：修复 DuckDB 2.0 中关联连接改用物化 CTE 后的两个回归：部分 lateral `UNNEST` 查询内存耗尽，以及 `json_valid` 无法先于相关表函数过滤坏输入。
- [#28515 · 等值连接的自适应 min/max 过滤](https://github.com/duckdb/duckdb/pull/28515)（kevintruong，窗口内合并至主线）：Parquet 与原生压缩扫描共享处理逻辑，按实际行数评估可选过滤器是否值得继续，而不是按字典项或压缩 run 的个数评估。暂停可选过滤时仍保留必需谓词。
- [#28790 · 将合资格的分组集部分聚合下推到连接之前](https://github.com/duckdb/duckdb/pull/28790)（h4nsmuller，窗口内合并至主线）：支持优化器生成的、已导出聚合状态的部分 `ROLLUP`、`CUBE` 和 `GROUPING SETS` 连接计划。连接前先聚合，连接后合并状态，再交给上层分组，不提前最终化。
- [#28969 · 修正某些 DECIMAL SUM 结果被放大](https://github.com/duckdb/duckdb/pull/28969)（alonfaraj，窗口内新建，核查时仍开放）：提案在聚合状态最终化后的类型不匹配时跳过相关下推重写，并加入回归测试。尚不能当作已修复。

- [#28953 · 解除事务对象对创建连接的部分依赖](https://github.com/duckdb/duckdb/pull/28953)（Robinho-MR，窗口内新建；北京时间 11 月 18 日 00:16 合并至主线）：事务元数据和本地写入路径不再持有创建连接的上下文引用，改由操作传入所需上下文。这是未来跨连接共享事务的准备工作，并没有实现共享事务。

## 官方博客

[DuckDB 与 Hugging Face 的评论分析工作坊](https://www.duckdb.org/2026/11/17/duckdb-user-group-workshop-ai-powered-review-analysis)（Geertjan Wielenga，官网及订阅源发布日期均为 11 月 17 日）：团队先用小样本验证流程，再用全量 210 万条 Amazon 评论运行。DuckDB 负责找出评分下滑的产品，并选取近期有帮助的低分评论；LLM 只处理选出的 40 条，归纳投诉主题。这个例子值得借鉴的是把可复现的筛选逻辑留在 SQL 中，再用模型做文本归纳。

## 方向观察（推测）

[#28793](https://github.com/duckdb/duckdb/pull/28793) 和 [#28515](https://github.com/duckdb/duckdb/pull/28515) 分别在规划时和执行时利用更接近实际扫描的数据，减少仅凭全表统计或压缩表示做决策的偏差。前者仍受行组粒度限制，后者只影响合适的可选过滤；这是本日合并内容呈现的共同方向，不是官方路线图。

## 覆盖与限制

按 GitHub 的创建、合并和更新时间筛选候选，再按原始时间戳与改动逐项核对；更新列表不保证穷尽每条讨论。官网文章对照博客索引和 Atom 订阅源。本文不独立复现 PR 基准，也不把主线合并视为稳定版发布。
