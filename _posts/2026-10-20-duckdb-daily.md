---
title: "DuckDB 日报 · 2026-10-20：默认块分配器、递归状态复用与解析减负"
date: 2026-10-20 12:00:00 +0800
description: "BlockAllocator 默认启用，字符串排序、递归 CTE、预编译执行与目录扫描优化合并；Mark 的 NUMERIC 审查推动运行时特化方案。"
coverage_date: "2026-10-20"
---

## 覆盖时间
北京时间 **2026-10-20 00:00 至 2026-10-21 00:00**，左闭右开；对应 UTC **2026-10-19 16:00 至 2026-10-20 16:00**。实际核查：北京时间 **2026-10-21 09:01–09:03**。下文状态为核查时状态，事件归属按创建、合并或具体讨论时间判断。

## 今日速览
- **分配与复用成为主线**：默认启用 BlockAllocator，递归 CTE 避免反复重建部分哈希状态，多类算子不再分配未使用的输出缓冲区。
- **短查询与元数据访问减负**：复用预编译计划时跳过优化器，索引扫描减少空任务，系统目录过滤提前到枚举阶段。
- **Mark 的设计反馈值得关注**：NUMERIC 不宜让绑定依赖列统计；新草案转向类似 VARIANT 的通用类型与运行时特化。尚未合并，更不是产品承诺。

## 重要 PR

