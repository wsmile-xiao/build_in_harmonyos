# mtfmt

`mtfmt`（Mini template formatter）是一个**纯 C** 实现的字符串格式化库，面向嵌入式系统：
实现了 [PEP-3101](https://peps.python.org/pep-3101/) 格式串的一个方言，并附带 .NET
日期时间「标准格式串 / 自定义格式串」子集。它自带不依赖操作系统的内存分配器
（调用方提供内存池），也提供 C++ 头文件包装（`mtfmt.hpp` / `mtfmt::string`）。

- 上游仓库：<https://github.com/MtFmT-Lib/mtfmt>
- 官网 / 文档：<https://mtfmt.cc/mtfmt/>
- 许可证：LGPL-3.0（源码 SPDX `LGPL-3.0`，根目录 `LICENSE` 为 LGPL v3 全文）

## 功能概述

- 无除法/取模的有符号、无符号整数格式化（二进制 / 八进制 / 十进制 / 十六进制）
- 量化值（`q31_t` 等）格式化
- 标准与自定义日期时间格式化（分隔符、项位置）
- 字符串格式化、对齐、填充宽度、符号显示
- C 数组格式化
- 内置堆分配器（`mstr_heap_init`，也可切换到 `malloc`）
- 动态长度字符串（栈上小缓冲区 + 溢出走堆）
- `va_list` 变参接口（`mstr_vformat` / `mstr_ioformat`）
- parser 错误定位与原因

## OHOS / HarmonyOS PC 适配要点

- **零源码改动**：`archives/m/mtfmt/<版本>/patches/` 不创建，全部差异在配方层。
- **安装布局**：上游 `install()` 写死嵌套 `mtfmt/` 前缀与 `mtfmt/lib/static/`，配方在
  `package()` 里拍平为 `include/` + `lib/`，并移除随之失效的 `lib/cmake/`
  （`install(EXPORT)` 内含拍平前的绝对导入路径；conan 消费者改由 CMakeDeps 提供配置）。
- **测试入口**：上游 CMakeLists 的 `enable_testing()`/`add_test()` 整段被注释，唯一注册的
  测试入口是顶层 `Makefile` 的 `make test`；配方在 `build()` 里调用它，测试不过即构建失败。
- **Unity 子模块**：`tests/` 依赖 git 子模块 `thirds/unity`，Release tarball 不含其内容，
  配方按 `v0.1.3` 树内指针从 `conandata.yml` 的 `test_sources.unity` 显式获取（仅测试用）。
- **编译器**：上游 Makefile 默认 `CC=gcc`，本平台须显式传 `CC=<clang>`（设备与 CI worker
  均无 `gcc`）。

## 依赖关系

- 运行 / 编译依赖：**无**（`src/`、`inc/` 只包含 C/C++ 标准头，未引用 libm、iconv、
  pthread 等任何系统库符号）。
- 测试依赖（不进包依赖链）：[Unity](https://github.com/ThrowTheSwitch/Unity) 测试框架。

## 参考资料

- 上游仓库：<https://github.com/MtFmT-Lib/mtfmt>
- PEP-3101：Advanced String Formatting <https://peps.python.org/pep-3101/>
- Conan Center Index 配方（0.1.3 条目，源码 sha256 同源）：
  <https://github.com/conan-io/conan-center-index/blob/master/recipes/mtfmt/all/conandata.yml>
