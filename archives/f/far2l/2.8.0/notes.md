# far2l 2.8.0 适配笔记

## 编译环境
- 构建系统: CMake（纯 CMake，无 autotools）
- 编译日期: 2026-08-16
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 目标平台: HarmonyOS (aarch64, musl libc)
- 状态: built

## 构建配置

far2l 上游提供丰富的编译开关，本适配根据设备环境做如下收敛：

| 开关 | 值 | 理由 |
|------|------|------|
| USEWX | NO | wxWidgets GUI 后端未适配，OHOS 无可运行桌面 |
| TTYX | NO | X11 TTY 扩展不需要 |
| USEUCD | NO | uchardet 编码探测库未适配（archives/ohpcd 无 recipe） |
| NETROCKS | NO | 网络协议插件依赖 samba/nfs/neon/aws-sdk 均未发布 |
| MULTIARC | NO | 归档插件依赖 libarchive（已发布但首轮收敛依赖面） |
| PYTHON | NO | Python 插件默认关闭 |
| TESTING | NO | 上游 smoke 测试需 Go 工具链 + 外网，设备不可跑 |
| LEGACY | NO | 旧版注册表支持关闭 |
| MUSL | YES | 添加 -D__MUSL__ 全局宏，对齐 musl libc 语义 |

## CMake 4.x 兼容

far2l 顶层 CMakeLists.txt 声明 `cmake_minimum_required(VERSION 3.5.0)`，设备 cmake 为 4.1.2。
通过 Conan recipe 中 `tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"]="3.5"` 解决 E103/E187 兼容问题。

## 上游测试

far2l 官方测试位于 `testing/` 目录，包含 6 个 smoke 测试用例：
1. `0001-run-and-exit` — 启动后正常退出
2. `0002-copy-files` — 文件复制
3. `0003-move-files` — 文件移动
4. `0004-vt-shell` — VT shell 交互
5. `0005-view-file` — 文件查看
6. `0006-view-file-word-wrap` — 自动换行查看

测试框架为 Go 程序（`testing/far2l-smoke.go`），依赖：
- Go >= 1.18（设备无 go 工具链）
- 外网拉取 `github.com/ActiveState/termest`、`dop251/goja` 等模块
- 写 `/tmp/far2l-smoke/output`（鸿蒙 /tmp 只读）

因此上游 6 个 smoke 测试标记为 **N/A（未运行）**。

## test_package 验证

test_package 提供消费者视角验证：
- `test_far2l.cpp`：验证 far2l 二进制存在、ELF64 格式、AARCH64 机器类型（13 个 CHECK 断言）
- `test_far2l.sh`：验证 ELF 格式 + 运行 `far2l --help` 检查输出包含 `--tty`、`--norgb`、`2.8.0`，并增加 TTY 无头启动测试（R40，验证 VT 后端初始化不崩溃）

通过 `self.run()` 显式调用（R34/L0d/L1e 门禁）。

## 已知限制与残余风险

1. **上游 smoke 测试 N/A**：6 个 Go smoke 测试因设备无 go 工具链且硬编码写 /tmp 而无法运行。
2. **/tmp 只读**：鸿蒙设备 /tmp 目录为只读，far2l 运行时若尝试写入 /tmp（如临时文件、缓存）可能失败。上游 smoke 框架硬编码 `/tmp/far2l-smoke/output`，这是标记 N/A 的原因之一。
3. **HMDFS 运行时风险**：far2l 的文件操作（复制/移动/查看）在 HMDFS 文件系统下可能遇到权限或行为差异。HMDFS 不支持硬链接、mkfifo 等操作，可能影响 far2l 的 pty 管理和 VT shell 交互功能。需在交付阶段进行人工运行时验证。
4. **TTY 无头测试局限性**：test_far2l.sh Test 7 验证 `far2l --tty --norgb` 无头启动不崩溃（segfault/abort 检查），但无法验证完整的 TTY 渲染和 VT 栈交互。真正的 TTY 功能验证需要交互式终端环境。
5. **uchardet 功能降级**：USEUCD=NO 关闭了编码自动探测功能，可能导致非 UTF-8 文件名显示异常。此为功能降级，非编译问题。

## 许可证

far2l 主项目许可证为 GPL-2.0。上游多组件各带独立许可证（LGPL-2.1、MIT、BSD-3-clause 等）。
multiarc 插件捆绑的 UnRAR 源码有自定义许可限制（非 OSI 自由许可），本适配通过 `-DMULTIARC=NO` 规避。

## 源码

- 官方源码 tarball：`https://github.com/elfmz/far2l/archive/refs/tags/v_2.8.0.tar.gz`
- SHA-256：`b0fddad2e3985f245f9e691e23b90fb97f7d29d9a0b131fe686aa3cbb2e4ea01`
- 解压根目录：`far2l-v_2.8.0/`
- 上游 tag：`v_2.8.0`（注意下划线前缀）
