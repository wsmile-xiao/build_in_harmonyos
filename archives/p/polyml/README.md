# Poly/ML

Poly/ML 是 Standard ML 的编译器和运行时实现，本归档提供其 HarmonyOS PC aarch64 Conan 2 配方。

## 功能概述

- 编译和交互执行 Standard ML 程序。
- 提供 `poly` 运行时、`polyc` 编译驱动和 `polyimport` 自举导入工具。
- 提供上游安装的 `libpolymain` + `libpolyml` 静态运行时/主程序库契约，可通过 Conan `polyml::polyml` target 消费。
- 支持 Standard ML 模块、模式匹配、高阶函数、任意精度整数及运行时垃圾回收。

## OHOS 适配

- 为 GNU `config.guess`/`config.sub` 增加 HarmonyOS triplet 识别。
- 通过 `autoreconf -fi` 从修补后的 `configure.ac` 生成构建脚本，并保存、恢复已适配的 GNU config 脚本。
- `config.status` 在 HarmonyOS 上使用 mode 0700、进程所有且带应用数据 MAC 标签的 `/data/storage/el2/base/cache` 创建私有临时目录，避开 HMDFS 不保留私有目录 mode 的行为。
- `OS.FileSys.tmpName()` 优先使用可写的 `TMPDIR`，避免只读 `/tmp`。
- alternate signal stack 由拥有者线程注销后再释放，避免线程退出阶段的无效内存访问。
- 已知限制：当前用户沙盒拒绝 pathname AF_UNIX `bind()`；对应上游 Test193 按 runner 原生机制记为 N/A，不计为通过。

## 依赖关系

- 编译依赖：`automake/1.18`、`libtool/2.5.4`（Conan `tool_requires`）。
- 编译工具：HarmonyOS 原生 Clang/Clang++、GNU Make。
- 运行依赖：无额外 Conan 运行库依赖；本版本采用静态构建并关闭 GMP 与 X11。

## 参考资料

- 官网：https://polyml.org/
- 源码仓库：https://github.com/polyml/polyml
- v5.9.2 发布页：https://github.com/polyml/polyml/releases/tag/v5.9.2
- Standard ML：https://smlfamily.github.io/
