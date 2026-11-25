---
title: "DuckDB 日报 · 2026-11-24：RLE 保留字典，LIST 聚合绕开完美哈希"
date: 2026-11-24 12:00:00 +0800
description: "原生 RLE 扫描复用字典向量；增长型 LIST 聚合改用可溢写的哈希路径；显式 Parquet schema 修复嵌套映射。官网发布 SproutMe 测试案例。"
coverage_date: "2026-11-24"
---

覆盖北京时间 **11 月 24 日 00:00 至 11 月 25 日 00:00**（左闭右开），即 UTC 11 月 23 日 16:00 至 11 月 24 日 16:00。实际核查：11 月 25 日约 09:03（01:03:44 UTC）。

## 今日速览

- **原生 RLE 扫描可保留字典向量。** 作者的 SF10 TPC-DS 全套查询几何平均耗时下降约 4.8%–5.3%，但有单项回退。
- **增长型 LIST 状态在计划阶段避开完美哈希。** 另一个独立修复让可安全收窄的 FULL JOIN 赶上过滤下推。
- **显式 Parquet schema 的嵌套映射修复已合并。** 官网另有案例：SproutMe 将集成测试步骤的中位耗时从 10.65 分钟降到 0.76 分钟，生产仍用 BigQuery。

## 重要 PR

### 扫描与执行

