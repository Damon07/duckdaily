---
title: "DuckDB 日报 · 2026-11-01：点更新、Parquet 裁剪与正确性修复提案"
date: 2026-11-01 12:00:00 +0800
description: "短语句锁竞争、稀疏 UPDATE 与 Parquet 过滤优化进入评审；ART、Arrow 和事务布局变更修复继续推进。本文选录均为未合并提案。"
coverage_date: "2026-11-01"
---

## 覆盖时间

北京时间 **2026-11-01 00:00 至 2026-11-02 00:00**（左闭右开），对应 UTC **2026-10-31 16:00 至 2026-11-01 16:00**。实际核查：北京时间 **2026-11-02 09:01–09:02**。状态取核查时；个别窗口之后的变化另行注明。

## 今日速览

- 短语句与点更新优化出现新方案：减少每条语句的全局锁访问，稀疏 UPDATE 只取命中行的基础值。
- Parquet 提案把统计裁剪放在 Bloom filter 读取之前；VARIANT 则继续优化缺字段提取、整数比较键和 shredding 边界。
- ART 的 AND/IN/NULL 语义、Arrow 空值与临时视图、DELETE 后 ALTER 再建索引的事务提交，均有针对性修复提案。**下列 16 项均未合并，不代表稳定版已经修复。**独立窗口合并检索未返回合并 PR。

## 重要 PR

### 执行与存储性能

