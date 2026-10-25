---
title: "DuckDB 日报 · 2026-10-24：易变表达式正确性与文件凭据隔离"
date: 2026-10-24 12:00:00 +0800
description: "IN 易变表达式修复已合并；文件级凭据、嵌套字段下推及 undo 锁竞争优化仍在提案阶段。"
coverage_date: "2026-10-24"
---

## 覆盖时间

北京时间 **2026-10-24 00:00 至 2026-10-25 00:00**（左闭右开），对应 UTC 2026-10-23 16:00 至 2026-10-24 16:00。实际核查：北京时间 **2026-10-25 09:02**。下列状态为核查时状态；“当日”按上述北京时间窗口判断，而非直接采用 GitHub 的 UTC 日期。

## 今日速览

- **正确性优先：** 易变表达式的短 IN 列表改写修复已合并；正则范围过滤、LEFT JOIN 与 EXISTS、连接重排的相关修复仍开放。
- **访问与执行边界：** 文件级凭据隔离、UNION ALL 嵌套字段下推、undo 分配锁减负均有新提案，尚不能当作稳定版能力。
- **依赖修复：** vendored Brotli 的上游解码修复移植已提出，未合并。官网与 Atom 均未见当日新博客。

## 重要 PR

### 1. 易变表达式不能被优化器重复求值

