---
title: "DuckDB 日报 · 2026-10-16：聚合与 JOIN 优化落地，Parquet 页索引继续评审"
date: 2026-10-16 12:00:00 +0800
description: "聚合性能、低内存分组和析取 JOIN 重写合入主线；Parquet 页索引、连续向量读取仍在评审。官网发布 JSON 类型化教程及 NVIDIA Vera 基准。"
coverage_date: "2026-10-16"
---

## 覆盖时间

北京时间 **2026-10-16 00:00 至 2026-10-17 00:00**，左闭右开；对应 UTC **2026-10-15 16:00 至 2026-10-16 16:00**。实际核查：北京时间 **2026-10-17 09:02**。

下文状态截至核查时；特别标明窗口之后的合并。**已合并到开发分支不等于稳定版已经发布、安装后即可使用。**

## 今日速览

- **聚合与优化器有实质落地**：lnkuiper 的聚合热路径和低内存修复、EslamAhmed171 的析取 JOIN 重写均已合并。
- **存储读取仍在推进方案评审**：Parquet 页索引和连续向量批量读取有新代码与具体评审反馈，尚不能当成已发布能力。
- **官网两篇新文**：JSON 文本转类型化列，以及 DuckDB v2.0-dev 在 NVIDIA Vera 上的 TPC-H 测试。

## 重点 PR

### 1. 聚合性能与低内存分组：两项已合并

作者均为 **lnkuiper**。

