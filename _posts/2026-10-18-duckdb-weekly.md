---
title: "DuckDB 周报 · 2026-10-12—2026-10-18：性能回归治理、存储正确性与 C API v2 边界"
date: 2026-10-18 12:00:00 +0800
description: "多核、规划与 Parquet 路径持续减负；C API v2 已合并 unstable 约束。按主题复盘本周重要合并与未完成提案，并核对三篇官方文章。"
coverage_date: "2026-10-18"
permalink: /weekly/2026/10/18/
---

覆盖时间：北京时间 **2026-10-12 00:00 至 2026-10-19 00:00**，不含终点；对应 UTC 2026-10-11 16:00 至 2026-10-18 16:00。实际检查：北京时间 **2026-10-19 09:03**。

## 本周速览

- **性能工作以削减重复工作和竞争为主**：多核扫描、规划、聚合、Parquet 读取均有实质合并，但不同测试的局部收益不能相加。
- **优化能力与正确性同时推进**：OR 等值连接改写、外部 hash join Bloom 下推修复，以及 VARIANT、INTERVAL、Arrow 的边界修复值得一起看。
- **扩展能力继续增长，兼容边界更明确**：C API v2 本周已合并 unstable 标记及加载约束，不能再沿用早期日报中的“待合并”。

截至检查，官方最新正式发行仍为 [v1.5.6（9 月 28 日）](https://github.com/duckdb/duckdb/releases/tag/v1.5.6)。下文“已合并”指对应开发或维护分支接收代码，**不等于稳定版已经可用**。

## 1. 执行与规划：减少竞争、重复遍历和细碎开销

**已合并。** lnkuiper 的 [#26967](https://github.com/duckdb/duckdb/pull/26967)、[#27142](https://github.com/duckdb/duckdb/pull/27142) 分别于北京时间 13、14 日合入 v2.0，涉及物化扫描任务分配、字典哈希缓存、动态过滤锁竞争、Top-N 边界读取及缓冲分配。16 日合入 main 的 [#27378](https://github.com/duckdb/duckdb/pull/27378) 则分批初始化聚合状态，并改善二元聚合有效位处理。意义在于降低执行基础设施开销，而非增加新的 SQL 功能。

规划侧，kryonix 的 [#26965](https://github.com/duckdb/duckdb/pull/26965)、[#26964](https://github.com/duckdb/duckdb/pull/26964) 于 13 日合并，分别减少连接候选对的重复评估和对完整计划的反复扫描。Dtenwolde 整理 lnkuiper 优化的 [#27393](https://github.com/duckdb/duckdb/pull/27393) 于 17 日合入 main，减少解析扫描与 token 迭代成本。它们覆盖查询真正执行前的延迟，不能只用扫描吞吐衡量价值。

## 2. 优化器：扩大适用范围，同时避免漏行和提前报错

**已合并。** EslamAhmed171 的 [#22797](https://github.com/duckdb/duckdb/pull/22797) 于 16 日合入 main，将适用的 OR 等值 JOIN 拆为比较连接分支，同时保留重复行、NULL 和外连接语义；不是简单追加 UNION 去重。

外部 hash join 的 Bloom 下推经历两步修复：DeviousCardi 的 [#25718 最终差异](https://github.com/duckdb/duckdb/pull/25718/files) 于 13 日先禁用该路径以避免漏行；kryonix 的 [#26959](https://github.com/duckdb/duckdb/pull/26959) 于 14 日改为在 Sink 阶段覆盖完整 build side 后恢复下推。这也更正了 13 日日报对第一步机制的描述，周报以最终代码为准。

evertlammerts 的 [#27108](https://github.com/duckdb/duckdb/pull/27108) 于 14 日合入 v2.0，把动态 PIVOT、部分 ALTER、IMPORT 等展开语句纳入同一次查询与事务生命周期。Tishj 的 [#27300](https://github.com/duckdb/duckdb/pull/27300) 于 16 日合入 main，避免未使用的 CASE/COALESCE 分支在规划期提前触发错误；真正执行出错分支仍会报错。

## 3. 内存与存储：更完整地记账，减少冗余复制

**已合并。** h4nsmuller 的 [#26919](https://github.com/duckdb/duckdb/pull/26919) 于 13 日将多类大分配纳入 buffer manager；lnkuiper 的 [#27298](https://github.com/duckdb/duckdb/pull/27298) 于 16 日修正低内存分组聚合的最低工作集预留。这有助于资源协调，但并不保证进程 RSS 永远低于 memory_limit，或任意低限额查询都能完成。

Robinho-MR 的 [#26924](https://github.com/duckdb/duckdb/pull/26924) 于 12 日合入 main，减少 UPDATE 撤销信息中可从基础存储重新取得的旧值复制。sebastiaan-dev 的 [#23462](https://github.com/duckdb/duckdb/pull/23462) 于 13 日引入 ART checkpoint shadow index，为同表不同索引的块共置打基础，范围不包括跨表共置。

**仍是提案。** pdet 的文件描述符预算 [#26927](https://github.com/duckdb/duckdb/pull/26927) 本周创建并迭代，尚未合并。ywelsch 的连续向量读取 [#27383](https://github.com/duckdb/duckdb/pull/27383) 也仍开放；[Mytherin 在 16 日的评审](https://github.com/duckdb/duckdb/pull/27383#issuecomment-6216032400)建议将快路下沉到 segment 层，覆盖部分向量及连续 run。这是值得跟踪的实现讨论，尚非确定方案。

## 4. Parquet：性能修复与类型语义一起推进

**已合并。** lnkuiper 的 [#26905](https://github.com/duckdb/duckdb/pull/26905)、guillesd 的 [#26960](https://github.com/duckdb/duckdb/pull/26960) 于 13 日合入 v2.0，涉及统计元数据重复构造、预取重复读取、row-group 准备锁竞争，以及字符串复制与验证开销。不能据此宣布所有相关性能回归都已解决。

本周 VARIANT 修复包括 PeterVanHolland 的 [#27273](https://github.com/duckdb/duckdb/pull/27273)（DECIMAL scale/width）、Robinho-MR 的 [#27240](https://github.com/duckdb/duckdb/pull/27240)（仅允许语义等价的转换下推）、Tishj 的 [#27248](https://github.com/duckdb/duckdb/pull/27248)（对象字段按 UTF-8 名称排序写出）。minhh-nguyen 的 [#27246](https://github.com/duckdb/duckdb/pull/27246) 于 17 日合并，避免字典把比较相等、但日期运算效果不同的 INTERVAL 表示合成一个值。

**仍是提案。** h4nsmuller 本周新建的页索引 [#27326](https://github.com/duckdb/duckdb/pull/27326) 拟支持 ColumnIndex/OffsetIndex 剪枝，尚未合并；跳过的行数也不能直接换算为节省的网络流量。

## 5. 扩展接口：能力增多，V2 仍明确不稳定

**已合并。** Maxxen 的 [#26863](https://github.com/duckdb/duckdb/pull/26863)、[#26872](https://github.com/duckdb/duckdb/pull/26872)、[#26886](https://github.com/duckdb/duckdb/pull/26886) 于 12 日合入 v2.0，补充 PRAGMA、自定义设置、宏、日志接收端与集合注入等接口。18 日 23:01 合入 main 的 [#26356](https://github.com/duckdb/duckdb/pull/26356) 增加基础统计回调，范围仅为 NULL/validity 信息，并非完整类型统计。

evertlammerts 的 [#27410](https://github.com/duckdb/duckdb/pull/27410) 已于 **18 日 19:07** 合入 v2.0：全部 V2 API 标为 unstable，要求消费者显式选择，V2 扩展绑定精确 DuckDB 版本，并包含加载端检查。扩展开发者应把这一约束与新增接口一起评估。

carlopi 的 [#27427 最终差异](https://github.com/duckdb/duckdb/pull/27427/files) 于 18 日合入 v2.0，增加外部扩展构建组并恢复 Lance 配置；Vortex 默认仍为 OFF，不能写成两者均已恢复。

## 6. 兼容性与边界修复

- **维护分支已接收**：hannes 的 [#27143](https://github.com/duckdb/duckdb/pull/27143/files) 于 14 日合入 v1.5-variegata，回移异常 Parquet 长度乘法溢出、列表重复级别下溢检查。尚不能据此宣称新补丁版已发布，也不推断 CVE。
- **已合并**：carlopi 的 [#27381](https://github.com/duckdb/duckdb/pull/27381)、[#27412](https://github.com/duckdb/duckdb/pull/27412) 于 18 日合入 v2.0，按原始 S3/hf 路径检查访问设置，并处理 URL 指定 endpoint 的边界，避免映射后的 HTTPS 地址误拒绝已授权路径。
- **已合并**：evertlammerts 的 [#27409](https://github.com/duckdb/duckdb/pull/27409) 于 18 日合入 v2.0，修复 NULL 索引的 Arrow STRUCT 字典读取崩溃；hawkfish 的 [#27342](https://github.com/duckdb/duckdb/pull/27342)、[#27345](https://github.com/duckdb/duckdb/pull/27345) 于 16 日分别修复 LEAD/LAG frame 定位和含子查询分组表达式的 collation 结果。

## 官网文章：三篇新文，无核心新正式发行

1. **10 月 13 日：[What Is Inside an Iceberg Table?](https://duckdb.org/2026/10/13/inside-iceberg-table.html)**  
   用 DuckDB 逐层检查 JSON 元数据、Avro manifests、Parquet 数据与删除文件。实践价值是借助快照、分区和列统计诊断扫描过多、文件堆积及行数异常。

2. **10 月 16 日：[From JSON Strings to Typed Columns](https://duckdb.org/2026/10/16/json-to-typed-columns.html)**  
   通过 json_group_structure 推断结构、json_merge_patch 调整类型，再用 json_transform 和 unnest 生成类型化列，避免导出后重读。适合重复分析事件载荷；严格转换模式可用于尽早暴露数据问题。

3. **10 月 16 日：[Benchmarking DuckDB v2.0-dev on NVIDIA Vera](https://duckdb.org/2026/10/16/nvidia-vera-benchmark.html)**  
   官方以开发预览构建运行完整 TPC-H SF1000，报告 Vera 配置的综合分数中位数比 Intel Xeon 6 基线高约 46%。这是特定硬件和配置下、未经正式 TPC 审计的比较，不能写成通用加速比，更不能作为 v2.0 正式发布的证据。

## 方向观察与下周关注

**推测，非官方路线图：** 从多核竞争、规划重复遍历、Parquet 读取与内存记账这组已合并工作看，当前重点之一是降低通用执行路径的额外开销，并治理性能与正确性回归。由于改动跨多个分支、测试负载不同，目前不能推导统一的端到端提升。

**推测，非官方路线图：** C API v2 一边扩展能力、一边显式绑定不稳定版本，说明接口演进仍需与扩展兼容管理同步进行；不意味着稳定 ABI 已经承诺。

后续可观察文件描述符预算、连续向量读取、Parquet 页索引，以及尚未合并的 [Bloom index #27402](https://github.com/duckdb/duckdb/pull/27402)、[小域相关子查询优化 #27426](https://github.com/duckdb/duckdb/pull/27426)。个人 PR 与微基准不等于官方路线图或普遍性能收益。

## 来源覆盖与限制

读取仓库 10 月 12–17 日日报作为线索；18 日日报在检查时不存在，已从原始 GitHub PR 检索补查周日进展。对重要条目回查 PR 元数据、最终差异或相关讨论，按主题去重，而非直接拼接日报。此为重要进展精选，不是全部 PR、评论和生态仓库的穷尽清单。

[官网新闻](https://duckdb.org/news/)、[官方 Atom feed](https://duckdb.org/feed.xml)及三篇文章已交叉核对；feed 的日期为站点提供的时间戳，不视作经过独立证明的实际发文时刻。发行状态核对自[官方 Releases](https://github.com/duckdb/duckdb/releases)。

当前状态与周内事件分别判断：例如 httpfs 更新 #27432 虽在周内提出，其合并发生于北京时间 19 日 02:10，故不计作本周合并成果。本文没有运行独立性能实验，也不将作者特定环境的结果外推为稳定版表现。
