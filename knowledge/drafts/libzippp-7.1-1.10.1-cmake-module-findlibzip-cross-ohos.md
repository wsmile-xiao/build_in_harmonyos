# libzippp 7.1-1.10.1 — 上游 MODULE 模式 FindLIBZIP.cmake 的 OHOS 交叉链接线（draft）

**Category**: build-system | cmake | ohos · **Severity**: 2 · **Tool**: cmake/conan

## 症状

1. cmake configure 打印 `Found ZLIB: lib/libz.so`（相对路径），generate 阶段报
   `Imported target "libzip::zip" includes non-existent path "<builddir>/include"`。
2. 链接期 `ld.lld: error: unable to find library -llibzippp`（产物名与链接名不一致）。
3. 运行期 `Error relocating ...: _ZTISt9exception: symbol not found`（libc++_shared.so 不在加载路径）。
4. 编译期 `no type named 'libzippp_int64' in namespace 'libzippp'`（typedef 在全局作用域）。

## 根因

- 上游 `find_package(LIBZIP MODULE)` 走自带 `cmake/FindLIBZIP.cmake`，三组 find 缓存变量
  （LIBZIP_INCLUDE_DIR / LIBZIP_LIBRARY / _libzip_pkgcfg）在 FIND_ROOT_PATH=ONLY 交叉链下
  搜不到 conan 依赖包目录——除非配方用真实绝对路径预置。
- FindLIBZIP.cmake 内部裸 `find_package(ZLIB REQUIRED)`：zlib 若只是传递依赖（libzip 引的），
  配方拿不到其 package_folder，CMake 内置 FindZLIB 就在交叉链下解析出不存在的**相对路径**，
  configure 假成功、generate 死。
- 上游 `set_target_properties(PREFIX "")` 消重前缀 → 产物 lib/libzippp.so，链接名 `-lzippp`。
- C++ 测试二进制 NEEDED libc++_shared.so：SDK 里在 llvm/lib/aarch64-linux-ohos/，
  默认加载路径不含它，conanrun env 也不带——链接与运行都得显式给。

## 处置（可复用）

1. 配方 build() 里把上游 Find 模块要的全部缓存变量用 conan 依赖真实路径预置
   （-DLIBZIP_INCLUDE_DIR / -DLIBZIP_LIBRARY / -D_libzip_pkgcfg），并配
   ohos-find-deps.cmake preload（CMAKE_PROJECT_TOP_LEVEL_INCLUDES）。
2. **把传递依赖提升为直接 requires**（zlib 显式声明），才能给嵌套 find_package(ZLIB)
   预置 ZLIB_INCLUDE_DIR/ZLIB_LIBRARY——否则内置 FindZLIB 乱猜相对路径。
3. package_info.libs 按真实产物写（['zippp']）。
4. C++ 库的 test_package：链接加 `-L<SDK>/llvm/lib/aarch64-linux-ohos -lc++`，
   test() 运行时同路径注入 LD_LIBRARY_PATH。
5. 上游全局 typedef（libzippp_int64）不能写成 libzippp:: 前缀。

## 验证

ohos-aarch64（clang 15）conan create 全绿：configure "Found LIBZIP" 真实路径；
打包 lib/libzippp.so + include/libzippp/libzippp.h + lib/cmake/libzippp/；test_package
8/8 断言 PASS（真实 zip 写读往返：addData → close → getEntry → readAsText）。
