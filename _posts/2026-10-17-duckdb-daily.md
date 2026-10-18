---
title: "DuckDB 日报 · 2026-10-17：解析器提速落地，Parquet 字典语义修复"
date: 2026-10-17 12:00:00 +0800
description: "解析器扫描优化与 INTERVAL 字典写出修复已合并；小域相关子查询、Bloom 索引和 C API v2 稳定性边界仍在提案阶段。"
coverage_date: "2026-10-17"
---

## 覆盖时间

北京时间 **2026-10-17 00:00 至 2026-10-18 00:00**（左闭右开），对应 UTC 2026-10-16 16:00 至 2026-10-17 16:00。实际核查：**2026-10-18 09:04 +08:00**。下文状态为核查时状态；**已合并不代表稳定版本已经发布或包含该改动**。

## 今日速览

- 两项落地：解析器减少重复扫描与迭代器开销；Parquet 写出不再合并表示不同的 INTERVAL 字典项。
- 性能探索：小域相关子查询保留过滤约束、原生 Bloom 索引、CSV 单遍转义，均仍为 open 提案。
- 兼容性与可靠性：C API v2 的稳定承诺、映射文件路径的访问检查，以及 JSON、Arrow、ADBC 等边界问题继续收敛。

## 重点 PR

### 已合并

