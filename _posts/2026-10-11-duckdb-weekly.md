---
title: "DuckDB 周报 · 2026-10-05—2026-10-11：v2.0 接口重构、并发边界与回归收敛"
date: 2026-10-11 12:00:00 +0800
description: "类型与文件元数据接口逐步清晰，checkpoint、资源预算和 Parquet 正确性集中改进；官方介绍 Java 导入、轻量视图目录与 CLI Agent Mode。"
coverage_date: "2026-10-05—2026-10-11"
permalink: /weekly/2026/10/11/
---

覆盖窗口：北京时间 **2026-10-05（周一）00:00 至 2026-10-12（周一）00:00，左闭右开**，对应 UTC 10 月 4 日 16:00 至 10 月 11 日 16:00。实际核查时间：**2026-10-12 09:00—09:04（Asia/Shanghai）**。下文日期和事件时间均为北京时间；状态以核查时为准，窗口外变化单独标明。

本周最值得关注的不是孤立的新功能，而是几条相互关联的工程主线：**引擎与扩展之间的职责拆分、并发存储的安全边界、资源使用与查询回归的收敛，以及嵌套数据语义的保真。** 这是基于公开活动的主题归纳，不是官方路线图。

核查[官方最新发布记录](https://github.com/duckdb/duckdb/releases/latest)，最新正式版仍为 **[v1.5.6](https://github.com/duckdb/duckdb/releases/tag/v1.5.6)，9 月 28 日发布**。本周没有发现新的正式版本；以下“merged”均指开发分支合并，**不等于已经进入稳定版**。除明确注明 main 外，本文列出的 PR 均面向 **v2.0-cyanoptera**。

## 一、Mark 的接口重构：先明确类型，再建立执行状态

Mark Raasveldt（**Mytherin**）本周两项合并可以连起来看：

- [#26548：拆分 ScalarFunction 的 resolve_types 与 bind](https://github.com/duckdb/duckdb/pull/26548)，10 月 6 日提出、**10 月 8 日 merged**。调用顺序变为选择重载、解析类型、转换参数、最后 bind。这样执行状态初始化拿到的已经是函数真正接受的参数，减少嵌套类型、NULL 和预处理参数带来的隐式假设。
- [#26584：单文件函数接收文件打开选项，文件描述移入 get_bind_info](https://github.com/duckdb/duckdb/pull/26584)，**10 月 7 日 00:21 提出、10 月 9 日 merged**。读取器可收到包含 filename、etag 等信息的结构值，复用 glob 或湖仓目录已提供的元数据；列标识、文件元数据和扫描表的描述也进一步拆分。这里按北京时间归档，不把 UTC 的 10 月 6 日误作本地创建日。

**hannes** 的 [#26553：typed NULL 函数折叠先确定返回类型](https://github.com/duckdb/duckdb/pull/26553)，**10 月 9 日 merged**，是类型职责拆分的直接应用；它避免过早折叠使类型信息丢失，但仍在 bind 中确定返回类型的函数尚未全部迁移。

与此同时，**Maxxen** 的 [#26820：C API v2 通用 factory / config 句柄](https://github.com/duckdb/duckdb/pull/26820) 从 10 月 10 日提案推进到 **10 月 11 日 22:49 merged**。对象创建、配置访问集中到共享句柄，实例支持 startup options，并补充函数文档和公共类型推导入口。

**对集成者的意义：** 需要关注回调执行顺序、元数据通路与句柄职责的迁移，而不能只检查 SQL 是否还能运行。上述变化并不证明整个 v2 API 已经稳定，也没有提供可直接推广的远程读取加速数据。

## 二、checkpoint：扩大并发范围，同时收紧持久化不变量

本周这条主线的完整过程是“评审发现风险 → 缩小支持范围 → 合并有限能力”。

**ywelsch** 的 [#26456：部分 DDL 与序列操作可和 checkpoint 并行](https://github.com/duckdb/duckdb/pull/26456)，10 月 5 日提出、**10 月 8 日 merged → main**。Mytherin 在 10 月 5 日的[评审](https://github.com/duckdb/duckdb/pull/26456#issuecomment-5994374368)中给出 SET NOT NULL 与 checkpoint、并发插入竞态的失败复现，包含已提交批次丢失。最终范围排除了 SET NOT NULL 等改变表存储的操作；视图、部分 schema 操作、重命名和序列使用获得更大并发空间。

这个风险属于**待合并实现的评审发现**，不能直接写成已确认的稳定版数据丢失缺陷。Mark 在这里是评审者，PR 作者是 ywelsch。同作者的 [#26478：UPDATE 事务与 checkpoint 并行](https://github.com/duckdb/duckdb/pull/26478) 本周提出，核查时仍 **open → main**，说明并发范围尚在继续探索。

持久化路径的几项已合并修复也应区分影响：

- **dentiny**：[#26638](https://github.com/duckdb/duckdb/pull/26638)，**10 月 7 日 merged**，把已释放但仍被扫描引用的块纳入持久化空闲块记账；[#26722](https://github.com/duckdb/duckdb/pull/26722)，**10 月 9 日 merged**，修正 checkpoint 与块分配竞态中的数据库头信息一致性。两者针对空间回收，不意味着数据库文件立即缩小。
- **kryonix**：[#26716](https://github.com/duckdb/duckdb/pull/26716)，**10 月 9 日 merged**，阻止旧块句柄读盘与元数据原地重写发生竞态。公开复现中磁盘文件本身完好，修的是虚假校验和失败及相关句柄生命周期问题。
- **ywelsch**：[#26750](https://github.com/duckdb/duckdb/pull/26750)，**10 月 9 日 merged**，使 checkpoint 期间的重复键在 INSERT 时就报错，避免应用直到 COMMIT 才失去整个显式事务。旧行为也不会提交重复键。

约束语义方面，**artjomPlaunov** 的 [#26423：DEFERRED PRIMARY KEY / UNIQUE](https://github.com/duckdb/duckdb/pull/26423) 于 **10 月 6 日 merged → main**，允许事务中暂时重复、提交前修复；主键 NOT NULL 仍即时检查，延迟键也不能作为外键引用目标或 ON CONFLICT 目标。同作者本周提出的 [#26814：checkpoint 前绑定有缓冲重放的索引，否则保留 WAL](https://github.com/duckdb/duckdb/pull/26814) 仍 **open**，不能算作已经交付的索引保护。

## 三、性能主线：减少无效工作，并让资源预算更贴近真实限制

### 解析器、执行器与优化器一起收敛

**carlopi** 的 [#26451：PEG FIRST-set 剪枝](https://github.com/duckdb/duckdb/pull/26451) 与 [#26479：legacy_parser 过渡扩展](https://github.com/duckdb/duckdb/pull/26479) 均于 **10 月 8 日 merged**。前者跳过不可能匹配当前 token 的子规则；作者语料上的解析耗时中位数从 65.7 μs 降至 29.8 μs，**仅是作者的解析器微基准，未独立复测**。后者提供尽力兼容的旧解析器入口，便于定位迁移问题，不支持所有新语法。其 [#26771：解析器健壮性](https://github.com/duckdb/duckdb/pull/26771) 于 **10 月 10 日 merged**，整合表达式嵌套深度检查及测试。

**lnkuiper** 的 [#26791：Regression fixes](https://github.com/duckdb/duckdb/pull/26791) 于 **10 月 9 日提出并 merged**，修正热循环、表过滤及部分优化器回归；同日提出的 [#26812：Join order regression fixes](https://github.com/duckdb/duckdb/pull/26812) 核查时仍 **open**，涉及采样、基数估算和运行时过滤成本。不能把前一项合并概括成 v2.0 的连接顺序回归已经全部解决。

正确性也约束着优化：**carlopi** 的 [#26592](https://github.com/duckdb/duckdb/pull/26592) 于 **10 月 8 日 merged**，移除 exp 不可靠的单调性标记；**kryonix** 的 [#26807](https://github.com/duckdb/duckdb/pull/26807) 于 **10 月 10 日 merged**，保留可能抛错的过滤条件位置，避免过滤上拉破坏求值语义和连接重建。数学性质、浮点实现和可移动表达式之间需要明确边界。

### 资源控制是分层改进，不是统一内存硬上限

- **jdctinuiti** 的 [#25913：分区 COPY 刷出期间限制缓冲增长](https://github.com/duckdb/duckdb/pull/25913)，**10 月 6 日 merged**，通过生产者背压限制等待批次，条件仍按行数判断。
- **J-Meyers** 的 [#25060：尊重 ROW_GROUP_SIZE_BYTES](https://github.com/duckdb/duckdb/pull/25060)，**10 月 6 日 merged**，让宽行批次可以在 chunk 内细分；它是压缩前尺寸的尽力控制，并非硬上限。
- **pdet** 的 [#25183：异步积压预算受 memory_limit 约束](https://github.com/duckdb/duckdb/pull/25183)，**10 月 10 日 merged**，预算上限设为 memory_limit/8，最低预留也受 memory_limit/16 限制；这只是该预算，不是整个进程的实际内存承诺。
- **Tobias2099** 的 [#25707：CTAS 临时空间复用](https://github.com/duckdb/duckdb/pull/25707)，**10 月 10 日 merged**；**d-justen** 的 [#26166：聚合哈希表自适应扩容](https://github.com/duckdb/duckdb/pull/26166)，**10 月 9 日 merged**，分别减少临时块浪费和扩容中的性能陡变。

这些 PR 多数早于本周创建，本周新闻点是实际合并。没有统一可比基准，不能把各自测量相加成总体加速比。

## 四、Parquet 与湖仓：从“能读写”推进到保留 schema、统计与值的语义

**Tishj** 的 [#26538：RETURN_STATS 补充 STRUCT/LIST 容器统计](https://github.com/duckdb/duckdb/pull/26538) 和 **h4nsmuller** 的 [#26516：多文件扫描接收 column_statistics](https://github.com/duckdb/duckdb/pull/26516) 均于 **10 月 8 日 merged**。前者区分整个结构为 NULL 与成员为 NULL，后者让目录或上游 COPY 生成的统计进入后续扫描。统计真实性仍由调用者负责，行数仍通过 explicit_cardinality 单独提供。

这与 Mytherin 的文件打开元数据通路形成呼应：**上游已经知道的信息，可以更明确地交给引擎使用。** 但这属于本文的工程归纳，并不等于官方承诺一个统一的湖仓架构。

另两项落地变化关注数据含义：
- **Tishj** 的 [#26777：嵌套字段提取下推的 schema 重映射](https://github.com/duckdb/duckdb/pull/26777)，**10 月 9 日 merged**，修正字段删除、重新加入等演进场景中 NULL、字段 ID、转换和默认值的应用。
- **hawkfish** 的 [#26503：Parquet INT96 类型选择](https://github.com/duckdb/duckdb/pull/26503)，**10 月 10 日 merged**，增加 timestamp、timestamp_ns、struct 读取选择；纳秒表示超范围时饱和为正负无穷，精度与日期范围需要一起考虑。

本周末仍 **open** 的工作说明边界尚未收敛：
- **Tishj** 的 [#26808](https://github.com/duckdb/duckdb/pull/26808)，10 月 9 日提出，支持嵌套位置的 VARIANT 写出；作者明确列出临时内存代价，未提供前后性能基准。
- **louie-duck** 的 [#26854](https://github.com/duckdb/duckdb/pull/26854)，10 月 11 日提出，修正按字节预算分批时跨越分区边界的问题。作者定位到 #25060 引入的 2.0 回归：**总行数可能正确，但行被写进错误分区**。这是本周性能改动与周末正确性跟进之间的重要联系。
- 同作者 10 月 11 日提出的 [#26855](https://github.com/duckdb/duckdb/pull/26855) 和 [#26846](https://github.com/duckdb/duckdb/pull/26846)，分别保留 Parquet 浮点字典中的正负零区别、避免列表内 NULL struct 的叶子统计重复计数。二者都不能写成稳定版已修复。

## 五、调用方的错误与访问边界更明确

**evertlammerts** 的 [#26704：ADBC 转向 ArrowFormat](https://github.com/duckdb/duckdb/pull/26704) 于 **10 月 8 日 merged**，统一结果转换路径，并修正取消、写入末尾失败、空参数流等错误行为。其 [#26747](https://github.com/duckdb/duckdb/pull/26747) 于 **10 月 10 日 merged**：连接仍持有未结束结果时，新 Submit / Query 返回 RESOURCE_IN_USE，而非中止原结果；调用方需要先消费或销毁结果。这是扩大流式执行支持的一步，不代表所有查询的流式改造已经完成。

**HendrikLambert** 的 [#26522：HTTP 日志脱敏](https://github.com/duckdb/duckdb/pull/26522) 于 **10 月 8 日 merged**，对非允许列表的请求/响应头值及 URL 敏感部分脱敏。**carlopi** 的 [#26821：INSTALL 路径外部访问检查](https://github.com/duckdb/duckdb/pull/26821) 和 **Robinho-MR** 的 [#26823：secret scope 按路径边界匹配](https://github.com/duckdb/duckdb/pull/26823) 于 10 月 10 日提出，核查时仍 **open**。日志改进与待合并访问控制必须分开看，不能据此宣称完整沙箱或全部敏感信息保护已经实现。

## 六、三篇官方文章：数据入口、共享目录、代理交互

按[官方博客列表](https://duckdb.org/news/)的标注日期，本周三篇文章各有不同实践重点：

1. **10 月 5 日：[Importing Data using Java Table Functions](https://duckdb.org/2026/10/05/import-data-with-java)**，署名 Guest Author、Geertjan Wielenga、Alex Kasko。以 MongoDB 导入为例比较 JDBC、Appender 与 Java 表函数，强调批量拉取、并行导入及资源约束。案例计时不能当成通用保证。
2. **10 月 7 日：[A DuckDB Database with No Data in It](https://duckdb.org/2026/10/07/view-only-mode)**，The DuckDB team。用只含视图的 DuckDB 文件分享远程数据目录，底层数据不搬迁；访问者仍需要数据权限，远程目录修改需本地编辑后重新上传，性能取决于网络和文件布局。
3. **10 月 9 日：[Agent Mode in the DuckDB CLI](https://duckdb.org/2026/10/09/agent-mode)**，The DuckDB team。v2.0 CLI 面向编程代理提供紧凑表格、显式截断、JSON 错误及成本/进度反馈。官方 TPC-H 实验中，查询输出读取 token 减少 **59%**，但总体成本和运行时间没有相应改善；不能把输出变短直接等同于端到端提效。

这些是使用模式和开发版体验介绍，不是本周正式发布公告。页面日期、Feed 日期零点、源码合并和实际部署时刻不同；本报按官网标注日期收录，不声称核实到精确首发时分秒。

## 下周观察点（推测）

- **接口迁移是否继续收敛：** C API 类型、文件元数据和公共句柄已变化，集成方仍应以具体分支与接口为准，不能推断最终兼容承诺。
- **性能改进之后的回归验证：** join order 后续仍 open，分区 COPY 新提案揭示只核对总行数还不够；应连同分区键、嵌套 NULL、正负零和类型范围检查结果语义。
- **checkpoint 并发的剩余边界：** UPDATE 并发与 WAL/索引保护仍未合并，后续评审和测试比笼统的“支持更多并发”更值得跟踪。

补充当前状态：**kryonix** 的 [#26843：带类型子树替换的 SQL 导出](https://github.com/duckdb/duckdb/pull/26843) 于 **10 月 11 日 02:00 创建**，但实际 **10 月 12 日 07:27 才 merged**，已经超出本周窗口。因此本周只计为新提案，不计为周内合并成果。

以上观察均为**推测性归纳，不是官方路线图、发布日期或性能承诺**。

## 覆盖方法与限制

- 已读取 10 月 5—11 日七篇日报作为线索，再直接复核 **38 项官方 duckdb/duckdb PR** 的作者、正文、创建时间、合并时间、目标分支与当前状态，并核对 Mark 的关键评审、官方博客列表及三篇原文、官方最新发布记录。日报只作发现线索，不用旧日报的 open 状态替代当前原始记录。
- 本报按主题合并连续进展；同一 PR 的提出、讨论和合并不当作三个独立功能。没有把每日候选数相加成周活跃度统计，也没有把 updated_at 当成完成时间。
- 本轮不是全仓库活动或所有历史评论的穷尽审计；重点覆盖 Mytherin、hannes、lnkuiper、pdet、Tishj、carlopi、hawkfish，同时按实际影响纳入其他贡献者。未全面扫描独立扩展仓库、未公开讨论及所有补丁版本。
- PR 当前正文可能包含窗口后的编辑；周内事件以实际时间戳区分。未独立编译、运行回归测试或重测性能，作者基准均按来源限定。
- 官网 view-only-mode 的带 .html 入口首次抓取失败，改用官方无后缀页面后完成读取；没有把读取失败解释为没有文章。本轮未独立复查 Feed，全周博客结论限于已读取的官方列表与原文。
