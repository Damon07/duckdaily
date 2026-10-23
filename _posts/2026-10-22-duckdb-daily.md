---
title: "DuckDB 日报 · 2026-10-22：实时诊断与分区写入落地，关注旧文件 NULL 裁剪风险"
date: 2026-10-22 12:00:00 +0800
description: "实时查询指标、失败查询 profile、整数分区 COPY 和窗口错误传播合并；旧版文件 NULL 裁剪修复、检查点并发与 Parquet 内存治理仍在提案阶段。"
coverage_date: "2026-10-22"
---

## 覆盖时间

北京时间 **2026-10-22 00:00 至 2026-10-23 00:00**，左闭右开；对应 UTC 2026-10-21 16:00 至 2026-10-22 16:00。实际核查：北京时间 **2026-10-23 09:03**。以下状态为核查时状态，事件时间均为北京时间。

## 今日速览

- **诊断能力补齐**：运行中的 I/O、内存指标，以及失败或中断查询的 profile，均已合入 main。
- **执行与存储减负**：有界整数键的分区 COPY、ART 插入路径迁移及窗口构建失败传播合并。
- **升级边界值得留意**：针对 1.x 写入文件的 NULL 裁剪错误已有公开复现和修复提案，尚未合并。不要把本日报的 main 合并项当成已进入 2.0.0 稳定版。

## 重要 PR

### 1. 旧文件的 NULL 行可能被错误裁剪：修复仍开放

