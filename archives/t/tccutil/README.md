# tccutil

## 简介

[tccutil](https://github.com/jacobsalmela/tccutil) 是一个 macOS 系统
TCC.db（Transparency, Consent, and Control，辅助功能/隐私权限数据库）的
命令行管理工具，单文件 Python 脚本实现。上游官方源由 Homebrew 收录
（formulae.brew.sh/formula/tccutil），1.5.1 为其最新版本。

## 特性

- 单文件 Python 脚本（约 393 行），无编译过程、无 C 扩展，易于审计
- 支持列出/插入/移除/启用/禁用 TCC 服务条目（--list / --insert / --remove
  / --enable / --disable）
- 支持 --user 操作本地用户 TCC.db（无需 sudo）
- --version / --help 为平台无关能力，任何平台可运行

## HarmonyOS PC 适配

纯 Python 工具，`settings` 仅 `os`/`arch`，无编译器依赖。适配补丁
`patches/0001-tccutil-py-ohos-compat.patch`（portability）：

1. shebang 改为 `python3`（OHOS 无 `python` 命令）
2. `packaging` 依赖回退：OHOS 精简环境可能未安装 packaging 第三方库，
   提供最小版本比较回退类（仅用于 macOS 版本门槛比较，非 macOS 平台这些
   分支不可达）
3. `osx_version` 容错：非 macOS 平台 `platform.mac_ver()[0]` 为空字符串，
   原代码 `Version('')` 抛 InvalidVersion 导致模块 import 即崩；回退
   `version('0.0.0')` 使 macOS 版本门槛分支全部不可达，--version/--help
   等平台无关能力仍可用

**平台限制**：TCC.db 读写为 macOS 系统数据库能力，OHOS 上无该系统数据库，
该部分功能天然不可用（工具固有平台限制）。test_package 验证平台无关的真实
能力（CLI 版本/帮助、模块 API）。

## 测试

上游无任何测试套件（源码仅 5 个文件，CI workflow 只跑 flake8 lint，pytest
步骤被注释）。test_package 提供 3 项消费者断言（--version / --help /
模块 API），并输出 `no_tests` 上游标记，不伪造通过率。
