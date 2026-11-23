---
title: "DuckDB 周报 · 2026-11-16 至 2026-11-22：2.0.1 LTS 发布，主线让连接与扫描少做无用功"
date: 2026-11-22 12:00:00 +0800
description: "2.0.1 LTS 带来迁移检查项和 Parquet 页索引；主线扩展数值与地理类型，并改善连接估算和扫描执行。"
coverage_date: "2026-11-22"
permalink: /weekly/2026/11/22/
---

覆盖窗口：北京时间 11 月 16 日 00:00 至 11 月 23 日 00:00（左闭右开；UTC 11 月 15 日 16:00 至 11 月 22 日 16:00）。实际核查：北京时间 11 月 23 日 09:00–09:03。

## 已发布：2.0.1 LTS，先查升级行为

11 月 20 日，DuckDB 团队发布 [2.0.1 LTS](https://www.duckdb.org/2026/11/20/announcing-duckdb-201)（[完整发布记录](https://github.com/duckdb/duckdb/releases/tag/v2.0.1)）。从 2.0.0 升级时，重点检查两处：主机或桶级 `SECRET` 不再匹配仅有共同前缀的目标；`UPDATE … FROM` 和 `MERGE` 会逐条应用匹配结果，多条源记录命中同一目标时，应先去重或保证更新值一致。版本也修复了过滤某些 1.x 数据库文件时可能漏掉 NULL 行的问题。

Parquet 读取可以利用已有的[页索引](https://github.com/duckdb/duckdb/pull/27326)跳过行组内不匹配的页；强制整行组预取仍会改变实际读取量。新版还将 Sirius 纳为核心扩展，在支持的 Linux + NVIDIA CUDA 环境运行 GPU 查询，未支持的查询回退到 CPU。1.4 LTS 社区支持已于 11 月 17 日结束。

## 已合入 main：改进规划、执行与类型表达

- **规划时避免错估。** [#28793](https://github.com/duckdb/duckdb/pull/28793)（h4nsmuller）给原生表过滤后的行数估算加上界：把确定不相交的行组排除，再用剩余行组总行数限制估算。这可能改变连接顺序，但不增加实际扫描的裁剪，也不精确估算边界行组。适合关注时间追加、范围聚簇数据。时间过滤是另一条主线：[修正范围重写的错算边界](https://github.com/duckdb/duckdb/pull/29078)、[让合资格的 DATE_PART / EXTRACT 也可改写为范围](https://github.com/duckdb/duckdb/pull/29079)（guillesd，包含 mrouvroy-floe 的工作）。
- **执行时让扫描和连接少做工作。** [#28865](https://github.com/duckdb/duckdb/pull/28865)（lnkuiper）让已就绪的原生扫描倾向使用靠近缓存块的 worker，仍允许工作窃取；[#29076](https://github.com/duckdb/duckdb/pull/29076)（同作者）减少选择性扫描的引用计数操作，让符合条件的小型 `IN`／同列等值 `OR` 参与自适应过滤，保留后续必需检查。作者的暖态原生 TPC-H Q19、192 核测试为 292.3 → 136.9 ms，系分批测试，非通用加速承诺。与此同时，[#28789](https://github.com/duckdb/duckdb/pull/28789)（h4nsmuller）补上符合条件的复合键哈希连接在溢写时的逐键运行时过滤。
- **类型扩展与数据边界。** [#26955](https://github.com/duckdb/duckdb/pull/26955)（h4nsmuller）用 BIGNUM 承载超过 38 位的 `DECIMAL`，保留较窄值的定长表示；[#28092](https://github.com/duckdb/duckdb/pull/28092)（Maxxen）在核心区分球面 `GEOGRAPHY` 与平面 `GEOMETRY`，并引入新的存储版本标识。不意味着旧客户端、所有空间函数或发布版已支持。
- **保留裁剪语义，再做重写。** [#29058](https://github.com/duckdb/duckdb/pull/29058)（guillesd）修复窗口查询改写为自连接时，重新绑定 Parquet 扫描却恢复了已被 Hive 分区过滤排除的文件，导致窗口计数从 2 错成 3。遇到无法可靠保留文件列表的扫描时，改回常规窗口算子。

## 仍开放：两种 Parquet 估算，以及低内存聚合

- **Parquet 连接估算不是单一问题。** [#29169](https://github.com/duckdb/duckdb/pull/29169)（grvpuri）处理文件大小悬殊造成的总行数失真，用文件字节和代表文件行密度估算；[#29173](https://github.com/duckdb/duckdb/pull/29173)（hsuchenc）则在预算允许时读取必要数据，算过滤后行数及近似连接键去重数。前者主要应对文件大小偏差，后者用计划阶段读数据来换更好的连接估算；与原生表只用行组上界的 #28793 不同。较准的估算不保证总查询更快。
- **聚合状态可能比键范围大得多。** [#29163](https://github.com/duckdb/duckdb/issues/29163) 报告 2.0.1 对少量整数分组构建大型 `list()` 时能在 64 MB 下 OOM。[#29175](https://github.com/duckdb/duckdb/pull/29175)（kevintruong）拟在内存不足时将支持的状态转交给可落盘的聚合路径。验收应同时看结果和运行时溢写，不能只看 EXPLAIN 的初始算子名称。

## 官网与扩展

除 2.0.1 公告外，11 月 17 日的[官方工作坊复盘](https://duckdb.org/2026/11/17/duckdb-user-group-workshop-ai-powered-review-analysis)介绍了先用 SQL 在约 210 万条评论中筛证据，再把较少的相关文本交给 LLM。另一个扩展动向是 [duckdb-fts #87](https://github.com/duckdb/duckdb-fts/pull/87)（Dtenwolde）已合入扩展 main：增量全文索引跟踪普通 `UPDATE`，旧增量索引需重建以安装新触发器。该合并不等于 2.0.1 已提供它，也未核实用户平台上的发行二进制。

## 方向观察与覆盖

**推测：** 本周优化更值得关注的是三个可分别测量的环节：规划预测会留下多少行，执行决定需读和解码多少数据，运行时再控制中间状态能否留在内存。更好的估算不一定省 I/O，读得少也不能替代正确性检查。这个判断来自公开补丁，不是官方路线图。

本周七份日报均有对应源稿；以上回查了原始 PR、官网与发布记录，选重点而非完整枚举。状态为核查时所见；未独立运行基准、回归或安装扩展。除明确写为已发布者，不把 main 或扩展仓合并当作稳定版可用。
