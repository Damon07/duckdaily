---
title: "DuckDB 日报 · 2026-10-23：多核与外部排序提案，Parquet 内存管理落地"
date: 2026-10-23 12:00:00 +0800
description: "NUMA、外部排序和延迟向量分配迎来新提案；Parquet 元数据内存管理、扫描量指标与低内存错误处理已合并。旧文件 NULL 裁剪回归仍待合并。"
coverage_date: "2026-10-23"
---

## 覆盖时间

北京时间 **2026-10-23 00:00 至 2026-10-24 00:00**，左闭右开；对应 UTC **2026-10-22 16:00 至 2026-10-23 16:00**。实际核查：北京时间 **2026-10-24 09:00**。下列事件时间均为北京时间，状态截至核查时。

## 今日速览

- lnkuiper 新建多核/NUMA、外部排序和延迟向量分配提案，关注计算局部性、溢写和分配开销，均尚未合并。
- Parquet 元数据内存管理、扫描量指标及低内存错误处理已合并；这些提交不代表稳定发行版已经包含。
- 旧版文件 NULL 行被错误裁剪的修复获得独立复现反馈，但 PR 仍开放，不能视为问题已发布修复。

## 重要 PR

### 执行与查询优化

- **[Many-core/NUMA improvements · #27782](https://github.com/duckdb/duckdb/pull/27782)**，作者 **lnkuiper**；**open，提案**，当日 **22:46 新建**。改进哈希连接和分组聚合预取，使连接分区的初始化与构建更贴近 CPU 分组，并复用大块分配、减少共享计数器争用。意义在于改善高核数机器的数据局部性与扩展性。作者提供特定机器上的测试结果，尚不能外推为所有查询或硬件的收益。

- **[Out-of-core sort improvements · #27783](https://github.com/duckdb/duckdb/pull/27783)**，作者 **lnkuiper**；**open，提案**，当日 **22:51 新建**。调整外部排序的分区、归并与缓冲管理，减少重复溢写并改善倾斜数据处理。主要影响超内存排序；作者所报收益来自其测试，本文未复现。该提案受 CrocSort 实验启发，但并未实现其全部技术。

- **[Lazy Vector Allocations · #27751](https://github.com/duckdb/duckdb/pull/27751)**，作者 **lnkuiper**；**open，提案**，当日 **15:52 新建**。将向量有效载荷推迟到首次可写访问再分配，并在重置时复用缓存缓冲区，同时处理嵌套类型与 C API 兼容性。意义在于减少未使用向量的分配工作；PR 整体基准结果有升有降，暂不据此宣称普遍提速。

- **[Window Join Pushdown · #27739](https://github.com/duckdb/duckdb/pull/27739)**，作者 **hawkfish**；**open，提案**，当日 **10:27 新建**。在满足分区函数依赖、连接类型及必要唯一性约束时，把筛选性连接移到窗口算子之前，减少窗口需处理的数据。最终效果取决于查询形态，不能理解为任意连接都可安全下推。

- **[Lazy initialize optimizer · #27441](https://github.com/duckdb/duckdb/pull/27441)**，作者 **dentiny**；**merged，已合并至 main**，当日 **00:02 合并**。最终差异将默认表达式重写规则改为首次访问时初始化，避免无需这些规则的语句承担构造开销，并调整自定义规则接口。这是规则初始化路径优化，不是所有优化器对象都改为惰性构造。

### 存储、可观测性与可靠性

- **[Allocate Parquet Thrift metadata from an ArenaAllocator · #27686](https://github.com/duckdb/duckdb/pull/27686)**，作者 **Robinho-MR**；**merged，已合并至 main**，当日 **16:45 合并**。Parquet Thrift 元数据的字符串、容器及嵌套对象使用 arena，减少细碎分配，并按实际 arena 大小计量缓存，让相关分配进入缓冲区分配器的内存限制管理。重点是更真实的记账与生命周期管理；作者极宽表测试也显示峰值 RSS 可能上升，不能简单称为“全面降低内存”。

- **[Add query.total_bytes_scanned / operator.bytes_scanned · #27682](https://github.com/duckdb/duckdb/pull/27682)**，作者 **Robinho-MR**，延续 **AimeryCM 的 [#26774](https://github.com/duckdb/duckdb/pull/26774)** 与 **SrikanthKandula 的 [#26641](https://github.com/duckdb/duckdb/pull/26641)**；**merged，已合并至 main**，当日 **02:14 合并**。加入查询级和算子级扫描字节指标，Parquet 在实际开始扫描行组时统计所选列块的压缩大小，避免把未开始扫描的行组计入。便于分析扫描与裁剪效果，但该口径不等同于物理磁盘或网络实际读取字节数。

- **[Report out of memory instead of aborting in worker threads, task errors and stack traces · #27629](https://github.com/duckdb/duckdb/pull/27629)**，作者 **Robinho-MR**；**merged，已合并至 main**，当日 **16:27 合并**。补强工作线程记账、任务错误记录和堆栈符号解析的分配失败处理，包括预备内存不足错误对象，降低“报告错误时再次分配失败”导致进程终止的风险。仍有重试上限等边界，不保证所有低内存路径都永不终止。

- **[Fix NULL rows dropped by zonemap pruning on constant segments written by v1.x · #27632](https://github.com/duckdb/duckdb/pull/27632)**，作者 **franz101**；**open，面向 v2.0-cyanoptera 的修复提案**。针对旧版文件把 NULL 信息仅存于 validity segment 时，2.0 的 zonemap 裁剪可能漏掉 NULL 行的问题，加载时结合 validity 信息修正数据段统计。当日 **11:05**，**alexisdegler-sys** 提交[独立对照验证](https://github.com/duckdb/duckdb/pull/27632#issuecomment-6356384262)：其 DuckLake 元数据查询应返回 4,500 条活动文件记录，发行版和撤销补丁的对照返回 1,428 条，PR 构建返回 4,500 条。验证限于所述元数据查询与测试样例，不是 PR 构建上完整 DuckLake 挂载流程的验证。

### 扩展与维护分支

- **[Enable spatial for wasm targets · #27672](https://github.com/duckdb/duckdb/pull/27672)**，作者 **carlopi**；**merged，已合并至 main**，当日 **00:22 合并**。完整扩展集构建配置不再排除 wasm 的 spatial，并更新扩展引用。它打开构建路径，不足以证明对应公开二进制已经发布或所有空间功能都可在浏览器使用。

- **[Backport labeled fixes to v2.0-cyanoptera · #27684](https://github.com/duckdb/duckdb/pull/27684)**，作者 **smvv**；**merged，已合并至 v2.0-cyanoptera**，当日 **21:04 合并**。集中回移标记修复并作维护分支适配，体现修复向 2.0 分支集成的进展；这是分支提交，不是新的补丁版发布公告，也不包含仍开放 PR 的发布保证。

## 官方博客

本次读取的[官方新闻列表](https://duckdb.org/news/)未列出 **2026-10-23** 发布的新文章；列表最新文章为 **2026-10-21** 的 “Announcing DuckDB 2.0.0 LTS ‘Cinnamon Teal’”，不计入本日报，也不作为上述当日合并提交已发布的证据。

[官方 RSS](https://duckdb.org/feed.xml)未能成功读取，因而这里的“未发现”仅基于已核对的新闻列表，不声称完成了双源交叉验证。

## 方向观察（推测）

- **执行性能的重心可能更多落在数据移动与分配成本。** 依据是 #27782 的 NUMA/预取、#27783 的溢写处理、#27751 的按需分配；但三者仍是开放提案，基准适用范围不同，不能当作官方路线图或统一性能承诺。
- **2.0 后的稳定化工作兼顾正确性、资源压力和可观测性。** 依据是 #27629、#27686、#27682 及维护分支回移；反面约束是 #27632 尚未合并，分支修复和实际发行仍有时间差。

## 覆盖与限制

- 通过 GitHub 公开 API 分页读取窗口起点之后更新的 **170 条 PR 候选**（两页，搜索未标记结果不完整），再按创建、合并及实际讨论时间筛选；未把单纯 updated_at 变化当作实质进展。重点条目核对详情，并按需读取代码差异与讨论。
- 已优先检查 Mytherin 及指定核心贡献者。未核实到适合本期单列的 Mytherin 当日实质事件，不以旧提案或无解释的更新时间凑数；其他作者的重要贡献同样纳入。
- PR 讨论与代码未逐条穷尽，性能数据未自行重跑；官网 RSS 读取失败，官方博客覆盖以新闻列表为限。
- **open 表示尚未合并的提案；merged 表示进入所注明分支，不等于稳定版已发布或用户安装版本已包含。** 本文没有把任何当日 PR 单独标为“已发布”。
