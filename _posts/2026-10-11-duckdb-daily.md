---
title: "DuckDB 日报 · 2026-10-11：C API v2 合并，Parquet 写入正确性新提案"
date: 2026-10-11 12:00:00 +0800
description: "C API v2 通用句柄重构已合并；分区 COPY、Parquet 负零与 NULL 统计修复进入评审，SQL 导出和宽 DECIMAL 转换继续推进。"
coverage_date: "2026-10-11"
updated_at: 2026-10-12T08:58:00+08:00
---

覆盖窗口：北京时间 **2026-10-11 00:00 至 2026-10-12 00:00，左闭右开**（UTC 10 月 10 日 16:00 至 10 月 11 日 16:00）。实际核查时间：**2026-10-12 08:56—08:58（Asia/Shanghai）**。下文时间均为北京时间，状态以核查时为准；窗口后的合并另行标明。

## 今日速览

- **C API v2 的通用 factory / config 句柄重构已合并。** 上期仍待评审的 #26820 本期落地，影响扩展及 C++ 包装层的开发接口。
- **写入正确性是新提案重点。** 分区 COPY 可能把下一分区的行写进当前分区，Parquet 字典编码可能丢失负零符号，嵌套 NULL 统计也有重复计数；对应修复均仍 open。
- **SQL 导出与数值转换继续推进。** 类型化子树替换本期提出、翌日合并；宽 DECIMAL 转换优化仍待合并。官方列表与 Feed 均未发现新博客。

