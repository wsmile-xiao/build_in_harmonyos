# ccmeta 1.0.0 — HarmonyOS PC 适配笔记

## 上游信息
- 仓库: https://github.com/Alfredvc/ccmeta
- 版本: 1.0.0 (commit 26e7b1d16436ef568ee7a9ae3cc6706036332ea4)
- 描述: Let Claude Code drive its own meta commands via tmux — Agent Skill framework
- 许可证: MIT
- 语言: Shell (tmux + bash), 无编译步骤

## 适配概述
ccmeta 是一个纯 Shell 的 Agent Skill 集合，包含 `ccmeta.sh` / `ccmeta-dangerous.sh` / `shared/ccmeta-core.sh` 三个脚本，通过 `tmux send-keys` 让 Claude Code 自主驱动 `/clear`、`/compact`、`/model` 等 meta 命令。无 C/C++ 编译，仅需安装脚本到 `share/ccmeta` 并提供 `bin/ccmeta` 入口。

由于是 Shell 项目，HarmonyOS 适配无需源码补丁，重点在：
1. 验证核心脚本语法 (`sh -n`)
2. 正确安装到 Conan package 的 `share/ccmeta` 与 `bin/ccmeta` wrapper
3. 消费测试直接执行 wrapper 与核心脚本语法检查

## 构建系统
- 类型: none (纯脚本安装)
- 源码获取: `conan.tools.files.get` 从 GitHub archive 拉取
- 安装: `conan.tools.files.copy` 复制 `shared/*.sh`, `skills/*/*.sh`, `*.md` 到 `share/ccmeta`
- 包装: 手写 `bin/ccmeta` wrapper，指向 `share/ccmeta/shared/ccmeta-core.sh`

## 依赖
- 运行时依赖: `tmux` (可选，仅在使用时需要；配方不声明，避免引入额外依赖)
- 构建依赖: 无

## HarmonyOS 适配要点
- `build()` 中对 `self.settings.os` 的判断使用 `in ("Linux", "OHOS")`，符合 R32
- 无需设置 `CMAKE_SYSTEM_NAME` 等工具链变量
- `package_info()` 正确声明 `bindirs = ["bin"]`, `libdirs = []`, `includedirs = []`，符合 application 类型要求
- 未引入任何系统同名库，无需 R26 静态限制

## 测试
- 上游无正式测试框架；源码中无 `test` 目录，CI 的 `build()` 通过 `sh -n shared/ccmeta-core.sh` 完成语法校验
- 消费者测试 (`test_package`):
  1. 检查 `share/ccmeta/shared/ccmeta-core.sh` 存在
  2. 执行 `sh -n` 语法检查
  3. 运行 `bin/ccmeta` wrapper，验证输出 `core: OK`

## 已知限制
- `tmux` 在 HarmonyOS PC 的 hnp 环境中可用 (`/data/service/hnp/bin/tmux`)，但 CI 预检不要求实际 tmux 会话，仅校验脚本
- `ccmeta-dangerous` 的高危命令 (`/loop`, `/remote-control` 等) 需用户显式授权，测试仅验证脚本存在与语法

## 验证
- 本地需在 HarmonyOS PC 真机执行 `conan create`，确认:
  - `conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing` 成功
  - `test_package` 输出 `HMBS_TEST_PACKAGE_RESULT` 与 `HMBS_UPSTREAM_TEST_RESULT` (status: no_tests)
