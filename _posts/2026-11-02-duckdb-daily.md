---
title: "DuckDB 日报 · 2026-11-02：短查询锁优化、Parquet 校验与公共子计划"
date: 2026-11-02 12:00:00 +0800
description: "三类短语句路径优化与公共子计划复用落地，Parquet 加强损坏检测；Mark 对聚合共享和日志优化提出性能边界。"
coverage_date: "2026-11-02"
---

## 覆盖时间

北京时间 **2026-11-02 00:00 至 2026-11-03 00:00**，左闭右开；对应 UTC 2026-11-01 16:00 至 2026-11-02 16:00。实际核查：北京时间 **2026-11-03 09:01–09:03**。下文状态为核查时状态，窗口后合并另行注明。**已合并不等于已在稳定版发布**；[最新正式 release](https://github.com/duckdb/duckdb/releases/latest) 核查时仍为 v2.0.0。

## 今日速览

- 短语句执行路径、公共子计划复用和 VARIANT 快速路径落地；其中“四锁”PR 的最终版本只保留三类优化，日志改动被移出。
- Parquet 增加页大小、footer、几何统计及短读校验；优化器、聚合和数值时间计算也有多项结果正确性修复。
- Mark 对单遍聚合的讨论强调过滤/切片成本：减少扫描次数不自动等于更快。CTE 过滤下推等新方案在窗口后才合并。

## 重要 PR

### 窗内已合并：执行与存储

- **[#28204：短语句路径减少全局锁竞争](https://github.com/duckdb/duckdb/pull/28204)**，作者 **dentiny**，merged。最终补丁包含扩展设置索引缓存、扩展回调 registry 无锁读取、线程池按需重启。**没有合入日志锁改动**：[Mark 要求先移除该部分](https://github.com/duckdb/duckdb/pull/28204#issuecomment-6572670721)，后续应覆盖启用日志的生产场景，而非只优化禁用日志的基准。不能把原始“四锁”方案的收益直接归给最终版本。
- **[#28144：公共子计划匹配扩展](https://github.com/duckdb/duckdb/pull/28144)**，作者 **lnkuiper**，merged。允许符合安全约束的不同投影与部分内连接子计划归一化后共享，减少重复扫描/连接；并非任意不同过滤都能合并。
- **[#28231：贪心连接枚举补查反方向](https://github.com/duckdb/duckdb/pull/28231)**，作者 **DinosL**，merged。首次方向非法时尝试相反方向，避免漏掉 LEFT/SEMI/ANTI 的合法候选，保留后续物化和并行优化机会。
- **[#28233：Parquet 元数据脱离扫描 reader 生命周期](https://github.com/duckdb/duckdb/pull/28233)**，作者 **lnkuiper**，merged。独立缓存绑定时元数据，即使初始 reader 被消耗或裁剪，统计与投影下推仍可使用；取统计前检查物理与输出 schema。
- **[#28192：聚合先查状态再触碰 VARIANT 输入](https://github.com/duckdb/duckdb/pull/28192)**、**[#28209：确定缺键直接返回常量 NULL](https://github.com/duckdb/duckdb/pull/28209)**，作者均为 **OneCyrus**，均 merged。前者减少已完成赋值的 FIRST/ANY_VALUE 对 shredded 数据的无用还原，保留 LAST/NULL 语义；后者仅在完全 shredded 且能确认缺键时跳过通用还原路径。
- **[#27930：系统目录过滤下推到表/视图身份](https://github.com/duckdb/duckdb/pull/27930)**，作者 **RishiSajay**，merged。将表名/OID 等过滤推进 duckdb_tables、duckdb_views，并让 duckdb_columns 使用同一分层扫描机制；远程目录可据此减少无关枚举，具体收益取决于目录实现。

### 窗内已合并：损坏输入与错误结果

- **[#28134：Parquet footer、几何统计和过滤短读校验](https://github.com/duckdb/duckdb/pull/28134)**、**[#28241：未压缩页与解压输出大小校验](https://github.com/duckdb/duckdb/pull/28241)**，作者均为 **HendrikLambert**，均 merged。分别防止长度运算溢出、非法几何代码和未读列表值流入下游，并拒绝 V2 页大小不匹配、GZIP/Brotli 解压不足的损坏数据。是输入防御增强，不据此宣称已发生攻击。
- **[#28225：IN 改写保留 TRY 与条件分支边界](https://github.com/duckdb/duckdb/pull/28225)**，作者 **kryonix**，merged。避免 mark join 将可能出错的 probe 提前执行到错误捕获或 CASE/COALESCE 等保护之外，防止本应被捕获/跳过的异常外泄。
- **[#28217：ROW_NUMBER 表达式不能当成裸行号](https://github.com/duckdb/duckdb/pull/28217)**，作者 **hsusul**，merged。Top-N 消除遇到加法等非列引用投影即停止，避免丢掉表达式而错误保留行；直接行号过滤仍可优化。
- **[#28098：排序聚合超过 65,535 个状态的分批收尾](https://github.com/duckdb/duckdb/pull/28098)**，作者 **jmestwa-coder**，merged。每批正确切片状态并加上输出偏移，防止重读已清空状态、漏算后续状态而输出 NULL。
- **[#28235：STRUCT→UNION 转换不得污染输入](https://github.com/duckdb/duckdb/pull/28235)**，作者 **alonfaraj**，merged。写入失败行的 NULL 前复制成员向量，避免共享底层数据使原值或后续重复转换发生变化。
- **[#28159：BIGINT 乘法回退溢出检查](https://github.com/duckdb/duckdb/pull/28159)**，作者 **kryonix**，merged。修正非 GCC/Clang 内建检查路径的漏报，尤其影响 MSVC 等构建，避免溢出静默绕回错误数值。
- **[#28210：未指定种子时混入新鲜熵](https://github.com/duckdb/duckdb/pull/28210)**，作者 **Richard-Durkee**，merged。随机函数和采样派生种子不再只依赖可能被 fork/快照复制的连接状态；显式种子仍保留可重复行为，不等于提供通用密码学随机保证。
- **[#28019：按 DOUBLE 实际存储值舍入](https://github.com/duckdb/duckdb/pull/28019)**，作者 **Robinho-MR**，merged。修正缩放后恰落中点造成的双重舍入，最终实现用乘积误差判定；例如 round(2.675::DOUBLE, 2) 的结果变为 2.67，可能影响依赖旧结果的断言。
- **[#27804：ICU time_bucket 接受纳秒带时区输入](https://github.com/duckdb/duckdb/pull/27804)**、**[#27923：纳秒日期部分提取](https://github.com/duckdb/duckdb/pull/27923)**，作者均为 **hawkfish**，均 merged。为相应类型提供显式路径，避免隐式降精度舍入把秒/分钟边界推到下一格；不应理解为 time_bucket 输出全面升级为纳秒精度。
- **[#28067：无穷时间戳连续分位数插值报错](https://github.com/duckdb/duckdb/pull/28067)**，作者 **kryonix**，merged。拒绝对不同端点中的无穷哨兵做有限数插值，并约束整数插值范围；相同端点、直接选取元素及离散分位数仍有各自语义。

### 窗内已合并：SQL 兼容性

- **[#28018：简单 CASE 的比较操作符](https://github.com/duckdb/duckdb/pull/28018)**、**[#28023：逗号分隔的 WHEN 候选](https://github.com/duckdb/duckdb/pull/28023)**，作者均为 **Dtenwolde**，均 merged。扩展为 CASE x WHEN < 0、WHEN 0, 1 等写法，减少重复条件；**[#28232](https://github.com/duckdb/duckdb/pull/28232)**（同作者，merged）恢复 CREATE SECRET 选项接受 CASE/COALESCE 等表达式的兼容性。

### 窗内提出，窗口后合并

- **[#28224：连接过滤推进 CTE 定义](https://github.com/duckdb/duckdb/pull/28224)**，作者 **lnkuiper**，窗口内新建，核查时 merged，实际合并为**北京时间 11 月 3 日 00:56**。合并多个消费者的运行时过滤并调整依赖调度，减少 CTE 物化数据。
- **[#28242：区分基数估计与保证上界](https://github.com/duckdb/duckdb/pull/28242)**，作者 **lnkuiper**，窗口内新建，核查时 merged，实际合并为**11 月 3 日 00:38**。避免 LIMIT 消除等依赖估算而作出不安全决定，Parquet 上界考虑保留的行组。
- **[#28230：顺序 CSV 缓冲改为溢写而非回头重读](https://github.com/duckdb/duckdb/pull/28230)**，作者 **fastio**，窗口内新建，核查时 merged，实际合并为**11 月 3 日 00:20**。随机访问缓冲仍可按字节范围重读，顺序缓冲由 buffer manager 恢复，移除反复 seek/reload 路径。

### 当前仍为提案：少扫描之外，还要少做重复工作

- **[#28257：同源兄弟标量聚合合成单遍扫描](https://github.com/duckdb/duckdb/pull/28257)**，作者 **h4nsmuller**，窗口内新建，open/draft。用 FILTER 聚合合并扫描，但并非所有基准都更快。[Mark 的窗内评审](https://github.com/duckdb/duckdb/pull/28257#issuecomment-6581258343)优先建议每个唯一“过滤条件＋输入”只计算过滤与切片一次；性能分歧仍需解释，不能预告普遍提速。
- **[#28243：连接基数计算保留数值范围](https://github.com/duckdb/duckdb/pull/28243)**，作者 **lnkuiper**，窗口内新建，open。减少中间乘积溢出/下溢与小数 SEMI/ANTI 估计损失，不是更换整套选择率模型。
- **[#28254：外部资源 SHOW 支持 WHERE](https://github.com/duckdb/duckdb/pull/28254)**、**[#28255：资源类型过滤下推](https://github.com/duckdb/duckdb/pull/28255)**、**[#28256：按外部资源类型自动加载扩展](https://github.com/duckdb/duckdb/pull/28256)**，作者均为 **carlopi**，窗口内新建、均 open。组合目标是少枚举无关 provider，并让类型发现与扩展加载衔接；尚非稳定版承诺。

## 官方博客

[官网新闻列表](https://duckdb.org/news/)与[官方 Atom feed](https://duckdb.org/feed.xml)均未见发布日期为 11 月 2 日的新文章；最新仍为 10 月 29 日的 DuckLake 用户案例，本日报不把旧文重计为新发布。网页阅读器不支持 XML，但本次通过正常 HTTP 成功读取并解析 feed，因此没有沿用此前的 RSS 访问失败结论。

## 方向观察（推测）

1. **性能优化更强调真实执行成本和安全边界。** #28204 移出只针对禁用日志的优化，#28257 的过滤/切片讨论说明“少锁”“少扫描”都需要对照真实工作负载；并不能从个别基准推出整体性能承诺。
2. **元数据既用于提速，也需要可信性约束。** #28233 保留统计来源，#28242 区分估计与上界，Parquet 校验拒绝损坏输入，体现优化信息与正确性共同收紧。这是本日补丁的归纳，不是官方路线图。
3. **VARIANT 正在减少不必要的还原工作。** #28192/#28209 的快路径均依赖可证明条件，不能扩展成所有半结构化查询都会加速。

## 覆盖与限制

通过 GitHub 公开 API 分两页检查 **135 个更新候选**，另以精确窗口独立检索确认 **29 次合并**；按创建、合并及原始讨论时间筛选，不把 updated_at 或机器人活动直接当作实质更新。重点项回查实际补丁，特别修正 #28204 标题/旧描述与最终内容的差异。按主题精选，不逐条罗列所有改动，也未在本机独立复跑作者基准。窗口后合并仅作状态补充，不计入当天合并数。全部内容来自公开 PR、官方博客/feed 和发布记录。
