# flann 1.9.2 适配笔记

## 软件概况
FLANN (Fast Library for Approximate Nearest Neighbors), C++ 近似最近邻搜索库。
- 构建系统: CMake (上游 `cmake_minimum_required(2.6)`, 较老)。
- 产物: `libflann_cpp.{so,a}` (C++ API) + `libflann.{so,a}` (C API), 安装头文件到 `include/flann/`。
- 上游仓库: https://github.com/flann-lib/flann
- License: BSD-3-Clause。

## 核心难点: lz4 硬依赖
上游顶层 `CMakeLists.txt` 无条件要求 lz4:
```cmake
find_package(PkgConfig REQUIRED)
pkg_check_modules(LZ4 REQUIRED liblz4)
include_directories(${LZ4_INCLUDE_DIRS})
```
且 `src/cpp/flann/util/serialization.h` 直接 `#include <lz4.h>` / `<lz4hc.h>`, 用于索引保存/加载的流式压缩 (`LZ4_compress_HC_continue` / `LZ4_decompress_safe_continue` 等)。**没有任何 CMake 选项可关闭 lz4。**

HarmonyOS PC 现状:
- 无 system `liblz4` (`find / -name liblz4*` 在容器内为空)。
- 无 `pkg-config`。
- 制品仓 (ohpcd) 无 `lz4` conan 配方; conancenter 的 lz4 在 OHOS triplet 下不可用。

→ **方案: vendor lz4 1.9.4 源码做 superbuild。** 仅需 `lz4.c` + `lz4hc.c` 两个文件 (flann 不用 lz4frame, 故不需要 xxhash/lz4frame.c)。补丁 `patches/0001-cmake-vendor-lz4.patch` 把 pkg_check 段替换为:
```cmake
add_library(lz4_vendored STATIC ${CMAKE_SOURCE_DIR}/lz4/lib/lz4.c ${CMAKE_SOURCE_DIR}/lz4/lib/lz4hc.c)
set_target_properties(lz4_vendored PROPERTIES POSITION_INDEPENDENT_CODE ON)
set(LZ4_INCLUDE_DIRS ${CMAKE_SOURCE_DIR}/lz4/lib)
set(LZ4_LINK_LIBRARIES PRIVATE lz4_vendored)
```
`source()` 中把 lz4 1.9.4 解压到 `<source>/lz4/`。`LZ4_LINK_LIBRARIES` 被原 `src/cpp/CMakeLists.txt` 的 `target_link_libraries` 引用。flann 的 C++ API 是 header-only 模板, `flann_cpp.cpp` 几乎空 → 共享 `libflann_cpp.so` 不引用 lz4, PRIVATE 链入的 lz4 目标代码被链接器丢弃 (故 `.so` 仅约 6KB、运行期无 lz4 NEEDED)。但消费者 TU 经内联的 `serialization.h` 直接引用 lz4 符号, 必须另链 `lz4_vendored`。`lz4_vendored` 经 `install(TARGETS ... EXPORT flann-targets)` 安装 `.a` 到 `lib/` 供消费者链接 (CMake 导出文件在 `package()` 中 `rmdir` 删除)。

参考同类经验: [[hmbs-vendor-unpublished-dep-superbuild]] (id3v2 vendor id3lib 的 superbuild 模式)。

### 补丁细节 (构建期逐步踩出)
1. **CMake < 3.5 兼容移除**: 上游 `cmake_minimum_required(2.6)` → 加 `CMAKE_POLICY_VERSION_MINIMUM=3.5` (不改源码)。
2. **install(EXPORT) 报 lz4 不在导出集**: lz4_vendored 被 flann 的静态库 `flann_cpp_s/flann_s` 经 keyword-less `target_link_libraries` 引用, 进入其链接接口 → 必须 export。解法: `LZ4_LINK_LIBRARIES` 含 `PRIVATE` 关键字 (展开成 `target_link_libraries(t PRIVATE lz4_vendored)`), 并把 lz4_vendored `install(TARGETS ... EXPORT flann-targets)`; 同时不在其上设 source-dir include (用目录级 `include_directories`), 避免 export 校验拒绝源码路径。
3. **共享库链接报 recompile with -fPIC**: hnp clang 是 wrapper, CMake 把 compiler id 判成 unknown → 不给 SHARED 目标自动加 -fPIC。无条件 `tc.extra_cflags/cxxflags.append("-fPIC")` 解决 (静态库本就显式 -fPIC, 无害)。
4. **cmake --install 报 CMakeRelink.dir 找不到 .so**: OHOS cmake 不支持共享库 install 时 RPATH 重链接。`CMAKE_SKIP_RPATH=ON`, 运行期靠 conanrun 的 LD_LIBRARY_PATH。
5. **flann C++ 库近空 + 头间接 include lz4**: `flann_cpp.cpp` 几乎空 (C++ API 是 header-only 模板), 但公开头 `serialization.h` 内联 `#include <lz4.h>` → 消费者编译期要 lz4.h, 链接期要 lz4 符号。故 package() 把 `lz4*.h` 拷进 include/, package_info.libs 含 `lz4_vendored`。

