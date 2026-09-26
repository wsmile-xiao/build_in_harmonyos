# libprotoc 31.1 编译笔记

## 编译信息
- **软件**: libprotoc（Protocol Buffers 编译器库）
- **版本**: 31.1（上游 protobuf 6.31.1）
- **上游仓库**: https://github.com/protocolbuffers/protobuf
- **编译系统**: CMake
- **编译日期**: 2026-09-22
- **状态**: built

## 背景：为什么源码目录是 protobuf

`libprotoc` **没有独立的上游仓库**。它是 Protocol Buffers 项目里 `cmake/libprotoc.cmake`
定义的一个 CMake 库目标，源码位于 `src/google/protobuf/compiler`：

```cmake
add_library(libprotoc ${protobuf_SHARED_OR_STATIC} ${libprotoc_srcs} ...)
target_link_libraries(libprotoc PRIVATE libprotobuf)
target_link_libraries(libprotoc PUBLIC  libupb ${protobuf_ABSL_USED_TARGETS})
set_target_properties(libprotoc PROPERTIES OUTPUT_NAME ${LIB_PREFIX}protoc)   # libprotoc.a
```

因此配方从 protobuf 官方 31.1 release 源码包构建，最终**只交付 libprotoc**。

## 交付内容（libprotoc 专用包）

| 产物 | 说明 |
|---|---|
| `libprotoc.a` | 交付目标（编译器库） |
| `libprotobuf.a` | 必需：libprotoc 以 PRIVATE 链接 |
| `libupb.a` | 必需：libprotoc 以 PUBLIC 链接 |
| `libprotobuf-lite.a` | 上游 export 集合成员，随之安装 |
| `include/` + `lib/cmake/protobuf/` | 公共头文件与 CMake 配置，供 `find_package` 消费 |

**不含** `protoc` 命令行工具及 `protoc-gen-*` 插件（仅在构建期作测试脚手架，打包前剥离）。

依赖闭环证据：`libprotoc.a` 单独存在 1313 个未定义符号，必须随运行时库与头文件一同交付。

## 编译步骤

```bash
python3 scripts/ohc-run.py conan-verify libprotoc 31.1
```

关键 CMake 选项：
- `protobuf_BUILD_LIBPROTOC=ON`（31.1 默认 OFF，须显式开启）
- `protobuf_BUILD_PROTOC_BINARIES=ON`（上游要求：开启测试即必须有可运行的 protoc）
- `protobuf_BUILD_TESTS=ON`（执行上游测试套件）
- `protobuf_LOCAL_DEPENDENCIES_ONLY=ON`（只用已发布的 conan 依赖）

## 上游测试（实际执行）

命令：`ctest --parallel 20 --output-on-failure --no-tests=error`（recipe `build()` 内自动执行）

| # | 用例名 | 结果 | 用例数 | 通过 | 跳过 | 耗时 |
|---|---|---|---|---|---|---|
| 1 | lite-test | Passed | 104 | 104 | 0 | ~0.4s |
| 2 | lazily-build-dependencies-test | Passed | — | — | — | ~0.1s |
| 3 | upb-test | Passed | 139 | 139 | 0 | ~11.8s |
| 4 | full-test | Passed | 4402 | 4390 | 12 | ~82s |
| | **合计** | **4/4** | **4645** | **4633** | **12** | **~95s** |

日志：`reports/conan-create.log`；CTest 原始日志见 conan 构建目录
`Testing/Temporary/LastTest.log`。

12 个 SKIPPED 为上游按编译配置条件跳过（如 `ArenaTest.SpaceReusePoisonsAndUnpoisonsMemory`、
`PortTest.ProtobufAssume`、`MicroStringTest.PoisonsTheUnusedCapacity`），非环境失败。

### HarmonyOS 特有测试（新增）

`test_package/test_ohos_runtime.cpp` —— CTest 名 `libprotoc_ohos_runtime`，**PASS**：

- libprotoc 在 OHOS musl 运行时导入 schema 并建立可查询的描述符池
- 缺失文件的诊断经 musl errno/strerror 路径正常上报（不崩溃）
- 描述符 proto 的 TextFormat 往返回环

