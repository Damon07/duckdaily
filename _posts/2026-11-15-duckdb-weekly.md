---
title: "DuckDB 周报 · 2026-11-09 至 2026-11-15：运行时过滤与 2.0 兼容"
date: 2026-11-15 12:00:00 +0800
description: "主线改进连接、CSV 扫描与高核扩展性；2.0 维护分支继续吸收升级和恢复修复，但回移不等于发布。"
coverage_date: "2026-11-15"
permalink: /weekly/2026/11/15/
---

覆盖窗口：北京时间 2026-11-09 00:00 至 2026-11-16 00:00（不含终点），即 UTC 2026-11-08 16:00 至 2026-11-15 16:00。核查时间：北京时间 2026-11-16 09:05:27。

## 本周速览

- 连接优化同时推进底层查找、运行时过滤和预聚合成本估算；这几个机制解决的是不同环节的问题。
- CSV 块扫描、高核内存分配和及时归还预读预算，分别减少解析工作、资源争用和不必要的落盘。
- 2.0 维护分支合入多批回移，下一批仍在评审。官网发了两篇实践文章，本周未见新稳定版。

## 查询执行：不仅要能过滤，还要赶在扫描之前

- **已合入 main。** [#27620](https://github.com/duckdb/duckdb/pull/27620)（smvv）让通用哈希连接根据构建端的实际整数键范围选择直接寻址，不再依赖优化器预先证明键范围足够紧凑。[#28726](https://github.com/duckdb/duckdb/pull/28726)（Richard-Durkee）让适合的小构建端多键连接能为单个键列分别生成 Bloom 或前缀范围过滤，扫描可先排除无望匹配的行，但仍要检查完整连接键。
- **已合入 main。** [#28768](https://github.com/duckdb/duckdb/pull/28768)（smvv）解决的是过滤器的到达时机，而非寻找新的下推目标：允许某些已有目标等待小构建端先发布过滤器，同时避免循环依赖。这与 #28726 增加可用过滤器互补，不能据此推断所有查询都减少物理 I/O。
- **已合入 main。** [#28521](https://github.com/duckdb/duckdb/pull/28521)（kryonix）让递归 CTE 的连接排序显式考虑哈希构建峰值内存，避免递归前沿被错误放大；[#28766](https://github.com/duckdb/duckdb/pull/28766)（lnkuiper）按两侧完整分组键集估算预聚合，避免把几乎不减行的聚合放到连接下方。[#28784](https://github.com/duckdb/duckdb/pull/28784)（hawkfish）则仍**开放**：本周补上共享物化 CTE 的提前停止回归，避免为一个消费者省工作时误截断另一个消费者的输入。

## 扫描与并行：减少解析、争用和预算占用

- **已合入 main。** [#28466](https://github.com/duckdb/duckdb/pull/28466) 与 [#28607](https://github.com/duckdb/duckdb/pull/28607)（PeterVanHolland）让 CSV 先按 64 字节块扫描，再对未投影列跳过值组装。宽 CSV 只选少数列时可少做工作，仍需识别分隔符、引号等记录结构。
- **已合入 main。** [#28622](https://github.com/duckdb/duckdb/pull/28622)、[#28707](https://github.com/duckdb/duckdb/pull/28707)、[#28748](https://github.com/duckdb/duckdb/pull/28748)（lnkuiper）从并行哈希构建、按 NUMA 节点分片的块分配器及 Linux 首次触页三个层面减少争用。并行化也带来平台边界：[#28682](https://github.com/duckdb/duckdb/pull/28682)（h4nsmuller，已合入 main）修正 Windows 32 位上哈希表并行插入时的读取问题。高核实验不能外推到所有机器。
- **已合入 main。** [#28687](https://github.com/duckdb/duckdb/pull/28687)（anhphanmd）在扫描耗尽时归还预读内存，后续算子不用等整个查询结束才拿回预算。这和 **仍开放**的 [#28504](https://github.com/duckdb/duckdb/pull/28504)（Richard-Durkee）不是一回事；Mark Raasveldt（Mytherin）在[评审](https://github.com/duckdb/duckdb/pull/28504#discussion_r4510986383)建议按实际延迟与带宽考虑并发，而不是把本地和远程文件当作固定性能类别。不能把这场讨论解读成更换 I/O 后端。

## 升级、恢复与扩展：分清主线、回移和发行

- **已合入 main。** [#28701](https://github.com/duckdb/duckdb/pull/28701)（DinosL）按 Mytherin 的[评审建议](https://github.com/duckdb/duckdb/pull/28701#issuecomment-6800229199)先在主线回退原地 `UPDATE … FROM` 的多匹配去重，解除大批更新上的共享锁开销；同一目标匹配多条源行时，又可能按匹配次数更新、计数和返回。[#28742](https://github.com/duckdb/duckdb/pull/28742)（DinosL，已合入 main）修的是另一条路径：跨行组追加时 `RETURNING` 少返回行，不是恢复去重。

- **已合入 main。** [#28580](https://github.com/duckdb/duckdb/pull/28580)（ywelsch）保留 v1.x 持久化的 `lead/lag` 偏移与默认值；[#28599](https://github.com/duckdb/duckdb/pull/28599)（jeewonhh）恢复旧 ASOF 计划的额外谓词。它们避免的是升级后 SQL 仍能运行、结果却悄悄改变。[#26814](https://github.com/duckdb/duckdb/pull/26814)（artjomPlaunov）则要求先处理索引的待回放更改，无法处理时保留 WAL 并跳过检查点，避免漏持久化索引条目。
- **已合入 main。** [#27334](https://github.com/duckdb/duckdb/pull/27334)（artjomPlaunov）在失败提交无法撤销部分写入时使受影响数据库失效；[#28650](https://github.com/duckdb/duckdb/pull/28650)（Robinho-MR）允许把某些不可恢复错误隔离到单个可分离附加库。另有三项**开放提案**：[#28833](https://github.com/duckdb/duckdb/pull/28833)（sohamm20，旧版 WAL 重放兼容）、[#28837](https://github.com/duckdb/duckdb/pull/28837)（zaidrain06，跳过 WAL 时的快照可见性）和 [#28847](https://github.com/duckdb/duckdb/pull/28847)（gulugulubing，内存库检查点失败时的清理）。
- **仍开放。** [#27989](https://github.com/duckdb/duckdb/pull/27989)（ywelsch）本周把大表 `ADD COLUMN` / `ALTER TYPE` 的列重写移入物理执行流水线；提案可按行组并行处理并接入进度、取消和超时，目标是减少全表重写的内存与临时空间压力。
- **扩展与边界。** 主线的 [#28647](https://github.com/duckdb/duckdb/pull/28647)（Robinho-MR）新增仍标为 unstable 的 C++ 表函数扩展点，让扫描初始化可接收部分过滤条件，并接入虚拟列、指标和统计。[#28570](https://github.com/duckdb/duckdb/pull/28570)（carlopi）也已合入主线，为新增扩展仓库加上显式启用门槛。另有已合入 **2.0 维护分支**的 [#28705](https://github.com/duckdb/duckdb/pull/28705)（autograaf），更新 Vortex 并开启支持的 Windows 构建；这不表示现有稳定二进制已经包含它。
- **维护分支。** [#28602](https://github.com/duckdb/duckdb/pull/28602)、[#28710](https://github.com/duckdb/duckdb/pull/28710) 与 [#28746](https://github.com/duckdb/duckdb/pull/28746)（Robinho-MR）已合入 `v2.0-cyanoptera`；[#28812](https://github.com/duckdb/duckdb/pull/28812) 仍**开放**，包含预读预算回收与部分连接过滤回移。[自动评审](https://github.com/duckdb/duckdb/pull/28812#pullrequestreview-5900084326)指出候选分支存在普通外键元数据和旧 `UPDATE … FROM` 序列化计划的兼容问题；这是候选代码的报告，不是已发布回归。[官方 Releases](https://github.com/duckdb/duckdb/releases)核查时最新稳定版仍为 **2.0.0**；[日历](https://duckdb.org/release_calendar)列出的 2.0.1 日期是计划，不是发行确认。

## 官网文章

- **11 月 10 日**，[Ducks in a Column](https://duckdb.org/2026/11/10/ducks-in-a-column)（DuckDB 团队）。用查询示例区分列式存储、向量化、列投影与行组剪枝。实践上，少读几列和跳过整组数据是两种收益，后者还取决于过滤条件与数据布局。
- **11 月 12 日**，[Local Analytics Doesn’t Need a Database Server](https://duckdb.org/2026/11/12/local-analytics-without-a-database-server)（Ilya Boyandin、Geertjan Wielenga、Tim Cox）。用地图和图数据应用说明 SQLRooms 如何把查询放进浏览器或桌面端。少运维一个数据库服务器，不代表数据一律离线：文中浏览器案例仍从对象存储获取 Parquet。

## 方向观察（推测）

连接过滤的**生成**、过滤器的**就绪时机**和预读预算的**释放时机**分别出现独立改进。这表明除优化单个算子外，控制算子何时开始工作、何时交还资源，也可能减少中间数据与落盘。回移批次的兼容评审则说明，主线收益不能直接换算成补丁版收益。这是从本周 PR 得出的观察，不是项目路线图。

## 覆盖与限制

读取了仓库 11 月 9–15 日全部 7 篇日报，并按精确 UTC 窗口分页核对 [主仓库 PR](https://github.com/duckdb/duckdb/pulls)（174 项合并、251 项新建，可能重叠），对重点条目回查作者、目标分支和讨论，另核 [官网](https://duckdb.org/news/)与官方发布记录。历史评论与评审没有全量快照，晚于窗口的更新时间不当作周内事件；未独立复跑 PR 的测试和基准。
