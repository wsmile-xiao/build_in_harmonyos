# kdecoration3 6.7.0 适配笔记

## 上游与构建环境

- 上游项目: https://invent.kde.org/plasma/kdecoration
- 上游标签: `v6.7.0`（commit `cabb2f92b3948679c9ba0fd8b8ffb54d43182a9f`）
- 官方源码包: https://download.kde.org/stable/plasma/6.7.0/kdecoration-6.7.0.tar.xz
- 源码 SHA-256: `acfe5657d889bf0dd5b8b50132bbe9c62f48b5074fcba8265a1cb84d6c227b5d`
- 构建系统: CMake，C++20
- 目标平台: HarmonyOS PC，AArch64
- 编译器: HarmonyOS SDK clang/clang++ 15.0.4
- 状态: `built`

## 依赖

- `qtbase/6.11.1`（Qt6 Core、Gui、Test）
- `ki18n/6.26.0`（KF6::I18n）
- `ecm/6.26.0`（构建工具）

## 构建命令

```bash
conan create archives/k/kdecoration3/6.7.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

## HarmonyOS 适配

1. 设置 `KF_IGNORE_PLATFORM_CHECK=TRUE`，允许 KDE 在 HarmonyOS 上配置；同时由 Conan 显式传入 `KDECORATION3_OHOS=ON`，不依赖原生 worker 的 CMake 系统名推断。
2. 跳过 `ki18n_install(po)`；该步骤要求构建环境未提供的 `msgmerge`，不影响 `KF6::I18n` 运行时能力。
3. 显式设置 C++20。Conan toolchain 会监视 CMake 标准变量，因此同时传入 `-std=c++20`。
4. 手动补齐 Qt、KI18n 与 ECM 的 CMake 搜索路径，并将 SDK 的包查找模式从仅 sysroot 调整为 `BOTH`。
5. 将共享库构建输出保持在 `lib/`，并为 HarmonyOS 补上 CMake 缺失的 SONAME 链接参数，避免安装后的公共库依赖构建目录相对路径。
6. 安装库的 RUNPATH 固定为可重定位的 `$ORIGIN`，不泄漏 Conan 缓存绝对路径。
7. 使用无窗口平台插件、隔离的 HOME/XDG 目录运行完整上游 CTest 测试。

## 测试清单

- 上游 CTest: 4 项
  - `appstreamtest`
  - `kdecoration3-decorationButtonTest`
  - `kdecoration3-decorationTest`
  - `kdecoration3-decorationShadowTest`
- Conan `test_package`: 1 项通用消费者测试，验证 `DecorationThemeMetaData`
  五个真实 API 结果。
- HarmonyOS PC 特有测试: 1 项，仅在 OHOS/HarmonyOS 目标构建并执行：
  - 编译期校验 `__OHOS__`、AArch64、64 位小端 ABI；
  - 运行期通过 `dladdr` 与 `RTLD_NOLOAD` 验证
    `libkdecorations3.so.6` 和 `libkdecorations3private.so.2` 的 SONAME 装载；
  - 调用真实 KDecoration3 API 验证 UTF-8 元数据与 `BorderRadius`。

测试结果：上游 CTest 4/4 通过，其中三个 QtTest 程序合计 80/80；
Conan 消费者测试 2/2、通用与鸿蒙专项运行期检查 11/11 通过。将首个
可见名称预期值故意改错后的负向测试按预期失败，确认测试真实依赖库
的行为。

## 预期产物

- `libkdecorations3.so.6.7.0`（SONAME `libkdecorations3.so.6`）
- `libkdecorations3private.so.6.7.0`（SONAME `libkdecorations3private.so.2`）
- `KDecoration3Config.cmake`、版本文件与导出 targets
- `include/KDecoration3/` 公共头文件

## 发现与知识积累

### 对话 #1：配方与测试闭环

- ✅ `knowledge/doc/E301.md`：`CMake.test(cli_args=...)` 会把参数传给构建命令；消费者测试改为显式运行 `ctest`。
- ✅ `knowledge/doc/E298.md`：消费者测试通过 `conanrun` 环境运行，并显式补齐依赖库搜索路径。
- ✅ `knowledge/doc/E383.md`：HarmonyOS 的 CMake 平台规则缺少共享库 SONAME 参数，配方在 toolchain 中补齐。
- ✅ `knowledge/doc/E438.md`：Qt、KI18n 与 ECM 的包配置位于 Conan 缓存外层，需放宽包查找模式并补充 CMake 搜索路径。
- ✅ `knowledge/doc/E537.md`：安装产物必须核验 `DT_NEEDED`、SONAME 和 RUNPATH，避免泄漏 Conan 缓存绝对路径。
---

**编译结束**: 2026-09-09 09:16
**最终状态**: built
