# adbtuifm 0.5.8 HarmonyOS PC 适配说明

## 软件说明

adbtuifm 是基于终端界面的 ADB 文件管理工具，使用 Go 开发。

## HarmonyOS PC 适配

- 使用 Go 工具链构建
- 设置 CGO_ENABLED=0
- HarmonyOS PC 使用 GOOS=linux、GOARCH=arm64
- 使用独立可写 Go workspace，避免 HMDFS 构建限制
- 对 Go SDK 及最终 ELF 进行 HarmonyOS 签名
- 无额外 Conan 依赖
- 无 Patch

## 测试

上游未提供 *_test.go 测试文件。

新增 test_package 非交互冒烟测试，共 3 个断言：

- --help 输出包含 --remote
- --help 输出包含 --local
- 非法 --local 路径输出 Invalid local path

本地 conan-verify 已通过 G1、G2、G3，并完成 G4、L2、L4、L5 检查。
