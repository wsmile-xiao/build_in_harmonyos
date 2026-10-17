# apache-arrow 25.0.0 — HarmonyOS PC 适配笔记

## 概要

| 项 | 值 |
|----|----|
| 上游 | https://github.com/apache/arrow |
| tag | `apache-arrow-25.0.0` |
| 源码 sha256 | `7ecdd404862c3d312601457861a11c30bb8f520328693e1323e3db1db985dbe5` |
| 构建系统 | CMake（≥3.25，`cpp/CMakeLists.txt:18`），**C++20** |
| 目标 | OHOS / armv8 / clang 15 / libc++ / Release |
| 依赖 | 无 Conan requires；xsimd 14.2.0 随配方内置（header-only） |
| 补丁 | 0001 / 0002（本版本已修订）/ 0003 / 0004 |
| 上一适配版本 | 24.0.0（本版本为**新版本重新适配**，逐项重新核验） |

## 1. 与 24.0.0 的关键差异（重新核验结果）

### 1.1 C++20 强制位置变化

| | 24.0.0 recipe 注释 | 25.0.0 实测 |
|---|---|---|
| 强制点 | `SetupCxxFlags.cmake:151` | `SetupCxxFlags.cmake:173-180`（`FATAL_ERROR "Cannot set a CMAKE_CXX_STANDARD smaller than 20"`） |

结论不变：`self.settings.compiler.cppstd = "20"` 仍然必需。

### 1.2 选项变化

| 选项 | 25.0.0 状态 |
|------|-------------|
| `ARROW_WITH_PYTHON` / `ARROW_WITH_JAVA` | **根本不是 Arrow 的 CMake 选项**（全树 0 命中）——旧 recipe 里的 `-D` 一直是 CMake 静默忽略的空操作，本配方不再设置 |
| `ARROW_SIMD_LEVEL` / `ARROW_RUNTIME_SIMD_LEVEL` | 仍存在（`DefineOptions.cmake:162-186`），**但不能跳过 xsimd**，见 §1.3 |
| `ARROW_BUILD_TESTS` | 默认 OFF（`DefineOptions.cmake:206-212`） |
| 其余（IPC/COMPUTE/CSV/FILESYSTEM/JSON/MIMALLOC/JEMALLOC/FLIGHT/DATASET/PARQUET/ORC/GANDIVA/CUDA/压缩族） | 全部仍存在，名称未变 |

### 1.3 xsimd 变为**无条件强制依赖**（本版本最重要的新约束）

`cpp/cmake_modules/ThirdpartyToolchain.cmake:2848-2855`：

```cmake
# Xsimd is mandatory as its CPU feature detection is the basis for Arrow CpuInfo
resolve_dependency(xsimd FORCE_ANY_NEWER_VERSION TRUE IS_RUNTIME_DEPENDENCY FALSE
                   REQUIRED_VERSION "14.2.0")
```

`grep SIMD_LEVEL ThirdpartyToolchain.cmake` → **0 命中**，即
`ARROW_SIMD_LEVEL=NONE` **不会**关掉 xsimd。旧 recipe 注释里
"ARROW_SIMD_LEVEL=NONE … avoid fetching xsimd" 的说法从未成立。
而 ohpcd 上**没有** xsimd 包。

**本版本的处置**：xsimd 是 header-only 库（INTERFACE target，
`ThirdpartyToolchain.cmake:2841-2843`），因此把上游 14.2.0 的源码树作为
**纯文本目录** `vendored-xsimd-14.2.0/` 随配方交付，在 `build()` 中拷贝到
构建目录、施加 OHOS 适配、再重打包，并通过 `ARROW_XSIMD_URL` 指向该归档——
configure 阶段**零网络**，也不需要为它新增一个 Conan 包（避免为了一个纯
头文件库引入额外依赖项）。

