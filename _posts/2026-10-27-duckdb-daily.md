---
title: "DuckDB 日报 · 2026-10-27：NUMA、紧凑向量与索引扫描改进合并"
date: 2026-10-27 12:00:00 +0800
description: "多核与热循环优化、物化过程保留常量和字典向量、ART 谓词识别及 CTE 规划改进进入主线；索引回滚修复落地，流式 CTE 死锁与 Parquet 内容定义分块仍为提案。"
coverage_date: "2026-10-27"
---

## 覆盖窗口与状态口径

北京时间 **2026-10-27 00:00 至 2026-10-28 00:00（不含终点）**，对应 UTC 10 月 26 日 16:00 至 10 月 27 日 16:00。实际核查：北京时间 **2026-10-28 09:01–09:06**。

下文“已合并”指进入官方仓库主线，并不表示稳定版已经包含。官方发布记录最新仍为 10 月 21 日的 [v2.0.0](https://github.com/duckdb/duckdb/releases/tag/v2.0.0)，未见窗口内新正式版本。性能数字若引用，均是作者在特定配置下的报告，不是本站复测或普遍保证。

## 今日速览

- **执行与内存布局一起减负。** 多核/NUMA、热点循环及聚合循环不变量优化合并；ColumnDataCollection 开始保留常量与字典表示，减少物化时展开复制。
- **让选择性过滤真正到达执行路径。** ART 支持上下界合取，等值 OR 可转为 IN 下推；视图子查询与递归 CTE 的部分规划回退得到修复。
- **正确性与可诊断性同步补齐。** COMMENT ON INDEX 回滚误删底层索引修复落地，溢写 I/O 统计补全；新的流式 CTE 死锁修复仍开放，不能当作已发布解决方案。

## 重要 PR

### 1. 多核/NUMA 优化进入主线

[**#27782 — Many-core/NUMA improvements**](https://github.com/duckdb/duckdb/pull/27782) · 作者 **lnkuiper** · **merged**，北京时间 10 月 27 日 00:49 合并。

改动覆盖 hash join/聚合桶预取、按 radix 分区与 CPU 邻近关系安排构建工作、减少 false sharing、复用大块分配，以及聚合行初始化和任务调度成本。作者在双路 96 核机器的 TPC-H SF100 特定查询上报告改善，也报告较小机器上的收益；不能由此推导所有查询或所有 NUMA 拓扑都会加速。

值得注意的是，评审曾发现溢写聚合临时写入放大，作者随后修正并报告恢复到原先水平。最终补丁已纳入相应预算/初始化调整，不能把早期回归直接当作最终合并状态，也不能把作者确认视为所有溢写场景的全面证明。

### 2. ColumnDataCollection 保留紧凑向量，避免物化即展开

[**#27380 — Preserve constant and dictionary vectors in ColumnDataCollection**](https://github.com/duckdb/duckdb/pull/27380) · 作者 **kryonix** · **merged**，23:19 合并。

追加时识别 CONSTANT/DICTIONARY，常量只保存值与行数，字典按 segment 复用；允许零拷贝的扫描返回对应向量表示，数据仍使用普通 buffer-managed blocks，可参与溢写。新字典还有覆盖率门槛，避免少量行引用大字典反而增加开销；不适用的输入继续走 flat 路径。

这项合并也体现了 **Mark Raasveldt（Mytherin）此前审查的实际影响**：[10 月 19 日的意见](https://github.com/duckdb/duckdb/pull/27380#issuecomment-6262158231)建议优先面向更常见的字典字符串与常量，而非先为重复 list 引入侵入式机制。此处是合并背景，不是声称 Mark 昨天才提出该意见。最终版本还让部分消费者使用向量迭代器；嵌套类型、部分窗口边界访问及 Parquet 写入仍存在展开或后续优化边界，不能概括为所有中间结果已端到端零拷贝。

### 3. 热循环与聚合循环消除重复工作

- [**#27905 — Optimise some hot loops**](https://github.com/duckdb/duckdb/pull/27905) · **lnkuiper** · **merged**，22:54 合并。批量布尔选择用于表达式及字典过滤，改进 join 匹配压缩、整数过滤/bitpacked 解码，并外提不变量；同时覆盖映射选择向量的正确性。
- [**#27859 — Cache invariant chunk counts in aggregate hash-table loops**](https://github.com/duckdb/duckdb/pull/27859) · **redox** · **merged**，12:56 合并。缓存 rehash 和 Perfect Hash 循环中的 chunk 行数，减少反复读取元数据。改动很小，但针对高频内环；作者的特定硬件微基准不应等同于整套工作负载收益。
- [**#27960 — More hot loop optimisations**](https://github.com/duckdb/duckdb/pull/27960) · **lnkuiper** · **open**，23:47 新建。继续提议 Bloom probe 预取、按 validity word 选 NULL、批量窗口 segment-tree 叶更新等。它与已合并的 #27905 是不同状态，尚未落地。

### 4. ART 更好地识别已有 SQL 谓词

- [**#27926 — Use ART index scans for range conjunctions on the indexed column**](https://github.com/duckdb/duckdb/pull/27926) · **dentiny** · **merged**，19:58 合并。识别同一索引表达式的一对上下界，使被改写为 AND 的 BETWEEN 等范围条件可用索引扫描。最终实现要求精确覆盖支持的条件，不能扩展解读为任意残余过滤、多列条件或复合索引均已支持。
- [**#27929 — Push OR of equalities down as an IN filter**](https://github.com/duckdb/duckdb/pull/27929) · **dentiny** · **merged**，19:42 合并。同列的等值 OR 在适用时下推成索引可识别的 IN 过滤；稠密范围优化仍优先保留。意义在于减少等价写法造成的计划落差，而不是承诺每个 IN 都会选择索引。

### 5. 视图、UNION ALL 与递归 CTE 规划回退得到收窄修复

- [**#27760 — Push view filters below delim joins and plan many UNION ALL subqueries in linear time**](https://github.com/duckdb/duckdb/pull/27760) · **Robinho-MR** · **merged**，20:30 合并。让符合安全条件的视图过滤越过更多 delim join 形态，减少先执行大量子查询再过滤的工作；无相关绑定时避免反复遍历 UNION ALL 分支。线性化针对所修复的无关子查询规划路径，不是所有相关计划复杂度的保证。
- [**#27089 — Restrict recursive partitions of CTE-decorrelated lateral joins**](https://github.com/duckdb/duckdb/pull/27089) · **kryonix** · **merged**，17:37 合并。让部分选择性关联键更早限制递归分区，并为复制源扫描增加成本门槛。最终版本按审查收窄到适合补丁修复的范围；深层 lateral、部分 EXISTS 等更一般形态仍未在本 PR 全面解决。[当天审查确认](https://github.com/duckdb/duckdb/pull/27089#issuecomment-6438023120)不能理解为未来版本已发布承诺。

### 6. 两项回滚修复：索引完整性与 checkpoint 快路径

- [**#27902 — Don't remove the index when rolling back a comment on it**](https://github.com/duckdb/duckdb/pull/27902) · **ywelsch** · **merged**，18:08 合并。回滚 COMMENT ON INDEX 时，保留与前一目录项共享 OID 的底层索引，避免 UNIQUE 校验失效以及后续 checkpoint/重新打开异常。这是值得优先关注的正确性修复；回补诉求不等于已有稳定版更新。
- [**#25587 — Fix rolled-back DELETE poisoning uncheckpointed_delete_commit**](https://github.com/duckdb/duckdb/pull/25587) · **dentiny** · **merged**，02:26 合并。最终代码以已提交删除为条件更新 checkpoint 相关标记，避免回滚/撤销删除长期阻断元数据复用快路径。这里依据合并 diff，而非原描述中的旧字段与哨兵判断。

### 7. 溢写统计补全，但仍不是所有写入都已计数

[**#27855 — Pass The Client Context Through ClientBufferManager Pins And Allocations So Spill I/O Is Counted**](https://github.com/duckdb/duckdb/pull/27855) · 作者 **Richard-Durkee** · **merged**，01:46 合并。

将客户端 QueryContext 传入相关 Allocate/Pin 路径，使 external hash join、窗口等经 ColumnDataCollection 发生的溢写读写更完整地归入查询指标。仍有 buffer allocator 触发的无上下文驱逐写入未完全统计；更准确的指标不应误读成“产生了更多真实 I/O”。

### 8. 扩展与内部连接：组合能力和取消边界

- [**#27264 — Nested connections**](https://github.com/duckdb/duckdb/pull/27264) · **carlopi** · **merged**，20:15 合并。内部连接关联调用者的基础上下文，约束嵌套深度并继承中断/查询期限，降低内部回调逃离外层控制的风险。
- [**#27289 — Add functions to add, list and remove grammar extensions**](https://github.com/duckdb/duckdb/pull/27289) · **Dtenwolde** · **merged**，18:49 合并。增删单个 grammar extension 不再必须覆盖整个激活列表，系统表增加 active 信息，CLI 开启 shell 语法时也不再挤掉其他扩展。
- [**#27387 — Improved error reporting for the parser**](https://github.com/duckdb/duckdb/pull/27387) · **Dtenwolde** · **merged**，18:25 合并。解析失败后利用语法验证补充错拼、缺失 token 或期望类别提示；不是未经验证地自动修改用户 SQL。

### 9. Late materialization 虚拟列修复

[**#27805 — Handle virtual columns when copying filters to late materialization LHS**](https://github.com/duckdb/duckdb/pull/27805) · 作者 **Flogex** · **merged**，00:32 合并。

复制过滤条件时通过 LogicalGet 的列类型接口处理 rowid 等虚拟列，替代把虚拟列标识直接当数组下标，修复相应 ORDER BY/LIMIT 查询的内部越界错误。

### 10. 尚未合并：流式 CTE 活性与 Parquet 内容定义分块

- [**#27936 — Fix idle deadlocks between materialized CTE exchange producers and gated buffered consumers**](https://github.com/duckdb/duckdb/pull/27936) · **kryonix** · **open**，15:38 新建。针对生产者被背压阻塞、消费者又等待其他阶段的空闲死锁，提出分离分析依赖与执行依赖、活性分析及保守回退物化，并加入可中断空闲等待的测试 watchdog。它是对更早修复思路的扩展，仍需评审验证，不能声称用户报告已由正式版本解决。
- [**#27911 — Parquet: cut data pages at content-defined boundaries**](https://github.com/duckdb/duckdb/pull/27911) · **lhoestq** · **open**，01:37 新建。拟按内容而非仅固定尺寸切数据页，以提高修改后文件在内容寻址/去重上传中的字节复用。仍输出普通 Parquet；提案限制在支持的顶层类型，row group 间状态与顺序写入是重要权衡，作者数字是特定 Xet/PyArrow 对照，不是普遍压缩率承诺。

## 官方博客

核查 [DuckDB Engineering Blog](https://duckdb.org/news/) 后，**未见标注 2026-10-27 的新文章**。最新仍是 10 月 26 日的《Gems of DuckDB 2.0.0》，不重复计入今天新文。RSS 请求返回 403，故这里是官网列表核查结论，而非成功读取全部 feed 后的绝对零更新判断。

## 方向观察（推测）

1. **优化重点正在同时覆盖数据表示、访存局部性与内环固定成本。** #27380、#27782、#27905、#27859 的合并是证据；但紧凑表示有适用门槛，多核收益受拓扑和溢写影响，不能简单累加各 PR 的性能数字。
2. **新执行/规划基础设施进入细粒度修复阶段。** CTE 下推、索引谓词识别、回滚与虚拟列处理均在减少计划落差和边界错误；#27936 仍开放说明流式调度尚有待验证的复杂形态。
3. **扩展组合与查询可控性受到重视。** grammar 增删与内部连接的期限传播提供了具体证据。这只是从当日变更归纳的趋势，不把单个作者提案当作官方路线图。

## 来源覆盖与限制

- GitHub 更新候选检索读取两页，共 **160 个 PR**，接口返回 incomplete_results=false；另用精确 UTC 窗口查询核实 **36 项合并**。候选包含窗口后更新，逐条按创建/合并时间筛选，并查重点 PR 详情、最终 diff 和相关讨论；不是把 updated_at 当作实质进展。
- 正文精选 **15 项已合并 PR、3 项新提案，共 18 项**，按主题去重。未穷举文档、CI 和小型改动；未对每个候选的全部历史讨论逐条审计。
- 特别注意日期边界：NUMA #27782 在北京时间 27 日凌晨合并；pre-bind hook #27872 和函数重载统一 #27703 的合并发生在北京时间 28 日，不计入本日合并。
- 官网页面与官方 release 记录可读取；RSS 403 限制如上。没有独立重跑各作者基准，也没有据回补标签推断正式发布。
