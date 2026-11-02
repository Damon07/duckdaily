---
title: "DuckDB 周报 · 2026-10-26—2026-11-01：紧凑执行、选择性 I/O 与事务边界"
date: 2026-11-01 12:00:00 +0800
description: "NUMA、紧凑向量、Parquet 页索引和连接过滤进入主线；事务隔离与并发写冲突修复落地，VARIANT 和远程 I/O 仍在迭代。"
coverage_date: "2026-11-01"
permalink: /weekly/2026/11/01/
---

## 范围与本周结论

覆盖完整北京时间 **2026-10-26（周一）00:00 至 2026-11-02（周一）00:00，不含终点**，对应 UTC **10 月 25 日 16:00 至 11 月 1 日 16:00**。实际检查：**2026-11-02 09:01–09:05，北京时间**。下文日期均为北京时间，状态取检查时；开放方案的窗口后修订另行注明。

- **性能工作从局部循环扩展到数据表示、访存与调度。** NUMA、常量/字典中间结果、窗口和连接过滤、Parquet 页索引构成相互关联但不能简单叠加收益的一组改动。
- **事务与生命周期修复同样重要。** 批量插入可见性、同一行并发写冲突、递归状态和缓冲释放的边界被收紧，不能只按“提速”理解。
- **扩展接口继续分层；VARIANT 与自适应远程读取仍是提案。** Mark 的设计审查推动缩小核心接口范围，不代表所有原始设想已获接受。

