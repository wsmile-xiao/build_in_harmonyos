# vineyard (v6d) 0.24.4 — HarmonyOS PC 适配笔记

## 1. 项目概述

- 上游：https://github.com/v6d-io/v6d （CNCF TAG-Storage 下的 in-memory immutable data manager，前阿里巴巴组件）
- 版本：0.24.4（tag，2025-05-15）
- 许可证：Apache-2.0；主页：https://v6d.io
- 构建系统：CMake（C++ 项目，默认 C++17；含 Python/java/go/rust 绑定，本轮不涉及）
- 源码包：`https://github.com/v6d-io/v6d/releases/download/v0.24.4/v6d-0.24.4.tar.gz`
  - sha256=`055bab09ca67542ccb13229de8c176b7875b4ba8c8a818e942218dccc32a6bae`
  - 与 Homebrew core `Formula/v/vineyard.rb` 一致（已实测下载校验通过）。

## 2. 依赖面与 submodule 分析（关键）

vineyard 依赖面极大，且大量通过 **git submodule** 组织：
- submodule（`thirdparty/` 与 `modules/*/thirdparty/`）共 14 个，.gitmodules 见
  v0.24.4：[etcd-cpp-apiv3, cpprestsdk, hiredis, redis-plus-plus, libfabric,
  libgrape-lite, pybind11, mimalloc, zstd, libcuckoo, GraphAr, boost-leaf,
  powturbo, DataFrame]。
- **官方 GitHub release 归档不含 submodule 源码**（只含顶层 dotfile）。已在
  本机解包核实：`thirdparty/mimalloc`、`zstd`、`libcuckoo` 等下仅有 `.git*` 等
  dotfile，无实际 build 源码。因此【必须 vendoring】用到的 submodule。
- 顶层 CMake 通过 pinned commit 引用它们（`add_subdirectory` 或 `find_*`）。

各模块依赖（v0.24.4 `CMakeLists.txt`）：
- `find_common_libraries()`（无条件执行）：glog、libcuckoo、libunwind、pthread、
  nlohmann-json（thirdparty 内自带，非 submodule）、zstd。
- `BUILD_VINEYARD_CLIENT`：核心 client。src/common 里 `status.h/arrow.h` include
  apache-arrow → **必须依赖 apache-arrow**。链接 `libzstd_static`。
- `BUILD_VINEYARD_BASIC`：`find_package(MPI REQUIRED)` + 内嵌 libgrape-lite
  submodule + arrow。**MPI 是 OHOS 主要阻塞点**。
- `BUILD_VINEYARD_IO` / `GRAPH`：需要 boost。
- `BUILD_VINEYARD_SERVER`：需要 gflags、mimalloc、etcd-cpp-apiv3/cpprestsdk、
  openssl、hiredis、redis-plus-plus、libfabric。
- Linux 专属块（libfabric/RDMA 编译与链接）：`if (${CMAKE_SYSTEM_NAME} STREQUAL
  "Linux")`。**OHOS 下 CMAKE_SYSTEM_NAME=HarmonyOS，该块被跳过**，显著简化。

## 3. 本轮适配范围（路径 A 基础适配）

第一轮目标 = 构建核心 **vineyard_client** 共享库，关闭所有外部重型模块：
```
BUILD_VINEYARD_SERVER=OFF  BUILD_VINEYARD_GRAPH=OFF  BUILD_VINEYARD_IO=OFF
BUILD_VINEYARD_BASIC=OFF   BUILD_VINEYARD_MALLOC=OFF BUILD_VINEYARD_CLIENT=ON
BUILD_VINEYARD_PYTHON_BINDINGS=OFF BUILD_VINEYARD_JAVA=OFF BUILD_VINEYARD_FUSE=OFF
BUILD_VINEYARD_LLM_CACHE=OFF BUILD_VINEYARD_HOSSEINMOEIN_DATAFRAME=OFF
BUILD_VINEYARD_TESTS=ON
```
- conan 依赖：# apache-arrow/24.0.0（仓库已有）、# glog/0.7.1（仓库已有）。
- vendoring submodule：zstd、libcuckoo、mimalloc（按 v0.24.4 树内 commit）。
  - zstd pinned `5059618295bc67f4f70eb6f12e6cf57b8d3de141`
    sha256=`6a047ec7442b2ffb1ba9ebfc2ae1a26d759e50032bfd86b8711c61fc9451ee76`
  - libcuckoo pinned `735a74b01610fb8d3614019429af370856e4a88c`
    sha256=`028a5954edd502ced0f7a508746da24d82d74e328a0476e63a6a5f1fe11938dc`
  - mimalloc pinned `dd7348066fe40e8bf372fa4e9538910a5e24a75f`
    sha256=`2ca84b107a61071b5b604a67882d258e74ea35e4ba40e6c271d0917613792ddc`
  - 三个 commit/sha256 均为本机实测下载计算。
- 依赖发现：用 `CMAKE_PREFIX_PATH` 指向 apache-arrow/glog 的 package_folder，
  使 v6d 自带 `cmake/FindGlog.cmake`（find_path/find_library）与
  `find_package(Arrow)` 能解析 conan 制品。apache-arrow recipe 的 CMakeDeps
  提供 `Arrow::arrow` config。

## 4. 上游测试策略

- 测试框架：**非 gtest**。`test/*.cc` 每个都是独立 `main()` 可执行（自定义
  CHECK / VINEYARD_CHECK_OK 断言，失败以非 0 退出码终止）。通过
  `test/CMakeLists.txt` 的 `add_test(<name> <name>)` 注册进 **ctest**，并收敛到
  自定义目标 `vineyard_tests`。
- 注册总数：`test/*.cc` = **58** 个 ctest 条目（`gpumalloc_test.cu` 仅
  USE_CUDA 时追加，本轮不启用）。口径 = `ctest_entries`。
- `MANIFEST.yml`：`upstream_test_total: 58`、`upstream_test_count_method:
  ctest_entries`，58 个 test 文件逐一列全。
- HMBS marker：build() 里 `cmake.build(target="vineyard_tests")` 后执行
  `ctest --output-on-failure`，从 ctest 确定性汇总行解析计数
  （`NN% tests passed, M tests failed out of K`），写入
  `HMBS_UPSTREAM_TEST_RESULT` 并持久化到 `res/upstream_test_result.json`。
- 预期缺口：58 个中大量用例需要完整模块栈（basic/arrow data-structure、
  server/vineyardd、MPI、etcd、redis、RDMA），本轮核心构建无法全部编译/运行；
  通过 count 与 gaps 如实呈现，后续迭代按模块逐个端口补齐。

## 5. test_package

- `test_package.cpp` 作为消费者冒烟测试（无需运行 vineyardd）：
  1) `vineyard_version()` 非空；2) `vineyard::Client` 默认构造（强制链接
  libvineyard_client）+ `Connected()==false`；3) `InvalidObjectID()==numeric max`。
- CMakeDeps + CMakeToolchain 消费 `vineyard::vineyard_client` target。
- 发射 `HMBS_TEST_PACKAGE_RESULT`（3 项断言）并重放 res/ 下的
  `HMBS_UPSTREAM_TEST_RESULT`。

## 6. 本轮结论 / 待真机验证

- 工作树已就绪（conanfile.py / conandata.yml / manifest.yaml / test_package/
  notes.md），未 commit。真机 rule4 门禁通过前不建 PR。
- 下一轮：真机预检 conan create。预期遇到的核心问题：
  - apache-arrow(24.0.0) 作为依赖的 C++20 覆盖 / Arrow find_package 集成；
  - vendored zstd/libcuckoo/mimalloc 的构建接入；
  - 核心 client 在 OHOS 下的编译警告/链接（如 /dev/shm、共享内存 syscall 等，
    需按错误逐一最小适配）。
  - 58 个上游测试的逐个可运行性（缺 server/模块会编译或运行时失败 → 如实计
    gaps，不伪造通过）。

## 7. Round-1 真机失败与修复（2026-09-19）

### 失败

- 失败阶段：compile（依赖构建阶段，在 vineyard 自身 build() 之前）。
- 直接证据：`cmake/3.31.12: ERROR: Error in build() method, line 35
  get(self, **self.conan_data["sources"][self.version][str(self.settings.os)][arch],
  KeyError: 'OHOS'`。
- 依赖图：`vineyard -> glog/0.7.1(conancenter) -> tool_requires cmake/3.31.12`，
  且 `gflags/2.3.0`(conancenter，被 conancenter glog 的 requirements 引入)。

### 根因

1. vineyard 的 `requires("glog/0.7.1")` 在**启用 conancenter** 的 hmbs 预检环境
   解析到 **conancenter 版 glog**（证据：依赖图出现 conancenter 的
   `gflags/2.3.0`，而仓库自适配 glog 用的是 `gflags/2.2.2`）。
2. conancenter 版 glog 的配方声明 `tool_requires("cmake/...")`，把 conancenter
   的 `cmake/3.31.12` 拉进构建闭包。
3. conancenter cmake 配方的 conandata `sources` 按 OS 分条目（Linux/Darwin/
   Windows...），**没有 OHOS 条目**，os=OHOS 时构建即 `KeyError: 'OHOS'`。

This is the same failure class as fceux/2.6.6（CCI cmake `KeyError: 'OHOS'`），
此仓库已有先例。

### 修复方案（vendoring glog，确定性消除 conancenter glog）

