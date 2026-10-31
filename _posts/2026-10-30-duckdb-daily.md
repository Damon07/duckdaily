---
title: "DuckDB 日报 · 2026-10-30：递归状态、内存边界与连接执行改进"
date: 2026-10-30 12:00:00 +0800
description: "递归 CTE、并行分位数与低内存执行修复合入主线；连接优化、远程读取和扩展统计接口继续推进。"
coverage_date: "2026-10-30"
---

## 覆盖时间

北京时间 **2026-10-30 00:00 至 2026-10-31 00:00**，左闭右开；对应 UTC **2026-10-29 16:00 至 2026-10-30 16:00**。实际核查时间：北京时间 **2026-10-31 08:56–09:00**。下文状态以核查时为准；窗口外后续进展会单独注明。**合入主线不等于已在稳定版发布。**

## 今日速览

- 递归 CTE 的迭代状态与重复调用、并行近似分位数的分配器归属得到修复，重点是避免错误结果及并发故障。
- Parquet 页索引缓存、JSON 多文件采样和排序转磁盘路径继续收紧内存与 I/O 边界；UUID/VARIANT 热路径减少逐行字符串分配。
- 连接过滤改进已合并；公共子计划、远程读取分块与 C API 统计能力仍是开放提案。Mark 对文件凭据方案提出缩小范围的评审要求。

## 已合并的重要 PR

以下各项均在报道窗口内合并，状态为 **merged**。

### 执行正确性与优化器

