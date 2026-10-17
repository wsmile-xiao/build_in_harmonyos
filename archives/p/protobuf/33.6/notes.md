# protobuf 33.6 适配笔记

## 编译环境

- 构建系统：CMake 3.16+
- 目标平台：HarmonyOS PC aarch64
- 编译器：OpenHarmony Clang 15.0.4，C++17
- 状态：Windows 主机 OHOS AArch64 交叉构建、打包和消费者链接已完成；2026-08-05 已在 HarmonyOS PC 真机完成上游测试入口、消费者用例和命令行制品验证，尚未发布

## 迁移范围

旧归档只有设备本地 `file://` 源码记录和两个 Android `liblog` 条件补丁，不能由 CI 复现。本次迁移新增正式 Conan recipe、官方源码 SHA256 和真实消费者测试。Protobuf 33.6 原生 CMake 已能识别 OHOS 工具链，不需要源码补丁；OHOS 也不应进入 Android 专用的 `liblog` 链接分支，因此删除旧补丁。

## 依赖版本

| 依赖 | 版本 | 用途 |
|------|------|------|
| abseil-cpp | 20260107.1 | Protobuf 公共头文件和运行库依赖；PR #3963 已合入，recipe revision 为 `57fe1e1fecfc80cf71336fd067d9bae5` |
| zlib | 1.3.1 | gzip 流支持；制品仓 recipe 已发布 |
| utf8_range | 上游内嵌 | 随 Protobuf 源码构建并安装 CMake target，不拆 Conan 依赖 |

上游 `cmake/dependencies.cmake` 记录的 Abseil 基线为 20250512.1；当前依赖使用已经完成本地验证且供 BRPC 精确引用的 20260107.1。网络 FetchContent 被禁用，所有外部依赖均由 Conan 提供。

## 构建与宿主/目标边界

- Windows 构建机只执行 CMake/Ninja；产出的 `protoc` 是 AArch64 目标程序，不在构建机执行。
- Protobuf 库源码已经包含引导所需的生成文件，关闭上游测试后不需要在构建阶段运行目标 `protoc`。
- 下游 BRPC 若要重新生成 `.proto`，必须单独注入经过版本和摘要验证的宿主 `protoc`，不能执行本包中的目标二进制。
- 保留上游安装的 `protobuf-config.cmake`、组件 targets 和 `utf8_range` config，避免把传递依赖降级为裸静态库路径。
- Windows CMake 不把 `CMAKE_SYSTEM_NAME=OHOS` 自动归类为 ELF；安装目标 `protoc` 和 upb 生成器时启用 `CMAKE_BUILD_WITH_INSTALL_RPATH=ON`，避免不受支持的构建/安装 RPATH 重链接。
- 上游生成的 `.pc` 文件默认固化 Windows Conan package 路径；打包阶段将 `prefix` 改为 `${pcfiledir}/../..`，其余目录从 `${prefix}` 派生，保证 pkg-config 元数据可重定位。

## 测试统计

- 上游 `cmake/tests.cmake` 注册 4 个 CTest 入口：`lite-test`、`full-test`、`lazily-build-dependencies-test`、`upb-test`。
- 静态扫描 `src/` 与 `upb/` 下 170 个测试源/头文件，共计 3175 处 `TEST`/`TEST_F`/`TEST_P`/`TYPED_TEST` 宏。
- 交叉构建生成上游 4 个 CTest 入口（`lite-test`、`full-test`、`lazily-build-dependencies-test`、`upb-test`）；这些 AArch64 测试程序不在 Windows 主机执行，改为部署到 HarmonyOS 真机执行。另有 4 个 Conan API 消费者用例、19 个断言和 1 个 `protoc --version` 命令行制品测试，同样在最终 HMDFS 路径签名后于 HarmonyOS 真机执行。
- 完整 `conan create` 成功，生成 10 个 AArch64 静态库及目标端 `protoc`/3 个 upb 代码生成器；消费者 `test_protobuf` 已完成 OHOS AArch64 编译和链接。
- 当前 `conan create` 日志 SHA256 为 `73A5CA20E0AA0A4B8E4408B70305670B7D95A9D82AB0768B2B610FD782F8EEE8`；recipe revision 为 `6454e7a97def3adff15c7bc981208e62`，package ID 为 `a3c051deb139e17bdef4965b92040fa58a49fcaf`，package revision 为 `f2dcb2e4f6f5d3ecbb501b6dce91bc2f`。
- 2026-08-05 使用真机 1 `currentUser@10.62.224.229:2222` 执行补测；SSH 实时探测返回 HarmonyOS HongMeng Kernel 1.12.0 AArch64。补测包 `protobuf-device-rebuilt-tests-20260805-33-6-v6.tar.gz` 本地/远端 SHA256 均为 `8d954c7920f2a136020c6fc19b5968fea574ceb6fe7b7ced4acb1a5b3e14bc6b`。
- 真机 run8 结果：`lite-test` 104/104 通过；`full-test` 4521 项运行，4505 项通过、16 项上游 SKIPPED，进程 rc=0；`lazily-build-dependencies-test` 9/9 通过；`upb-test` 269/269 通过；4 个消费者用例共 19 个断言通过；`protoc --version` 输出 `libprotoc 33.6`；总结果 `OVERALL_RC=0`。