### 1. BlockAllocator 改进并默认启用
**作者 lnkuiper；[改进 #27472](https://github.com/duckdb/duckdb/pull/27472)、[默认启用 #27520](https://github.com/duckdb/duckdb/pull/27520) 均 merged**，分别于北京时间 10 月 20 日 03:07、20:00 合并。

先加入按时间衰减、有界后台回收，以及偏向 CPU 本地复用的大块分配缓存；随后用运行时开关 `enable_block_allocator` 取代 `block_allocator_memory`。固定块池仅适用于 64 位，MinGW 默认关闭，关闭开关不撤销已有分配或虚拟地址保留。意义是同时控制分配成本与内存留存，不能简单理解为“多缓存即更快”。#27472 作者在 c7a.metal-48xl 的指定分析负载报告了耗时与 RSS 下降，不能直接外推到所有机器。

### 2. 字符串排序减少重复比较与堆块留存
**作者 lnkuiper；[String sorting performance #27477](https://github.com/duckdb/duckdb/pull/27477)，merged**，北京时间 01:32 合并。

变长键比较跳过已经确认相同的内联前缀，外部归并更及时释放已消费的堆块。作者报告约 100 字节、共同前缀约 50 字节的键在内存内和超内存排序中约有 30% 改善；这是特定键分布的结果，不是所有 ORDER BY 的统一增益。

### 3. 递归 CTE 复用哈希状态，兼顾增长阶段的内存预留
**作者 kryonix；[Reuse hash state across recursive CTE iterations #27461](https://github.com/duckdb/duckdb/pull/27461)，merged**，北京时间 20:15 合并。

聚合分区按递归轮次真正可能使用的工作线程重新配置，保留可复用的本地连接哈希表，并回收未发布给扫描端的 Bloom filter；已经发布的过滤器不可修改。Perfect Hash 执行器仍逐轮重建，不能把这项改动概括为“所有哈希状态都复用”。当天审查还修复了递归分区增长时预留下限未同步的问题，避免低内存场景不必要地溢写；普通聚合的预留策略不在此次变更范围内。[当天修订说明](https://github.com/duckdb/duckdb/pull/27461#issuecomment-6287154840)

### 4. PEG 解析器继续压缩控制流开销
**作者 Dtenwolde；[Parser matcher driver (Parser performance 4/N) #27527](https://github.com/duckdb/duckdb/pull/27527)，merged**，当天创建、北京时间 19:30 合并。

结构匹配器从多个过程对象切换到统一驱动循环；提前排除不可能匹配的子项、折叠已知为空的尾部，并让语句内 packrat 缓存按 token 位置索引。面向扩展的单步 Resume 接口保留。作者预期大输入解析时间约减少五分之一、内存约减少四分之一；这里不作独立复现背书。

### 5. 预编译执行、索引任务和算子缓冲区减少无效工作
以下三项均在当天创建并合并：
- **dentiny，[#27506](https://github.com/duckdb/duckdb/pull/27506)，merged，14:31**：预编译计划无需重新绑定时，不再构建并运行优化器；有重新绑定子计划时仍正常优化。
- **dentiny，[#27512](https://github.com/duckdb/duckdb/pull/27512)，merged，14:27**：索引扫描并行度以实际 row-ID 批次数为上限，同时考虑事务本地行，避免点查启动大量无工作任务。
- **DinosL，[#27522](https://github.com/duckdb/duckdb/pull/27522)，merged，20:32**：Filter、Streaming Limit、Streaming Sample 与 Projection 只为真正写入的列分配缓冲区，避免仅引用输入时仍分配整份输出。

三者针对不同固定成本，收益不能相加，也不意味着 DuckDB 已转向某种新的事务处理定位。

### 6. 系统目录枚举支持提前过滤
**作者 RishiSajay；[Prune catalog/schema enumeration #27291](https://github.com/duckdb/duckdb/pull/27291)，merged**，北京时间 22:56 合并。

`duckdb_tables()` 与 `duckdb_views()` 在枚举前利用 database/schema 身份列过滤，跳过无关目录和 schema，并提供目录自定义查找入口。对远程目录尤其重要：作者的 77-schema Glue 样例由 78 次调用减少到 2 次，均值由 13.6 秒降到 0.93 秒；该数字依赖具体目录规模和网络环境。改动也修正了重新放回扫描上方的过滤器对输出列布局的映射。

### 7. 轮换 COPY 中断时的生命周期修复
**作者 h4nsmuller；[Keep the shared prepare file state alive #27560](https://github.com/duckdb/duckdb/pull/27560)，merged**，当天创建、北京时间 22:41 合并。

轮换输出文件时，若创建替代文件途中抛错，旧共享 prepare 状态可能提前销毁，而其他线程仍在使用它。修复先在锁内转移其所有权，避免异常路径中的释放后使用。这是并发写出正确性修复，而非一般性能优化。

### 8. Mark 关注 NUMERIC 的绑定边界，新方案仍为草案
**作者 h4nsmuller；[#27547](https://github.com/duckdb/duckdb/pull/27547) 与替代草案 [#27567](https://github.com/duckdb/duckdb/pull/27567)，均 open**；新草案北京时间 23:02 创建。

Mark Raasveldt（Mytherin）在北京时间 21:15 指出：若 NUMERIC 的类型选择要求绑定阶段知道列的精确范围，会模糊绑定与优化之间的边界，并引入复杂性；建议借鉴 VARIANT，让类型保持通用，遇到具体运行时表示再特化。[原始审查](https://github.com/duckdb/duckdb/pull/27547#issuecomment-6291731984)

作者随后提交 #27567，改为运行时表示与特化，依赖尚未合并的宽 DECIMAL 工作。草案自述仍有性能、超过 38 位的 SUM 累加及 Arrow 导出等限制。这里记录的是设计探索与具体审查反馈，不能视为已确定的新类型或官方路线图。

### 9. 常量／字典表示保留继续审查
**作者 kryonix；[Preserve constant and dictionary vectors in ColumnDataCollection #27380](https://github.com/duckdb/duckdb/pull/27380)，open、draft**。

当天的[修订说明](https://github.com/duckdb/duckdb/pull/27380#issuecomment-6289040270)称 MODE／quantile 窗口游标、终端表格渲染和旧 C API 结果转换开始直接读取紧凑页；WindowCursor 与 Parquet writer 仍保留部分 flatten 边界。意义是把“保留压缩表示”推进到消费端，但并非全链路零拷贝已经完成，尚未合并。

## 其他值得记下的合并
- **Tishj，[#27388](https://github.com/duckdb/duckdb/pull/27388)，merged**：`txid_current()` 改用 MetaTransaction，避免在非原生目录上错误假定 DuckTransaction 存在而触发内部异常。
- **Robinho-MR，[#27471](https://github.com/duckdb/duckdb/pull/27471)，merged**：一批正确性修复，包括 TRY 内公共子表达式不应被提取出去、函数状态初始化错误的捕获，以及 LIMIT PERCENT 基数估算。部分 BIGNUM 内容仅补测试，不能全部称为新实现。
- 扩展集成层面：**pdet 的 [DuckLake 更新 #27480](https://github.com/duckdb/duckdb/pull/27480)**、**carlopi 的 [Iceberg 更新 #27489](https://github.com/duckdb/duckdb/pull/27489)** 和 **[重新启用 Vortex #27479](https://github.com/duckdb/duckdb/pull/27479)** 均 merged。这里只确认主仓库集成变化，不把版本指针更新推定为扩展正式发布。

## 官方博客
交叉检查[官方新闻页](https://duckdb.org/news/)与 [Atom feed](https://duckdb.org/feed.xml)，**未发现覆盖窗口内发布的新文章**；两处最新文章日期均为 10 月 16 日，因此不重复充当当天新闻。

## 方向观察（推测）
- 默认块池、算子分配减量、递归状态复用及短查询任务控制共同显示：近期多项工作在削减“真正处理数据之前／之外”的成本，而不只优化计算内核。依据是多项独立合并，仍不能据此推断正式版本的统一性能提升。
- NUMERIC 审查和紧凑向量草案显示对通用表示、绑定边界及消费端兼容性的重视；两项仍在审查，最终设计与收益可能变化。
- 远程目录与扩展修复反映互操作可靠性持续推进，但集成成功不等于每个稳定版本、平台或扩展组合都可用。

## 覆盖与限制
GitHub 公开 API 按更新日期自窗口起点检索，分页读取 118 条候选，包含窗口结束后继续更新的 PR，避免因只查 updated_at 的封闭窗口而漏掉当日创建或合并项；再按具体事件筛选。重点条目核对详情、相关讨论和主要代码差异，不以更新时间单独判断实质进展。优先关注 Mytherin 与核心贡献者，同时保留其他作者的重要贡献。

这是精选日报，不是所有 PR、审查事件或 CI 的完整清单；未逐一复现性能数据，文中数字均注明为作者样例。官方 feed 的网页读取器不支持 XML，已改用直接读取 Atom 交叉确认，并非将读取失败当作无更新。所有 **merged 仅指代码合并，不代表已在稳定版发布**。
