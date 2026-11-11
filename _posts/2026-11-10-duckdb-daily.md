---
title: "DuckDB 日报 · 2026-11-10：CSV 提速、升级兼容与持久化修复"
date: 2026-11-10 12:00:00 +0800
description: "CSV 块扫描与列跳过、Top-N 列剪枝和聚合域优化合并；旧版数据兼容、WAL 索引回放及外部访问边界继续补齐。"
coverage_date: "2026-11-10"
updated_at: 2026-11-11T09:04:46+08:00
---

覆盖时间：北京时间 2026 年 11 月 10 日 00:00 至 11 月 11 日 00:00（左闭右开），即 UTC 11 月 9 日 16:00 至 11 月 10 日 16:00。实际核查时间：北京时间 2026 年 11 月 11 日 09:04。下文时间均为北京时间，PR 状态为核查时状态；窗口结束后的合并单独注明。

## 今日速览

- CSV 的 64 字节块扫描与未投影列跳过相继合并，Top-N 窗口查询恢复列剪枝；优化重点是减少不必要的解析、读取与聚合工作。
- 索引 WAL 回放与 checkpoint 的正确性修复，以及多项 v1.x 到 v2.0 的序列化兼容修复值得升级用户关注。
- Mytherin 推动关闭外部访问时整体禁止 SQL secret 创建。官网另有标注 11 月 10 日的列式存储实践文章，属于教程而非版本发布。

## 重要 PR

### 1. CSV 扫描连续减少无效工作

作者均为 PeterVanHolland，核查时均为 **merged，合入 main**。

