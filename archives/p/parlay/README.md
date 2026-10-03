# parlay

Enrich SBOMs with data from third party services — Snyk 开源的纯 Go 命令行工具，
输入 CycloneDX/SPDX SBOM，从 ecosyste.ms、Snyk、OpenSSF Scorecard 等外部服务补全包元数据后输出更丰富的 SBOM。

## 概述

parlay 支持 `ecosystems enrich`（许可证/外部链接/维护者等）、`snyk enrich`（漏洞信息，需 SNYK_TOKEN）、
`scorecard enrich`（OpenSSF Scorecard 外部引用）等子命令，SBOM 经 stdin/stdout 管道流转，
可与 Syft、cdxgen、bomber 等工具串联。

## 已编译版本

- **0.11.0** (2026-10-02) — Go 1.24.0, CGO_ENABLED=0, static build

## 关键信息

- **源码**: https://github.com/snyk/parlay
- **构建系统**: Go（custom，根包 `go build .`，main.go 在仓库根）
- **依赖**: Go >= 1.23（go.mod 声明 go 1.23）
- **平台**: linux/arm64（HarmonyOS/OpenHarmony，GOOS=linux，GOARCH=arm64）

## 鸿蒙适配要点

1. 纯 Go 静态编译：CGO_ENABLED=0、GOOS=linux、GOARCH=arm64，无 cgo 依赖
2. Go linker mmap 在 HMDFS 上失败 → 链接输出放到 ext2 可写分区（`/data/storage/el2/base/haps/entry/files`）
3. OHOS 上每个被 fork/exec 的 ELF 必须用 binary-sign-tool 自签名（含 `.codesign` section），Go SDK 工具链同样需要签名
4. 上游 0.11.0 有 13 个 `*_test.go`、72 个 Test 函数；配方在 build() 内真实运行 `go test -v -count=1 ./...`
   并解析 `--- PASS:/--- FAIL:/--- SKIP:` 行输出机器证据；另在 test_package 提供消费者冒烟测试
   （`--version` / `--help` / 无效文件失败闭合 / SBOM 提及）

## 依赖关系

- **编译依赖**: Go 1.24.0 SDK（本地未找到时自动下载）
- **运行依赖**: 无（静态二进制）

## 参考资料

- **源码仓库**: https://github.com/snyk/parlay