## 路径分类

本次申报路径为路径 A（基础适配）。Protobuf 虽同时交付目标库、目标 `protoc` 编译器和多组代码生成插件，且上游测试规模较大，但人工评审已确认单库适配不满足路径 C 的赛事申报条件，因此不将上述技术复杂度作为路径 C 计分依据。

## CI 取证

- Buildbot #11199（buildid `11779`）未携带 `ci_revision` 或 `ci_source_branch`，`revision` 为空；`checkout-pr` 原始日志 `67925` 明确输出“非 PR 构建，使用 main 分支”。
- 因构建机没有应用 PR #3202 的 diff，随后报告 `archives/p/protobuf/33.6` 缺少 `conanfile.py`、`No packages to build`。该结论只对应当时检出的 `main`，不是当前 PR 配方的构建结果。
- 后续 CI 必须同时满足：Buildbot revision 与当前 PR HEAD 一致、checkout 日志明确应用 PR diff，并实际进入 Protobuf 的 `conan create`；在这些证据出现前不声明 CI 已通过。
- 2026-08-05 复核确认 Abseil PR #3963 已合入，`abseil-cpp/20260107.1` 的 Conan v2 revisions 返回 HTTP 200，recipe revision 为 `57fe1e1fecfc80cf71336fd067d9bae5`；此前由未发布依赖和错误 checkout 引起的旧 CI 失败不代表当前 HEAD。

## 发布边界

当前仅声明本地构建状态。依赖 PR、Protobuf 自身 CI、合并、CNB 上传和下游 BRPC 发布分别核验；任何一个远端门禁未完成时都不写成已发布。
---

**编译结束**: 2026-08-05 08:30
**最终状态**: built

## 2026-08-05 P1 复核补测（run9）

- AI Review P1 指出配方和补丁源码中额外使用 OHOS 专用平台宏。已删除配方侧额外宏注入，补丁源码改为通用 POSIX `TempDir()` 与通用 `ResolvePluginPathForTest()` helper，不再通过平台条件编译切分源码逻辑。
- clean build 复核时发现 upb generated source 规则虽然已使用 host `protoc`/host plugin 执行命令，但 `DEPENDS` 仍可能把目标端 `protoc` / `libupb.a` 纳入隐式依赖并形成 Ninja dependency cycle；已同步切换为 host 可执行文件依赖，并在 CMake 3.27+ 启用 `DEPENDS_EXPLICIT_ONLY`。
- 2026-08-05 使用真机 2 `currentUser@10.62.148.108:2222` 重新执行 v7 补测包：`lite-test` 104/104 通过，`full-test` 4521 项运行、4505 通过、16 项上游 SKIPPED，`lazily-build-dependencies-test` 9/9 通过，`upb-test` 269/269 通过，4 个消费者用例共 19 个断言通过，`protoc --version` 输出 `libprotoc 33.6`，总体 `OVERALL_RC=0`。

## 2026-08-06 真机上游测试复核（run10）

- 为闭环“上游测试用例未在真机上执行”的评审意见，在当前提交 `fa58d34951c112d12514e938e88d47ca6747db8a` 对应的 v7 补测包上重新执行完整目标端验证；真机 1 `10.62.224.229:2222` 当前连接超时，改用可达的真机 2 `currentUser@10.62.148.108:2222`。
- 远端补测包 `protobuf-device-stage-20260805-33-6-v7.tar.gz` SHA256 为 `b97243ce9cf4329e6162e8b1c3abb1caf683b2ab2350cbb9693ac2f6b2c145e2`；完整远端日志 `device-run10-20260806.log` SHA256 为 `025cdacca32325a572014fdc4274d42f8e3e8546098bdefbcdc3e1fddc2788d2`。
- 真机 run10 结果：`lite-test` 104/104 通过；`full-test` 4521 项运行、4505 通过、16 项上游 SKIPPED，进程 rc=0；`lazily-build-dependencies-test` 9/9 通过；`upb-test` 269/269 通过；4 个消费者用例共 19 个断言通过；`protoc --version` 输出 `libprotoc 33.6`；总体 `OVERALL_RC=0`。
- 归档报告：`archives/p/protobuf/33.6/reports/harmonyos-pc-device-run10-20260806.md`。
