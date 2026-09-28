# logr 0.8.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-27
- 编译器: clang 15.0.4 (HarmonyOS PC toolchain)
- 状态: built

## 编译步骤
logr 是 C++17 header-only INTERFACE 库。核心 `logr_base` 仅依赖 fmt；
spdlog/glog/log4cplus/boostlog 四类 backend 为可选 INTERFACE 组件。

```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```
- source(): 从 conandata.yml 官方 tag tarball 下载并校验 SHA-256
- generate(): CMakeToolchain 设 `LOGR_*` 各开关；os=OHOS 时显式
  `CMAKE_SYSTEM_NAME=OHOS`、`CMAKE_SYSTEM_PROCESSOR=aarch64`
- build(): cmake configure+build（INTERFACE 目标，无编译产物）
- package(): cmake.install() 装 header + cmake config，删 lib/cmake

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 conanfile 要求 fmt/11.2.0、spdlog/1.15.3、boost/1.83.0、benchmark/1.9.4，ohpcd 无这些精确版本 | 制品仓版本与上游声明的版本不一致 | 对齐可用版本：fmt/12.2.0、spdlog/1.17.0、boost/1.84.0、benchmark/1.9.5（glog/0.7.1、log4cplus/2.1.2、gtest/1.17.0 一致） |
| 2 | 上游 configure() 对 spdlog.no_exceptions / log4cplus.unicode 赋值 | ohpcd 的 spdlog/log4cplus 配方只暴露 shared/fPIC | 移除该两处调参（属上游基准微调，非 OHOS 必需） |
| 3 | conan 默认把 os=OHOS 映射为 CMAKE_SYSTEM_NAME=HarmonyOS，cmake 无同名平台文件 | 缺少 SONAME/平台变量会静默丢 | generate() 中显式指回 OHOS + aarch64（同 fmt 归档） |

## 源码修改
无补丁。header-only 库，上游源码直接用 OHOS 工具链构建。

## 依赖版本
fmt/12.2.0、spdlog/1.17.0、glog/0.7.1、log4cplus/2.1.2、boost/1.84.0、
gtest/1.17.0、benchmark/1.9.5

## 验证结果
见 test_package / MANIFEST.yml / reports/upstream-test-ledger.md
---

**编译结束**: 2026-09-27 22:57
**最终状态**: built
