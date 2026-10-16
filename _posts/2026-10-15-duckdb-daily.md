---
title: "DuckDB 日报 · 2026-10-15：2.0 分支同步，聚焦数据正确性与资源边界"
date: 2026-10-15 12:00:00 +0800
description: "2.0 开发分支同步至 main；Parquet VARIANT、secret 兼容性与统计结果获修复，低内存聚合和嵌套连接继续推进。"
coverage_date: "2026-10-15"
---

覆盖窗口：北京时间 **2026-10-15 00:00 至 2026-10-16 00:00**（左闭右开），即 UTC 2026-10-14 16:00 至 2026-10-15 16:00。实际核查时间：**北京时间 2026-10-16 09:07**。以下事件时间均为北京时间；状态以核查时为准。

## 今日速览

- **2.0 开发分支同步到 main**，解析器兼容性与数值计算修复继续集中落地。这是开发代码集成，不是 2.0 稳定版发布。
- **数据正确性是主线**：VARIANT 小数写入 Parquet 的错误缩放、转型下推语义、离散分位数边界和字符串 collation 均有合并修复；旧版 HTTP secrets 的读取与显示遮蔽也得到调整。
- **资源管理仍在推进**：lnkuiper 新提低内存分组聚合修复；carlopi 的嵌套连接提案关注取消、超时和回调递归。官方博客索引未发现当日新文。

## 重要 PR

### 1. 2.0 修复批次合入，随后同步 main

