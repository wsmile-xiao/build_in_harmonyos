# msgpack-tools 0.6 适配笔记

## 上游

- URL: https://github.com/ludocode/msgpack-tools/releases/download/v0.6/msgpack-tools-0.6.tar.gz
- SHA256: `98c8b789dced626b5b48261b047e2124d256e5b5d4fbbabdafe533c0bd712834`
- License: MIT（tarball 内 LICENSE 同时涵盖 contrib/ 捆绑组件）
- 构建: CMake（`cmake_minimum_required(VERSION 2.6)`）
- 上游测试: CTest 26 项（`ctest --show-only`），wrapper 位于 tools/，依赖
  valgrind（无 valgrind 时 wrapper 自动跳过内存检查、仅跑功能断言）

## 依赖策略

上游实际不依赖 msgpack-c：核心转换基于 ludocode/mpack（单头库）+ rapidjson
+ libb64，三者均内置于官方 tarball 的 contrib/ 目录，CMakeLists 以 EXISTS
检查存在性、不联网下载。因此 conanfile 无 requires / tool_requires，不构成
vendoring（使用官方发布制品原样构建）。

## 鸿蒙适配要点

1. **CMAKE_SYSTEM_NAME=Linux**（知识 E092）：OHOS 适配版 conan 默认映射
   HarmonyOS，上游/mpack 的 CMakeLists 无 HarmonyOS 分支；HarmonyOS 基于
   Linux 内核，Linux 平台模块可直接使用。同时设
   CMAKE_SYSTEM_PROCESSOR=aarch64。
2. **CMAKE_POLICY_VERSION_MINIMUM=3.5**（知识 E321）：上游声明
   `cmake_minimum_required(VERSION 2.6)`，CMake 4 拒绝兼容 3.5 以下策略
   版本；本包未列入豁免清单，需在 toolchain 传入该变量。
3. **bash shebang / CTest**：上游 26 项测试 wrapper（tools/valgrind.sh、
   tools/test-*.sh）shebang 为 `#!/bin/bash`，鸿蒙 PC 无 /bin/bash。CTest
   以 `sh <wrapper>` 方式运行 wrapper（cmake add_test 传
   shell 路径参数），因此在 build 目录放置转发 sh 的 bash shim 并前置
   PATH，全部测试无改动即可运行。
4. **CONFIG_SHELL**：test_package 沿用仓库惯例
   `/data/service/hnp/bin/bash` 执行 test.sh（mksh 无法执行 ELF）。

## 测试

- 上游 26 项 CTest 在 build() 内全量运行并统计（详见 conanfile.py
  `_run_upstream_tests`），0 failed 方可通过。
- test_package 功能测试：JSON↔MessagePack 正反转换，覆盖整数（含 int64
  边界）/字符串/浮点/布尔/null/数组/map 嵌套/binary/非法输入（损坏
  msgpack、非法 JSON 必须报错退出）。
- test_package 鸿蒙特有测试：两个 CLI 的 ELF64 AArch64（EI_CLASS/EI_DATA/
  e_machine/e_type）、musl 链接（静态或仅 libc.so）、`.codesign` 签名段、
  NEEDED/RPATH 洁净性（无构建机绝对路径、无 glibc/libstdc++ 泄漏）、
  OHOS 上真实 UTF-8 转换。

## 已知限制

- 上游 valgrind 内存检查在鸿蒙上不可用（无 valgrind），wrapper 自动降级
  为功能断言，不影响 26 项测试的运行与判定。
