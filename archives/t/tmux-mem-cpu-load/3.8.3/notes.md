# tmux-mem-cpu-load 3.8.3 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-07-15
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 使用 `ohc-run.py conan-init tmux-mem-cpu-load 3.8.3` 生成 Conan 配方骨架。
2. 通过 CMakeToolchain 配置 OHOS aarch64 交叉编译环境。
3. 在 `build()` 中应用 `patches/0001-CMakeLists.txt.patch`，让上游 CMake 在 OHOS/HarmonyOS 平台复用 Linux 的 CPU、内存和 load 源文件。
4. 执行 `ohc-run.py conan-verify tmux-mem-cpu-load 3.8.3` 进行 Conan 配方验证。
5. 执行 `ohc-run.py finish tmux-mem-cpu-load 3.8.3 built` 完成归档收尾和本地 CI 模拟。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 CMake 不识别 OHOS/HarmonyOS 平台 | 原始平台分支仅覆盖 Linux、Darwin、FreeBSD、OpenBSD 等系统名 | 添加 OHOS/HarmonyOS 分支，复用 Linux 源码路径 |
| 2 | test_package 在交叉编译场景无法运行目标二进制 | OHOS aarch64 产物不能在构建机直接执行 | 交叉编译时验证包内可执行文件存在；本机运行时通过 `test_cli.py` 执行 `--help` 和无参数烟雾测试 |

## 源码修改

- `patches/0001-CMakeLists.txt.patch`: 为 `CMakeLists.txt` 添加 OHOS/HarmonyOS 平台检测分支，并设置 `METER_SOURCES` 为 `linux/memory.cc`、`linux/cpu.cc` 和 `common/load.cc`。

## 依赖版本

无第三方 Conan 依赖。

## 验证结果

```bash
python3 scripts/ohc-run.py conan-verify tmux-mem-cpu-load 3.8.3
# G1/G2/G3/G4/L2/L4/L5 PASS, conan create PASS

python3 scripts/ohc-run.py finish tmux-mem-cpu-load 3.8.3 built
# W3 本地 CI 模拟 PASS, submit 就绪预检 PASS
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 2.x application 配方 |
| conandata.yml | 官方源码 URL、sha256 和补丁声明 |
| patches/0001-CMakeLists.txt.patch | OHOS/HarmonyOS CMake 平台适配补丁 |
| test_package/conanfile.py | 消费者侧可执行文件验证 |
| test_package/MANIFEST.yml | 测试清单 |
| commands.json | 命令行工具声明 |

## 注意事项

- 该包为命令行工具，`package_info()` 声明 `bindirs`，不导出库文件。
- `test_cli.py` 在本机运行场景中要求 `--help` 成功；无参数运行用于烟雾覆盖，允许返回非零状态。
---

**编译结束**: 2026-07-15 06:13
**最终状态**: built
