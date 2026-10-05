# DuckDaily

非官方 DuckDB 中文社区日报。公开来源、中文概述、原始链接、明确区分事实与推测。

## 部署

在 GitHub 的 Settings → Pages 选择 **Deploy from a branch**，发布源为 **main / (root)**。GitHub 原生 Jekyll 构建会在推送后自动发布；不需要个人访问令牌、外部 API 密钥或自定义部署 workflow。

预期地址：`https://damon07.github.io/duckdaily/`（必须在首次部署成功后验证）。

## 发布日报

按 `PUBLISHING.md` 的约定写入 `_posts/YYYY-MM-DD-duckdb-daily.md`。文件名日期和 front matter 日期对应报道覆盖日，而非文章生成日。同一日期只保留一个文件，重试先检查现有内容，避免重复发布。

每日资料检索和中文撰写由外部已授权的定时助手负责；本仓库只负责存储、构建和公开展示，不包含独立内容生成定时器。不要把私有对话、邮箱、访问令牌或其他私人资料写入此公开仓库。

## 本地检查

安装 Ruby / Bundler 后：

```sh
bundle install
bundle exec jekyll build --strict_front_matter
bundle exec jekyll serve --baseurl /duckdaily
```

内容基础校验：`python3 scripts/check_posts.py`。

网站支持移动端、明暗色模式、归档与 Atom RSS。没有日报时显示真实空状态，不生成示例新闻。
