# Test Report — libidl2 0.8.14

**Date**: 2026-09-18
**Build System**: Autotools（conan create 干净构建，ohos-aarch64 profile）
**Upstream Suite**: 无 make check 目标（tstidl 为 noinst_PROGRAMS，仅随构建编译不执行）

## Test Results

**消费者验证（test_package）**: 通过（OHOS 交叉编译 + 链接成功，测试程序在 CI worker/真机执行）

```text
[100%] Linking C executable test_libidl2
[100%] Built target test_libidl2
```

### 测试说明

1. **上游测试**：libIDL 0.8.14 无 `make check` 目标。唯一测试程序 `tstidl`
   （noinst_PROGRAMS）只随构建编译、不自动执行；本机 macOS 原生构建中手工运行
   `tstidl` 验证 IDL 解析正确（1/1 通过）。
2. **消费者验证（rule12, N>=1）**：test_package/test.c 实质调用库 API
   - `IDL_parse_filename`（解析真实 IDL 源文件）
   - `IDL_tree_walk_in_order`（遍历 AST）
   - `IDL_tree_to_IDL`（AST 反序列化）
   - 断言接口节点存在；OHOS 构建时同时断言 `__OHOS__` 平台宏
3. **本机验证矩阵**：
   - macOS 原生构建：configure + make + tstidl 运行通过（上游测试 1/1）
   - G0 干净构建（clean-verify）：configure / make / install 全通过
   - OHOS 交叉构建（本机 OHOS 5.1.0 SDK 工具链 + 制品仓 glib 二进制）：
     configure（含 guint64 交叉分支补丁）→ make → test_package 编译链接全通过
   - W3 本地 CI 模拟（build_and_test.sh）：100% 通过（L0/L1/L4/L5 全绿）

## 已知限制

- OHOS 测试程序二进制无法在本机（macOS）执行，test_package 运行在 OHOS CI
  worker/真机完成（can_run() 守卫 + user.build:flex_bison_native 模拟 conf 说明见 notes.md）
