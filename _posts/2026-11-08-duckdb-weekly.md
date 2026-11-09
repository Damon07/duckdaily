---
title: "DuckDB 周报 · 2026-11-02—2026-11-08：执行边界与存储正确性"
date: 2026-11-08 12:00:00 +0800
description: "Context 重构、计划复用、递归 CTE 与存储正确性进展，以及仍需关注的统计问题。"
coverage_date: "2026-11-08"
permalink: /weekly/2026/11/08/
---

覆盖范围：北京时间 2026 年 11 月 2 日周一 00:00 至 11 月 9 日周一 00:00，不含终点；对应 UTC 11 月 1 日 16:00 至 11 月 8 日 16:00。检查时间：北京时间 11 月 9 日 09:08。

本周工作的共同主题是拆分执行服务边界、减少重复计算，并加强优化所依赖的统计和语义约束。性能收益与额外内存、I/O 或个别查询退化需要一起看。合并到主线或维护分支不等于已发布。

## 架构与复用：从服务边界到语义契约

- [#28314 Context 服务抽象](https://github.com/duckdb/duckdb/pull/28314)，Mytherin，11 月 5 日合并至 main。将设置、日志、指标和文件系统等服务从 ClientContext 的多重职责中拆分，为后续跨客户端共享事务做准备；本次并未实现共享事务。[#28417](https://github.com/duckdb/duckdb/pull/28417)，Robinho-MR，11 月 6 日合并，继续迁移调用方。
- [#28324 表函数稳定性契约](https://github.com/duckdb/duckdb/pull/28324)，kryonix，11 月 6 日合并。公共子计划等复用依据稳定性决定是否共享，避免独立调用被错误合并。现有 C API 注册仍按 volatile 处理；不能认为稳定性设置接口已向该 API 开放。
- [#28375 v2 C API 字符串接口](https://github.com/duckdb/duckdb/pull/28375)，Maxxen，11 月 6 日合并：移除两种包装类型，使用字符串与长度参数。这是尚不稳定的 v2 API。
- [#28204 短语句锁竞争](https://github.com/duckdb/duckdb/pull/28204)，dentiny，11 月 2 日合并三类锁路径优化。Mytherin 要求考虑生产环境开启日志的场景；同作者后续 [#28337](https://github.com/duckdb/duckdb/pull/28337) 已于 11 月 4 日合并，覆盖日志开启与关闭，而不是仍在等待。
- [#28257 同源标量聚合共享扫描](https://github.com/duckdb/duckdb/pull/28257)，h4nsmuller，11 月 4 日合并，配合此前 [#28264](https://github.com/duckdb/duckdb/pull/28264) 复用聚合过滤工作。文件来源可减少重复扫描，但原生表默认不启用该改写，因为过滤成本可能超过节省的扫描成本。[Mytherin 的评审](https://github.com/duckdb/duckdb/pull/28257#issuecomment-6581258343)强调每组唯一过滤条件与输入只应过滤和切片一次。

## 计划质量、Parquet 与存储效率

- [#28193 连接选择率和基数](https://github.com/duckdb/duckdb/pull/28193)，kryonix，11 月 4 日合并；[#28341 独立基数估计](https://github.com/duckdb/duckdb/pull/28341)，lnkuiper，11 月 5 日合并。二者调整连接和过滤估计、统计传播；整体改善与个别查询退化并存。[#28362](https://github.com/duckdb/duckdb/pull/28362)，DinosL，同日合并至 **v2.0-cyanoptera**，保留原始连接顺序作为候选，并非合并至 main。
- [#28095 合并 Parquet Bloom filter 读取](https://github.com/duckdb/duckdb/pull/28095)，guillesd，11 月 4 日合并，减少远程请求；作者实验为模拟环境，本地热缓存有退化。[#27990](https://github.com/duckdb/duckdb/pull/27990)，kryonix，同日合并，减少 Parquet 写入时对常量及字典向量的展开。
- [#28373 多文件 footer 统计](https://github.com/duckdb/duckdb/pull/28373)，Robinho-MR，11 月 5 日合并。可为有限数量的文件提供合并统计，但默认关闭且启用会增加 footer I/O。[#28530](https://github.com/duckdb/duckdb/pull/28530)，SrikanthKandula，11 月 8 日新建、检查时开放，处理指定 schema 时列统计被忽略的问题。
- [#28312 跨表打包列段和索引](https://github.com/duckdb/duckdb/pull/28312)，sebastiaan-dev，11 月 6 日合并，可改善块空间利用；持久化 ART 内存计入 BASE_TABLE 是统计分类上的取舍。

## 递归执行：性能与内存共同权衡

[#27883](https://github.com/duckdb/duckdb/pull/27883) 缓存递归流水线列表、[#28368](https://github.com/duckdb/duckdb/pull/28368) 修复特定无 worker 调度条件下的等待，均由 kryonix 提交并于本周合并。[#28078](https://github.com/duckdb/duckdb/pull/28078) 11 月 7 日合并，在提交时物化 USING KEY 的 finalize 结果，减少重复计算与锁；作者同时报告某些负载内存增加。后续 [#28520](https://github.com/duckdb/duckdb/pull/28520) 和 [#28521](https://github.com/duckdb/duckdb/pull/28521) 仍开放，分别针对物化副本及连接顺序造成的中间结果膨胀。

## 正确性、安全与未完成事项

- [#28274 WAL 轮转](https://github.com/duckdb/duckdb/pull/28274)，maazq4808-pixel，11 月 5 日合并：强制 checkpoint 开始时即使 WAL 为空也轮转，修复并发提交导致重启失败的风险。PR 指出删除 WAL 会丢失已提交行。
- [#28355 旧版文件 NULL 过滤](https://github.com/duckdb/duckdb/pull/28355)，PeterVanHolland，11 月 5 日合并：避免 DuckDB 2.0 在特定过滤下错误裁剪 v1.x 文件中的行。[#28267](https://github.com/duckdb/duckdb/pull/28267)，wasade，11 月 4 日合并，缓解特定 Linux 内核和透明大页组合下的内存分配风险；并非所有 Linux 环境受影响。
- [#27791 Brotli 非法流解码](https://github.com/duckdb/duckdb/pull/27791)，alitrack，11 月 4 日合并上游修复。[#28419](https://github.com/duckdb/duckdb/pull/28419)，Robinho-MR，11 月 6 日合并，修复 read-ahead 异步任务的 heap-use-after-free。
- **列表统计仍需跟踪：**[#28408](https://github.com/duckdb/duckdb/pull/28408)，Robinho-MR，11 月 6 日合并，但嵌套列表统计的最后修复未进入 squash；[#28467](https://github.com/duckdb/duckdb/pull/28467) 检查时仍开放，相关错误可能影响结果。
- **压缩读取的后续状态已变化：**[#28406](https://github.com/duckdb/duckdb/pull/28406) 合并后出现密集读取退化；[#28465](https://github.com/duckdb/duckdb/pull/28465) 仍为开放草案。早期 UPDATE 正确性问题已经修复并获[复核](https://github.com/duckdb/duckdb/pull/28465#discussion_r4497584756)，不能沿用日报中的旧状态；部分选择密度仍有性能权衡。
- [#28290](https://github.com/duckdb/duckdb/pull/28290) 和 [#28396](https://github.com/duckdb/duckdb/pull/28396)，Robinho-MR，本周合并至 v2.0-cyanoptera，均列有未回移或调整的项目，不代表所有主线修复均已进入维护分支。

## 扩展与外部资源

[#28022](https://github.com/duckdb/duckdb/pull/28022)，smvv，11 月 4 日合并的是受支持 Linux 目标上的 Sirius 轻量加载器；CUDA 后端仍为社区扩展。carlopi 的 [#28383](https://github.com/duckdb/duckdb/pull/28383) 和 [#28399](https://github.com/duckdb/duckdb/pull/28399) 本周合并，改善外部资源查询与提供扩展加载；后续 [#28522](https://github.com/duckdb/duckdb/pull/28522)、[#28525](https://github.com/duckdb/duckdb/pull/28525)、[#28529](https://github.com/duckdb/duckdb/pull/28529) 的类型发现、provider 信息和批量注册仍开放。

## 官方博客与发布

- 11 月 3 日：[Bringing Local Analytics to the Quant’s Desktop](https://duckdb.org/2026/11/03/bringing-local-analytics-to-the-quants-desktop)。介绍 QStudio 将远程查询结果保存为本地 Parquet 以便重复分析，以及 Pulse、PeachQ 的本地分析用途。这是采用案例，不是新版本公告。
- 11 月 5 日：[How JetBrains Built Cross-Database Queries into DataGrip with DuckDB](https://www.duckdb.org/2026/11/05/jetbrains-datagrip)。DataGrip 嵌入 DuckDB 并通过自定义表函数跨数据库连接查询；更广泛的优化与文件数据源仍是未来方向。
- 官方发布记录显示本周没有新的 DuckDB 核心正式版；最新为 10 月 21 日发布的 [v2.0.0](https://github.com/duckdb/duckdb/releases/tag/v2.0.0)。[官方日历](https://duckdb.org/release_calendar)暂列 2.0.1 于 11 月 18 日，日期可能变化。

## 方向观察

**推测：** Context 重构和稳定性契约反映贡献者在让执行服务与复用边界更明确；统计、扫描合并和 Parquet I/O 工作则试图减少不必要的数据处理。列表统计后续修复与性能退化提醒我们，优化能力扩展必须同时验证正确性和不同负载的成本。这是对具体 PR 的归纳，不是官方路线图。

## 来源与局限

以 11 月 2–7 日日报为线索，并补查 11 月 8 日公开 PR；独立核对重点 PR、事件时间、目标分支和评审。本周合并搜索返回 203 项，包含回移与批量工作，未逐项做完整代码审计。性能数据来自作者或评审，未独立复现。官方博客列表、正文及发布记录已核对；RSS 因 XML 格式未能通过网页工具解析。11 月 9 日才发生的合并不计入本周。