> **交付形态的更正（诚实记录）**：早期版本交付的是
> `vendored-xsimd-14.2.0.tar.gz`，并声称用 `FETCHCONTENT_SOURCE_DIR_XSIMD`
> 指向解包目录。两点都已作废：
> Arrow 对 xsimd 走的是 `externalproject_add(... URL ...)`
> （`ThirdpartyToolchain.cmake:2830-2835`），**不是 FetchContent**，
> `FETCHCONTENT_SOURCE_DIR_XSIMD` 对它完全无效；唯一受支持的入口是
> `ARROW_XSIMD_URL`（`:813-819`），且该下载会按 `cpp/thirdparty/versions.txt`
> 里的 `ARROW_XSIMD_BUILD_SHA256_CHECKSUM` 校验，所以那一行必须同步更新。
> 至于为什么不再交付归档，见 §1.7。

### 1.4 flatbuffers：**不需要 flatc**（关键跨编译结论）

- `cpp/thirdparty/flatbuffers/` 只有 17 个 `.h`（**无 `src/`、无 `CMakeLists.txt`、无 `flatc`**），
  经 `ThirdpartyToolchain.cmake:370-372` 以 INTERFACE target 引入。
- 生成头文件**已随源码提交**：`cpp/src/generated/{File,Message,Schema,SparseTensor,Tensor,feather}_generated.h`。
- 因此 `ARROW_IPC=ON` **不需要** flatbuffers 编译器，也不需要 flatbuffers Conan 包。

### 1.5 最小核心无宿主代码生成（跨编译安全）

所有会**运行**新构建二进制的 `add_custom_command` 都落在被本配方关闭的模块里：

| 模块 | 位置 | 是否启用 |
|------|------|----------|
| Flight（protoc + grpc plugin） | `cpp/src/arrow/flight/CMakeLists.txt:112,139` | OFF |
| Substrait（protoc） | `ThirdpartyToolchain.cmake:2394,2415,2425` | 不启用 |
| Gandiva（clang→bitcode） | `cpp/src/gandiva/precompiled/CMakeLists.txt:38,44,52` | OFF |
| ORC / gRPC / brotli / protobuf | `ThirdpartyToolchain.cmake` 多处 | 不启用 |

核心路径上唯一的 `add_custom_target(..._merge ALL)`（`BuildUtils.cmake:184-189`）
执行的是 `${CMAKE_AR} -M`（工具链自带工具，非新构建二进制）。

**结论：最小核心（IPC+COMPUTE+CSV+FILESYSTEM）不需要任何宿主代码生成器。**

### 1.6 四个补丁的重新验证

`patch -p1 --dry-run` 实测（25.0.0 源码树）：

| 补丁 | 应用结果 | 偏移 | 处置 |
|------|----------|------|------|
| 0001-setupcxxflags-unknown-processor | 干净应用 | 无 | 保留 |
| 0002-buildutils-ohos-soname | 干净应用 | +1 行 | **本版本已修订**，见下 |
| 0003-ohos-file-io-edge-cases | 干净应用 | `io/file.cc` +6 行；`localfs.cc` 无 | 保留 |
| 0004-vendored-date-tzdir | 干净应用 | 无 | 保留 |

**0002 的修订（诚实记录）**：24.0.0 的补丁条件写的是
`if(CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS")`。但 Conan 的 OHOS profile
设置的是 `CMAKE_SYSTEM_NAME=OHOS`（profile 中 `os=OHOS`），
写成 `HarmonyOS` 时条件**不会命中**，SONAME 也不会被加上。
本版本把条件改为
`if(CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS" OR CMAKE_SYSTEM_NAME STREQUAL "OHOS")`，
两种写法都接受，避免这个静默失效。其余 hunk 内容不变。

### 1.7 交付形态：内置归档会让 CI 的 checkout-pr 直接失败

内置 `.tar.gz` 的版本在 CI 上过不了 PR 检出阶段：

```
missing binary patch data
```

