---
title: "DuckDB 日报 · 2026-11-26：多文件扫描修复与连接规划提速"
date: 2026-11-26 12:00:00 +0800
description: "修复特定多文件扫描静默漏行；Parquet 精确写入 128 位整数，连接优化器扩大重排范围并减少大计划的重复工作。"
coverage_date: "2026-11-26"
---

覆盖窗口：北京时间 2026-11-26 00:00 至 2026-11-27 00:00（左闭右开；UTC 11-25 16:00 至 11-26 16:00）。实际核查：北京时间 2026-11-27 09:05 至 09:06。

## 今日速览

- **多文件扫描漏行已修复。** 跳过后一个已打开的文件时，不再误跳过前一个应读文件；这是结果正确性修复，不是性能优化。
- **128 位整数精确写入 Parquet。** 新写入使用 `DECIMAL(39,0)`；作者验证的旧稳定版仍读成近似 `DOUBLE`。
- **连接规划有两类进展。** LinDP 可处理更多连接形态，大型连接区域则减少候选枚举和计划重建中的重复工作。

## 正确性与存储

- [#29133：修复多文件扫描漏行](https://github.com/duckdb/duckdb/pull/29133)（kryonix，窗口内合入 main）。初始化阶段若有多个已打开的 reader，跳过后一个文件曾误推进全局扫描游标。已报告的触发包括 `read_parquet` 设 `maximum_files_for_stats` 并预开多个文件、以及 `read_duckdb` 的 `union_by_name`；仅打开 Parquet 的 `union_by_name` 不属于此例。回归覆盖跳过文件在列表首部、中间和末尾。另有 [#29149：修正转换列的下推过滤](https://github.com/duckdb/duckdb/pull/29149)（kryonix，合入 main），解决 `read_duckdb` 在列的类型或结构转换前错误应用谓词的问题，两者不是同一缺陷。
- [#29342：Parquet 精确写入 HUGEINT / UHUGEINT](https://github.com/duckdb/duckdb/pull/29342)（h4nsmuller，窗口内合入 main）。新写入保留两种类型的完整值，加入 min/max 统计；这些列不再写 Bloom filter，避免旧读端以 DOUBLE 的哈希误裁剪。作者验证 1.4.5、1.5.6、2.0.0、2.0.1 仍按舍入后的 DOUBLE 读取新文件，其他引擎兼容性未验证。另有 [#29388：保存 ART 索引键类型](https://github.com/duckdb/duckdb/pull/29388)（h4nsmuller，合入 main）：从 v2.1.0 存储格式起记录键类型，读时跳过类型不匹配的索引，写时拒绝继续使用它，避免漏查或唯一性约束失效。
- [#29373：保留加密页序号](https://github.com/duckdb/duckdb/pull/29373)、[#29432：修复加密页跳读和过滤](https://github.com/duckdb/duckdb/pull/29432)、[#29433：初始化过滤列 AAD](https://github.com/duckdb/duckdb/pull/29433)（alpbeysir、carlopi、alpbeysir，均窗口内合入 main）。修正跨次读页的认证序号、跳过页时的加密开销计数及 AES-GCM 过滤列认证信息，并以 parquet-rs 和 Arrow 生成的文件覆盖相关路径。[#29135：避免不必要的 Bloom I/O](https://github.com/duckdb/duckdb/pull/29135)（dentiny，合入 main）则让嵌套谓词先尊重 min/max 裁剪结论，不读取无法改变结论的 Bloom 数据。
- [#29393：避免覆盖活动 header 引用的元数据块](https://github.com/duckdb/duckdb/pull/29393)（carlopi，窗口内新建，仍开放）。针对 [#27837](https://github.com/duckdb/duckdb/issues/27837) 报告的提交触发 checkpoint 中断后数据库无法打开，提议以写时复制保留旧 header 指向的有效数据；PR 的回归专门检查 header 切换前的中断。不代表稳定版已修复。

## 优化器与执行

- [#29366：LinDP 扩展到非 INNER 连接和超边](https://github.com/duckdb/duckdb/pull/29366)、[#29357：合格 MARK JOIN 参与排序](https://github.com/duckdb/duckdb/pull/29357)（均 lnkuiper，窗口开始后合入 main）。前者增加对合格 LEFT、SEMI、ANTI 连接与多关系谓词的支持，仍受合法性约束；后者允许符合条件的非相关 MARK JOIN 参与重排，不把其 build 侧整体摊平。
- [#29384：按图邻接关系枚举贪心候选](https://github.com/duckdb/duckdb/pull/29384)、[#29415：减少大连接区域的重复扫描](https://github.com/duckdb/duckdb/pull/29415)、[#29426：减少关系集合查找及计划重建开销](https://github.com/duckdb/duckdb/pull/29426)（均 lnkuiper，窗口内合入 main）。#29384 的 1,024 输入样例候选检查由 1,046,529 次降到 3,049 次；#29426 在 #29415 基础上将作者的 4,096 输入热 PREPARE 从 7.94 秒降至 5.36 秒，但 65 输入的选择性外部连接对照慢了约 4–6%。这些数字不是普通查询的通用收益。
- [#29267：在连接排序前推导分组等值键](https://github.com/duckdb/duckdb/pull/29267)（kevintruong，合入 main）。排名在不同组重复时，原先缺少的分组等值条件现在可通过投影显露，避免跨组配对。作者样例首个连接的实际输出从 1,164,800 行降到 20,800 行，两处排名连接的估算未变；性能表的基线是此前 PR 版本，不是发布版。
- [#28081：普通哈希连接按批量选择探测内核](https://github.com/duckdb/duckdb/pull/28081)（gropaul，合入 main）。大批次初次探测走无分支路径，小批次（至多 32 行）及键匹配失败后的重试走分支路径。作者约 50% 命中率的 SF10 特定连接在 M4 Pro、EPYC 上分别为 1.27×、1.12×；[SF100 全套跟测](https://github.com/duckdb/duckdb/pull/28081#issuecomment-7189910336)总体持平。
- [#28809：按分组键取 Top-N 时提前收紧聚合输入](https://github.com/duckdb/duckdb/pull/28809)（h4nsmuller，合入 main）。动态边界淘汰不可能进入前 N 的键，同时保留候选组的全部行；作者内存样例 `GROUP BY user_id ORDER BY user_id LIMIT 10` 为 226→10 ms（8 线程、两次取最佳），标准套件整体影响较小。
- [#29424：回移小型运行时过滤生产者调度](https://github.com/duckdb/duckdb/pull/29424)（DinosL，窗口内合入 **v2.0-cyanoptera**，未确认进入正式发行版）。补丁与 [#28768](https://github.com/duckdb/duckdb/pull/28768) 一致，改善已有目标扫描等待过滤器的时机，不扩展目标发现。

## 文件系统与在审提案

- [#29377：将外部缓存移到绑定上下文的打开路径](https://github.com/duckdb/duckdb/pull/29377)、[#29423：拆分 FileSystem 与 BaseFileSystem](https://github.com/duckdb/duckdb/pull/29423)（均 Robinho-MR，窗口内合入 main）。区分调用者使用的上下文绑定接口与可扩展的后端基类；缓存仍保存解压前字节。后端位置读仍是同步接口，没有新增原生异步后端。
- [#29429：连接加入共享事务](https://github.com/duckdb/duckdb/pull/29429)（Robinho-MR，窗口内新建、仍开放）。共享的是同一事务及其未提交写入，而不只是快照；最后一个参与者退出时才结束事务，任一回滚会使整体回滚。作者单独提交的 [#29418](https://github.com/duckdb/duckdb/pull/29418) 已合入 main，保留 ALTER 前的本地存储供仍在使用的对象，不等于共享事务上线。
- [#29437：嵌套 PREPARE 的统计重绑定](https://github.com/duckdb/duckdb/pull/29437)（carlopi，窗口内新建、仍开放）处理 C API 包装 SQL PREPARE 后可能保留过期统计并返回旧计数。[#29446：流水线结束时通知其他线程](https://github.com/duckdb/duckdb/pull/29446)（DinosL，窗口内新建、仍开放）针对并行流式 LIMIT 达标后仍有线程继续扫描的问题；已阻塞读取须先恢复以传递预读唤醒。
- [#29413：保留基数估算及独立上界](https://github.com/duckdb/duckdb/pull/29413)（lnkuiper，窗口内新建，**下一北京时间日**才合入 main）。连接规划中保留分数估算并独立传递结构性最大行数；不要把统计点估算当作可证明的上界。

## 官方博客

[官方新闻页](https://duckdb.org/news/)与 [Atom](https://duckdb.org/feed.xml) 均未发现 11 月 26 日新稿；最近一篇仍是 11 月 25 日的 [I Don’t Want a Lesson in Computer Science!](https://duckdb.org/2026/11/25/star-trek-queries-duckdb)，已在前一日覆盖。

## 方向观察（推测）

连接优化这批改动分成两件事：一是让更多合法计划进入搜索，二是降低大计划的搜索成本。#29366 与 #29384、#29415、#29426 分别提供证据；但 65 输入对照的回退说明不能用一个超大计划的收益推断普遍提速。多文件路径则适合把**裁剪前后的结果正确性**与**实际读了哪些文件、哪些字节**分开验证；#29133 与 #29135 展示了这两个问题为什么不能混为一谈。这是对当日变动的解读，不是官方路线图。

## 覆盖与限制

GitHub 时间窗检索返回 55 条新建、59 条合并、106 条按最近更新时间筛选的 PR（分段去重，类别可重叠），再按原始 PR 的事件时间和分支筛选。更新列表不能还原之后又更新过的全部讨论。性能数据均为作者或评审公布的指定样例，未独立运行；合入 main 或维护分支不代表已随稳定版发布。
