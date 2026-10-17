# lerc 4.2.0 适配笔记

## 概述

Esri 的 LERC（Limited Error Raster Compression）有损/无损栅格压缩编解码器，
提供纯 C API（Lerc_c_api.h）。产物 libLerc.so.4。C++17 实现。

## OHOS 适配要点

- **依赖**：无（自包含，仅 libm）。C++ 运行时为 libc++_shared.so，真机加载器
  须能解析（4.1.1 已在真机验证）。
- **构建系统**：cmake，复用 4.1.1 的 OHOS 工具链模式（自发现 ohos.toolchain
  + 裸 cmake 绕开 conan_toolchain，`-DCMAKE_INSTALL_LIBDIR=lib` 强制 64 位
  lib/ 目录）。
- **版本**：CMakeLists `project(Lerc VERSION 4.2.0)`，`set_target_properties
  SOVERSION 4` → libLerc.so.4。Conan `cpp_info.libs = ['Lerc']` 匹配文件名。
- **安装布局**：`PUBLIC_HEADER` = src/LercLib/include/Lerc_c_api.h +
  Lerc_types.h → include/；库 → lib/；Lerc.pc → lib/pkgconfig/。
- **API**：C 面 12 个导出函数（4 个 2D 编解码/查询 + 4 个 _4D 变体 +
  computeCompressedSize/encodeForVersion 系列）。Lerc_types.h 的枚举是 C++ 专属
  （namespace/enum class），C 消费者只可见 lerc_status 与版本宏。

## 测试

test_package 构建两个无需输入数据的可执行文件：

1. `lerc_api_surface` — 对 libLerc.so.4 全部 12 个导出 C 函数生成强制活重定位，
   确保 ABI 完整、无缺符号。
2. `lerc_version_contract` — 校验版本宏（LERC_VERSION_MAJOR=4 / MINOR=2 /
   PATCH=0 / LERC_VERSION_NUMBER=40200 / LERC_AT_LEAST_VERSION 判定）与
   lerc_status==unsigned int 的类型契约。

## 参考

- 官网: https://github.com/Esri/lerc
- 源码: https://github.com/Esri/lerc/archive/refs/tags/v4.2.0.tar.gz
- 任务: 4384（liblerc 4.2.0）