- **前提**：官方 CI 的 `ci/conan/setup.sh` 会 `conan remote disable conancenter`，
  此时 `glog/0.7.1` 解析到 ohpcd 自适配配方（无 cmake tool_requires），配方本可
  通过；但 hmbs 预检开启了 conancenter，导致解析到 conancenter 版。为对两种
  环境都健壮，把 glog 改为配方内 **vendoring 源码构建**。
- **具体修改**：
  1. `conanfile.py`：删除 `self.requires("glog/0.7.1")`，只保留
     `apache-arrow/24.0.0` 这个 conan 依赖。
  2. `conandata.yml`：新增 `glog:` 源码条目
     (`https://github.com/google/glog/archive/v0.7.1.tar.gz`，
     sha256=`00e4a87e...`，与仓库自适配 glog 完全一致)。
  3. `source()`：把 glog 下载到 `thirdparty/glog`，应用仓库自适配补丁
     `patches/0001-glog-CMakeLists.txt.patch`（CXX_STANDARD 14，HMDFS 兼容）。
  4. `build()`：先用生成工具链把 glog 以静态库构建到
     `<build>/vendored-glog/install`（`WITH_GFLAGS=OFF -DWITH_GTEST=OFF
     -DWITH_UNWIND=none -DWITH_SYMBOLIZE=OFF -DWITH_TLS=OFF`，复用
     `user.hmbs:cmake_path`/`HMBS_CMAKE` 指向的宿主 cmake，避免再走 cmake 包），
     再把它写进 `CMAKE_PREFIX_PATH` 让 vineyard 的 `FindGlog.cmake` 找到。
  5. `package()`：把 vendored glog 的 `include/glog` 与 `lib/*.a` 一并装入包，
     供消费方链接（glog 静态链进 vineyard_client.so，无额外运行时 .so 依赖）。
- **为什么不 pin RREV**：本地按 conan FileTreeManifest 复算 apache-arrow 配方
  RREV 与 ohpcd 实际 RREV（预检日志 `6ea5c119...`）不一致；fceux/2.6.6 笔记已
  记录 RREV 本地复算易错（minizip 实证）教训，故不猜 RREV，采用 vendoring 这一
  确定性路线（fceux minizip 同款）。

## 8. Round-2 真机失败与修复（2026-09-19）

### 失败

- 失败阶段：compile（vineyard 自身的 `cmake.configure()` 阶段）。
- 直接证据：
  ```
  CMake Error at CMakeLists.txt:1 (cmake_minimum_required):
    Compatibility with CMake < 3.5 has been removed from CMake.
    Update the VERSION argument <min> value.
    Or, use the <min>...<max> syntax
  Problem parsing /proc/meminfo
  ```
- 真机环境：`HMBS_BUILD_TOOLS.cmake.version = "4.1.2"`。

### 根因

vineyard 0.24.4 的顶层 `CMakeLists.txt` 第一行为：
```cmake
cmake_minimum_required(VERSION 3.3)
```
CMake 4.x（真机使用 4.1.2）已移除对 < 3.5 的兼容性支持，configure 阶段直接报错退出。

### 修复方案

在 `patches/` 目录新增 `0002-increase-cmake-minimum-required-to-3.22.patch`，将 `cmake_minimum_required` 从 3.3 提升到 3.22（3.22 是 glog 0.7.1 的要求版本，同时向后兼容 CMake 3.22+ 的所有特性）。在 `conandata.yml` 中添加 `patches:` 条目，让 `apply_conandata_patches(self)` 在 `build()` 中自动应用。

### 修改文件

1. **新增** `patches/0002-increase-cmake-minimum-required-to-3.22.patch`
2. **修改** `conandata.yml` — 新增 `patches:` 块
3. **修改** `manifest.yaml` — `patches_applied` 增加新补丁条目
4. `conanfile.py` 无需修改（`apply_conandata_patches(self)` 会自动读取 `conandata.yml` 中的 `patches:` 条目）

## 9. Round-3 真机失败与修复（2026-09-19）

### 失败

- 失败阶段：compile（vineyard 自身的 `cmake.configure()` 阶段，配置 submodule 时）。
- 直接证据：
  ```
  CMake Error at thirdparty/zstd/build/cmake/CMakeLists.txt:10 (cmake_minimum_required):
    Compatibility with CMake < 3.5 has been removed from CMake.
    Update the VERSION argument <min> value.
  -- Configuring incomplete, errors occurred!
  ```
- 真机环境：`HMBS_BUILD_TOOLS.cmake.version = "4.1.2"`。

### 根因

Round-2 只补丁了 vineyard 顶层 `CMakeLists.txt` 的 `cmake_minimum_required(VERSION 3.3)`。
但 source() 里 vendoring 进来的 thirdparty submodule（zstd `build/cmake/CMakeLists.txt`
line 10，可能还有 libcuckoo / mimalloc）各自带更老的 `cmake_minimum_required(< 3.5)`，
CMake 4.x（真机 4.1.2）已移除 < 3.5 兼容，configure 处理 submodule 时直接报错退出。
对每个 submodule 逐个打补丁不现实，应统一放行。

### 修复方案（CMAKE_POLICY_VERSION_MINIMUM=3.5）

在 conanfile.py 的 `generate()` 里，用 CMakeToolchain 的 **cache 变量**设置
`CMAKE_POLICY_VERSION_MINIMUM=3.5`：

```python
tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
```

`CMAKE_POLICY_VERSION_MINIMUM` 必须在 configure 一开始（顶层 project() 之前）就
存在于 cache，`cache_variables` 会以 `-D` 形式在 configure 命令行注入，因此生效。
这样所有子项目/三方 submodule 中任何 `cmake_minimum_required(< 3.5)` 都会被 CMake
按 3.5 对待，不再硬性报错。这是仓库内通用约定（archives 大量配方如 airspy /
alacenc / n2n / nanoarrow 等均用同一 cache 变量处理 CMake 4.x 兼容）。此前
Round-2 的顶层补丁 0002 保留（guarded 3.22），vendored glog 构建已单独带
`-DCMAKE_POLICY_VERSION_MINIMUM=3.5`。

### 修改文件

1. **`conanfile.py`** — `generate()` 新增 `tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"]="3.5"`。

## 10. Round-4 真机失败与修复（2026-09-19）

### 失败

- 失败阶段：compile（vineyard 自身的 `cmake.configure()` 阶段，Generate 阶段处理 test/CMakeLists.txt 时）。
- 直接证据（真机 log）：
  ```
  CMake Error in test/CMakeLists.txt:
    Found relative path while evaluating include directories of "lru_test":
      "GLOG_INCLUDE_DIR-NOTFOUND"
  ...（plasma_test / rpc_test / name_test / persist_test / session_test / tensor_test
      等 50+ 个测试目标同一错误）
  -- Generating done (1.1s)
  CMake Generate step failed.  Build files cannot be regenerated correctly.
  ```
- 真机环境：`HMBS_BUILD_TOOLS.cmake.version = "4.1.2"`。

### 根因

Round-3 的 `CMAKE_POLICY_VERSION_MINIMUM=3.5` 已让 configure 越过 zstd 等 submodule 的
旧 `cmake_minimum_required`。现在卡在 **GLOG 头文件目录解析**：

- v6d 顶层 `CMakeLists.txt` 的 `find_common_libraries()` 调用 `cmake/FindGlog.cmake`，
  其中 `find_path(GLOG_INCLUDE_DIR glog/logging.h PATHS ${GLOG_ROOT_DIR})`。
- 该 `find_path`（显式 `PATHS` 仅为空的 GLOG_ROOT_DIR）并不能可靠地沿
  `CMAKE_PREFIX_PATH/include` 遍历到 vendored glog 的头文件，于是
  `GLOG_INCLUDE_DIR` 被置为 `GLOG_INCLUDE_DIR-NOTFOUND`。
- `test/CMakeLists.txt` 对所有测试目标执行
  `target_include_directories(${testname} PRIVATE ${GLOG_INCLUDE_DIRS})`，其中
  `GLOG_INCLUDE_DIRS=${GLOG_INCLUDE_DIR}=...-NOTFOUND` 为相对路径，CMake 4.x 报
  "Found relative path"，configure（Generate 阶段）失败退出。

### 修复方案（直接缓存 GLOG 头/库绝对路径）

v6d 的 `FindGlog.cmake` 依赖 `GLOG_INCLUDE_DIR` 与 `GLOG_LIBRARY` 两个 **cache 变量**
（`find_path`/`find_library` 在 cache 已有绝对有效路径时直接采用、不再搜索）。因此在
conanfile.py 的 `generate()` 里用 CMakeToolchain 的 cache 变量**确定性注入**这两个值：
指向 vendored glog 安装前缀下 `include` 与 `lib/libglog.a`：

```python
glog_inc = os.path.join(self._glog_prefix_dir(), "include")
tc.cache_variables["GLOG_INCLUDE_DIR"] = glog_inc
tc.cache_variables["GLOG_LIBRARY"] = os.path.join(
    self._glog_prefix_dir(), "lib", "libglog.a")
```

`GLOG_FOUND` 相应置为 TRUE，`GLOG_INCLUDE_DIRS`/`GLOG_LIBRARIES` 非空，顶层
`include_directories(SYSTEM ${GLOG_INCLUDE_DIR})` 与 test 目标的
`target_include_directories(... ${GLOG_INCLUDE_DIRS})` 均解析为合法绝对路径，configure
不再报相对路径错误。`CMAKE_PREFIX_PATH` 仍保留用于 `find_package(Arrow)`（apache-arrow）。

### 修改文件

1. **`conanfile.py`** — `generate()` 新增 `GLOG_INCLUDE_DIR` 与 `GLOG_LIBRARY` 两个 cache 变量。

