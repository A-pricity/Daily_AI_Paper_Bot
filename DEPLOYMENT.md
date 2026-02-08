# GitHub 部署指南

## 步骤 1：创建 GitHub 仓库

1. 访问 https://github.com/new
2. 创建新仓库，命名为 `daily_ai_paper_bot`
3. 选择 Public 或 Private（Private 需要付费才能使用 Actions）

## 步骤 2：上传代码

### 方法 A：使用 Git 命令行

```bash
cd d:\UCAS\daily_ai_paper_bot
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/你的用户名/daily_ai_paper_bot.git
git push -u origin main
```

### 方法 B：使用 GitHub Desktop

1. 打开 GitHub Desktop
2. File -> Add Local Repository
3. 选择 `d:\UCAS\daily_ai_paper_bot` 目录
4. Publish repository

## 步骤 3：配置 GitHub Secrets

1. 进入你的仓库页面
2. 点击 `Settings` -> `Secrets and variables` -> `Actions`
3. 点击 `New repository secret`
4. 添加以下 Secrets：

| Name | Value | 说明 |
|------|-------|------|
| `NVIDIA_API_KEY` | 你的 NVIDIA API Key | 必填 |
| `WECHAT_WEBHOOK` | 企业微信 Webhook URL | 可选 |

## 步骤 4：修改 GitHub Actions 配置

编辑 `.github/workflows/daily_paper_bot.yml` 文件，将第 44 行的仓库地址修改为你的实际地址：

```yaml
# 将这一行：
wechat_message += f"\n📮 [点击查看完整报告](https://github.com/your-username/daily_ai_paper_bot/blob/main/daily_report.md)"

# 修改为（替换 your-username 为你的 GitHub 用户名）：
wechat_message += f"\n📮 [点击查看完整报告](https://github.com/你的实际用户名/daily_ai_paper_bot/blob/main/daily_report.md)"
```

## 步骤 5：启用 GitHub Actions

1. 进入仓库的 `Actions` 标签页
2. 如果提示启用 Actions，点击 "I understand my workflows, go ahead and enable them"

## 步骤 6：测试运行

### 手动触发

1. 进入 `Actions` 标签页
2. 左侧选择 `Daily AI Paper Digest`
3. 点击 `Run workflow` -> `Run workflow`

### 查看运行日志

点击运行的工作流，可以查看详细的运行日志。

## 步骤 7：验证微信推送（如果配置）

检查企业微信群是否收到了推送消息。

## 常见问题

### Q: Actions 运行失败

**A:** 检查以下几点：
1. Secrets 是否正确配置
2. NVIDIA API Key 是否有效
3. 查看 Actions 运行日志获取详细错误信息

### Q: 微信推送失败

**A:**
1. 确认 Webhook URL 格式正确
2. 确认机器人未被禁用
3. 查看错误日志

### Q: 如何修改运行时间

**A:** 编辑 `.github/workflows/daily_paper_bot.yml`：

```yaml
schedule:
  # 格式：分 时 日 月 周
  # 例如：每天 UTC 时间 01:00（北京时间 09:00）
  - cron: '0 1 * * *'
```

时区转换：UTC 时间 = 北京时间 - 8 小时

### Q: API 配额用完怎么办

**A:**
1. 检查 NVIDIA API 的配额限制
2. 考虑升级 API 计划
3. 或切换到其他 API（如 DeepSeek）

## 完成！

现在你的 AI 论文日报生成器已经部署成功，每天早上 9 点会自动运行并推送日报到微信！
