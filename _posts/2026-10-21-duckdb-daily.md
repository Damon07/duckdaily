---
title: "DuckDB 日报 · 2026-10-21：2.0 LTS 发布，优化器减负与执行修复并进"
date: 2026-10-21 12:00:00 +0800
description: "DuckDB 2.0.0 LTS 正式发布；main 合并冗余排序消除、取模统计传播、窗口帧分析及分区 COPY 死锁修复，NUMERIC 仍在设计审查。"
coverage_date: "2026-10-21"
---

## 覆盖时间
北京时间 **2026-10-21 00:00 至 2026-10-22 00:00**，左闭右开；对应 UTC 10 月 20 日 16:00 至 10 月 21 日 16:00。实际核查：北京时间 **2026-10-22 09:04**。以下时间均为北京时间，状态截至核查时。

## 今日速览
- **2.0.0 LTS 已正式发布**，不再只是开发版预告；升级前需检查存储格式、lambda 语法和扩展兼容性。
- main 合并了冗余排序消除、取模统计传播、窗口帧分析和优化器锁竞争减负。
- 执行可靠性继续补强：分区 COPY 的连接任务死锁、低内存聚合预留及损坏数据边界校验；NUMERIC 和整数成员连接优化仍是开放提案。

**版本边界：下列 PR 的“merged”指合入 main，不表示它们都已包含在当天的 2.0.0 安装包。本文未逐项核对发行标签的提交包含关系。**

## 重要 PR

