---
title: "DuckDB 日报 · 2026-11-09：升级正确性与规划简化"
date: 2026-11-09 12:00:00 +0800
description: "旧版窗口表达式兼容、加密 Parquet 边界修复，以及 DISTINCT 规划和 BIGNUM 优化。"
coverage_date: "2026-11-09"
updated_at: 2026-11-10T09:02:00+08:00
---

覆盖时间：北京时间 2026 年 11 月 9 日 00:00 至 11 月 10 日 00:00（左闭右开），即 UTC 11 月 8 日 16:00 至 11 月 9 日 16:00。检查时间：北京时间 11 月 10 日 09:02。

## 今日重点

- 修复 v1.x 保存的 lead/lag 参数在 2.0 中丢失及 checkpoint 后被持久化错误的问题。
- BIGNUM 改用 64 位 limb，DISTINCT 规划统一到聚合；性能仍需结合实际负载评估。
- Mytherin 对类型绑定、异步文件并发和函数重载删除提出设计意见，相关方案仍在演进。

## 重要 PR

### 正确性与存储

- [#28580 修复旧版 lead/lag 参数](https://github.com/duckdb/duckdb/pull/28580)，ywelsch，**11 月 9 日 23:45 合并至 main**。修复 v1.x 保存的窗口表达式在 2.0 读取时可能静默丢失 offset/default 的问题；若先进行 checkpoint，错误参数可能被持久化。对使用旧数据库文件升级的场景尤其重要。
- [#28572 加密 Parquet 边界检查](https://github.com/duckdb/duckdb/pull/28572)，HendrikLambert，**21:03 合并**。处理加密数据短读未复制及损坏 page 长度可能导致的越界写，改善损坏输入处理。
- [#28548 CI 修复整合](https://github.com/duckdb/duckdb/pull/28548)，carlopi，**03:52 合并**。整合 Context 改动后的扩展兼容、row-id Bloom 缓冲越界、CI 内存及 Wasm triplet 等修复。该 PR 11 月 8 日新建，合并发生在本日报窗口。

### 执行与规划

- [#28497 BIGNUM 64 位 limb](https://github.com/duckdb/duckdb/pull/28497)，h4nsmuller，**19:27 合并**。内部运算改用 64 位 limb，存储格式保持不变。作者报告部分求和与转字符串基准改善，数据未独立复测，也不代表所有负载均会提速。
- [#28456 DISTINCT 规划为聚合](https://github.com/duckdb/duckdb/pull/28456)，Robinho-MR，**21:34 合并**。binder 将 DISTINCT 和 DISTINCT ON 直接规划成聚合，减少 LogicalDistinct 专用优化分支，同时保留旧计划反序列化兼容。评审中曾记录特定重写和过滤下推的性能权衡，不能简单等同于普遍加速。
- [#28579 按成本消除重复域](https://github.com/duckdb/duckdb/pull/28579)，lnkuiper，**当日新建，检查时开放**。提议只对下游连接实际需要的 key 做去重聚合，以改善去相关和聚合计划；仍需评审和负载验证。
- [#28573 聚合参数下推的异常语义](https://github.com/duckdb/duckdb/pull/28573)，h4nsmuller，**当日新建，检查时开放**。避免把可能抛错的聚合参数推进 inner join 下方，令原本会被连接过滤掉的坏值提前触发错误；同时保留对安全表达式的优化机会。
- [#28556](https://github.com/duckdb/duckdb/pull/28556)、[#28557](https://github.com/duckdb/duckdb/pull/28557)、[#28558](https://github.com/duckdb/duckdb/pull/28558)，Waterpine，**当日新建，检查时均开放**。分别探索大 TopN 批量选择、多 key radix tie bucket 及已排序 runs 合并。作者提供部分基准改善数据，均为未独立复测的提案。

### Mytherin 的设计讨论

- [#28499 类型绑定](https://github.com/duckdb/duckdb/pull/28499#discussion_r4510864340)，Robinho-MR：Mytherin 强调 resolve_types、具体类型与 bind 的结构边界，反对只为 PREPARE 元数据打补丁；作者随后[收窄改动](https://github.com/duckdb/duckdb/pull/28499#discussion_r4510950588)。聚合与窗口路径仍可能出现 UNKNOWN，不宜推广为所有绑定都已具体化。
- [#28504 异步文件并发](https://github.com/duckdb/duckdb/pull/28504#discussion_r4510986383)，Richard-Durkee：Mytherin 建议结合带宽、延迟和可配置性考虑预开文件策略，而不是只按本地或远程分类，NFS 是反例。提案仍开放。
- [#27890 删除单个函数 overload](https://github.com/duckdb/duckdb/pull/27890#discussion_r4512331798)，kryonix：Mytherin 要求从 parser 起贯通标准 ALTER 路径；同日 lnkuiper 发现并提供[并发依赖创建影响 WAL 重放的修复](https://github.com/duckdb/duckdb/pull/27890#issuecomment-6738883829)，作者确认采用。PR 仍开放，讨论不等于最终方案。
- [#28574 typed defaults](https://github.com/duckdb/duckdb/pull/28574#discussion_r4514389226)，Robinho-MR：Mytherin 当晚讨论移除 DefaultCastAs 和配置作用域。此 PR 在 **11 月 10 日 05:43** 才合并，不计入 11 月 9 日的合并。

## 官方文章

[官方博客列表](https://duckdb.org/news/)和[官网源码目录](https://github.com/duckdb/duckdb-web/tree/main/_posts)未发现标注 11 月 9 日的新文章。最新可见的 [DataGrip 案例](https://www.duckdb.org/2026/11/05/jetbrains-datagrip)发表于 11 月 5 日；外部简报在 11 月 9 日再次提及，不代表官方当天新发布。官方 feed 因读取工具不支持 XML 而未能解析。

## 方向观察

**推测：** 规划节点简化、聚合下推的异常语义和类型绑定讨论，显示贡献者既在减少特殊执行路径，也在明确优化必须保留的行为边界；旧格式及损坏输入修复则强调升级与存储正确性。开放提案可能变化，这些观察不是官方路线图。

## 覆盖与局限

公开 GitHub PR、仓库评论与评审按页读取，并以创建、合并和具体评论时间划分窗口；重点筛选不是完整代码审计。性能数据为作者报告，未独立复现。官网列表及源码目录可读，feed 未解析。除另有说明时间均为北京时间。**合并至 main 不代表稳定版已包含相关变化。**
