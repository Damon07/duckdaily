---
title: "DuckDB 日报 · 2026-10-14：多核修复与异步执行落地，Parquet 防护回移"
date: 2026-10-14 12:00:00 +0800
description: "多核回归修复、外部连接 Bloom filter 和异步展开语句进入开发分支，Parquet 越界写防护回移至 v1.5；Mytherin 参与评审连接内存与 VARIANT 语义改进。"
coverage_date: "2026-10-14"
---

## 覆盖窗口与核查时间

- 覆盖北京时间 **2026-10-14 00:00 至 2026-10-15 00:00**，左闭右开；对应 UTC **2026-10-13 16:00 至 2026-10-14 16:00**。
- 资料于北京时间 **2026-10-15 08:55–09:01**核查。下文事件时间均为北京时间，状态为核查时状态。
- **已合并不等于已发布。** 除另行标注，本文已合并 PR 的目标为 `v2.0-cyanoptera` 开发分支；维护分支的回移也不代表已有正式发行包。

## 今日速览

1. **开发分支集中收敛性能与正确性。** lnkuiper 的多核后续修复落地，外部哈希连接恢复完整构建的 Bloom filter，宽查询规划、过滤下推与低内存清理也有修复。
2. **异步查询语义进一步成形。** 展开为多个内部语句的操作可以作为一个查询和事务完成；结果状态通知、连接内存节省和秘密信息兼容仍有开放方案。
3. **v1.5 获得 Parquet 防护回移；未发现当日官方新博客。** 不将回移合并写成正式版本发布。

## 重要 PR

### 1. Mytherin 参与的主线：分支同步、连接内存与 VARIANT 语义

