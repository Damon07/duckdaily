---
title: "DuckDB 日报 · 2026-10-19：S3 URL 兼容变化，解析与规划减负"
date: 2026-10-19 12:00:00 +0800
description: "S3 URL 默认解释规则变化值得迁移关注；PEG 解析、相关子查询规划、文件描述符预算与外部缓存核算取得进展。"
coverage_date: "2026-10-19"
---

覆盖窗口：北京时间 **2026-10-19 00:00 至 2026-10-20 00:00**，不含终点；对应 UTC 2026-10-18 16:00 至 2026-10-19 16:00。实际检查：北京时间 **2026-10-20 09:04**。以下事件时间均为北京时间。

## 今日速览

- **兼容性重点：** v2.0 分支引入 S3 URL 新默认解释方式，问号及后续文本成为对象键的一部分，旧式 URL 参数需要显式选择。
- **性能与资源管理：** PEG 解析、宽表相关子查询规划、Parquet 文件描述符预算和外部文件缓存核算均有重要合并。
- **设计讨论：** Mytherin 提出用类型系统统一携带敏感标记；Bloom index 是否进入核心仍有明确分歧，不能当成确定路线。

截至检查，[官方最新正式版本](https://github.com/duckdb/duckdb/releases/tag/v1.5.6)仍为 9 月 28 日发布的 v1.5.6。**下述合并不等于稳定版已经提供这些变化。**

## 重要 PR

### 1. S3 URL 默认语义变化：不能只当作扩展版本更新

**[#27476](https://github.com/duckdb/duckdb/pull/27476)**，作者 **lnkuiper**，**merged**，22:13 合入 v2.0-cyanoptera，引入 [httpfs #491](https://github.com/duckdb/duckdb-httpfs/pull/491)。

S3 URL 默认不再解析问号后的旧式参数，而把问号及后续文本视为对象键字节。新设置 s3_enable_deprecated_url_parameters=true 可恢复旧行为；显式设置 false 则在该数据库实例中不可逆地禁用旧解释。上游提醒应在读取前确定配置，因为缓存不会隔离解释模式变化。依赖旧 URL 参数的调用方需要关注这一兼容边界；本文不意味着用户现用稳定版已改变。

### 2. PEG 解析器：折叠匹配链，减少名称查询与临时内存

**[#27395](https://github.com/duckdb/duckdb/pull/27395)**、**[#27478](https://github.com/duckdb/duckdb/pull/27478)**，作者 **Dtenwolde**，承接 **lnkuiper** 的性能工作，分别于 18:10、22:27 **merged** 至 main。

前者折叠 matcher 列表链、跳过不可能匹配的分支，并缩小 ParseResult；后者以 PEGRuleId 替代规则名称查询并回收 transform 临时内存。意义是降低查询进入执行器之前的成本。作者的 M5 Pro 解析微基准及后续 CI 数据均显示收益，但负载与测量范围不同，不能相加，也不能外推为所有 SQL 的端到端提升。

### 3. 相关子查询规划：处理宽表下的二次复杂度

**[#27391](https://github.com/duckdb/duckdb/pull/27391)**，作者 **kryonix**，**merged**，19:31 合入 main。

为 DelimJoinCTERewriter 的列绑定替换图建立索引，并按子节点输出边界裁剪。作者在“200 列、20 个相关子查询”的复现中报告 EXPLAIN 从 47.1 秒降至 0.41 秒；这是特定规划退化案例，不是通用查询加速比。Mytherin 当天参与回应，该项已从提案进入代码合并阶段。

### 4. 文件描述符与缓存：完善资源预算和内存核算

- **[#26927](https://github.com/duckdb/duckdb/pull/26927)**，作者 **pdet**，20:48 **merged** 至 main。多 Parquet 文件扫描将“正在打开”与“已预先打开”的文件一并计数，按进程文件描述符上限控制预打开预算，降低低限额环境中 Too many open files 风险。仍保留保证执行推进的例外，不是整个进程的绝对硬上限。讨论提出了 v2.0 回移需求，不能据此认为回移已完成。
- **[#26379](https://github.com/duckdb/duckdb/pull/26379)**，作者 **dentiny**，22:05 **merged** 至 main。修复外部文件缓存块元数据未被正确计入内存的问题，增加 buffer-pool reservation 与内存压力下的驱逐处理。对持续读取外部文件的长运行进程尤其相关。

### 5. 数值与文件格式能力补齐

- **[#26932](https://github.com/duckdb/duckdb/pull/26932)**，作者 **h4nsmuller**，15:20 **merged** 至 main。为 BIGNUM 增加乘法、整数除法和取模，并修复长整数取负后的比较问题。这为更宽 DECIMAL 打基础，不等于任意精度 DECIMAL 已经实现。
- **[#27367](https://github.com/duckdb/duckdb/pull/27367)**，作者 **RileyWen**，16:06 **merged** 至 main。支持 Parquet FIXED_LEN_BYTE_ARRAY 的 BYTE_STREAM_SPLIT 编码，覆盖相应 DECIMAL、UUID、FLOAT16 与 BLOB 读取路径。相关集成 [#27382](https://github.com/duckdb/duckdb/pull/27382) 作为同一项能力处理，不重复计数。

### 6. C API v2 profiling 与扩展设置枚举

**[#26874](https://github.com/duckdb/duckdb/pull/26874)**，作者 **Maxxen**，04:54 **merged** 至 v2.0-cyanoptera。移植 profiling 指标接口，返回需要显式释放的独立快照。[作者当天说明](https://github.com/duckdb/duckdb/pull/26874#issuecomment-6254242793)为避免新 API 功能倒退先纳入 v2.0，未来稳定前仍需调整；这不是稳定 API 承诺。

**[#27432](https://github.com/duckdb/duckdb/pull/27432)**，作者 **carlopi**，02:10 **merged** 至 v2.0-cyanoptera，属于本日而非前一日报窗口。除更新 httpfs、删除本地补丁外，新增 duckdb_settings(include_all := true)，让设置枚举包括 debug 和 deprecated 项，供扩展自动加载入口生成使用。

## 当日提出，次日才合并

- **[#27472](https://github.com/duckdb/duckdb/pull/27472)**，作者 **lnkuiper**，19:43 创建。增加 BlockAllocator 衰减回收、后台有限回收和 CPU 局部 AllocationCache。当天提交明确保留 opt-in，不能写成默认开启。**日界状态为提案；检查时已 merged，实际合并为 10 月 20 日 03:07。**
- **[#27477](https://github.com/duckdb/duckdb/pull/27477)**，作者 **lnkuiper**，20:40 创建。减少字符串公共前缀的重复比较，并更早释放外部归并堆块；作者特定长键/公共前缀场景有收益，不能外推。**日界尚未合并；检查时已 merged，实际合并为 10 月 20 日 01:32。**

## 维护者讨论与方向观察

**设计讨论，未落地：** [Mytherin 在 #27407 的评论](https://github.com/duckdb/duckdb/pull/27407#issuecomment-6261900185)于 15:20 建议由类型系统携带敏感标记，以统一 SQL 导出、secret 与日志脱敏；Maxxen 讨论了参数化类型、自定义 cast 等前提。这是公开技术方向探索，不是官方发布计划。

**仍有分歧：** [lnkuiper 在 Bloom index #27402 的评论](https://github.com/duckdb/duckdb/pull/27402#issuecomment-6262907223)于 16:22 认为目前优势不足以支持进入核心，建议作为扩展实现。因此不能把该个人 PR 描述为核心索引路线已经确定。

**方案调整：** [hannes 在 #27282 的评论](https://github.com/duckdb/duckdb/pull/27282#issuecomment-6261585042)于 14:59 质疑 Go 绑定必须在仓库保存静态归档的前提；作者随后提出自托管 Go 模块原型并关闭 PR。状态为 **closed，未合并**，不能写作方案落地。

**推测：** 解析、规划重复工作与文件/缓存预算同时获得修复，显示当日一条主线是治理通用路径的额外成本和资源退化。各项属于不同阶段和负载，现有证据不支持统一的端到端加速数字。

## 官方博客

交叉核对[官网新闻](https://duckdb.org/news/)与[官方 Atom feed](https://duckdb.org/feed.xml)，**未发现 10 月 19 日的新博客**；最新文章日期仍为 10 月 16 日。没有把旧文章重新计为当天发布。

## 来源覆盖与限制

通过 GitHub 连接器按 updated 排序读取两页、共 200 个 PR，覆盖到窗口起点之前；窗口候选中有 33 项新建、32 项合并，含集成和重复 PR，不能视为同数量独立功能。对重点项目核对真实创建/合并时间、目标分支、核心差异；额外读取 50 个旧 PR 的评论/评审，筛选窗口内实质讨论，并检查重点作者提交时间。

公共 curl API 曾触发限流，已改用可用的 GitHub 连接器读取，并未将失败当作零更新。本文是重要进展精选，未逐一审计全部候选的每次提交，也不穷尽所有生态仓库与 Discussions；性能数字为作者特定测试，不是本日报独立实测。当前状态与事件归属分别判断，跨日合并已明确标注。
