---
title: "DuckDB 日报 · 2026-11-04：安全修复与查询执行"
date: 2026-11-04 12:00:00 +0800
description: "Linux 内存分配风险、Brotli 解码修复，以及连接估计和 Parquet 读写进展。"
coverage_date: "2026-11-04"
---

覆盖时间：北京时间 2026 年 11 月 4 日 00:00 至 11 月 5 日 00:00（左闭右开；UTC 11 月 3 日 16:00 至 11 月 4 日 16:00）。检查时间：北京时间 11 月 5 日 08:57。

## 今日重点

- Linux 特定内核与透明大页组合下的潜在静默数据丢失风险得到缓解。
- Brotli 解码器修复非法数据流处理；连接基数估计和 Parquet 读写路径均有改进。
- Sirius 加载器进入核心扩展分发，但 CUDA 后端仍是社区扩展。

## 重要 PR

### 可靠性与安全

- [#28267 Linux jemalloc MADV_FREE 缓解](https://github.com/duckdb/duckdb/pull/28267)，wasade，**11 月 4 日 02:36 合并至 main**。将内置 jemalloc 的 muzzy decay 调为 0，避免受影响的 Linux 内核和透明大页组合下的大型 MADV_FREE 调用。对相关环境中受内存压力影响的 CLI 和 Python wheel 用户值得关注；不能据此认为所有 Linux 环境均受影响。
- [#27791 修复 Brotli 非法数据流解码](https://github.com/duckdb/duckdb/pull/27791)，alitrack，**11 月 4 日 00:08 合并至 main**。移植上游修复，对非法块切换停止解码，避免继续使用过期状态。PR 将其关联到 CVE-2026-111497；此处未独立核验安全公告。[Mytherin 确认计划纳入 2.0.1](https://github.com/duckdb/duckdb/pull/27791#issuecomment-6605866568)，但这不等于版本已经发布。
- [#28310 一组面向 v2.0 回移的修复](https://github.com/duckdb/duckdb/pull/28310)，Robinho-MR，**11 月 4 日 03:00 合并至 main**。涵盖 Parquet 字符串统计与 interval 写入、NULL 聚合行为和实例清理等问题。评审指出部分提交存在回移冲突，main 合并不代表这些修复均已回移或发布。另有 [#28290](https://github.com/duckdb/duckdb/pull/28290) 于当日合并至 v2.0 分支，汇集较早的一批修复并记录例外。

### 优化与存储

- [#28193 连接顺序与基数估计调整](https://github.com/duckdb/duckdb/pull/28193)，kryonix，**11 月 4 日 05:01 合并**。调整范围比较、等值域、LEFT 连接边界和 CTE 估计，旨在减少糟糕计划及中间结果膨胀。作者报告多组查询结果一致、整体耗时接近原来，但个别查询仍有退化，不能视为普遍加速。
- [#28257 合并同一文件来源的标量聚合扫描](https://github.com/duckdb/duckdb/pull/28257)，h4nsmuller，**11 月 4 日 16:34 合并**。对同一文件或表函数来源的无关联聚合合并扫描，减少重复读取。原生表路径默认关闭，因为部分基准反而变慢。
- [#28095 合并 Parquet Bloom filter 读取](https://github.com/duckdb/duckdb/pull/28095)，guillesd，**11 月 4 日 19:09 合并**。合并相邻读取并共享缓冲区，以降低远程请求开销。作者模拟的远程测试请求数显著减少，但本地热缓存案例有退化；该测试并非真实 S3。评审还指出[内存分配粒度的后续问题](https://github.com/duckdb/duckdb/pull/28095#pullrequestreview-5737647624)。
- [#27990 Parquet 写入保留紧凑向量](https://github.com/duckdb/duckdb/pull/27990)，kryonix，**11 月 4 日 23:39 合并**。数值、字符串和时间类型的写入路径可直接处理常量及字典向量，减少展开和重复工作；部分特殊或嵌套路径仍会展开。作者的单线程测试显示特定字符串数据受益，实际收益取决于数据形态。

### 扩展与待评审提案

- [#28022 Sirius 核心扩展加载器](https://github.com/duckdb/duckdb/pull/28022)，smvv，**11 月 4 日 20:37 合并**。在受支持的 Linux 目标上提供轻量加载器，并固定到官方 Sirius 仓库；CUDA 12/13 后端仍为社区扩展，不应理解为 GPU 引擎已内置到 DuckDB。
- [#28375 简化不稳定的 v2 C API 字符串接口](https://github.com/duckdb/duckdb/pull/28375)，Maxxen，**11 月 4 日新建，目前开放**。提议移除两种包装类型，改用字符串及长度参数，涉及大量文件；这是待评审提案，不是已交付的稳定 API。
- [#28341 独立基数估计与扫描统计](https://github.com/duckdb/duckdb/pull/28341)，lnkuiper，**11 月 4 日新建，目前开放**。尝试改进扫描和过滤统计的估计方式，值得结合上述连接优化观察，但仍需评审和性能验证。
- [#28364 COPY TO 可选 fsync](https://github.com/duckdb/duckdb/pull/28364)，PeterVanHolland，**11 月 4 日新建，目前为开放草案**。针对断电或磁盘故障后的持久性，提议同步受支持的输出文件和 POSIX 目录；选项默认关闭，尚未交付。

## 官方文章

[DuckDB 官方新闻列表](https://duckdb.org/news/)未见标注 11 月 4 日的新文章。最新可见文章为 11 月 3 日的 [Bringing Local Analytics to the Quant’s Desktop](https://www.duckdb.org/2026/11/03/bringing-local-analytics-to-the-quants-desktop)，页面仅显示日期，无法核实精确发布时间及其是否落入本次北京时间窗口。

## 方向观察

**推测：** 连接估计、重复文件扫描和 Parquet 远程读取的多项合并，显示贡献者正在同时关注计划质量与实际 I/O 成本；本日的内存分配和解码修复也凸显了可靠性工作。这只是从上述具体 PR 归纳的观察，不代表官方路线图。

## 覆盖与局限

公开 PR 列表按更新时间读取两页共 200 条，已越过窗口起点；候选 PR 的创建、合并时间及重点讨论另行核对，但并非逐条完整审计全部历史事件。作者提供的性能数据未独立复现。官网新闻列表已检查；RSS 读取受限，精确博客发布时间未完全核实。所有时间为北京时间。**合并至主线或维护分支不等于已进入稳定发布版本。**