根因不在配方，而在传输层：**GitCode 的 PR `.diff` 不携带二进制补丁载荷**。
二进制文件无法由 `.diff` 重建，检出阶段就失败，Conan 根本没机会运行。
因此这个错误**不是** PR 冲突、**不是** rebase 问题、**也不是** BUILD_ERROR，
反复 rebuild 不会有任何变化。

**处置**：去掉内置归档，改为纯文本目录 `vendored-xsimd-14.2.0/`
（123 个文件，108 个 `.hpp`，全文本）。归档在 `build()` 中由
`_write_deterministic_tarball()` 现场生成——只用 Python 标准库
`tarfile`/`gzip`，**不联网、不调用系统 `tar`**。

确定性打包固定了全部可变输入：

| 项 | 取值 |
|----|------|
| 条目顺序 | 先按路径深度、再按字典序（父目录先于子项） |
| `mtime` | 0 |
| `uid` / `gid` | 0 |
| `uname` / `gname` | 空字符串 |
| 模式 | 目录 `0755`，文件 `0644` |
| gzip 头 `MTIME` | 0 |
| gzip 头 `FNAME` | 不写入（`FLG=0x00`） |

由于 `versions.txt` 里的 checksum 由现场计算的 sha256 写入，确定性并非正确性
的前提；这样做的目的是让同一份源码在任何机器、任何时间都产出同一个 sha256，
便于复现与比对。

**验证证据**（均为实测）：

| 项 | 结果 |
|----|------|
| 同一目录连打两次 | sha256 完全相同（`3c7502d359cf65a7…`） |
| gzip 头 | `MTIME=0`，`FLG=0x00`（无 FNAME） |
| 归档条目 | 134 条，元数据未固定的条目数 = **0** |
| 条目顺序 | 深度+字典序，实测有序 |
| 文件数 | 归档 123 = 源码树 123 |
| **与原始上游归档逐文件比对** | **123/123 内容 sha256 完全一致** |
| OHOS SVE 锚点 | `xsimd_cpu_features_arm.hpp` 中命中 1 次，`_fix_xsimd_sve_probe()` 仍可生效 |
| `conan export` | 导出 123 个文件，`es/` 下 `.tar.gz` 数量 = **0** |
| `git diff --binary $(git merge-base main HEAD)` | 无 `GIT binary patch` 块、无 `Binary files differ` |

即：**构建输入与原归档逐字节等价**，变化的只是交付形态。

## 2. 构建配置

```
-DCMAKE_BUILD_TYPE=Release
-DCMAKE_CXX_STANDARD=20（由 recipe 强制 cppstd=20）
-DBUILD_SHARED_LIBS=ON
-DARROW_BUILD_SHARED=ON / -DARROW_BUILD_STATIC=OFF
-DARROW_IPC=ON -DARROW_COMPUTE=ON -DARROW_CSV=ON -DARROW_FILESYSTEM=ON
-DARROW_JSON=OFF          （ARROW_JSON=ON 会经 ThirdpartyToolchain.cmake:410-412
                           自动要求 RapidJSON 的 FetchContent 下载；第一阶段不需要）
-DARROW_FLIGHT/DATASET/PARQUET/ORC/GANDIVA/CUDA=OFF
-DARROW_MIMALLOC=OFF -DARROW_JEMALLOC=OFF
-DARROW_SIMD_LEVEL=NONE -DARROW_RUNTIME_SIMD_LEVEL=NONE
-DARROW_WITH_{RE2,UTF8PROC,ZLIB,ZSTD,LZ4,SNAPPY,BROTLI,BZ2}=OFF
-DARROW_BUILD_TESTS=OFF -DARROW_BUILD_EXAMPLES=OFF -DARROW_BUILD_BENCHMARKS=OFF
ARROW_XSIMD_URL=<build>/_vendored/xsimd-14.2.0-ohos.tar.gz
                          （**环境变量**，由配方 build() 现场生成并导出；零网络。
                            注意不是 CMake 变量，也不是 FETCHCONTENT_SOURCE_DIR_XSIMD）
```