**已合并不等于已发布。** 核查时[最新正式版仍为 v1.5.6](https://github.com/duckdb/duckdb/releases/tag/v1.5.6)，于 9 月 28 日发布。以下选入 PR 的目标分支均为 **v2.0-cyanoptera**。

## 重要 PR

### 1. C API v2：通用句柄重构正式合并

[#26820 — [C-API-V2] Break-out common functionality +](https://github.com/duckdb/duckdb/pull/26820)，作者 **Maxxen**，10 月 10 日创建，本期 **22:49:44 merged**。

本期新增事实是合并，接续[前日报]({{ '/daily/2026/10/10/' | relative_url }})的 open 状态：将对象创建与配置分别集中到 `duckdb_v2_factory`、`duckdb_v2_config`；实例支持创建时传入 startup options，并补充函数文档及公共类型推导接口。减少连接与上下文间重复的构造接口，对扩展移植者有直接影响。

作者在本期[讨论](https://github.com/duckdb/duckdb/pull/26820#issuecomment-6110053411)明确表示先合并、随后补回 C++ 的 Environment。相关后续发生在本窗口之后，因此不能把这一轮开发接口当作已经稳定的最终形态。

### 2. 分区 COPY 与 Parquet：三项数据正确性修复待评审

以下三项作者均为 **louie-duck**，本期新建，核查时均 **open**。

- [#26854 — Partitioned COPY: do not count rows of the next partition into a ROW_GROUP_SIZE_BYTES batch](https://github.com/duckdb/duckdb/pull/26854)，**16:15:26 创建**。当分区边界正好落在批次边界时，按字节预算推进的循环仍消费下一分区的一行，继而可能把整个后续分区写进前一分区。复现中总行数仍正确，但原本各 2,048 行的两个分区变为一个 4,096 行分区。提案将循环改为先检查边界；作者将其定位为 2.0 开发分支回归。实践上，测试应核对分区键与行分布，不能只看总行数。
- [#26855 — Parquet writer: keep -0.0 and 0.0 as separate dictionary entries](https://github.com/duckdb/duckdb/pull/26855)，**16:16:14 创建**。FLOAT / DOUBLE 字典此前按浮点相等性合并正负零，导致写入文件丢失符号。拟在相等比较中保留 sign bit，同时仍让 NaN 共用字典项。这是写出的值本身受影响，不只是读取显示问题。
- [#26846 — Parquet writer: count a NULL struct inside a list once in the leaf null_count](https://github.com/duckdb/duckdb/pull/26846)，**04:45:40 创建**。嵌套列表里的 NULL struct 可能同时计入叶子自己的 NULL 和祖先 NULL，造成元数据重复计数。提案统一两类计数的汇总路径，并补充列表、结构体嵌套的回归用例。

已查看上述补丁与测试文件；作者报告的测试结果未独立复跑。这些提案尚不能作为正式版已经修复的依据。

### 3. SQL 导出：保留类型化边界与嵌套类型信息

[#26843 — Allow SQL export with typed subtree replacements](https://github.com/duckdb/duckdb/pull/26843)，作者 **kryonix**，本期 **02:00:25 创建**。核查时为 **merged**，但实际合并发生于 **10 月 12 日 07:27:41，窗口之外**。

新增 `ExportWithSources` 路径，在已解析的逻辑计划中以带类型的 SQL relation 替换明确子树，保留原计划及替换 AST 的所有权，并检查既有绑定与类型。替换边界必须互不重叠、保持输出绑定和类型；不能忠实重建的场景返回不支持，而非勉强生成 SQL。这有助于需要重用部分计划的集成，但不代表任意计划都能无损往返。

同一作者本期还创建两项依赖提案，核查时均 **open**：

- [#26861 — Preserve union_value member names in SQL export](https://github.com/duckdb/duckdb/pull/26861)，**21:16:49 创建**：从单成员 UNION 返回类型恢复命名参数，解决通用导出路径无法重建成员名的问题。
- [#26862 — Preserve collations in exported aggregate states](https://github.com/duckdb/duckdb/pull/26862)，**21:16:52 创建**：保留聚合中间状态签名及嵌套类型的 collation，避免只靠类型名字符串丢失比较规则；也处理已知返回类型的带类型 NULL 在提前折叠时丢失 collation 的边界。

### 4. STRUCT 与 ARRAY：避免优化改写后丢失语义

两项均由 **louie-duck** 本期提出，核查时 **open**：

- [#26844 — struct_update: resolve the updated fields at bind time instead of reading argument aliases](https://github.com/duckdb/duckdb/pull/26844)，**04:44:03 创建**。优化器可能改写参数别名，运行时再按别名定位字段会误把更新当作新增字段，触发断言或内存错误。拟保存绑定阶段已确定的字段映射，供执行、统计及 SQL 导出共同使用。
- [#26845 — Cast a fixed-size ARRAY to LIST when the unnest rewriter builds a LogicalUnnest](https://github.com/duckdb/duckdb/pull/26845)，**04:44:53 创建**。侧向 UNNEST 重写漏掉 ARRAY 到 LIST 的转换，可能触发断言或崩溃；拟在重建表达式的两条路径补上转换。普通 SELECT 列表中的 UNNEST 不走这一问题路径。

这组提案共同提醒：逻辑等价的优化改写还必须保留绑定后类型与字段映射。

### 5. 宽 DECIMAL 转换：移出逐位执行的 128 位除法

[#26848 — Avoid a 128-bit division per digit when casting VARCHAR to DECIMAL](https://github.com/duckdb/duckdb/pull/26848)，作者 **minhh-nguyen**，本期 **05:45:00 创建，open**。

宽度大于 18 的 DECIMAL 使用 HUGEINT。逐位解析时，溢出阈值中的除以 10 未被编译器折叠，重复执行昂贵的 128 位除法；补丁改为每种模板实例缓存阈值。作者在 macOS arm64 的示例中报告 DECIMAL(28,10) 从约 1.50 秒降至 0.196 秒，**这是作者的特定基准，未经独立复测，也不能推广到所有转换负载**。同题旧提案 [#26841](https://github.com/duckdb/duckdb/pull/26841) 已 closed、未合并，本报不重复计为两项优化。

## 官方博客

[官方博客列表](https://duckdb.org/news/)最新仍为 **2026-10-09** 的 [Agent Mode in the DuckDB CLI](https://duckdb.org/2026/10/09/agent-mode.html)，此前已经报道，本期不重复介绍。

[官方 Feed](https://duckdb.org/feed.xml)经直接读取 XML 核对，最新条目的 published / updated 均为 **2026-10-09T00:00:00+00:00**，未发现本期窗口内的新条目。网页抓取工具首次未能解析 Feed，随后直接读取成功。日期零点是来源标注，不据此推断精确上线时刻。

## 方向观察（推测）

1. **开发接口继续集中化。** #26820 已合并，说明 C API v2 在消除重复接口；作者明确保留后续调整，因此接口稳定性和最终范围仍需后续验证。
2. **正确性修复深入到写入边界与类型细节。** 分区边界、正负零、NULL 统计和绑定映射都有具体复现支撑；这些大多仍是待评审提案，不能据此宣称一轮可靠性改进已经发布。
3. **计划重用重视语义保真。** SQL 导出子树替换、UNION 成员名及 collation 处理方向一致，但依赖项尚未全部合并，通用性仍有限。

以上是公开活动的**推测性归纳，不是官方路线图**。

## 覆盖与限制

- GitHub 搜索 API 从 UTC 10 月 10 日 16:00 检索至本次核查，向窗口后延伸以减少后续更新导致的漏检；返回 **43 个候选，incomplete_results=false**。逐项读取 PR 元数据后确认其中 **14 项在窗口创建、1 项在窗口合并**，这是检索快照统计。
- 核对作者、标题、状态、目标分支及实际创建／合并时间，并检查旧候选的时间线及重点补丁。不会仅凭 updated_at 报告当天技术进展：例如多项 sebastiaan-dev 旧 PR 只是删除来源分支，部分旧 PR 只是 stale-bot 提醒，均未重新包装为新闻。
- 重点作者 Mytherin、hannes、lnkuiper、pdet、Tishj、hawkfish 的本次作者检索未返回更新候选；carlopi 的 #26866 创建于窗口之后，未纳入。未发现候选不等于这些作者没有其他活动。
- 对照此前日报去重；#26820 仅因本期实际合并而跟进。未全面审计所有历史评论页、独立扩展仓库及未公开活动，未访问内部问题，未独立运行 DuckDB 测试或性能基准。
