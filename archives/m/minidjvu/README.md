# minidjvu

minidjvu 是一个用于编码、解码和处理黑白 DjVu 文档的 C/C++ 库与命令行工具，支持 PBM、BMP，并可通过 libtiff 支持 TIFF。

## 功能概述

- 提供位图、图像、JB2 与 DjVu 页面处理 API。
- 支持 PBM、BMP、TIFF 与单页 DjVu 的读写转换。
- 提供 `minidjvu` 命令行编码与解码工具。

## HarmonyOS 适配

- 为旧版 GNU `config.guess`/`config.sub` 增加 `aarch64-unknown-linux-ohos` 识别。
- 使用 Conan 注入的 Clang、libc++ 与依赖路径进行原生 HarmonyOS/aarch64 构建。
- 保留上游共享库和命令行工具，新增真实公共 API 测试及 HarmonyOS/aarch64 专项测试。

## 依赖关系

- libtiff 4.7.2（并由 Conan 管理其传递依赖）。
- 系统 libc、libm。

## 参考资料

- 官网：https://minidjvu.sourceforge.net/
- 官方源码：https://sourceforge.net/p/minidjvu/code/
