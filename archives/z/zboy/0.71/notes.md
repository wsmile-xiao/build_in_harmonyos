# zBoy 0.71 HarmonyOS 适配笔记

## 源码与依赖

- 上游：SourceForge 官方 `zboy-0.71.tar.xz`
- SHA256：`d359b87e3149418fbe1599247c9ca71e870d213b64a912616ffc6e77d1dff506`
- 许可证：GPL-3.0-or-later
- Conan 依赖：`sdl2/2.30.10`（依赖预检确认已发布）
- 构建：上游 `Makefile.linux`，通过 `PkgConfigDeps` 与 `AutotoolsToolchain` 注入 SDL2 和 Conan 编译器参数；单线程构建以适配 HarmonyOS 文件系统。

## HarmonyOS 变更

1. Makefile 读取 Conan 提供的编译器/参数，以 SDL2 的 `pkg-config --static` 参数链接。
2. `libunzip/Makefile` 改用 `CC` 和 `AR`，移除硬编码 GCC 命令。
3. 增加早期 `--version` 输出，使包管理器可以非交互地执行可执行文件冒烟检查。
4. 仅测试构建启用 `DEBUGSERIAL`：用原版 Game Boy 测试 ROM 的串口文字结果判定结果；正式安装包不包含测试宏。

## 上游测试审计

| 项目 | 清点结果 |
|---|---|
| `tests/` 目录 | 0 |
| `make check` / CTest | 0 个注册入口；`Makefile.linux` 没有测试目标 |
| 官方 CPU 测试套件 | `tools/roms/cpu_instrs/cpu_instrs.gb`；README 描述全部 CPU 指令测试并以串口输出总结果 |
| 官方时序测试套件 | `tools/roms/instr_timing/instr_timing.gb`；README 描述 CPU 指令时序测试并以串口输出 `Passed` 或失败信息 |
| 诊断 ROM | `cpu_instrs/individual/` 下 11 个单项 ROM；上游 README 指定用于重现主套件中的单项失败 |
| 上游测试实测 | 官方 `01-special.gb` 单项诊断 ROM 在原生 OHOS/armv8 Conan 重建中通过；完整 ROM 套件结果见下表 |

ROM 测试使用上游 SDL2 模拟器测试构建，在 SDL dummy 驱动下运行；`DEBUGSERIAL` 将 ROM 写到 Game Boy 串口的字符转发到 stdout，测试脚本等待上游成功标记或失败信息。每套最长 900 秒。

## Conan 消费者测试

- 运行打包二进制 `zboy --version` 并断言输出为 `zBoy 0.71`。
- 运行打包二进制 `zboy --help` 并断言输出包含上游用法。
- HarmonyOS/ARM64 上初始化 SDL 视频、创建窗口/Renderer、创建并更新 RGB565 纹理，然后呈现一帧并关闭资源。
- HarmonyOS 设备上的测试 ELF 使用设备提供的 `binary-sign-tool` 签名临时副本；不改写 Conan 包内文件。

## 构建与设备记录

| 验证项 | 结果 |
|---|---|
| Conan 原生 OHOS 6.0/armv8 `conan create --build=zboy/0.71` | 通过（退出码 0；clang 15；新鲜重建并执行 test_package） |
| 消费者 `zboy --version` / `zboy --help` | 通过（版本与上游帮助标题断言通过） |
| HarmonyOS 专项 SDL 测试 | 通过（真机初始化视频、建窗、创建 Renderer、更新 RGB565 纹理并呈现一帧） |
| 上游 `cpu_instrs/individual/01-special.gb` | 通过（真机串口观察到 `Passed`） |
| 上游完整 `cpu_instrs.gb` | 未完成（真机两次各运行至 900 秒，输出停留在 `01:ok 02:ok 03`，没有报告失败） |
| 上游 `instr_timing.gb` | 未运行（完整 CPU 套件在设备上的运行时间超出本次验证预算） |
| 仓库 W3 本地 CI | 通过（设备端 `setup.sh` 与 `build_and_test.sh` 均通过） |
| 完整 `finish zboy 0.71 built` 流程 | 未全通过：W3 与 Conan 验证通过；之后 W5 检出基线知识图谱 E219/E253/E305 必填字段缺失；临时快照还生成了 `SUMMARY.md` 变更。未修改这些仓库级文件或新增知识草稿。 |

Windows 工作区上的首次 W3 尝试因缺少 `zsh` 未能启动 setup；随后在 HarmonyOS 设备上的隔离仓库快照运行同一 `finish` 工作流，W3 已通过。完整工作流退出码为 1 的原因在上表列出，不能据此声称所有 finish 步骤均通过。
---

**编译结束**: 2026-09-23 23:50
**最终状态**: built
