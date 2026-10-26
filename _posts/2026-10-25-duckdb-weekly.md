---
title: "DuckDB 周报 · 2026-10-19 至 2026-10-25：2.0 LTS 发布，执行减负与升级正确性"
date: 2026-10-25 12:00:00 +0800
description: "2.0.0 LTS 正式发布；解析、规划、内存与诊断路径持续减负，旧文件 NULL 裁剪风险和 NUMA、NUMERIC 等未完成工作值得跟踪。"
coverage_date: "2026-10-25"
permalink: /weekly/2026/10/25/
---

## 覆盖窗口与本周结论

覆盖北京时间 **2026-10-19 00:00 至 2026-10-26 00:00**，不含终点，即 UTC **10 月 18 日 16:00 至 10 月 25 日 16:00**。实际核查：北京时间 **2026-10-26 08:57–09:02**。事件归属依据创建、合并或具体讨论时间；当前状态为核查时快照。

- **正式发行是本周最重要的节点：** DuckDB 2.0.0 LTS 发布，但存储、SQL 与客户端兼容性需要逐项验证，不能把“能打开文件”当作迁移验收。
- **性能工作集中于少分配、少重复执行、少等待：** 默认块分配器、PEG 解析、相关子查询规划、预编译执行及分区写出均有合并；NUMA、超内存排序和惰性向量分配仍在提案阶段。
- **诊断与可靠性同步推进：** 实时指标、失败查询 profile、Parquet 内存核算与错误传播落地；旧文件 NULL 裁剪修复仍未合并。

**状态约定：** merged 只表示进入所注明分支；open 是未合并提案。除了单独核实的 2.0.0 正式发行，本文不将任何本周 PR 自动标为“稳定版已包含”。

## 一、2.0 LTS：新增能力与升级边界必须一起看

