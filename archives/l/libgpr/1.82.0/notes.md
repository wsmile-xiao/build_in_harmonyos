# libgpr 1.82.0 适配笔记（HarmonyOS PC / aarch64）

## 结论

- **本包是 gRPC 1.82.0 的 `gpr` 组件**（Google Portable Runtime：日志、时间、同步、分配、env/cpu、mpscq、host/port 字符串），即上游 `CMakeLists.txt` 的 `add_library(gpr ...)` 产物。
- **不是 AdaCore 的 libgpr**（那是 GPRbuild 的 GNAT 工程文件库，版本 21–27，无 1.82.0）。
- 交付：`libgpr.a` + grpc 公开头（`include/grpc/impl/codegen/*`、`include/grpc/support/*`）+ 消费者测试。

## 为什么按「模块拆分件」做

仓库已有同族先例：`archives/l/libgrpc_unsecure/1.82.0`（其 manifest 的 `split_targets` 明确含 `gpr`）、`archives/l/libgrpc_authorization_provider/1.82.0`，均在制品仓（`libgrpc_unsecure/1.82.0`）。本包复用同一套 provider 接线与 OHOS 补丁，只把 `_TARGETS` 收敛到 `gpr`。

## 关键事实

1. **源码路径变了**：grpc 1.82 里 gpr 的源码在 `src/core/config/*` 与 `src/core/util/**`（旧的 `src/core/lib/gpr/` 已不存在）。
2. **运行期依赖只有 abseil**：`target_link_libraries(gpr ...)` 是 22 个 `absl::*`；protobuf / c-ares / re2 / openssl / zlib 仅因顶层 `find_package` 被无条件调用而成为**配置期**依赖。
3. **OHOS 缺 `pthread_cancel`**：`src/core/util/posix/thd.cc` 的 `Thread::Kill` 无法实现 → 用构建系统特性宏 `GPR_NO_PTHREAD_CANCEL` 走 `GPR_ANDROID` 同款 stub（补丁 0001，不改源码里的平台名宏观）。
4. **CMakeDeps 目标名桥接**：注册表的 abseil-cpp / c-ares / openssl / zlib 导出的 target 名与 grpc 期望的不一致 → 补丁 0002/0003/0004/0006。
5. **测试子模块**：release tarball 的 `third_party/googletest` 为空，按 grpc v1.82.0 pin 的 commit 填充（本包只需要 googletest）。

## 上游测试

- gpr 自己的单测在 `test/core/util/*.cc`（`time_test`、`host_port_test`、`mpscq_test`、`string_test`、`sync_test`、`time_util_test`…），但它们的链接闭包里有测试专用 `grpc_test_util`，会把**完整 grpc 核心**拉进来——那是 `libgrpc_unsecure` 包的产物，不属于 gpr 拆分件。
- 因此本包构建并运行链接闭包只有 `gpr + absl + gtest` 的那批单测（`_TEST_TARGETS`），真实执行统计写进 `test_package/MANIFEST.yml` 与 PR 正文。

## 验证

- `test_package`：真实调用 `gpr_now`/`gpr_time_add`/`gpr_time_to_millis`/`gpr_time_cmp`/`gpr_malloc`/`gpr_strdup`/`gpr_cpu_num_cores`/`gpr_mu_*`/`gpr_log`，断言后返回非 0 表示失败。
- 本地：`conan create archives/l/libgpr/1.82.0 -pr:h/-pr:b=ohos-aarch64-wsl --build=missing`。