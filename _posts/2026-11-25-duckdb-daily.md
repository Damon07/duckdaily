---
title: "DuckDB 日报 · 2026-11-25：LinDP 进入连接排序，行组剪枝修复错结果"
date: 2026-11-25 12:00:00 +0800
description: "受限的内连接线性化动态规划合入主干；原生行组统计与扫描线程的两个提案进入讨论；Parquet 页裁剪及文件枚举有新进展。"
coverage_date: "2026-11-25"
---

覆盖北京时间 **11 月 25 日 00:00 至 11 月 26 日 00:00**（左闭右开），即 UTC 11 月 24 日 16:00 至 11 月 25 日 16:00。实际核查：11 月 26 日 09:01:40 北京（01:01:40 UTC）。

## 今日速览

- **近似连接排序引入 LinDP**：精确枚举回退时，普通连通内连接可在受限空间内比较树状计划。
- **行组统计有两条不同的优化线**：一条减少计划阶段可见行计数，另一条尝试限制执行线程。并列极值导致的 Top-N 错结果修复已合并，另两种情况仍待修。
- **远程 Parquet 不能只看读了多少字节**：文件枚举现在可以把元数据交给读取器以省去部分 HEAD；另有全扫报告，同样的字节数却产生 4 对 79 次 GET。

## 重要 PR

### 连接排序和原生扫描