[官方 Releases](https://github.com/duckdb/duckdb/releases)核查时最新正式版本仍为 **[v2.0.0，10 月 21 日发布](https://github.com/duckdb/duckdb/releases/tag/v2.0.0)**，本周未见新的正式 release。**以下 merged 表示代码已合并，不等于当前稳定安装包已包含。** 回补 PR、版本映射与 storage version 标记也不是发行公告。

## 一、减少物化、访存与内存生命周期成本

以下均在本周合并（merged），但改善的层次不同。

- **多核与排序**：[NUMA / many-core #27782](https://github.com/duckdb/duckdb/pull/27782)（**lnkuiper，10/27**）改善哈希分区任务局部性、预取与分配；[外部排序 #27783](https://github.com/duckdb/duckdb/pull/27783)（**lnkuiper，10/26**）减少重复溢写并改善偏斜分区处理。作者基准依赖硬件、数据和查询，不能合并成一个通用加速数字。
- **保留紧凑表示**：[ColumnDataCollection #27380](https://github.com/duckdb/duckdb/pull/27380)（**kryonix，10/27**）让常量和字典跨中间结果物化保留，仍使用可 spill 的 buffer-managed blocks；[延迟 Vector 分配 #27751](https://github.com/duckdb/duckdb/pull/27751)（**lnkuiper，10/26**）推迟 payload 分配。前者不是所有消费者端到端零拷贝，后者的作者热查询对照也不足以证明普遍加速。
- **及时释放与少争锁**：[partial block 副本释放原 buffer #28129](https://github.com/duckdb/duckdb/pull/28129)、[已 pin 块快速路径 #27798](https://github.com/duckdb/duckdb/pull/27798)（均 **ywelsch，10/31**）分别减少小压缩段占用整块内存、降低并行写入反复 pin/unpin 的锁竞争；首个 pin、最后一次 unpin 等仍需锁。[小结果缓存 #27996](https://github.com/duckdb/duckdb/pull/27996)（**DinosL，10/31**）从小容量开始并延迟分配，但仍按行数而非字节数控制。
- **低内存边界**：[晚到内存压力下允许排序转 external #28003](https://github.com/duckdb/duckdb/pull/28003)（**Robinho-MR，10/30**）与 [JSON union_by_name 释放采样缓冲 #28005](https://github.com/duckdb/duckdb/pull/28005)（**DinosL，10/30**）解决不同的内存积累问题。不是调高 memory_limit，也不是承诺所有 OOM 已消失。

**为何重要：**中间表示、buffer 生命周期与锁竞争往往比单个表达式更决定多核或内存受限负载的表现。验证时应分开观察峰值内存、spill、CPU 与实际耗时，而非把各 PR 的作者倍率相乘。

## 二、过滤必须到达读取层，也必须赶上扫描

- **Parquet 从行组走向页级裁剪**：[页索引 #27326](https://github.com/duckdb/duckdb/pull/27326)（**h4nsmuller，10/29，merged**）加入 ColumnIndex/OffsetIndex 读写及候选页读取。**读取默认启用，写入 WRITE_PAGE_INDEX 默认关闭**；显式启用且未另设页大小时才采用 1 MiB，加密文件不写页索引。
- **处理反复点查与同步等待**：[缓存感知读大小 #27772](https://github.com/duckdb/duckdb/pull/27772)（**h4nsmuller，10/30，merged**）在缓存碎片和内存条件符合时改读整列块，并吸收已有小块；[不能 park 的扫描并行 I/O fallback #27690](https://github.com/duckdb/duckdb/pull/27690)（同作者，**10/29，merged**）避免同步等待把独立读取串行化。不是无条件扩大所有预取。
- **规划、过滤与调度协同**：[窗口连接下推 #27739](https://github.com/duckdb/duckdb/pull/27739)（**hawkfish，10/26，merged**）在函数依赖、唯一性等条件允许时减少进入 WINDOW 的行数；[连接过滤 #28059](https://github.com/duckdb/duckdb/pull/28059) 与 [后续改进 #28086](https://github.com/duckdb/duckdb/pull/28086)（**lnkuiper，10/29、10/30，merged**）拓展安全下推路径，并让适合的扫描等待过滤构建。NULL、可抛错表达式和循环依赖仍是限制，不是任意过滤都能穿透任意算子。
- **基数更贴近过滤后值域**：[#28013](https://github.com/duckdb/duckdb/pull/28013)（**lnkuiper**）和 [GROUP BY 值域上界 #28021](https://github.com/duckdb/duckdb/pull/28021)（**h4nsmuller**）均 **10/29 merged**，分别改善 SEMI/ANTI、分组估计及有限类型值域上界；信息不足时仍回退，不保证总能选到最优计划。

**仍待验证：**[按网络吞吐/延迟调整远程 split #28138](https://github.com/duckdb/duckdb/pull/28138)（**pdet，10/30 新建，open**）和 [先做 min/max 再读取 Bloom filter #28199](https://github.com/duckdb/duckdb/pull/28199)（**quentin-sommer，11/1 新建，open**）继续减少请求成本。前者需评估不同带宽/延迟下的并行度，后者保留未被统计排除行组的 Bloom 检查；两者尚未落地。

## 三、事务语义、索引和递归状态：升级时不能忽略的修复

- **批量插入隔离与失败清理**：[ #27764](https://github.com/duckdb/duckdb/pull/27764)（**Robinho-MR，10/28，merged**）用插入事务 ID 保持提交前不可见，并在提交追加失败时清理已追加行、索引及行组，守住快照隔离和失败原子性。
- **同一行的写写冲突收紧**：[#26676](https://github.com/duckdb/duckdb/pull/26676)（**ywelsch，10/31，merged**）检测 DELETE 与 UPDATE 的交错，避免静默丢写。**同一行不同列的并发 UPDATE 也会冲突**，应用应准备事务重试。这是行为边界变化，不是提高并发度的宣传。
- **批量按 row-id 回取**：[#27383](https://github.com/duckdb/duckdb/pull/27383)（**ywelsch，10/29，merged**）以 scan/select 窗口替代逐行压缩 fetch_row，减少删除提交及索引清理中的重复解码，同时确保字符串不引用失效缓冲。
- **递归执行状态**：[#28079](https://github.com/duckdb/duckdb/pull/28079) 与 [#28126](https://github.com/duckdb/duckdb/pull/28126)（**kryonix，均 10/30 merged**）分别将每轮状态失效与延迟初始化分开，并清空 recurring 累计集合，避免多分支递归、重复执行或嵌套递归继承错误状态。
- **未完成的风险点**：[流式 CTE 背压死锁 #27936](https://github.com/duckdb/duckdb/pull/27936)（**kryonix，10/27 新建，open**）、[部分向量回滚残留 insert ID #28190](https://github.com/duckdb/duckdb/pull/28190)（**fastio，10/31 新建，open**）与 [DELETE→ALTER→建索引提交布局 #28205](https://github.com/duckdb/duckdb/pull/28205)（**fastio，11/1 新建，open**）仍需评审。它们分别涉及调度活性、回滚版本信息和新旧存储布局，不能因同周其他修复合并就宣布已全部解决。

## 四、绑定器与扩展：统一接口，同时缩小设计承诺

- [函数重载选择与绑定统一 #27703](https://github.com/duckdb/duckdb/pull/27703)（**Maxxen，10/28，merged**）复用已选函数、推导类型和参数映射，模板推导失败可继续尝试候选，并给出更具体的错误。这里落地的是绑定基础设施，不是作者展望中的所有新函数能力。
- [pre-bind hook #27872](https://github.com/duckdb/duckdb/pull/27872)（**Richard-Durkee，10/28，merged**）为扩展在绑定前启动远程目录加载提供入口。[Mark / Mytherin 10/26 的审查](https://github.com/duckdb/duckdb/pull/27872#issuecomment-6415467210)指出仅遍历原始语法树无法正确展开 CTE/视图，促使方案转为通用 hook；**不是核心已经实现完整目录批量预取**。
- [嵌套连接 #27264](https://github.com/duckdb/duckdb/pull/27264)（**carlopi，10/27，merged**）传播外层中断/期限并约束深度；[绑定期、线程安全 profiler 指标 #28117](https://github.com/duckdb/duckdb/pull/28117)（**Richard-Durkee，10/30，merged**）让目录请求计数和耗时更容易进入 profile，但预编译绑定时的值不自动保留到后续执行。
- **接口正确性与迁移**：[C API V2 聚合误去重 #28118](https://github.com/duckdb/duckdb/pull/28118)（**sbrunk，10/31，merged**）区分同签名但不同身份的聚合；[ODBC 更新及恢复自动加载 #27860](https://github.com/duckdb/duckdb/pull/27860)（**staticlibs，10/31，merged**）配合 C API V2，外部访问检查不是被取消，而是已在扩展上游实现。
- **凭据设计仍在评审**：[#27799](https://github.com/duckdb/duckdb/pull/27799)（**SrikanthKandula，open**）本周多次修订。Mark 在 [10/30 评审](https://github.com/duckdb/duckdb/pull/27799#pullrequestreview-5710637402)要求先仅支持经 OpenFileInfo 携带 secrets，secret management 层留待后续。不能把完整凭据生命周期设想写成已接受设计。

Mark 本周的可核实贡献主要体现为上述设计审查与多项事务/存储修复的合并维护，而不是新建 PR 数量；作者与合并维护者不混为一谈。hannes 推进了页索引及并行 I/O fallback 合并。

## 五、SQL 兼容与下一批开放优化

**已合并的 SQL 边界：**[旧存储箭头 lambda #27122](https://github.com/duckdb/duckdb/pull/27122)（**xproblematique，10/26**）恢复低于 2.0 存储版本中已存视图/宏的绑定，不恢复新 SQL 的旧语法；[标量宏 RETURNS #27889](https://github.com/duckdb/duckdb/pull/27889)（**kryonix，10/29**）可约束返回类型，但持久化要求 v2.1.0 storage version，这不是该版本已经发布；[TRY 标量子查询 #27386](https://github.com/duckdb/duckdb/pull/27386)（同作者、同日）采用绑定后逻辑改写，WHERE、连接条件和聚合内部等错误仍可能传播，不是全执行边界兜底。

**开放优化，当前均 open：**

- [公共子计划 #28144](https://github.com/duckdb/duckdb/pull/28144)（**lnkuiper，10/30 新建**）尝试让不同输出选择共享扫描和符合成本条件的小连接；不能只凭可共享就忽略物化代价。
- [短语句减少全局锁 #28204](https://github.com/duckdb/duckdb/pull/28204) 与 [稀疏 UPDATE 只取命中行基础值 #28206](https://github.com/duckdb/duckdb/pull/28206)（**dentiny，11/1 新建**）针对多连接短请求与压缩数据点更新的固定开销，作者局部基准不是一般分析查询的收益保证。
- **VARIANT 保留拆分表示**：[COUNT #28175](https://github.com/duckdb/duckdb/pull/28175)、[整数比较键 #28194](https://github.com/duckdb/duckdb/pull/28194)、[缺字段常量 NULL #28209](https://github.com/duckdb/duckdb/pull/28209)（均 **OneCyrus，10/31–11/1 新建**）分别减少为读有效位、比较或判缺键而重建通用值。各有 flat/fully-shredded 等前提，不适用仍回退。
- [VARIANT 字段拆分边界 #28195](https://github.com/duckdb/duckdb/pull/28195)（**OneCyrus，10/31 新建**）本周从出现率门槛推进到最多 32 字段并保留门槛；**窗口之后**（11/2 01:19）又改为只选最常见的 32 字段、去掉出现率门槛。当前方案仍未合并，变化本身说明策略尚未定型。

## 官方博客：两篇新文，不能混成两次功能发布

- **[Gems of DuckDB 2.0.0](https://www.duckdb.org/2026/10/26/gems-of-duckdb-200)**，**10/26**，**Gábor Szárnyas、Geertjan Wielenga**。补充已发布 2.0 的实用功能，包括 Python Appender、CLI 函数手册/历史、配置查询和自定义分区路径，以及扩展兼容矩阵、窗口函数扩展接口。实践上，程序生成行可用 Appender，已有 DataFrame/Arrow 仍可走批量 SQL；升级还要核对扩展平台支持。这不是本周 merged PR 的发行公告。
- **[From Spreadsheets to DuckLake: A Data Engineer's Road to DuckDB](https://www.duckdb.org/2026/10/29/from-spreadsheets-to-ducklake)**，**10/29**，**Matt Martin、Geertjan Wielenga、Tim Cox**。用户案例围绕熟悉的 SQL、更少基础设施和 SQL 元数据管理展开，讨论 DuckLake、异步 I/O 与 Quack 的实践。启示是按工作负载需要选择复杂度，而非宣称分布式系统已无必要；文中的 alpha 体验属于访谈历史语境，不能改变 2.0 已于上周发布的事实。

## 方向观察（推测）

1. **从“算得快”到“少展开、少读取、少等待”形成较一致的优化线索。**证据包括紧凑中间表示、页裁剪、缓存策略、连接过滤和锁快速路径；但 opt-in 写索引、消费者 Flatten、不同内存记账说明尚不是统一完成的自适应架构。
2. **复用与并发越深入，生命周期与语义验证越关键。**事务可见性、递归状态和缓冲释放修复，与性能改动同时出现。不能据此认定所有新增优化都存在问题，也不能只看作者基准忽略正确性回归测试。
3. **核心与扩展的边界倾向于小接口、分阶段落地。**pre-bind 已合并，凭据层仍被要求缩减范围；VARIANT 等同作者提案群则尚未形成发布承诺。以上是基于公开证据的归纳，**不是官方路线图**。

## 来源覆盖与限制

- 读取仓库 **10/26–11/1 七篇日报**作为线索，再独立分页检索公开 GitHub API：五页共 **441 个自周窗口起更新的候选 PR**，另两页精确窗口检索 **165 项合并**，均返回 incomplete_results=false。候选包含窗口后活动；入选按创建、合并、提交或评审时间区分，未把机器人标签变化当技术成果。
- 对本文重点回查官方详情、最终 changed-file patches 和必要的原始评论/评审；不是简单拼接日报，也不是对全部 441 项的全历史审计。特别检查指定核心作者，同时保留其他贡献者的重要工作。
- 官网新闻列表、上述两篇博客正文和官方 GitHub Releases 均可读取；**RSS feed.xml 因工具不支持 XML 未成功核对**。博客按官网标注日期归档，不臆测精确上线时刻，亦不把 feed 读取失败当成零更新。
- 状态与开放补丁是检查时快照，窗口后的设计迭代已单列；没有复跑性能实验或测试，没有访问私有仓库、内部 issue 或用户资料。性能观点不构成跨负载保证，是否已随稳定版交付应以实际发行记录为准。
