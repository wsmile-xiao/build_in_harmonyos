# srpc 0.10.4 适配笔记

## 编译环境
- 构建系统: cmake（上游 src/CMakeLists.txt，C++14 + gnu90）
- 编译日期: 2026-10-01
- 编译器: clang/clang++ 15.0.4（aarch64-linux-ohos, musl, libc++）
- 状态: built

## 编译步骤

配方直接走 CMake 路径，无探索阶段的临时命令残留：

```bash
conan create archives/s/srpc/0.10.4 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

配方内部：`source()` 解包上游 v0.10.4 官方 tarball →
`generate()` 注入依赖 include/lib/宏 → `build()` 配置编译主库 →
`_run_upstream_tests()` 单独配置 test/ 子树构建并运行上游 gtest 套件 →
`package()` 安装 + OHOS 共享库签名 → test_package 消费者往返测试。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `NotADirectoryError: b/build/Release` | 上游顶层 `BUILD`（Bazel）与 conan `cmake_layout` 的 `build/` 目录在 HMDFS 大小写不敏感文件系统上同名冲突 | `source()` 中删除不参与 CMake 构建的 `BUILD`/`WORKSPACE`（同 workflow 配方） |
| 2 | `fatal error: 'IOService_linux.h' file not found` | workflow 在 OHOS 上必须用线程池版 IOService（内核 AIO 的 eventfd 通知路径无效），头文件选择宏 `WORKFLOW_USE_THREAD_IOSERVICE` 由 workflow 包的 `cpp_info.defines` 导出；srpc 不走 conan 的 CMakeDeps 目标，直接编译源码，宏不会自动生效 | 配方把依赖 `cpp_info.defines` 显式转成 `-D` 编译宏（C/CXX/\_FLAGS_INIT/test 子树全套）；test_package 同理从依赖导出宏生成 `DEP_DEFINES` |
| 3 | `find_package(Snappy)` / `check_include_file_cxx("workflow/Workflow.h")` / `find_library(lz4)` 探测失败 | 上游用 module 模式探测 + `include "snappy.h"` 裸头名，不吃 conan 的 CMakeDeps config | 注入 `CMAKE_REQUIRED_INCLUDES`/`CMAKE_REQUIRED_FLAGS`/`CMAKE_INCLUDE_PATH`/`CMAKE_LIBRARY_PATH` 与 `-I`/`-L`（CMAKE_\*_FLAGS_INIT、linker flags） |
| 4 | `find_program(PROTOC "protoc")` 找不到 | 依赖的 bin/ 不在 PATH（非 tool_requires） | 显式 `-DPROTOC=<protobuf>/bin/protoc` 与 `-DProtobuf_PROTOC_EXECUTABLE=` |
| 5 | 上游 test/ 子树链接 `-lsnappy -llz4` 失败 | 上游只 `link_directories(SRPC_LIB_DIR WORKFLOW_LIB_DIR Protobuf_LIB_DIR)` | 测试子树配置额外传 `-DCMAKE_EXE_LINKER_FLAGS/-DCMAKE_SHARED_LINKER_FLAGS=-L<各依赖 lib>` |
| 6 | protobuf 版本选择 | 上游 `src/CMakeLists.txt` 固定 `-std=c++14`（追加在 conan 注入的 -std=c++17 之后生效）；protobuf ≥ 4.22 生成的 .pb.cc 依赖 abseil，需 C++17 | 选制品仓 `protobuf/3.17.3`（自带 protoc/libprotoc，无 abseil 依赖） |

## 源码修改

**无补丁**（`patches: {}`）。所有平台差异都通过 conanfile.py 的构建变量注入
解决，未改动上游源码或构建文件。

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| workflow | 1.1.0 | C++ 异步网络引擎（公共头传递） |
| protobuf | 3.17.3 | 消息序列化 + protoc |
| openssl | 3.5.6 | TLS |
| snappy | 1.2.2 | RPCCompressSnappy |
| lz4 | 1.10.0 | RPCCompressLz4 |
| zlib | 1.3.1 | RPCCompressGzip/Zlib |
| gtest | 1.17.0 | 上游单测（test_requires） |

## 验证结果

```text
上游测试（build() 内执行，2 套 gtest 套件）:
  unittest:     exit=0 ok=6 failed=0
  var_unittest: exit=0 ok=2 failed=0
  HMBS_UPSTREAM_TEST_RESULT={"status": "passed", "framework": "gtest",
    "discovered": 8, "executed": 8, "passed": 8, "failed": 0, "skipped": 0}

消费者测试（test_package，protoc + srpc_generator 生成桩代码）:
  SYNC_RESP: Hi back: Hello, srpc!
  ASYNC_RESP: Hi back: async-hello
  COMPRESS_ROUNDTRIP_OK gzip 8192->43
  COMPRESS_ROUNDTRIP_OK snappy 8192->388
  COMPRESS_ROUNDTRIP_OK lz4 8192->43
  CONSUMER_TEST_OK
```

## 交付物

| 文件 | 说明 |
|------|------|
| lib/libsrpc.a | 静态库 |
| lib/libsrpc.so.0.10.4 | 共享库（SONAME libsrpc.so.0，已签名） |
| bin/srpc_generator | protoc 插件（生成 .srpc.h RPC 桩） |
| include/srpc/*.h | 公共头 |

## 注意事项

- 消费者使用 srpc 时必须同时链接 workflow 并带
  `WORKFLOW_USE_THREAD_IOSERVICE` 宏（workflow 包已通过 cpp_info.defines
  导出，CMakeDeps 消费者自动获得）。
- 版本号 = 上游 0.10.4，无适配修复后缀（首次适配）。
---

**编译结束**: 2026-10-01 12:02
**最终状态**: built
