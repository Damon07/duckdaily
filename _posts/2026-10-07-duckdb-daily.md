---
title: "DuckDB 日报 · 2026-10-07：文件元数据接口、存储回收修复与轻量视图目录"
date: 2026-10-07 12:00:00 +0800
description: "Mytherin 推进 C API 单文件读取元数据传递；checkpoint 存储块回收修复已合并，扩展瘦身与优化器正确性有新提案，官网介绍只存视图的共享目录。"
coverage_date: "2026-10-07"
---

覆盖窗口：北京时间 **2026-10-07 00:00 至 2026-10-08 00:00，不含终点**，对应 UTC 10 月 6 日 16:00 至 10 月 7 日 16:00。实际核查时间：**2026-10-08 10:04—10:08（Asia/Shanghai）**。下文事件时间均为北京时间，状态以核查时为准。

## 今日速览

- **C API 文件读取继续补齐元数据通路。** Mytherin 提案让单文件函数直接接收打开选项，并把文件描述移入独立回调；尚未合并
- **存储与写出修复已落地。** checkpoint 不再漏记仍被扫描引用的空闲块；列段按行读取、Parquet VARIANT 禁用 shredding 的修复同时合并
- **官网介绍“只存视图的数据库”。** 把远程数据的查询定义放入小型 DuckDB 文件，以一个地址分享可查询目录；数据权限和远程文件布局仍是使用前提

