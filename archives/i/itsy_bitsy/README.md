# itsy.bitsy

## 简介

itsy.bitsy 是一个 header-only C++ 位操作库，提供 bit view、bit span、bit vector、
dynamic bitset 和相关算法；上游版本 0.8 使用 CMake 导出 `itsy::bitsy` 目标。

## OHOS 适配要点

- HarmonyOS PC arm64 使用 OHOS clang 15 和 C++17；CMake 平台名设置为 `Linux` 以进入
  上游兼容的 POSIX 分支，实际编译器和目标架构仍为 OHOS/aarch64。
- C++17 的 `bit_span.hpp` 需要 `span-lite/0.11.0`，该依赖通过 Conan 公共依赖传递；
  移除该头路径后编译 `itsy/bit_span.hpp` 直接报 `a span of some sort is required`（设备端负对照）。
- GitHub 源码归档中的 range-v3/span-lite 子模块目录为空，配方在源码阶段按 SHA256
  固定补齐；range-v3 仅用于上游测试。
- 安装配置中的上游 sol2 复制残留已修复，消费者可使用 `find_package(itsy.bitsy)`。
- 设备构建使用 `make -j2`，上游 CTest 以串行 `ctest --output-on-failure` 执行。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| span-lite | 0.11.0 | C++17 `bit_span` 公共依赖 |

## 功能验证

```bash
# profile 必须用绝对路径：相对路径会被 ~/.conan2/profiles 下的同名残留副本截获
conan create archives/i/itsy_bitsy/0.8 \
  -pr:h="$PWD/ci/conan/profiles/ohos-aarch64" \
  -pr:b="$PWD/ci/conan/profiles/ohos-aarch64" --build=missing
```

- 上游正式测试（`tests/`）：CTest `6/6` 通过；两个 Catch2 runtime 驱动各报告 `554` 个逻辑用例、
  `3640828` 条断言（合计 1108 次逻辑用例执行、7281656 条断言）。启用 `examples/` 时另有
  `14/14` 个示例检查通过，完整配置的 CTest 注册数为 `20`。
- 消费者：`test_package` 拆成 5 个独立 CTest 用例（`binary_digits`、`bit_vector`、
  `bit_vector_flip`、`popcount`、`bit_span`），逐条做过“改错期望值→看到真实失败→复原→重跑通过”
  的反向取证，明细见 `0.8/notes.md`。

## 参考

- [源码仓库](https://github.com/ThePhD/itsy_bitsy)
