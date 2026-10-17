# CMake `CheckLibraryExists` / `-l<name>` 型依赖在 OHOS 交叉构建下的接线

> **状态**：DRAFT（待主编评审提升为 E 条目）
> **来源**：zst 0.4 适配（HarmonyOS PC / aarch64 / clang 15 / cmake 4.1.2 / conan 2.29.1）
> **关联**：`knowledge/drafts/g3log-2.4-cmake-ohos-sysroot.*`（同属 CMake sysroot 探测类，但那条讲 FindBacktrace 回退，本条讲**依赖静态接线**）

## 适用场景（一类工程，而非某个库）
上游 CMake 工程用**功能探测**而不是 `find_package` 找依赖：

```cmake
include(CheckLibraryExists)
function(find_lib define so func)
  CHECK_LIBRARY_EXISTS(${so} ${func} "" HAVE_LIB${define})
  if(${HAVE_LIB${define}})
    set(libs ${libs} ${so} PARENT_SCOPE)     # 裸库名
  endif()
endfunction()
find_lib(Z z gzread)
find_lib(BZ2 bz2 BZ2_bzBuffToBuffCompress)
find_lib(LZMA lzma lzma_code)
find_lib(ZSTD zstd ZSTD_compress)
...
add_executable(app ${sources})
target_link_libraries(app ${libs})          # -lz -lbz2 -llzma -lzstd
```
（kilobyte/zst 的 `CMakeLists.txt` 即此形态；`config.h.cmake` 用 `#cmakedefine HAVE_LIBZ` 等落盘。）

## 两个坑

1. **头文件**：`compress.c` 里 `#include <zlib.h>` 等来自 conan 包；
   交叉链的 `FIND_ROOT_PATH_MODE=ONLY` 会滤掉 sysroot 之外的包路径 → 需要显式 `-I`。
2. **探测静默失败**：`CHECK_LIBRARY_EXISTS` 内部是 `try_compile`，它**不继承**最终链接的
   `CMAKE_EXE_LINKER_FLAGS`，也不认识 conan 包目录 → `-lzstd` 解析失败 → 返回 false →
   `config.h` 里 `#define HAVE_LIBZSTD` 缺失 → **编译"成功"但该压缩格式整体消失**。
   这是本条最危险的地方：没有编译错误，只有功能静默丢失。

## 修法（recipe 内完成，零上游源码改动）

1. 建**只含 `.a` 的私有 lib 目录**（搜索路径上没有 `.so`，`-l<name>` 必然解析到静态库）；
   这就是"想静态链接"的开关——否则链接器优先选 `.so`。
2. `-DCMAKE_C_FLAGS="-I<dep include>..."`（多路径需整体加引号，否则被 shell 拆成多个参数）。
3. **两个 `-L` 都要给**：
   - `-DCMAKE_REQUIRED_LINK_OPTIONS=-L<dir>` → 供 `check_*` 的 `try_compile`
   - `-DCMAKE_EXE_LINKER_FLAGS=-L<dir>` → 供最终链接
   缺一不可，且不能互相替代。
4. cmake 4.x 还需 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`（上游 `cmake_minimum_required(2.8.12)`
   会被 CMake ≥ 4.0 直接拒绝；见 `DRAFT-E321-cmake4-policy-version-minimum`）。

## 验证（防"静默降级"）
- configure 后 `grep '#define HAVE_LIB' <build>/config.h` → 四个都在；
  `grep HAVE_LIB <build>/CMakeCache.txt` → `HAVE_LIB*:INTERNAL=1`。
- 产物 `llvm-readelf -d` 核对 `DT_NEEDED`（全静态时仅 `libc.so`）。

## 参考实现
`archives/z/zst/0.4/conanfile.py` → `_static_lib_dir()` + `build()`。
依赖：`zlib/1.3.1`（仅 libz.a）、`bzip2/1.0.8.2`（仅 libbz2.a）、`xz/5.6.2`（仅 liblzma.a）、
`zstd/1.5.7.1`（同包含 `libzstd.a` + `libzstd.so`；对比 `zstd/1.5.7` 只有 `.so`）。
