# json-c 0.18 适配笔记

## 构建系统
- json-c 0.18 使用 CMake (非 autotools)
- CMake 最低版本要求: 3.9
- 项目是纯 C 库，无外部依赖

## 编译过程
1. `cmake .. -DCMAKE_INSTALL_PREFIX=$PREFIX -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON -DBUILD_SHARED_LIBS=ON`
2. `make -j2` — 全部目标编译成功
3. `make install DESTDIR=$TEST_PREFIX` — 安装成功

## 测试
- ctest 全部失败，原因是 HarmonyOS 动态链接器不支持相对 RPATH (`../libjson-c.so`)
- 直接设置 `LD_LIBRARY_PATH` 运行测试可正常通过
- 这是平台 RPATH 限制，非代码问题

## 产物
- libjson-c.so (共享库)
- libjson-c.a (静态库)
- 头文件: json-c/json.h, json_object.h, json_tokener.h 等
- pkg-config: json-c.pc
- CMake config: json-c-config.cmake

## Conan 配方
- 使用 CMake 构建 (conan.tools.cmake)
- 默认 shared=True (json-c 非系统同名库，可动态链接)
- 无外部依赖
---

**编译结束**: 2026-07-14 10:34
**最终状态**: built
