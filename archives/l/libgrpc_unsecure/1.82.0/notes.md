# libgrpc_unsecure 1.82.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-18
- 编译器: clang/clang++ (Clang 15, OHOS SDK)
- 状态: built（待 CI）

## 背景

gRPC 模块拆分件（任务 #13213）：从 grpc v1.82.0 源码树构建 TLS-free 核心库
`grpc_unsecure`（C 核心）与 `grpc++_unsecure`（C++ 绑定），供只需要非加密
RPC 的下游精确依赖，无需拉取完整 grpc 主件（含 TLS/secure 全量产物的重件）。

**模块拆分复用范式**：核仓 grpc/1.70.0 主件（PR !6943，goblinrs）构建体系
完备（provider=package 接线 + 5 个 OHOS 移植补丁 + notes 详实），本件完整
复用其构建体系，仅改动：
1. 源码版本 1.70.0 → 1.82.0（补丁点在 1.82 中逐项核验同构可移植）
2. 构建目标收敛为 unsecure 闭包（`cmake --build --target` 15 个目标）
3. gRPC_INSTALL=OFF + 手动打包（上游 install 脚本要求全量 target 存在，
   只建闭包时 `cmake.install()` 会失败）
4. gRPC_BUILD_CODEGEN=OFF（unsecure 核心无 codegen 需求：upb 生成源码
   已预生成在 tarball 内；protoc/grpc_cpp_plugin 由 grpc 主件提供）

## 编译步骤

```bash
conan create . -pr:h ~/.conan2/profiles/ohos-aarch64 -pr:b ~/.conan2/profiles/ohos-aarch64 --build=missing
```

