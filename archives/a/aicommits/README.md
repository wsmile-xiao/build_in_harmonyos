# aicommits — AI 生成 git commit message 的 CLI 工具

## 一句话说明
aicommits 是一个用 AI 自动生成 git commit message 的命令行工具：读取暂存区的 git diff，调用配置的 AI 提供商生成提交信息。

## 功能概述
- 自动生成 commit message（支持 plain/conventional/gitmoji/subject+body 等格式）
- 支持多家 AI 提供商：OpenAI、TogetherAI、Groq、xAI、OpenRouter、Ollama、LM Studio 及自定义 OpenAI 兼容端点
- 提供 `aicommits` 与 `aic` 两个命令别名，支持 git commit 透传参数（--all 等）
- git hook 集成（prepare-commit-msg）
- 配置文件与命令行参数/环境变量多级配置

## OHOS 适配
- **零依赖 Node.js CLI**：npm 发布包已包含打包后的 `dist/cli.mjs`，无编译步骤，直接作为 application 打包（libexec + bin 启动脚本）。
- **运行时依赖 node**：启动脚本 `exec node <libexec>/dist/cli.mjs "$@"`，需系统 node（hnp node v24.13.0 已验证）。
- **npm/node 环境限制**：本机 node 在 HOME 未正确设置的环境变量下会崩溃（Signal 5），构建与运行需干净环境（`env -i` + HOME/TMPDIR）。

## 依赖关系
- 运行时：node（系统 hnp 提供），零 npm 依赖
- 编译：无（npm tarball 即最终产物）

## 参考资料
- 上游仓库：https://github.com/Nutlope/aicommits
- npm：https://www.npmjs.com/package/aicommits
- 版本：3.4.0（MIT）
