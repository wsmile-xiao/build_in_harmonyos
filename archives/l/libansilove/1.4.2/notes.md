# libansilove 1.4.2 编译笔记（HarmonyOS PC）

## 上游核实

- 官方源码：GitHub release 资产 `https://github.com/ansilove/libansilove/releases/download/1.4.2/libansilove-1.4.2.tar.gz`（62,575 字节）
- SHA256：`8bd4d0775ff558aacfebd7e7e284baa96d781183bf767283bf8410f44a2e2434`
- License：BSD-2-Clause（LICENSE 文件）
- 构建：CMake ≥ 3.10、C99；objlib 结构同时产出 `libansilove.so`（VERSION 1.4.2 / SOVERSION 1）与 `libansilove-static.a`，无 BUILD_SHARED_LIBS 开关
- 依赖：GD 库（`find_path(gd.h)` + `find_library(gd)`）+ libm；PNG 输出经 `gdImagePngPtr()`，libpng/zlib 为 GD 的传递依赖
- 公共 API（include/ansilove.h）：`ansilove_init/error/loadfile/savefile/clean` + 7 个 loader（ansi/artworx/binary/icedraw/pcboard/tundra/xbin），`C_VISIBILITY_PRESET hidden`（默认隐藏）
- 上游测试：无（全树无 add_test/enable_testing；example 默认不构建；fuzz 需 sanitizer）。见 `reports/upstream-tests.md`

## 依赖决策

选 **gd/2.3.3**（包 `3017226d8c89ba5cd4aa962fb356382842603160`，已在 ohpcd 可下载）：
- 真 PNG 实现：二进制含 33 个 `png_*` 引用、`gdImagePngPtr` 为真实现，依赖 libpng/1.6.58 + zlib/1.3.1.1
- gd/2.3.3.2（`gd1556959be1e26`）为 PNG 桩版：配方 `ENABLE_PNG=OFF`，`gdImagePngPtr` 仅 8 字节桩、返回 NULL——libansilove 的核心功能（PNG 输出）会直接失败，不可用
- gd/2.3.3.1 依赖 freetype/fontconfig/webp/tiff/jpeg，对 PNG 输出链路过重

## 鸿蒙适配要点

1. **SONAME 注入**（libharu-2.3.0-missing-dt-soname 同根因）：HarmonyOS 无 `Platform/HarmonyOS.cmake`，`CMAKE_SHARED_LIBRARY_SONAME_C_FLAG` 为空 → 上游 `set_target_properties(SOVERSION 1)` 失效，产物无 DT_SONAME。修复：`CMAKE_PLATFORM_NO_VERSIONED_SONAME=ON` + `CMAKE_SHARED_LIBRARY_SONAME_C_FLAG=-Wl,-soname,`。在探索构建中实测：产物 `libansilove.so` 带 `SONAME libansilove.so`（无版本后缀，因 NO_VERSIONED_SONAME）。
2. **ohos.toolchain 自发现**：本仓库 glfw/libjpeg-turbo/zstd/libxml2 同法，绕开 conan_toolchain 的 os=OHOS 平台映射问题（cmake "System is unknown" 警告）。
3. **gd 静态链入 + png/zlib 补链**：gd/2.3.3 为静态库，对象完整链入 libansilove.so（NEEDED 无 gd），但其 png_*/z_* 符号在 .so 链接时必须解析——OHOS lld 对最终产物强制 `--no-allow-shlib-undefined`，需在 CMAKE_SHARED_LINKER_FLAGS 补 `-lgd -lpng16 -lz`（上游只 find_library(gd)）。产物 NEEDED = libpng16.so.16 + libz.so + libc.so。
4. **.codesign 重签**：cmake 直出 .so 的自签无效，`_sign_shared_libs` 剥旧 `.codesign` 段后 `binary-sign-tool -selfSign` 重签（CI 环境）。
5. **musl compat**：上游 `config.h` 自带 `strtonum`/`reallocarray` 回退（check_function_exists 探测），musl 均已提供，无需补丁。
6. **OHOS toolchain 下 find_library 看不到 Conan gd 库**（远端 CI 失败根因，PR #9925）：官方 OHOS CMake toolchain 的库搜索根路径规则受 `CMAKE_SYSROOT` 约束，上游 CMakeLists.txt 的 `find_library(GD_LIBRARIES gd REQUIRED)` 在 `CMAKE_PREFIX_PATH`/`-L` 均不命中的情况下配置阶段直接失败（本机曾因缓存路径恰好可见而侥幸通过）。`CMAKE_PREFIX_PATH`、`link_directories`、追加 `-L` 只影响搜索路径，不能保证命中。修复：build() 中从 `self.dependencies["gd"]` 的 `package_folder` 与 `cpp_info` 元数据（includedirs/libdirs 为相对 package_folder 的相对路径，Conan 2.x 消费侧不改写，需自行折叠为绝对路径）推导 gd.h 头文件目录与实际 libgd 库文件，fail-closed（元数据为空/头文件目录不存在/找不到库文件/候选歧义均抛错）后作为 cache 变量 `GD_INCLUDE_DIRS:PATH`、`GD_LIBRARIES:FILEPATH` 显式注入——cache 已有值时 find_path/find_library 直接短路，不再依赖 toolchain 默认搜索范围。含空格的 `CMAKE_*_LINKER_FLAGS` 须整体单引号包裹作为单个 argv 传递（空格安全）。与 E447（vendored FindSDL2 桥接）同族：均为 OHOS 交叉编译下 find_* 找不到 Conan 包、以依赖元数据显式注入 cache 变量修复。

## 构建产物（实测）

```
$ readelf -d libansilove.so
(SONAME) Library soname: [libansilove.so]
(NEEDED) Shared libraries: [libpng16.so.16]
(NEEDED) Shared libraries: [libz.so]
(NEEDED) Shared libraries: [libc.so]
$ readelf -S libansilove.so | grep codesign
  [31] .codesign PROGBITS ...
$ nm -D --defined-only libansilove.so | grep -c " T ansilove"
12  （init/error/loadfile/savefile/clean + 7 loader，visibility hidden 生效）
```

## 上游测试执行

上游无测试套件（0 个 add_test）。本仓库自有测试：
- `test_package/test.c`：25 个 CHECK（内联 ANSI/XBIN 全链路、PNG 尺寸断言、错误路径）
- `test_package/test_ohos.c`：13 项运行断言（源码 19 个 CHECK 位点，`#if/#else` 与
  `if/else` 互斥分支各只执行一侧；编译期 AArch64/musl + 真实 SGR ANSI 渲染 + 字体表索引）
- `test_package/test_elf.sh`：8 项 ELF 断言（源码 6 个 echo 位点，NEEDED 检查对
  libpng16/libz/libc 三库循环展开为 3 次执行）
- 合计 46 项断言全部 PASS（见 reports/conan-create.log，25+13+8）
