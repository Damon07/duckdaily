---
title: "DuckDB 日报 · 2026-10-13：多核与 Parquet 回归修复，补齐内存和查询正确性"
date: 2026-10-13 12:00:00 +0800
description: "多核、Parquet 扫描和查询规划优化进入 v2.0 开发分支，外部哈希连接漏行与内存追踪问题得到修复；Mytherin 参与的异步查询和秘密信息遮蔽方案继续推进。"
coverage_date: "2026-10-13"
---

## 覆盖窗口与核查时间

- 覆盖北京时间 **2026-10-13 00:00 至 2026-10-14 00:00**，左闭右开；对应 UTC **2026-10-12 16:00 至 2026-10-13 16:00**。
- 资料于北京时间 **2026-10-14 08:57–09:02**核查。下文事件时间均为北京时间，PR 状态是核查时状态。
- **已合并不等于已发布。** 除特别标注外，本文已合并 PR 的目标都是 `v2.0-cyanoptera` 开发分支；不代表稳定版已经包含这些改动。

## 今日速览

1. **性能回归修复集中落地。** lnkuiper 的多核优化、Parquet 元数据与预取调整，以及 guillesd 的三项扫描修复完成合并；更多多核修复仍在开放 PR 中。
2. **资源边界与结果正确性同样重要。** 外部哈希连接的 Bloom filter 漏行问题得到修复，多类大内存分配被纳入 buffer manager；影子索引检查点进入 `main`。
3. **官方没有可核实的当日新博文。** 10 月 9 日的 CLI Agent Mode 文章在窗口内补充了环境变量用法，应视为旧文更新。

## 重要 PR

### 1. Mytherin 参与推进：秘密信息遮蔽与异步查询仍需区分评审和合并

