---
title: "DuckDB 日报 · 2026-10-25：并行写入与 JSON 扫描减负，补齐执行边界"
date: 2026-10-25 12:00:00 +0800
description: "undo 分配与 NDJSON 扫描优化继续修订；流式 CTE、纳秒时间字段提取、虚拟列过滤及关联表函数参数修复进入评审。本文重点均为未合并提案。"
coverage_date: "2026-10-25"
---

## 覆盖窗口

北京时间 **2026-10-25 00:00 至 2026-10-26 00:00（不含终点）**，对应 UTC 2026-10-24 16:00 至 2026-10-25 16:00。实际核查：**2026-10-26 09:00 北京时间**。下文状态以核查时为准，发生在窗口之后的变化不算作当日成果。

## 今日速览

- **并行路径减负仍在评审**：undo 分配修订减少逐项加锁与 pin；NDJSON 扫描修订避免每个文件额外产生一个空尾批次。
- **正确性优先**：新增流式 CTE 挂起、纳秒时间字段进位、Parquet 虚拟列过滤、关联表函数命名参数等修复提案。
- **部署与运行环境适配**：CPU affinity 感知的默认线程数、模板二进制瘦身与 HTTP 长响应头处理值得跟进。本次合并时间检索未发现窗口内合并的 PR；以下精选项目均为 **open，尚未合并**，更不代表稳定版已可用。

## 重要 PR

### 1. undo 分配：把锁与 pin 从每个条目的热路径移开

