# libpano13 2.9.23 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-15
- 编译器: clang 15.0.4（OHOS NDK ohos.toolchain.cmake）
- 状态: published

## 编译步骤

1. `conan create . --version=2.9.23 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing`
2. 配方内裸 cmake + OHOS ohos.toolchain.cmake（绕开 conan_toolchain 的
   CMAKE_SYSTEM_NAME=HarmonyOS 映射，cmake 4.1.2 不识别该平台名）
3. 关键 cmake 参数：
   - `-DOHOS_ARCH=arm64-v8a`
   - `-DCMAKE_INSTALL_LIBDIR=lib`（ohos.toolchain 64 位默认装 lib64/，须改回 lib）
   - `-DCMAKE_C_FLAGS=-D__Ansi__`（见"遇到的问题"第 2 条）
   - `-DSUPPORT_JAVA_PROGRAMS=OFF -DUSE_SPARSE_LEVMAR=OFF`（可选特性默认关闭）
4. 依赖注入用 CMake 内置 find 缓存变量（JPEG_LIBRARY/PNG_LIBRARY/TIFF_LIBRARY/
   ZLIB_LIBRARY + INCLUDE 变量），绕过 FIND_ROOT_PATH_MODE=ONLY 交叉搜索限制

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 静态库 libpano13.a 归档失败 "Error running link command: no such file or directory" | OHOS SDK native/llvm/bin/ 只有 llvm-ar、无 llvm-ranlib；ohos.toolchain 把 CMAKE_RANLIB 固定为 SDK 内不存在的 llvm-ranlib 路径 | 配方内 `-DCMAKE_RANLIB=/data/service/hnp/bin/llvm-ranlib`（系统软链指向 llvm-ar）显式重指 |
| 2 | PTDialogs.c include sys_X11.h 报 libgimp/gimp.h not found | CMakeLists 的 `IF(UNIX) ADD_DEFINITIONS(-D__Ansi__)` 在 OHOS 上不生效（cmake 不识别 HarmonyOS 平台，UNIX 变量为假），源码落入 X11/GUI 分支 | `-DCMAKE_C_FLAGS=-D__Ansi__` 注入，使源码条件编译走纯 ANSI 分支（无 GIMP/GTK 依赖） |
| 3 | conan get() 下载 SourceForge URL 报 BadZipFile | SourceForge 下载 URL 以 /download 结尾，conan 无法从 URL 推断 tar.gz 格式 | conandata.yml 显式声明 `filename: libpano13-2.9.23.tar.gz` |
| 4 | test_package 运行期 "Error loading shared library libpano13.so.3" | libpano13 SONAME 为 libpano13.so.3，conanrun 聚合 env 未覆盖被测包自身 libdir | test() 中显式把所有依赖 libdirs 注入 LD_LIBRARY_PATH |
| 5 | tools 二进制 ctest 时 "Error loading shared library ../libpano13.so"（探索编译期） | CMake 生成 tools 的 NEEDED 为斜杠相对路径 ../libpano13.so，加载器按 cwd 解析 | 探索编译期在 build/tests/ 放置父目录符号链接；conan 配方经 -Wl,-rpath-link 与安装期部署规避（与 DRAFT-libjpeg-turbo 相对 NEEDED 同根因） |

## 源码修改

无（纯配方级适配，未改动上游源码，无 patches/ 补丁）

## 依赖版本

- zlib/1.3.1.1
- libpng/1.6.58
- libtiff/4.7.2（传递依赖 libjpeg-turbo/zstd/libwebp/xz 由制品仓自动解析）
- libjpeg-turbo/3.2.0

## 验证结果

```bash
# 上游 ctest（探索编译期，8/8 通过）
cd build && LD_LIBRARY_PATH=... ctest --output-on-failure   # 100% tests passed

# conan create 全流程（含 test_package API 断言）
conan create . --version=2.9.23 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
# panoProjectionFormatCount() = 22
# queryFOVLimits(1) -> rc=1 maxhfov=360.0 maxvfov=179.0
# libpano13 test OK
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | CMake 构建配方（含 ranlib/__Ansi__/find 变量注入） |
| conandata.yml | 源码声明（SourceForge + sha256 + filename） |
| test_package/ | 消费者测试（3 项 API 断言） |
| commands.json | 11 个命令行工具声明（PTblender/PTmender/PTinfo 等） |

## 注意事项

- 上游 2.9.23 从 autotools 迁移到 CMake 构建（2025-09-10 移除 FIND_PACKAGE(PkgConfig)）
- 可选特性 SUPPORT_JAVA_PROGRAMS（需 Java/JNI）与 USE_SPARSE_LEVMAR（需 SuiteSparse）
  默认关闭，不影响核心库与命令行工具功能
---

**编译结束**: 2026-09-15 03:57
**最终状态**: published
