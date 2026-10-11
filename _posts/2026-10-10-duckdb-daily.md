---
title: "DuckDB 日报 · 2026-10-10：异步内存预算、Parquet 精度与查询回归修复"
date: 2026-10-10 12:00:00 +0800
description: "异步积压预算、CTAS 临时空间和过滤上拉修复已合并；Parquet INT96 新增精度选项，C API v2 与外部访问边界继续推进。"
coverage_date: "2026-10-10"
---

覆盖窗口：北京时间 **2026-10-10 00:00 至 2026-10-11 00:00，左闭右开**（UTC 10 月 9 日 16:00 至 10 月 10 日 16:00）。实际核查时间：**2026-10-11 08:59—09:02（Asia/Shanghai）**。下文事件时间均为北京时间，状态以核查时为准。

## 今日速览

- **资源控制与查询回归继续修复。** pdet 的异步积压内存预算、CTAS 临时空间复用，以及过滤上拉导致笛卡尔积的问题均已合并。
- **Parquet INT96 增加精度选择。** hawkfish 的读取选项已合并；预取重复计数和显式绑定输出 schema 则是本期新提案。
- **接口与访问边界仍在演进。** 异步结果的连接占用检查已合并，C API v2 通用句柄、INSTALL 外部访问检查和 secret 路径边界提案仍 open。未发现官方新博客。