## 11. Round-5 真机失败与修复（2026-09-19）

### 失败

- 失败阶段：compile（`cmake.build()` 编译 `vineyard_client` 阶段）。
- 直接证据（真机 log）：
  ```
  In file included from .../src/common/rdma/rdma.h:23:
  In file included from .../src/common/rdma/util.h:24:
  .../thirdparty/libfabric/include/rdma/fabric.h:43:10: fatal error: 'rdma/fi_errno.h' file not found
  #include <rdma/fi_errno.h>
  make[2]: *** [CMakeFiles/vineyard_client.dir/.../src/client/rpc_client.cc.obj] Error 1
  ```
- 真机环境：`HMBS_BUILD_TOOLS.cmake.version = "4.1.2"`。
- Round-4 的 GLOG cache 变量修复已让 configure 完整通过（"Configuring done (25.7s) / Generating done"）。

### 根因

- v6d 顶层 `CMakeLists.txt` 的 `vineyard_client` 源码 glob 无条件包含
  `src/client/*.cc`（含 `rpc_client.cc`）与 `src/common/rdma/*.cc`。
- v6d 用 `#if defined(__linux__)` 门控 RDMA：`src/common/rdma/util.h` 等在此宏下
  `#include "libfabric/include/rdma/fabric.h"`。**HarmonyOS 的 clang 工具链同样定义
  `__linux__`**（OHOS 基于 Linux kernel），因此 OHOS 下该分支被激活，去拉取 libfabric 头。
- 但 v6d 只在 `if (${CMAKE_SYSTEM_NAME} STREQUAL "Linux")` 块里构建/接入 libfabric；OHOS 下
  `CMAKE_SYSTEM_NAME=HarmonyOS`，该块被跳过，`thirdparty/libfabric` 仅有部分头文件
  （缺 `rdma/fi_errno.h`），且 `thirdparty/libfabric/include` 不在 include 路径上，故
  `fabric.h` 里的 `<rdma/fi_errno.h>` 找不到。
- 副作用：即使头文件能编过，RPC/RDMA 类（RPCClient / RDMAClient / RDMAClientCreator）
  依赖 libfabric 符号与 RDMA 硬件，在 OHOS 上本就不可能运行。

### 修复方案（非 Linux 平台把 RDMA/RPC 门控出构建）

RDMA/RPC 本质是 Linux-only（依赖 libfabric + RDMA 硬件），OHOS 无此能力，故按 v6d
自身的 `CMAKE_SYSTEM_NAME STREQUAL "Linux"` 约定，在非 Linux 平台把 RDMA/RPC 门控出
编译，并对依赖它们的上游测试做同样门控（对应 gaps 记 ohos_feature，总数仍按 58）：
- **Patch 0003 `CMakeLists.txt`**：`vineyard_client` glob 移除 `src/common/rdma/*.cc`；
  仅 Linux 下追加 rdma 源与 `src/client/rpc_client.cc`，非 Linux 下 `REMOVE_ITEM`
  rpc_client.cc（因它依赖 RDMA 类）。
- **Patch 0004 `test/CMakeLists.txt`**：非 Linux 下跳过 10 个 RPC/RDMA 依赖测试：
  rpc_test、rpc_delete_test、rpc_get_object_test、rdma_test、rdma_blob_perf_test、
  remote_buffer_test、remote_buffer_with_rdma_test、invalid_connect_test、
  lru_spill_test、concurrent_lru_spill_test（均已审计 grep 确认 include
  `client/rpc_client.h` 或 `common/rdma/*`）。
- 这两个补丁经 `patch --dry-run -p1` 对 v0.24.4 原始文件验证可干净应用。
- 其余 client 源（client.cc / client_base.cc / io.cc / utils.cc）均不含 RDMA/RPC 引用，
  门控后可独立编链，IPC `Client` 主类不受影响。

### 修改文件

1. **新增** `patches/0003-gate-rdma-rpc-off-non-linux.patch`
2. **新增** `patches/0004-skip-rpc-rdma-tests-non-linux.patch`
3. **修改** `conandata.yml` — `patches:` 追加 0003、0004
4. **修改** `manifest.yaml` — `patches_applied` 追加两项
5. **修改** `test_package/MANIFEST.yml` — `portability_changes` 记录 RDMA/RPC 门控；
   `upstream_test_total` 保持 58（官方注册口径），10 个门控测试以 ohos_feature gaps 呈现
6. **修改** `conanfile.py` — 新增类常量 `upstream_test_total=58`（与 MANIFEST 一致）；
   `_run_upstream_tests()` 的 gaps 记账：`gated = 58 - ctest_total`（非 Linux 下门控的
   10 个 RPC/RDMA 测试，ohos_feature）+ 失败测试（test_failure），保证
   `gaps_total == upstream_test_total - passed`，满足 rule4 硬门禁恒等。

## 12. 备注

- 真机/命令为内部基建，此内容仅 notes.md，不写入 PR 正文。
- 若某轮源码下载超时，把 conandata 主源 URL 改为有序镜像列表（参考
  ci/conan/build_and_test.sh 的 GitHub/GNU 镜像映射），保持官方 URL 在最后
  回退，sha256 不变。

## 13. Round-6 真机失败与修复（2026-09-19）

### 失败

- 失败阶段：compile（source() 下载 thirdparty submodule 阶段）。
- 直接证据：
  ```
  vineyard/0.24.4: Sources correctly downloaded from https://github.com/v6d-io/v6d/releases/download/v0.24.4/v6d-0.24.4.tar.gz
  vineyard/0.24.4: WARN: network: Error downloading file https://github.com/facebook/zstd/archive/5059618295bc67f4f70eb6f12e6cf57b8d3de141.tar.gz:
    'HTTPSConnectionPool(host='github.com', port=443): Max retries exceeded with url: /facebook/zstd/archive/...
    (Caused by ConnectTimeoutError(<HTTPSConnection(host='github.com', port=443) at ...>, 'Connection to github.com timed out. (connect timeout=30)'))'
  vineyard/0.24.4: Waiting 5 seconds to retry...
  ERROR: vineyard/0.24.4: Error in source() method, line 107
    get(self, **spec, strip_root=True, destination=dest)
  ConanException: Error downloading file https://github.com/facebook/zstd/archive/...
  ```
- 真机环境：`HMBS_BUILD_TOOLS.cmake.version = "4.1.2"`，网络直连 github.com 超时。

### 根因

真机环境（HarmonyOS PC 预检机器）直连 github.com 存在严重的网络连接超时问题（ConnectTimeoutError，30s 超时）。
主源码包（v6d-0.24.4.tar.gz）下载成功（可能走了 CDN 或已缓存），但 thirdparty submodule（zstd/libcuckoo/mimalloc）和 glog
的 GitHub 直连均超时失败。这是纯网络可达性问题，非代码或依赖问题。

### 修复方案（GitHub URL 镜像降级）

在 conandata.yml 中所有 GitHub URL 前添加 `https://gh-proxy.com/` 镜像作为首选，原始 URL 保留在最后作兜底。
格式与仓库内其他已验证配方（如 astroterm/1.0.9）一致：`url:` 下挂列表。

具体修改：
1. `sources` 段：单值 url → 列表，gh-proxy.com 前置
2. `thirdparty.zstd` / `libcuckoo` / `mimalloc`：同上
3. `glog`：同上
4. sha256 校验值保持不变（镜像返回内容与官方完全一致）
5. conanfile.py 无需修改（`get(self, **spec)` 自动支持 url 列表，Conan 2.x 会逐个尝试）

### 经验决策

- [经验 1] conandata.yml 指向不可达的源码归档时改为 vendor 本地源码 → **reject**
  理由：本轮并非源码完全不可达（主包下载成功），而是直连 github.com 超时；采用镜像降级而非 vendoring，
  保持与上游相同的源码身份和 sha256 校验，改动更小、更易维护。


## 14. Round-7 真机失败与修复（2026-09-19）—— 门控补丁 0003 失效的真正根因

### 失败

- 失败阶段：compile（`cmake.build()` 编译 `vineyard_client` 阶段）。
- 直接证据（真机 log）：
  ```
  In file included from .../src/client/rpc_client.cc:
  In file included from .../src/common/rdma/rdma.h:23:
  In file included from .../src/common/rdma/util.h:24:
  .../thirdparty/libfabric/include/rdma/fabric.h:43:10: fatal error: 'rdma/fi_errno.h' file not found
  make[2]: *** [CMakeFiles/vineyard_client.dir/.../src/client/rpc_client.cc.obj] Error 1
  ```
- 与 Round-5 完全相同的错误指纹：Round-5 创建的 0003 补丁已导出/应用，但真机仍编译 rpc_client.cc。

### 根因（关键）

- Round-5 的 0003 补丁写法：`file(GLOB CLIENT_SRC_FILES "src/client/*.cc" ...)` 之后在非 Linux 分支
  `list(REMOVE_ITEM CLIENT_SRC_FILES "src/client/rpc_client.cc")`。
- **CMake 的 `file(GLOB ...)` 始终返回绝对路径**（实测 `/path/to/src/client/rpc_client.cc`），而
  `REMOVE_ITEM` 用的是相对路径字面量 `src/client/rpc_client.cc`，二者永不相等，因此 rpc_client.cc
  从未被移除，仍然进入 `add_library(vineyard_client ...)` 并触发 `#include <rdma/fi_errno.h>` 缺失。