- [#26901 · Redact SECRET values in metadata, query logs and profiling output](https://github.com/duckdb/duckdb/pull/26901)，作者 **HendrikLambert**；状态 **open**。方案覆盖秘密信息的元数据展示、查询日志、预处理语句和 profiling 输出。当天作者调整了重写前保存遮蔽状态的方式，Mytherin 在 **20:11:56** [留言认可](https://github.com/duckdb/duckdb/pull/26901#issuecomment-6145252516)。这是实质评审推进，尚不能称为已修复并发布。
- [#27108 · [async results] Run a statement that expands into several as one query](https://github.com/duckdb/duckdb/pull/27108)，作者 **evertlammerts**；当天 **19:38:02** 创建，状态 **open**。拟把动态 PIVOT、部分 ALTER、IMPORT 等展开为多个内部语句的操作，放进一个提交查询和事务生命周期；Mytherin 于 **20:46:28** [批准评审](https://github.com/duckdb/duckdb/pull/27108#pullrequestreview-5503708967)。评审批准并不等于合并。
- 同一作者的前序 [#26880 · [async results] Remove planner eagerness](https://github.com/duckdb/duckdb/pull/26880) 已于当天 **00:35:48 merged**：规划器不再强制所有非普通 SELECT 的结果立即物化，由结果消费者决定如何完成。需要注意，CLI、ADBC 和 C API 的流式边界仍有明确限制，不能概括为“所有客户端已支持任意语句流式执行”。

### 2. lnkuiper：多核扩展性修复落地，后续仍在继续

[#26967 · Many-core bottleneck/regression fixes](https://github.com/duckdb/duckdb/pull/26967)，作者 **lnkuiper**，当天 **12:06:31 merged**。提交涉及物化扫描任务分配、字典哈希缓存初始化、buffer pool 记账、窗口与哈希连接中的锁竞争等，目标是修复相对 1.5 的多核瓶颈与回归。

后续 [#27142 · Many-core regressions follow-up](https://github.com/duckdb/duckdb/pull/27142) 于当天 **22:49:58** 创建，核查时仍 **open**。窗口内提交继续处理动态过滤并发读取、read-ahead 预留及不必要的 buffer 分配。这说明修复还在迭代，不能把首批合并理解为全部性能回归已经解决。

### 3. Parquet：减少重复工作，恢复并行扫描效率

- [#26905 · Reuse Parquet statistics metadata and guard initial prefetch](https://github.com/duckdb/duckdb/pull/26905)，作者 **lnkuiper**；当天 **16:58:57 merged**。复用列统计的元数据读取器，优先使用重叠预取区间中已取得的 buffer，并在合适的宽表扫描场景尝试先读过滤列。意义是减少重复 schema 构造及不必要的初始读取，并非无条件减少所有查询的 I/O。
- [#26960 · Fix three parquet scan regressions found in the DuckLake benchmarks](https://github.com/duckdb/duckdb/pull/26960)，作者 **guillesd**；当天 **17:32:03 merged**。把 row group 扫描准备移出多文件扫描全局锁、避免部分字符串的多余复制，并缩小重复 UTF-8 校验范围。作者的测试涉及 DuckLake 的远程 Parquet 场景，也适用于普通 `read_parquet`；**不涉及原生存储**。PR 明确表示部分 TPC-DS 差距仍存在，不能宣称已全面超过 1.5。

### 4. 外部执行：先保证不漏行，再处理 spill 生命周期

[#25718 · Fix external hash join dropping rows via stale Bloom filter pushdown](https://github.com/duckdb/duckdb/pull/25718)，作者 **DeviousCardi**；当天 **02:12:09 merged**。外部哈希连接分轮构建时，旧过滤器可能只覆盖首轮分区，提前过滤掉后续轮次本应匹配的行。修复在发布 Bloom filter 前覆盖完整 build-side 分区，并逐分区释放 pin，避免为修复漏行反而撑爆内存。这是结果正确性修复，值得低内存连接用户关注。

[#26929 · Fix aggregate spill transitions and source hash table cleanup](https://github.com/duckdb/duckdb/pull/26929)，作者 **lnkuiper**；当天 **03:16:41 merged**，处理聚合 spill 状态切换和源哈希表清理。作者明确说明原 issue 并未被完全解决，因此这里只报告已落地的部分。

### 5. 内存管理：让更多大分配遵守内存预算

两项均由 **h4nsmuller** 提交并在当天合并：

- [#26919 · Track large allocations in the buffer manager and drop memory that was never needed](https://github.com/duckdb/duckdb/pull/26919)，**02:41:58 merged**。把聚合、WAL、窗口、采样、CSV 等路径中的多类大分配纳入 buffer manager，并去除部分不必要的分配。实践意义是减少绕开 `memory_limit` 的资源使用，不能据此保证进程 RSS 永远等于或低于该设置。
- [#26938 · Shrink the retained JSON auto-detect buffer and allocate it through the buffer allocator](https://github.com/duckdb/duckdb/pull/26938)，**04:25:37 merged**。多文件 JSON 自动探测不再为每个小文件长期保留完整容量的 buffer，并改用受管理的分配路径，针对 `union_by_name` 扫描大量小文件的内存膨胀。

### 6. 查询规划：减少大量 DISTINCT 聚合的重复遍历

作者 **kryonix** 的 [#26965 · Evaluate each candidate pair once in greedy join ordering](https://github.com/duckdb/duckdb/pull/26965) 于 **15:48:50 merged**，[#26964 · Avoid full-plan sweeps in compressed materialization](https://github.com/duckdb/duckdb/pull/26964) 于 **18:41:19 merged**。

前者避免贪心连接排序每一步都重新评估已有候选对，后者把绑定替换限定在相关祖先路径而非反复扫整棵计划。两者共同针对大量 `count(DISTINCT)` 列画像查询的规划时间增长问题。PR 作者报告特定 200 聚合复现中组合后 EXPLAIN 从约 39 秒降至 0.84 秒；这是其指定构建和复现的测量，**不是本日报独立复测，也不是通用性能承诺**。

### 7. ART 检查点：影子索引进入 main，跨表共置尚未实现

[#23462 · Implement and use a shadow index while checkpointing](https://github.com/duckdb/duckdb/pull/23462)，作者 **sebastiaan-dev**；当天 **00:00:32 merged**，目标为 **main**，恰好落在本窗口开始后 32 秒。

检查点通过构造影子索引管理新旧 buffer，给索引块共置提供基础；本 PR 支持同一张表不同索引的共置，**不包含跨表索引共置**。立即刷盘和延后安装的模式仍有不同条件，不能把这一基础设施变化说成索引锁完全消失或已经进入稳定版。

### 8. 其他核心贡献者动向

- **Tishj**：[#26998 · [VARIANT] Disable VARIANT::JSON cast pushdown combined with extract](https://github.com/duckdb/duckdb/pull/26998)，当天 **19:05:08 merged**。在字段提取路径中阻止不安全的 JSON cast 下推，保护逻辑类型语义，避免类似字符串 `"true"` 被错误改成布尔值。字段提取本身仍可下推。
- **hawkfish**：[#26975 · Internal #11336: TIMESTAMP_TZ_NS Formatting](https://github.com/duckdb/duckdb/pull/26975)，当天 **18:08:43 merged**。公开 PR 说明修复纳秒级带时区时间戳格式化的下溢，并增加复用转换函数；未访问其引用的内部 issue。
- **pdet**：[#26927 · Keep the files a scan opens ahead within the file descriptor limit](https://github.com/duckdb/duckdb/pull/26927)，状态 **open**。窗口内新增跨扫描共享打开文件预算、统计已打开预读文件及预算满时等待 I/O 的提交，针对多小文件扫描的文件描述符耗尽。当前属于迭代中的方案，不能写成已合并修复。
- **hannes**：[#27143 · [Parquet] Backport of #23420 and #26564](https://github.com/duckdb/duckdb/pull/27143)，当天 **22:52:18** 创建，状态 **open**，目标是 **v1.5-variegata**。拟回移两项处理异常 Parquet 文件时的越界写防护；这是维护分支回移请求，不是已经发布的安全更新。

## 官方博客：没有新文，Agent Mode 旧文补充环境变量

核查 [官方新闻索引](https://duckdb.org/news/)和[官网文章源码目录](https://github.com/duckdb/duckdb-web/tree/main/_posts)，未发现覆盖日新发布的博文。可见最新文章仍是 The DuckDB team 于 **2026-10-09** 发布的 [Agent Mode in the DuckDB CLI](https://duckdb.org/2026/10/09/agent-mode)。

该旧文在当天 **16:26:22** [补充](https://github.com/duckdb/duckdb-web/commit/aee842aa305977eef35266cd3f30cbe905334365)了 `DUCKDB_AGENT_MODE` 环境变量说明，并于 **16:47:32** [继续编辑](https://github.com/duckdb/duckdb-web/commit/bf5bb30bbf200e149356d4b24bd62a61c083181a)，加入开启示例。对不能方便修改 CLI 参数的脚本，这提供了强制控制 Agent Mode 的方式。

对应 **carlopi** 的 [#26416](https://github.com/duckdb/duckdb/pull/26416) 早在 **10 月 5 日**就已合并进 `v2.0-cyanoptera`；今天是文档更新，不是功能首次合并或正式发布。

## 方向观察（推测）

- **推测：本轮重点是开发分支的性能与可靠性收敛。** 依据是多核、Parquet、规划耗时、spill 和内存追踪的多项合并，而非某一个 PR 的标题。反面证据是后续多核 PR 仍开放、作者承认部分性能差距与原 issue 尚未完全解决，所以不能推断“优化已完成”或据此猜发布日期。
- **推测：异步执行与可观测性正在共同补齐边界。** `#26880` 已合并，`#27108` 和 `#26901` 获得积极评审，表明结果消费、事务完成和诊断输出的语义都在被细化。但后两者仍开放，不能将其写成官方承诺或现有稳定功能。

## 覆盖与限制

- 从[官方 PR 列表](https://github.com/duckdb/duckdb/pulls)定位，以 GitHub API 按窗口起点后的 `updated` 检索并读完 **4 页、371 个去重候选**；该集合包含窗口结束后的后续变化，不等于“当天新增 371 个 PR”。重要条目另核对创建、合并、提交或评审的实际时间。
- 优先核查 Mytherin 的参与记录及 hannes、lnkuiper、pdet、Tishj、carlopi、hawkfish 的候选，同时保留其他作者的重要变化。纯标签、关闭重复稿和一般 CI 维护未逐项列出；不是全量 changelog。
- [RSS](https://duckdb.org/feed.xml)读取返回错误，替代域名返回 XML 内容类型不受支持，因此博客结论来自新闻索引、文章正文与公开源码交叉核查，**不能说 RSS 已确认无更新**。
- 性能数字和测试结论来自公开 PR 作者说明，本日报没有本地复测；未读取内部 issue，也未推断合并改动已经进入任何正式发行包。
