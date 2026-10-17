# lwrb 3.3.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-27
- 编译器: clang 15.0.4 (aarch64-linux-ohos, OHOS 6.0)
- 状态: built

## 编译步骤

```bash
# Conan 配方驱动（ohos-aarch64 profile, Release）
conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 -r=ohpcd --build=missing
# 内部流程: source() 获取官方 tarball → 恢复 Unity/sanitizers-cmake submodule →
#   补丁 0001-0004 → cmake 库专用构建 (LWRB_BUILD_DEV=OFF) → 上游测试双套件 →
#   install (liblwrb.so + lwrb/lwrb.h) → test_package 消费者
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 官方 tarball 中 third_party/Unity 与 sanitizers-cmake submodule 为空，上游测试项目无法配置（`Unknown CMake command "add_sanitizers"`、`unity.h file not found`） | GitHub archive 不打包 submodule 内容 | 配方 source() 从官方源补齐：Unity v2.7.0 tag 归档 + sanitizers-cmake master 分支归档（仓库无 tag） |
| 2 | test_ex.c（10 个 Unity 用例）从未被任何构建目标引用（`#ifdef TEST` 守卫） | 上游遗留测试文件，未接线 | 补丁 0002 新增 lwrb_test_ex 目标（TEST/LWRB_DEV/LWRB_EXTENDED 定义） |
| 3 | test_ex.c 引用已更名 API：`.r`/`.w` 字段、`lwrb_copy()` 不存在 | 3.3.0 结构体字段更名 r_ptr/w_ptr、函数更名 lwrb_move | 补丁 0003 移植到 3.3.0 公开 API，并校正 overwrite_5 旧语义断言 |
| 4 | test_ex.c 只定义用例无 main()，链接报 `undefined symbol: main` | 上游从未接线，无入口 | 补丁 0004 新增 lwrb_test_ex_main.c runner 派发 10 个用例 |
| 5 | CMake 顶层项目构建 dev 演示可执行并注入 PUBLIC WIN32/_DEBUG/CONSOLE/LWRB_DEV 定义 | 上游 dev 分支设计 | 补丁 0001 增加 LWRB_BUILD_DEV 选项（默认 OFF），库专用构建 + install 规则 |

## 源码修改

| 补丁 | 修改内容 |
|------|----------|
| 0001-CMakeLists-dev-option.patch | 根 CMakeLists: LWRB_BUILD_DEV 选项、库专用 else 分支、install(TARGETS lwrb + lwrb.h) |
| 0002-test-ex-target.patch | lwrb/test/CMakeLists: 新增 lwrb_test_ex 目标 + add_test 注册 |
| 0003-test-ex-api-port.patch | lwrb/test/test_ex.c: r→r_ptr、w→w_ptr、lwrb_copy→lwrb_move，overwrite_5 断言对齐 3.3.0 语义 |
| 0004-lwrb-test-ex-runner.patch | 新增 lwrb/test/lwrb_test_ex_main.c（Unity main + RUN_TEST 派发） |

## 依赖版本

- 无外部 runtime 依赖（纯 C 库）
- 测试框架: Unity 2.7.0、sanitizers-cmake（master 分支，sha256 锁定）

## 验证结果

```bash
# 上游测试（conan create 内 HMBS_UPSTREAM_TEST_RESULT）
# lwrb_test:   5/5 PASS (test.c, 16 断言)
# lwrb_test_ex: 10/10 PASS (test_ex.c, 106 断言)
# discovered=15 executed=15 passed=15 failed=0 → 全量通过率 15/15 = 100%

# 鸿蒙专项 test_ohos（run_ohos_test.py，针对已安装包）
# T1 aarch64 ELF64 PASS / T2 无 glibc PASS / T3 无宿主路径泄漏 PASS /
# T4 真实环形缓冲往返校验 PASS (LWRB_OHOS_OK)

# 消费者 test_package
# PASS: lwrb consumer roundtrip OK (32 bytes written/read, data verified)
```

## 交付物

无独立打包产物（.so 由 Conan 制品仓管理）；packaging/ 目录留空占位。

## 注意事项

- lwrb 环形缓冲容量语义为 size-1（读写指针需保留满/空区分位），消费者写入时不得超过 size-1 字节。
- 知识草稿：DRAFT-lwrb-3.3.0-upstream-test-suite-restore-and-instantiate（官方 tarball 缺测试框架 submodule + 孤儿测试文件三段式实例化）。
---

**编译结束**: 2026-09-27 23:34
**最终状态**: built
