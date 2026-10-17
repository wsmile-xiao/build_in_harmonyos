# grpc 1.84.0 — HarmonyOS PC 适配笔记

## 概要

| 项 | 值 |
|----|----|
| 上游 | https://github.com/grpc/grpc |
| tag | `v1.84.0` |
| 源码 sha256 | `17a4d25717f4871eb71cfdf191f7491f66a59c8ebc782ab53d52fcbfc478959f` |
| 构建系统 | CMake（≥3.22，`CMakeLists.txt:25`），C++17 |
| 目标 | OHOS / armv8 / clang 15 / libc++ / Release |
| 依赖（全部制品仓） | abseil-cpp/20260107.1、protobuf/33.6、c-ares/1.34.6、re2/2024-04-01、openssl/3.5.6、zlib/1.3.1 |
| 补丁 | 0001（pthread_cancel）、0003（c-ares target）、0004（openssl target）、0005（$TMPDIR） |
| 参考版本 | 1.70.0（已发布）——**本版本逐项重新核验，非复制** |

## 1. 逐项重新核验的结果（1.70.0 → 1.84.0）

### 1.1 五个旧补丁的应用性（实测 `patch -p1 --dry-run`）

| 补丁 | 目标 | 应用结果 | 处置 |
|------|------|----------|------|
| 0001 thd-pthread-cancel | `src/core/util/posix/thd.cc:202` | 干净应用 | **保留** |
| 0002 abseil-cpp-cmake-alias | `cmake/abseil-cpp.cmake:35` | 机械上可应用，**但语义已失效** | **弃用**（见 1.2） |
| 0003 cares-cmake-target | `cmake/cares.cmake:38` | 干净应用 | **保留** |
| 0004 ssl-cmake-target | `cmake/ssl.cmake:61` | 干净应用 | **保留** |
| 0005 tmpfile-tmpdir | `src/core/util/posix/tmpfile.cc:44` | 干净应用 | **保留**（1.84.0 全树仅此一处硬编码 `/tmp`） |

### 1.2 0002 补丁为什么被弃用（重要）

旧补丁用**别名**的方式把制品仓的聚合 target 映射成 absl 的组件 target。
它内置的组件名列表有两个问题：

1. 列表写的是 `absl_check`、`absl_log` 这类**带 `absl_` 前缀**的名字，
   而展开成 `absl::${_c}` 后期望的目标名是 `absl::check`、`absl::log`——
   前缀重复，映射出来的名字与实际被引用的名字不一致。
2. 1.84.0 的 `CMakeLists.txt` 按名引用了 **59 个** `absl::<name>` 组件，
   其中 **9 个不在旧列表里**：
   `charset`、`fixed_array`、`log_entry`、`log_sink`、`log_sink_registry`、
   `overload`、`prefetch`、`string_view`、`strings_internal`。
   （例如 `CMakeLists.txt:3226` 引用 `absl::string_view`。）

一旦 `find_package(abseil-cpp CONFIG QUIET)` 成功，补丁就会**跳过**真正的
`find_package(absl REQUIRED CONFIG)`，而制品仓的 abseil-cpp 包在内置
config 里并未定义这些组件 target → CMake generate 期报
“Target links to absl::string_view but the target was not found”。

**本版本的解法**：制品仓的 abseil-cpp/20260107.1 是以
`ABSL_ENABLE_INSTALL=True` 构建的，包内**自带上游 abslConfig.cmake**
（`<pkg>/lib/cmake/absl/`），该 config 定义了全部真实的 `absl::<组件>`
target。因此配方只设置

```python
tc.variables["absl_DIR"] = os.path.join(abseil.package_folder, "lib", "cmake", "absl")
```

让上游的 `find_package(absl REQUIRED CONFIG)` 正常命中即可——不需要任何
target 别名，且对组件列表的变化天然免疫（组件增删都不需要改配方）。

### 1.3 已移除 / 新增的 CMake 选项

| 选项 | 1.84.0 状态 | 处置 |
|------|-------------|------|
| `gRPC_BUILD_CSHARP_EXT` | **已移除**（全树零命中） | 从配方删除 |
| `gRPC_DOWNLOAD_ARCHIVES` | **新增**，默认 `ON`（`CMakeLists.txt:52`） | 显式 `OFF` |
| `gRPC_USE_SYSTEMD` | **新增**（`cmake/systemd.cmake:15`，默认 AUTO） | 显式 `OFF` |
| `gRPC_ABSL/CARES/RE2/SSL/ZLIB/PROTOBUF_PROVIDER` | 仍在（`CMakeLists.txt:66-89`），取值仅 `module`/`package` | 保持 `package` |
| `gRPC_BUILD_GRPC_{CSHARP,NODE,OBJECTIVE_C,PHP,PYTHON,RUBY}_PLUGIN` | 仍在（`:626-646`） | 保持 `OFF` |
| `gRPC_BUILD_GRPC_CPP_PLUGIN` | 仍在（`:622`） | 保持默认 `ON` |

