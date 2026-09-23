# sgc

## 简介

sgc 打包上游 libsigc++，为标准 C++ 提供类型安全的回调框架
(signal/slot 系统)，是 gtkmm-4 相关生态的基础依赖。

- 上游: https://github.com/libsigcplusplus/libsigcplusplus
- 许可证: LGPL-2.1-or-later

## OHOS 适配要点

- **构建系统**: Meson (`cpp_std=c++17`)，产物为 `libsigc-3.0`，
  pkg-config 名 `sigc++-3.0`。
- **依赖**: 无外部运行时依赖。
- **关键适配**: OHOS CI 的 Meson 原生文件中按绝对路径 pin `llvm-ar`，
  避免 `Unknown linker(s)` 失败；`benchmark` 选项关闭 (需 boost 的 opt-in 项)。
- **测试**: 上游 `meson test` 40 个用例在 `build()` 内执行；
  `test_package` 覆盖 signal/slot/emit、断开、bind、trackable。

## 版本

- 3.6.0: 首次适配
