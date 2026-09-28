# volk

## 简介

VOLK（Vector Optimized Library of Kernels）是 GNU Radio 生态的 SIMD 内核库，
提供可移植的矢量优化信号处理内核（复数运算、FFT 辅助、极坐标变换、调制/
解调与纠错码等）以及运行期 CPU 特性分发：同一 kernel 带 generic/neon/
neonv8 等多份实现，运行时按当前 CPU 能力选择最快版本。

本软件条目对应上游 [gnuradio/volk](https://github.com/gnuradio/volk)
（LGPL-3.0-or-later），是 GNU Radio 及各 SDR/物理层栈的核心前置依赖。

## 版本

| 版本 | 状态 | 编译日期 |
|------|------|----------|
| 3.3.0 | built | 2026-09-28 |

> 说明：同目录下 `1.4.350/` 是同名但**完全无关**的历史归档（上游
> `zeux/volk`，Vulkan Overlay Loader），不是 GNU Radio VOLK 的版本，
> 本次适配未改动其内容。

## 依赖

- `fmt/11.1.3`：上游通过 FetchContent 钉 10.2.1，制品仓无该版本；
  取 11.1.3 并使用 fmt 官方兼容开关 `FMT_DEPRECATED_HEAVY_CORE`
  （自 fmt 11 起 `<fmt/core.h>` 不再导出 `fmt::format`）。
- 构建期 Python 依赖 `mako`（recipe 的 `build()` 内确定性安装，CI 可复现）。
- ORC 关闭：制品仓 `orc/0.4.42` 未提供 `orcc` 工具，上游 `FindORC`
  必然失败，故显式 `ENABLE_ORC=OFF`。

## 编译说明

- 构建系统：CMake（Conan `CMakeToolchain` + 上游 `volk_test_all` CTest 套件）。
- 关键 CMake 变量：
  - `ENABLE_TESTING=ON`（构建上游 QA 可执行文件 `volk_test_all`，154 个 CTest 用例）
  - `ENABLE_ORC=OFF`
  - `CMAKE_BUILD_WITH_INSTALL_RPATH=ON`（避免安装期 RPATH 改写使 OHOS
    ELF `.codesign` 失效；安装后仍按 E077 四步流程重签 bin/ 与 lib/）
- 上游 `volk.pc` 内嵌绝对安装前缀，recipe 在 `package()` 中改写为
  `${pcfiledir}` 相对路径，保证 Conan cache 与下游安装可重定位。

## 使用方法

```cmake
find_package(Volk REQUIRED)
target_link_libraries(your_target PRIVATE Volk::volk)
```

```bash
# pkg-config
pkg-config --cflags --libs volk
```

命令行工具：

```bash
volk-config-info --version        # 3.3.0
volk-config-info --machine        # 当前使用的 SIMD 机器
volk-config-info --all-machines   # 构建包含的机器列表
volk-profile                      # 运行内核基准并生成 ~/.volk/volk_config
volk_modtool                      # 生成新的 VOLK 模块骨架
```

## 相关链接

- 社区: https://www.gnuradio.org/
- 源码: https://github.com/gnuradio/volk