`gRPC_DOWNLOAD_ARCHIVES` 说明：1.84.0 的六个第三方归档目录
（`cel-spec`/`envoy-api`/`googleapis`/`grpc-proto`/`protoc-gen-validate`/`xds`）
在 tarball 中存在但为空，守卫是 `NOT EXISTS <dir>` 因此默认不会触发下载；
但 `cmake/download_archive.cmake` 用 `file(DOWNLOAD ... TIMEOUT 60)` +
`FATAL_ERROR`，为避免 configure 期引入网络不确定性，仍显式关闭。

### 1.4 C++ 标准

1.84.0 **没有全局 C++ 标准默认值**：`CMAKE_CXX_STANDARD` 只在 Apple 分支
被设置（`CMakeLists.txt:289-293`），其余靠 590 处
`target_compile_features(... cxx_std_17)` 按 target 强制。
配方显式设 `CMAKE_CXX_STANDARD=17` + `CMAKE_CXX_STANDARD_REQUIRED=ON`，
避免交叉工具链下标准漂移。

### 1.5 pthread_cancel

全树**仅一处**调用：`src/core/util/posix/thd.cc:204`，守卫仍是
`#ifndef GPR_ANDROID`（`:202`）。OHOS musl 不提供 `pthread_cancel`，
不处理会在链接期失败。补丁 0001 + 配方注入的 `GPR_NO_PTHREAD_CANCEL`
宏仍然必需且充分（1.84.0 未新增调用点）。

补充：`src/core/util/posix/thd.cc:130` 使用的是两参数
`pthread_setname_np(pthread_self(), buf)` 形式——因为 OHOS clang 的目标三元组
是 `aarch64-linux-ohos`，会定义 `__linux__`，从而命中
`include/grpc/support/port_platform.h:245` 的 musl 分支
（`GPR_LINUX_PTHREAD_NAME`）。这也解释了为什么 `pthread_cancel` 那行会被
编译到。

### 1.6 依赖版本下限

| 依赖 | 约束 | 位置 |
|------|------|------|
| c-ares | **≥ 1.13.0**（唯一硬下限） | `cmake/cares.cmake:38` |
| protobuf / absl / re2 / openssl / zlib | 无版本约束 | `cmake/{protobuf,abseil-cpp,re2,ssl,zlib}.cmake` |

制品仓的 c-ares/1.34.6 满足。`third_party/*` 在 tarball 中均为**空占位目录**，
唯一版本信息在 `MODULE.bazel`（Bazel 路径，仅供参照；其中 protobuf 标为
35.1，而制品仓提供 33.6——若出现 protobuf API 漂移，编译期即可暴露）。

## 2. 构建配置

```
-DCMAKE_CXX_STANDARD=17 -DCMAKE_CXX_STANDARD_REQUIRED=ON
-DgRPC_{ABSL,CARES,PROTOBUF,RE2,SSL,ZLIB}_PROVIDER=package
-DgRPC_BUILD_CODEGEN=ON -DgRPC_BUILD_TESTS=OFF -DgRPC_INSTALL=ON
-DgRPC_BUILD_GRPCPP_OTEL_PLUGIN=OFF
-DgRPC_BUILD_GRPC_{CSHARP,NODE,OBJECTIVE_C,PHP,PYTHON,RUBY}_PLUGIN=OFF
-DgRPC_DOWNLOAD_ARCHIVES=OFF -DgRPC_USE_SYSTEMD=OFF
-DProtobuf_DIR=… -Dutf8_range_DIR=… -Dabsl_DIR=… -DOPENSSL_ROOT_DIR=…
预处理宏：-DGPR_NO_PTHREAD_CANCEL
```

## 3. 宿主工具 / 目标库的区分（专项规则要求）

| 工具 | 归属 | 本配方是否使用 |
|------|------|----------------|
| `protoc` | **HOST** 工具（生成 .pb.cc） | **不需要**——库的 `.pb.cc` 已随源码树提供 |
| `grpc_cpp_plugin` | **HOST** 工具（生成 .grpc.pb.cc） | **不需要**——同上 |
| `libgrpc` / `libgrpc++` / `libgpr` | **TARGET** 库（aarch64） | 构建并安装 |

判定依据（关键）：`CMakeLists.txt` 中的 210 处 proto 代码生成调用
（`protobuf_generate_grpc_cpp_with_import_path_correction`）只被
**两处**引用：

1. `if (gRPC_BUILD_TESTS)` 块内（`CMakeLists.txt:708` 起，例如 `:4877`
   引用 `${_gRPC_PROTO_GENS_DIR}/src/proto/grpc/testing/echo.pb.cc`）；
