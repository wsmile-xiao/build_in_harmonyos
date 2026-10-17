# libe57format

libe57format 是 E57 三维点云文件格式的读写库 (上游
asmaloney/libE57Format), 提供易用的 Simple API (扫描点云读写) 与完整
的 Foundation API。

## 功能概述

- E57 文件的读取与写入 (ASTM E57 1.0 标准)
- Simple API: `e57::Writer` / `e57::Reader` 点云扫描读写
- Foundation API: 底层节点树访问
- 版本查询: `e57::Version` (ASTM 版本与库标识)

## OHOS 适配

- 直编构建 (不执行 CMake `project()`, 真机 compiler identification unknown 规避), C++14, 默认静态库 (`shared=False`)
- XML 解析依赖本仓 `xerces-c/3.2.5` (RREV pin 到 ohpcd 已适配修订版)
- 上游 GoogleTest 套件 (43 用例) 在 `build()` 中直编为 testE57 二进制真实运行 (先计数后实跑),
  测试数据随源码拉取官方数据仓
- 上游测试默认的 ASan/UBSan 在 OHOS NDK 下不可用, 直编不启用 sanitizer
- 与 Linux 的差异: 消费者测试执行需经 bash 显式调用 (OHOS 无 /bin/sh)

## 依赖关系

- 编译依赖: xerces-c/3.2.5
- 测试编译依赖 (不传播): gtest/1.17.0.1
- 运行依赖: 无 (静态库, 仅系统 libm/pthread)

## 参考资料

- 上游仓库: https://github.com/asmaloney/libE57Format
- 上游文档: https://asmaloney.github.io/libE57Format-docs/
- 测试数据: https://github.com/asmaloney/libE57Format-test-data
