# aiac

Artificial Intelligence Infrastructure-as-Code Generator — 纯 Go 编写的命令行工具，通过 LLM 后端（OpenAI / Azure OpenAI / Amazon Bedrock / Ollama）生成基础设施即代码（Terraform、CloudFormation、Kubernetes 等）模板。

## 概述

aiac 将自然语言提示转换为 IaC 模板。用户描述想要的基础设施，aiac 调用配置的 LLM 后端生成对应代码，支持交互式会话（继续对话、保存、复制到剪贴板）与非交互 quiet 模式。

## 已编译版本

- **5.3.0** (2026-09-03) — Go 1.26.5, CGO_ENABLED=0, static build

## 关键信息

- **源码**: https://github.com/gofireflyio/aiac
- **构建系统**: Go (custom，根包 `go build .`，无 ./cmd 子目录)
- **依赖**: Go ≥ 1.19
- **平台**: linux/arm64 (HarmonyOS/OpenHarmony)

## 鸿蒙适配要点

1. 纯 Go 静态编译：CGO_ENABLED=0、GOOS=linux、GOARCH=arm64，无 cgo 依赖
2. Go linker mmap 在 HMDFS 上失败 → 链接输出放到 ext2 可写分区（`/data/storage/el2/base/haps/entry/files`）
3. OHOS 上每个被 fork/exec 的 ELF 必须用 binary-sign-tool 自签名（含 `.codesign` section），Go SDK 工具链同样需要签名
4. 上游 5.3.0 无任何测试文件（`go test ./...` 每包 `[no test files]`），新增消费者冒烟测试覆盖 `--version` / `--help` / 错误路径

## 依赖关系

- **编译依赖**: Go 1.26.5 SDK（本地未找到时自动下载）
- **运行依赖**: 无（静态二进制，仅依赖 libc 内核接口）

## 参考资料

- **官网**: https://www.firefly.ai/
- **源码仓库**: https://github.com/gofireflyio/aiac