配方 generate() 关键设置（承袭 grpc/1.70.0）：
- 全部依赖走制品仓：gRPC_{ABSL,CARES,PROTOBUF,RE2,SSL,ZLIB}_PROVIDER=package
- gRPC_BUILD_CODEGEN=OFF（unsecure 闭包不需要；codegen 插件属主件产物）
- 显式指定依赖 config：Protobuf_DIR / utf8_range_DIR / absl_DIR
- 构建目录改名：cmake_layout(build_folder="cmake-build")（源码根有名为 build 的 Bazel 文件）
- GPR_NO_PTHREAD_CANCEL 特性宏注入（0001 补丁配套）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `absl::overload` / `absl::die_if_null` target not found | 1.70 的 0002 补丁 alias 组件清单不含 1.82 新引用的组件（protobuf-config 依赖 die_if_null；grpc_plugin_support 依赖 overload） | 0002 补丁组件清单扩充：+die_if_null +charset +fixed_array +log_entry/log_sink/log_sink_registry +strings_internal +overload +variant 等（52→64 组件全覆盖） |
| 2 | `CMake.build() got an unexpected keyword argument 'targets'` | conan 2.x 的 CMake helper 不支持 targets 参数 | 改 `self.run(f'cmake --build "{self.build_folder}" --target t1 --target t2 ...')` |
| 3 | test_package CMakeDeps config 报 `protobuf::protobuf` 悬空 | protobuf/33.6 配方 cmake_find_mode=none（不生成 CMakeDeps target），主包 CMakeDeps 自动传播依赖时生成 find_dependency(protobuf) 引用不到 | 主包 package_info 设 cmake_find_mode=none（不发 CMakeDeps config）；test_package 手动链接 .a 清单 + 显式 Protobuf_DIR（对齐 grpc/1.70.0 test_package 范式） |
| 4 | conan create 报 `direct dependency 'protobuf' is not used by any cpp_info.requires` | package_info 手动设置 requires 只列了 abseil/c-ares/zlib，protobuf 未列入 | requirements 保持 protobuf（grpcpp 公开头 include google/protobuf/*.h，transitive），package_info 不再手动设 requires（依赖自动传播） |
| 5 | 测试程序链接 undefined symbol: inflate/deflate（zlib） | grpc 的 cmake/zlib.cmake 用旧式 FindZLIB 模块 target（ZLIB::ZLIB），CMakeDeps registry zlib 导出的是 zlib::zlib | 0006 补丁：接受 registry target 名 |
| 6 | configure 期 file COPY 找不到 third_party/cel-spec 等 proto | gRPC_BUILD_TESTS=ON 触发全量测试 proto 复制链，而 tarball 的测试支撑子模块全为空 | conandata 声明 7 个 pin commit 子模块源，source() 阶段填充 third_party/ 槽位（离线可配） |
| 7 | googleapis/xds 等 get() 解压后混入源码根 | conan 2.x get() 无 dst 参数 | glob 定位 <name>-<sha> 目录 shutil.move 进 third_party/<name> |

## 产物（模块拆分闭包）

- `libgrpc++_unsecure.a`（C++ 绑定）
- `libgrpc_unsecure.a`（C 核心）
- `libgpr.a` + `libupb_{base,descriptor,hash,json,lex,mem,message,mini_descriptor,mini_table,wire,reflection,textformat}_lib.a`（内部静态依赖，消费者需按序链接）
- `libaddress_sorting.a`
- 全量 `include/grpc/` + `include/grpcpp/` 公共头

## 依赖

- abseil-cpp/20260107.1（与 protobuf ABI 一致，transitive headers）
- protobuf/33.6（grpcpp 公开头依赖；cmake_find_mode=none 特化）
- c-ares/1.34.6、zlib/1.3.1（链接符号）
- re2/2024-04-01、openssl/3.5.6（仅配置期 find_package 需要——grpc 顶层 CMakeLists 无条件 find；unsecure 目标链接面不引用其符号）

## 上游测试（rule4 真机执行，2026-09-18 补；口径按审核裁决改全仓申报）

**申报口径（全仓）**：grpc 全仓 gtest 5267 TEST 宏（test/core 3817 + test/cpp 1450，
静态计数）——PR 统计表按此申报（覆盖审核三轮实测 5260/5266/3815 的口径波动）。

**执行口径（模块关联）**：拆分件产物 = grpc_unsecure + grpc++_unsecure target
闭包。执行链接该闭包的全部上游测试程序：**直链 grpc_unsecure 的**
（filter_test_test、party_test）+ **经 grpc_test_util_unsecure 传递链接的**
（arena_promise/arena/basic_work_queue/factory/memory_quota/resource_quota/
thread_pool/uri）——共 10 程序，静态 TEST 宏 134，实测展开 **146 用例**。
其余 5121 宏属 grpc 完整面测试（end2end/xds/grpc++/secure/插件），被测代码
不在本件产物内（PR 正文"减少原因"段逐类定性）。

**真机执行结果（conan create 内建，build 阶段构建+运行，10/10 程序 146/146 用例 100% 通过）**：

| 测试程序 | 实测用例 | 通过 | 失败 | exit |
|----------|---------|------|------|------|
| arena_promise_test | 6 | 6 | 0 | 0 |
| arena_test | 28 | 28 | 0 | 0 |
| basic_work_queue_test | 7 | 7 | 0 | 0 |
| factory_test | 3 | 3 | 0 | 0 |
| memory_quota_test | 20 | 20 | 0 | 0 |
| resource_quota_test | 1 | 1 | 0 | 0 |
| thread_pool_test | 12 | 12 | 0 | 0 |
| uri_test | 29 | 29 | 0 | 0 |
| filter_test_test | 15 | 15 | 0 | 0 |
| party_test | 25 | 25 | 0 | 0 |
| **合计** | **146** | **146** | **0** | - |

**执行机制**（配方 build() 内建，CI 可复现）：
- gRPC_BUILD_TESTS=ON + gRPC_BUILD_CODEGEN=ON（测试程序消费生成的 .grpc.pb.cc；
  本机 native aarch64 OHOS——protoc/grpc_cpp_plugin 编出即原生可跑）
- conandata 声明 7 个测试支撑子模块源（googletest/cel-spec/googleapis/xds/
  opencensus-proto/protoc-gen-validate/envoy-api——tarball 内为空子模块，
  按 v1.82.0 pin commit 填充，离线可配）
- cmake --build --target 收敛 10 测试程序 + grpc_test_util_unsecure
- 逐程序直跑，gtest 汇总解析写 test_results/upstream_tests_summary.txt
- TMPDIR 重定向到 build 目录（OHOS /tmp 只读，0005 补丁配套）

## 源码修改（5 个补丁，全部承袭 grpc/1.70.0 已合入范式）

- 0001-thd-pthread-cancel.patch：src/core/util/posix/thd.cc，OHOS 无 pthread_cancel
- 0002-abseil-cpp-cmake-alias.patch：cmake/abseil-cpp.cmake，absl 组件别名（组件清单扩充至 1.82 需求）
- 0003-cares-cmake-target.patch：cmake/cares.cmake，接受 c-ares::c-ares
- 0004-ssl-cmake-target.patch：cmake/ssl.cmake，接受 openssl::openssl
- 0005-tmpfile-tmpdir.patch：src/core/util/posix/tmpfile.cc，$TMPDIR 支持
- 0006-zlib-cmake-target.patch：cmake/zlib.cmake，接受 zlib::zlib（测试程序链接需要）

## 验证结果

```bash
conan create . -pr:h ~/.conan2/profiles/ohos-aarch64 -pr:b ~/.conan2/profiles/ohos-aarch64 --build=missing
# libgrpc_unsecure/1.82.0 编译通过（0 error），test_package 通过
# 1/1 Test #1: test_package Passed 0.06 sec（100% 通过）
```

真机直跑输出：
```
grpc version: 1.82.0
grpc core version: 55.0.0
test_package: OK（InsecureChannelCredentials 通道构造 + CompletionQueue + Shutdown 全过）
```

上游 unsecure 闭包测试：**146/146（100%）**，见"上游测试"节明细表。