- **[More join filter pushdown improvements #28086](https://github.com/duckdb/duckdb/pull/28086)** · **lnkuiper**：沿等价内连接键寻找更多扫描目标，并通过符合安全条件的聚合、窗口算子传递过滤；对适合的扫描增加等待过滤构建的调度依赖，让过滤赶在扫描前生效，同时规避循环依赖。这不意味着所有扫描无条件等待，额外调度也不覆盖递归 CTE。
- **递归 CTE 的两个状态边界** · **kryonix**：[统一算子状态生命周期 #28079](https://github.com/duckdb/duckdb/pull/28079) 将每轮失效与初始化分离，共享状态每轮只失效一次，并在依赖完成后延迟重建，修复多分支递归成员的 LIMIT/OFFSET 语义及依赖 sink 状态的扩展算子初始化次序；[重置 recurring 状态 #28126](https://github.com/duckdb/duckdb/pull/28126) 则在每次递归调用时清空累计集合，防止预编译语句再次执行或嵌套递归继承旧结果。
- **[Fix parallel quantile corruption and flaky CI tests #28076](https://github.com/duckdb/duckdb/pull/28076)** · **kryonix**：并行合并近似分位数状态时，如果目标 digest 仍属于旧 sink 的 arena，就复制到当前合并分配器，避免不同分区并发增长同一 arena。还修复测试临时目录、端口及过滤表达式等隔离问题；这些测试调整不应全部理解为查询引擎错误。
- **[Window self-join drops frame ORDER BY tie-breakers #28029](https://github.com/duckdb/duckdb/pull/28029)** · **k9-doctor**：保留仍影响窗口结果的平局排序键，避免窗口自连接改写丢失必要顺序。最终补丁按参数排序能否已决定结果来判断，不是无条件追加所有 ORDER BY。
- **[Fix dict-surviving hash join internal error on UNNEST / cross product build sides #28087](https://github.com/duckdb/duckdb/pull/28087)** · **DinosL**：修正字典保留型哈希连接处理 UNNEST、笛卡尔积构建侧时的适用条件，避免内部错误；属于优化适用范围的正确性修复。

### 内存、存储与热路径

- **[Parquet page index: adapt the read size to what the cache already holds #27772](https://github.com/duckdb/duckdb/pull/27772)** · **h4nsmuller**：当反复点查留下多个小缓存块，且仍有缺失页面、列块也符合内存上限时，改读整个列块并吸收该范围的小缓存块，减少碎片间隙造成的额外请求。它平衡首次选择性读取与后续重复访问，不是一律扩大预取。
- **[Let a sort go external after a thread finished its run in memory #28003](https://github.com/duckdb/duckdb/pull/28003)** · **Robinho-MR**：允许部分线程已在内存中完成本地排序后，整体排序仍切换到外部执行。修补内存压力较晚出现时无法正确转向 spill 的边界。
- **[Fix OOM in read_json with union_by_name over many files #28005](https://github.com/duckdb/duckdb/pull/28005)** · **DinosL**：多文件按列名合并读取 JSON 时，及时释放不再需要的采样缓冲，避免文件数量增加导致采样内存累积。对大量小文件和异构 JSON 数据集尤其相关。
- **[Avoid per-row std::string allocations in UUID casts and VARIANT shredding #28048](https://github.com/duckdb/duckdb/pull/28048)** · **dentiny**：最终实现让 UUID 解析直接接收 `string_t`，并在 VARIANT 字段查找中复用字符串键及其存储，减少逐行临时字符串构造。作者的单线程特定数据基准显示收益，但本文未独立复测，不将其外推为通用加速比例。

### 扩展可观测性与兼容性

- **[Make Query Profiler Metrics Thread-Safe And Settable While Binding #28117](https://github.com/duckdb/duckdb/pull/28117)** · **Richard-Durkee**：为字符串指标的计时、计数和取值加锁，允许扩展在绑定阶段设置已注册指标，并新增外部测量时间的累加接口。目录请求数量与耗时因此更容易进入查询 profile；预编译绑定时记录的值不会自动保留到后续执行。
- **[2026f Time Zones #28108](https://github.com/duckdb/duckdb/pull/28108)** · **hawkfish**：更新 ICU 时区数据，覆盖古巴永久夏令时变更。依赖当地时间换算的工作负载需要关注数据版本；这里确认的是代码合并，不是稳定安装包已经更新。

## 新提案与实质评审

- **[Improve CommonSubplanOptimizer #28144](https://github.com/duckdb/duckdb/pull/28144)** · **lnkuiper** · **open**：北京时间 10 月 30 日 23:57 新建，核查时方案扩展不同输出列的共享扫描，并尝试让特定小型或高选择性内连接共享中间结果，保留各分支的剩余过滤；用基数与表达式安全条件约束物化。补丁已有窗口结束后的迭代，本日报只将其记为当日提出的工作，不将后续方案或性能当作当天已落地成果。
- **[Size remote read splits from the measured network throughput #28138](https://github.com/duckdb/duckdb/pull/28138)** · **pdet** · **open**：当日 22:16 新建，提议利用测得的网络吞吐调整远程读取拆分尺寸，使调度更适应连接条件。仍需评审及不同延迟、带宽场景验证，不是已发布的自适应 I/O 能力。
- **[Report table function column statistics via the unstable v2 C API #28140](https://github.com/duckdb/duckdb/pull/28140)** · **h4nsmuller** · **open**：当日 22:33 新建，为表函数向优化器提供 min/max 等统计、构造统计对象及检查谓词增加接口，并以 unstable 开关隔离。潜在价值是让外部 reader 的边界信息参与剪枝；统计必须对实际输出有效，接口也未承诺稳定。
- **[Branch-free probing for join hashtable #28081](https://github.com/duckdb/duckdb/pull/28081)** · **gropaul** · **open**：当日 21:54、23:47 的提交继续拆分哈希探测中的加载、向量检查和候选行压缩，并统一探测轮次的结果处理。作者报告部分多键连接获益，也披露聚集键可能变慢、构建侧超出缓存后收益有限；应按工作负载评估。
- **[Carry credentials on file opens and globs #27799](https://github.com/duckdb/duckdb/pull/27799)** · **SrikanthKandula** · **open**：Mark Raasveldt（**Mytherin**）在当日 19:24 的[评审](https://github.com/duckdb/duckdb/pull/27799#pullrequestreview-5710637402)要求先将范围缩小到通过 OpenFileInfo 携带 secrets，把 secret management 层及 secret-specific cache key 留到后续。重要进展是设计边界收敛，不能按旧 PR 描述写成完整凭据生命周期方案已获接受。

## 官方博客与发布边界

截至检查时，[官方新闻列表](https://duckdb.org/news/)最新条目仍为 10 月 29 日，未见 10 月 30 日新博客；官方域名定向搜索也未找到当日文章。[RSS](https://duckdb.org/feed.xml) 因读取工具不支持 XML 而未能核对，结论以新闻列表和搜索可见范围为限。

[版本发布列表](https://github.com/duckdb/duckdb/releases)核查时最新正式 release 仍为 **v2.0.0（10 月 21 日）**。本日报中的主线合并及开放 PR 不代表已进入稳定版；版本映射或回移分支的变更本身也不构成发行公告。

## 方向观察（推测）

- **执行复用越深入，生命周期约束越重要。** 递归状态、字典保留连接与并行 digest 的修复，都指向复用与并发边界上的正确性。这是对多项补丁的归纳，不表示这些机制此前所有场景都有问题。
- **I/O 优化正在同时考虑缓存和资源压力。** 页索引读取、JSON 采样释放与排序转磁盘已合并，网络感知分块仍待评审；它们成熟度不同，不能合称已完成的统一自适应引擎。
- **扩展与核心的协作接口继续细化。** 指标接口已落地，统计接口和凭据传递尚在讨论，尤其 Mark 对凭据方案的缩减要求说明实现仍需分层推进。这不是官方路线图。

## 覆盖与限制

从公开 GitHub API 分两页检查 **147 个自窗口起更新的候选 PR**，包括检查时已到次日的新活动；检索返回 `incomplete_results=false`。再按创建、合并、提交或评审时间筛选，识别 **32 项窗口内合并**，仅精选有实质影响的内容。对入选项核对 PR 元数据及最终补丁，评审条目另查原始讨论；不把 stale 标签、请求 review 或单纯 `updated_at` 变化当作技术进展。

开放 PR 的当前补丁可能包含窗口结束后的修改；本文明确区分事件时间与当前状态。没有独立运行性能基准或测试，也未将作者数据视为跨工作负载保证。官方 RSS 读取受限；公开搜索及 API 不能保证覆盖所有未索引讨论。仅使用公开社区资料。