- [#28466 Scan CSV rows in 64-byte blocks](https://github.com/duckdb/duckdb/pull/28466)，**01:33 合并**：以 64 字节块扫描代替逐字节状态机，用可移植 SWAR 代码寻找分隔符、引号和换行等结构字符。不适用的方言与边界情况仍回退旧路径。作者在 96 核 AMD EPYC、缓存文件和显式 CSV 方言/类型的基准中，报告单线程扫描耗时最多下降约 34%，96 线程最多约 22%。
- [#28607 Skip unprojected CSV columns in the block scan](https://github.com/duckdb/duckdb/pull/28607)，**19:30 合并**：在块扫描基础上跳过查询不需要的字段值组装。作者报告少列扫描耗时进一步最多下降 37%（单线程）和 17%（96 线程），全列读取基本不变。[评审后的作者说明](https://github.com/duckdb/duckdb/pull/28607#issuecomment-6763942326)澄清：`count(*)` 仍读取并校验第一列 VARCHAR，lineitem 实际跳过 16 列中的 15 列，并非完全不读字段；同时补充错误行定位和成功 null padding 的测试。

两项数字采用不同基线，不能把最高增益直接相加；本文没有独立复测。

### 2. Top-N 窗口查询恢复列剪枝

[#28620 Read only the partition and order columns under the top-N window rewrite again](https://github.com/duckdb/duckdb/pull/28620)，作者 **ywelsch**，**22:29 合并，状态 merged**。

修复 v2.0 中 Top-N window elimination 与 late materialization 配合时，首遍扫描错误读取 payload 列的问题。现在首遍只读分组与排序所需列，之后再取胜出行的 payload，避免宽表数据重复加载。作者在 150 万行、每行 768 字节 payload 的特定测试中测得 0.077 秒降至 0.014 秒，表数据加载量由 740 MiB 降至 5.2 MiB。该 PR 带 v2.0 backport 标签，但标签不代表稳定版本已经包含修复。

### 3. checkpoint 前落实索引 WAL 回放

[#26814 Bind indexes with buffered replays before checkpoint starts, or skip it and keep the WAL](https://github.com/duckdb/duckdb/pull/26814)，作者 **artjomPlaunov**，**21:05 合并，状态 merged**。

重启后索引采用延迟绑定，WAL 回放会先缓冲索引操作。此前自动 checkpoint 可能在应用这些操作前序列化未绑定索引，造成索引条目丢失。修复将必要绑定移到 checkpoint 开始前；绑定失败时，自动 checkpoint 跳过并保留 WAL，显式 checkpoint 则报错。这项变化首先关乎持久化正确性。[评审讨论](https://github.com/duckdb/duckdb/pull/26814#discussion_r4522758693)还解释了为何要在正式 checkpoint 之前完成绑定，以处理失败和死锁风险。

### 4. v1.x 到 v2.0 的兼容性修复组

以下均已 **merged 至 main**，合并发生在本日窗口：

- [#28625 保留旧版整数类型参数字面量](https://github.com/duckdb/duckdb/pull/28625)，**ywelsch，22:47**：修复旧版固定数组等类型参数被改写为 cast 表达式的问题。涉及保留旧 storage version 时 checkpoint 失败并使数据库失效、`COPY FROM DATABASE` 失败，以及 `EXPORT/IMPORT` 无法往返。
- [#28599 保留旧序列化计划的 ASOF 额外条件](https://github.com/duckdb/duckdb/pull/28599)，**jeewonhh，15:53**：读回此前会被静默丢弃的额外 predicate，避免 ASOF join 匹配错误行。
- [#28592 修复旧 view/macro 中命名参数调用的子查询绑定](https://github.com/duckdb/duckdb/pull/28592)，**ywelsch，15:48**：不再预先复制无法复制的已绑定子查询，而是在确需回退时重新绑定解析后的参数。
- [#28605 保持旧 REPEATABLE sample 的固定种子语义](https://github.com/duckdb/duckdb/pull/28605)，**jeewonhh，18:44**：避免旧计划读入后变成随机采样，也避免面向 v1.5 的存储写入其不识别的新字段。

### 5. 聚合、类型转换与统计量优化

以下均已 **merged 至 main**：

- [#28579 DuplicateEliminatedDomainOptimizer](https://github.com/duckdb/duckdb/pull/28579)，**lnkuiper，16:54 合并**：新增基于成本的优化步骤，对支持的 grouping-key join，将聚合输入限制为下游实际需要的键。它在少算分组与键去重、SEMI join、CTE 物化/读取成本间取舍，支持固定或运行时键域及共享、嵌套 CTE。适用性取决于连接形态与成本模型，不意味着所有 `GROUP BY` 都会加速。
- [#28061 Serialize VARIANT directly when casting to VARCHAR](https://github.com/duckdb/duckdb/pull/28061)，**dentiny，23:06 合并**：直接从 VARIANT 编码写入可复用缓冲，减少逐行 Value 树、分配和重复 cast 绑定。作者在 Apple Silicon 单线程 reldebug 的特定嵌套数据基准中报告明显改善；这只针对 **VARIANT→VARCHAR**，不改变 VARIANT→JSON，部分特殊情况保留旧路径。
- [#28576 移除比较中可逆的 cast](https://github.com/duckdb/duckdb/pull/28576)与 [#28611 扩展支持的源类型](https://github.com/duckdb/duckdb/pull/28611)，**dentiny，分别于 00:30、20:04 合并**：让可安全改写的 equality/IN 谓词回到原列上，减少转换并恢复扫描下推和 row-group/segment 剪枝。后者扩展到 BOOLEAN、DECIMAL、UUID 和部分日期时间转换等。
- [#28140 通过 unstable v2 C API 报告列统计量](https://github.com/duckdb/duckdb/pull/28140)，**h4nsmuller，00:03 合并**：table function 可报告 min/max 等统计量，帮助优化器排除外部 reader 中不可能命中的扫描。入口受 `DUCKDB_V2_API_ALLOW_UNSTABLE` 保护，不能视为稳定 API 承诺。
- [#28632 Propagate list element statistics through UNNEST](https://github.com/duckdb/duckdb/pull/28632)，**kryonix，23:49 合并**：传播 list/array 元素统计量，让不可能满足的谓词折叠为空结果；多个 UNNEST 的 NULL padding 保守处理。这项改动不直接改变 UNNEST 节点基数估计。

### 6. 内存耗尽时避免二次异常

[#28508 堆耗尽时避免析构和 shell 错误处理再次分配](https://github.com/duckdb/duckdb/pull/28508)，作者 **h4nsmuller**，**21:53 合并，状态 merged**。修复 OOM 后清理路径再次分配内存、继而触发未捕获 `bad_alloc` 或 `terminate` 的问题。作者用分配故障注入检查初始化、查询、结果销毁及退出路径；这是对已识别路径的加固，不保证所有 OOM 场景都已解决。

## 当日新建与实质讨论

### NUMA：大核数收益也要检查小机器的代价

[#28622 More NUMA improvements](https://github.com/duckdb/duckdb/pull/28622)，作者 **lnkuiper**，**11 月 10 日 16:26 新建；核查时 merged，但直到 11 月 11 日 01:08 才合并**，不计入本日合并。

改动减少 shared ownership/refcount 流量，并调整 DECIMAL 元数据、dictionary ownership、hash build 并行化与 Bloom filter 局部性。作者预计 192 核 Graviton4 上 TPC-H SF100 总查询耗时约降 15%。评审要求补充中小核数测试后，作者[报告 8 核机器的倾斜数据退化](https://github.com/duckdb/duckdb/pull/28622#issuecomment-6766883425)，并将并行构建的 skew 阈值从 0.25 收紧到 0.20。动态类型元数据变大仍是代价，不能将大机器收益推广到所有负载。

### 外部访问关闭时的权限边界

- [#28637 Refuse CREATE SECRET when enable_external_access is false](https://github.com/duckdb/duckdb/pull/28637)，作者 **h4nsmuller**，**11 月 10 日 18:47 新建，核查时 open**。[Mytherin 当日要求](https://github.com/duckdb/duckdb/pull/28637#issuecomment-6765582740)从局部 env provider 修复扩大为整体拒绝 SQL secret 创建。作者随后补上管理器和绑定器入口检查，并[在选项表达式求值前拒绝](https://github.com/duckdb/duckdb/pull/28637#discussion_r4526500475)，避免先发生副作用再报权限错误。方案尚未合并。
- [#28635 Refuse ATTACH ... EXTERNAL RESOURCE when enable_external_access is false](https://github.com/duckdb/duckdb/pull/28635)，作者 **h4nsmuller**，**11 月 10 日 18:45 新建；核查时 merged，合并时间为 11 月 11 日 00:44**。当日[公开评审](https://github.com/duckdb/duckdb/pull/28635#discussion_r4524986542)指出仅检查语句 binder 不足，公共资源函数也要覆盖。本文将其归入本日新建与讨论，不列作本日已合并修复。

这些是公开 PR 中的权限检查改动，不能据此推定已发布安全公告或 CVE。

## 官方博客

[Ducks in a Column](https://duckdb.org/2026/11/10/ducks-in-a-column)，作者 **The DuckDB team**，官网标注发布日期 **2026-11-10**。

文章从列式存储减少读取量讲起，用 SQL 示例串起直接查询文件、列选择与变换、聚合、窗口函数和 ASOF JOIN，并介绍 Parquet 分区、排序与压缩。实践重点是只取所需列、按查询过滤方式组织文件，并用 `EXPLAIN ANALYZE` 检查实际读取和下推效果。这是一篇使用教程，不是新版本或新功能发布公告。

日期已与[官方新闻列表](https://duckdb.org/news/)及[官网源码目录](https://github.com/duckdb/duckdb-web/tree/main/_posts)交叉核对，未发现第二篇标注当日的文章。**官网只给出日期，没有精确发布时间；feed 因 XML 抓取限制未能读取，无法严格确认实际上线时刻属于本期北京时间窗口。** 因此按“官网标注 11 月 10 日”收录，不作精确上线时间断言。

## 方向观察

**推测：** CSV 列跳过、Top-N 列剪枝、聚合输入域和统计量传播，体现出减少无用工作的共同思路；升级兼容和索引回放修复则说明性能工作与正确性维护并行。外部访问讨论也在推动入口检查覆盖更多路径。

依据是本期多项独立 PR 及公开评审，但单日合并集合受开发节奏影响，不能上升为官方路线图。NUMA 的内存占用与倾斜数据权衡、CSV 的方言回退、优化器的成本限制，都提醒我们收益需要按实际数据和机器验证。

## 覆盖与限制

- 仅使用公开 DuckDB 来源。主仓库检索使用精确 UTC 边界：窗口内最后更新时间命中 112 项（两页），另查当日创建 40 项、合并 37 项、关闭 38 项，查询未报告截断。各集合重叠，不能相加；updated 与 created 联合去重得到 124 个候选。
- 重点筛选后核对 PR 正文、作者、合并时间及目标分支，并读取关键评论和评审，以实际创建、合并或评论时间判断事件归属，不把 `updated_at` 等同于当天完成。
- GitHub 的 updated 搜索使用最后更新时间：老 PR 若本日互动后次日再次更新，且本日未新建或合并，仍可能遗漏。没有逐时历史快照，当前 PR 正文也可能在窗口后编辑，因此不是全部历史互动的穷尽记录。
- 未运行 DuckDB 代码、独立复现性能测试或逐项代码审计。基准均为作者报告，适用范围见各条说明；引用公开 PR 说明不表示读取了其中链接的私有 issue。
- **合并至 main、带 backport 标签，都不等于稳定版本已发布这些变化。**
