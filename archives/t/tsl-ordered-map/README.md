# tsl-ordered-map

C++ implementation of a fast hash map and hash set that preserves key insertion
order (header-only, C++11). Maintained by Tessil (same family as robin-map).

## 功能概述

- `tsl::ordered_map` / `tsl::ordered_set` / `tsl::ordered_hash` 容器
- 纯头文件 INTERFACE 库，无运行时链接库
- 通过 CMake 安装 `tsl-ordered-map` 包配置，供下游 `find_package` 使用

## OHOS 适配

- 构建系统：CMake（安装头文件 + Config.cmake，无需编译二进制）
- CMake 包名：`tsl-ordered-map`；目标：`tsl::ordered_map`（与上游一致）
- 无外部库依赖；`settings.os` 兼容 `Linux` 与 `OHOS`（R32，E092）
- 上游测试链接预编译 `Boost::unit_test_framework` → 0001 补丁切换
  header-only Boost.Test（同 robin-map 先例），配合 `-isystem` 引入 Boost 头文件
  与 `BOOST_DISABLE_THREADS`（OHOS pthread 无 `pthread_setcancelstate`）

## 依赖关系

- 编译/安装：cmake
- 运行时：无
- 测试：Boost 1.86.0 源码头文件（配方直接下载并校验 SHA256）

## 验证结果

- OpenHarmony 6.0 aarch64 Conan 构建与安装通过（ohos-aarch64 profile）
- 上游 Boost.Test：86/86 通过（3 个上游空断言用例不计数）
- Conan 消费测试：1/1 通过
- `conan-verify`：G0-G4、L2/L4/L5 全部通过
- 干净 CMake 构建复验：configure/build/install RC=0，产物 include/tsl + share/cmake 齐备

## 参考资料

- 上游：https://github.com/Tessil/ordered-map
- 同族参考：archives/r/robin-map/1.4.1/
