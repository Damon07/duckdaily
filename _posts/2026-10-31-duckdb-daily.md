---
title: "DuckDB 日报 · 2026-10-31：并发写冲突收紧，内存与 VARIANT 路径继续优化"
date: 2026-10-31 12:00:00 +0800
description: "行级写写冲突、块锁与小结果缓存优化已合并；远程读取、VARIANT 和结果正确性修复仍有多项开放提案。"
coverage_date: "2026-10-31"
---

## 覆盖时间

北京时间 **2026-10-31 00:00 至 2026-11-01 00:00**，左闭右开；对应 UTC 2026-10-30 16:00 至 2026-10-31 16:00。实际核查：**2026-11-01 08:55–09:00（北京时间）**。纳入依据为窗口内创建、合并或实质修订；下述状态和方案以核查时为准，不把窗口后的修改算作当天完成。

## 今日速览

- **并发写语义有实际变化：**同一行 DELETE/UPDATE 的冲突检测修复已合并，同一行不同列的并发 UPDATE 也会冲突，应用需准备事务重试。
- **内存与并行开销继续下降：**释放已复制列段的整块缓冲、减少重复 pin 的锁竞争、小结果缓存按需增长均已合并。
- **VARIANT 提案密集出现：**JSON 推断、宽整数编码、拆分数据上的聚合/过滤和长尾字段成本都有新方案，但均未合并。**已合并不等于已发布，维护分支上的提案也不等于稳定版已可用。**

## 已合并的重要 PR

以下六项均在本窗口合并；时间为北京时间。