- [#27378 Aggregation performance](https://github.com/duckdb/duckdb/pull/27378)：当日新建，**20:27 北京时间合入 main，merged**。最终 diff 将聚合状态初始化改为最多 128 个指针一批；给忽略 NULL 的二元聚合增加 flat vector 有效位交集快路；移除原有哈希表预热。意义是减少聚合热路径的回调、格式转换和无效访存。作者报告约 3% 的整体小幅收益，非本日报独立复测结果。
- [#27298 Fix grouped aggregation OOM at low memory limits](https://github.com/duckdb/duckdb/pull/27298)：此前创建，**当日 16:55 合并，merged**。重新计算 radix hash table 的最低工作集，计入分区、每线程元数据及余量，并修正 reservation 请求上限。针对低算子内存预算时的不合理 OOM，**不是取消全局内存限制，也不保证任意低内存查询都能成功**。

### 2. 析取 JOIN 重写进入主线

[#22797 Add Disjunctive Join Rewriter Optimizer](https://github.com/duckdb/duckdb/pull/22797)，作者 **EslamAhmed171**；**当日 16:20 合并，merged**。

把适用的跨输入等值条件 OR 拆成比较连接分支，使这类查询能够利用更合适的连接计划。实现保留输入重复行，排除重复匹配的“行对”，并处理 NULL 与外连接未匹配行，不能简单理解为 UNION 后全局去重。对 volatile、可能抛错的谓词及过多分支设有保护。它是规划重写，不是新增通用连接算子；评审提及后续版本，不能据此认定稳定版已具备该功能。

### 3. Mark 关注的连续向量读取：仍在讨论实现层次

[#27383 Scan full vectors of consecutive rows in bulk instead of fetching them row by row](https://github.com/duckdb/duckdb/pull/27383)，作者 **ywelsch**；当日 **19:27 新建，open**。

当前快路只针对完整、连续、没有相关更新的 vector，批量扫描后复制到结果自有内存，主要服务于带索引表大批删除后的取数与清理，避免逐行解压。**Mytherin（Mark Raasveldt）**在[当日评审](https://github.com/duckdb/duckdb/pull/27383#issuecomment-6216032400)建议下沉到 segment 层，扩展到部分向量及连续 run；作者随后解释 VARCHAR 块固定生命周期的权衡。因此尚不宜把作者单项基准外推为所有 DELETE/TRUNCATE 都会大幅加速。

### 4. Parquet 页索引：读取剪枝与预取协同是关键

[#27326 Parquet: read and write the page index](https://github.com/duckdb/duckdb/pull/27326)，作者 **h4nsmuller**；当日 **01:03 新建并持续评审，open**。

新增 ColumnIndex/OffsetIndex 读写，利用页级统计与行范围跳过无关页面，特别针对带页索引的 Spark Parquet 文件。核查时 diff 中读取默认启用，**写入需显式 WRITE_PAGE_INDEX，默认关闭**。当日讨论涉及写入开销、页大小、预取范围合并及缓存实际请求；[最新窗口内反馈](https://github.com/duckdb/duckdb/pull/27326#issuecomment-6217995385)仍指出阈值、日志及复杂列限制。**跳过的行数不等于省下的网络字节**，不能仅以选择率或作者单个基准认定收益。

### 5. Parquet 格式兼容：一项落地、一项提案

- [#27248 Sort written field-ids by their corresponding field names](https://github.com/duckdb/duckdb/pull/27248)，作者 **Tishj**；**当日 21:11 合并，merged**。VARIANT 对象写入时按 UTF-8 字段名字典序排列 field IDs/offsets，即使字典本身未排序也遵守格式要求，改善跨实现互操作。
- [#27382 BYTE_STREAM_SPLIT support for FIXED_LEN_BYTE_ARRAY](https://github.com/duckdb/duckdb/pull/27382)，作者 **Robinho-MR**，保留 **RileyWen** 的 [#27367](https://github.com/duckdb/duckdb/pull/27367) 原始贡献；**当日 19:21 新建，open**。补齐这类编码的定长字节数组读取，覆盖 Arrow 写出的部分 DECIMAL 文件；统一按值宽度解码，并处理解码缓冲区生命周期。仍是提案。

### 6. Arrow 下推边界修复已合并

[#27319 [arrow] Fix pushdown errors](https://github.com/duckdb/duckdb/pull/27319)，作者 **evertlammerts**；创建在窗口前，**当日 19:15 合并，merged**。

字典列按其值类型判断能否下推，提前识别 run-end encoding，并让动态 JOIN/Top-N 下推也遵守扫描函数的类型能力检查。避免把生产者不支持的过滤交给 PyArrow，造成报错甚至 INTERNAL error。这里是编码与过滤能力边界的正确性修复，不是对所有 Arrow 查询关闭下推。

### 7. SQL 正确性：窗口、排序规则与常量折叠

- [#27342 Fix LEAD/LAG with an argument ORDER BY…](https://github.com/duckdb/duckdb/pull/27342)，作者 **hawkfish**；当日新建，**15:23 合入 v2.0-cyanoptera，merged**。修复当前行不在窗口 frame 内时，排序树与共享排序快路的定位、偏移及边界错误。
- [#27345 Collated Group By Subqueries](https://github.com/duckdb/duckdb/pull/27345)，作者 **hawkfish**；当日新建，**15:14 合入 main，merged**。对含子查询的分组表达式保留并重新绑定未应用 collation 的表达式，避免 SELECT/HAVING/ORDER BY 读到内部排序表示而非原始值。
- [#27300 Fix case simplification and constant folding issues…](https://github.com/duckdb/duckdb/pull/27300)，作者 **Tishj**；创建在窗口前，**当日 01:41 合并，merged**。CASE 简化和常量参数探测改用可失败的求值接口，普通求值错误可留待运行期处理；内部错误仍传播。避免启用除零报错后，在优化阶段过早失败。

### 8. 存储提交与远程访问：两项仍 open

- [#27334 Invalidate the database instead of corrupting indexes when a COMMIT fails mid-flush](https://github.com/duckdb/duckdb/pull/27334)，作者 **artjomPlaunov**；当日 **01:48 新建，open**。区分已恢复共享状态、可正常失败的约束错误，与提交刷写中可能留下不可回滚状态的异常；后者使数据库失效，防止 checkpoint 持久化损坏索引。该保护尚未合并。
- [#27381 Check the file system path of remapped HTTP requests against the access settings](https://github.com/duckdb/duckdb/pull/27381)，作者 **carlopi**；当日 **19:21 新建，open**。为 S3 等映射成 HTTP 的请求保留原文件路径，避免允许的 s3:// 目录因底层 HTTPS 地址而被拒绝。Mark 当日建议把测试放在 httpfs；核查时已有窗口外 follow-up，不能写成当日已修复发布。

### 9. 规划与解析速度：注意合并跨日和堆叠 PR

- [#27391 Fix quadratic planning time…](https://github.com/duckdb/duckdb/pull/27391)，作者 **kryonix**；当日 **21:20 新建，open**。为 column binding 替换图建立索引并按输出边界裁剪，针对宽表及相关子查询引发的规划耗时放大；收益针对规划，不等同 SQL 执行吞吐。
- [#27393 Parser performance 1/N](https://github.com/duckdb/duckdb/pull/27393)，作者 **Dtenwolde**，正文注明来自 lnkuiper 的系列提交；当日 **21:51 新建**。减少扫描、token iterator 和 matcher 开销。**当前 merged，但实际合并为 10 月 17 日 00:49，晚于本报道窗口。**
- [#27395 Parser matcher folding, 2/N](https://github.com/duckdb/duckdb/pull/27395)，作者 **Dtenwolde**；当日 **22:36 新建，open**。进一步折叠 grammar matcher 链、利用 FIRST set 跳过不可能分支，减少解析状态开销。它叠加在 1/N 之上，不能重复统计两份 diff 或直接相加性能百分比。

### 10. 分支同步与批量修复

作者 **Robinho-MR** 的 [#27284](https://github.com/duckdb/duckdb/pull/27284)（当日 **16:39，merged**）批量合入多项正确性修复；其中最终 diff 明确允许全局字典缓存按稳定 ID 识别重包裹后的字典，避免仅比较 entry 地址导致错误。原 [#27150](https://github.com/duckdb/duckdb/pull/27150) 为 **closed、未直接合并**，不应与批量落地重复计数。

同作者 [#27371 Merge v2.0-cyanoptera into main](https://github.com/duckdb/duckdb/pull/27371) 当日新建，由 **Mytherin** 于 **20:48 合并，merged**。这是开发分支同步，不是稳定版发布。后续批量修复 [#27390](https://github.com/duckdb/duckdb/pull/27390) 当日 **21:17 新建，仍 open**。

## 官网文章

两篇均在官网标注 **2026-10-16**，并由 [news](https://duckdb.org/news/) 与 [feed](https://duckdb.org/feed.xml) 交叉确认。feed 的 published 均为 UTC 00:00（北京时间 08:00）；该元数据不代表独立核实了精确上线时刻。

- **[From JSON Strings to Typed Columns](https://duckdb.org/2026/10/16/json-to-typed-columns.html)**：说明如何直接在 SQL 中把文本列中的 JSON 转为类型化列：推断并调整结构，再用 json_transform、unnest 建表，避免导出后重读；也处理嵌套字段重名、对象数组及转换失败。实践意义是把半结构化清洗留在数据库内完成。
- **[Benchmarking DuckDB v2.0-dev on NVIDIA Vera](https://duckdb.org/2026/10/16/nvidia-vera-benchmark.html)**：用开发预览版在 NVIDIA Vera 和 Intel Xeon 6 上跑完整 TPC-H SF1,000；该文报告 Vera 的综合分数中位数高约 **46%**。结果绑定具体硬件与配置，**未经官方 TPC-H 审计**，不能解释为稳定版或任意工作负载都提升 46%。

## 方向观察（推测）

- **更细粒度的批量化和剪枝仍是性能抓手**：聚合初始化批处理已落地，连续向量读取和页索引仍在评审。依据是上述实际 diff；反面边界是页索引与预取、缓存、列宽的相互作用，因此不能把“处理更少行”直接当作“更少 I/O”。
- **开发分支整合与语义修复同步推进**：分支同步、窗口函数、Arrow 和 VARIANT 修复显示当前重视正确性与互操作。此为公开变更的归纳，不是官方路线图，也不能据此推定发布日期。

## 覆盖与局限

按公开 GitHub API 分页筛选：窗口内 updated 候选 **231** 条，另交叉查询窗口内新建 **76** 条、合并 **35** 条；补查窗口后 updated 的 **39** 条，避免仅靠最后更新时间漏掉跨日进展。数字是检索集合，彼此重叠，不是重要更新数量。优先核查核心贡献者，但按变更重要性纳入其他作者；重点条目已查看详情、最终可见 diff 和相关讨论，未逐行审计所有候选。

匿名 API 读取中途达到速率限制，已用 GitHub 连接补足所选条目的 diff/讨论；官网正文和 feed 均成功读取。未独立运行 PR 基准或完整测试，不引用私有 issue 内容；未将 bot PR 的关闭视作合并，也未把开发分支 merged 等同稳定版已发布。开放 PR 的实现与状态仍可能继续变化。