## 3. 测试：诚实申报

### 3.1 上游测试（未运行，如实申报）

| 项 | 值 |
|----|----|
| 框架 | googletest——**不内置**，由 `ThirdpartyToolchain.cmake:2607-2638` 从 GitHub FetchContent 下载 |
| 规模 | `cpp/src/arrow/**/*_test.cc` 共 **230** 个（顶层 19 个） |
| 最小核心相关子目录 | array 13、ipc 5、io 5、compute 8（递归 37）、csv 7、json 6；buffer/table 目录 0（其覆盖并入 array/ipc 测试） |
| ctest 标签 | 基础标签 `unittest`（`BuildUtils.cmake:794-795`），另有 `arrow-compute-tests`、`filesystem` 等 |
| 本次执行 | **未执行（NOT_RUN）** |

未执行的技术原因：

1. 启用 `ARROW_BUILD_TESTS` 需要 googletest，而上游是 **FetchContent 从
   GitHub 下载**（本仓库规则禁止构建期网络依赖；同目录 xsimd 的处理方式
   同理需要额外内置 googletest 源码）。
2. 230 个测试文件的构建在 farm 的单线程约束（`tools.build:jobs=1` +
   `CMAKE_BUILD_PARALLEL_LEVEL=1`）下属不可行量级。
3. 测试二进制为 aarch64，只能在目标设备运行；本版本未安排"构建→传输→
   设备侧运行"的额外流程。

如实申报 NOT_RUN，不把未运行的测试计为 PASS。旧版本 24.0.0 目录中的
`reports/upstream-test-results.md` 等报告**属于 24.0.0**，本版本未复跑，
故不在本版本引用其结论。

### 3.2 test_package（已执行，消费者视角）

`test_package/test_arrow.cpp` 真实调用 Arrow 核心 API，5 组断言：

| # | 模块 | 断言 |
|---|------|------|
| 1 | Builder/Array | `Int32Builder::Append(42)` + `AppendValues({1,2,3})` + `Finish()`；数组长度 4、类型 int32、`Value(0)==42`、`Value(3)==3` |
| 2 | Schema | `schema({field("value", int32(), false)})`，字段数 1、字段名 `value` |
| 3 | Table | `Table::Make(schema,{arr})` 非空、`Validate()` 通过、形状 4×1 |
| 4 | Compute | `compute::CallFunction("add", {arr, arr})` 成功，`[0]==84`（42+42）、`[1]==2`（1+1） |

由 conanfile 的 `test()` 直接运行测试二进制（aarch64，在 OHOS PC 上原生执行）。

## 4. 产物

`lib/libarrow.so`（含 SONAME，由补丁 0002 保证）、`include/arrow/**` 公共头、
`lib/cmake/Arrow/ArrowConfig.cmake`（导出 `Arrow::arrow_shared` /
`Arrow::arrow`，见 package_info 的 cmake_target_aliases）。

## 5. 后续可扩展项（本版本未做，如实记录）

| 项 | 前置条件 |
|----|----------|
| `ARROW_JSON=ON` | 需内置 RapidJSON 1.1.0（header-only，处理方式同 xsimd） |
| `ARROW_WITH_ZSTD/LZ4/SNAPPY/ZLIB` | 需要 CMake `find_package` 与制品仓包目标名逐一核对（zstd 在制品仓是 shared-only） |
| `ARROW_WITH_RE2/UTF8PROC` | 制品仓有 `re2/2024-04-01`、`utf8proc/2.11.3`，可后续接入 |
| Parquet / Dataset / Flight | 依赖链显著增大（thrift / gRPC / protobuf），建议单独评估 |
| 上游 230 项测试 | 需内置 googletest + 设备侧运行流程 |

## 6. 参考

- 上一版本配方与报告：`archives/a/apache-arrow/24.0.0/`（作为演进基线，
  其 `reports/` 与 `scripts/` 属于该版本，本版本未复制）
- 上游：https://arrow.apache.org/