- [#27235 · Merge v2.0-cyanoptera into main](https://github.com/duckdb/duckdb/pull/27235)，作者 **Robinho-MR**；当天 **22:45:47 merged → main**。将当时的 v2.0 开发分支同步到 main，协调索引约束、PEG 解析器、检查点与异步 API 等差异。Mytherin 在 **22:07:59** [解释基准测试失败与 dbgen 改动的关系](https://github.com/duckdb/duckdb/pull/27235#issuecomment-6170293702)。这是代码分支集成；随后才合并到 v2.0 的其他 PR 不能一并视作已进入 main。
- [#27237 · Skip join output allocations for columns that only reference/slice existing vectors](https://github.com/duckdb/duckdb/pull/27237)，作者 **DinosL**；当天 **19:37:46** 创建，状态 **open → main**。链式 JOIN 会不断加宽中间 DataChunk，但很多列只引用已有向量；方案让算子声明这些列，避免无用 buffer 分配。Mytherin 当天 **21:54–21:55** [参与评审并建议简化接口](https://github.com/duckdb/duckdb/pull/27237#pullrequestreview-5519053995)。作者报告特定 40 层连接复现的峰值 buffer 内存从 2.0 nightly 的 6.59 GiB 降至 939 MiB；这是作者测试，尚未合并，也不是通用内存保证。
- [#27240 · Only apply a pushed-down cast to a shredded VARIANT field when it matches the VARIANT cast](https://github.com/duckdb/duckdb/pull/27240)，作者 **Robinho-MR**；当天 **19:54:49** 创建，状态 **open → main**。Tishj 当天批准评审，Mytherin 在 **20:14–20:15** [提出修改意见](https://github.com/duckdb/duckdb/pull/27240#discussion_r4270603350)，推动统一普通 VARIANT 转换和 shredded 字段转换语义，避免相同值因存储布局或下推路径不同而得到不同结果。当前方案仍在评审，不能视作所有转换兼容性问题已经解决。

### 2. lnkuiper：多核后续修复与两组正确性修复合并

[#27142 · Many-core regressions follow-up](https://github.com/duckdb/duckdb/pull/27142)，作者 **lnkuiper**；当天 **22:47:58 merged**。继 #26967 后继续处理相对 v1.5 的多核回归，提交涉及动态过滤共享锁、Top-N 边界读取、read-ahead 预留、只引用列的分配和本地读取 buffer 预触页等。当天还补充了 DuckLake 动态过滤读取端的共享锁适配。意义是减少并发争用和不必要的内存工作，不能据此宣布全部回归消失。

同一作者的两组汇总也在 **22:47:58–59 merged**：
- [#27059 · Combined PR](https://github.com/duckdb/duckdb/pull/27059) 集成 12 项已审阅修复，包括 Arrow 数组所有权、TRY 中异常转换、prepared currval 重绑定及窗口任务分配。
- [#27147 · Combined PR: minor fixes](https://github.com/duckdb/duckdb/pull/27147) 集成 9 项修复，包括非对齐 Arrow buffer、嵌套排序规则、DISTINCT 逻辑比较键与选定溢出字符串读取。作者明确说明部分强制 RLE 场景仍有性能代价，不能把这组改动概括为全面提速。

这些汇总含已有源 PR，不应把汇总数量再当作独立新功能数量叠加。

### 3. hannes：Parquet 越界写防护回移至 v1.5

[#27143 · [Parquet] Backport of #23420 and #26564](https://github.com/duckdb/duckdb/pull/27143)，作者 **hannes**；当天 **21:33:45 merged → v1.5-variegata**。

回移两处针对异常 Parquet 文件的防护：长度 buffer 大小乘法溢出检查，以及列表重复级别造成首元素索引下溢时的运行时检查。它们针对可能触发堆越界写的输入，值得需要读取外部文件的用户关注。这里能确认的是维护分支已接收修复，未据此宣称稳定版已经更新，也未推断公开漏洞编号或影响版本范围。

### 4. 异步执行：展开语句合并落地，通知回调仍开放

[#27108 · [async results] Run a statement that expands into several as one query](https://github.com/duckdb/duckdb/pull/27108)，作者 **evertlammerts**；当天 **15:37:49 merged**。动态 PIVOT、部分 ALTER、IMPORT 等展开操作现在按一次提交查询运行：自动提交在结果完成时才提交，提前关闭或出错则回滚。元数据需等到实际产出行的语句绑定后才能获取，ADBC 与 C API 仍有明确边界。Mytherin 的批准发生在前一覆盖日，今日新增事件是合并。

后续 [#27250 · [async results] Notify the consumer of a query result when its state changes](https://github.com/duckdb/duckdb/pull/27250) 由同一作者于当天 **22:38:39** 创建，状态 **open**。拟用状态通知回调让消费者等待唤醒，减少持续轮询；回调不可阻塞、抛异常或重新调用 DuckDB。C API v2 暴露该回调仍列为后续工作。

### 5. 外部连接：在保证过滤器完整的前提下恢复下推

[#26959 · Restore bloom filter pushdown for external hash joins](https://github.com/duckdb/duckdb/pull/26959)，作者 **kryonix**；当天 **19:30:10 merged**。

对预计会 spill 的连接，在 Sink 阶段累计整个 build side 的 Bloom filter，完成封存且有用后才发布。若原本预计在内存中的连接意外 spill，则安全退回不使用 Bloom filter。它主要帮助 min/max 范围内仍有大量不匹配 probe key 的查询；作者也报告无法额外过滤时会有构建开销，因此收益依赖工作负载。

**对昨日实现说明的更正：** #25718 的描述仍保留遍历分区重建过滤器的早期方案，但其[最终 diff](https://github.com/duckdb/duckdb/pull/25718/files)实际通过禁用外部连接 Bloom 下推修复漏行。今日 #26959 才用新的完整构建方式恢复下推。昨日“修复漏行”的结论不变，实现机制应以最终代码为准。

### 6. 数据正确性与资源边界：几项值得关注的合并

- **过滤下推不能改变结果。** [#26968 · Do not consider narrowing DECIMAL casts and structure-changing nested casts invertible](https://github.com/duckdb/duckdb/pull/26968) 和 [#26990 · Only rewrite filters into the file type when the cast from the file type is invertible](https://github.com/duckdb/duckdb/pull/26990)，作者均为 **Robinho-MR**；以及 **PeterVanHolland** 的 [#27100 · Do not push a filter into the reader when the file column is read with a lossy cast](https://github.com/duckdb/duckdb/pull/27100)，均于当天 **22:47:59–22:48:01 merged**。分别补齐 DECIMAL/嵌套类型可逆性判断、文件类型转换方向检查和纳秒时间精度缩减边界，避免错误返回行或静默漏行。
- **宽查询规划。** [#27104 · Avoid quadratic planning time for queries with many columns](https://github.com/duckdb/duckdb/pull/27104)，作者 **Robinho-MR**；**22:47:59 merged**。通过复用列统计查找表、一次性移除无用列，减少按列反复扫描与删除造成的二次复杂度。
- **低内存时应报错而非崩溃。** [#27212 · Release pin handles when finalizing the pin state of a collection without segments](https://github.com/duckdb/duckdb/pull/27212)，作者 **h4nsmuller**；**19:01:31 merged**。处理聚合 repartition 遇到 OOM 后的清理路径，避免对已空 collection 解引用。其 [#26981 · Allocate the window partition, order and filter masks through the buffer allocator](https://github.com/duckdb/duckdb/pull/26981) 于 **16:06:28 merged**，把窗口掩码分配纳入 buffer allocator 的内存预算。
- **HTTP 重试抑制故障放大。** [#26947 · HTTP retries: full-jitter back-off with a cap, per-host retry quota, attempt hook](https://github.com/duckdb/duckdb/pull/26947)，作者 **h4nsmuller**；**22:48:01 merged**。加入有上限的随机退避、按主机共享重试配额，并使 http_retries=0 真正禁用重试。完整的 provider 结果确认协议仍需配套 httpfs 改动，不能将 core 合并等同于全部 S3 行为已经更新。

### 7. 新提案：旧版秘密信息兼容与数值稳定性

- [#27257 · Fix reading secrets from older versions and redact HTTP headers in secrets](https://github.com/duckdb/duckdb/pull/27257)，作者 **HendrikLambert**；当天 **23:41:15** 创建，状态 **open**。接替 #26901，聚焦恢复 1.1.0、1.1.2、1.1.3 写出的持久化秘密信息读取，并遮蔽 HTTP headers；此前的认可不等于这个新 PR 已合并。同日 **Robinho-MR** 的 [#27253](https://github.com/duckdb/duckdb/pull/27253) 也在处理旧版嵌套值反序列化兼容，仍 **open**，应关注最终采用的修复边界。
- [#27214 · Accumulate central moments for skewness and kurtosis instead of raw power sums](https://github.com/duckdb/duckdb/pull/27214)，作者 **h4nsmuller**；当天 **13:59:32** 创建，状态 **open**。拟用稳定的在线中心矩算法，修复常量或近常量数据在偏度、峰度计算中的浮点抵消问题，并涉及导出聚合状态布局变化。它仍是待评审方案，尚不能称数值问题已在发布版修复。

### 8. 其他核心贡献者动态

- **Tishj** 的 [#27160 · [Parquet][Copy] Make the 'SHREDDING' option preserve case for column names](https://github.com/duckdb/duckdb/pull/27160)（**01:07:12** 创建）和 [#27248 · [Parquet][Variant][COPY] Sort written field-ids by their corresponding field names, lexicographically](https://github.com/duckdb/duckdb/pull/27248)（**21:48:17** 创建），均 **open → main**。分别修正大小写匹配与 Parquet VARIANT 写出顺序；评审标签不能代替合并状态。
- **hawkfish** 的 [#27191 · ICU DATE_PART Nanoseconds](https://github.com/duckdb/duckdb/pull/27191)（**05:58:49** 创建）和 [#27198 · MAKE_TIMESTAMP Bounds Checks](https://github.com/duckdb/duckdb/pull/27198)（**08:15:26** 创建），均 **open → main**。前者补充纳秒带时区时间戳的字段提取，后者加强时间戳构造的越界检查；均未按已落地功能报告。
- **carlopi** 当天 **02:41:45** [批准](https://github.com/duckdb/duckdb/pull/27134#pullrequestreview-5508310911) **maiadegraaf** 的 [#27134 · Re-enable vortex at e4b9a57](https://github.com/duckdb/duckdb/pull/27134)，后者于 **22:47:58 merged**，重新启用 Vortex 并更新对应版本固定点。
- **pdet** 的 [#26927](https://github.com/duckdb/duckdb/pull/26927) 虽有当日更新时间，但所核查的最后提交和讨论均在覆盖窗口之前，因此不将它重复列为当日实质进展。

## 官方博客

交叉检查[官方新闻索引](https://duckdb.org/news/)、[官网文章源码目录](https://github.com/duckdb/duckdb-web/tree/main/_posts)及目标时间窗的文章目录提交记录，**未发现当日新博客，也未发现该目录在窗口内的新提交**。

最新可见文章仍为 The DuckDB team 于 **2026-10-09** 发布的 [Agent Mode in the DuckDB CLI](https://duckdb.org/2026/10/09/agent-mode)。这是既有文章，不计作本日新发布内容。

## 方向观察（推测）

- **推测：v2.0 开发工作的重点继续向性能回归和边界正确性收敛。** 依据是多核、过滤下推、OOM 清理和多组修复的集中合并，同时存在向 main 的同步。反面证据是仍有连接分配、秘密信息兼容和数值稳定性新 PR 开放；这些活动不能推导正式发布日期或“回归已经清零”。
- **推测：异步执行正在从能运行走向更完整的消费协议。** 展开语句事务已落地，状态通知另行评审，说明事务完成、结果元数据和消费者唤醒都在细化。回调的 C API 支持尚未落地，不能据此宣称各客户端已具备同样能力。

## 覆盖与限制

- GitHub API 按窗口起点之后的 updated 检索，读取 **7 页、623 个去重 PR 候选**；结果包含窗口之后的变化，且不少旧 PR 在同一时段集中更新，**不等于当日新增 623 个 PR**。纳入正文的创建、合并和评审另核对实际时间；未把单纯 updated_at 变化当成实质进展。
- 优先核查 Mytherin 的参与及 hannes、lnkuiper、pdet、Tishj、carlopi、hawkfish 等贡献者，同时保留其他作者的重要变化。本文为重要变化筛选，不是全部 PR、评论或提交的 changelog。
- [RSS](https://duckdb.org/feed.xml)抓取返回错误；博客结论来自新闻索引与官方源码交叉检查，不能说 RSS 已成功确认无更新。
- 未访问 PR 引用的内部 issue，未本地复测 DuckDB 性能或测试结果。文中的作者测量与提案目标均保留其范围，不当作独立验证或官方路线图。
