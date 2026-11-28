---
title: "DuckDB 日报 · 2026-11-27：并行扫描减锁，外连接错算待回补"
date: 2026-11-27 12:00:00 +0800
description: "原生行组扫描改用原子领取任务；2.0.1 外连接聚合错算仍待维护分支修复；扩展获得同步流式表算子。"
coverage_date: "2026-11-27"
---

覆盖窗口：北京时间 2026-11-27 00:00 至 2026-11-28 00:00（左闭右开，对应 UTC 11 月 26 日 16:00 至 11 月 27 日 16:00）。实际核查：北京时间 2026-11-28 08:57:47。

## 今日速览

- **先看正确性**：DuckDB 2.0.1 的一个 LEFT JOIN + SUM 查询可返回错误结果；维护分支的补丁还未合并。
- **原生扫描换了优化方向**：按 zonemap 预先限制线程数的方案关闭，主分支改用原子计数器分发行组，线程数估算不变。
- **扩展可以边读边产出，但还不是异步 in-out**：C API V2 的流式表算子已进入 main；数据源阻塞是另一个仍开放的提案。

## 正确性与事务

- [#29463：修正空输入时的 join 统计](https://github.com/duckdb/duckdb/pull/29463) · @saeedzareian · **新建，开放，目标为 v2.0-cyanoptera**。[报告 #29456](https://github.com/duckdb/duckdb/issues/29456) 中，LEFT JOIN 右侧被过滤为空，左侧仍应保留，然而 2.0.1 错把 SUM 的比较折叠为 0，应为 1；同一复现在 1.5.6、以及 2.0.1 禁用 `statistics_propagation` 后均返回 1。两个原因是左侧统计被右子树覆盖，以及错误地用空右侧约束外连接输出上界。[#28649](https://github.com/duckdb/duckdb/pull/28649) 已在 main 处理这些机制，不能据此认为 2.0.1 已修好。维护补丁的 [AI 辅助审查](https://github.com/duckdb/duckdb/pull/29463#pullrequestreview-6086301559) 还提出 ANTI/RIGHT_ANTI 与聚合溢出测试，未在此独立复现。
- [#29216：在线建索引与并发提交](https://github.com/duckdb/duckdb/pull/29216) · @artjomPlaunov · **合并至 main**。修正建索引期间的可见性与索引列表的更新时机，避免构建漏掉期间提交的行，以及其他提交执行到一半时看到不同索引列表。作者明确说仍有后续并发边界待处理。
- [#29429：连接加入已有事务](https://github.com/duckdb/duckdb/pull/29429) 与 [#29485：扩展创建继承调用事务的连接](https://github.com/duckdb/duckdb/pull/29485) · @Robinho-MR · **均合并至 main**。前者共享整个事务而非只共享快照，最后一个参与者退出时才决定提交或回滚；后者让扩展回调在调用者事务中执行 SQL，支持语句自动提交事务，但继承连接不能结束它。
- [#29484：带 Bloom filter 的加密 Parquet](https://github.com/duckdb/duckdb/pull/29484) · @carlopi · **合并至 main**。把独立存放的 Bloom filter 与数据页的认证模块区分开，修正第一数据页可能出现的 AES 标签校验错误。parquet-mr 生成的回归样本也检查了加密 Bloom filter 的行组裁剪。

- [#29468：旧存储版本拒绝 VARIANT 中的 GEOGRAPHY](https://github.com/duckdb/duckdb/pull/29468) · @carlopi · **合并至 main**。阻止按旧版本写出包含新类型标签的文件，以免 2.0.x 无法读取；覆盖嵌套值、UPDATE 和 CTAS。

## 扫描与优化器

- [#29479：降低并行原生扫描的锁开销](https://github.com/duckdb/duckdb/pull/29479) · @lnkuiper · **合并至 main**。普通扫描从初始化的行组目录用原子索引领取任务，再照常用 zonemap 裁剪；有序扫描、显式分区、行号与并行验证保留加锁路径。补丁同时给未被更新的列加了无锁快速检查。此前 [#29329](https://github.com/duckdb/duckdb/pull/29329)（@dentiny）**关闭未合并**，Mark 提过为估算扫描线程再遍历一遍 zonemap 的额外成本。作者在热数据、192 线程 Graviton 上测得 9,766 组点查 **14.530→4.992 ms**，TPC-H Q6 SF704 **86.49→83.82 ms**；结果来自整组补丁，不是单独去锁的收益，也不是 Parquet 数据。
- [#29469：恢复固定间隔时间戳表达式的行组裁剪](https://github.com/duckdb/duckdb/pull/29469) · @carlopi · **合并至 main**。对无时区时间戳加减常量、无月份分量的 interval，在输入统计边界有限时恢复 zonemap 裁剪。原生测试断言扫描 **2/5** 个行组；跨月末的日历运算不适用，也不能从扫描组数推断基数估计变得更准。
- [#29472：合并并强化扫描过滤器](https://github.com/duckdb/duckdb/pull/29472)、[#29476：冗余 join-key 谓词改为自适应](https://github.com/duckdb/duckdb/pull/29476) · @lnkuiper · **均合并至 main**。前者让后续合格谓词穿过已经带过滤条件的扫描，并在生成最终过滤条件时消除冗余；作者的单线程热数据物化 CTE 示例扫描 **82→1** 组，耗时 **31→2 ms**。后者保留 build 侧约束，在符合条件的内等值连接中允许 probe 侧暂停低收益的重复过滤；作者的一线程弱过滤字符串案例有收益，但也记录了四线程下两个高选择性 Parquet 案例的小幅回退。
- [#29483：减少连接顺序估计中的重复工作](https://github.com/duckdb/duckdb/pull/29483) · @lnkuiper · **合并至 main**。在同一估计范围内复用等值域准备，减少重复处理谓词和子图，不改变估算公式或枚举策略。作者在此前基线的 ARM 两线程断言构建中，重复视图的 4,096 输入 **PREPARE 69.70→2.73 s**（每组两次），64 输入 **18.08→16.54 ms**（每组十二次）；不是执行提速，亦不能和 [#29426](https://github.com/duckdb/duckdb/pull/29426) 的不同基线直接相加。
- [#29489：识别完整复合唯一键](https://github.com/duckdb/duckdb/pull/29489)、[#29498：区分独立等值连接与传递等值](https://github.com/duckdb/duckdb/pull/29498)、[#29496：穿过投影等值传播表达式过滤](https://github.com/duckdb/duckdb/pull/29496) · @lnkuiper · **均合并至 main**。#29489 复用统一的唯一性分析，作者的 TPC-DS Q14 示例估计 **1,214,891→102,000**，实际 **92,954**；#29498 避免把确实独立的等值条件误当成同一条传递约束；#29496 是规划期静态传播，不代表新增了执行时过滤目标。
- [#29459：无外部缓存时尊重显式 EXACT 读取](https://github.com/duckdb/duckdb/pull/29459) · @kevintruong · **新建，开放**。针对 [#29322](https://github.com/duckdb/duckdb/issues/29322)，避免在缓存关闭且显式选 EXACT 时仍按缓存块拆读；不改 AUTO，也不是新增异步后端。作者基于 2.0.1 的独立 ARM64 原型将全扫 **79→4 次 GET**，字节与结果不变；4 个服务端槽位、每次 GET 50 ms 的条件下，扫描中位数 **1,125→258 ms**。这不是 main 补丁的独立复测。
- [#29454：每轮并行流式 LIMIT/OFFSET 仅求值一次](https://github.com/duckdb/duckdb/pull/29454) · @DinosL · **合并至 main**。独立的 [#29446：让中间算子结束时其他任务也停下](https://github.com/duckdb/duckdb/pull/29446) · **开放**；窗口内的新补丁在最后一笔在途预读结束时唤醒所有等待消费者，不再依赖某个被唤醒消费者先重新取数据。唤醒并不等于取消已提交的读。

## 扩展

- [#29493：C API V2 流式 table in-out](https://github.com/duckdb/duckdb/pull/29493) 与 [#29501：C API V2 数据源可阻塞在引擎任务上](https://github.com/duckdb/duckdb/pull/29501) · @Robinho-MR · **前者合并至 main，后者新建且开放**。流式算子可从一个输入块产生多个输出块，但没有 `BLOCKED`；数据源提案则要求空批次且至少一个 DuckDB 调度任务，之后才恢复。同步模式会内联执行任务，不能据此实现等待任意外部 I/O 完成的 in-out 算子。
- [#28403：扩展 CI 复用匹配的测试运行器](https://github.com/duckdb/duckdb/pull/28403) · @smvv · **合并至 main**。下游可用同版本、同平台的 DuckDB CLI 与 `test` 扩展运行 SQL 测试，不必重编原生 unittest 可执行文件；扩展、测试数据以及单独编译的 C++ 测试包仍须提供。

## 官方博客

核查了 [DuckDB 官方博客](https://duckdb.org/news/) 和 [Atom 源](https://duckdb.org/feed.xml)，未发现 11 月 27 日新文章。最新条目仍是 11 月 25 日的文章，不重复计入。

## 方向观察（推测）

原生扫描这次选择降低线程领取工作的成本，而不是先多做一遍统计检查来少开线程。#29479 的高线程、多行组案例支持这个选择在部分场景有效，但82 个行组的时间范围案例差异在波动内。另一条线是把扩展的输入输出协议与数据源调度拆开；目前的补丁没有给出外部 I/O 完成接口，不能把这些改动当作官方异步路线图。

## 覆盖与限制

GitHub 公开搜索返回 50 条新建、48 条合并、94 条最近更新候选（更新按半日分查，按 PR 去重；各类之间可重叠）。重点条目以 PR 原文、实际创建/合并时间和最新补丁复核；更新搜索不是完整的评论或历史事件清单。性能数字来自作者的指定版本与工作负载，未独立重跑；main 合并不等于稳定版发布。
