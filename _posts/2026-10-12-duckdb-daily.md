---
title: "DuckDB 日报 · 2026-10-12：内存治理、连接回归修复与 C API v2"
date: 2026-10-12 12:00:00 +0800
description: "连接排序、访问控制和 C API v2 多项改动合并；内存治理、宽 DECIMAL 与 Parquet 扫描继续推进。官网博客列表未发现当日新文。"
coverage_date: "2026-10-12"
---

## 覆盖窗口与核查时间

- 覆盖北京时间 **2026-10-12 00:00（含）至 2026-10-13 00:00（不含）**，即 UTC 2026-10-11 16:00 至 2026-10-12 16:00。
- 实际资料核查：北京时间 **2026-10-13 09:06**。下文事件时间均为北京时间；状态为核查时状态。
- “当日新建”“当日合并”和“窗口结束后合并”分别标明。合并到开发分支不等于已随正式版本发布。

## 今日速览

1. **稳定性与资源管理是密集主线。** 连接排序回归、UPDATE 撤销信息内存优化、调度公平性等已经在窗口内合并；大规模内存治理汇总和 JSON 缓冲优化在窗口内提出、次日凌晨合并。
2. **扩展能力与安全边界同时推进。** C API v2 补齐 PRAGMA、自定义配置、宏、日志接收端与 Appender 相关接口；HTTP、扩展安装和 SQLite 本地文件访问检查得到修补。
3. **较大功能仍在评审。** 255 位 DECIMAL、BIGNUM 算术、写语句的 EXPLAIN (SQL) 导出属于新提案；官网博客列表未见当日新文章。

## 一、窗口内已合并的重要 PR

### 连接排序与调度：先修回归，再改善并发体验