**已合并不等于已发布。** 核查时[最新正式版仍为 v1.5.6](https://github.com/duckdb/duckdb/releases/tag/v1.5.6)，发布日期为 9 月 28 日。除特别注明外，以下 PR 目标分支均为 **v2.0-cyanoptera**。

## 重要 PR

### 1. pdet 与其他贡献者：限制异步积压，减少 CTAS 临时空间浪费

- [#25183 — Bound the async backlog budget by the memory limit](https://github.com/duckdb/duckdb/pull/25183)，作者 **pdet**，8 月 31 日创建，本期 **01:17:30 merged**。异步内存管理器不再只按线程数确定预算：预算上限为 `memory_limit/8`，最低预留量也受 `memory_limit/16` 限制，针对低内存配置下积压预算过大的问题。这不代表整个进程内存被严格限制在该比例。前日报只说明其合并落在窗口之外，本期按实际事件归档。
- [#25707 — Fix CTAS excessive temp usage](https://github.com/duckdb/duckdb/pull/25707)，作者 **Tobias2099**，9 月 15 日创建，本期 **00:26:52 merged**。把临时块子分配状态移到 RowGroup，使同一行组的多个追加状态能继续利用部分填满的块，修复内存数据库建表时临时存储使用过高的回归；附有回滚重试与 CTAS 回归测试，未独立复测节省比例。

### 2. 异步结果：连接有未完成结果时，新语句明确报错

[#26747 — [async results] Error Submit / Query when the connection holds an open result](https://github.com/duckdb/duckdb/pull/26747)，作者 **evertlammerts**，10 月 8 日创建，本期 **00:58:53 merged**。

同一连接已有未完成结果时，Submit / Query 现在返回 `RESOURCE_IN_USE`，并保留原结果与事务。此前新语句可能中止未完成写入，导致随后的 COMMIT 成功却没有提交那些写入。C API 新增对应错误类型；ADBC 在自身 COMMIT / ROLLBACK 前把打开的流读入内存。对调用方而言，需要先消费或销毁结果，再发下一条语句。作者称这是扩大流式查询支持的第二步，不能视作所有查询的流式改造已完成。

### 3. hawkfish：Parquet INT96 可选择纳秒或日期时间结构

[#26503 — Issue #25857: Parquet TIMESTAMP_NS](https://github.com/duckdb/duckdb/pull/26503)，作者 **hawkfish**，10 月 6 日创建，本期 **03:25:02 merged**。

新增 `int96_as` 读取选项：默认 `timestamp` 保持微秒精度；`timestamp_ns` 保留纳秒，但超出其可表示范围的值饱和为正负无穷；`struct` 暴露 `STRUCT(date DATE, time TIME_NS)`，用于保留更宽的日期范围及纳秒部分。[补丁与测试](https://github.com/duckdb/duckdb/pull/26503/files)同时覆盖字典编码、字段提取与 COPY FROM。读取历史 INT96 文件时，精度和范围需要一起考虑。

两项本期创建、核查时仍 **open** 的相关提案：

- [#26826 — Parquet reader: count each column chunk once when sizing a row group's prefetch](https://github.com/duckdb/duckdb/pull/26826)，作者 **louie-duck**，**02:06:32 创建**。拟按实际列块去重计算预取大小，避免多个 VARIANT 字段或重复列引用使正常文件被误报为页偏移错误，或让本地预取停用。
- [#26827 — Support explicit bound output schemas in Parquet scans](https://github.com/duckdb/duckdb/pull/26827)，作者 **kryonix**，**04:47:58 创建**。拟加入可选 `bound_schema`，避免拆分文件组后重新推断类型导致精度丢失，例如 DOUBLE 数据先被读成 INTEGER 再转回 DOUBLE。它与按字段 ID 映射的 `schema=` 不同，初始方案不支持 union-by-name 等部分组合。

### 4. 优化器与解析器：保留必要过滤条件，提前拒绝过深输入

[#26807 — Keep fallible predicates below projections during filter pullup](https://github.com/duckdb/duckdb/pull/26807)，作者 **kryonix**，10 月 9 日创建，本期 **14:56:36 merged**。

当过滤条件可能抛错时，将其留在投影之下，防止过滤上拉后无法下推、丢失重建 join 所需条件。原示例因此从两个哈希连接加一个笛卡尔积恢复为三个哈希连接。整个过滤批次一起保留，还用于保护转换、溢出或易变表达式的求值语义；不能据此声称所有连接顺序回归已解决。

解析边界也有合并：
- [#26771 — Improve parser robustness](https://github.com/duckdb/duckdb/pull/26771)，作者 **carlopi**，10 月 8 日创建，本期 **02:30:13 merged**；它整合测试与 [#26591](https://github.com/duckdb/duckdb/pull/26591) 的实现。后者作者 **Robinho-MR**，10 月 7 日创建，**02:30:14 merged**：在转换阶段检查表达式嵌套深度，避免等到 binder 检查前递归已溢出。两者是关联工作，不计为两项独立功能。
- [#26269 — Fix unbounded type nesting depth](https://github.com/duckdb/duckdb/pull/26269)，作者 **Kareemingit**，9 月 30 日创建，本期 **01:37:55 merged**，为解析和类型遍历补上嵌套深度约束。

### 5. C API v2 与访问控制：新提案仍待合并

- [#26820 — [C-API-V2] Break-out common functionality +](https://github.com/duckdb/duckdb/pull/26820)，作者 **Maxxen**，本期 **00:08:35 创建，open**。提议抽出通用 factory / config 句柄，统一对象创建与配置接口，并支持实例启动选项、函数文档及公共类型推导。对扩展作者，这是开发中接口继续重构的信号，尚非稳定 API 变更。
- [#26821 — HttpUtil: properly guard file access on install](https://github.com/duckdb/duckdb/pull/26821)，作者 **carlopi**，本期 **00:45:06 创建，open**。拟让 INSTALL 路径也检查 `enable_external_access`。
- [#26823 — Match secret scopes only on a path separator boundary](https://github.com/duckdb/duckdb/pull/26823)，作者 **Robinho-MR**，本期 **01:23:57 创建，open**。拟避免 `s3://scope_a` 的 secret 错误匹配 `s3://scope_a_evil/...` 等仅共享字符前缀的路径。公开说明指出可能选择错误凭据；这里不把未合并提案写成已发布安全修复。
- [#26831 — Skip windows_amd64 extension builds on pull requests instead of allow failure](https://github.com/duckdb/duckdb/pull/26831)，作者 **carlopi**，本期 **16:09:58 创建、18:48:02 merged**。暂时跳过 PR 的该架构扩展构建，push 和 alpha 构建仍保留。它接替了同日已合并但未能消除失败报告的 [#26822](https://github.com/duckdb/duckdb/pull/26822)，不表示 Windows 支持被移除。

### 6. 仍在排查的窗口分析问题

[#26502 — Internal #10721: Window Frame Analysis](https://github.com/duckdb/duckdb/pull/26502)，作者 **hawkfish**，10 月 6 日创建，核查时 **open**，目标分支 **main**。本期 **05:07:05**，作者在[评审讨论](https://github.com/duckdb/duckdb/pull/26502#discussion_r4234556501)补充不含窗口函数的复现，显示延迟约束与唯一列组合分析的问题也影响 ORDER BY。这是排查范围的实质推进，未据此认定修复完成或当天新增代码。

## 官方博客

截至核查，[官方博客列表](https://duckdb.org/news/)最新文章仍是 **2026-10-09** 的 [Agent Mode in the DuckDB CLI](https://www.duckdb.org/2026/10/09/agent-mode)，已在前日报介绍；本期**未发现标注 10 月 10 日的新文章**，不重复包装成今日首发。

[Feed](https://duckdb.org/feed.xml)访问返回抓取错误，未能独立完成 RSS 核对。博客发布日期并非精确上线时刻，因此这里不声称穷尽窗口内所有网页变动。

## 方向观察（推测）

1. **v2.0 的资源与错误边界在收敛。** 异步积压预算、临时块复用、结果占用检查和过滤上拉修复均提供依据；本期没有可比较的统一基准，不能推导普遍加速幅度。
2. **Parquet 读入的类型与物理细节更加显式。** 已合并的 INT96 选项，与尚待评审的预取去重、绑定 schema 方案方向相近，但后两者的最终接口与合并时间仍不确定。
3. **扩展接口和外部访问规则继续调整。** C API v2 句柄重构与 INSTALL / secret 边界提案值得集成者关注，尚不能当作正式版承诺。

以上为公开活动的**推测性归纳，不是官方路线图**。

## 覆盖与限制

- GitHub 搜索 API 按 updated 时间从 UTC 10 月 9 日 16:00 检索至 10 月 11 日 01:00，向窗口后延伸以减少后续更新造成的漏检；返回 82 个候选，单页完整读取，`incomplete_results=false`。其中 17 项在报道窗口创建，11 项在窗口合并，属于检索快照统计。
- 核对选入 PR 的作者、正文、创建或合并时间、目标分支和状态，并对关键实现及评审讨论作补充检查。没有把 updated_at 单独当作实质进展，也未逐条审计全部候选的历史事件。
- 重点检查 Mytherin、hannes、lnkuiper、pdet、Tishj、carlopi、hawkfish。Tishj 的 #25515、#25517 本期仅见 stale-bot 评论，不列为技术进展；Mytherin、hannes、lnkuiper 的本次作者检索未返回更新候选，不等于其没有其他公开活动。
- 与前日报对照去重；未访问内部问题链接或私人讨论，未全面覆盖独立扩展仓库，也未独立运行 DuckDB 测试或性能基准。博客 Feed 的访问限制如上。