2. `tools_c` / `tools_cxx` / `plugins` 自定义目标（`:655-663`）。

这两者**都不在默认 ALL 构建里**。函数体本身只是
`add_custom_command(...)` 声明，没有 target 依赖就不会执行。
因此 `gRPC_BUILD_TESTS=OFF` 时，库源码树自带的已生成 `.pb.cc`
直接编译，构建过程**不调用 protoc / grpc_cpp_plugin**，也就不需要提供
在构建主机上可执行的宿主工具。

**注意**：`grpc_cpp_plugin` 本身仍会被构建（`CMakeLists.txt:20230`，
`gRPC_BUILD_GRPC_CPP_PLUGIN` 默认 ON），产物是 **aarch64 目标二进制**，
安装到 `bin/`。它**不能**在构建主机上执行——这是正确的产物语义
（它是给目标机/下游 target 用的），本次构建流程也不会去执行它。

如果将来需要构建 gRPC 自身的测试或 tools 目标（即需要 codegen），
必须额外提供宿主 protoc + 宿主 grpc_cpp_plugin：grpc 在
`CMAKE_CROSSCOMPILING` 下用 `find_program` 查找它们
（`CMakeLists.txt:595`、`cmake/protobuf.cmake:72`），并且**全树没有
`CROSSCOMPILING_EMULATOR` 支持**，不会自动使用刚构建出来的目标二进制。

## 3.1 修正：`third_party/grpc-proto` 不能留空（实测踩到）

先前判断"关闭 `gRPC_BUILD_TESTS` 后原型生成完全不执行"**不完整**：
`CMakeLists.txt:696-703` 在测试块**之外**仍会为三个文件调用
`protobuf_generate_grpc_cpp_with_import_path_correction()`：

```
third_party/grpc-proto/grpc/channelz/v1/channelz.proto
third_party/grpc-proto/grpc/reflection/v1/reflection.proto
third_party/grpc-proto/grpc/reflection/v1alpha/reflection.proto
```

该函数的第一件事就是 `file(COPY ...)`（`CMakeLists.txt:591`），
文件缺失时 CMake **立即报错**：

```
CMake Error at CMakeLists.txt:591 (file):
  file COPY cannot find ".../third_party/grpc-proto/grpc/channelz/v1/channelz.proto"
Call Stack: CMakeLists.txt:696 (protobuf_generate_grpc_cpp_with_import_path_correction)
```

`third_party/grpc-proto` 是 git submodule，发布 tarball 里是**空目录**；
`cmake/download_archive.cmake` 的守卫是 `NOT EXISTS <dir>`，目录存在就不下载，
因此 `gRPC_DOWNLOAD_ARCHIVES` 开关对这里无效。

**处置**：把上游 grpc-proto 仓库的这三个 `.proto` 随配方内置，
路径与上游仓库布局一致：

```
vendored-grpc-proto/grpc/channelz/v1/channelz.proto
vendored-grpc-proto/grpc/reflection/v1/reflection.proto
vendored-grpc-proto/grpc/reflection/v1alpha/reflection.proto
```

在 `build()` 中拷贝到 `third_party/grpc-proto/`，configure 前落地，构建期零网络。

> 早期版本内置的是 `vendored-grpc-proto.tar.gz`（sha256
> `23a79f6e91818dc0a14b31c4abc21da4e6eaa0d69070e673eaadc0c89c3f8356`）。
> 该做法已废弃——原因见 3.3。三个 `.proto` 在两种形式下逐字节一致
> （sha256 见 3.3），因此这次转换不改变任何构建输入。

## 3.2 修正：内置 tarball 必须放进 `export_sources`

第一次带内置 proto 的构建失败于：

```
ConanException: vendored tarball missing:
  .../conan/WIN01/p/grpc324e7ad716b1b/e/vendored-grpc-proto.tar.gz
```

根因：Conan 执行 `build()` 时 **`self.recipe_folder` 指向缓存里的配方目录
（`p/<pkg>/e`）**，不是原始源码目录；未被 `export_sources` 声明的文件
根本不在那里。实测确认：

- `self.recipe_folder` = `.../p/grpc<id>/e`
- `self.export_sources_folder` = `.../p/grpc<id>/es`（导出后可见）

**处置**：在 `export_sources()` 中显式导出这些文件：

```python
def export_sources(self):
    export_conandata_patches(self)
    copy(self, "*",
         src=os.path.join(self.recipe_folder, "vendored-grpc-proto"),
         dst=os.path.join(self.export_sources_folder, "vendored-grpc-proto"))
```

（该属性行为已在设备上用最小样例工程实测确认。
`copy()` 的 `pattern="*"` 是**递归**的——不是逐层匹配，已实测：
导出后 `cache/p/<id>/es/` 下三个 `.proto` 全部按原相对路径落地。）

