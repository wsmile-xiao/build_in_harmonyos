# captive 1.0.0 适配笔记

- 软件: captive-browser（captive 门户浏览器守护进程）
- 上游: https://github.com/pacoorozco/captive-browser (tag v1.0.0)
- 语言/构建: Go 1.24.1 / go build
- 状态: published
- 适配日期: 2026-08-28

## 构建环境

- 目标平台: HarmonyOS PC (aarch64)
- 交叉编译: GOOS=linux GOARCH=arm64 CGO_ENABLED=0
- Go SDK: go1.24.1.linux-arm64（aliyun 镜像下载）
- Conan 版本: 2.29.1

## 关键适配点

1. **Go SDK 与产物签名**：HarmonyOS PC 上 Go SDK 工具链 ELF 和最终二进制都必须用
   `binary-sign-tool sign -selfSign 1 -signAlg SHA256withECDSA` 签名才能执行。
2. **链接输出位置**：`go build -o` 输出到 HMDFS 会报 `mapping output file failed:
   permission denied`，需先输出到可写工作区（如 /data/storage/.../link-out）再复制。
3. **DNS 重定向实现**：Go 1.24 标准库 resolver 对假 DNS 校验严格（EDNS、A+AAAA 双查询），
   为满足"强制经上游 DNS 解析"且测试确定，将 UpstreamResolver 重写为纯 Go 裸 UDP
   DNS 客户端（查询与解析全自控）。
4. **OHOS patch 行为**：本平台 `patch --dry-run` 仍会真实创建新文件，会污染 .orig
   基线目录，导致 refresh-patch 误判新增文件（详见 knowledge）。

## 补丁列表

- 0001-core.go.patch: 新增 core.go（LoadConfig/ExtractDHCPDNS/StartSocksProxy/Execute +
  纯 Go UpstreamResolver 裸 UDP DNS 客户端）
- 0002-core_test.go.patch: 新增 21 个功能测试（DHCP DNS 提取、TOML 配置、DNS 解析器、
  SOCKS5 代理端到端、Execute 编排）
- 0003-main.go.patch: 重构 main.go，抽离共享逻辑至 core.go；新增 --version/--help
- 0004-udp_smoke_test.go.patch: 新增 connected-UDP 往返冒烟测试

## 依赖版本

- Go 工具链: 1.24.1（go.mod 要求 go 1.24.1）
- 无第三方 Conan 依赖（纯 Go module 依赖）

## 测试情况

- 上游 v1.0.0 tag 与 main 分支均无 _test.go（已双重核查）
- 新增 22 个 Go 功能测试全部通过（test-report.md 详述）
- test_package 冒烟测试 4 项断言全部通过

## 最终状态

- status: published
- conan-verify: Verdict PASS（G0-G4 全过；L2/L4/L5 无 cache 路径跳过）
- .ci-result.json: exit_code 0（W3 本地 CI 模拟通过）