**已合并不等于已发布。** 核查时[最新正式发布](https://github.com/duckdb/duckdb/releases/latest)仍是 9 月 28 日的 [v1.5.6](https://github.com/duckdb/duckdb/releases/tag/v1.5.6)。下述开发分支变更不能视作该正式版已包含。

## 重要 PR

### 1. Mytherin：把文件打开选项交给单文件函数

[#26584 — C API v2: pass the file to single-file functions together with its open options, and describe files through get_bind_info](https://github.com/duckdb/duckdb/pull/26584)，作者 **Mytherin**，本期 **00:21 新建**，目前 **open → v2.0-cyanoptera**。

单文件 C API 读取器此前只能拿到路径，可能需要再次请求文件大小、etag 等已经存在于 glob 结果或湖仓元数据里的信息。提案允许函数接收路径字符串，或含 filename 及打开选项的结构体，让这些信息传到实际文件打开环节。

另一部分是职责拆分：列标识和文件键值元数据改由 get_bind_info 描述，被扫描的表则交给独立 get_table_entry 回调。现有接收 VARCHAR 的单文件函数仍可使用，但只收到路径。对扩展作者，值得跟踪的是**输入签名和元数据回调迁移**；对远程读取，潜在收益是减少重复元数据请求，**目前没有可引用的端到端性能测量**。

### 2. checkpoint 补记“已释放、仍在使用”的块

[#26638 — Fix storage leak for blocks freed while still in use](https://github.com/duckdb/duckdb/pull/26638)，作者 **dentiny**，本期 **11:47 新建，22:19 merged → v2.0-cyanoptera**。

长扫描仍引用旧块时，更新和 checkpoint 可以把这些块标记为已释放但仍在使用。此前写入持久化空闲块列表时可能漏掉这部分记录，重启后块既不算已使用，也不在空闲列表中，造成存储空间泄漏。

[补丁](https://github.com/duckdb/duckdb/pull/26638/files)把 free_blocks_in_use 纳入写入的空闲块集合，回归场景覆盖长扫描与连续 checkpoint 交错后重启。它修的是**块回收记账**，不是承诺立即缩小数据库文件，也没有证据可将其泛化为数据丢失修复。

同作者的 [#26645 — Fix out-of-bound access for column segment](https://github.com/duckdb/duckdb/pull/26645) 于 **14:08 新建、22:19 merged → v2.0-cyanoptera**。按行获取列段数据时，改用段内位置计算行号，避免把列内全局偏移传给期望段内偏移的 FetchRow。公开复现启用了 debug_force_fetch_row；不应据此声称所有普通扫描都会触发。

### 3. Parquet：禁用 VARIANT shredding 的选项真正生效

[#26462 — [Parquet] Fix disabling VARIANT shredding in COPY](https://github.com/duckdb/duckdb/pull/26462)，作者 **Tishj**，10 月 5 日创建，本期 **19:43 merged → v2.0-cyanoptera**。

原有测试虽然设置了禁用 shredding，却没有充分验证输出确实未被拆分存储，也未覆盖 SHREDDING 选项的多种输入形态。这次补齐测试并修正发现的问题。它关系到写出格式是否遵循调用者选项，**不是默认关闭 VARIANT shredding**，也没有新的压缩率或查询加速数据。

### 4. 优化器：数学上的单调性不能直接套用到浮点库

[#26592 — Drop the monotone annotation from exp(): libm exp is not monotone](https://github.com/duckdb/duckdb/pull/26592)，作者 **carlopi**，本期 **03:02 新建**，目前 **open → v2.0-cyanoptera**。

公开复现指出，Apple libm 的 exp 对某些相邻 DOUBLE 输入会出现舍入后的次序倒置。若优化器仍把它当作单调不减函数，就可能推导出错误的统计边界，产生内部错误，或通过统计传播和行组剪枝排除本应匹配的行。

提案移除 exp 的单调性标记，并加入与物化计算结果对照的回归测试。这是以减少一项不可靠优化换取正确性；**不是重新实现 exp，也没有宣称改善其数值精度**。触发条件依赖平台浮点库，不能把复现扩大到所有系统。

### 5. 扩展瘦身：借 C API 避免静态牵入完整执行路径

[#26690 — Add CreateAConnectionAndQuery … to significantly decrease aws extension size](https://github.com/duckdb/duckdb/pull/26690)，作者 **carlopi**，本期 **23:35 新建**，目前 **open → v2.0-cyanoptera**。

提案增加一次性建立连接并执行 SQL 的入口，通过 C API 函数表调用，避免扩展静态引用解析器、绑定器、优化器等重代码路径。作者报告 aws 扩展从 **51.79 MB 降至 21.65 MB，约缩小 58%**。

这些是**作者报告、未独立复测**，作者也明确将方案称为初步实现。数字仅指所测扩展包体积，不能等同于查询提速或运行时内存下降，更不能推广到所有扩展。

### 6. 并发写与聚合内存：两个值得跟踪的新提案

- [#26676 — Detect write-write conflicts between DELETE and UPDATE of the same row](https://github.com/duckdb/duckdb/pull/26676)，**ywelsch**，本期 **19:51 新建**，目前 **open → main**。提案让并发事务对同一行的 DELETE 与 UPDATE 双向冲突，而非两者都提交后悄然丢失一次写入；也涉及通过删除再插入执行的 UPDATE。若方案落地，碰到此类竞态的应用需要像处理其他写写冲突一样重试。**目前仍是提案，未形成正式版行为变更。**
- [#26682 — Cap the reservation request of the hash aggregate at the memory limit](https://github.com/duckdb/duckdb/pull/26682)，**Robinho-MR**，本期 **22:25 新建**，目前 **draft / open → v2.0-cyanoptera**。低 operator_memory_limit 下，哈希聚合可能反复翻倍申请临时内存，最终溢出，并在此前干扰其他算子的预留份额计算。提案以 buffer manager 的内存上限限制申请值；它限制的是**预留请求**，不能解读为所有查询实际内存的严格封顶。

## 官方新博客

[A DuckDB Database with No Data in It](https://duckdb.org/2026/10/07/view-only-mode.html)，**The DuckDB team，2026-10-07**。[官方 Atom feed](https://duckdb.org/feed.xml)标记 published 为 00:00 UTC，即北京时间 **08:00**，在本期窗口内。

文章演示把远程 Parquet 查询保存为视图，再将只含视图定义的 DuckDB 文件发布为可只读附加的共享目录。消费者使用稳定的关系名；发布者可通过更新视图适配底层分区和字段变化，而不必复制数据。

适合给已有数据湖提供轻量查询入口。限制是：消费者必须同时拥有目录和底层数据访问权限，HTTPS/S3 上的目录修改需要编辑本地副本后重新上传，查询性能仍依赖网络与文件布局。**这是使用模式介绍，不是新的正式版本发布。**

## 方向观察（推测）

本期提案与官网文章共同指向更清晰的“数据在哪里、引擎知道什么、扩展负责什么”：单文件读取沿用上游元数据，扩展通过更窄的调用边界减少体积，视图目录则把查询定义与数据文件分开分享。

另一条主线是为优化与并发划清正确性边界：exp 放弃不可靠的单调性假设，checkpoint 补齐块记账，并发 DELETE/UPDATE 提案补足冲突检测。

以上是对公开活动的**推测性归纳，不是官方路线图**。其中多个接口和并发行为仍未合并；扩展体积收益只有单个作者样本；轻量视图目录也没有消除权限、更新发布和网络成本。

## 覆盖与限制

- 检索官方 duckdb/duckdb 在窗口内创建、合并和最后更新的 PR，并完成搜索结果分页：创建查询 102 项、合并查询 15 项、updated 查询 153 项，三类去重为 186 个候选。按影响筛选，重点核对上述 PR 正文、状态及相关代码差异，兼顾核心维护者与其他贡献者
- 这些数字是本次检索结果，不是历史活动穷尽统计。updated 搜索只反映当前最后更新时间，窗口后再次更新的旧 PR 可能不在其中；未逐条审计所有评论和提交，也未全面覆盖扩展仓库
- 纳入依据为明确创建或合并时间，不把 updated_at 当作完成时间。PR 正文及补丁可能含核查前的后续修改，文中状态以核查时为准
- 官网新闻列表、文章和 Atom feed 已交叉核对。网页抓取工具读取 feed 失败后，使用普通 HTTP 请求成功读取，未把单一入口失败误报为没有新文
- 未独立运行 DuckDB 回归测试或性能基准；作者测量已标注。开发分支合并、未合并提案与正式发布分别呈现