- **[#28204 · Remove four global locks from the per-statement path](https://github.com/duckdb/duckdb/pull/28204)** — **dentiny**；当天新建，**open**。为关闭日志的常见路径增加无锁快捷处理，缓存扩展设置索引，并调整回调注册表和线程池重启标志，降低多连接短查询的同步开销。作者基准集中在短 prepared 语句，不能据此推断一般分析查询也有同等收益；MinGW 的部分设置查找仍保留锁。
- **[#28206 · Only fetch the updated rows' base values in UPDATE](https://github.com/duckdb/duckdb/pull/28206)** — **dentiny**；当天新建，**open**。稀疏更新只读取待更新行的基础值，避免解压整个向量，同时处理空值和字符串堆生命周期；超过标准向量大小四分之一的更新仍走整向量路径。对压缩字符串点更新尤其有意义，作者的收益并非所有类型和批量都一致。
- **[#28199 · Skip Bloom filter reads for row groups already ruled out by min max](https://github.com/duckdb/duckdb/pull/28199)** — **quentin-sommer**；当天新建，**open**。先完成各过滤条件的行组统计裁剪，再注册读取；已被统计或较早 Bloom filter 排除的行组，不再读取后续 Bloom filters。目标是减少远程 Parquet 的无效请求，仍存活的行组继续使用 Bloom filter。

### 结果正确性与接口兼容

- **[#28197 · Intersect ART index scan keys across AND conjuncts](https://github.com/duckdb/duckdb/pull/28197)** — **NUAAwqy**；当天新建，**open / draft**。将同列 AND 子条件产生的 ART 候选键取交集，而不是合并为并集，防止 `IN (..., NULL)` 的约束被丢掉后返回错误行。候选交集为空时保守回退，并增加索引扫描和结果回归测试。
- **[#28205 · Use the latest altered storage when removing deleted rows from indexes](https://github.com/duckdb/duckdb/pull/28205)** — **fastio**；当天新建，**open**。同一事务先 DELETE、再 ALTER TABLE、再对新布局建索引时，提交阶段可能从旧布局读取索引列。提案记录存储替换链，删除索引条目时使用最新布局，覆盖增删列、类型变化与回滚等情形。
- **[#28203 · Fix Arrow import of a fixed_size_binary child of a NULL struct](https://github.com/duckdb/duckdb/pull/28203)** — **NUAAwqy**；当天新建，**open / draft**。移除固定长度二进制子列转换时重复设置有效位图的操作，保留从父 STRUCT 继承的 NULL，避免把占位字节当真实值。作者验证的是导入；问题报告中的 Parquet 往返移位未由新增测试覆盖，不能一并宣称解决。
- **[#28201 · Create temporary view for Arrow scan](https://github.com/duckdb/duckdb/pull/28201)** — **arnoldwakim**；当天新建，**open**。让 `duckdb_arrow_scan()` 真正创建临时、连接局部的视图，避免文件数据库提交时尝试将进程内 Arrow 绑定数据序列化到 WAL。API 签名不变，行为与已有文档对齐。
- **[#28198 · Use registered JSON casts for custom types in JSON and VARIANT](https://github.com/duckdb/duckdb/pull/28198)** — **chiranjeevi-max**；当天新建，**open**。让 JSON 构造、COPY JSON 及 VARIANT 转换尊重扩展自定义类型注册的精确 JSON cast，递归处理嵌套值，避免把物理编码直接输出为逻辑值。没有自定义 JSON cast 的类型保留原行为。

### VARIANT：继续迭代，尚无落地承诺

- **[#28209 · Emit constant NULL for shredded VARIANT extract of a missing key](https://github.com/duckdb/duckdb/pull/28209)** — **OneCyrus**；当天新建，**open**。对完全 shredded 且类型里不存在的键直接返回常量 NULL，避免整向量反 shredding。部分 shredded、数组或不支持的路径仍回退，不能泛化为所有缺键访问。
- **[#28194 · Speed up filtering on shredded integer Parquet VARIANTs](https://github.com/duckdb/duckdb/pull/28194)** — **OneCyrus**；旧提案当天有[实质提交](https://github.com/duckdb/duckdb/commit/fe7c512fa0406c36cd320ca514db55d88801d719)，**open**。从完全 shredded 的整数 typed values 构建比较键，避开通用 VARIANT 遍历和中间十进制字符串。仍然生成编码比较键，并非直接执行整数谓词；部分 shredded 数据继续走通用路径。
- **[#28172 · Shred UINT64 values in the Parquet VARIANT encoding](https://github.com/duckdb/duckdb/pull/28172)** — **OneCyrus**；当天[补齐本地存储侧路径](https://github.com/duckdb/duckdb/commit/62d63db7695c424543cfc70046b9bf393e5197ab)，**open**。将可表示为 INT64 的 UINT64 映射扩展至 read-time shredding 和 compaction，而不只处理 Parquet 写入。超过 INT64_MAX 的值仍留在 overlay，符合范围的值读回可能成为 INT64；不是对所有无符号整数宽度的通用支持。
- **[#28195 · Bound which VARIANT object fields are shredded](https://github.com/duckdb/duckdb/pull/28195)** — **OneCyrus**；当天[提交](https://github.com/duckdb/duckdb/commit/2de4ca2d34dcc3cbb905114393910177015d8a59)引入最多 32 字段并将出现率门槛降为 1%，**open**。目的是控制宽稀疏对象的列膨胀，未选字段保留 overlay。**窗口之后**，北京时间 11 月 2 日 01:19 的[后续提交](https://github.com/duckdb/duckdb/commit/d7a1cfc7d3ed41bdecb7911efedb0b3c3776612b)又取消出现率门槛，只选最常见的 32 字段；这才是核查时版本，不能混作当天已定方案。

### 扩展、CLI 与依赖修复

- **[#28208 · Add statement hooks and isLastStatement to client context](https://github.com/duckdb/duckdb/pull/28208)** — **ThijsDreef**；当天新建，**open**。为一个查询展开出的内部语句提供开始/结束回调与“是否最后一条”的查询接口，区分 query 和 statement 生命周期，并在语句失败时传递错误。方便扩展状态管理，仍是拟议接口。
- **[#27616 · Support CREATE FUNCTION ... LANGUAGE](https://github.com/duckdb/duckdb/pull/27616)** — **kryonix**；旧架构提案当天[加固 ValidateCreate 的签名保护](https://github.com/duckdb/duckdb/commit/cffa989b07ccab499ecab67ffd6affd72c753b61)，**open**。通过回调前后的序列化类型身份比较，拒绝扩展经共享元数据改变已解析签名，补上仅靠 const 视图无法阻止的修改路径。整体方案仍拟复用宏目录持久化语言函数；并非当天新增或已发布的语言支持。
- **[#27876 · CLI background color query](https://github.com/duckdb/duckdb/pull/27876)** — **KassaSana**；当天根据反馈更新并重新请求评审，**open**。TERM 缺失、为空或不支持时跳过背景色探测，`-version` 提前退出，避免不必要的约五秒等待。宣称 xterm 但不响应的 PTY 仍可能等待，不能写成所有终端停顿均修好。
- **[#27791 · Pull in upstream Brotli decoder fix](https://github.com/duckdb/duckdb/pull/27791)** — **alitrack**；当天作者报告重基后的验证结果，**open**。补丁更早识别无效 block switch，区分格式错误和需要更多输入，并传播解码错误。本次独立核实对应 [CI run 41215013377](https://github.com/duckdb/duckdb/actions/runs/41215013377) 已成功；这是提案验证进展，不是 DuckDB 已发布该依赖修复。

## 官方博客

[官网新闻列表](https://duckdb.org/news/)和官方域名搜索未发现发布日期为 **2026-11-01** 的新文章；列表最新仍是 10 月 29 日的文章，不重复作为今日新文。[RSS](https://duckdb.org/feed.xml) 未成功读取，见覆盖限制。

## 方向观察（推测）

1. **短查询固定成本正成为一条可见的优化线索。** #28204 与 #28206 分别减少锁和无效解码，#28199 减少无效 I/O；它们针对不同瓶颈，不能把作者的局部基准相加或推广为整体性能提升。
2. **复杂类型快路径必须伴随语义边界校验。** ART 的 NULL/AND、Arrow 父子有效位图、自定义 JSON cast 和 VARIANT overlay 都说明，绕过通用处理需要保留完整语义。VARIANT 字段策略在覆盖窗口后仍变化，恰好说明设计尚未定型。
3. 上述是从公开提案归纳的观察，**不是官方路线图**。本日未发现值得单列的 Mytherin 新建或合并 PR；核心作者优先检查不等于只收录核心作者。

## 覆盖与限制

- GitHub 公开 API 检索从窗口起点更新至核查时的 **33 个候选 PR**，返回未截断；逐项按创建、提交或讨论时间筛选，另做精确窗口合并检索，结果为 0。窗口之后新建的 PR、纯机器人 stale/草稿状态变化及机械整理未列入重点。
- 选录 16 项的当前补丁均已核对，旧项另核提交或讨论时间。PR 状态为核查时快照，不保证随后不变；作者的本地性能与测试报告并非本日报独立复现。未把“open”写成已修复，更未将未来合并等同稳定版发布。
- RSS 网页读取不支持 XML，直接 HTTP 请求返回 403，因此博客判断依据官网列表及官方域名搜索；不能据 RSS 失败断言没有更新。搜索索引也可能滞后，本报不是仓库逐条变更审计。
