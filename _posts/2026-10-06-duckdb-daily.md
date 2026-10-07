---
title: "DuckDB 日报 · 2026-10-06：类型绑定拆分、延迟约束合并与写出内存治理"
date: 2026-10-06 12:00:00 +0800
description: "Mytherin 提议拆分标量函数类型解析与绑定，延迟唯一约束已合并；分区 COPY、Parquet 行组及哈希表内存路径继续改进。"
coverage_date: "2026-10-06"
---

覆盖窗口：北京时间 **2026-10-06 00:00 至 2026-10-07 00:00，不含终点**，对应 UTC 10 月 5 日 16:00 至 10 月 6 日 16:00。实际核查时间：**2026-10-07 08:57—09:01（Asia/Shanghai）**。下文事件时间均为北京时间，状态以核查时为准。

## 今日速览

- **类型解析与绑定拟分家。** Mytherin 新提案把标量函数的类型决策移到独立步骤；hannes 随即提交依赖该重构的 typed NULL 修复，两者仍为 open
- **延迟 PRIMARY KEY / UNIQUE 已合并。** 可以选择在事务提交时检查唯一性，但并不意味着外键、NOT NULL 和 ON CONFLICT 一并支持延迟语义
- **写出与内存路径多点落地。** 分区 COPY 背压、宽行 Parquet 行组尺寸控制及哈希表大页请求均已合并；各自都有明确适用边界