### test_package 为何直接编译 (不走 CMakeDeps)
conan 2.29.1 的 CMakeDeps `find_library` 对带 soname 的近空共享库 `libflann_cpp.so` 报 "not found in package" (链路 .so→.so.1.9→.so.1.9.2 解析异常)。改用直接 `clang++` 编译链接, 编译器取自 `tools.build:compiler_executables` (容器=hnp wrapper, CI=OHOS clang)。
## 构建选项
关闭一切可选/外部依赖项, 只出核心 C/C++ 库:
```
BUILD_PYTHON_BINDINGS=OFF  BUILD_MATLAB_BINDINGS=OFF  BUILD_CUDA_LIB=OFF
BUILD_DOC=OFF  BUILD_EXAMPLES=OFF  BUILD_TESTS=OFF
USE_OPENMP=OFF  USE_MPI=OFF
```
- `USE_OPENMP=OFF`: 否则若 worker 找到 OpenMP 会让 `.so` 产生 libomp/libgomp 运行期依赖, OHOS 上未必存在 → 默认关闭更确定。
- HDF5/MPI: 上游 `find_hdf5()` 找不到仅警告 (非致命); `USE_MPI=OFF` 且无并行 HDF5 时 MPI 分支不触发, 不需 Boost。
- `BUILD_C_BINDINGS` 保持默认 ON, 同时产出 C API 库 (`libflann.so`)。

## 平台/系统名
- 容器中 conan profile `host==build (os=OHOS)`, conan 不写 `CMAKE_SYSTEM_NAME`, cmake 退回宿主。
- flann 唯一的 Linux 专属分支 (`if(CMAKE_SYSTEM_NAME STREQUAL "Linux" AND CMAKE_COMPILER_IS_GNUCC)`) 用 `dummy.c` + whole-archive 造共享库, 但**额外要求 GNUCC**, clang (`CMAKE_COMPILER_IS_CLANG`) 不满足 → 走 else 通用分支 (`add_library(flann_cpp SHARED ${CPP_SOURCES})` 直接编译)。因此显式 `CMAKE_SYSTEM_NAME=Linux` 安全, 与 charls 等库一致。

## 共享 vs 静态 / package_info
- flann 的 CMake **无条件同时编出静态 (`_s`) 与共享两套库**, `BUILD_SHARED_LIBS` 不影响其选择。
- 仍按铁律声明 `shared` 选项 (本仓 conan 2.29.1 对 library 类型强制要求), 默认 `shared=True`。
- `package_info`: `shared=True` 时 `libs=["flann_cpp", "lz4_vendored"]`; `shared=False` 时 `libs=["flann_cpp_s", "lz4_vendored"]` + `defines=["FLANN_STATIC"]`。两种模式都需链 vendored lz4 —— flann C++ API 是 header-only 模板, `flann_cpp.so` 近空、不含 lz4, 消费者 TU 经内联 `serialization.h` 直接引用 lz4 符号 (实测仅 `-lflann_cpp` 报 5 个 undefined lz4 符号)。

## 下游 cmake 配置冲突
flann install 会落 `lib/cmake/flann/flann-config.cmake` (引用其 targets export)。`test_package` 经 conan `CMakeDeps` 生成同名 `flann::flann`, 两者冲突 → `package()` 中 `rmdir(lib/cmake)` 删上游导出, 下游统一用 conan 目标。

## test_package
真实调用 flann C++ API: 200×5 点集, 建 4 棵随机 kd-tree (`Index<L2<float>>(dataset, KDTreeIndexParams(4))` + `buildIndex()`), 对"数据集第 7 行的副本"做 `knnSearch(nn=1)`, 断言命中索引 7 且距离 0。实质建索引 + 真实搜索 + 正确性校验, 满足 R34 (非空壳)。

上游 `test/*.cpp` 有 8 个 gtest 单测, 但依赖 GTest + HDF5 + 在线下载数据集 (cs.ubc.ca), 不适合 CI; 关闭 BUILD_TESTS, 用自带 smoke test。

## 验证命令 (容器内)
```
docker exec -e CONAN_HOME=/var/conan/flann-1.9.2 hmbs-builder hmbs-conan-init
docker exec -w "$PWD" -e CONAN_HOME=/var/conan/flann-1.9.2 hmbs-builder \
  conan create archives/f/flann/1.9.2 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

## 风险/待 CI 确认
- 容器 clang 是 Alpine musl (aarch64-alpine-linux-musl), CI worker 是 OHOS SDK clang (ohos sysroot); 编译产物运行行为以 CI 为准。本 test_package 只用纯 C++ 标准库 + flann, 不涉系统 API, 预期两边一致。