- [#29075：原生 RLE 扫描复用字典向量](https://github.com/duckdb/duckdb/pull/29075)（lnkuiper，20:22 合并至 main）：符合容量条件时，扫描状态只物化一份运行值，批次用选择向量映射，符合条件的过滤也可复用字典上的计算结果。稀疏筛选等仍可走平坦向量。PR 的四线程 SF10 实验中，TPC-DS 全套耗时的几何平均在 ARM64 和 x86-64 分别下降 5.27% 和 4.77%；x86-64 的 TPC-H 基本不变，另有对 TPC-DS Q91 约 1.34% 回退的确认。这个改动是 DuckDB 原生存储的 RLE 路径，不是 Parquet RLE 解码优化。
- [#29175：为增长型聚合状态改选哈希算子](https://github.com/duckdb/duckdb/pull/29175)（kevintruong，02:05 合并至 main）：最终方案不是运行时迁移，而是在**计划阶段**把分组 `LIST` 等不符合条件的聚合交给可溢写的常规哈希算子。作者的 400 万行、1,000 组、64 MB 用例原先 OOM，补丁后通过；旧版禁用完美哈希也能过同一用例。这不是对单组超大可变状态的内存保证。
- [#29225：按实际行组数估计原生扫描并行度](https://github.com/duckdb/duckdb/pull/29225)（lnkuiper，01:22 合并至 main）：实际行组数给扫描可用线程数的估算兜底，小行组不再仅靠目标行组大小估算；流水线原有线程上限保留。改变的是并行度，不是过滤后行数估算。
- [#29296：避免重复复制执行参数](https://github.com/duckdb/duckdb/pull/29296)（dentiny，23:31 合并至 main）：在可复用时按引用取参数映射与值，并移除一处重复验证；绑定接口仍验证参数。作者的内存库宽表基准中，1,000 列 prepared 单行插入约快 7.3%，单参数点查约快 0.6%，不是通用 prepared 加速幅度。

### 优化器与正确性

- [#29195：先收窄 FULL JOIN，再下推过滤](https://github.com/duckdb/duckdb/pull/29195)（kevintruong，03:01 合并至 main）：符合安全条件的拒绝 NULL 谓词可在下推阶段就把 FULL JOIN 收窄，让 Parquet 有机会剪掉行组；对合并等值键的范围仍可在收窄前传给两侧。另有 [#29291](https://github.com/duckdb/duckdb/pull/29291)（lnkuiper，21:45 合并）把仅服务于 OR 过滤的相邻同键 MARK JOIN 合成一次 SEMI JOIN，为重排和下推腾出空间。
- [#29158：显式 schema 下的 LIST/MAP 映射](https://github.com/duckdb/duckdb/pull/29158)（kryonix，21:57 合并至 main）：嵌套容器的子项全取默认值时，保留源容器的结构；按名称映射列表时，不再把 Parquet 重复组的名称误当成元素能否匹配的条件。按 field ID 映射的规则不变。
- [#29211：修复普通 TIMESTAMP 的整月差值统计](https://github.com/duckdb/duckdb/pull/29211)（kevintruong，00:21 合并至 main）：闰日附近，连续日期的整月差可能在中间反向跳变，不能用两端的结果直接界定全组；补丁改用保守边界。另一个 [ICU TIMESTAMPTZ 补丁 #29253](https://github.com/duckdb/duckdb/pull/29253)（porkedchop）在本窗口提出，**北京时间 11 月 25 日 05:11** 才合并；它收紧了可声明单调的时间单位，不是同一条修复。
- [#29309：兼容 1.1.x 写出的部分 ART 内联叶节点](https://github.com/duckdb/duckdb/pull/29309)（DinosL，23:18 新建，核查时未合并）：针对特定旧索引叶节点携带不应使用的标记。作者指出该路径可能在修改索引后漏查或损坏索引；不是所有旧库文件都受影响。另见 [#29312](https://github.com/duckdb/duckdb/issues/29312)（Alan Puglisi，23:37 新建，仍开放）：报告称默认严格模式下，串行 `read_csv` 遇到文件尾部未闭合引号可能无报错地只返回前缀；同一用例并行读取报错。报告涵盖 1.5.6、2.0.0 和 2.0.1，本刊未独立复现。

### 两项 Parquet 读取进展

- [#29268：合并小远程行组的读取范围](https://github.com/duckdb/duckdb/pull/29268)（Srikanth Kandula，本日新建，仍为草案）：缓存不能服务、未测得网络开销且没有固定 gap 时，符合大小限制的小行组可跨至多 256 KiB 的**单个间隙**合并读取。作者的一个回环测试中请求数由 300 降到 150，传输却由 3.6 MB 增到 13.0 MB。不能据此推断生产延迟，也不是整文件预读。
- [#28272：Parquet VARIANT 按字段裁剪](https://github.com/duckdb/duckdb/pull/28272)（OneCyrus，仍未合并）：本日 [报告者复测](https://github.com/duckdb/duckdb/issues/29272#issuecomment-7121546796) 显示，该补丁在同机对照中改善了空对象和整行组缺键两个场景，随后关闭报告。其一个 OpenTelemetry 文件的单属性过滤从 3.29–3.47 秒降到 0.11 秒（8 线程）；这是 PR 构建的个案，不是稳定版修复或普遍提速承诺。

## 官方博客

[SproutMe 用 DuckDB 缩短集成测试](https://duckdb.org/2026/11/24/sproutme-faster-pipeline-testing)（11 月 24 日，Archit Dukhande、Geertjan Wielenga、Tim Cox）。SproutMe 在本地和 CI 用 DuckDB 运行同一个 dbt 项目，CI 用固定测试输入和预期输出来检查回归；线上仓库仍为 BigQuery。案例报告 88 次 CI/CD 运行中，每次合并的集成测试步骤中位耗时由 639 秒降到 45.6 秒。值得借鉴的是把快速反馈与生产迁移分开，数字不是两个引擎的通用性能比较。

## 方向观察（推测）

今天汇入主干的 [近似连接排序测试 #29290](https://github.com/duckdb/duckdb/pull/29290) 让同一套 SQL 测试也能覆盖贪心回退。当天提出的 [候选评估重构 #29301](https://github.com/duckdb/duckdb/pull/29301) 把代价、基数和合法性判断与枚举器分开，作者说是为 LinDP++ 做准备；它在北京时间次日 00:11 才合并，且保留现有策略。推测后续算法可以在共同的代价模型下更容易对比；这两条还没有实现 LinDP++，也不是发布承诺。

## 覆盖与限制

GitHub 分别按创建、合并与更新检索，命中 50、41、97 条 PR（集合有重叠；更新索引会随之后的活动变化），另筛查窗口内新问题。重点条目按 PR 和讨论核对时间与状态；不是所有更新都是实质进展。官网新闻列表与 Atom 均确认本日新文章。未独立运行基准、问题复现或版本回归测试；合并至 main 不等于稳定版已发布。