[**#27256 · Merge v2.0.0 PRs (2)**](https://github.com/duckdb/duckdb/pull/27256)，作者 **Robinho-MR**，状态 **merged**：10 月 15 日 **02:33** 合入 `v2.0-cyanoptera`。

最终补丁包含 Dtenwolde、okruitho、louie-duck 等人的解析器修复：纠正比较运算后 `NOT` 的优先级，保留 `WITHIN GROUP` 与 `OVER` 组合时的排序，拒绝被意外接受的表达式和语句形式；还纳入 h4nsmuller 的中心矩算法，减少 skewness/kurtosis 使用原始幂和带来的数值误差，常量输入对应的零方差返回 NULL。

同一作者的 [**#27260 · Merge v2.0-cyanoptera into main**](https://github.com/duckdb/duckdb/pull/27260) 于 **20:35** 合入 **main**。这两项是修复集成事件，不能将其中较早编写的所有代码都算作当天新功能，也不能据此推断稳定版发布日期。

### 2. HTTP secrets：升级兼容性与展示遮蔽

[**#27257 · Fix reading secrets from older versions and redact HTTP headers in secrets**](https://github.com/duckdb/duckdb/pull/27257)，作者 **HendrikLambert**，状态 **merged**：**17:53** 合入 `v2.0-cyanoptera`。

恢复读取 1.1.0、1.1.2、1.1.3 写出的 HTTP secrets，同时将 `extra_http_headers` 纳入遮蔽字段；加载持久化 secret 时，合并当前遮蔽规则并保留原有键。对升级用户而言，既减少旧 secret 无法读取的问题，也降低凭据出现在 secret 展示结果中的风险。新增测试针对 `duckdb_secrets()` 输出，不能扩大解读为所有日志渠道都已完成修复。

### 3. Parquet VARIANT：修正小数拆列与转型快捷路径

- [**#27273 · Shred a VARIANT decimal only into a column of its scale that fits its width**](https://github.com/duckdb/duckdb/pull/27273)，作者 **PeterVanHolland**，**merged**：**19:27** → `v2.0-cyanoptera`。仅在物理类型、scale 和可容纳的 width 都匹配时拆列，否则保留原始 VARIANT 值。修复混合 scale 重写时可能把 **9.00 读成 90.0** 的问题，对 Parquet 重写、压实等流程尤其重要。
- [**#27240 · Only apply a pushed-down cast to a shredded VARIANT field when it matches the VARIANT cast**](https://github.com/duckdb/duckdb/pull/27240)，作者 **Robinho-MR**，**merged**：**19:17** → **main**。只有直接转换拆列字段与 VARIANT 转型等价时才走快捷路径；JSON、ENUM、UNION 等差异场景回退，字段提取仍可下推。最终补丁还调整后备转换为普通 cast，例如字符串 `'001'`、`'1.5'` 转 INTEGER 得到 1、2。核心价值是避免同一 SQL 因存储布局或优化路径不同而改变结果。

### 4. 查询结果一致性：分位数与 collation

- [**#27210 · Fix quantile_disc off-by-one with a DOUBLE quantile at integral n*q (FMA contraction)**](https://github.com/duckdb/duckdb/pull/27210)，作者 **h4nsmuller**，**merged**：**18:51** → **main**。修复 DOUBLE 分位参数在整数秩边界受到浮点/FMA 影响、选到相邻元素的问题，覆盖普通聚合、分组、相关子查询和列表形式；DECIMAL 分支不变。这是离散分位数修复，不是连续分位数算法更新。
- [**#27233 · Preserve collations across projection elimination and compression**](https://github.com/duckdb/duckdb/pull/27233)，作者 **kryonix**，**merged**：**13:26** → **main**。投影消除和压缩重绑定保留 collation，最终补丁也包含 EXCEPT/INTERSECT 双侧比较规则，避免 NOCASE 随计划形状变化而失效。PR 正文仍有堆叠分支说明，此处以实际合并目标和最终 diff 为准。

### 5. SQL 可检查性增强，旧式设置语法开始告警

[**#27276 · Support CREATE TABLE AS and COPY TO in EXPLAIN (SQL)**](https://github.com/duckdb/duckdb/pull/27276)，作者 **kryonix**，**merged**：**22:18** → **main**。扩展 SQL 重建到 CTAS 与 COPY TO，保留可重建的写出选项；无法忠实重建的情况明确拒绝，避免生成语义已变的 SQL。单纯 EXPLAIN 不执行建表或写出。

[**#27280 · Warn when PRAGMA name=value is used to set a setting**](https://github.com/duckdb/duckdb/pull/27280)，作者 **Robinho-MR**，**merged**：**22:39** → `v2.0-cyanoptera`。用 `PRAGMA name=value` 设置配置时记录弃用警告，引导改用 `SET`；`warnings_as_errors` 可令其成为错误。PRAGMA 函数调用及 SQLite 兼容形式不在此变更范围。当前补丁是告警，不是已经移除语法；最终代码也没有承诺具体移除版本。

### 6. 新提案：低内存聚合、嵌套连接与语法扩展共存

- [**#27298 · Fix grouped aggregation OOM at low memory limits**](https://github.com/duckdb/duckdb/pull/27298)，作者 **lnkuiper**，**21:40 新建，open，目标 main**。把初始 radix 分区、元数据和每线程余量纳入分组聚合的最低工作集预留，避免极低内存限额下反复 spill 仍然 OOM。加入 1MB/6MB、多线程与大量分组的回归测试；尚不能当作已可用修复。
- [**#27264 · Nested connections**](https://github.com/duckdb/duckdb/pull/27264)，作者 **carlopi**，**04:29 新建，open，目标 main**。内部连接关联最外层调用者，将取消信号和截止时间传递到外部资源回调，并限制回调嵌套深度为 16。**16:33 Mytherin 的评审**仍在讨论截止时间如何保存，设计尚未定稿。该 PR 混有分支历史，不能把全部文件统计当作本次功能规模。
- [**#27289 · Add functions to add, list and remove grammar extensions**](https://github.com/duckdb/duckdb/pull/27289)，作者 **Dtenwolde**，**20:21 新建，open，目标 main**。拟增加逐项启停语法扩展的函数和 active 状态列，让 CLI 激活 shell 语法时保留已启用扩展，减少整体替换配置造成的互相覆盖。

### 7. 窗口分析与纳秒时区类型：已有提案的实质推进

- [**#26502 · Internal #10721: Window Frame Analysis**](https://github.com/duckdb/duckdb/pull/26502)，作者 **hawkfish**，**open，目标 main**。**07:21 的具体提交**将 DEFERRED 唯一/主键约束排除在可推断的唯一列组合之外，避免事务中暂存的重复值让优化器错误删除排序键，或把 RANGE 窗口当成单行；随后重新请求评审。这是当天的正确性修订，并非当天新建 PR。
- [**#27191 · Internal #11413: ICU DATE_PART Nanoseconds**](https://github.com/duckdb/duckdb/pull/27191)，作者 **hawkfish**，**open，目标 main**。窗口内补充 TIMESTAMPTZ_NS 的 ICU 函数注册与测试，**16:22 获批准**。它扩展纳秒带时区输入的适用范围，但相关路径会先向负无穷取整到微秒，不能解读为 DATE_PART 全链路保留纳秒精度。

### 8. 当日新提、窗口后合并：避免提前计算未使用分支的错误

[**#27300 · Fix case simplification and constant folding issues caused by error_on_division_by_zero=true**](https://github.com/duckdb/duckdb/pull/27300)，作者 **Tishj**。**10 月 15 日 21:55 新建**；核查时为 **merged**，但合入 main 的时间是 **10 月 16 日 01:41，已在本窗口之外**。

最终代码让 CASE 简化和可选常量参数探测在求值失败时保留运行时路径，避免未使用的 CASE/COALESCE 分支因除零或转换错误提前失败；真正执行到该分支时仍报原始错误。当天应计为新提案，后续合并仅作为核查时状态补充。

## 官方博客

本窗口**未发现官方新博客**。[官方博客索引](https://duckdb.org/news/)已成功读取；最新条目仍是 DuckDB team 于 **2026-10-13** 发布的 [What Is Inside an Iceberg Table?](https://duckdb.org/2026/10/13/inside-iceberg-table.html)，不计入当天新增。`feed.xml` 抓取返回异常，不能将其表述为 RSS 已完整核验。

## 方向观察（推测）

本日的分支集成、解析器兼容性修复，以及 VARIANT、collation、统计边界的集中纠正，显示开发工作正在着重收敛 2.0 的语义与迁移风险；低内存聚合和嵌套连接则体现了对资源边界的继续打磨。**这只是从公开改动归纳的观察，不是官方路线图或发布时间承诺**。未合并提案仍可能调整，单日样本也不能代表全部开发重点。

## 覆盖与限制

- 使用公开 `duckdb/duckdb` PR 与官方博客。分页读取窗口内 updated 搜索的 **152 条**结果，另查 **54 条当日新建**和 **22 条当日合并**，并补查窗口后更新，避免仅按最后更新时间漏项；这些是检索数量，不是重要更新数量。
- 重要条目结合 PR 元数据、具体提交/评审及最终补丁筛选。纯同步、标签变化、重复或批量关闭不自动算实质进展；例如 pdet 的 #26927、Tishj 的 #26808 虽有更新时间，未核实到窗口内独立功能进展，未列作当日新功能。
- 只对入选改动做重点核查，未逐一审计全部历史讨论，也未本地运行 DuckDB 测试。文中的新增测试表示补丁包含这些用例，不代表独立验证 CI 全部通过。
- 合并到 `main` 或 `v2.0-cyanoptera` 均不等于进入稳定发行版。核查时 [GitHub 最新稳定发行条目仍为 v1.5.6](https://github.com/duckdb/duckdb/releases/tag/v1.5.6)（2026-09-28 发布）。