### 1. 消除上层不再需要的排序
[ #27569 · Remove ORDER BY operators whose order is discarded above them](https://github.com/duckdb/duckdb/pull/27569)  
作者 **h4nsmuller**；**merged**，当日 19:08 合并。

新增 `redundant_order` 优化，移除被上层分组、连接、去重或另一排序丢弃的子查询排序，避免无效排序和溢写。最终代码与最初正文有所区别：按 [Mytherin 的审查](https://github.com/duckdb/duckdb/pull/27569#pullrequestreview-5588274640)，分组哈希聚合路径可移除输入排序；未分组聚合仍检查顺序依赖。LIMIT、窗口等不能随意跨越。不要把子查询排序当作分组聚合内部顺序的保证。

### 2. 取模统计不仅帮助裁剪，也衔接有限去重
[#27595 · Propagate statistics through the modulo operator](https://github.com/duckdb/duckdb/pull/27595)  
作者 **h4nsmuller**；**merged**，当日 21:49 合并。

为 `%` 推导结果范围，使不可能成立的过滤可折叠、部分行组可裁剪，同时保留除零错误语义。**最终 diff 还包含** PERFECT_HASH_GROUP_BY 到 LIMITED_DISTINCT 的条件改写，避免更精确统计选中 perfect hash 后失去适用的 LIMIT 提前终止；PR 正文“另行修改”的描述未完全同步，本文以代码为准。

### 3. 窗口帧分析利用唯一列组合
[#26502 · Window Frame Analysis](https://github.com/duckdb/duckdb/pull/26502)  
作者 **hawkfish**；**merged**，当日 15:44 合并。

复用函数依赖分析，通过唯一列组合识别退化为单行的窗口，简化合适的窗口计算。补充排名函数和延迟唯一约束的边界处理，避免错误地把排名函数当作普通帧内聚合。意义是用已知唯一性消除工作，而不是所有窗口都获得相同加速。

### 4. 并发短查询跳过默认配置下的优化器互斥锁
[#27578 · Skip the disabled_optimizers lock when no optimizer is disabled](https://github.com/duckdb/duckdb/pull/27578)  
作者 **dentiny**；**merged**，当日 16:23 合并。

用同步维护的原子标志识别“没有禁用优化器”的常见情况，避免每轮优化都争抢数据库级互斥锁。针对多连接点查的规划开销，作者提供的测试收益随负载变化；不能推广为所有查询的固定提升。

### 5. 修复分区 COPY 与连接源之间的等待环
[#27562 · Do not let a producing IE join / hash join source block on its siblings under a partitioned COPY](https://github.com/duckdb/duckdb/pull/27562)  
作者 **h4nsmuller**；**merged**，当日 20:27 合并。

已经产出数据的连接任务若继续等待同阶段任务，可能阻止分区写出完成局部合并，形成互相等待。修改覆盖 IE join、非溢写 RIGHT/FULL hash join 和相关外连接 AsOf 路径，并加入测试。**溢写 hash join 的跨轮等待风险未在此解决**，不能据此宣称分区 COPY 的所有死锁已消除。

### 6. 低内存与损坏输入防护
- [#27592 · Revert TemporaryMemoryManager reservation cap](https://github.com/duckdb/duckdb/pull/27592)，**lnkuiper**，**merged**，当日 17:53：撤回预留上限逻辑，并让聚合预留增长依据当前使用量，而非未获满足的旧请求，处理低内存分组聚合问题；不等于取消整体内存限制。
- [#27535 · Batch the new Ready To Merge fixes](https://github.com/duckdb/duckdb/pull/27535)，**Robinho-MR**，**merged**，当日 23:12：集中补强 Parquet Thrift 列表、BIGNUM、索引磁盘偏移、WAL 索引分配及 shredded VARIANT 反序列化等边界校验，并修正若干 SQL 重建细节。重点是损坏或异常输入的可控失败，不把它擅自定性为已披露安全漏洞。

### 7. 两项仍开放的设计与执行提案
- [#27567 · NUMERIC](https://github.com/duckdb/duckdb/pull/27567)，**h4nsmuller**，**open**：当日继续改进运行时数值特化并报告性能实验。Mytherin 在 [18:37 的讨论](https://github.com/duckdb/duckdb/pull/27567#issuecomment-6313922399)中接受逻辑类型可不同，但要求重新评估与 VARIANT 数值物理表示的共享。独立存储和编码方案尚非定案，分组、排序仍有开销，作者基准不是独立验证结果。
- [#27620 · Optimize integer membership joins with perfect hashing](https://github.com/duckdb/duckdb/pull/27620)，**smvv**，**open**：当日 22:49 新建，将紧凑位图 perfect hash 路径扩展至整数 SEMI/ANTI 成员连接，考虑重复键、NULL 语义和稀疏度回退；MARK 连接仍留在旧路径。当前实现与基准可能包含窗口后的修订，本文只将“新提案”计入当日，不将后续实验归为当日完成。

## 官方博客与正式发布
[Announcing DuckDB 2.0.0 LTS “Cinnamon Teal”](https://duckdb.org/2026/10/21/announcing-duckdb-200)，**The DuckDB team**，官方日期 **2026-10-21**。

[GitHub v2.0.0 release](https://github.com/duckdb/duckdb/releases/tag/v2.0.0)在当日 **20:49:12** 发布，既非 draft 也非 prerelease，明确落在窗口内。官方介绍 Quack/CONNECT、异步 I/O、VARIANT、默认 PEG 解析器、触发器和 CLI agent mode，LTS 支持至少延续至 2027 年 10 月。

实践上优先做升级兼容性验证：2.0 新建数据库文件不能由旧版读取；旧数据库可由 2.0 读写并保持旧版可读。旧单箭头 lambda 默认关闭，C++ 构建要求提高到 C++17；C API v2 尚未宣布稳定，部分客户端和扩展可能稍后到齐。官方建议关键业务可考虑等待 11 月首个补丁版，先用代表性负载做影子测试。

## 方向观察（推测）
- #27569、#27595、#26502 与 #27578 共同体现“减少不必做的工作”：计划简化、范围推导、唯一性利用和锁竞争削减。这是本日代码变化的归纳，不是官方性能路线图。
- #27562 与 #27592 显示并行执行、写出背压和内存预算仍需协同调整；已知未覆盖路径提醒我们不能用单项修复代表整个子系统稳定。
- NUMERIC 审查显示维护者重视与既有 VARIANT 基础设施共享，但是否采用、如何实现仍未确定。它与已经发布的 2.0 LTS 应分开理解。

## 覆盖与限制
GitHub 公开 API 按更新时间分页检查 **108 条候选 PR**，并核查精选条目的创建、合并或讨论时间、主要最终差异；排除纯机器人活动与窗口后新建项，不把 updated_at 直接当作实质进展。不是逐 PR 全量审计，也未自行运行基准。部分 PR 链接私有 issue，本文只依据公开代码与讨论。

官网新闻列表和新博文均可读取，列表中本日新文为上述一篇；Atom feed 因工具不支持 XML、直接读取返回 HTTP 403，**未完成 RSS 交叉验证**，不将读取失败当作没有更新。PR 状态为核查时快照；除已单独确认的正式发行外，合并、提案和稳定版可用性分别表述。
