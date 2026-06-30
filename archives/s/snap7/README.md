# snap7

snap7 是一个以太网通信套件，原生支持与 Siemens S7 系列 PLC 通信。它提供了多平台客户端、服务端和合作方组件，支持 S7 协议的完整功能集。

## 功能概述

- **S7 客户端**: 连接并读写 Siemens S7 PLC 数据区
- **S7 服务端**: 模拟 S7 PLC，可被其他 S7 客户端访问
- **S7 合作方**: 实现两个 TCP 端点之间的 S7 数据交换
- **多语言绑定**: 提供 C/C++、Pascal、C#、Python、Java 等语言的封装

## OHOS 适配要点

- snap7 使用自定义 Makefile 构建（`build/unix/`），非标准 autotools/cmake
- 源码以 .7z 格式分发，需要 7za 工具解压（系统预装 p7zip 16.02）
- HarmonyOS 缺少 `pthread_cancel` 和 `pthread_setcanceltype`，已在源码中禁用线程取消机制
- snap7 是 C++ 库，消费者需要链接 C++ 运行时 (libc++, libc++abi)
- 编译器使用 clang++ 15，归档工具使用 llvm-ar
- 构建为静态库 libsnap7.a (R26: BUILD_SHARED_LIBS=OFF)

## 依赖关系

- **编译依赖**: 无第三方依赖
- **运行依赖**: 无（静态库内嵌所有功能）
- **系统依赖**: libc++, libc++abi (C++ 运行时)

## 参考资料

- 官网: https://snap7.sourceforge.net/
- 源码: https://sourceforge.net/projects/snap7/
- 许可证: LGPL-3.0-or-later