- 顶层 `include_directories(SYSTEM ${PROJECT_SOURCE_DIR}/thirdparty)`（原 CMakeLists line 547）是
  无条件添加的，故 OHOS 下 `common/rdma/util.h` 的 `#include <rdma/fabric.h>` 能解析到源码树里
  不完整的 `thirdparty/libfabric/include/rdma/fabric.h`（缺 `fi_errno.h`），最终编译报错。
- `CMAKE_SYSTEM_NAME=HarmonyOS`（ci/conan/profiles/ohos-aarch64: CMakeToolchain 映射 OHOS→HarmonyOS），
  该分支本身是走 else 的，问题不在分支选择，而在 REMOVE_ITEM 的路径形式不匹配。

### 修复方案（按 basename 过滤，不依赖路径形式）

重写 0003 补丁：不再用相对路径 `REMOVE_ITEM`，而是对 `CLIENT_SRC_FILES` 逐个取 basename，凡是
`rpc_client.cc` 或文件名含 `rdma` 的一律从库源码中排除，并对 rdma glob 照旧删除。这样无论
`file(GLOB)` 返回绝对还是相对路径都能正确过滤，且做成无条件排除（本适配永远不构建 libfabric）。
同时在实机输出一条 `message(STATUS "vineyard: excluded RDMA/RPC sources ...")` 便于诊断确认。

```
set(_VINEYARD_EXCLUDED_SRC)
foreach(_vf ${CLIENT_SRC_FILES})
    get_filename_component(_vname "${_vf}" NAME)
    if(_vname STREQUAL "rpc_client.cc" OR _vname MATCHES "rdma")
        list(APPEND _VINEYARD_EXCLUDED_SRC ${_vf})
    endif()
endforeach()
if(_VINEYARD_EXCLUDED_SRC)
    list(REMOVE_ITEM CLIENT_SRC_FILES ${_VINEYARD_EXCLUDED_SRC})
    message(STATUS "vineyard: excluded RDMA/RPC sources from vineyard_client ...")
endif()
```

- 验证：用本机 CMake 复现 —— `file(GLOB)` 得到 `/tmp/.../rpc_client.cc` 绝对路径，相对路径
  `REMOVE_ITEM` 无效（BEFORE 与 AFTER 相同）；改用 basename 过滤后 AFTER 不再含 rpc_client.cc。
- 0003 补丁在 0002 之后的 v0.24.4 原始 `CMakeLists.txt` 上 `patch -p1` 干净应用（前后 hunk 计数 `-889,8 +889,26`）。
- 0004 补丁（test/CMakeLists.txt 跳过 10 个 RPC/RDMA 测试）用的是 `testname`（由相对 testfile 的
  `string(REGEX MATCH)` 取 basename），不存在绝对路径问题，无需改动；`-p1` 在 v0.24.4 原文件干净应用。
- 其余 client 源（client.cc / client_base.cc / io.cc / utils.cc）均不含 RDMA/RPC 符号；client.h 仅为
  `class RPCClient;` 前置声明（无符号引用），移除 rpc_client.cc 后 vineyard_client 可独立编链。

### 修改文件

1. **重写** `patches/0003-gate-rdma-rpc-off-non-linux.patch` — 由相对路径 `REMOVE_ITEM` 改为 basename 过滤
2. `conanfile.py` / `test_package/MANIFEST.yml` / `manifest.yaml` / `conandata.yml` 的投入与 gating 记账不变
   （10 个 RPC/RDMA 测试 ohos_feature gaps，总数仍 58，口径 ctest_entries）。


## 15. Round-8 真机失败与处理（2026-09-19）—— 非配方问题：hmbs CONAN_HOME/global.conf 含非法 conf

### 失败现象

- 失败阶段：compile（`conan create` 在 **Conan 初始化阶段**即退出退出码 1，任何配方代码都未执行）。
- 直接证据（stderr 全文）：
  ```
  Error in Conan initialization: [conf] 'tools.env:defines' does not exist in configuration list.
  Run 'conan config list' to see all the available confs.
  ```
- hmbs 使用独立 `CONAN_HOME=.../clients/<id>/conan-home`（专用，含 OHOS settings）。

### 根因（已用本地 conan 2.29.1 复现，非推测）

1. 该错误来自 **Conan 初始化**（`cli/cli.py main()` 里 `ConanAPI()` 构造阶段），即 conan 加载
   `CONAN_HOME/global.conf` 时对 conf 名做校验。`internal/model/conf.py` 的
   `_check_conf_name()`：conf 若不匹配 `user.*` 且不在 `BUILT_IN_CONFS` 中，立即抛
   `[conf] 'X' does not exist in configuration list`。
2. `tools.env:defines` **不是合法 Conan 2 conf**。`BUILT_IN_CONFS` 里 env 域只有
   `tools.env.virtualenv:powershell` / `tools.env:dotenv` / `tools.env:deactivation_mode`；
   “编译期 defines”的合法 conf 名是 **`tools.build:defines`**（已用 `conan config list` 验证）。
3. **本机复现**：在任意空 CONAN_HOME 的 `global.conf` 写入一行 `tools.env:defines=FOO=1`，
   然后 `conan create` 一个与 vineyard 无关的最小配方 → 得到一模一样的初始化错误。
   配方内容对错误完全无影响。因此这是 hmbs 生成的 `CONAN_HOME/global.conf` 中写入了
   非法的 `tools.env:defines`，与 vineyard 配方、补丁、依赖均无关。
4. **时间线佐证**：notes.md Round-5/6/7（13:37 之后的真机轮）都已通过 Conan 初始化
   （失败点是更晚的 CMake configure/build/源码下载阶段）；本轮(16:56)却卡在初始化。
   期间配方只改了 CMake 补丁 0003（16:49），不可能影响 conan 初始化。故本轮
   `tools.env:defines` 进入 global.conf 是 hmbs 预检环境侧新增的回归，非配方变更。

### 处理结论

- 这是 **hmbs/真机预检环境的 harness 回归**（CONAN_HOME/global.conf 写入了非法的
  `tools.env:defines`），不属于配方、编译或测试代码问题，配方侧无法修复（初始化在校验
  global.conf，配方法根本没有机会执行）。
- 正确修复在 hmbs 侧：把 global.conf 里的 `tools.env:defines` 改为合法的
  `tools.build:defines`，或改为 user 域 / 移除。若确需为 CMake 注入编译 defines，
  应采用合法 conf 名。
- 我方不伪造配方改动去“绕开”该错误（守则禁止），工作树配方保持不变，等待 hmbs 修复
  环境后再复跑真机预检。

### 经验决策

- [经验 1] conandata.yml 源码归档不可达→vendor 本地源码 → **reject**：本轮不是源码下载问题，
  是 conan 初始化 global.conf 校验失败，与源码归档/下载完全无关。
- [经验 2] test_package 编译标准与库一致 → **reject**：本轮根本未进入构建/测试阶段，
  与消费方编译标准无关。
## 16. Round-9 真机失败与修复（2026-09-19）—— OHOS musl 无 malloc_trim

### 失败

- 失败阶段：compile（`cmake.build()` 编译 `vineyard_client` 阶段）。
- 直接证据（真机 log）：
  ```
  .../src/common/util/env.cc:161:30: error: use of undeclared identifier 'malloc_trim'
    malloc_trim(1024 * 1024 /* 1MB */);
    ^
  1 error generated.
  make[2]: *** [CMakeFiles/vineyard_client.dir/.../src/common/util/env.cc.obj] Error 1
  ```

### 根因

- `src/common/util/env.cc` 的 `trim_rss()`：
  ```cpp
  void trim_rss() {
  #if defined(__linux__) || defined(__linux) || defined(linux) || defined(__gnu_linux__)
    malloc_trim(1024 * 1024 /* 1MB */);
  #endif
  }
  ```
  用 `__linux__` 等宏门控，调用 glibc 特有的 `malloc_trim()`。
- **HarmonyOS 的 clang 工具链同样定义 `__linux__`**（OHOS 基于 Linux kernel），因此该
  glibc 分支被激活。
- 但 OHOS 的 libc 是 musl，`<malloc.h>` **不声明 `malloc_trim`**。clang 在 C++ 模式下遇到
  未声明的函数引用即报 `use of undeclared identifier 'malloc_trim'`，编译失败。
- 与 Round-5（RDMA util.h 的 `__linux__` 门控）同根因：OHOS 的 `__linux__` 宏门控不能
  直接当作 glibc 语义。

### 修复方案（按 libc 能力判定，`__GLIBC__` 门控 `malloc_trim()`）

`malloc_trim()` 是 glibc 特有接口（`<malloc.h>` 声明），musl（OHOS 的 libc）没有。
原本用 `__linux__` 门控会误判——OHOS clang 同样定义 `__linux__`，导致调用不存在的
`malloc_trim()` 编译失败。按 libc 能力判定：`malloc_trim()` 仅 glibc 提供，故将该
调用整体门控到 `#if defined(__GLIBC__)`：

- 补丁 `patches/0005-guard-malloc_trim-non-ohos.patch` 把
  `#if defined(__linux__) || ... || defined(__gnu_linux__)` 改为
  `#if defined(__GLIBC__)`。
- glibc 系统：`__GLIBC__` 由 `<malloc.h>` → `<features.h>` 定义（env.cc 已
  `#include <malloc.h>`），行为不变，`trim_rss()` 照常调用 `malloc_trim()`。
- musl（OHOS）：`__GLIBC__` 未定义，`malloc_trim()` 调用不编译，`trim_rss()`
  退化为空实现（保持公共 API 符号存在、可链接）。
- **不引入 `__OHOS__` 平台宏**，符合 R8（patches/ 禁止平台条件编译宏，preflight PF5
  机械门禁拦截 patches 新增行含 `__OHOS__`），也符合 AI Review 建议——用 libc 能力
  检测而非平台宏表达，非 glibc 目标自然不编译该调用。

