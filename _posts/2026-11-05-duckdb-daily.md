---
title: "DuckDB 日报 · 2026-11-05：可靠性与 Context 重构"
date: 2026-11-05 12:00:00 +0800
description: "WAL 与旧版数据库文件正确性修复、Context 架构调整，以及查询优化和 DataGrip 集成。"
coverage_date: "2026-11-05"
---

覆盖时间：北京时间 2026 年 11 月 5 日 00:00 至 11 月 6 日 00:00（左闭右开），即 UTC 11 月 4 日 16:00 至 11 月 5 日 16:00。检查时间：北京时间 11 月 6 日 09:07。

## 今日重点

- WAL 检查点与旧版文件 NULL 过滤的正确性问题得到修复。
- Mytherin 的 Context 重构已合并，为后续跨客户端共享事务做准备，但共享事务本身尚未实现。
- Parquet 统计、基数估计和递归 CTE 调度有重要进展；官方介绍了 DataGrip 跨数据库查询的集成案例。

## 重要 PR

### 正确性与可靠性

- [#28274 修复强制检查点时的 WAL 轮转](https://github.com/duckdb/duckdb/pull/28274)，maazq4808-pixel，**11 月 5 日 22:00 合并至 main**。强制检查点开始时即使 WAL 为空也执行轮转，避免并发提交造成 WAL 与数据库头的迭代号不一致、重启失败。PR 描述指出，删除 WAL 的恢复办法会丢失已提交行；新增回归测试检查重启后的数据。
- [#28355 修复旧版文件中 NULL 行被错误跳过](https://github.com/duckdb/duckdb/pull/28355)，PeterVanHolland，**11 月 5 日 04:04 合并至 main**。DuckDB 2.0 在读取 v1.x 文件时，某些接受 NULL 的过滤条件可能错误裁剪数据段，静默遗漏行，包括影响 DuckLake catalog 的情况。修复采用更保守的 NULL 可能性标记，换取正确结果。
- [#28368 修复特定调度条件下递归 CTE 无法中断](https://github.com/duckdb/duckdb/pull/28368)，kryonix，**11 月 5 日 21:26 合并**。没有内部 worker 且递归执行需要普通调度器继续运行时，内联等待可能死锁，包括 threads=1 的情况。修复会处理待执行任务并检查中断和超时；并非所有递归 CTE 都受影响。
- [#28346 改进 fsum 与 favg 精度](https://github.com/duckdb/duckdb/pull/28346)，alonfaraj，**11 月 5 日 00:28 合并**。修正补偿求和及最终校正，改善抵消场景下的数值结果，并覆盖分组、并行和窗口场景。溢出时也避免因校正而错误得到 NaN。

### 架构与查询优化

- [#28314 引入 Context 抽象](https://github.com/duckdb/duckdb/pull/28314)，Mytherin，**11 月 5 日 06:14 合并**。将设置、日志、指标、文件系统等服务从 ClientContext 中拆分，为后续客户端间共享事务做准备。当前合并的是基础重构，不是共享事务功能本身。后续 [#28417](https://github.com/duckdb/duckdb/pull/28417)，Robinho-MR，于当日新建，继续迁移调用方，目前开放。
- [#28373 可选的多文件 Parquet 统计](https://github.com/duckdb/duckdb/pull/28373)，Robinho-MR，**11 月 5 日 05:51 合并**。在文件数满足配置条件时，并行读取 footer，向优化器提供行数与合并统计。maximum_files_for_stats 默认关闭；启用会增加 footer I/O，不是所有查询都自动受益。
- [#28341 独立基数估计和统计传播](https://github.com/duckdb/duckdb/pull/28341)，lnkuiper，**11 月 5 日 16:41 合并**。让基数估计不依赖连接枚举，并改进扫描、过滤及选定连接的统计传播。作者在[讨论](https://github.com/duckdb/duckdb/pull/28341#issuecomment-6638205590)中接受了平均改善与个别查询退化并存的权衡，不能概括为全面加速。
- [#28362 将输入连接顺序保留为候选计划](https://github.com/duckdb/duckdb/pull/28362)，DinosL，**11 月 5 日 19:42 合并**。在贪心方案之外保留原始连接顺序作为候选，降低优化器错过该方案的风险。

### 值得关注的开放提案

- [#28324 表函数稳定性与公共子计划复用](https://github.com/duckdb/duckdb/pull/28324)，kryonix，**仍开放**。11 月 5 日 Mytherin 参与讨论稳定性契约；作者随后报告实现：内置表函数默认在查询内一致，有副作用或可变状态的函数需显式退出，现有 C API 注册仍按 volatile 处理以保持兼容。提案尚未合并。
- [#28364 COPY TO 可选 fsync](https://github.com/duckdb/duckdb/pull/28364)，PeterVanHolland，**仍开放**。提案面向断电或崩溃后的持久性；评审提出重新打开文件权限及替换清理风险后，作者调整为同步原始句柄并保护已有目标。部分平台和完整测试尚未全部验证，功能未发布。
- [#27567 高精度 NUMERIC 类型](https://github.com/duckdb/duckdb/pull/27567)，h4nsmuller，**仍开放**。提议支持最高 255 位的精确数值及运行时特化。11 月 5 日[评审](https://github.com/duckdb/duckdb/pull/27567#pullrequestreview-5784896129)指出 Vortex 外部构建仍有类型兼容问题；Arrow 导出和部分聚合也存在列明的限制。

[回移批次 #28396](https://github.com/duckdb/duckdb/pull/28396) 于 11 月 5 日新建，收录 #28355、#28346 等修复；它在 11 月 6 日才合并至维护分支，超出本日报窗口。维护分支合并同样不等于稳定版已经发布。

## 官方文章

[How JetBrains Built Cross-Database Queries into DataGrip with DuckDB](https://duckdb.org/2026/11/05/jetbrains-datagrip.html)，Ilia Epelbaum、Geertjan Wielenga、Tim Cox，官方标注 **2026 年 11 月 5 日**。文章介绍 DataGrip 如何嵌入 DuckDB，借助自定义表函数和 DuckDB SQL 跨数据库连接查询数据，省去自行构建查询引擎。文件数据源和更广泛的优化用途属于未来方向，而非文章确认已交付的功能。这是一篇集成案例，不是 DuckDB 版本发布公告。官方 feed 时间为 UTC 00:00，可能是按日期归一化的时间，不能确定实际发布时刻。

## 方向观察

**推测：** Context 拆分、表函数稳定性契约和统计传播的工作，显示贡献者正同时改善执行服务边界与优化器使用信息的方式；WAL 和旧格式修复则反映数据正确性仍是重要工作。开放提案可能改变或不被合并，单个 PR 不能代表官方路线图。

## 覆盖与局限

使用公开 GitHub 搜索分别核对窗口内新建和合并的 PR，并查看重点 PR 与讨论；新建与合并类别可能重叠，未逐条审计所有更新的历史事件。性能结论依赖 PR 作者及评审，未独立复现。官方新闻列表与 feed 已检查；文章正文从官方 feed 核对，文章页面本身未能通过网页工具打开。所有时间为北京时间。**合并至 main 或维护分支不等于稳定版已包含这些变化。**