**[Evaluate a volatile IN left-hand side only once · #27758](https://github.com/duckdb/duckdb/pull/27758)**  
作者：**DinosL**；状态：**merged**。北京时间 **10 月 24 日 01:28** 合并。

短 IN 列表原本可展开成多个等值比较，复制左侧表达式；若其中包含序列等易变操作，各次比较可能拿到不同值。补丁对易变左值保留原 IN 表达式，不进行这种展开。意义是修正查询语义，而不是单纯减少计算量。Mytherin 的致谢发生在此前的北京时间 10 月 23 日，不计作本日新审查。

**[Skip the regex range filter when the regexp_full_match subject is volatile · #27807](https://github.com/duckdb/duckdb/pull/27807)**  
作者：**hsusul**；状态：**open**，当日新建。

同类问题出现在正则范围预过滤：添加上下界比较可能重复执行 subject，甚至过滤掉本应匹配的行。提案遇到易变 subject 时跳过该改写，非易变输入仍可使用优化。代码差异已核对；作者报告的测试不等于已发布修复。

### 2. 表访问路径携带独立文件凭据

**[Carry credentials on file opens and globs · #27799](https://github.com/duckdb/duckdb/pull/27799)**  
作者：**SrikanthKandula**（说明中致谢 pslawski 的设计与原型）；状态：**open**，当日新建。

同一文件经直接路径读取或经 catalog 表读取，可能应使用不同凭据。提案让文件打开和 glob 携带 FileCredentials，约束到创建它的连接、路径 scope 与事务生命周期；带此类凭据的读取不使用共享外部文件缓存及 Parquet 元数据缓存。意义是把表级授权语义传递到文件系统边界，而非仅靠全局路径匹配秘密。仍需审查与集成，不能视为现有稳定版的隔离保证。

### 3. 把嵌套字段提取推过 UNION ALL

**[Push nested field extracts through UNION ALL · #27802](https://github.com/duckdb/duckdb/pull/27802)**  
作者：**jdctinuiti**；状态：**open**，当日新建。

为各分支建立一致的提取列布局，使 STRUCT／VARIANT 的字段读取有机会继续下推到扫描，而非让完整值穿过 UNION ALL；UNION DISTINCT 和递归状态维持原处理。作者的 Parquet 对照报告读取字节减少，但这不是延迟保证，本日报未复跑基准。对半结构化数据的多源合并查询尤其值得关注。

### 4. 将 undo 块的 pin 移出分配器锁

**[Pin undo buffer blocks outside of the allocator lock · #27798](https://github.com/duckdb/duckdb/pull/27798)**  
作者：**ywelsch**；状态：**open**，当日新建。

并行 UPDATE／DELETE 的线程原本在分配器互斥锁内 pin 当前 undo 块。提案先解锁完成 pin，再重新加锁检查当前块及剩余空间后预留，减少串行区。作者在 3,000 万行、14 线程测试中报告若干语句耗时下降；这是提案作者的特定环境结果，不代表通用收益或主线已有改进。

### 5. ICU time_bucket 接受纳秒时区时间戳

**[ICU Time_Bucket Nanoseconds · #27804](https://github.com/duckdb/duckdb/pull/27804)**  
作者：**hawkfish**；状态：**open**，当日新建。

增加 TIMESTAMPTZ_NS 输入支持及测试，并处理无穷值转换。代码仍将输入按截断规则转换到已有时间桶实现，不能把“接受纳秒输入”解读为“新增纳秒宽度的桶”或“输出保留纳秒精度”。这项区别对高精度时间序列的边界行为很重要。

### 6. 两个与连接优化有关的正确性修复提案

**[Fix filters referencing projected-out IN mark columns during join ordering · #27795](https://github.com/duckdb/duckdb/pull/27795)**  
作者：**Ecthlion**；状态：**open**，当日新建。

过滤条件引用 IN 改写生成的 mark 列时，连接重排可能把条件移动到该列已被投影掉的位置，导致绑定错误。补丁要求所有引用列在目标关系边界可见才允许提取。作者指出 DuckLake 删除文件相关查询可生成这种形状；不是所有 DuckLake 查询都受影响。

**[LIMIT dropped and EXISTS returns false over a filtered LEFT JOIN onto an empty table · #27809](https://github.com/duckdb/duckdb/pull/27809)**  
作者：**RohinJoshi1**；状态：**open**，当日新建。

右表为空并不意味着 LEFT JOIN 结果为空。提案修正相关基数传播，并避免因零基数估计错误移除 LIMIT，针对 EXISTS 得到错误布尔结果的案例添加回归测试。它提醒我们统计信息不仅影响执行快慢，也可能参与会改变计划语义的规则。

### 7. 移植上游 Brotli 解码错误检查

**[Pull in upstream Brotli decoder fix · #27791](https://github.com/duckdb/duckdb/pull/27791)**  
作者：**alitrack**；状态：**open**，当日新建。

移植上游对非法 block switch 的提前拒绝与错误传播，保留 DuckDB 内嵌 Brotli 的命名空间及分配器适配。PR 将其关联到 CVE-2026-111497，并报告有效 BROTLI Parquet 的往返测试。这里确认的是修复提案及代码方向，未独立审计 CVE 的 DuckDB 可利用性，也未确认补丁已进入任何发行版；不能据此声称稳定版已经解决该问题。

## 官方博客与发行状态

核查 [官方新闻列表](https://duckdb.org/news/) 与直接读取的 [Atom feed](https://duckdb.org/feed.xml)，**未发现 2026-10-24 发布的新文章**。最新列出的文章仍是 10 月 21 日的 [DuckDB 2.0.0 LTS 发布公告](https://duckdb.org/2026/10/21/announcing-duckdb-200.html)，不重复算作本日新闻。

[GitHub releases](https://github.com/duckdb/duckdb/releases) 最新正式发行仍为 10 月 21 日发布的 v2.0.0。本日报中的后续主线合并，不代表 v2.0.0 已包含；开放 PR 更不能视为发行承诺。

## 方向观察

**推测：** #27758、#27807、#27795 与 #27809 显示，优化器正在持续补齐“易变性、列可见性、空输入与外连接”这些语义边界。依据是具体保护条件与回归测试，而非新路线图；其中只有 #27758 在报道窗口内合并。

**推测：** #27799 与 #27802 分别尝试细化授权传播和数据读取粒度，#27798 则缩小写事务中的锁范围。它们共同指向“少共享不必要的状态、少搬运不必要的数据”，但属于不同作者的独立提案，尚不足以推出官方统一架构计划。

## 覆盖与限制

- GitHub 公开 API 对更新于窗口起点之后的 **103 条候选 PR 分两页检索**，保留窗口结束后仍有更新的候选，再核对创建／合并及相关讨论时间；没有将 updated_at 或 stale-bot 活动直接当作实质进展。
- 对精选条目读取 PR 详情及主要代码差异，重点关注核心贡献者，同时保留其他作者的重要正确性与架构贡献。未对全部开放 PR 作完整代码审计，也未运行其测试或基准。
- 网页读取器不支持 Atom 的 XML 内容类型，已改为直接读取并解析 feed 成功，**本次没有遗留 RSS 缺口**。
- 本文仅使用公开资料；PR 作者测试、性能与风险判断均与本日报独立验证的状态区别标注。内部 issue 的内容不在覆盖范围。
