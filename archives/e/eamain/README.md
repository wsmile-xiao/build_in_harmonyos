# eamain

EAMain — Electronic Arts 跨平台 main 入口与命令行解析库（BSD-3-Clause）。

- 上游：https://github.com/electronicarts/EAMain（commit 24ca8bf，官方 codeload 源）
- 版本：0.0.0-24ca8bf
- 构建系统：CMake（静态库，R26）
- 状态：built（本地 conan create + test_package 验证通过，R02 依赖发布后恢复交付）

## 依赖（均已发布 ohpcd，R02 conan download 实测可消费）

- eabase/0699a15（header-only）
- eaassert/0.0.0-e5e1812
- eastdc/0.0.0-fbcc34e
- eathread/0.0.0-f3c6c54

## OHOS 适配要点

1. 官方 release tar 不含 test/packages submodule，顶层 CMakeLists 的
   `include(CommonCppFlags)` 缺失 → 补丁 `0001-remove-submodule-commoncppflags.patch`
   移除该 include（等价编译标志由 Conan toolchain 提供）。
2. 上游声明 `cmake_minimum_required(VERSION 3.1)`，CMake 4.x 已移除 <3.5 兼容 →
   补丁 `0002-bump-cmake-minimum.patch` 提升至 3.5。
3. EAStdC 依赖链要求 user-provided 调试 operator new/delete，消费者测试需提供
   转发实现（test_package/ea_allocator_impl.cpp，与 eastdc 同款）。

## 测试

- 上游 CTest：EAMainTestRuns 1/1 通过（82 处 EAMAIN_TEST 宏断言）
- 鸿蒙专项：OHOS-EAMAIN-TEST PASS
- 消费者验证：test_package test_eamain 1/1 通过（CommandLine/Report/PlatformStartup 公开 API）

## 知识沉淀

- DRAFT-ea-submodule-commoncppflags-remove（配对草稿，随本 PR 交付）