- [#29355：近似内连接排序使用线性化 DP](https://github.com/duckdb/duckdb/pull/29355)（lnkuiper，21:59 合并至 main）：在精确枚举回退时，用生成树构造候选线性顺序，再对其中的连续区间做动态规划，可以探索一部分分支型连接树。它沿用现有基数、代价和合法性判断，不是对全部候选树做穷举。配套的[候选评估重构 #29301](https://github.com/duckdb/duckdb/pull/29301)（lnkuiper）于 00:11 合并。[#29366](https://github.com/duckdb/duckdb/pull/29366) 扩展到非内连接和超边，[#29357](https://github.com/duckdb/duckdb/pull/29357) 让合格的 MARK JOIN 参与排序；两条均由 lnkuiper 在本日提出，分别在北京时间 **11 月 26 日 00:06、00:09** 才合并。
- [#29326：只对未被 zonemap 排除的行组数可见行](https://github.com/duckdb/duckdb/pull/29326)（dentiny，开放）：这是 [#28793](https://github.com/duckdb/duckdb/pull/28793) 的**计划阶段基数上界**后续。先查各组是否可能匹配，再对剩下的组按当前可见性精确计数，目标是不改变上界。作者在 1,000 万行、无 checkpoint、执行 1 万次点删除后，测到 prepared 点查由约 4.9 ms 降至 118 µs；未删除时基线约 96 µs。
- [#29329：用未剪掉的行组数限制扫描线程](https://github.com/duckdb/duckdb/pull/29329)（dentiny，开放）：这是**执行初始化**，不是基数估计。作者的 18 线程排序时间戳窄范围测试由 300.0 µs 降至 244.9 µs。[Mark Raasveldt](https://github.com/duckdb/duckdb/pull/29329#issuecomment-7161527875) 质疑为估算线程额外遍历一遍 zonemap；[Laurens Kuiper 的评审草案](https://github.com/duckdb/duckdb/pull/29329#issuecomment-7165852259) 改为初始化行组目录，由工作线程用原子索引领取并并行剪枝。后者仍是讨论中的替代方案，不能把原版基准归给它。
- [#29337：在执行中调整同列 AND 谓词的次序](https://github.com/duckdb/duckdb/pull/29337)（lnkuiper，18:30 合并至 main）：宽松的范围过滤与高度选择性的运行时 `IN` 并存时，可先应用后者，减少无效判断。作者的 2,000 万行对两键连接用例由 666 ms 降至 396 ms；不代表一般连接均有此收益。

### 正确性与内存

- [#29317：修复行组并列极值的 ORDER BY LIMIT](https://github.com/duckdb/duckdb/pull/29317)（Mustafa Hasan Khan，20:50 合并至 main）：避免重复计入延后统计的行，导致提前停扫、返回错误的极值。另两条是独立问题：[事务内新插入 NULL 被 OFFSET 跳过 #29318](https://github.com/duckdb/duckdb/pull/29318) 和 [DELETE/UPDATE 后旧极值被当成精确统计 #29332](https://github.com/duckdb/duckdb/pull/29332)，均由同一作者提出，核查时开放。
- [#29349：串行 CSV 扫描报告未闭合引号](https://github.com/duckdb/duckdb/pull/29349)（alonfaraj，23:30 合并至 main）：承接昨日 [#29312](https://github.com/duckdb/duckdb/issues/29312)，此前串行路径记录错误却未报告，可能只返回文件的有效前缀；测试还覆盖忽略错误及拒绝记录模式。[#29327](https://github.com/duckdb/duckdb/pull/29327)（hawkfish，20:23 合并至 main）则补上 C++ 时间解析的纳秒字段初始化；[报告](https://github.com/duckdb/duckdb/issues/29325) 指出它可能影响 Iceberg 边界值，不是普通 SQL 时间转换的普遍问题。
- [#29356：延迟创建直连 CTE 消费者](https://github.com/duckdb/duckdb/pull/29356)（lnkuiper，21:49 合并至 main）：无序消费者到首批输入才创建，避免空输入也为每个分支、每个工作线程预分配向量。带批次索引的路径仍提前创建；主干已有更广的 #27751 绕开报告用例，本条提供范围较小的修复，不代表 2.0.2 已发布。

### Parquet 与远程 I/O

- [#29234：通过 glob 表函数传递文件列表和元数据](https://github.com/duckdb/duckdb/pull/29234)（Robinho-MR，22:57 合并至 main）：可复用枚举时已获得的文件大小、修改时间、ETag 等信息来验证缓存和省去部分 HEAD。做读取后端 A/B 时，宜固定相同的显式路径，并单独测枚举和 HEAD，避免把文件发现的收益算给读取。
- [#29188：Parquet 页索引用函数谓词剪枝](https://github.com/duckdb/duckdb/pull/29188)（dentiny，18:56 合并至 main）：页级统计推导现在能把上下文交给函数统计回调，使有可用边界的表达式过滤有机会跳过页；不是所有函数都能裁剪。另一个 [#29220](https://github.com/duckdb/duckdb/pull/29220)（dentiny，19:41 合并至 main）让含 NaN 的列也能写入非 NaN 极值；作者提醒，读取端早于 2.0.0 时不认识 NaN 计数，跨版本读写需核对。
- [#29322：远程 Parquet 全扫 GET 数回归报告](https://github.com/duckdb/duckdb/issues/29322)（Cédric de Saint Léger，仍开放）：在报告者的单文件 MinIO 用例中，1.5.6 发 4 次 GET，2.0.1 发 79 次，字节数相同。关闭缓存或切换 EXACT 仍为 79；把上限提至 32 MiB 降至 6。但[小文件窄投影](https://github.com/duckdb/duckdb/issues/27787) 反而可能变成整文件读取。需要分别看请求数、字节和耗时，不能把调大上限当通用解法。

## 官方博客

[Hannes Mühleisen 用《星际迷航》台词测试自然语言查库](https://duckdb.org/2026/11/25/star-trek-queries-duckdb)（11 月 25 日）。作者从 11 个场景选取对话，用合成舰船数据让 Claude Code 写 SQL、由 DuckDB 执行；按作者判读，49 个答案中 40 个与剧本吻合。一个错误来自把六个月边界写成严格大于，漏掉恰好处于边界的记录。值得借鉴的是保留 SQL 和可核对的结果；这是挑选场景的演示，不是自然语言转 SQL 的通用准确率。

## 方向观察（推测）

同一天既有连接枚举改进，也有围绕行组统计的争论。推测后续性能验证需要把**估算有多准、估算本身有多贵、执行少做了多少工作**分开测。例如 #29326 不改估算规则而试图减少取数成本，#29329 则要证明减少扫描任务能抵消额外的初始化成本；这两条未定稿，不能视为路线图。

## 覆盖与限制

GitHub 按创建、合并和更新分别命中 60、41、87 条 PR（集合重叠，更新按两段查询，索引会随之后的活动变化），另筛查了 7 个新问题。官网列表、Atom 和官方文章源核对了发布日期与内容。未独立运行基准或回归测试；合入主干不等于稳定版已发布。
