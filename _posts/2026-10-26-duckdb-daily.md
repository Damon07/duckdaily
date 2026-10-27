---
title: "DuckDB 日报 · 2026-10-26：外部排序、窗口下推与升级兼容修复落地"
date: 2026-10-26 12:00:00 +0800
description: "外部排序、延迟向量分配和窗口连接下推合并；旧文件 lambda、Arrow 与 Parquet 统计修复推进。官方新文介绍 2.0 的实用功能。"
coverage_date: "2026-10-26"
---

## 覆盖窗口

北京时间 **2026-10-26 00:00 至 2026-10-27 00:00，不含终点**，即 UTC 2026-10-25 16:00 至 2026-10-26 16:00。实际核查时间：**2026-10-27 09:04 北京时间**。下列“当日”指事件落在这一窗口；状态为核查时状态。**合并到开发或维护分支不等于已随稳定版本发布。**

## 今日速览

- lnkuiper 的外部排序和延迟向量分配、hawkfish 的窗口连接下推均已合并；性能收益必须按各自证据解读，不能把结构调整一概写成全面提速。
- 兼容性与正确性修复集中落地：旧文件中存储的箭头 lambda、Arrow 嵌套 NULL/切片、Parquet 返回统计，以及相关子查询和易变过滤表达式。
- 官网新增《Gems of DuckDB 2.0.0》；Mark 对远程目录预取方案的审查推动 PR 收敛为通用 pre-bind 扩展接口。

## 重要 PR

### 1. 外部排序：减少重复溢写，改善偏斜处理