> 该测试是**在上游测试统计之外的额外检查**，不替代上游测试统计。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `ResolvePluginPathForTest` 未定义，full-test 编译失败 | protobuf 31.1 不内嵌 googletest，33.6 补丁中该 hunk 打到 `googletest/` 目录，31.1 源码树没有该目录 | 补齐 `command_line_interface_unittest.cc` 的 hunk（helper 函数 + 调用点） |
| 2 | full-test 崩溃：`Failed to create tmp file /tmp/gtest_captured_stream.XXXXXX` | googletest 硬编码 `/tmp`，HarmonyOS 用户 shell 无可用 `/tmp`（E002） | 新增 `0002-googletest-honor-tmpdir.patch`，改为 `testing::TempDir()` 并尊重 `TEST_TMPDIR` |
| 3 | googletest 补丁 `source/target file does not exist` | conandata 的键名写成 `patch_base_path`，被 `patch()` 的 `**kwargs` 吞掉，未生效 | 改用正确键名 `base_path: "googletest/googletest"` |
| 4 | `find_program(protobuf_PROTOC_EXE protoc REQUIRED)` 失败 | 关闭 `protobuf_BUILD_PROTOC_BINARIES` 后，上游测试仍需 protoc 生成测试 proto | 打开该选项，protoc 仅作测试脚手架，打包阶段剥离 |
| 5 | 消费者 `find_package(Protobuf CONFIG)` 报 `protobuf::protoc` 引用不存在的文件 | 剥离 `bin/` 后，导出配置仍引用 `protobuf::protoc` / `protoc-gen-*` | `package()` 中同步清理 `protobuf-targets.cmake` 与 `protobuf-targets-release.cmake` 里的工具目标 |
| 6 | test_package 用例报 usage 错误 | `add_test` 未传入测试所需的 `<source_dir>` 参数 | 在 `add_test` 中补 `${CMAKE_CURRENT_SOURCE_DIR}` |

## 源码修改

两个补丁（均在 `patches/`，作用于上游源码，无本项目私有 hack）：

1. `0001-use-local-googletest-source.patch`（5 文件）
   - `cmake/abseil-cpp.cmake`：从固定 abseil 源构建测试所需的 `absl::scoped_mock_log`
   - `cmake/gtest.cmake`：使用本地 googletest 源（`protobuf_GTEST_SOURCE_DIR`）
   - `cmake/protobuf-generate.cmake`：交叉构建时区分宿主 protoc
   - `cmake/tests.cmake`：OHOS 下测试插件按相对路径解析；宿主插件目录支持
   - `src/google/protobuf/compiler/command_line_interface_unittest.cc`：补 `ResolvePluginPathForTest` helper
2. `0002-googletest-honor-tmpdir.patch`（1 文件）
   - googletest `src/gtest-port.cc`：`/tmp/` → `TempDir()`，尊重 `TEST_TMPDIR`/`TMPDIR`

## 依赖版本

- abseil-cpp/20260107.1（community, transitive_headers=True）
- zlib/1.3.1
- 构建工具：clang 15.0.4、cmake 4.1.2、make 4.4.1、pkg-config 0.29.2

## 验证结果

```bash
# 门禁
conan-verify: G0/G1/G2/G3/G4/L2/L4/L5 全部 PASS → Verdict: PASS

# test_package（6/6）
1/6 libprotoc_descriptor    Passed
2/6 libprotoc_pool          Passed
3/6 libprotoc_importer      Passed
4/6 libprotoc_diagnostics   Passed
5/6 libprotoc_roundtrip     Passed
6/6 libprotoc_ohos_runtime  Passed   ← 鸿蒙特有
100% tests passed, 0 tests failed out of 6
```

## 注意事项

- 本包**只交付 libprotoc 及其依赖**，不包含 `protoc` 命令行工具。若需 CLI，请使用
  `protobuf/33.6.1` 或 `protobuf/34.1`。
- 包内 `lib/cmake/protobuf/` 的导出已剔除工具目标，`find_package(Protobuf CONFIG)`
  可正常解析 `protobuf::libprotoc`。
---

**编译结束**: 2026-09-22 10:20
**最终状态**: built