[官方公告：Announcing DuckDB 2.0.0 LTS “Cinnamon Teal”](https://duckdb.org/2026/10/21/announcing-duckdb-200)，日期 **10 月 21 日**；[GitHub v2.0.0 正式发行](https://github.com/duckdb/duckdb/releases/tag/v2.0.0)于北京时间 **10 月 21 日 20:49:12** 发布，非 draft、非 prerelease。核查时仍是最新正式发行，未见本周后续补丁版。

公告将 Quack／CONNECT、异步 I/O、VARIANT、默认 PEG 解析器、触发器及 CLI agent mode 列为重点，LTS 支持至少延续至 **2027 年 10 月**。这些是正式公告的产品能力，不应和下文尚在评审的 NUMERIC、NUMA 等工作混在一起。

[官方迁移指南](https://duckdb.org/docs/2.0/operations_manual/migration)值得在升级前逐项检查：

- 新建文件默认使用存储版本 69，旧版 DuckDB 不能读取；用 2.0 写入既有旧文件会保留其存储版本。这个格式保证不等于所有旧文件查询都没有回归，见下一节。
- 单箭头 lambda 默认关闭；正则运算符、整数除零、MERGE 多源行匹配同一目标等语义有变化。S3 URL 旧式配置参数默认关闭，应检查依赖它们的调用。
- Python 要求 3.11+，C++ 构建要求 C++17；C API v2 尚未稳定，扩展和客户端兼容性需分别验证。

实践上宜先用副本与代表性查询做结果对照；官方也建议关键业务考虑等待补丁发行，而不是只看版本号就原地替换。

## 二、升级正确性：旧文件 NULL 裁剪仍是未完成事项

[**#27632 · Fix NULL rows dropped by zonemap pruning on constant segments written by v1.x**](https://github.com/duckdb/duckdb/pull/27632)，作者 **franz101**，**open**，10 月 22 日新建，目标 **v2.0-cyanoptera**。

1.x 文件可能只在 validity 段记录 NULL，常量数据段却声明没有 NULL；2.0 对接受 NULL 的条件进行 zonemap 裁剪时，可能错误跳过行。提案在加载列时合并重叠 validity 段的信息。

10 月 23 日的[独立对照反馈](https://github.com/duckdb/duckdb/pull/27632#issuecomment-6356384262)使用旧版写入的 DuckLake 元数据：应返回 4,500 条的查询，在 2.0.0 及撤销该补丁的对照中返回 1,428 条，PR 构建返回 4,500 条。验证的是元数据可见性条件，**不是 PR 构建上完整 DuckLake 挂载流程的验收**，也不是所有旧文件都会出错。

[**#27684 · Backport labeled fixes to v2.0-cyanoptera**](https://github.com/duckdb/duckdb/pull/27684)，**smvv**，10 月 23 日 **merged** 到维护分支，说明一批修复已回移；但它不等于新补丁发行，也不能替仍开放的 #27632 提供发布保证。迁移验收应包含 NULL 条件、过滤后计数和关键结果集对照。

## 三、执行性能：减少计算之外的成本

### 分配、复用和数据局部性

**lnkuiper** 的 [BlockAllocator 改进 #27472](https://github.com/duckdb/duckdb/pull/27472)与[默认启用 #27520](https://github.com/duckdb/duckdb/pull/27520)于 **10 月 20 日 merged 至 main**。前者加入衰减回收和 CPU 本地复用，后者将默认路径切换到块分配器；平台与开关仍有边界，不能理解为所有构建无条件启用。

**kryonix** 的 [递归 CTE 哈希状态复用 #27461](https://github.com/duckdb/duckdb/pull/27461)同日 **merged 至 main**：减少每轮重建的工作，并处理递归增长阶段的内存预留。它不是“所有哈希状态永久复用”，Perfect Hash 仍有逐轮重建边界。

这些已合并工作之后，lnkuiper 于 **10 月 23 日**提出三个仍 **open** 的方向：

- [**#27782 · Many-core/NUMA improvements**](https://github.com/duckdb/duckdb/pull/27782)：哈希连接与聚合预取、CPU 分组局部性及共享计数器争用。
- [**#27783 · Out-of-core sort improvements**](https://github.com/duckdb/duckdb/pull/27783)：外部排序的分区、归并与缓冲管理，减少重复溢写。
- [**#27751 · Lazy Vector Allocations**](https://github.com/duckdb/duckdb/pull/27751)：首次可写访问才分配向量负载，并复用缓冲区；基准有升有降，不能预先宣布普遍提速。

另一个仍 **open** 的表示层工作是 **kryonix** 的 [ColumnDataCollection 保留常量／字典向量 #27380](https://github.com/duckdb/duckdb/pull/27380)：本周继续处理稀疏字典门槛和消费端兼容，避免中间物化一律展平；客户端结果、嵌套类型等仍有 flatten 边界，不能称为全链路零拷贝。

### 查询进入执行器之前，也有大量可省工作

**Dtenwolde** 的 PEG 系列 [#27395](https://github.com/duckdb/duckdb/pull/27395)、[#27478](https://github.com/duckdb/duckdb/pull/27478)、[#27527](https://github.com/duckdb/duckdb/pull/27527)于 **10 月 19–20 日 merged 至 main**，分别压缩匹配链、以规则 ID 减少名称查找并回收临时内存、改进统一驱动循环。作者微基准不能相加为所有 SQL 的端到端收益。

**kryonix** 的 [#27391](https://github.com/duckdb/duckdb/pull/27391)于 **10 月 19 日 merged 至 main**，为相关子查询重写中的列绑定替换建立索引并裁剪传播边界，针对宽表下的二次复杂度退化。作者的 200 列、20 个相关子查询 EXPLAIN 样例从 47.1 秒降到 0.41 秒；这是规划退化修复，不是通用执行加速倍数，仍有其他规划成本未消除。

**dentiny** 的三项合并从另一侧降低固定成本：[复用预编译计划时跳过优化器 #27506](https://github.com/duckdb/duckdb/pull/27506)（20 日）、[默认配置下跳过 disabled_optimizers 锁 #27578](https://github.com/duckdb/duckdb/pull/27578)（21 日）、[延迟初始化表达式规则 #27441](https://github.com/duckdb/duckdb/pull/27441)（23 日）。最后一项以最终代码为准，是规则集首次访问时初始化，不是所有优化器对象都变成惰性构造。

### 利用已知范围消除工作，但保留语义边界

**h4nsmuller** 的 [移除冗余排序 #27569](https://github.com/duckdb/duckdb/pull/27569)与[取模统计传播 #27595](https://github.com/duckdb/duckdb/pull/27595)于 **10 月 21 日 merged 至 main**。前者删除上层不保留的排序，分组哈希聚合不承诺保留子查询输入顺序；需要确定顺序的聚合应显式指定自身 ORDER BY。后者除了推导取模结果范围，**最终差异还把符合条件的 PERFECT_HASH_GROUP_BY 纳入 LIMITED_DISTINCT 改写**，避免更精确统计反而丢失 LIMIT 提前终止机会；不能照抄正文中“后续另做”的旧描述。

同作者的 [整数分区 COPY #27603](https://github.com/duckdb/duckdb/pull/27603)于 **10 月 22 日 merged 至 main**：满足单整数键、已知窄范围及预算等条件时使用直接分区路径，键空间上限为 256，越界有回退。它不是所有 PARTITION_BY 的统一加速。

## 四、存储与诊断：把真实成本和失败状态暴露出来

- **pdet，[#26927](https://github.com/duckdb/duckdb/pull/26927)，19 日 merged 至 main：** Parquet 扫描把正在打开和预先打开的文件一起计入预算，并参考进程文件描述符上限，降低多小文件扫描的句柄耗尽风险。这是扫描预打开启发式预算，不是整个进程绝对硬上限。
- **dentiny，[#26379](https://github.com/duckdb/duckdb/pull/26379)，19 日 merged 至 main；Robinho-MR，[#27686](https://github.com/duckdb/duckdb/pull/27686)，23 日 merged 至 main：** 分别补全外部文件缓存元数据核算，以及让 Parquet Thrift 元数据采用 arena 并进入内存预算。后者极宽表实验的峰值 RSS 反而上升，因此“核算准确”不等于“内存必然更少”。
- **artjomPlaunov，[#26153](https://github.com/duckdb/duckdb/pull/26153)，22 日 merged 至 main：** ART 插入路径继续迁移到 buffer-managed 索引，通过 handle 约束节点与子指针生命周期；这是存储基础设施推进，未据此声称整体索引提速。
- **Richard-Durkee，[实时指标 #26311](https://github.com/duckdb/duckdb/pull/26311)与[失败／中断查询 profile #26578](https://github.com/duckdb/duckdb/pull/26578)，22 日 merged 至 main：** 查询运行中可读取现有 I/O、内存计数，失败后也不再留下上一次查询的 profile。未完成 pipeline 的部分算子行数仍可能缺失，不能当作完整计量。
- **Robinho-MR，[扫描字节指标 #27682](https://github.com/duckdb/duckdb/pull/27682)，承接 AimeryCM 的 [#26774](https://github.com/duckdb/duckdb/pull/26774)，23 日 merged 至 main：** 按实际开始扫描的 Parquet 行组所选列块压缩大小计数；它衡量扫描工作量，不等于物理磁盘或网络实际读取量。

可靠性方面，**h4nsmuller** 的 [分区 COPY／连接源等待环 #27562](https://github.com/duckdb/duckdb/pull/27562)（21 日）与[窗口构建失败传播 #27596](https://github.com/duckdb/duckdb/pull/27596)（22 日）均 **merged 至 main**，处理错误或背压条件下无法结束的路径；前者不覆盖所有溢写 hash join 等待情况。**Robinho-MR** 的 [#27629](https://github.com/duckdb/duckdb/pull/27629)（23 日 merged）补强工作线程、任务错误记录和堆栈处理的分配失败路径，减少直接终止进程的情况，但仍有重试上限等边界。

## 五、Mark 的审查重点：通用表示，而非给新特性单独开一套机制

**NUMERIC 仍是开放设计。** h4nsmuller 的 [#27547](https://github.com/duckdb/duckdb/pull/27547)与替代方案 [#27567](https://github.com/duckdb/duckdb/pull/27567)均未合并。[Mytherin 在 10 月 20 日的反馈](https://github.com/duckdb/duckdb/pull/27547#issuecomment-6291731984)质疑让绑定阶段依赖精确列统计，建议保持通用类型、按运行时表示特化；[21 日进一步强调](https://github.com/duckdb/duckdb/pull/27567#issuecomment-6313922399)，逻辑类型可以不同，但应重新评估与 VARIANT 数值表示的共享。作者随后推进原生键和聚合路径，Robinho-MR 也在[22 日评审](https://github.com/duckdb/duckdb/pull/27567#issuecomment-6342609766)中质疑第二套持久化格式。作者实验取得进展不等于物理设计已经达成共识。

**敏感标记也有类似思路。** [Mytherin 在 #27407 的 19 日讨论](https://github.com/duckdb/duckdb/pull/27407#issuecomment-6261900185)建议通过类型系统携带敏感性，统一 SQL 导出、secret 和日志脱敏，而非各路径分别补机制。这是设计建议，尚非正式路线图。

与之相关但独立的 [文件凭据传递 #27799](https://github.com/duckdb/duckdb/pull/27799)，由 **SrikanthKandula** 于 **24 日**提出，说明中致谢 **pslawski** 的设计与原型，仍 **open**：让表访问路径将凭据传给打开文件和 glob，并限制连接、路径 scope 与事务生命周期；带此类凭据的读取绕过共享外部文件及 Parquet 元数据缓存。不能把它当作稳定版已有隔离保证。

## 六、周末新增提案与下周观察清单

为避免依赖尚未生成的 25 日日报，直接回查周日公开 PR：

- **alonfaraj，[#27841](https://github.com/duckdb/duckdb/pull/27841)，25 日 21:46 新建，open：** 给缓冲 CTE 消费者补上等待生产者完成的调度边，使循环检测能选择物化回退，针对流式 CTE 挂起。
- **levin-kitty，[#27844](https://github.com/duckdb/duckdb/pull/27844)，25 日 22:05 新建，open：** Linux glibc 路径按 CPU affinity 与 cgroup 限制共同确定默认线程数；SLURM 路径未改，不能泛化为全部平台。
- **alonfaraj，[#27851](https://github.com/duckdb/duckdb/pull/27851)，25 日 23:39 新建，open：** 常量与列类型不一致时放弃 zonemap 裁剪，过滤仍执行，针对正则范围过滤下推后的类型断言问题。
- **carlopi，[spatial wasm 构建 #27672](https://github.com/duckdb/duckdb/pull/27672)，23 日 merged 至 main：** 完整扩展集不再排除 wasm spatial，但配置合并不能证明对应二进制已公开分发。

继续观察 #27632 是否合并并进入补丁发行；NUMA／外部排序／惰性向量分配是否通过审查；NUMERIC 是否确定共享物理表示；实时诊断是否补齐失败 pipeline 的细粒度计数。没有把周界之后新建的 PR 算作本周成果。

## 方向观察（推测）

1. **性能优化越来越关注工作量与资源生命周期，而不只是计算内核。** 依据是块池复用、解析／规划去重、窄整数专用路径和元数据预算；反面限制是各项面向不同负载，且多核／超内存方向仍开放，不能给出统一提速幅度。
2. **2.0 发布后的工程重心包含可诊断性与兼容性收敛。** 实时指标、失败 profile、错误传播与回移支持这一判断；尚未合并的旧文件 NULL 修复说明，发行完成不等于所有迁移风险已经关闭。
3. **通用基础设施复用是一条可见的评审偏好。** Mark 对 NUMERIC／VARIANT 与敏感类型的意见提供证据，但这些是具体讨论，不能升格为已承诺的新类型或官方产品路线。

## 来源覆盖与限制

- 读取仓库 **10 月 19–24 日六篇日报**作为线索；初查时 **25 日日报不存在**，已从公开 PR 补查周日，不把日报缺失当作社区无更新。日报与本周报独立发布。
- GitHub 公开 API 按更新下界分页读取 **452 条候选、5 页、452 个唯一 PR**，搜索未标记结果不完整；再用创建、合并及评论时间筛选，剔除纯机器人更新和周界后新建项。精选条目进一步核对详情、目标分支及关键最终差异；这不是全部 PR 的逐行审计，也不穷尽所有生态仓库。
- 核查官方新闻列表、公告、迁移指南和 GitHub releases；本周新闻列表仅有上述 **10 月 21 日一篇公告**。Atom feed 读取器不支持 XML，**RSS 交叉验证未完成**；未把读取失败解释为没有新文章。
- 所有性能数字与测试反馈均注明来自作者或独立评论者，本周报未自行复跑。未访问内部 issue，不将个人 PR 当官方承诺。除正式发行外，未逐项核对提交在 v2.0.0 标签中的包含关系。
