---
title: "DuckDB 日报 · 2026-11-12：整数哈希连接、递归查询内存与扩展扫描接口"
date: 2026-11-12 12:00:00 +0800
description: "整数键哈希连接与递归 CTE 成本模型改进合入主线，扫描接口为 ORC 迁移补齐能力；同日还有远端访问边界修复和本地分析案例。"
coverage_date: "2026-11-12"
---

覆盖窗口：北京时间 2026-11-12 00:00 至 2026-11-13 00:00（不含终点），即 UTC 2026-11-11 16:00 至 2026-11-12 16:00。核查时间：北京时间 2026-11-13 09:00:56。

## 今日速览

- 整数键直接寻址进入通用哈希连接；递归 CTE 的连接排序开始显式考虑构建侧峰值内存。
- 多文件扫描可在初始化时把部分谓词交给底层剪枝；远端目录白名单与 secret 作用域边界同时收紧。
- 官网用地图和图数据应用展示如何把 DuckDB 嵌在桌面和浏览器里，而不是另设数据库服务器。

## 重点 PR

以下“已合并”指代码进入所列分支，不代表稳定版可用。

### 执行、优化与存储

- [#27620 通用整数键完美哈希连接](https://github.com/duckdb/duckdb/pull/27620) · **smvv** · 15:45 合并至 `main`。通用哈希连接可根据构建侧的实际键范围选择紧凑的直接寻址结构，条件不满足则回退。把整数键快路径用到更多连接场景，不要求每个查询都走快路径。
- [#28521 按峰值内存为递归 CTE 内的连接估算成本](https://github.com/duckdb/duckdb/pull/28521) · **kryonix**（lnkuiper 参与成本模型讨论）· 22:28 合并至 `main`。优化器估算构建侧的峰值内存，并用当前递归工作集的估计限制独立连接子树的中间结果，减少因选错连接顺序而耗尽内存的风险。
- [#28707 NUMA 感知的块分配器](https://github.com/duckdb/duckdb/pull/28707) · **lnkuiper** · 15:24 合并至 `main`。固定大小块分配复用按 NUMA 节点分片的分配器，目标是在多插槽机器上减少跨节点访问和争用。作者报告的收益来自特定硬件和查询，不是通用性能承诺。
- [#28698 修复 LATERAL 读取 CTE 的错误结果](https://github.com/duckdb/duckdb/pull/28698) · **Robinho-MR**（基于 ywelsch 的修复）· 10:25 合并至 `main`。移出独立 CTE 后不再重复去相关左侧输入，修复特定查询返回错误结果或触发循环列绑定的问题。
- [#28701 回退多匹配去重](https://github.com/duckdb/duckdb/pull/28701) · **DinosL** · 21:44 合并至 `main`。在 Mytherin、lnkuiper 参与讨论后，移除会串行化大型更新的全局去重，恢复 `UPDATE … FROM` 的原地更新路径。代价是同一目标行匹配多条源记录时可能再次被重复更新、计数或返回。

### 扩展与兼容性

- [#28647 表函数新增虚拟列、指标和统计接口](https://github.com/duckdb/duckdb/pull/28647) · **Robinho-MR** · 21:00 合并至 `main`。多文件扫描初始化时可把符合条件的单列谓词交给底层做剪枝，DuckDB 仍负责实际过滤。Mytherin 在讨论中将这些接口与 ORC 迁移关联；接口仍标为不稳定。
- [#28684 收紧远端路径与 secret 作用域边界](https://github.com/duckdb/duckdb/pull/28684) · **HendrikLambert** · 18:22 合并至 `main`。禁用外部访问时，远端路径先拒绝路径回退段，再检查白名单；以主机或桶名结尾的 secret scope 必须匹配完整名称边界。原先依赖主机或桶名部分前缀的配置需改用明确作用域，显式端口也需要匹配。
- [#28705 更新 Vortex 并启用 Windows 构建](https://github.com/duckdb/duckdb/pull/28705) · **autograaf** · 22:42 合并至 `v2.0-cyanoptera`。将 Vortex 固定到 0.92 对应的提交，Windows 构建不再一律排除，MinGW 仍除外。这是维护分支变更，并非 2.0.1 已发布。

- [#28737](https://github.com/duckdb/duckdb/pull/28737)、[#28740](https://github.com/duckdb/duckdb/pull/28740)（**ywelsch**）及 [#28739](https://github.com/duckdb/duckdb/pull/28739)（**ThijsDreef**）· 当日合并至 `main`。修复读取旧版序列化计划时的三类兼容问题：DECIMAL 的 `approx_quantile`、相关子查询中丢失字段别名的 `struct_pack`，以及外部 catalog 的 `MERGE … SET DEFAULT`。

### 仍在提案阶段

- [#27989 将大表 ALTER 的数据改写迁到物理执行算子](https://github.com/duckdb/duckdb/pull/27989) · **ywelsch** · 当日根据评审调整方案，尚未合并。目标是降低大表 `ADD COLUMN` 或 `ALTER TYPE` 时的内存和临时空间压力。Mytherin 建议收敛为一次扫描接单一算子，讨论也涉及旧 WAL 的回放兼容性。

- [#28760 将过滤下推穿过 delim join 的 CTE](https://github.com/duckdb/duckdb/pull/28760) · **Robinho-MR** · 23:23 新建，尚未合并。提案让过滤更早抵达 LATERAL 的 UNNEST 或表函数输入，针对中间结果膨胀以及 `json_valid` 保护条件失效的回归。
- [#28726 多键连接的运行时过滤](https://github.com/duckdb/duckdb/pull/28726) · **Richard-Durkee** · 07:36 新建，尚未合并。提案按连接键分别构建 Bloom 或前缀范围过滤器，让扫描有机会更早丢弃不可能匹配的行，而不只依赖 min/max。

## 官方博客

[Local Analytics Doesn’t Need a Database Server](https://duckdb.org/2026/11/12/local-analytics-without-a-database-server) · **Ilya Boyandin、Geertjan Wielenga、Tim Cox** · 官网标注 11 月 12 日，Atom 标注北京时间 08:00。文章介绍 SQLRooms 如何把 DuckDB 嵌进 React 分析工作区：Foursquare Spatial Desktop 按地图视窗在本机筛选数据并生成矢量瓦片，Cosmograph 则通过浏览器后台 worker 内的 DuckDB-Wasm 查询图数据。案例说明交互式分析不一定需要远端数据库；但若接入外部 AI 服务，仍要单独审查发送的 schema 和查询结果。

## 方向观察（推测）

[#28647](https://github.com/duckdb/duckdb/pull/28647) 与 [#28726](https://github.com/duckdb/duckdb/pull/28726) 都在尝试让扫描端更早排除不可能匹配的数据，但一个是已合并的不稳定扩展接口，另一个仍是优化器提案。两者可作为观察扫描剪枝的线索，不代表官方路线图，也不能外推通用加速比例。

## 覆盖与限制

以 [DuckDB PR](https://github.com/duckdb/duckdb/pulls) 的创建、合并和更新时间筛选候选，回查重点 PR 的详情和讨论；未将更新时间当作实质进展。GitHub 的最后更新时间会被后续活动覆盖，也不保证检出全部评论或评审。官网交叉检查 [新闻列表](https://duckdb.org/news/) 与 [Atom](https://duckdb.org/feed.xml)；[官方 Releases](https://github.com/duckdb/duckdb/releases) 未见当日发布的新稳定版。
