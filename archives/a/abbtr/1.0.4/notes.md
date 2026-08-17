# abbtr 1.0.4 HarmonyOS PC 适配说明

## 软件信息

- 软件：abbtr
- 版本：1.0.4
- 上游：https://github.com/manuwarfare/abbtr
- 许可证：BSD-3-Clause
- 构建系统：Go

## 源码

源码来自上游 v1.0.4 标签。

SHA256：

22746190c644070d2e3550d4b10c53c57a617febc2196e030cf7391adca9fe29

## 依赖

abbtr 仅使用 Go 标准库，go.mod 未声明第三方模块，因此无 Conan 运行时依赖。

程序创建并执行用户规则时会生成 bash 脚本，因此完整规则执行功能依赖目标系统提供 shell/bash 环境。

## HarmonyOS PC 适配

使用仓库已有 Go CLI 的适配方式：

- CGO_ENABLED=0
- GOOS=linux
- GOARCH=arm64
- 使用独立可写目录保存 Go 临时文件和缓存
- 避免在 HMDFS 上直接执行 Go linker 输出
- 对 Go SDK ELF 和最终 abbtr ELF 执行 HarmonyOS binary-sign-tool 签名
未修改上游源码，无补丁。

## 产物

主要产物：

- bin/abbtr
- share/man/man1/abbtr.1
- licenses/LICENSE
- res/README.md

## 测试

上游源码未提供独立 Go 单元测试文件。

test_package 提供消费者视角冒烟测试：

- 实际执行 abbtr -v，确认版本为 1.0.4
- 实际执行 abbtr -h，确认帮助信息可正常输出
- 检查帮助信息包含可用选项

由于 abbtr 启动时会检查 HOME/.local/bin，测试使用独立 HOME 并提前把该目录加入 PATH，避免测试进入交互提示。
