# soplex 3.1.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-16
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos)
- 状态: built

## 编译步骤

```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 -o "&:shared=False"
```

配方要点（conanfile.py generate()）：
- OHOS 平台缓存变量 CMAKE_SYSTEM_NAME=Linux、CMAKE_SYSTEM_PROCESSOR=aarch64（与同源 scip 配方一致）
- GMP=ON、ZLIB=ON（保留有理数求解与 gz 读取能力）
- SANITIZE_UNDEFINED=OFF
- CMAKE_POLICY_VERSION_MINIMUM=3.5：上游 CMakeLists 声明 cmake_minimum_required(3.0.0)，
  CMake 4.x 移除了 <3.5 兼容（首错：Compatibility with CMake < 3.5 has been removed）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan create 配置阶段报 "Compatibility with CMake < 3.5 has been removed" | 上游 cmake_minimum_required(3.0.0)，本机 CMake 4.1.2 移除旧兼容 | generate() 注入 CMAKE_POLICY_VERSION_MINIMUM=3.5（仓库其他配方相同先例） |
| 2 | test_package 消费者断言 objective=200 失败（实际 90） | LPCol(obj,col,upper,lower) 语义下 x0 下界 15、x1 下界 20，最优 x0=15,x1=20→90 | 按真实 LP 语义修正断言为 90 并通过 |

## 源码修改

无补丁（patches/ 为空）。CMake 兼容通过缓存变量解决，不改上游源码。

## 依赖版本

- gmp/6.3.0（rational/exact 求解）
- zlib/1.3.1（gz 流 I/O）

## 验证结果

1. conan create 全绿，test_package 两个用例通过：
   - test_soplex（消费者用例）：公开 API 求解 LP，objective=90 PASS
   - test_ohos_soplex（鸿蒙专项）：aarch64-ohos ELF(e_machine=183) + OPTIMAL + objective=90 ALL PASS
2. 上游 ctest 全量 320/320 通过（37+3 实例 × 8 settings），`100% tests passed`，
   日志 reports/upstream-ctest-run.log SHA-256 5b552e322a6f0281fc46dc9b92b19f32635c6627c74c2e9fa6aebfbfb2683ab8

## 交付物

- libsoplex.a / libsoplex-pic.a（静态库）
- bin/soplex（CLI LP 求解器，命令声明见软件级 archives/s/soplex/commands.json）
- 头文件 include/soplex.h 等（install 到 include/）

## 注意事项

- 上游官网下载曾限流（429），conandata.yml 使用官方 URL 直下 tarball 实测 SHA-256
- 库与 CLI 同为交付物，commands.json 按 R38 在软件级目录声明
---

**编译结束**: 2026-09-16 13:41
**最终状态**: built
