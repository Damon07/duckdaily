---
title: "DuckDB 日报 · 2026-11-03：Context 拆分提案、CTE 过滤下推与存储正确性"
date: 2026-11-03 12:00:00 +0800
description: "Mark 提出独立 Context 服务层；CTE 过滤、集合运算规划、Parquet 和压缩估算改进合并，多项重扫与持久化错误修复落地。"
coverage_date: "2026-11-03"
---

## 覆盖时间

北京时间 **2026-11-03 00:00 至 2026-11-04 00:00**，左闭右开；对应 UTC **2026-11-02 16:00 至 2026-11-03 16:00**。实际核查：北京时间 **2026-11-04 09:05**。以下区分窗口内进展与核查时状态；**合并到 main 不等于稳定版已发布**。

## 今日速览

- Mark 的 **Context 服务层拆分**仍为提案；连接、事务与通用服务的职责边界值得关注。
- **CTE 运行时过滤、集合运算逻辑规划、自连接改写**合并，性能优化同时加强可重复性、NULL 和基数上界保护。
- **Parquet 裁剪、DICT_FSST 估算、checkpoint 和可重入扫描**集中修正；官网发布量化桌面本地分析案例。

## 重要 PR

### 架构与查询优化

- **[Context 服务层 #28314](https://github.com/duckdb/duckdb/pull/28314)** · Mytherin（Mark Raasveldt）· **open，当日新建**。从 ClientContext 中分出配置、日志、指标、文件系统等服务，QueryContext 改为引用可选服务。让“为什么需要上下文”更明确；作者提到为跨客户端共享事务铺路，但本 PR 尚未提供该功能，也不是已确定的发布承诺。
- **[CTE 连接过滤下推 #28224](https://github.com/duckdb/duckdb/pull/28224)** · lnkuiper · **merged，窗内**。把各消费者运行时过滤以 OR 合并，推入物化 CTE，减少提前物化的数据；要求相关列覆盖全部消费者，并跳过含递归 CTE 的计划，不能泛化到所有 CTE。
- **[区分估计与上界 #28242](https://github.com/duckdb/duckdb/pull/28242)**、**[保留基数数值范围 #28243](https://github.com/duckdb/duckdb/pull/28243)** · lnkuiper · **均 merged，窗内**。前者避免把日期 range 等估计当成可用于消除 LIMIT 的保证；后者用缩放表示保护连接基数的中间乘积，避免溢出/下溢。改善优化器依据，不代表估计已精确。
- **[自连接改写为聚合 #28259](https://github.com/duckdb/duckdb/pull/28259)** · h4nsmuller · **merged，窗内**。对等值键加单条不等条件、上层只关心键集合的受限形状，改用单次扫描和 min/max 聚合，避免成对行膨胀。最终代码要求表函数可重复，并保护类型与 NULL 语义。
- **[合并 OR 范围 #28262](https://github.com/duckdb/duckdb/pull/28262)** · h4nsmuller · **merged，窗内**。合并同表达式的重叠范围，整数还能合并相邻闭区间，使过滤更直接；最终实现拒绝含常量的输入表达式，避免 INTERVAL、正负零等“比较相等但行为不同”的误改写。
- **[EXCEPT/INTERSECT 提前转连接 #28002](https://github.com/duckdb/duckdb/pull/28002)** · Robinho-MR · **merged，窗内**。在逻辑规划期构造 ANTI/SEMI join，ALL 通过分区行号匹配重复项；修复排序规则、特殊数值和易变过滤表达式相关的错误搬移或重复求值，保留旧序列化计划路径。
- **[递归调度缓存持有流水线列表 #27883](https://github.com/duckdb/duckdb/pull/27883)** · kryonix · **merged，窗内**。把固定流水线枚举移至构建阶段，减少每轮递归遍历与临时向量；动态溢写检查、线程界限和 reset 去重仍保留。

### 存储、扫描与凭据传递

- **[跳过无用 Bloom 读取 #28199](https://github.com/duckdb/duckdb/pull/28199)** · quentin-sommer；**[非字典列 folded Bloom 写入 #28038](https://github.com/duckdb/duckdb/pull/28038)** · guillesd · **均 merged，窗内**。前者让 min/max 已排除的行组不再读 Bloom；后者扩大可写 Bloom 的列范围，但受大小预算和类型限制，且增加写入成本，不是所有列或查询都受益。
- **[DICT_FSST 大小估算 #25785](https://github.com/duckdb/duckdb/pull/25785)** · krleonid · **merged，窗内**。最终实现模拟 writer 的逐块字典、编码与布局，并按部分块阈值计费，替代简单按原字符串体积打折的估计，使压缩选择更贴近实际文件。不是旧 PR 正文所述的简单“两种估算取较小值”。
- **[停用 INT96 统计裁剪 #28180](https://github.com/duckdb/duckdb/pull/28180)** · NUAAwqy；**[截断 bit-packed run 检查 #28280](https://github.com/duckdb/duckdb/pull/28280)** · jmestwa-coder · **均 merged，窗内**。前者宁可少裁剪，也不依赖缺乏可靠排序语义的 INT96 min/max 漏掉结果；后者把当前位偏移纳入长度检查，防止损坏输入越界读取，未据此推定可利用漏洞。
- **[顺序 CSV 缓冲溢写 #28230](https://github.com/duckdb/duckdb/pull/28230)** · fastio · **merged，窗内**。顺序扫描缓冲交给 buffer manager 溢写，不再销毁后 seek 重读，修复 gzip 和解码后偏移相关问题；随机访问缓冲仍可重读。
- **[checkpoint 只记录实际行的删除 #28190](https://github.com/duckdb/duckdb/pull/28190)** · fastio · **merged，窗内**。避免失败事务留下的空尾槽被持久化为删除，进而让后续追加数据在重启后消失。
- **[文件打开与 glob 携带凭据 #27799](https://github.com/duckdb/duckdb/pull/27799)** · SrikanthKandula · **merged，窗内**。最终实现保留完整 OpenFileInfo，以 secret 名称选项查找凭据并核验 scope/type，防止 schema discovery 等路径丢失选项。原正文中的新增连接/事务生命周期与缓存保障不应当作最终实现事实。

### 正确性修复与待观察方案

- **[扫描状态与绑定数据分离 #27949](https://github.com/duckdb/duckdb/pull/27949)** · kryonix · **merged，窗内**。JSON 序列化 SQL 和 Parquet metadata 扫描各自重新初始化结果/文件游标，修复递归查询过早结束、重扫错误；有副作用的语句按每次扫描重新执行，不只是回放缓存。
- **[索引绑定失败可重试 #28270](https://github.com/duckdb/duckdb/pull/28270)** · h4nsmuller · **merged，窗内**。异常后恢复 UNBOUND，避免后续写入或 checkpoint 永久等待；最终补丁还保留重试所需存储所有权，防止失败重放释放仍引用的索引块。
- **[连接重排后的列映射 #28289](https://github.com/duckdb/duckdb/pull/28289)** · fastio；**[approx_top_k 合并计数 #28292](https://github.com/duckdb/duckdb/pull/28292)** · DinosL · **均 merged，窗内**。分别保护重建 join tree 后的父节点输出布局，以及未满部分聚合状态中不存在值的零计数，避免错误列选择和 top-k 结果。
- **[跨表列段与索引块共置 #28312](https://github.com/duckdb/duckdb/pull/28312)** · sebastiaan-dev · **open，当日新建**。利用延迟 publication 和共享部分块管理减少块空间浪费；仍需观察索引重建与内存统计取舍，尚不能承诺普遍空间收益。
- **[UNNEST 列表聚合基数 #28299](https://github.com/duckdb/duckdb/pull/28299)** · kryonix · **open，当日新建**。传递列表聚合的元素数估计，避免把大量输入的列表展开估为一行；这是特定形状的估计，不是任意列表长度的保证上界。
- **[字符串聚合状态竞争 #28315](https://github.com/duckdb/duckdb/pull/28315)** · DinosL；**[并行 NDJSON 跨块尾行 #28316](https://github.com/duckdb/duckdb/pull/28316)** · Robinho-MR · **均 open，当日新建**。分别修复复用聚合行后多个线程向同一 arena 分配字符串，以及无末尾换行的跨块记录丢前缀/漏读；尚未合并。

**窗口后状态补充，不计入当日合并：**

- **[共享聚合 FILTER #28264](https://github.com/duckdb/duckdb/pull/28264)** · h4nsmuller · 当日提出，核查时 **merged，北京 11 月 4 日 07:16**。复用相同过滤的 selection，减少无参数聚合切片；易变过滤仍分开执行。
- **[jemalloc 避免 MADV_FREE 路径 #28267](https://github.com/duckdb/duckdb/pull/28267)** · wasade · 当日提出，核查时 **merged，北京 11 月 4 日 02:36**。把 muzzy_decay_ms 设为 0，以规避作者报告的部分 Linux 内核与透明大页组合下的数据丢失风险；适用性取决于具体内核，不能说所有 Linux 都受影响或现有稳定包已修复。

## 官方新博客

**[Bringing Local Analytics to the Quant's Desktop](https://github.com/duckdb/duckdb-web/blob/main/_posts/2026-11-03-bringing-local-analytics-to-the-quants-desktop.md)** · Ryan Hamilton、Geertjan Wielenga、Tim Cox · 官网标注 **2026-11-03**，已核官方仓库原文。

文章介绍 QStudio 将昂贵远程查询的结果保存为本地 Parquet，方便分析者反复探索；Pulse 用 DuckDB 做快照与缓存，PeachQ 则组合实时引擎与 DuckDB 历史存储。可借鉴之处是先把可复用中间结果留在桌面，而不必为每次分析重跑远程工作。文中性能与适用范围是受访者经验，不是统一基准或 DuckDB 官方产品承诺。

## 方向观察（推测）

1. **服务边界更明确，状态生命周期也更严格。** Context、文件打开信息和扫描状态修复都在减少隐式依赖；但跨客户端事务仍只是作者后续意向，不能据此宣布路线图。
2. **“少做工作”需要可验证的语义条件。** CTE 下推、自连接聚合和范围合并减少计算，同时显式限制消费者覆盖、可重复性和特殊值；收益必须结合计划与负载验证。
3. **存储优化与保守正确性并行。** Bloom/压缩估算争取少读少写，INT96 则主动放弃不安全裁剪。这些提交支持上述观察，不保证每项性能都上升。

## 覆盖与限制

通过公开 GitHub API 分两页检查 **163 个更新候选**，另以精确 UTC 合并窗口检索 **44 项合并**；本文按重要性精选，未把机器人标签或单纯 updated_at 当实质进展。入选项核对原始元数据与最终代码补丁，重点纠正过时 PR 正文。未独立重跑性能基准，也未穷尽所有评论和外部扩展仓库。

[官网新闻列表](https://duckdb.org/news/)可读，文章日期/作者与[官方文章源文件](https://github.com/duckdb/duckdb-web/blob/main/_posts/2026-11-03-bringing-local-analytics-to-the-quants-desktop.md)互相核对。文章网页直连不可用，已读取官方仓库全文；[RSS](https://duckdb.org/feed.xml)本次直接访问返回 403，网页读取工具亦不支持 XML，未将读取失败当作零更新。所有状态为上述核查时点快照。