[**#27783 — Out-of-core sort improvements**](https://github.com/duckdb/duckdb/pull/27783)  
作者：**lnkuiper**；**当日合并到 main（merged）**。

最终改动涉及排序分区预算、偏斜分区拆分、只固定所需 payload 范围、键和 payload 的分开释放，以及变长排序键的内联尾部等。目标是减少不必要的临时 I/O，并避免宽 payload 或偏斜数据把工作分配拉歪。作者报告在其复现的 CrocSort 论文实验中改善约 20–50%；这是特定实验的作者结果，不是所有 ORDER BY 查询的保证，也没有声称实现论文的全部算法。

### 2. 延迟分配 Vector：保留兼容边界，不夸大基准收益

[**#27751 — Lazy Vector Allocations**](https://github.com/duckdb/duckdb/pull/27751)  
作者：**lnkuiper**；**当日合并到 main（merged）**。

数据块初始化先建立类型化存储，首次可变访问才分配 payload；Reset 递归恢复缓存的 flat 缓冲区。最终版本释放 dictionary wrapper，而非保留早期方案的复杂包装；旧 C API 在暴露原始指针前准备数据，V2 路径移除额外 Flatten。作者补充的多核 TPC-H 热查询对照差异很小且有正有负，**不足以证明普遍加速**。意义主要在更清晰的分配时机与生命周期，而不是一个未经证实的性能数字。

### 3. 窗口算子前的安全连接下推

[**#27739 — Window Join Pushdown**](https://github.com/duckdb/duckdb/pull/27739)  
作者：**hawkfish**；**当日合并到 main（merged）**。

加入可独立禁用的 `window_join_pushdown` 优化器，在 projection pullup 后处理符合约束的连接。代码检查窗口分区与连接键的函数依赖，以及会扩张输入的连接所需唯一性条件，避免改变窗口内行集合和计数。价值是让筛选尽可能提前，减少窗口阶段处理量；并非任意连接都能穿过 WINDOW，叠加窗口等形态仍受限制。

### 4. 查询尚未结束，也能看 I/O 次数、耗时和 spill

[**#27856 — Expose I/O Operation, I/O Time And Spill Metrics As Live Query Metrics**](https://github.com/duckdb/duckdb/pull/27856)  
作者：**Richard-Durkee**；**当日合并到 main（merged）**。

将已有原子计数器开放为实时指标：读写操作次数、累计读写耗时、写入临时目录的字节数。最终 profile 的名称和数值语义不变，重点是运行中可观察，方便判断是否正在溢写或受 I/O 限制。注意读写耗时跨线程累加，可能大于查询墙钟时间，不能直接当作耗时占比。

### 5. 2.0 升级兼容：允许绑定旧文件存储的箭头 lambda

[**#27122 — Keep binding arrow lambdas stored before 2.0**](https://github.com/duckdb/duckdb/pull/27122)  
作者：**xproblematique**；**当日合并到 main（merged）**。

旧版本写入视图、宏的 `x -> ...` 在部分存储版本中被序列化为普通 SINGLE_ARROW，2.0 加载后会按已弃用语法拒绝。修复在反序列化时结合 catalog 存储版本，将低于 2.0 的已存对象识别为旧存储语法；checkpoint 加载和 WAL 回放均覆盖。**这不恢复新 SQL 的箭头 lambda**，也不豁免按 2.0 存储版本升级的对象；弃用警告仍可能影响 `warnings_as_errors`。

### 6. Parquet 文件统计：全 NULL 行组不应抹掉其他行组的边界

[**#27875 — Parquet writer: keep a column's min/max in RETURN_STATS when a row group holds only NULLs for it**](https://github.com/duckdb/duckdb/pull/27875)  
作者：**h4nsmuller**；**当日合并到 v2.0-cyanoptera（merged）**。

`COPY ... RETURN_STATS` 汇总文件级统计时，全 NULL 行组本来没有 min/max，却导致其他行组已经提供的边界被清除。现在确认 `null_count == num_values` 时不破坏已有边界；有非 NULL 值却缺少统计的行组仍使边界失效。对利用这些统计估计连接规模的 DuckLake 尤其重要，可避免相同数据因并行写入分组不同而得到不稳定的规划输入。不要与旧文件读取时的 NULL zonemap 裁剪问题混为同一修复。

### 7. 优化器正确性：守住求值次数、NULL 和相关分组语义

- [**#27757 — Fix volatile filter pushdown, constant_or_null folding, statistics and projection placement**](https://github.com/duckdb/duckdb/pull/27757)，作者 **Robinho-MR**，**当日合并到 main（merged）**。把易变过滤保留在 GROUP BY/DISTINCT 之上，避免由每组求值变为每行求值；另修复失效参数的统计传播、带类型 NULL 的折叠、不能下推过滤所需的额外列，以及 projection placement 的重复读取计数。这里既有错误结果修复，也有规划开销改善，不应仅归类为性能 PR。
- [**#27878 — Preserve correlated MARK groups with row-identity decorrelation**](https://github.com/duckdb/duckdb/pull/27878)，作者 **kryonix**，**当日合并到 main（merged）**。让 MARK join 的类型元数据对应实际 delimiter 连接键，而不是全部相关 payload，恢复相关 IN 在各组内的 NULL 与空集处理，避免别的组含 NULL 时影响本组结果。
- [**#27880 — Preserve replacement source rows below scalar projections and VALUES**](https://github.com/duckdb/duckdb/pull/27880)，作者 **kryonix**，**当日合并到 main（merged）**。SQL 导出时，显式替换源优先于 dummy scan 的单行捷径，防止多行或空关系被错误导出为单行；VALUES 同样保留输入驱动的展开。

### 8. Arrow 嵌套数据与超大本地文件读取

- [**#27756 — Fix Arrow scans of sliced structs and unions and of NULL fixed-size lists**](https://github.com/duckdb/duckdb/pull/27756)，作者 **Robinho-MR**，**当日合并到 main（merged）**。修正嵌套 struct/sparse union 的切片偏移传递，并在嵌套 list/array 转换时保留父级 NULL mask，避免读取错位或把隐藏在 NULL 父节点下的数据当成有效值。
- [**#27864 — Read Extension Files Fully When Installing From Disk**](https://github.com/duckdb/duckdb/pull/27864)，作者 **Richard-Durkee**，**当日合并到 main（merged）**。扩展安装不再假定一次 read 就能取得整个文件，改用循环读取路径，修复超过约 2 GB 的文件尾部元数据缺失。
- [**#27870 — Read local files in chunks of at most 1 GiB per pread**](https://github.com/duckdb/duckdb/pull/27870)，作者 **louie-duck**，**当日合并到 main（merged）**。补齐 macOS 单次超大 pread 会返回 EINVAL 的平台差异，将每次读取限制为 1 GiB。两项属于文件读取完整性修复，不代表改变扩展签名验证。

### 9. 仍在审查：解析器减负与远程目录预取接口

- [**#27874 — Parser performance 5/N**](https://github.com/duckdb/duckdb/pull/27874)，作者 **Dtenwolde**，**当日新建，仍 open**。通过预编译可折叠列表链、在原 frame 内处理 leading choice、减少临时容器与 arena 拷贝，压缩 PEG 匹配工作。作者微基准的指令数下降约 17.7–23.3%；这是解析微基准而非 SQL 端到端延迟，尚未合并。
- [**#27872 — Let Catalogs Prefetch The Tables A Statement References Before Binding**](https://github.com/duckdb/duckdb/pull/27872)，作者 **Richard-Durkee**，**当日新建并修订，仍 open**。目的在于重叠远程 catalog 查表请求。**不能照抄原始标题/描述，把当前方案写成 Catalog::PrefetchEntries 已加入。** [Mytherin 当日审查](https://github.com/duckdb/duckdb/pull/27872#issuecomment-6415467210)指出原始语法树引用无法正确展开 CTE/视图，建议先提供通用 pre-bind 扩展 hook。随后提交 `84e6a923` 的最终 diff 已改为在 Binder 之前调用 `PlannerExtension::pre_bind_function`；具体预取逻辑留给扩展层。通用、结构化的目录处理仍是后续问题。

## 官方新博客

[**Gems of DuckDB 2.0.0**](https://www.duckdb.org/2026/10/26/gems-of-duckdb-200)  
官网标注日期：**2026-10-26**；作者：**Gábor Szárnyas、Geertjan Wielenga**。

文章补充已经发布的 2.0 实用功能：Python Appender 适合程序逐行生成的数据；已有 DataFrame/Arrow 数据仍可优先用批量 SQL 导入。CLI 增加函数手册、历史查询和更易读的 schema 输出；SQL 与 COPY 提供配置查询、序列赋值、自定义分区路径等能力。扩展页面增加版本/平台兼容矩阵，窗口函数也可由扩展注册。实践上，升级除了检查核心版本，也应核对所需扩展在目标平台是否已部署。**这些是官方介绍的已发布功能，不应与本篇当日新合并 PR 混算。**

## 方向观察（推测）

1. **执行器优化更强调减少内存与 I/O 浪费，而非只增加并行度。** 外部排序、延迟向量分配和窗口下推分别减少重复溢写、提前分配和进入昂贵算子的行数。不过 lazy vector 的实测结果接近噪声，说明“架构更合理”不能自动推导为所有负载更快。
2. **2.0 后的兼容和语义边界仍需要持续打磨。** 旧 lambda、Arrow NULL、Parquet 统计与易变过滤的修复各自有明确触发条件；不能据此断言所有升级问题已解决。
3. **Mark 的预取审查体现了将通用 hook 与扩展专属策略分开的取向。** 证据限于这次审查及随后修订，不等于官方承诺采用某个完整远程 catalog 路线图。

## 覆盖与限制

- GitHub 公开 API 的 `updated >= 2026-10-25T16:00:00Z` 检索读取两页，共 **157 个候选**，结果标记 `incomplete_results=false`；另按精确窗口核对 **35 个合并 PR**。候选包括次日更新，入选按创建、合并或实质修订时间筛选，不将标签/机器人更新当成果。本篇精选 **14 项 PR**，不是全量 changelog。
- 对重点 PR 回查详情、最终文件 diff 和必要的审查/提交时间；仅使用公开内容，未访问 PR 引用的内部 issue。重点检索包含核心贡献者，但按重要性保留其他作者。
- 北京时间次日发生的合并不计入本日“已合并”事件，例如 NUMA #27782 的合并时间是 10 月 27 日 00:49，北京时间，不因 UTC 日期仍为 26 日而提前归入。
- 官网新闻列表及新文章正文已核实；RSS `feed.xml` 在网页工具中不支持 XML，独立请求返回 403，无法完成 feed 交叉核对。博客按官网标注发布日期归档，不推断精确首次上线时刻。
- 未独立运行本文 PR 的性能实验或测试；作者基准均作来源限定。除官方新文明确介绍的发行功能外，不把主线或维护分支合并视为当前稳定包已包含。
