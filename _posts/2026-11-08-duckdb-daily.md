---
title: "DuckDB 日报 · 2026-11-08：CI 修复与索引过滤"
date: 2026-11-08 12:00:00 +0800
description: "CI 修复整合、ART 残余过滤，以及正则和数值边界的开放修复。"
coverage_date: "2026-11-08"
updated_at: 2026-11-09T09:09:00+08:00
---

覆盖时间：北京时间 2026 年 11 月 8 日 00:00 至 11 月 9 日 00:00（左闭右开），即 UTC 11 月 7 日 16:00 至 11 月 8 日 16:00。检查时间：北京时间 11 月 9 日 09:09。

## 今日重点

- 当日未检索到合并 PR；一组扩展和 CI 修复进入整合，次日凌晨合并。
- ART 索引残余过滤、多文件统计和 Parquet Bloom 裁剪均有新提案。
- 正则、时间戳及大整数边界正确性修复待评审。

## 重要 PR

### CI 与兼容性

- [#28548 Green CI 修复整合](https://github.com/duckdb/duckdb/pull/28548)，carlopi，**11 月 8 日 19:11 新建**。汇总 Context 改动后的扩展兼容、row-id Bloom 缓冲越界、CI 内存与超时及 Wasm triplet 修复。该整合 PR **11 月 9 日 03:52 才合并**，不计入 11 月 8 日合并。
- [#28546 Wasm 扩展 triplet](https://github.com/duckdb/duckdb/pull/28546)，carlopi，**11 月 8 日 18:54 新建**，使用实际 VCPKG_TARGET_TRIPLET 链接 Wasm 扩展；次日凌晨合并至 main。[#28545](https://github.com/duckdb/duckdb/pull/28545) 是对应维护分支的工作，也在次日合并。

### 索引与查询优化

- [#28544 ART 扫描后处理残余过滤](https://github.com/duckdb/duckdb/pull/28544)，dentiny，**18:15 新建，检查时开放**。使用索引扫描后再应用其余 AND 条件，避免因额外谓词退回全表扫描；仍是单索引方案，不覆盖一般 OR。作者报告特定点查基准有明显收益，未独立复测。
- [#28530 多文件读取的列统计](https://github.com/duckdb/duckdb/pull/28530)，SrikanthKandula，**01:48 新建，检查时开放**。在提供 schema、绑定阶段未打开文件时仍使用 column_statistics，帮助过滤裁剪与基数估计。当天为草案，次日转为 ready。
- [#28550 Parquet Bloom 与保值 cast](https://github.com/duckdb/duckdb/pull/28550)，dentiny，**21:10 新建，检查时开放**。尝试反向转换比较常量，让保值类型转换不妨碍 Bloom filter 裁剪。
- [#28537 NULL 端点与 ART 范围扫描](https://github.com/duckdb/duckdb/pull/28537)，dentiny，**08:58 新建，检查时开放**。避免对含 NULL 端点的 BETWEEN 选择不正确的 ART 范围扫描。

### 边界正确性与设计讨论

- [#28538 正则空非捕获组](https://github.com/duckdb/duckdb/pull/28538)，alitrack，**09:46 新建，开放**。修正空非捕获组使 contains 被错误判作前缀或后缀匹配的问题。
- [#28539 时间戳字符串转换](https://github.com/duckdb/duckdb/pull/28539)，alitrack，**10:19 新建，开放**。补充 timestamp_ms/sec 转换，作者当晚增加 infinity 回归测试；[讨论](https://github.com/duckdb/duckdb/pull/28539#issuecomment-6721728474)中提到的统计最小值问题仍留待后续，不能说所有统计问题已解决。
- [#28540 UBIGINT 常量](https://github.com/duckdb/duckdb/pull/28540) 和 [#28549 UHUGEINT 重写](https://github.com/duckdb/duckdb/pull/28549)，alitrack，分别于 **11:15、20:41 新建，均开放**。前者避免先经有符号 64 位转换触发内部错误；后者在无法安全扩宽时跳过 MoveConstants 重写，避免错误结果。
- [#27890 函数或宏指定签名删除](https://github.com/duckdb/duckdb/pull/27890)，kryonix，**仍开放**。11 月 8 日更新方案使用标准 ALTER 路径保留对象身份与事务冲突语义，并为旧存储版本保留兼容的 WAL 表示；Robinho-MR 当晚[重新批准](https://github.com/duckdb/duckdb/pull/27890#pullrequestreview-5818539753)，但尚未合并。

## 官方文章

[DuckDB 官方博客列表](https://duckdb.org/news/)未发现标注 11 月 8 日的新博客；最新可见文章标注 11 月 5 日。RSS 未能通过网页工具解析，故不将列表检查等同于完整 feed 验证。

## 方向观察

**推测：** 当天的索引、Parquet 和统计提案继续关注减少无关扫描，同时正则和大整数修复强调优化改写必须保留边界正确性。多数仍是开放 PR，不能视为官方路线图或已发布功能。

## 覆盖与局限

公开 GitHub 候选、时间线和评审按页检查，以创建、合并和具体评论时间判断当天进展；REST 时间线不能保证还原所有正文编辑。性能数据来自作者，未独立复测。官网列表已检查，RSS 受格式限制未解析。除另有说明时间均为北京时间。**合并至 main 或维护分支不等于稳定版已包含相关变化。**