**已合并不等于已发布。** 核查[官方发布记录](https://github.com/duckdb/duckdb/releases)时最新正式版本仍为 [1.5.6](https://github.com/duckdb/duckdb/releases/tag/v1.5.6)，发布时间为 9 月 28 日；不能把下述开发分支能力视作该正式版已包含。

## 重要 PR

### 1. Mytherin 拆分标量函数类型解析，hannes 跟进 typed NULL 修复

[PR #26548 — Split up ScalarFunction::bind into resolve_types and bind](https://github.com/duckdb/duckdb/pull/26548)，作者 **Mytherin**，**19:54 新建**；目前 **open → v2.0-cyanoptera**。

现有 bind 同时承担输入/返回类型调整和执行期 FunctionData 创建，而且接收到的参数还未转换为函数所需类型。提案把流程改为“选择重载 → resolve_types → 参数类型转换 → bind”，让 bind 面对转换后的参数，减少嵌套类型、NULL 字面量及预处理参数带来的混淆；同时向 C API v2 暴露新的类型解析回调。对扩展作者而言，值得关注的是回调职责与执行顺序变化，而不是把它理解为新增 SQL 函数。

[hannes 的 #26553 — Determine the return type when folding a function call with a typed NULL argument](https://github.com/duckdb/duckdb/pull/26553) 于 **20:24 新建**，目前同样 **open → v2.0-cyanoptera**，叠加在 #26548 之上。它在折叠带类型的 NULL 参数时先确定返回类型，避免丢失类型信息后选错下游重载或影响 UNION ALL。**仍在 bind 中解析返回类型的函数尚未全部迁移**，因此不是所有 NULL 类型问题的一次性解决。

### 2. 延迟唯一约束从提案进入主分支

[#26423 — DEFERRED mode for PRIMARY KEY / UNIQUE](https://github.com/duckdb/duckdb/pull/26423)，作者 **artjomPlaunov**，10 月 3 日创建，本期 **16:58 merged → main**。

显式选择 DEFERRED 后，事务中可以暂时出现重复键，只要在 COMMIT 前修复；提交时仍有重复就会失败。这为需要分步重排键值的数据变更提供了新的事务内空间。

边界同样重要：主键的 **NOT NULL 仍即时检查**；外键不能引用延迟键，延迟约束也不能作为 ON CONFLICT 的冲突目标。PR 还修复了事务中新增索引后删除并重新插入同一键的一类误报，但**建索引之前已经发生的删除仍有既存限制**。它没有实现所有约束类型的延迟检查，也没有改变默认约束模式。

### 3. COPY 的两项改进：限制等待缓冲，细化宽行分批

- [#25913 — Bound partitioned COPY buffering during active flushes](https://github.com/duckdb/duckdb/pull/25913)，**jdctinuiti**，**09:13 merged → v2.0-cyanoptera**。分区 COPY 在前一批仍在刷出时，后一批可能持续增长；改动在达到现有刷出条件后阻塞生产者，并处理唤醒和中断，保留输入与刷出的重叠。**条件按行数而非字节数判断，不是每批内存的硬上限。** 作者明确说明，早期吞吐和内存测量针对已被替换的实现，本文不引用这些数字
- [#25060 — Respect ROW_GROUP_SIZE_BYTES](https://github.com/duckdb/duckdb/pull/25060)，**J-Meyers**，**13:57 merged → v2.0-cyanoptera**。允许在一个输入 chunk 内切分批次，减少超宽 BLOB 等场景中实际行组远超目标字节数的情况。**它仍是压缩前尺寸的尽力控制，不是硬上限，也未改动 FILE_SIZE_BYTES。** 作者宽行测试中，目标 8 MiB 的行组由数百 MiB 降至约 8.68 MiB；分区路径约 9.17 MiB。这些是作者测试结果，未独立复测

两项都是较早创建、本期合并。共同价值是减少写出过程中过大的中间批次，但不能据此宣称 COPY 已拥有统一的严格内存封顶。

### 4. 哈希表请求透明大页：收益依赖平台和负载

[#25869 — Request huge pages for the join hash table entry array](https://github.com/duckdb/duckdb/pull/25869)，作者 **abokhalill**，**08:49 merged → v2.0-cyanoptera**。

最终[代码差异](https://github.com/duckdb/duckdb/pull/25869/files)同时覆盖 **join 与 grouped aggregate 哈希表**。在受支持的 64 位 Linux 环境下，大分配可向内核请求透明大页，减少随机探测时的地址转换负担。实现要求分配至少 8 MiB、且至少容纳四个检测到的大页；会读取系统的大页大小，建议失败则忽略。PR 正文中“硬编码 2 MB”的早期描述已不符合最终补丁。

作者报告的 TPC-H SF10 测试为 Q9 用时下降约 7%、22 条查询合计下降约 2.2%；**未独立复测，也不是所有查询或平台的统一收益保证**。

### 5. 多文件扫描与执行正确性修复

[#26472 — Count pushed-down files in multi-file wrapper and patch postgres_scanner catalog cache race](https://github.com/duckdb/duckdb/pull/26472)，作者 **pdet**，**21:34 merged → v2.0-cyanoptera**。动态过滤可能在绑定后排除部分文件，包装层现在按运行时列表计数，向读取器提供实际扫描文件数；另一个修正处理 PostgreSQL catalog cache 加载、清空与读取之间的竞态，避免并发清空导致查找或扫描遗漏条目。问题来自升级 DuckLake 所用 DuckDB 时发现的集成边界。

同日 **lnkuiper** 的两项修复也已进入 **v2.0-cyanoptera**：
- [#26480 — Fix multi-source pipeline detection](https://github.com/duckdb/duckdb/pull/26480)，**13:33 merged**，修正多源 pipeline 的识别
- [#26481 — Get consecutive list before compressing in Parquet](https://github.com/duckdb/duckdb/pull/26481)，**12:04 merged**，修正重复或嵌套列表写入 Parquet 时的缓冲区尺寸估算：最终补丁按已准备页面的估计尺寸分配字符串缓冲，避免前期分析低估重复列表负载

后两项结合公开代码与回归测试核对，本文不据此扩大故障影响范围或推断性能收益。

### 6. 行组快照提案：先稳定规划与扫描的共同视图

[#26569 — Cache row-group collection snapshots for partition statistics and table scan](https://github.com/duckdb/duckdb/pull/26569)，作者 **Damon07**，**22:16 新建**，目前 **open → v2.0-cyanoptera**。

提案缓存行组集合快照，供规划期分区统计和执行期表扫描共用，以应对并发 append、checkpoint 改变行组列表的问题，并重新启用部分聚合预计算。对于含写操作的 DML CTE，则跳过相关规划期分区优化，以保留随后扫描对这些写入的可见性。

这更适合看作**恢复优化之前的正确性基础**：公共测试覆盖事务本地行、预处理语句重复执行、规划与执行之间的 checkpoint 以及 DML CTE；但仍未合并，也没有可引用的性能测量。

### 7. PEG 解析器有新测量，也有构建开销

[#26451 — PEG matcher: skip sub-matchers that cannot start at the current token (FIRST set)](https://github.com/duckdb/duckdb/pull/26451)，作者 **carlopi**，10 月 5 日创建，目前 **open → v2.0-cyanoptera**。本期 **15:43 的[评审回复](https://github.com/duckdb/duckdb/pull/26451#issuecomment-6011733247)**补充 FIRST-set 剪枝的测量：解析基准几何均值从 218.5 ms 降至 115.6 ms，约下降 47.1%；同时语法构建从 599.8 ms 增至 740.0 ms，约增加 23.4%。

这是窗口内的实质讨论更新，**不是当天新建或合并**。两组数字均为作者报告、未独立复测；解析耗时下降不能改写成 SQL 端到端执行提速，初始化成本也应一起评估。

## 官方新博客

本覆盖窗口内，**未发现官网新发布博客**。[新闻列表](https://duckdb.org/news/)和可用的[官方 Atom feed](https://duckdb.org/feed.xml)最新条目均为 [Importing Data using Java Table Functions](https://duckdb.org/2026/10/05/import-data-with-java.html)，发布日期为 **2026-10-05**；feed 的 published 为 **2026-10-05 00:00 UTC，即北京时间 08:00**，不在本期窗口内，故不重复算作今日新文。

## 方向观察（推测）

本期活动显示两条相互配合的方向：一是把隐含语义变得更明确，例如类型解析与绑定分离、显式延迟唯一约束；二是在正确性边界内改进执行与资源使用，例如 COPY 背压、行组分批及共享扫描快照。

这是对公开 PR 的**推测性归纳，不是官方路线图**。反面约束也很具体：类型回调迁移尚未完成，COPY 字节目标仍为尽力控制，行组快照仍在提案阶段；main 与 v2.0-cyanoptera 的合并不能推导出同一正式版本的交付日期。

## 覆盖与限制

- 检索官方 duckdb/duckdb 在窗口内创建、合并、更新的 PR：创建查询返回 78 项，合并查询 46 项，按四个时间段检索 updated 返回共 147 项；三类去重得到 165 个候选。按重要性筛选并核对重点 PR 详情，兼顾核心维护者及其他贡献者
- updated 查询反映当前最后更新时间；旧 PR 若窗口后再次更新，可能移出该范围。因此这些数字是本次搜索覆盖，不是历史活动穷尽统计，本文也未审计全部行内评论和提交
- 各条纳入依据是明确的创建、合并或评审回复时间，不把 updated_at 等同于功能完成；当前 PR 正文可能含后续编辑
- 请求的 /news/feed.xml 返回 404；改读官网 /feed.xml，并与新闻列表及公开网站源码交叉核对。没有把某个入口读取失败当成“没有博客”
- 未运行 DuckDB 回归测试或独立性能基准；作者数据均已标注。开发分支合并、提案与正式发布已分别呈现
