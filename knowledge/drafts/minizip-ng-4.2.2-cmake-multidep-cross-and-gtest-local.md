# minizip-ng 4.2.2 — cmake 多依赖交叉接线 + SDK ranlib 缺位 + gtest 本地执行（draft）

**Category**: build-system | cmake | ohos | testing · **Severity**: 2 · **Tool**: cmake/conan/gtest

## 症状

1. 多依赖 cmake 包在 OHOS 交叉链下 find_package(ZLIB/OpenSSL/zstd/BZip2) 全空。
2. 造静态库报 `Error running link command: no such file or directory`（不指名哪个程序）。
3. test_package 链接报 `undefined symbol: mz_os_delete_file`。
4. gtest 套件本地跑 stream/encrypt 全挂：`mz_stream_os_open("LICENSE") Which is: -111`。

## 根因

- 交叉链 FIND_ROOT_PATH=ONLY：每个依赖都要预设自己的 `<Name>_DIR` 缓存变量（单靠
  CMAKE_PREFIX_PATH 不够——ohos.toolchain 用普通 set() 盖掉命令行 cache 变量）。
- ohos.toolchain.cmake 把 CMAKE_RANLIB 指 `$SDK/llvm/bin/llvm-ranlib`，SDK 只带 llvm-ar；
  造 .a 时 `<AR> qc && <RANLIB>` 第二步 ENOENT。
- minizip-ng 4.x API 更名：mz_os_delete_file → mz_os_unlink（readelf 验符号才能发现）。
- 上游 gtest 用例以相对路径开数据文件（LICENSE/test.p12/uniform.bin），必须从**源码根
  目录**起跑；在 build/test/ 下全部 -111（MZ_OPEN_ERROR）。

## 处置（可复用）

1. 配方 build() 对每个 requires 依赖：找 `<pkg>/lib/cmake/<name>` → `-D<Name>_DIR=` 预设
   （name/小写/大写三试 + 目录扫描兜底），配 ohos-find-deps.cmake preload。
2. 包本体走 .so（BUILD_SHARED_LIBS=ON）绕开 ar/ranlib；测试构建若必须 .a，传
   `-DCMAKE_RANLIB=/data/service/hnp/bin/llvm-ranlib` 且**清 CMakeCache**（旧 link.txt
   缓存旧 ranlib 路径，-D 改了也不生效）。
3. 写 test_package 前先 `readelf -W --dyn-syms` 对着真实导出符号核对 API 名。
4. CI 离线包的上游 gtest 套件：本地用 registry gtest/1.17.0 构建（GTEST_ROOT/GTest_DIR +
   MZ_FETCH_LIBS=OFF 类开关），从源码根目录执行，LD_LIBRARY_PATH 带 SDK libc++ 与
   openssl 包 lib。
5. musl 无 iconv → MZ_ICONV=OFF；MZ_LIBBSD=OFF 防交叉乱猜。

## 验证

ohos-aarch64 conan create 全绿：libminizip.so + include/minizip/ 打包签名；test_package
9/9（deflate 建包/读回往返）。上游 gtest 42/42 PASSED（stream/encrypt/compat/path/os/
crypt 全套，exit 0）。