- **[同一行 DELETE/UPDATE 写写冲突检测 #26676](https://github.com/duckdb/duckdb/pull/26676)** · **ywelsch** · **merged，00:46**。把更新标记纳入行版本信息，防止删除与更新交错时静默丢写。兼容性上，同一行不同列的 UPDATE 也不再允许独立并发提交；这比单纯性能修复更值得应用端检查。
- **[复制到 partial block 后释放原缓冲 #28129](https://github.com/duckdb/duckdb/pull/28129)** · **ywelsch** · **merged，01:04**。压缩段移入共享块后不再保留原来的整块 buffer，并调整 pipeline 完成时序，先释放局部状态与 pins，再允许 sink finalize。高压缩、大量小段写入可少占无效内存；没有据此认定已回补到稳定版。
- **[已 pin 块的快速路径 #27798](https://github.com/duckdb/duckdb/pull/27798)** · **ywelsch** · **merged，02:34**。利用原子读者计数减少重复 Pin/Unpin 的 block lock，并让事务 undo 头块持续 pin 到提交/回滚。重点是降低并行写入竞争；首个 pin、最后一次 unpin 等路径仍要锁，并非完全无锁。
- **[小结果 caching operators 降内存 #27996](https://github.com/duckdb/duckdb/pull/27996)** · **DinosL** · **merged，03:19**。缓存从较小容量起步、延迟分配下一块，flush 尽量引用原向量而非重建。多层连接的小结果尤其相关；缓存仍按行数而非字节数控制，大字符串复制成本并未一并解决。
- **[C API V2 聚合误去重修复 #28118](https://github.com/duckdb/duckdb/pull/28118)** · **sbrunk** · **merged，00:07**。函数名相等检查与携带函数身份的 bind data 共同区分“签名和输入相同、实际函数不同”的调用，防止两种聚合返回同一结果；同一函数的合法去重仍保留。
- **[更新 ODBC 扩展并恢复自动加载 #27860](https://github.com/duckdb/duckdb/pull/27860)** · **staticlibs** · **merged，00:27**。更新到 C API V2 版本，把 ODBC 放回 autoload 名单。移除的是已经在扩展上游实现的外部访问检查补丁，不是取消访问保护。

## 开放提案与实质进展

### 存储、执行与远程 I/O

- **[小型 transient 段可溢写 #28146](https://github.com/duckdb/duckdb/pull/28146)** · **ywelsch** · **open，本日新建**。让 validity 与嵌套列子段共享可淘汰块，并修正 validity 偏移，针对内存受限时小缓冲不能释放的问题。作者也报告无需溢写时可能增加 buffer 占用，不能只看收益。
- **[部分向量回滚清理 insert ID #28190](https://github.com/duckdb/duckdb/pull/28190)** · **fastio** · **open，本日新建**。清除已撤销行残留版本信息，避免失败追加后，后续行经 checkpoint/重启被误判消失。回归测试明确覆盖旧存储格式的索引表；“存储格式版本”不是“引擎发行版本”。
- **[远程读取按吞吐量调整分块 #28138](https://github.com/duckdb/duckdb/pull/28138)** · **pdet** · **open，本日修订**。[04:48 的实现提交](https://github.com/duckdb/duckdb/commit/e0ebe2964c7125e02de6b8e8f7b912cccc1e6ca4)把缓存基础块与网络 split 大小分开，避免大块读错误吸收已有缓存块；整体方案根据延迟和吞吐量调整 HTTP/S3 读取。机器人复审仍质疑部分请求模式下并行度不足，远程负载收益尚待验证。
- **[标量子查询避免不必要逐行展开 #28191](https://github.com/duckdb/duckdb/pull/28191)** · **fastio** · **open，本日新建**。将内部“子查询返回多行”检查标为 CONSISTENT，避免 volatile 错误函数迫使外层按行身份展开、反复计算内部聚合；多行报错语义仍需保留。
- **[范围连接基数估计 #28193](https://github.com/duckdb/duckdb/pull/28193)** · **kryonix** · **open，本日新建**。严格范围比较按约半个笛卡尔积估计，非严格比较考虑相等项，并修正 LEFT JOIN 保留侧基数下界，减少严重低估引出的差计划。这仍是启发式估计，不是所有范围连接都能更快。

### VARIANT：七项新提案，均尚未合并

以下均由 **OneCyrus** 提交，核查时均为 **open、非 draft**，目标为 **v2.0-cyanoptera**；“针对维护分支”不等于已回补。

- **输入与整数兼容性：**[JSON infer_object #28173](https://github.com/duckdb/duckdb/pull/28173)增加把推断对象读为 VARIANT 的选项，同时保留推断结构用于拆分；[UINT64 拆分 #28172](https://github.com/duckdb/duckdb/pull/28172)让可容纳的无符号整数进入 BIGINT 拆分字段，更大值保留未拆分；[宽整数 Parquet 写入 #28174](https://github.com/duckdb/duckdb/pull/28174)将超 INT64 范围但能精确容纳的整数编码为 DECIMAL(38,0)，仍超范围则报错。后两项可能改变回读类型，不能称原类型完全保真。
- **减少不必要重建：**[COUNT #28175](https://github.com/duckdb/duckdb/pull/28175)在适用拆分向量上直接读有效性位图；[FIRST/LAST/ANY_VALUE #28192](https://github.com/duckdb/duckdb/pull/28192)先判断聚合状态是否需要新值，再准备输入，不能笼统说 LAST 可跳过后续批次；[整数过滤比较键 #28194](https://github.com/duckdb/duckdb/pull/28194)从完全拆分的整数值直接生成兼容比较键，减少中间转换和逐行分配，其他输入仍回退。
- **控制长尾字段成本：**[对象字段拆分阈值 #28195](https://github.com/duckdb/duckdb/pull/28195)在存储 checkpoint 与 Parquet schema 分析中采用至少 10% 的字段出现率，稀有字段留在未拆分部分，以减少物理列和元数据膨胀。这是频率阈值，不是固定的列数上限。

### 结果正确性与安全视图边界

- **[停止依据 INT96 统计裁剪 Parquet #28180](https://github.com/duckdb/duckdb/pull/28180)** · **NUAAwqy** · **open / draft，本日新建**。对 INT96 返回未知统计，避免不可靠时间戳 min/max 导致漏行；代价是失去该类列的行组与页裁剪，原始元数据展示不变。
- **[piecewise merge join 应用两侧投影 #28189](https://github.com/duckdb/duckdb/pull/28189)** · **NUAAwqy** · **open，本日新建**。先用完整列计算连接条件，再按 projection maps 输出，修复复杂连接中的错列或内部错误。仅覆盖 range-join 路径，不包含同一 issue 的 nested-loop 部分。
- **[非 GCC/Clang 路径的 BIGINT 乘法溢出 #28159](https://github.com/duckdb/duckdb/pull/28159)** · **kryonix** · **open，本日新建**。重写手工溢出检测，避免 MSVC 等构建把越界乘积静默回绕，并允许合法的 INT64 最小值结果。平台差异是这项修复的关键。
- **[安全视图连接优化 #27924](https://github.com/duckdb/duckdb/pull/27924)** 与 **[相关 profiler 行数隐藏 #28167](https://github.com/duckdb/duckdb/pull/28167)** · **khuspsha** · **均 open**。前者本日有实质提交，后者本日新建：让连接优化穿过安全视图时，对隐藏行视图下的过滤逐行检查，避免可选过滤行为受隐藏数据影响；配套隐藏相关中间行数及汇总，减少对过滤实现细节的依赖。仍是待评审方案，不是已完成安全保证。

## 官方博客

核查[官网新闻列表](https://duckdb.org/news/)与官方域名搜索，**未发现标注 2026-10-31 发布的新文章**；列表最新日期仍为 10 月 29 日，不把旧文重列为今日更新。[RSS](https://duckdb.org/feed.xml)未能读取，限制如下。

## 方向观察（推测）

- **推测：内存优化正同时触及 buffer 生命周期、块锁和算子自身缓存。**依据是 #28129、#27798、#27996 的独立合并；但这些层次的记账方式不同，不能把某个作者测试的峰值下降外推为所有查询或 memory_limit 的保证。
- **推测：VARIANT 的后续优化更重视保留拆分表示，并约束不规则数据成本。**上述七个 PR 提供具体证据；反面限制是它们来自同一作者、全部未合并，不能据此宣布官方路线图或版本交付计划。

## 覆盖与限制

- 公开 GitHub 搜索完整返回 **75 个近期更新候选**（incomplete_results=false），另按精确窗口检索确认 **9 项合并**；按实质重要性选录，非逐条变更日志。所有入选项核对原始详情和实际补丁，旧提案另核提交/讨论时间，未把打标签或格式修改当作重大进展。
- 优先检查 Mytherin 与指定核心贡献者。相关 Mytherin 评论/评审未见落在本窗口的新内容，因此未把早前评审包装为今日消息。lnkuiper 的 #28144 窗内只有机器人评审，#28081 仅注释/格式调整，没有重复列作新实现。
- #28172、#28194 在窗口结束后仍有更新；本文以“窗口内新建”为纳入依据，概述核查时方案。开放提案的性能数字与测试结论未独立复测，故不传播通用加速倍率。
- RSS 在网页工具中因 XML 类型不受支持而失败，普通 HTTP 读取返回 403；已使用可读取的官网列表和官方域名搜索交叉检查，不能据此证明绝无遗漏。未访问任何私人仓库、内部 issue 或用户资料。