- [#26812 · Join order regression fixes](https://github.com/duckdb/duckdb/pull/26812)，作者 **lnkuiper**；10 月 12 日 **16:25:43 合并**，状态 **merged**，目标分支 `v2.0-cyanoptera`。修复整向量 distinct 采样、极小估计的哈希构建成本、LEFT JOIN 组合键估计、运行时过滤器成本，以及稠密整数 OR 条件的精确范围下推。意义是缓解连接排序改进暴露的基数估计短板；作者明确表示本 PR 只处理其中部分问题，不能视为所有连接计划回归已经解决。
- [#26809 · Task scheduler threads should use a ConsumerToken to improve query execution fairness](https://github.com/duckdb/duckdb/pull/26809)，作者 **bleskes**；**15:47:12 合并**，状态 **merged**，目标 `v2.0-cyanoptera`。工作线程和外部执行线程使用 ConsumerToken，并把轮转配额从 256 调为 16，减少新查询持续压过旧查询的情况。这是调度公平性改进，不是严格的查询延迟保证。

### UPDATE 与绑定：减少重复分配和重复计算

- [#26924 · Stop copying base data into update undo info, and size update infos to their contents](https://github.com/duckdb/duckdb/pull/26924)，作者 **Robinho-MR**；**21:08:01 创建、23:29:46 合并**，状态 **merged**，目标 **main**。首次更新行时不再把本可从基础存储读取的旧值复制到事务撤销信息中，并按实际内容分配 UpdateInfo。对稀疏更新和 VARCHAR 更新尤其相关，也减少旧字符串的长期保留。作者在“更新 1,000 万行中 1% 的 BIGINT + VARCHAR”场景报告更新内存从 375 MB 降至 44 MB；这是 PR 自测数据，本文未复现，不能外推为所有 UPDATE 的固定收益。
- [#26795 · Fold constant function arguments while binding](https://github.com/duckdb/duckdb/pull/26795)，作者 **h4nsmuller**；**23:30:56 合并**，状态 **merged**，目标 `v2.0-cyanoptera`。绑定器保留已经计算出的常量参数，避免在嵌套表达式中重复求值；同时调整 switch 和窗口绑定相关处理。含列引用的长表达式仍可能有其他优化器成本，本改动不等于通用规划性能问题全部消失。

### Parquet：显式绑定输出模式，防止重新绑定改变语义

[#26827 · Support explicit bound output schemas in Parquet scans](https://github.com/duckdb/duckdb/pull/26827)，作者 **kryonix**；**23:12:33 合并**，状态 **merged**，目标 `v2.0-cyanoptera`。

新增可选 `bound_schema`，为拆分文件组后的扫描保留完整、有序的输出模式。PR 举例说明：原扫描的 DOUBLE 列若在子文件组重绑定时被推断成 INTEGER，可能先把 1.4 转成 1，外层再转回 DOUBLE 也无法恢复。新参数让类型映射在原生逐文件处理前确定。

这是与现有 `schema=` 不同的接口；初始契约不支持 union-by-name、多文件模式采样及 `allow_empty`。使用者应关注这些边界，而不是把它当作任意 schema 演化的通用解法。

### 访问控制：补上绕过普通文件系统路径的检查

- [#26821 · HttpUtil: properly guard file access on install](https://github.com/duckdb/duckdb/pull/26821)，作者 **carlopi**；**14:02:35 合并**，状态 **merged**。在 INSTALL 路径也检查 `enable_external_access`。
- [#26742 · Check enable_external_access in the central HTTP request path](https://github.com/duckdb/duckdb/pull/26742)，作者 **Robinho-MR**；**14:02:36 合并**，状态 **merged**。在中央 HTTP 请求路径检查访问权限，覆盖扩展直接发起、没有经过普通文件系统的请求，例如 REST catalog 调用。安装路径有自己的权限检查逻辑，不能仅由中央检查概括其全部行为。
- [#26740 · Patch sqlite_scanner to check the file access settings before opening local databases](https://github.com/duckdb/duckdb/pull/26740)，作者 **Robinho-MR**；**21:11:00 合并**，状态 **merged**。在 SQLite 原生打开本地数据库前验证访问设置，覆盖 ATTACH、sqlite_scan、sqlite_attach；允许目录和内存数据库仍按各自规则处理。

以上三项均合入 `v2.0-cyanoptera`。它们是已合并的访问控制修补，本文没有把它们描述为已发布安全公告或已确认的 CVE。

### C API v2：扩展迁移所需接口继续补齐

三项均由 **Maxxen** 提交并合入 `v2.0-cyanoptera`，核查时状态均为 **merged**：

- [#26863 · C-API-V2：PRAGMA、MACRO、SET custom_option 等](https://github.com/duckdb/duckdb/pull/26863)：**00:32:14 创建、05:39:54 合并**。新增自定义 PRAGMA、带变更回调的配置项、向量转换、标量/表宏和文件路径辅助接口，旨在解除更多 C++ 扩展迁往 C API 的阻碍。
- [#26872 · C-API-V2：Log-sink support](https://github.com/duckdb/duckdb/pull/26872)：**05:50:34 创建、07:06:39 合并**。把 V1 的日志存储能力带入 V2，并采用 log sink 命名。
- [#26886 · C-API-V2：statement_add_collection 与其他接口](https://github.com/duckdb/duckdb/pull/26886)：**15:52:30 创建、21:58:14 合并**。恢复把列数据集合注入语句 CTE 的接口，调整 C++ Appender 使用方式，并增加清空 chunk、文件扩展名及 glob/move/remove 等 API。

## 二、当日新建及实质推进：仍须区分提案与落地

### 内存治理与文件扫描

- [#26919 · Track large allocations in the buffer manager and drop memory that was never needed](https://github.com/duckdb/duckdb/pull/26919)，作者 **h4nsmuller**；10 月 12 日 **20:32:08 创建**。汇总窗口函数、WAL、采样、quantile、TopN、DELETE RETURNING、CSV 写出等未纳入 buffer manager 的大分配，并删除无用 CSV 缓冲和错误保留。核查时 **merged**，但合并发生在 **10 月 13 日 02:41:58，属于窗口外**。部分测试预期从“默默超出 memory_limit”变成可控的内存不足错误；这不等于所有查询都更省内存或都能完成。被此 PR 替代而关闭的独立草稿不重复计为合并成果。
- [#26938 · Shrink the retained JSON auto-detect buffer and allocate it through the buffer allocator](https://github.com/duckdb/duckdb/pull/26938)，作者 **h4nsmuller**；10 月 12 日 **22:13:05 创建**。缩小 JSON 自动检测后保留的缓冲，并纳入受跟踪分配器，针对 union_by_name 下大量小文件的内存放大。核查时 **merged**，合并时间为 **10 月 13 日 04:25:37，窗口外**。
- [#26927 · Keep the files a scan opens ahead within the file descriptor limit](https://github.com/duckdb/duckdb/pull/26927)，作者 **pdet**；**21:26:36 创建**，状态 **open**。拟把“正在打开”和“已预先打开”的文件都计入扫描预开窗口，并根据文件描述符上限约束规模，处理大量小 Parquet 文件的 Too many open files。比例是启发式，尚非正式接口承诺。
- [#26929 · Fix aggregate spill transitions and source hash table cleanup](https://github.com/duckdb/duckdb/pull/26929)，作者 **lnkuiper**；10 月 12 日 **21:29:12 创建**。修复聚合溢写阶段切换与源哈希表清理；作者注明并未完全解决关联问题。核查时 **merged**，但在 **10 月 13 日 03:16:41** 才合并。
- [#26905 · Reuse Parquet statistics metadata and guard initial prefetch](https://github.com/duckdb/duckdb/pull/26905)，作者 **lnkuiper**；**19:34:47 创建**，状态 **open**。拟复用绑定时的统计元数据、优先使用已取得的重叠缓冲，并对适合的宽扫描尝试过滤列优先读取。
- [#26960 · Fix three parquet scan regressions found in the DuckLake benchmarks](https://github.com/duckdb/duckdb/pull/26960)，作者 **guillesd**；**23:44:11 创建**，状态 **open**。针对 row group 准备阶段锁竞争、DELTA_LENGTH_BYTE_ARRAY 字符串重复复制及 UTF-8 重复验证提出修复。PR 的性能结果来自特定模拟 S3 延迟和带宽条件；作者仍指出部分查询未恢复到 1.5.5 水平，本文不把结果外推到所有存储环境。

### 正确性、安全与新能力提案

- [#26959 · External hash join dropping rows through a partial bloom filter](https://github.com/duckdb/duckdb/pull/26959)，作者 **kryonix**；**23:38:04 创建**，状态 **open**。继承此前修复工作，拟在外部连接的 Sink 阶段收集完整 Bloom filter，避免只基于某一轮分区构建的过滤器错误排除后续行。这是结果正确性问题的修复提案，尚不能称已修复发布。
- [#26901 · Redact SECRET values in metadata, query logs and profiling output](https://github.com/duckdb/duckdb/pull/26901)，作者 **HendrikLambert**；**19:04:12 创建**，状态 **open**。拟在 secrets 元数据、查询日志、预备语句和 profiling 文本中隐藏秘密相关内容，包含 HTTP 额外头字段。
- [#26907 · Re-enable verifying direct-loaded extensions against community signing key](https://github.com/duckdb/duckdb/pull/26907)，作者 **Maxxen**；**19:51:02 创建**，状态 **open**。拟恢复直接 LOAD/INSTALL 路径对社区签名的兼容，前提是启用 `allow_community_extensions`；自动加载和具名仓库的信任边界仍分别处理，不能概括为“所有扩展都信任社区密钥”。
- [#26932 · Add multiplication, integer division and modulo for BIGNUM](https://github.com/duckdb/duckdb/pull/26932) 与 [#26955 · Support DECIMAL widths up to 255 digits, stored as BIGNUM blobs](https://github.com/duckdb/duckdb/pull/26955)，作者均为 **h4nsmuller**；分别于 **21:51:08、23:06:10 创建**，状态均 **open**，目标 **main**。前者补 BIGNUM 乘法、整除和取模，后者在其基础上提出 39–255 位 DECIMAL，并覆盖 Parquet/Arrow 等互操作。宽 DECIMAL 的 AVG、若干取整函数及超过 76 位的 Arrow 导出尚不支持；普通除法仍返回 DOUBLE。不要据此认为当前正式版本已经支持 255 位 DECIMAL。
- [#26958 · Support INSERT, UPDATE, DELETE and MERGE INTO in EXPLAIN (SQL)](https://github.com/duckdb/duckdb/pull/26958)，作者 **kryonix**；**23:32:26 创建**，状态 **open**。拟把优化逻辑计划的 SQL 重建扩展到写语句、RETURNING 及数据修改 CTE；包括 WHEN NOT MATCHED BY SOURCE 在内的一些无法正确表达的形状会明确拒绝，避免生成语义错误的 SQL。

### 讨论也会改变方向：嵌套 VARIANT 暂缓，分支整合仍是草稿

- [#26808 · Parquet：在嵌套结构中写入 VARIANT](https://github.com/duckdb/duckdb/pull/26808)，作者 **Tishj**，核查时 **open / draft**。10 月 12 日 **18:41:06 转为草稿**，作者随后于 **18:41:23 表示延后，v2.0 并非必需**。这是一项明确的范围收缩，不是新增功能落地。[当日讨论](https://github.com/duckdb/duckdb/pull/26808#issuecomment-6122642375)
- [#26558 · Merge v2.0-cyanoptera into main](https://github.com/duckdb/duckdb/pull/26558)，作者 **Robinho-MR**，核查时 **open / draft**。作者在 **21:01:17** 报告刷新分支整合，涉及 702 个 cyanoptera 提交、11 处冲突，并报告本地 reldebug 与 7,216 项 fast 测试通过。这是作者报告的整合进度，并不代表该 PR 已合并、全部 CI 已通过或 v2.0 已发布。[当日进度评论](https://github.com/duckdb/duckdb/pull/26558#issuecomment-6124788370)

### Mytherin 参与的评审：流式结果推进，实时指标先核正确性

- [#26880 · Remove planner eagerness](https://github.com/duckdb/duckdb/pull/26880)，作者 **evertlammerts**；10 月 12 日 **14:49:09 创建**，移除规划器对非普通 SELECT 结果的强制物化，是流式/异步结果工作的后续改动。Mytherin 于 **17:21:24 给出 LGTM**，作者在 **19:04:51 确认解决合并冲突**，并于 **20:37:22 进入合并队列**。核查时 **merged**，实际合并在 **10 月 13 日 00:35:48，窗口外**。[评审意见](https://github.com/duckdb/duckdb/pull/26880#issuecomment-6121381286)
- [#26311 · Expose Live Query Metrics](https://github.com/duckdb/duckdb/pull/26311)，作者 **Richard-Durkee**；Mytherin 在 10 月 12 日 **18:55:45** 的评审指出重复重置导致内存计数偏低、切换 profiling 丢失前一查询指标，以及无锁快照可能混合两个查询等风险。当天事件是实质评审，不能写成这些问题已在窗口内修复。核查时 **open / draft**；转草稿和后续修复提交发生在窗口结束后。[评审原文](https://github.com/duckdb/duckdb/pull/26311#pullrequestreview-5489711159)

## 三、官方博客与版本发布

在 [DuckDB 官方博客列表](https://duckdb.org/news/) 中，**未发现 2026-10-12 新发布文章**。核查时列表最新文章为 10 月 9 日的 [Agent Mode in the DuckDB CLI](https://duckdb.org/2026/10/09/agent-mode)，原文日期与列表一致；它是旧闻，不计入本期新增资讯。

[官方 RSS](https://duckdb.org/feed.xml) 本次未能成功读取：网页工具不支持该 XML 响应，另一只读获取返回 403。因此这里的结论仅为“官网列表未发现新增”，不是 RSS 完整性保证。

[官方 Releases](https://github.com/duckdb/duckdb/releases) 当前最新正式发布条目仍为 [v1.5.6](https://github.com/duckdb/duckdb/releases/tag/v1.5.6)，发布时间为北京时间 2026-09-28 21:35:11。本期所述开发分支合并不得等同于新的正式发布。

## 四、方向观察（推测）

- **推测：近期工程重点倾向于让资源约束更可信。** 依据是内存治理汇总、JSON 缓冲缩减、文件描述符窗口和聚合溢写修复同时出现。但更多分配受到 memory_limit 约束，也可能使原本越界运行的查询更早报错；不能只用“内存优化”理解全部行为变化。
- **推测：v2.0 相关工作在补齐扩展能力的同时收紧回归风险。** C API v2 的多项合并、连接排序修复与访问控制检查支持这一判断；嵌套 VARIANT 被明确延后则说明功能范围仍会调整。单日 PR 集合不是官方路线图，也不足以推断发布日期。
- **推测：高精度计算和可解释 SQL 是值得跟踪的后续能力方向。** BIGNUM、宽 DECIMAL 和 DML SQL 导出提供了具体提案证据，但仍有未支持操作、兼容性和评审不确定性，不应提前用于生产能力承诺。

## 五、覆盖与限制

- 通过 GitHub 创建、合并及更新检索筛选公开 PR，并补充读取从窗口起点至核查时的全部 4 页更新搜索结果；搜索接口当时报告 320 条、未标记 incomplete。更新范围包含窗口外活动，仅用来发现候选，入选事项另核对创建、合并或具体评论/事件时间。
- 优先关注 Mytherin、hannes、lnkuiper、pdet、Tishj、carlopi、hawkfish 相关活动，同时按实质影响纳入其他贡献者。正文不是所有 PR、所有评论或提交的逐条清单；未列出某位贡献者不表示其当日没有工作。
- PR 内容按核查时可见描述概述，描述可能在窗口结束后继续修改；归属日依据明确事件，不把 updated_at 当作完成时间。窗口外合并已单独注明。
- 性能和测试结果若有引用，均为作者在公开 PR 中的报告，本文没有独立运行 DuckDB 基准或测试。未读取内部 issue 的私有内容。
- 官方博客列表可读，RSS 不可读；这项覆盖缺口如上披露。
