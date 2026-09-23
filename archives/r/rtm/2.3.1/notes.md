# rtm 2.3.1 适配笔记

## 编译环境
- 软件: Realtime Math (rtm)，Nicholas Frechette，SIMD 优化的数学库
- 版本: 2.3.1（官方 tag v2.3.1，commit 745bd25673d93b46941eda55e0993327dbc12b53）
- 官方来源: https://github.com/nfrechette/rtm
- 类型: **纯 header-only C++ 库**（includes/rtm 62 个头文件，无编译产物）
- 构建系统: CMake（project(rtm CXX)），仅用于安装头文件与驱动测试
- 编译器: clang 15.0.4
- 状态: built（conan create 通过 + test_package 实质测试通过）

## 语言预检说明（lang-preflight 误报复查）
- 首次 lang-preflight 判定 mixed（gradle/maven），根因：源码树内
  `tools/android_misc/build.gradle` 与 `tests/main_android/*.java` 属辅助 Android
  示例目录。
- 复核：排除辅助目录后检测结果为 **cpp（CMakeLists.txt project(rtm CXX)，
  源文件 185 个中 cpp 183、主体占比 99%）**。按 R47 边界规则"辅助脚本不算主体"
  正确判定为 cpp，继续适配。

## 编译步骤
- 无 configure/make：header-only 库无编译产物，conan create 仅解包 + 拷贝头文件
- 上游测试：`tests/main_generic`（Catch2 驱动）+ `ctest` 全量运行通过

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | lang-preflight 误判 mixed | 源码树含 tools/android_misc/build.gradle 等辅助 Android 示例 | 按 R47 边界规则复核为 cpp（见上），证据留档 |
| 2 | GitHub 直连超时 | 执行端网络无法直连 github.com | 改用官方 codeload.github.com 下载 tag 源码包，SHA-256 与官方一致 |

## 源码修改
- patches/0001-cmake-CMakePlatforms.cmake.patch: cmake/CMakePlatforms.cmake
  增加 HarmonyOS 平台分支（CMAKE_SYSTEM_NAME=HarmonyOS → 按 Linux 系处理，
  aarch64-linux-ohos 为 Linux 内核）。仅此一处平台识别补丁，header-only
  头文件本体无修改。

## 依赖版本
- 无第三方构建依赖（内嵌 external/catch2 仅用于上游测试）

## 验证结果
- conan create rtm/2.3.1: 通过（test_package 实测 vector_add/点积断言）
- 上游 ctest: 全量通过

## 本地知识查重结论（executor_local_required）
- 知识快照: /storage/Users/currentUser/runnerljs002/knowledge-snapshot-rtm-2.3.1-r01-pc1-58-20260907T153609Z
  （knowledge@main HEAD 720939d0，外部只读稀疏快照）
- **knowledge_decision: reuse_existing（路径 A）**，未创建草稿
- 逐字段适用性验证（等价命中）:
  1. lang-preflight 对辅助目录 build.gradle 的 mixed 误判 → 等价命中
     DRAFT-emio-0.9.0-lang-preflight-aux-cargo-misdetect（根因同为
     _manifest_scan 全文件检索辅助目录 manifest > 顶层 CMakeLists.txt；
     R47 辅助工具不算主体，复核判 cpp 继续适配）
  2. CMakePlatforms.cmake `Unknown platform HarmonyOS!` → 等价命中
     E092 / E140 / E267（CMAKE_SYSTEM_NAME=HarmonyOS 平台识别，
     映射 Linux 系处理）
  3. header-only 配方 copy() 相对 dst 落入 build 目录（test_package 报
     `Imported target includes non-existent path`）→ 等价命中
     DRAFT-boost-te-1.0.0-headeronly-copy-abs-path-commit-incremental
     （同根因同错误签名，须用 package_folder 绝对路径）
  4. JC5 full 模式命中 util-linux-login/.ci-trigger 基线噪声 → 等价命中
     同 DRAFT-boost-te（同库同文件同模式；真实 CI 走 pr.diff 不受影响，
     本地 W3 已临时 index 隔离并复验通过后无条件恢复）
  5. `Package type is 'library', but no 'shared' option declared` →
     等价命中 E283（header-only 应声明 package_type=header-library）
  6. patch_ng 严格 hunk 解析（hunk 行数不精确导致解析失败）→ 等价命中
     E475（exact hunk offsets，用 diff -u 生成规范补丁）
- 结论: 无新增跨库知识价值，走路径 A（常规基础适配），标题前缀【积分赛】
---

**编译结束**: 2026-09-08 02:52
**最终状态**: built