**[Allocate undo entries without a lock or a pin per entry · #27798](https://github.com/duckdb/duckdb/pull/27798)**  
作者：**ywelsch**；状态：**open**；当日进展：北京时间 19:25 更新实现与标题，已核对对应提交及时间线，并非当天新建。

并行 UPDATE / DELETE 各线程按向量分配 undo 条目，旧分配器会反复争用事务分配锁及块 pin 的锁。修订保持当前头块 pinned，多个分配共享该 pin，通过 compare-and-swap 预留空间，仅新增块时取互斥锁。更新段自己的 allocator 仍保持逐项 pin，不能概括成所有分配都无锁。

作者报告的 3,000 万行、14 线程 Release 中位数里，全表 UPDATE 从 54 ms 到 47 ms，半表 DELETE 从 56 ms 到 42 ms；单线程没有变化。代价是事务保留当前 undo 块的 pin。这是作者的特定测试，不是本文复测或普遍性能保证。

### 2. NDJSON 小文件：不再调度空尾批次

**[Do not create an empty trailing batch for each newline-delimited JSON file · #27736](https://github.com/duckdb/duckdb/pull/27736)**  
作者：**mxmarkovics**；状态：**open**；当日进展：北京时间 01:41 的修订提交，随后重新请求评审。

原扫描器通过下一次零字节读取才发现文件结束，导致每个文件额外分配一个空批次；该批次还可能等待前一个批次、占用线程和缓冲区。提案让读到文件末尾的批次直接承担最后一条记录解析，取消空批次。单缓冲区大小的小文件可由两个缓冲区降为一个。

作者的 2,000 个小文件、24 线程、每次读人为增加 10 ms 延迟的实验，耗时由 1.83 s 降至 1.00 s，CPU 时间由 20.6 s 降至 0.58 s；较大文件并未显示相同收益。人为延迟只是模拟高延迟存储，不能当作真实对象存储基准。

### 3. 流式 CTE：补齐完成依赖，避免循环等待

**[Fix hang with streamed CTE consumers · #27841](https://github.com/duckdb/duckdb/pull/27841)**  
作者：**alonfaraj**；状态：**open**；当日新建（21:46）。

buffered CTE consumer 不仅要等 producer 初始化才能开始，还需要等 producer 完成才能结束。提案在 pipeline schedule 中补入完成阶段的依赖边，使循环检测识别此前漏掉的环，能够退回读取物化 CTE 结果。附单线程与默认线程配置的回归用例。意义是修复执行挂起，而不是单纯提高 CTE 吞吐。

### 4. TIMESTAMP_NS：字段提取不应先四舍五入到下一秒

**[Extract TIMESTAMP_NS date parts without rounding into the next second · #27824](https://github.com/duckdb/duckdb/pull/27824)**  
作者：**Pyolar**；状态：**open**；当日新建（01:31）。

隐式转换到微秒时间戳时的舍入，可能把 `09:59:59.999999533` 的 hour / minute / second 错读为下一小时的字段。新增纳秒类型重载，用向下截断的微秒值提取字段，同时覆盖 1970 年之前的负时间边界。

这是字段提取的兼容性修复提案，不是全局改变时间戳转换规则：`nanosecond()` 保持原有精度路径，`date_sub` 不在本次修改范围。

### 5. 优化器保护：虚拟列与类型不匹配不能套用普通列假设

- **[Skip filters on virtual columns when creating the late materialization LHS get · #27820](https://github.com/duckdb/duckdb/pull/27820)**，作者 **Pyolar**，**open**，当日 00:21 新建。延迟物化复制过滤器时，不能拿 `filename` 等虚拟列 ID 去索引普通返回类型数组。提案不复制这类过滤器到新 LHS，但保留原扫描上的过滤，修复带文件名条件的 Parquet TOP-N 查询内部错误。
- **[Skip zonemap pruning when the constant type doesn't match the column type · #27851](https://github.com/duckdb/duckdb/pull/27851)**，作者 **alonfaraj**，**open**，当日 23:39 新建。正则范围改写得到的 BLOB 常量经连接简化、过滤下推后，可能遇到 VARCHAR 列统计。提案在类型不一致时放弃 zonemap 裁剪，实际过滤仍运行，以保守扫描换取正确性。

两项都已有针对性回归用例；本文核对了改动，不声称亲自运行测试。

### 6. 关联表函数：命名选项不能变成位置参数

**[Bind named options in correlated table-function calls · #27833](https://github.com/duckdb/duckdb/pull/27833)**  
作者：**rustyconover**；状态：**open**；当日新建（11:30）。

在相关/LATERAL 表函数调用里，未知命名参数可能被当成输入列或位置参数，甚至静默选中另一个重载。提案先区分位置输入与命名选项，让选项参与签名选择，并复用校验、类型转换与默认值处理；位置输入仍留在输入计划中。

这影响的不只是报错质量，也涉及扩展表函数实际收到的参数和值。作者明确披露全量测试并非全绿，且存在与未修改 main 同样出现的失败/超时；不能把局部测试通过写成完整验证通过。

### 7. 默认线程数尊重 CPU affinity

**[Limit the default thread count by the CPU affinity mask · #27844](https://github.com/duckdb/duckdb/pull/27844)**  
作者：**levin-kitty**；状态：**open**；当日新建（22:05）。

在当前 Linux/glibc 实现中，默认 CPU 上限拟取 cgroup 限额与主线程 affinity mask CPU 数量的较小值，避免 `taskset` / `numactl` 限定少量 CPU 后仍按整机配置线程。读取失败保留旧行为，SLURM 分支尚未改变。

作者在 12 CPU VM 上验证，将进程限制为两个 CPU 时，默认 `threads / async_threads` 从 12 / 48 变成 2 / 8。没有新增环境无关的自动测试，不能据此认定所有 Linux libc 或大型 NUMA 环境都已覆盖。

### 8. 二进制瘦身：共享模板异常路径，裁剪专门常量执行器

作者均为 **louie-duck**；以下三项均为当日新建、**open**：

- **[Throw from non-template helpers in template-heavy code · #27842](https://github.com/duckdb/duckdb/pull/27842)**：将重复实例化的异常构造/格式化放进共享 helper，保持消息语义。作者在仅包含 core_functions、`-Oz` 与 `SMALLER_BINARY` 的构建中报告 stripped binary 减少 463 KB（约 2%）。
- **[Throw the UnifiedVectorFormat type mismatch from a non-template helper · #27845](https://github.com/duckdb/duckdb/pull/27845)**：同类方法用于 UnifiedVectorFormat 类型错误路径，该特定构建报告减少 33 KB。
- **[Add the scalar_executor_constant SMALLER_BINARY feature · #27847](https://github.com/duckdb/duckdb/pull/27847)**：允许裁剪专门的全常量执行器，改用通用路径计算一行后标记为常量，报告减少 115 KB。

这些数字来自各自实验，不相加为一个已验证组合收益；也不是普通完整构建的缩减比例或查询提速承诺。

### 9. HTTP 与测试稳定性：区分产品修复和降低测试深度

**[Fix CI: accept long response header lines in httplib, keep the deep VARIANT test within a 128 KiB thread stack · #27825](https://github.com/duckdb/duckdb/pull/27825)**  
作者：**louie-duck**；状态：**open**；当日新建（02:21）。

一部分把 vendored httplib 的单行响应头上限从 8 KiB 提高到 64 KiB，并用本地服务器返回 12 KiB 头的测试覆盖，针对较长 GitHub 重定向响应头导致的读取失败。

另一部分将深层 JSON→VARIANT 测试数据降低到 100 层，以适应 CI 的 128 KiB 工作线程栈，仍超过该 Parquet shredding 测试关注的 32 层界限。**这没有修复 JSON→VARIANT 转换本身的递归栈风险**，不能写成深层嵌套问题已全面解决。

## 官方博客

核对 [DuckDB 官方新闻列表](https://duckdb.org/news/)，未发现标为 **2026-10-25** 的新博客；最新条目仍为 10 月 21 日的 DuckDB 2.0.0 LTS 发布公告，本日报不将其重算作新文章。

[官方订阅源](https://duckdb.org/feed.xml) 本次无法成功读取：网页工具不支持返回的 XML 类型，独立 HTTP 请求返回 403。因此这里只能报告新闻列表的核对结果，不能宣称 RSS 同步验证通过。

## 方向观察（推测）

- **并行优化正聚焦协调开销，而非只优化算子计算。** #27798 的锁/pin 共享和 #27736 的空批次消除，分别减少写入与扫描路径里的非必要同步。二者仍未合并，测试负载也不同，不能外推为所有工作负载共同提速。
- **优化边界与新版兼容性仍需保守处理。** #27841、#27820、#27851 和 #27824 分别从调度、列绑定、统计裁剪与时间精度补充条件，说明执行改进必须配合正确性护栏；这是基于本组改动的观察，不是官方路线图。
- **嵌入式体积与受限运行环境有独立价值。** 模板瘦身和 affinity 提案关注二进制规模、可用 CPU 与默认资源配置，不应全部归为查询性能优化。

## 覆盖与限制

- 通过 GitHub 公开 API 检索窗口起点以来更新的 **54 个候选 PR**（返回 `incomplete_results=false`，一页完整返回），再按创建、提交、合并及讨论时间筛选；另查窗口内合并记录，返回 0 项。使用无结束上界的候选检索，避免遗漏在窗口结束后又更新的旧 PR；窗口之后新建的 PR 不纳入本日。
- 优先查看 Mytherin 及指定核心作者，但不为了作者配额凑内容。lnkuiper 的 #24561、carlopi 的 #26415 当日可见更新仅为自动标签变化，不将已有方案包装为新进展；hawkfish 的 #27739 当日讨论涉及 CI 状态，没有据此宣称新优化已完成。
- 对重点项目复查 PR 元数据、关键补丁、提交或时间线；未独立复跑构建、基准和测试。GitHub 搜索索引可能延迟，本文是重要进展精选，不保证涵盖全部活动。
- 当前所有精选 PR 仍开放。标签、作者的回移请求或测试描述不等于已合并；已合并也不等于已进入正式稳定版。