- `conandata.yml` `patches:` 追加 0005。
- `conanfile.py` 的 `exports_sources = "patches/*"` 已覆盖，无需改动。
- 已在 v0.24.4 原始 env.cc 上 `patch --dry-run -p1` 干净应用（无 fuzz）。

### 经验决策

- [经验 1] conandata.yml 源码归档不可达→vendor 本地源码 → **reject**：本轮是源码编译错误
  （OHOS musl 无 malloc_trim），与源码归档/下载完全无关。
- [经验 2] test_package 编译标准与库一致 → **reject**：本轮是主配方 client 库编译失败，
  与 test_package 消费方编译标准无关。


## 17. Round-10 真机失败与修复（2026-09-19）—— 手写补丁 hunk 行数不匹配，Conan 严格解析失败

### 失败

- 失败阶段：compile（`build()` 的 `apply_conandata_patches(self)` 应用 0005 时）。
- 直接证据（真机 log）：
  ```
  vineyard/0.24.4: Apply patch (file): patches/0005-guard-malloc_trim-non-ohos.patch
  .../0005-...patch: error: patch stream is incomplete!
  ConanException: Failed to parse patch: .../patches/0005-guard-malloc_trim-non-ohos.patch
  ```

### 根因

- Round-9 的 0005 补丁是**手写 hunk 头**（`@@ -158,7 +158,14 @@`），但实际 hunk 内容只有
  **6 行旧内容 / 13 行新内容**（旧侧 context 2 + 删除 4 = 6，非声明的 7；新侧 context 2 +
  新增 11 = 13，非声明的 14）。
- GNU `patch` 对 hunk 头行数不敏感，会用 fuzz/容差容忍，`patch --dry-run` 能通过，掩蔽了错误。
- 但 Conan 2.x 的 `apply_patch` 用 Python `patch` 库严格解析 unified diff：hunk 头声明的
  行数必须与实际增删行数一致，不一致即抛 `ValueError: patch stream is incomplete!`，
  最终 `Failed to parse patch`。

### 修复方案（用 diff -u 生成规范补丁，不用手写）

用 `diff -u` 对原文件与目标修改后的文件生成标准 unified diff，再把文件头改成
`--- a/src/common/util/env.cc` / `+++ b/src/common/util/env.cc`。`diff -u` 会算出
**正确**的 hunk 头 `@@ -156,7 +156,13 @@`（旧 7 行 / 新 13 行与内容精确一致），同时保证
结尾换行完整（不出现 dangling 行），Conan 严格解析即可通过。结果内容与 Round-9 完全一致
（OHOS 下 `trim_rss()` 退化为空实现，Linux/glibc 行为不变）。

### 经验教训

- 本仓库其他 conan 补丁（0002/0003/0004）均由真实 diff 生成（或行数与内容一致），故能通过
  Conan 解析；只有手写 0005 因 hunk 行数错配触发 `patch stream is incomplete!`。
- 结论：**所有 conan 补丁必须用 diff 工具生成并校验 hunk 行数，不能手写行数**。本地验证不能
  只看 GNU patch 是否通过（GNU 容差掩盖行数错误），必须以 `diff -u`（规范行数）+ 行数与
  内容核对为准。

### 经验决策

- [经验 1] conandata.yml 源码归档不可达→vendor 本地源码 → **reject**：本轮是补丁 hunk 行数
  格式问题，与源码归档/下载无关。
- [经验 2] test_package 编译标准与库一致 → **reject**：本轮是主配方补丁解析失败，与
  test_package 消费方编译标准无关。


## 18. Round-11 真机失败与修复（2026-09-19）—— 测试目标缺 arrow 头 & 上游测试大多依赖未构建模块

### 失败

- 失败阶段：compile（`cmake.build(target="vineyard_tests")` 编译 test 目标）。
- 直接证据（真机 log）：
  ```
  [34%] Built target vineyard_client
  .../test/spill_test.cc:20:10: fatal error: 'arrow/api.h' file not found
  #include "arrow/api.h"
  1 error generated.
  make[2]: *** [test/CMakeFiles/spill_test.dir/.../spill_test.cc.obj] Error 1
  ```
- 上游测试：发现 0，执行 0。

### 根因（两层）

1. **测试目标缺 arrow 头**：v6d 顶部只在
   `if(BUILD_VINEYARD_BASIC OR IO OR MIGRATION OR PYTHON_BINDINGS)` 分支里调用
   `find_apache_arrow()` + `include_directories(SYSTEM ${ARROW_INCLUDE_DIR})`。
   core-client-only 构建直接 `BUILD_VINEYARD_CLIENT=ON`，不满足该分支，arrow 头/目标
   未对测试目标暴露；而 `test/*.cc`（如 spill_test）直接 `#include "arrow/api.h"`。
   vineyard_client 本身不 include arrow，故 client 能编过、测试编不过。
2. **绝大多数测试依赖未构建模块**：审计 58 个 `test/*.cc` 的 include，绝大部分拉入
   `basic/ds/*`（需 BUILD_VINEYARD_BASIC -> MPI/boost）、`io/io/*`、`server/*`、
   `malloc/*`、`boost/process.hpp`、DataFrame、hosseinmoein-dataframe，或需要
   ipc_socket 连接运行中的 vineyardd（version/custom_vector/concurrent_id）。这些模块在
   本轮（路径 A）未构建，头文件/符号不在，即使补上 arrow，`vineyard_tests` 仍会在这些
   测试上编译失败。

### 修复方案

- **补丁 0006 `CMakeLists.txt` + `test/CMakeLists.txt`**：把 `BUILD_VINEYARD_CLIENT`
  加入 arrow 发现门控（`OR BUILD_VINEYARD_CLIENT`），使 `find_apache_arrow()` 运行、
  `Arrow::arrow` 目标创建；测试 `add_test_case` 里优先
  `target_link_libraries(... Arrow::arrow)`（获得头文件 + 符号），并在 conanfile
  `generate()` 导出 `VINEYARD_ARROW_INCLUDE_DIR`（apache-arrow 包 include 目录）作为
  头文件可靠回退，加到测试 include dirs。
- **补丁 0007 `test/CMakeLists.txt`**：按 keep-list 只构建 3 个 core 可编译且**自含**
  （不依赖运行中 vineyardd）的上游测试：`compressor_test / concurrent_memcpy_test /
  signature_test`；其余 55 个在非 Linux 门控里 `continue()` 跳过，全部以 ohos_feature
  gaps 如实记账（总数仍 58，口径 ctest_entries）。
- **conanfile.py `_run_upstream_tests`**：更新 ohos_feature gap 的 detail/evidence，
  明确描述 55 个门控测试的原因为模块栈未构建或需运行中的 vineyardd server。
- 同步更新 `manifest.yaml`（patches_applied 加 0006/0007、knowledge_gained）、
  `test_package/MANIFEST.yml`（portability_changes 加 0006/0007 说明）、
  `conandata.yml`（patches 加 0006/0007）。
- 补丁均由 `diff -u` 生成，hunk 行数与内容一致（吸取 Round-10 手写行数教训），并在
  v0.24.4 原始树上按 0002→0007 顺序 `patch -p1` 全部干净应用验证。

### 经验决策

- [经验 1] conandata.yml 源码归档不可达→vendor 本地源码 → **reject**：本轮是测试编译缺
  arrow 头 + 模块依赖问题，与源码归档/下载无关。
- [经验 2] test_package 编译标准与库一致 → **reject**：本轮是主配方内上游测试目标编译/
  门控问题，与 test_package 消费方编译标准无关。


## 19. Round-12 真机失败与修复（2026-09-19）—— core-client 构建不再引入 apache-arrow（去掉 0006）

### 失败

- 失败阶段：compile（`build()` 的 `cmake.configure()`，conanfile 行 279）。
- 直接证据（真机 log）：
  ```
  -- Could NOT find Arrow (missing: Arrow_DIR)
  -- Checking for module 'arrow'
  --   No package 'arrow' found
  -- Could NOT find Arrow (missing: ARROW_INCLUDE_DIR ARROW_LIB_DIR ARROW_FULL_SO_VERSION ARROW_SO_VERSION)
  CMake Error at CMakeLists.txt:172 (_message):
    apache-arrow is required, please install it and retry
  Call Stack (most recent call first):
    CMakeLists.txt:318 (message)
  -- Configuring incomplete, errors occurred!
  ```
- 上游测试：发现 0，执行 0。

### 根因（这是相对 Round-11 的【新】configure 失败，不是测试编译失败）