[**#27632 · Fix NULL rows dropped by zonemap pruning on constant segments written by v1.x**](https://github.com/duckdb/duckdb/pull/27632)，作者 **franz101**。**open**，目标分支为 v2.0-cyanoptera；22 日 00:36 新建。

1.x 文件把 NULL 信息记录在 validity 段，而常量数据段可能声明“不含 NULL”。提案在加载时传播重叠 validity 段的 NULL 信息，避免接受 NULL 的过滤条件错误跳过数据。[22 日 10:16 的独立复现](https://github.com/duckdb/duckdb/pull/27632#issuecomment-6331072060)报告：2.0.0 读取由 1.5.6 写入的 DuckLake 元数据文件时，特定查询返回 1,428 而非 4,500；复现者明确未测试修复分支。**这是一项具体兼容性风险，不是所有旧文件都会出错，也不是已发布修复。** 使用此类目录的团队宜先用副本核对结果再迁移。

### 2. 查询还在运行时就能读取指标，失败后也保留 profile

- [**#26311 · Expose Live Query Metrics**](https://github.com/duckdb/duckdb/pull/26311)，作者 **Richard-Durkee**；**merged**，22 日 17:52 合入 main。新增 C++ 快照接口和 `duckdb_live_query_metrics()`，读取每个连接的读写字节、已分配内存等现有计数；无需开启 profiling。空闲连接展示最近查询的指标。
- [**#26578 · Emit The Profile Of Queries That Fail Or Are Interrupted**](https://github.com/duckdb/duckdb/pull/26578)，同作者；**merged**，22 日 18:09 合入 main。错误或中断不再把本次 profile 丢掉、留下前次查询的输出；并修整解析失败等路径的计时生命周期。

意义：监控与故障排查不必只等待成功完成。不过 #26578 明示，失败时正在运行的 pipeline 的部分算子行数仍可能为零，不能把该 profile 当作完整执行计量。

### 3. 分区 COPY 为小范围整数键增加直接输入路径

[**#27603 · Partitioned COPY: direct integer partition input next to the sorted path**](https://github.com/duckdb/duckdb/pull/27603)，作者 **h4nsmuller**；**merged**，22 日 20:35 合入 main。

在已知边界、至多 256 个键值且满足内存预算等条件下，整数分区可绕过常规哈希分桶与排序；批次规划和写出仍共用一套流程，越界键有排序回退，不依赖统计信息绝对准确。lnkuiper 当天继续审查读取接口、额外拷贝与批次边界；[关于上限的讨论](https://github.com/duckdb/duckdb/pull/27603#discussion_r4345386425)强调，分区太多反而会使输入趋向逐行处理。**这是有适用范围的优化，并非所有 PARTITION_BY 都会加速**；多列键、分区内排序等仍走其他路径，未将旧修订的基准数字作为最终合并版收益。

### 4. 窗口计算遇到内存错误时退出，而不是一直忙等

[**#27596 · Window: propagate build failures instead of livelocking the merge sort tree barriers**](https://github.com/duckdb/duckdb/pull/27596)，作者 **h4nsmuller**；**merged**，22 日 00:31 合入 main。

并行构建排序树的等待循环检查中断，阶段计数仅在任务成功后推进，避免一个线程抛出错误后其他线程永远等待或使用半成品状态。重点是 DISTINCT 窗口聚合等压力场景的可终止性，而非正常查询提速。[后续测试 #27636](https://github.com/duckdb/duckdb/pull/27636)同作者，当天 18:49 合并；不同窗口的测试不都意味着此前存在相同挂起问题。

### 5. ART 插入路径继续迁移到 buffer-managed 索引

[**#26153 · Buffer managed indexes 4d art insert**](https://github.com/duckdb/duckdb/pull/26153)，作者 **artjomPlaunov**；**merged**，22 日 17:34 合入 main。

公开描述将其定位为 ART 插入迁移的一步；差异中可见通过节点 handle 保持父节点有效、约束子指针引用的生命周期。意义在于索引存储管理基础设施的推进；没有公开基准足以据此声称整体索引速度提升，也不从其内部 issue 链接推断未公开计划。

### 6. Parquet VARIANT、Arrow 与 CSV 补上实际边界错误

- [**#27621 · Parquet VARIANT: stop auto-shredding at 32 levels of nesting**](https://github.com/duckdb/duckdb/pull/27621)，**h4nsmuller**；**merged**，22 日 16:04。深层剩余值保持未拆分表示，避免自动 shredding 制造过深 schema、级别溢出或栈溢出。
- [**#27622 · Keep empty VARIANT object keys out of the shredded Parquet type**](https://github.com/duckdb/duckdb/pull/27622)，提交者 **h4nsmuller**，说明注明沿用 **PeterVanHolland** 的提交；**merged**，16:21。空对象键留在未拆分值中，避免被改名或形成不能写出的类型。
- [**#27626 · Fix Arrow scans of run-end encoded list children and empty list dictionaries**](https://github.com/duckdb/duckdb/pull/27626)，**Robinho-MR**；**merged**，15:44。修复空首块、列表编码子节点等转换问题，减少错误值及崩溃。
- [**#27630 · Fix CSV sniffer with comment character, buffer boundary column check and piped read cardinality**](https://github.com/duckdb/duckdb/pull/27630)，**Robinho-MR**；**merged**，22:53。涉及显式注释字符下的引号识别、缓冲边界的列索引检查，以及管道输入被估算为零行导致的不合理连接选择。部分无自动检测场景仍有估算限制。

### 7. 检查点并发：减少索引锁阻塞，拆分 DROP 的存储生命周期

[**#27676 · Write a table's indexes during a checkpoint without the index list lock**](https://github.com/duckdb/duckdb/pull/27676)与[**#27678 · Let DROP TABLE and DROP INDEX run alongside checkpoints**](https://github.com/duckdb/duckdb/pull/27678)，作者均为 **ywelsch**；均 **open**，分别于 22 日 19:32、19:50 新建。

前者拟用索引列表快照缩短 checkpoint 对提交的阻塞；后者在其基础上区分目录删除、后续 checkpoint 排除及旧快照结束后释放，让 DROP 与 checkpoint 并行。这是并发与崩溃恢复语义上的提案，不是已落地保证；创建或替换表等操作也不在后者本次覆盖范围内。

### 8. Parquet 元数据内存拟纳入统一预算

[**#27686 · Allocate Parquet Thrift metadata from an ArenaAllocator**](https://github.com/duckdb/duckdb/pull/27686)，作者 **Robinho-MR**；**open**，22 日 22:34 新建。

将元数据的字符串、容器及嵌套结构放入 arena，按真实分配量估算缓存并计入 memory_limit，同时减少细碎分配。作者的极端宽表实验显示旧缓存估算明显偏低，但新方案的峰值 RSS 也更高；**内存核算更准确不等于 RSS 必定更低**，且共享机器基准存在噪声。

### 9. NUMERIC 提案继续推进，但物理设计仍在争论

[**#27567 · NUMERIC: a generic exact numeric type with run-time representations**](https://github.com/duckdb/duckdb/pull/27567)，作者 **h4nsmuller**；**open**。

[22 日 18:31 的进展](https://github.com/duckdb/duckdb/pull/27567#issuecomment-6338609359)讨论让排序、分组和连接键利用已知数值范围选择原生表示，以及统计估算和聚合的优化；[21:59 的评审](https://github.com/duckdb/duckdb/pull/27567#issuecomment-6342609766)则主张复用限制为数值的 VARIANT 物理表示，质疑第二套持久化格式及通用代码中的专用逻辑。该方向承接此前 Mytherin 对运行时特化的意见，**但本日这两条实质进展分别来自作者与 Robinho-MR，不应写成 Mark 当日的新提案或最终决定**。性能数字为作者实验，未独立复测。

## 官方博客

[官网新闻列表](https://duckdb.org/news/)与[Atom feed](https://duckdb.org/feed.xml)均未发现发布日期为 **10 月 22 日**的新文章。最新仍为 [10 月 21 日的 DuckDB 2.0.0 LTS 发布公告](https://duckdb.org/2026/10/21/announcing-duckdb-200.html)，不作为今天的新博客重复计数。feed 的全局更新时间不等于某篇文章发布日期。

## 方向观察（推测）

- **推测：可观测性开始覆盖“进行中”和“失败后”两个缺口。** 依据是 #26311 与 #26578 同日合并；反证与限制是未完成 pipeline 的细粒度计量仍不完整。
- **推测：性能改进更强调有条件的专用路径与资源生命周期。** #27603 为整数范围设置硬上限，#27686 正视元数据预算，#27676/#27678 则试图拆解 checkpoint 锁与释放时机。后面三项仍开放，不能将它们当作已承诺的官方路线图。
- **升级验证应优先正确性。** #27632 的公开复现说明，只检查能否打开旧文件还不够；需要检查带 NULL 条件的结果。此判断仅针对已披露场景，不扩展为对整个 2.0 版本的笼统结论。

## 覆盖与限制

GitHub 按更新下界分页检索，共检查 **110 条候选 PR**，并保留在窗口之后继续更新的条目，再以创建、合并及具体讨论时间判断是否纳入；重点项进一步核对详情、相关差异和讨论。优先留意 Mytherin、hannes、lnkuiper、pdet、Tishj、carlopi、hawkfish，但未将作者身份替代重要性筛选。这里是重点摘要，不是全量变更清单，也未逐条审计所有评论或运行基准。

本次网页工具无法解析 XML，随后直接读取 Atom 成功，博客检查没有残留 RSS 访问缺口。文中合并状态以公开 API 为准；**main 合并不等于稳定版已可用**，提案也可能继续改写或不被接受。对关闭、合并或发布发生在覆盖窗口之外的事件，不归入当天成果。