## 3.3 修正：内置归档会让 CI 的 checkout-pr 直接失败

内置 `.tar.gz` 的版本在 CI 上过不了 PR 检出阶段：

```
missing binary patch data
```

根因不在配方，而在传输层：**GitCode 的 PR `.diff` 不携带二进制补丁载荷**。
二进制文件无法由 `.diff` 重建，检出阶段就失败，Conan 根本没机会运行。
因此这个错误不是 PR 冲突、不是 rebase 问题、也不是 BUILD_ERROR，
反复 rebuild 不会有任何变化。

**处置**：去掉归档，改为普通文本目录（见 3.1）。

转换后的等价性证据（转换前后逐字节比对）：

| 文件 | sha256 |
|---|---|
| `grpc/channelz/v1/channelz.proto` | `9931f5b510a5b440717ce2a1890585b4a0dc19b71320df963e04bccfd3c952a7` |
| `grpc/reflection/v1/reflection.proto` | `92fe8aab9378b0b9807b081de1fc743f847262c1fb6d1ca16501f9e91d450b19` |
| `grpc/reflection/v1alpha/reflection.proto` | `308ce7f1027f59670283454182436729f64acc24ea86167ce3cf21752393ccd4` |

转换后 PR 差分实测：`git diff --binary $(git merge-base main HEAD)` →

- 15 个文件，全部为文本
- `GIT binary patch` 块：**0**
- `Binary files ... differ` 行：**0**

（`vendored-grpc-proto.tar.gz` 在本分支中为新增文件，从新增改为不存在，
因此该路径在 PR 差分中完全不出现，连删除记录都没有。）

## 4. 测试：诚实申报

### 4.1 上游测试（未运行，如实申报）

| 项 | 值 |
|----|----|
| 位置 | `test/cpp`（gtest） |
| 启用条件 | `gRPC_BUILD_TESTS=ON` |
| 本次执行 | **未执行（NOT_RUN）** |

未执行的技术原因：测试目标依赖 210 处 proto 代码生成（见 §3），
需要能在**构建主机**上执行的 `protoc` + `grpc_cpp_plugin`。farm 的
HarmonyOS 构建机上没有这两个宿主工具（设备上 `which protoc` 为空），
且 gRPC 上游 CMake 不提供 `CROSSCOMPILING_EMULATOR` 或 imported-host-tools
机制。要在 Harmony PC 上跑上游测试，需要先为构建机构建 native 的
protoc 1.84.0 配套 grpc_cpp_plugin——这是一个独立的基础设施任务，
不属于本库适配范围。因此如实申报 NOT_RUN，不把未运行的测试计为 PASS。

### 4.2 test_package（已执行，消费者视角）

`test_package/test_grpc.cpp` 是一次**真实的服务端/客户端交互**，
不使用 protobuf 代码生成（用 grpc 公开 C++ API 直接驱动传输层）：

| # | 动作 | 断言 |
|---|------|------|
| 1 | `grpc::Version()` | 返回非空（链接 + 运行时符号解析） |
| 2 | `ServerBuilder::AddListeningPort("127.0.0.1:0")` + `BuildAndStart()` | 返回非空 server 且获得有效端口 |
| 3 | `CreateChannel("127.0.0.1:<port>")` | 返回非空 channel |
| 4 | 轮询 `GetState` 至 `GRPC_CHANNEL_READY`（≤20s） | 通道达到 READY——证明 event engine / resolver / HTTP2 settings 全链路握手在 OHOS 上真实完成 |
| 5 | 指向死端口 `127.0.0.1:1` 的通道 | **不得**报告 READY（负向对照） |
| 6 | `channel.reset()` + `server->Shutdown()` + `Wait()` | 干净关闭，无崩溃 |

由 `enable_testing()` + `add_test` 与 conanfile `test()` 的
`ctest --output-on-failure --no-tests=error` 自动执行。
测试二进制为 aarch64，在 OHOS PC 上原生运行。

> 说明：本测试刻意不生成 protobuf 桩代码。一次真实 RPC 往返同样要在
> §3 所述的同一套传输栈上完成，而测试第 4/5 步正是对该栈的端到端断言；
> 用生成桩代码只会额外引入宿主 protoc 依赖，却不增加对**本库**的覆盖。

## 5. 产物

`lib/libgrpc++.a`、`lib/libgrpc.a`、`lib/libgpr.a`、`include/grpc++/**`、
`include/grpc/**`、`lib/cmake/grpc/gRPCConfig.cmake`（组件丰富，
含 `gRPC::grpc++` 等）、`bin/grpc_cpp_plugin`（aarch64，供下游 target 使用）。

## 6. 参考

- 上一版本配方：`archives/g/grpc/1.70.0/`（已发布，作为演进基线）
- 上游：https://github.com/grpc/grpc
