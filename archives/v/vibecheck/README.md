# vibecheck

vibecheck 是一个跨平台命令行 AI 工具，通过将 commit message 生成外包给 LLM 来自动化
git commit 流程。支持 OpenAI、Gemini、Anthropic、Groq、Grok、Kimi、Qwen、DeepSeek、
Perplexity 与 Ollama 等 provider。

## 功能概述

- `vibecheck commit` — 分析暂存区 diff，调用 LLM 生成符合规范的 commit message
- `vibecheck keys` — 交互式管理各 provider 的 API key（存储于 `~/.vibecheck_keys.json`，显示时掩码）
- `vibecheck models` — 切换/选择各 provider 的模型
- `vibecheck dashboard` — 查看已生成 commit 与节省成本等统计
- `vibecheck upgrade` — 自升级

## OHOS 适配

- 纯 Go CLI，静态构建（CGO_ENABLED=0），可运行于 HarmonyOS PC aarch64。
- 上游官方测试为 `go test -v ./...`（115 个顶层 Test* 函数）。
- hmbs 预检 conan-create 沙盒只注入 cmake/make/ninja/python3，不含 Go 工具链；
  设备无 go 或过旧时，配方自动从 aliyun Go 镜像 bootstrap go >= 1.24 工具链并
  ELF 签名（algernon/alloy 先例），随后真实运行上游 `go test -v ./...`（115 个
  顶层 Test* 函数）。

## 依赖关系

- 编译依赖：Go 工具链（>= 1.24.11）
- 运行依赖：无（纯 Go 静态二进制）

## 参考资料

- 上游源码：https://github.com/rshdhere/vibecheck
- 版本：v1.7.7
- 许可证：MIT