Round-11 为了让 test/*.cc 里 `#include "arrow/api.h"` 能编译，新增补丁 0006，
把 `BUILD_VINEYARD_CLIENT` 加进 v6d 顶部 `find_apache_arrow()` 的门控：
```
if(BUILD_VINEYARD_BASIC OR BUILD_VINEYARD_IO OR BUILD_VINEYARD_MIGRATION OR
   BUILD_VINEYARD_PYTHON_BINDINGS OR BUILD_VINEYARD_CLIENT)
    find_apache_arrow()   # 找不到 arrow 时 message(FATAL_ERROR)
    include_directories(SYSTEM ${ARROW_INCLUDE_DIR})
endif()
```
副作用：core-client 仅构建（不再满足 BASIC/IO 分支）现在也会无条件执行
`find_apache_arrow()`。而在 OHOS 上 `find_package(Arrow)` 找不到 apache-arrow 的
conan 配置（`Arrow_DIR` 缺失），`cmake/FindArrow.cmake` 同样失败，最终
`message(FATAL_ERROR "apache-arrow is required")` 让 configure 直接崩掉。

**关键审计**：核心 client 与 keep-list 的 3 个测试其实根本不用 arrow——
- `src/common/util/status.h` 并不 include arrow（仅注释引用）；`src/common/util/arrow.h`
  （include "arrow/api.h"）只被 server 目录引用。
- `src/client/ds/blob.h` / `remote_blob.h` 对 `arrow::Buffer` 只做
  `namespace arrow { class Buffer; }` 前向声明，不 include arrow。
- 全局 grep `src/client/`、`src/common/` 无任何 `#include "arrow"`。
- keep-list 的 `compressor_test/concurrent_memcpy_test/signature_test` 只 include
  `common/compression`、`common/memory`、`common/util`，与 arrow 无关。
- test_package 只 include `client/client.h` + `common/util/version.h`，不 include arrow。

所以最初的假设"common/util/status.h 依赖 apache-arrow、核心 client 必须提供 arrow"
（notes round-1 / manifest knowledge_gained）是**错误**的。本轮改为彻底移除。

### 修复方案（去箭头，恢复原始门控）

1. **删除补丁 0006** `patches/0006-fix-test-arrow-availability.patch`（其 top-level
   hunk 是 configure 崩溃直接原因；test/CMakeLists.txt 部分的 Arrow 链接代码对
   不用 arrow 的 3 个测试是死代码）。
2. **conandata.yml** `patches:` 去掉 0006，保留 0002/0003/0004/0005/0007（顺序与
   实测一致：0002→0003→0004→0005→0007）。
3. **conanfile.py**：
   - 删除 `self.requires("apache-arrow/24.0.0")`（真实的不能引入，避免再触发
     `find_package(Arrow)`）。
   - `_prefix_paths()` 只返回 vendored glog 前缀；`generate()` 删除
     `VINEYARD_ARROW_INCLUDE_DIR` 导出与相关注释。
   - 更新模块 docstring 与上游 gap 描述（不再提 arrow 模块）。
4. **manifest.yaml**：`dependencies` 置空；`patches_applied` 去掉 0006；
   `knowledge_gained` 修正"status.h 依赖 arrow"的错误认知并记录 0006 副作用。
5. **test_package/MANIFEST.yml**：dependency/portability_changes 去掉 arrow 依赖说法。
6. notes.md 记录本轮。

### 验证逻辑

- 去掉 0006 后，顶部 arrow 门控恢复为原始
  `if(BUILD_VINEYARD_BASIC OR ... OR BUILD_VINEYARD_PYTHON_BINDINGS)`，本轮
  BASIC/IO/MIGRATION/PYTHON 全部 OFF ⇒ `find_apache_arrow()` 不再执行 ⇒ configure
  不再对 arrow 做强依赖。
- OHOS `CMAKE_SYSTEM_NAME != Linux`（真机 log "unknown to cmake / Platform/HarmonyOS"
  证明），0007 keep-list `if(NOT ... STREQUAL "Linux")` 生效 ⇒ 只构建 3 个自含测试
  （compressor/concurrent_memcpy/signature）并注册进 ctest ⇒ 无需 arrow。
- test_package 消费 `vineyard_client` 且不 include arrow，链接/加载不依赖 arrow。

### 经验决策

- [经验 1] conandata.yml 源码归档不可达→vendor 本地源码 → **reject**：本轮是 configure
  依赖解析（arrow）问题，与源码归档/下载/网络镜像完全无关。
- [经验 2] test_package 编译标准与库一致 → **reject**：本轮是主配方 configure 对
  apache-arrow 的强依赖问题，与 test_package 消费方编译标准无关。
- 本轮为策略周期第 3 次未通过，改走**不同于前两轮**的地图：不再"补箭头/补门控"，
  而是据源码审计判定 arrow 根本不必要，直接移除依赖与补丁 0006。


## 20. Round-13 真机失败与修复（2026-09-19）—— 重生成 0007 补丁以匹配去掉 0006 后的源码状态

### 失败

- 失败阶段：compile（`build()` 的 `apply_conandata_patches(self)`，conanfile 行 268）。
- 直接证据（真机 log）：
  ```
  vineyard/0.24.4: WARN: .../patches/0007-gate-module-dependent-tests.patch:   actual  : b'    endif()'
  vineyard/0.24.4: .../patches/0007-gate-module-dependent-tests.patch: source file is different - b'test/CMakeLists.txt'
  vineyard/0.24.4: ERROR: ... Failed to apply patch: .../patches/0007-gate-module-dependent-tests.patch
  ```
- 上游测试：发现 0，执行 0。

### 根因

Round-12 移除了 0006 补丁（去 arrow 依赖），conandata `patches:` 应用顺序变为
0002→0003→0004→0005→0007。但 0007 补丁的 hunk 上下文（@@ -70,6 +70,32 @@）当初是
针对【0006 已应用】的 test/CMakeLists.txt 生成的：0006 在 add_test_case 宏里插入的
Arrow 相关行让插入点整体下移，所以 0007 应落在第 70 行附近。去掉 0006 后，唯一改动
test/CMakeLists.txt 的前置补丁只剩 0004（RPC/RDMA 跳过块），插入点实际在第 58 行。
0007 的 hunk 旧行号/上下文与真实文件不匹配：
- GNU `patch` 会用 fuzz/offset 容忍并成功（掩蔽错误）；
- 而 Conan 2.x 的 Python `patch` 库对 hunk 定位更严格，找不到匹配即报
  "source file is different" 并整体失败。

这是与 Round-10（hunk 头行数不匹配，patch stream is incomplete）【不同】的格式病：
本轮的旧 0007 行号/上下文偏移导致 Conan 无法定位。因此这次采用不同策略——用 `diff -u`
针对【去掉 0006 后的真实状态】重生成 0007，让 hunk 行号与上下文与源码完全对齐（无偏移）。

### 修复方案（重生成 0007）

1. 在干净 v6d-0.24.4 上先按 conandata 顺序应用 0002→0003→0004→0005（不含 0006），
   得到 insert 前的真实 test/CMakeLists.txt。
2. 用 Python 把 0007 的 keep-list 块插入到该文件（RPC/RDMA 跳过块之后、
   `message(STATUS "Found unit_test - " ...)` 之前），并顺手把块注释里 "+ arrow"
   改为 "+ glog/zstd"（arrow 已不再构建）。
3. `diff -u 原始 目标` 生成规范 unified diff，写回 `patches/0007-gate-module-dependent-tests.patch`
   （hunk 变为 @@ -58,6 +58,32 @@，与真实文件对齐）。
4. 全部 5 个补丁（0002/0003/0004/0005/新0007）在干净树上按 conan 顺序
   `patch -p1 --fuzz=0` 全部干净应用（零 fuzz/偏移）验证。

### 验证逻辑

- `--fuzz=0` 强制 GNU 不做模糊匹配；5 个补丁全部干净应用 ⇒ hunk 行号与上下文与真实
  文件完全一致（这是 Conan 严格 `patch` 解析器成功的必要条件）。
- 最终 test/CMakeLists.txt：add_test_case 宏为原始版（无 0006 的 Arrow 代码），
  keep-list `continue()` 在 `add_test_case` 之前 ⇒ 非 Linux 只构建/注册
  compressor/concurrent_memcpy/signature 3 个自含测试。
- Round-10 修的是"hunk 头行数不匹配"；本轮修的是"去掉前置补丁后 hunk 行号/上下文
  偏移不匹配"——两类都指向同一个原则：**conan 补丁必须用 diff 工具针对真实、最终
  应用顺序下的源码重生成，且用 --fuzz=0 校验零偏移**。

### 经验决策

- [经验 1] conandata.yml 源码归档不可达→vendor 本地源码 → **reject**：本轮是补丁
  0007 因 0006 移除后 hunk 行号/上下文偏移导致 Conan 应用失败，与源码归档/下载/网络
  完全无关。
- [经验 2] test_package 编译标准与库一致 → **reject**：本轮是主配方 apply_conandata_
  patches 对 0007 的严格定位失败，与 test_package 消费方编译标准无关。


## 21. Round-14 真机失败与修复（2026-09-19）—— test 目标找不到 glog 头 & glog 0.7.1 export 契约

### 失败

- 失败阶段：compile（`cmake.build(target="vineyard_tests")`）。
- 直接证据（真机 log）：
  ```
  test/compressor_test.cc:23: fatal error: 'glog/logging.h' file not found
  In file included from .../test/compressor_test.cc:23:
    .../src/common/util/logging.h:19:10: fatal error: 'glog/logging.h' file not found
  ```
- 上游测试：发现 0，执行 0。20:43 preflight 是【第一次】真正编译 3 个被保留的上游测试
  （compressor/concurrent_memcpy/signature），此前轮次都在更早阶段（configure/apply_patch）失败。

### 根因（两层，需同时满足 test 编译）

**A. glog 头文件不在 include 路径上（头缺失）**
- 真机 configure 已打印 `Found glog (include: .../vendored-glog/install/include, library: .../libglog.a)`，
  `GLOG_FOUND=TRUE`，`GLOG_INCLUDE_DIR`（缓存 var）与全局
  `include_directories(SYSTEM ${GLOG_INCLUDE_DIR})` 都会把 `vendored-glog/install/include` 加到
  test 目标 include 路径（本地 CMake 复现已证实：预置缓存变量时 find_path/find_library 直接返回缓存值，
  GLOG_FOUND=TRUE、GLOG_INCLUDE_DIRS=该路径、全局 include 命中 test 目标）。
- 但 test 仍报 `'glog/logging.h' file not found` ⇒ **vendored glog 的 `cmake --install` 在 OHOS 上
  没有把头文件装到 `<prefix>/include/glog/`**（lib 装上了、头没装上）。此前 client 一直能编过是因为：
  client 源文件（src/client/*、src/common/compression|memory|util/*.cc 等）里没有任何一个 include
  `<glog/logging.h>`（只有 `src/common/util/logging.h` 引用它，而无 .cc 包含 logging.h），所以 client
  从不真正需要 glog 头；只有 3 个保留 test（compressor/concurrent_memcpy/signature）包含
  `common/util/logging.h`（-> `<glog/logging.h>`），故测试编译首次暴露出头缺失。

**B. glog 0.7.1 的 export 契约：必须定义 `GLOG_USE_GLOG_EXPORT` 并提供 `glog/export.h`**
- glog 0.7.1 的 `src/glog/*.h`（logging.h/flags.h/raw_logging.h/vlog_is_on.h/log_severity.h）顶部是：
  ```
  #if defined(GLOG_USE_GLOG_EXPORT)
  #  include "glog/export.h"
  #endif
  #if !defined(GLOG_EXPORT) || !defined(GLOG_NO_EXPORT)
  #  error <glog/logging.h> was not included correctly. ...
  #endif
  ```
  无 fallback：`GLOG_EXPORT`/`GLOG_NO_EXPORT` 只由【生成的】`export.h` 提供，而 `export.h` 又只在
  `GLOG_USE_GLOG_EXPORT` 被定义时才 include。v6d 用 FindGlog（原始库路径）链接，`glog::glog` 目标上的
  PUBLIC `GLOG_USE_GLOG_EXPORT` 定义不会传播到 test 目标 ⇒ 即使头到位，也会触发 `#error`。

### 修复方案（conanfile 两张牌）

1. **保证头文件在位**：`_build_vendored_glog()` 在 `cmake --install` 后，把
   `src/glog/*.h`（8 个源头）与【构建目录生成的】`<bdir>/glog/export.h` 拷贝到
   `<prefix>/include/glog/`（与 `GLOG_INCLUDE_DIR` 指向的 include 目录一致）。幂等、无害。
2. **定义 `GLOG_USE_GLOG_EXPORT`**：`generate()` 向 `CMAKE_CXX_FLAGS` 追加 `-DGLOG_USE_GLOG_EXPORT`
   （client 不 include glog，无副作用），使 `glog/logging.h` include 到 `glog/export.h` 并满足 `#error` 守卫。
   静态构建下 `export.h` 生成 `GLOG_EXPORT=GLOG_NO_EXPORT=`（空），与静态链一致。

### 验证逻辑

- 头拷贝目标 = `_glog_prefix_dir()/include/glog` = `GLOG_INCLUDE_DIR` 父目录下的 glog 子目录：
  只要 include 路径（全局 include + GLOG_INCLUDE_DIRS）不变，`#include <glog/logging.h>` 必命中。
- `-DGLOG_USE_GLOG_EXPORT` 全局生效后，`#error` 守卫通过，`GLOG_EXPORT` 空值对静态链无碍。
- 3 个保留 test 均只经 `common/util/logging.h` 用 glog，修复对全部生效；client 侧无 glog 头依赖，不受影响。

### 经验决策

- [经验 1] conandata.yml 源码归档不可达→vendor 本地源码 → **reject**：本轮是 vendored glog 头在
  OHOS 上未装入 include + glog 0.7.1 export 契约问题，与源码归档/下载/网络完全无关。
- [经验 2] test_package 编译标准与库一致 → **reject**：本轮是主配方 test 目标（上游测试）编译
  glog 头/宏定义问题，与 test_package 消费方编译标准无关。

## 22. Round-15 真机失败与修复（2026-09-20）—— test 链接缺 vendored glog 静态库 libglog.a

### 失败

- 失败阶段：compile（`build()` 的 `cmake.build(target="vineyard_tests")`，conanfile 行 302）。
- 直接证据（真机 log）：
  ```
  [ 89%] Building CXX object test/CMakeFiles/concurrent_memcpy_test.dir/concurrent_memcpy_test.cc.obj
  make[3]: *** No rule to make target 'vendored-glog/install/lib/libglog.a', needed by 'bin/concurrent_memcpy_test'.  Stop.
  make[2]: *** [CMakeFiles/Makefile2:650: test/CMakeFiles/concurrent_memcpy_test.dir/all] Error 2
  make[1]: *** [CMakeFiles/Makefile2:205: CMakeFiles/vineyard_tests.dir/rule] Error 2
  make: *** [Makefile:182: vineyard_tests] Error 2
  ```
- 上游测试：发现 0，执行 0（test 目标根本没链接成功）。

### 根因

- 3 个保留 test（compressor/concurrent_memcpy/signature）的目标通过 `GLOG_LIBRARY`
  （= `<prefix>/lib/libglog.a` 的绝对路径，CMake 在 makefile 中转为相对
  `vendored-glog/install/lib/libglog.a`）直接链接 vendored glog 静态库。
- make 报 "No rule to make target" 意味着 `<build>/vendored-glog/install/lib/libglog.a`
  这个文件**在链接阶段根本不存在**。
- 这与 Round-14 观察到的现象同源：**该 OHOS 交叉工具链下 `cmake --install` 对 vendored
  glog 不可靠**——Round-14 已证实它没把头文件装到 `<prefix>/include/glog/`；同样的不可靠
  install 也会漏掉 `lib/libglog.a`（尽管 `cmake --build` 已在 glog 构建目录 `bdir/libglog.a`
  产出该静态库，`self.run` 未报错是因为 install 步骤 rc=0 但产物没落到预期路径）。
- configure 阶段的 `Found glog (library: .../libglog.a)` 是**假阳性**：`GLOG_LIBRARY` 被
  `generate()` 以绝对缓存变量预置，`FindGlog.cmake` 信任该缓存值、不再做真实文件存在性
  检查，所以 configure 不报错，链接时 make 才发现文件缺失。
- `package()` 里虽有 glog lib 拷贝，但那是**打包阶段**；test 链接发生在 `build()` 内、
  configure 后，来不及等到打包，`_build_vendored_glog()` 必须自己保证 lib 在位。

### 修复方案（沿用 Round-14 的头拷贝 belt-and-suspenders，扩展到静态库）

- 在 `_build_vendored_glog()` 的 `cmake --install` 之后、与头文件强制拷贝并列，新增：
  遍历 glog 构建目录 `bdir`（os.walk）找到 `libglog.a`，用 `conan_copy` 复制到
  `<prefix>/lib/`（`GLOG_LIBRARY` 指向的确切路径）。幂等（源头 `cmake --build` 产物），
  且不依赖 `cmake --install` 是否把 lib 落到预期位置。
- 找不到 `libglog.a` 时输出 warning，方便真机日志定位（正常情况下 `bdir/libglog.a`
  一定存在，因为 glog configure/build 已成功）。
- 本地复现验证：用同样 cmake 配置（`BUILD_SHARED_LIBS=OFF -DWITH_*` + 0001 补丁）在
  x86 gcc 上构建 glog，确认 `bdir/libglog.a` 存在、install 默认落 `lib/libglog.a`；修复的
  拷贝逻辑正是把这个 `bdir/libglog.a` 强制放到 `GLOG_LIBRARY` 所指路径，覆盖 OHOS install
  不可靠的情况。

### 经验决策

- [经验 1] conandata.yml 源码归档不可达→vendor 本地源码 → **reject**：本轮是 vendored
  glog 静态库在 OHOS 上未落到 `<prefix>/lib` 导致 test 链接失败，与源码归档/下载/网络镜像
  完全无关。
- [经验 2] test_package 编译标准与库一致 → **reject**：本轮是主配方内上游 test 目标链接
  vendored glog 静态库的路径问题，与 test_package 消费方编译标准无关。


## 23. Round-16 真机失败与修复（2026-09-20）—— ctest 顶层无 CTestTestfile，「No tests were found!!!」

### 失败

- 失败阶段：compile（`build()` 的 `_run_upstream_tests()`，conanfile 行 326/357）。
- 直接证据（真机 log）：
  ```
  [100%] Built target vineyard_tests
  vineyard/0.24.4: RUN: cd ".../build/Release" && ctest --output-on-failure > ctest_output.log 2>&1
  vineyard/0.24.4: Test project .../build/Release
  vineyard/0.24.4: No tests were found!!!
  RuntimeError: could not parse ctest summary from .../ctest_output.log
  ```
- 上游测试：发现 0，执行 0。注意：Round-15 的 glog 静态库修复已生效——`[100%] Built target
  vineyard_tests`，3 个保留 test（compressor/concurrent_memcpy/signature）已成功编译链接；
  本轮瓶颈移到 ctest 发现不到任何测试。

### 根因

- v6d 只在 `test/CMakeLists.txt`（子目录）第 1 行调用 `enable_testing()`；顶层
  `CMakeLists.txt` 从不调用。
- CMake 的行为：`enable_testing()` 只在被调用的目录及其后代生成 `CTestTestfile.cmake`。
  因为只写在 test/ 子目录，CMake 只在 `build/Release/test/` 生成 CTestTestfile.cmake，
  **顶层 `build/Release` 没有 CTestTestfile.cmake**。
- `_run_upstream_tests()` 从 `self.build_folder`（= `build/Release` 顶层）执行 `ctest`，
  顶层没有 CTestTestfile.cmake ⇒ ctest 报告 “No tests were found!!!”（尽管 test/ 下已注册
  3 个 add_test）。
- 本地最小复现证实：`enable_testing()` 只在 sub/ 子目录时，顶层 build/CTestTestfile.cmake
  **不生成**、ctest 顶层找不到测试；把 `enable_testing()` 放顶层后顶层 CTestTestfile.cmake
  生成，ctest 顶层即可发现并执行 sub/ 下的用例。

### 修复方案（新增补丁 0008：顶层 enable_testing）

- 新增 `patches/0008-enable-top-level-testing.patch`：在顶层 `CMakeLists.txt` 的
  `project(vineyard ...)` 之后加 `enable_testing()`，使顶层 build 目录生成
  CTestTestfile.cmake，ctest 从 build/Release 即可递归发现 test/ 下的 3 个保留用例。
- `conandata.yml` `patches:` 追加 0008（顺序 0002→0003→0004→0005→0007→0008，在干净树上
  `patch -p1 --fuzz=0` 全部零偏移应用验证）。
- 已核对 ctest 计数不会被第三方程污染：zstd 的 add_test 在 `if(ZSTD_BUILD_TESTS)`
  （find_zstd 置 OFF）、mimalloc 的 add_test 在 `if(MI_BUILD_TESTS)`（find_mimalloc 置
  OFF 且本回合 BUILD_VINEYARD_MALLOC=OFF 不调用）、libcuckoo 仅 enable_testing 无
  add_test 且不以 add_subdirectory 加入。故 ctest 仅含 test/ 下 3 个保留用例，与
  upstream_test_total=58、gated=55（ohos_feature gaps）的记账一致。
- manifest.yaml 更新 patches_applied 加 0008、knowledge_gained 记录该根因。

### 经验决策

- [经验 1] Conan 字典型 conf 读取方式 → **reject**：本轮是 CMake 测试发现（ctest 顶层
  CTestTestfile 缺失）问题，与 conan conf 字典读取完全无关。
- [经验 2] conandata.yml 源码归档不可达→vendor 本地源码 → **reject**：本轮是上游构建/
  测试注册问题，与源码归档/下载/网络镜像完全无关。

## 24. Round-17 真机失败与修复（2026-09-20）—— ctest 未真正运行测试，全部 "***Not Run"

### 失败

- 失败阶段：compile（`build()` 的 `_run_upstream_tests()`，conanfile 的 ctest 阶段）。
- 直接证据（真机 log）：
  ```
  1/3 Test #1: compressor_test ...................***Not Run   0.00 sec
  2/3 Test #2: concurrent_memcpy_test ............***Not Run   0.00 sec
  3/3 Test #3: signature_test ...................***Not Run   0.00 sec
  0% tests passed, 3 tests failed out of 3
  The following tests FAILED:
	  1 - compressor_test (Not Run)
	  2 - concurrent_memcpy_test (Not Run)
	  3 - signature_test (Not Run)
  RuntimeError: upstream vet test suite failed: 0/3 passed
  ```
- 上游测试：发现 3，执行 3，通过 0，失败 3。（注意：Round-16 的顶层 enable_testing 已生效，
  ctest 能发现 3 个用例，但每个都 “Not Run”——即 ctest 根本没启动测试二进制，0 断言执行。）

### 根因

- vineyard 上游 `test/CMakeLists.txt` 的 `add_test_case` 宏用**旧式** `add_test(${testname} ${testname})`
  注册每个测试，命令只是**裸可执行名**。CMake 只有在目标属于 ALL 时才会把裸名解析为二进制的
  **完整路径**；而本回合 `BUILD_VINEYARD_TESTS_ALL=OFF`（默认），所以 `add_executable(... EXCLUDE_FROM_ALL)`
  创建的测试目标**不会**被 add_test 解析成路径。
- 且顶层 `CMakeLists.txt` 设了 `CMAKE_RUNTIME_OUTPUT_DIRECTORY=${PROJECT_BINARY_DIR}/bin`，测试
  二进制落在 `build/Release/bin/`，不在 ctest 的查找位置（test/ 构建目录 + 各 config 子目录，
  即 `build/Release/test/{,Release,Debug,...}/`）。
- 结果：ctest 找不到可执行文件 → 每个用例报 “***Not Run”，0 断言真实执行 → passed=0 → 主配方
  `_run_upstream_tests` 抛 RuntimeError “0/3 passed” → compile 阶段失败。
- 本地 cmake 3.28 最小复现确认：旧式 `add_test(compressor_test compressor_test)` 在 EXCLUDE_FROM_ALL +
  自定义 RUNTIME_OUTPUT_DIRECTORY 下，生成的 CTestTestfile 为
  `add_test(compressor_test "compressor_test")`（裸名），ctest 报 “Unable to find executable ... Not Run”。

### 修复方案（新增补丁 0009：add_test 用绝对路径）

- 新增 `patches/0009-add-test-abspath.patch`：把 `add_test_case` 宏里的
  `add_test(${testname} ${testname})` 改为
  `add_test(NAME ${testname} COMMAND $<TARGET_FILE:${testname}>)`。
- `$<TARGET_FILE:...>` 生成器表达式无论 EXCLUDE_FROM_ALL / RUNTIME_OUTPUT_DIRECTORY 都展开为
  已链接二进制的**绝对路径**；CMake 把它写进 CTestTestfile：
  `add_test(compressor_test "/.../build/Release/bin/compressor_test")`，ctest 真正启动二进制并
  如实上报 Passed / Failed。
- 本地复现验证：改成 new-style+TARGET_FILE 后，故意让 signature_test `return 1`（失败桩），
  ctest 输出 `signature_test ...***Failed`（真真切到失败）、compressor_test 输出 `Passed`——证明
  harness 真能在二进制运行，pass/fail 计数来自测试框架真实结果，非猜测。
- 3 个保留测试（compressor/concurrent_memcpy/signature）均已核对源码，是**自含用例**：不连
  vineyardd、不依赖外部模块；compressor 对 1MB 随机数据往返压缩解压并校验、concurrent_memcpy
  对 8MB~776MB 大块做多线程 memcpy 并校验、signature 做 UUID 序列化往返校验。编译已通过
  （round-15/16 的 `[100%] Built target vineyard_tests`），运行即可真实通过。
- `conandata.yml` `patches:` 追加 0009（顺序 0002→0003→0004→0005→0007→0008→0009，在干净
  上游树 `patch -p1 --fuzz=0` 全部零偏移应用验证通过）。
- manifest.yaml 更新 patches_applied 加 0009、knowledge_gained 记录该根因。

### 经验决策

- [经验 1] Conan 字典型 conf 读取方式 → **reject**：本轮是 CMake `add_test` 路径解析（test 命令
  未指向已构建二进制）问题，与 conan conf 字典读取完全无关。
- [经验 2] conandata.yml 源码归档不可达→vendor 本地源码 → **reject**：本轮是上游测试注册/执行的
  CMake 语义问题，与源码归档/下载/网络镜像完全无关。

## 25. Round-18 真机失败与修复（2026-09-20）—— test_package 调用未限定命名空间

### 失败

- 失败阶段：compile（test_package 阶段，`test_package/conanfile.py` build() 的 `cmake.build()`）。
- 直接证据（真机 log）：
  ```
  [ 50%] Building CXX object CMakeFiles/test_vineyard.dir/test_package.cpp.obj
  test_package.cpp:24:21: error: use of undeclared identifier 'vineyard_version'; did you mean 'vineyard::vineyard_version'?
    const char* ver = vineyard_version();
                    ^~~~~~~~~~~~~~~~
                    vineyard::vineyard_version
  ...
  inline const char* vineyard_version() { return VINEYARD_VERSION_STRING; }
  1 error generated.
  ```

### 结果背景

- 上一轮（Round-17）的上游测试修复已生效：本轮真机日志显示「上游测试：发现 3，执行 3，通过 3，
  失败 0，跳过 0」——3 个保留用例（compressor/concurrent_memcpy/signature）真正运行且全部通过与
  ctest 门禁。本轮瓶颈已移到 test_package 冒烟用例的编译。

### 根因

- `test_package/test_package.cpp` 第 24 行以**未限定**方式调用 `vineyard_version()`，但该函数在
  `src/common/util/version.h` 中声明于 `namespace vineyard` 内（`inline const char* vineyard_version()`
  在 `namespace vineyard { ... }` 中）。因此裸调用 `vineyard_version()` 编译器报 undeclared，且明确
  建议改为 `vineyard::vineyard_version()`（错误信息里直接给出模板：`vineyard::vineyard_version`）。
- test_package.cpp 的 include（`client/client.h`、`common/util/version.h`）与本库 `package_info`
  includedirs（`include/vineyard`）解析正常——编译已越过 include 阶段，只卡在函数调用处的命名空间。

### 修复方案

- 把 `const char* ver = vineyard_version();` 改为 `const char* ver = vineyard::vineyard_version();`，
  与上游公共 API 的命名空间一致；同步更新文件头注释里对它的引用。
- 未改动任何断言逻辑/计数：仍验证 1) version 非空、2) vineyard::Client 默认构造未 Connected、
  3) InvalidObjectID()==numeric max，test_package 3 项断言保持不变。

### 经验决策

- [经验 1] Conan 字典型 conf 读取方式 → **reject**：本轮是 test_package 源码的 C++ 命名空间写法
  问题（未限定调用 namespaced 函数），与 conan conf 字典读取完全无关。
- [经验 2] conandata.yml 源码归档不可达→vendor 本地源码 → **reject**：本轮无源码下载/归档问题，
  与镜像/vendor 无关。
