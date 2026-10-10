# mmdbctl

MMDB 文件管理 CLI，支持 MMDB 数据库文件的多种操作（read/import/export/diff/metadata/verify）。

## 功能概述

- `mmdbctl read` — 查询 MMDB 库
- `mmdbctl import` — 从 CSV/TSV/JSON 导入构建 MMDB
- `mmdbctl export` — 导出 MMDB 为 CSV/TSV/JSON
- `mmdbctl diff` — 对比 MMDB 文件
- `mmdbctl verify` — 校验 MMDB 文件
- `mmdbctl metadata` — 查看 MMDB 元数据

## OHOS 适配

- 纯 Go CLI，静态构建（CGO_ENABLED=0），可运行于 HarmonyOS PC aarch64。
- 上游官方测试为 `go test -v ./...`（25 个顶层 Test* 函数）。
- hmbs 预检 conan-create 沙盒只注入 cmake/make/ninja/python3，不含 Go 工具链；
  设备无 go 或过旧时，配方自动从 aliyun Go 镜像 bootstrap go1.26.5 并
  ELF 签名（algernon/alloy/vibecheck 先例），随后真实运行上游 `go test -v ./...`。
- test_package 为免编译 python 消费者测试（alloy/algernon 先例，无需 clang/CMake）。

## 依赖关系

- 编译依赖：Go 工具链（>= 1.24.0，go.mod 要求）
- 运行依赖：无（纯 Go 静态二进制）

## 参考资料

- 上游源码：https://github.com/ipinfo/mmdbctl
- 版本：mmdbctl-1.4.10
- 许可证：Apache-2.0
