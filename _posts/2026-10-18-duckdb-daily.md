---
title: "DuckDB 日报 · 2026-10-18：C API v2 不稳定边界落地，扩展与类型兼容修复"
date: 2026-10-18 12:00:00 +0800
description: "C API v2 显式选择与版本约束、基础统计回调合并；S3/hf 权限、Arrow 字典、几何过滤下推和切片序列化获得修复。"
coverage_date: "2026-10-18"
---

覆盖窗口：北京时间 **2026-10-18 00:00 至 2026-10-19 00:00**，不含终点；对应 UTC 2026-10-17 16:00 至 2026-10-18 16:00。实际检查：北京时间 **2026-10-19 09:08**。以下事件时间均为北京时间。

## 今日速览

- C API v2 的 unstable 约束已合并；另一项基础统计回调让扩展参与 NULL/有效值推断，但不是完整类型统计。
- S3/hf 路径权限检查、Arrow STRUCT 字典 NULL、几何过滤下推和数组切片序列化等兼容问题得到修复。
- Lance 构建恢复；另有预编译语句结果类型、remap_struct 参数校验提案，尚未合并。

**已合并不等于已发布。** 本文区分 main 与 v2.0-cyanoptera 开发分支；截至检查，[官方最新正式版本](https://github.com/duckdb/duckdb/releases)仍为 v1.5.6。

## 重要 PR

### 1. C API v2：不稳定接口约束与基础统计能力

- **[#27410：C API v2 unstable 约束](https://github.com/duckdb/duckdb/pull/27410)**，作者 **evertlammerts**。**merged**，19:07 合入 v2.0-cyanoptera。消费者需显式开启不稳定 API，V2 扩展绑定精确 DuckDB 版本，并有加载端检查。意义是把接口仍在演进的风险落实到使用约束，不能称为“稳定 API 发布”。
- **[#26356：基础统计回调](https://github.com/duckdb/duckdb/pull/26356)**，作者 **Maxxen**。**merged**，23:01 合入 main。为标量、聚合及表函数增加统计回调与 stats handle，让扩展参与优化器的 NULL/有效值推断。目前仅提供通用有效性信息，没有类型专属统计；嵌套字段等场景仍有限制。

### 2. S3/hf 访问设置：检查正确的路径，同时保留目标权限约束

**[#27381](https://github.com/duckdb/duckdb/pull/27381)／[#27412](https://github.com/duckdb/duckdb/pull/27412)**，作者均为 **carlopi**。两项均 **merged**，约 21:58 合入 v2.0-cyanoptera。

修复 s3://、hf:// 被映射为 HTTP 后，allowed_directories 按错误路径判断的问题；后续版本同时保留 URL 指定 s3_endpoint 时的实际目标权限校验。这是避免合法路径被误拒绝的兼容性修复，不是绕过访问控制。两项为相关推进，合并呈现以免重复计算。

### 3. Lance 恢复构建，Vortex 默认仍关闭

**[#27427](https://github.com/duckdb/duckdb/pull/27427)**，作者 **carlopi**。**merged**，19:23 合入 v2.0-cyanoptera。

恢复 Lance 配置并增加 external 扩展 CI 组；最终差异中 Vortex 默认仍为 OFF，Windows 的 Lance 测试不加载。因此不能概括成“两种扩展全面恢复”。相关的 autograaf 提案 [#27379](https://github.com/duckdb/duckdb/pull/27379) 当天关闭，未合并。

### 4. Arrow 字典 NULL 哨兵：修复 STRUCT 扫描崩溃

**[#27409](https://github.com/duckdb/duckdb/pull/27409)**，作者 **evertlammerts**。**merged**，19:55 合入 v2.0-cyanoptera。

带 NULL 索引的 Arrow STRUCT 字典可能触发段错误；修复把 NULL 哨兵递归传播到 STRUCT/ARRAY 子向量。这是明确的边界正确性修复，PR 仍将另外两类字典缺陷留待后续，不能宣称 Arrow 字典问题已全部解决。

### 5. GEOMETRY 元数据转换恢复过滤下推

**[#27249](https://github.com/duckdb/duckdb/pull/27249)**，作者 **jatorre**。**merged**，20:51 合入 v2.0-cyanoptera。

将 GEOMETRY → GEOMETRY 元数据转换识别为运行时不会抛错，使带 CRS 几何列、混合谓词的查询重新具备过滤下推与 Parquet row-group 裁剪机会。意义是避免无害转换阻挡其他过滤条件；没有据此推导通用性能加速比。

### 6. 开放边界切片的序列化兼容

**[#27120](https://github.com/duckdb/duckdb/pull/27120)**，作者 **Maxxen**。**merged**，19:57 合入 main。

修复 x[2:]、x[:2] 等表达式的序列化，兼顾 v1.5/v2.0 存储往返和旧库读取。覆盖视图、宏、默认值、生成列及约束，重点是表达式写入数据库后仍可正确恢复。

### 7. 既有修复回移与扩展版本更新

**[#27069](https://github.com/duckdb/duckdb/pull/27069)**，作者 **carlopi**，20:09 **merged** 至 v2.0-cyanoptera：回移五项已有修复，涉及远程 URL 查询参数、列表推导中的 cast、yearweek 非单调性、窗口 volatile 表达式限制及 GLOB 尾部连字符。它们不是当天新推出的五项功能。

**[#27385](https://github.com/duckdb/duckdb/pull/27385)**（**benfleis**，19:41）与 **[#27396](https://github.com/duckdb/duckdb/pull/27396)**（**duckdblabs-bot**，19:27）均已合并，更新 Delta、Unity Catalog、Azure 等扩展引用；部分范围重叠，不重复计作独立能力新增。

## 新提案与后续观察

- **[#27430：预编译语句结果类型](https://github.com/duckdb/duckdb/pull/27430)**，**patrickswedish**，00:44 创建，当前 **open / draft**。拟保留 SELECT、INSERT、UPDATE、DELETE 等实际类型，避免统一报告为 EXECUTE；附普通、streaming、pending 路径测试，尚未落地。
- **[#27434：remap_struct 参数校验](https://github.com/duckdb/duckdb/pull/27434)**，**abp002**，21:09 创建，当前 **open**。第三个参数仅允许 STRUCT 或 NULL，把 MAP/LIST/ARRAY 引发的 internal error 提前变成清晰的绑定错误。
- **[#27432：httpfs 与设置枚举](https://github.com/duckdb/duckdb/pull/27432)**，**carlopi**，19:19 创建。当天增加 duckdb_settings(include_all := true)，避免生成扩展自动加载入口时遗漏 debug/deprecated 设置，同时更新 httpfs。**日界状态：未合并；检查时状态：merged，合并发生于 10 月 19 日 02:10，属于次日，不计入本日合并成果。**
- **[#24605](https://github.com/duckdb/duckdb/pull/24605)**（**gulugulubing**）与 **[#25916](https://github.com/duckdb/duckdb/pull/25916)**（**Maxxen**）仍 **open**。前者当天改进 IS NOT DISTINCT FROM 下推测试的辨识力；后者修正自定义 VFS 的 C++ 初始化顺序以修 CI。两项增量有限，不把整个既有提案包装成当天新功能。

## 官方博客

[官网新闻](https://duckdb.org/news/)与[官方 Atom feed](https://duckdb.org/feed.xml)交叉核对后，**未发现 10 月 18 日的新文章**。最新条目仍为 10 月 16 日的 JSON 类型化列教程与 NVIDIA Vera 开发版基准测试；不重复当作今日发布。

## 方向观察

**推测，非官方路线图：** C API v2 的显式 unstable 边界、扩展构建恢复与多项兼容修复同时合并，表明当天工作更偏向让开发分支的接口、加载和类型边界更可控。依据是上述实际合并内容，而非单个 PR 的愿景。

**推测：** GEOMETRY 转换分类影响到过滤下推，说明性能问题有时源于表达式语义标记，而不只是扫描实现。当前证据仅支持这一具体路径，不能推广成所有空间查询都会提速。

## 覆盖与限制

按更新时间分页读取 duckdb/duckdb 的公开 PR 列表两页、共 200 项；第二页最新更新时间已早于本日窗口。对窗口候选回查时间线，重点项目核对实际差异，核实 11 项合并、3 项新提案及若干旧提案进展，排除仅在窗口后发生的合并。未发现 Mytherin 本人在窗口内新建或合并的 PR；不据此推断他没有其他社区活动。

本文为重要进展精选，不穷尽所有扩展仓库、Issues 或 Discussions，也没有独立运行性能实验。各项状态以检查时为准，事件归属以北京时间窗口判断。周内全局趋势另见[本周周报](/duckdaily/weekly/2026/10/18/)。