**[#27393 Reduce parser scanning and token-iterator overhead](https://github.com/duckdb/duckdb/pull/27393)** · 作者 **Dtenwolde**，整理 **lnkuiper** 的优化；**merged**，北京时间 10 月 17 日 **00:49** 合入 main。

最终差异包括内联简单 token 访问器、复用 ASCII 判定、过长字面量在哈希前退出，以及批量跳过字符串、标识符和注释中的普通字节。作者报告其解析器工作负载汇总改善约 **6.2%**；这是 PR 自述基准，不是所有 SQL 端到端加速。carlopi 随后提出回移到 v2.0 分支的建议，**建议不等于已回移或发布**。

**[#27246 Keep normalization-equal intervals apart in Parquet dictionaries](https://github.com/duckdb/duckdb/pull/27246)** · 作者 **minhh-nguyen**；**merged**，北京时间 **00:25** 合入 main。

字典键改为比较和哈希原始 `months/days/micros` 三元组，避免把“比较相等但日期运算不同”的间隔写成同一个值。例如 `1 month 2 days` 与 `32 days` 加到月末日期上可得不同结果。回归测试覆盖两种 Parquet 版本与插入顺序；意义是保护往返读写语义，而非压缩率优化。

### 新建或实质推进，尚未合并

**[#27412 Fix remapped external access: follow up](https://github.com/duckdb/duckdb/pull/27412)** · 作者 **carlopi**；**open**，本日新建，叠加在 [#27381](https://github.com/duckdb/duckdb/pull/27381) 上，并吸收 **SrikanthKandula** 的 [#27405](https://github.com/duckdb/duckdb/pull/27405) 思路。

为 HTTP 请求携带原始文件访问路径，让 `s3://`、`hf://` 路径的授权检查不被映射后的 HTTPS URL 误伤，同时处理 URL 指定 endpoint 的边界。它修正的是路径与权限语义，不能概括成“一律跳过外部访问检查”。

**[#27426 Keep delimiter domain reductions for provably small domains](https://github.com/duckdb/duckdb/pull/27426)** · 作者 **kryonix**；**open**，本日新建。

用结构性行数上界识别至多一个标准向量的小域，保留相关子查询的半连接过滤，避免单个 key 的查询反而先聚合整张表。作者在 TPC-H SF1 的特定单线程例子中报告 **0.41 秒→0.010 秒**；不是通用 TPC-H 提速，且中等规模嵌套域和完整成本决策仍未解决。

**[#27402 Implement bloom index](https://github.com/duckdb/duckdb/pull/27402)** · 作者 **mrrandom0110**；**open**，本日新建。

新增 BLOOM 索引类型及扫描时按向量跳过不可能匹配数据的路径，面向 min/max zonemap 难以剪枝的等值查询。作者用特制的 4,000 万行 BIGINT 数据报告约十倍的中位数差异；分布刻意让 zonemap 失效，不能推广到一般查询，也不代表已获维护者采纳。

**[#27410 Mark C API v2 unstable](https://github.com/duckdb/duckdb/pull/27410)** · 作者 **evertlammerts**；**open**，本日新建。

提议将 v2 接口生命周期统一标为 unstable，显式选择不稳定接口并把扩展绑定到精确 DuckDB 版本；最终差异也包含加载侧检查。重点是避免过早冻结函数签名和扩展表布局，**这是待审兼容性方案，不是已发布 API 政策**。

**[#27403 Catalog: redirect a statement's table lookup](https://github.com/duckdb/duckdb/pull/27403)** · 作者 **xiaoxuandev**；**open**，本日新建。

增加 catalog 可选表查找重定向钩子，让元数据目录中的表交给另一个已附加 catalog 提供服务。方案限制为一跳，并保留只读附件及依赖检查；典型用途是 Glue 中 Hive/Iceberg 表共存。它是扩展集成能力提案，不是跨库写事务范围的放宽。

**[#27427 Add external workflow, and enable for lance](https://github.com/duckdb/duckdb/pull/27427)** · 作者 **carlopi**；**open**，本日新建。

在 **autograaf** 的 [#27379](https://github.com/duckdb/duckdb/pull/27379) 基础上增加外部扩展构建组并恢复 Lance 构建配置。核查时差异中 **Vortex 默认仍关闭**，因此不能写成两者都已恢复可用；相关依赖分支在统计窗口结束后还有提交，本文不把这些后续算入昨日完成事项。

### 值得关注的修复提案

以下均为本日新建、核查时 **open，尚未合并**：

- **louie-duck · [#27419 JSON 缩小缓冲区后的再次读取](https://github.com/duckdb/duckdb/pull/27419)**：回收的自动检测缓冲区不足时重新分配，并加读取边界断言，防止按完整容量读取到较小分配中。该问题跟随此前已合并的缓冲区缩小改动出现。
- **evertlammerts · [#27409 Arrow 字典的 NULL 哨兵](https://github.com/duckdb/duckdb/pull/27409)**：递归标记 STRUCT/ARRAY 子项为空，避免 NULL 索引复制时读取未初始化子值导致崩溃；没有把 LIST 内容一并展开。
- **Pitchfork-and-Torch · [#27418 ADBC 重复执行保护](https://github.com/duckdb/duckdb/pull/27418)**：目标是 **v1.5-variegata**，参数批次已消费时返回错误，避免再次执行后读取无效结果。不能当作 main 新增功能或稳定补丁已发布。
- **jdctinuiti · [#27399 异步写入取消死锁](https://github.com/duckdb/duckdb/pull/27399)**：丢弃待提交写入后，先释放提交锁，再等待完成队列，避免完成回调补队列时争用同一把锁。
- **iliaal · [#27401 日志刷新失败的析构处理](https://github.com/duckdb/duckdb/pull/27401)**：把刷新异常转为查询错误，避免连接清理时异常逃出析构函数而终止进程。
- **louie-duck · [#27421 常量参数错误的求值时机](https://github.com/duckdb/duckdb/pull/27421)**：字符串空针与 LEFT JOIN 改写使用可失败的常量求值，避免空表或永不执行分支在规划期提前报错。
- **kryonix · [#27406 重复行后的统计量](https://github.com/duckdb/duckdb/pull/27406)**、**[#27425 向量 validity 容量](https://github.com/duckdb/duckdb/pull/27425)**：分别清除会随重复行失效的累加统计，及让按 count 构建的缓冲区拥有覆盖物理容量的有效性掩码。后者作者明确说明当前 main 尚无已证明的 SQL 级复现，不应写成已确认普遍数据损坏。
- **kryonix · [#27407 敏感参数的 SQL 导出](https://github.com/duckdb/duckdb/pull/27407)**：为函数参数和 COPY 选项增加敏感标记，遇到可能导出凭据的调用时拒绝生成 SQL，而非输出语义改变的遮罩文本。
- **Kirill-Katz · [#27400 CSV 转义单遍处理](https://github.com/duckdb/duckdb/pull/27400)**：避免引号与转义符同时出现时重复遍历字符串；收益依赖内容分布，本日报不把作者微基准当成普遍写出性能。

## 官方博客

[官网新闻列表](https://duckdb.org/news/)未发现标注 **2026-10-17** 的新文章。最近两篇页面日期均为 **2026-10-16**：

- [NVIDIA Vera 基准](https://duckdb.org/2026/10/16/nvidia-vera-benchmark)：比较开发版 DuckDB 在 Vera 与 Xeon 6 上的大规模 TPC-H 工作负载。结果受硬件配置与预览构建约束，不表示 v2.0 已发布。
- [JSON 转为类型化列](https://duckdb.org/2026/10/16/json-to-typed-columns)：以结构推断及 JSON 转换函数串联落表流程；抽样可能遗漏稀有字段，严格转换有助于暴露异常。

**日期边界限制：**以上仅作最近文章索引，不计为已确认的本日新增。页面缺少精确发布时间与时区，[RSS](https://duckdb.org/feed.xml)读取失败，无法排除 10 月 16 日晚间发布而落入本北京时间窗口的情况。

## 方向观察（推测）

1. **性能改动正与语义边界一起推进。** 已合并解析器优化与待审小域过滤、Bloom 索引表明减少无效扫描仍是活跃方向；但特制基准与小域适用条件限制了可推广程度，不能据此预测统一性能提升。
2. **扩展接入与兼容性承诺仍在收敛。** C API v2、catalog 重定向及 Lance 构建提案是证据；它们尚未合并，不能视为官方路线图。
3. **字典编码必须保留值的完整语义。** INTERVAL 写出修复与 Arrow NULL 哨兵提案分别说明比较等价、嵌套有效性并不自动等同于可安全复用的物理表示；这不是关于所有字典路径性能的结论。

## 覆盖与限制

按公开 GitHub API 检索窗口内最后更新时间的 **57** 个 PR，并独立交叉检查窗口内 **22** 个新建、**2** 个合并结果；另检查窗口后更新的候选，避免其掩盖昨日活动。筛选优先关注 Mytherin、hannes、lnkuiper、pdet、Tishj、carlopi、hawkfish，但不按作者排除重要贡献。

重点条目核对了 PR 元数据、代码差异和相关讨论；旧 PR 只有标签或一般更新不直接算实质进展。例如 Parquet page-index 提案 [#27326](https://github.com/duckdb/duckdb/pull/27326)本窗口提交主要补自动加载注册，未把前一日读写设计讨论重复算作新落地。未对所有候选逐条复现测试，性能数字仅为作者报告。匿名 API 中途限流后改用 GitHub 连接继续读取；RSS 精确时间仍受限。本文不是完整 changelog，也未独立验证这些变更已进入任何稳定发行版。
