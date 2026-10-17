# libheif-jpeg 1.23.0 适配笔记

## 编译环境

- 构建系统: cmake（上游根 `CMakeLists.txt` + `CMakePresets.json`；tarball 内另有
  `configure.ac` 残留，`init-build` 的启发式因此误探测成 autotools，已按实修正为 cmake）
- 编译日期: 2026-09-20
- 编译器: clang/clang++ 15.0.4（OHOS SDK 26.0.0.18，`--target=aarch64-unknown-linux-ohos`）
- Conan: 2.29.1（OHOS 适配版）+ profile `ci/conan/profiles/ohos-aarch64`
- 状态: built
- 设备: HarmonyOS PC / aarch64（`MemFree` 与 affinity 见 `$TASK_DIR/readiness.md`）

## 交付面判定（本包交付什么）

任务名 `libheif-jpeg` 属「**父 tarball 内的子模块**」这一类：上游没有独立的 `libheif-jpeg`
项目，但父 tarball `libheif-1.23.0` 的构建系统里有对应的**目标与产物**：

```cmake
# libheif/plugins/CMakeLists.txt:76-82
set(JPEG_DECODER_sources decoder_jpeg.cc decoder_jpeg.h)
plugin_compilation(jpegdec JPEG JPEG_FOUND JPEG_DECODER JPEG_DECODER)
set(JPEG_ENCODER_sources encoder_jpeg.cc encoder_jpeg.h)
plugin_compilation(jpegenc JPEG JPEG_FOUND JPEG_ENCODER JPEG_ENCODER)
```

`plugin_compilation()` 在 `PLUGIN_LOADING_SUPPORTED_AND_ENABLED AND WITH_<X>_PLUGIN` 时
`add_library(heif-${name} MODULE ...)` 并 `install(... LIBRARY DESTINATION ${COMPUTED_PLUGIN_INSTALL_DIRECTORY})`，
否则把源码静态编入宿主。故本包交付面 = **两个独立插件模块 + 它们赖以运行的宿主**：

| 产物 | 来源 | 说明 |
|---|---|---|
| `lib/libheif/libheif-jpegdec.so` | `libheif/plugins/decoder_jpeg.cc` → 目标 `heif-jpegdec` | JPEG → HEIF 解码后端插件 |
| `lib/libheif/libheif-jpegenc.so` | `libheif/plugins/encoder_jpeg.cc` → 目标 `heif-jpegenc` | HEIF → JPEG 编码后端插件 |
| `lib/libheif.so`（+ `.so.1`） | `libheif/`（同源同版本） | 插件宿主；运行期由它 `dlopen` 插件才注册后端 |
| `include/libheif/*.h`、`lib/pkgconfig/libheif.pc`、`lib/cmake/libheif/*` | 上游 install 规则 | 消费者链接面 |

> **上游目标名是 `heif-jpegdec`/`heif-jpegenc`，不是 `heif-jpeg`**；包名按任务卡的权威包目录名
> `archives/l/libheif-jpeg/1.23.0` 取（CI 分支名门禁按「分支名去前缀 == 包目录名-版本」精确匹配），
> 并保持同族 `libheif-<后端>` 口径。

**自包含交付宿主的原因**：插件以 `target_link_libraries(heif-${name} PRIVATE ${JPEG_LIBRARIES} heif)`
依赖宿主，运行期还必须由宿主 `dlopen` 才生效；仓库既有的 `archives/l/libheif/1.22.2` 是
`ENABLE_PLUGIN_LOADING=OFF` 的 codec-free 核心，**装不了插件**（且跨版本插件 ABI 不匹配），
不能作为本包依赖。

## 依赖边界与选型

JPEG 实现**不在树内**：`find . -iname '*jpeg*'` 只命中 `plugins/decoder_jpeg.{cc,h}`、
`plugins/encoder_jpeg.{cc,h}`、`heifio/decoder_jpeg.{cc,h}`、`tests/jpeg2000.cc`，全是**调用方**。
上游找实现的方式是 **CMake 内建 MODULE 包** `find_package(JPEG)`（`cmake/modules/` 下没有
`FindJPEG.cmake`），所以必须由外部包提供 `jpeglib.h` + `libjpeg.so`。

仓库内候选逐个实测 ohpcd 制品仓可得性（`conan download <ref> -r=ohpcd --only-recipe`）：

| 候选 | 制品仓 | 结论 |
|---|---|---|
| `libjpeg-turbo/3.2.0` | EXISTS | **选定** |
| `libjpeg-turbo/3.0.4` | EXISTS | 版本较旧 |
| `libjpeg-turbo/3.1.4.1` | absent（仓库有目录但未发布） | 不可用 |
| `libjpeg/10` | EXISTS | `default_options.shared=False`（R26 避免抢系统 SONAME），静态副本会进两个插件，且不能继承已签名的共享库结论 |
| `libjpeg9/9f`、`libjpeg6b/6b2` | EXISTS | 更旧 |

选 `libjpeg-turbo/3.2.0`：①IJG API/ABI 直接替代，装出的形态正是内建 `FindJPEG` 期望的；
②仓库内最新已发布的 libjpeg-turbo；③该配方已在本设备解决 OHOS 特有问题
（`WITH_SIMD=OFF` 规避 E096 链接失败、`_sign_shared_libs()` 规避鸿蒙 PC `dlopen` 的
`.codesign` 校验），复用即继承这两条结论。

**依赖如何被找到（实测，不是推断）**：配方既没有 `CMakeDeps`，也没有手钉
`JPEG_INCLUDE_DIR`/`JPEG_LIBRARY`。`CMakeToolchain` 会把依赖目录写进搜索路径：

```cmake
# <build>/generators/conan_toolchain.cmake
list(PREPEND CMAKE_LIBRARY_PATH "/…/.conan2/p/libjp…/p/lib")
list(PREPEND CMAKE_INCLUDE_PATH "/…/.conan2/p/libjp…/p/include")
```

于是内建 `FindJPEG` 的 `find_path`/`find_library` 直接命中 Conan 缓存：

```text
-- Found JPEG: /storage/Users/currentUser/.conan2/p/libjp48ea65bd29cfb/p/lib/libjpeg.so (found version "62")
```

⚠️ 这条链是「目录搜索」而非「目标解析」：若依赖漏声明，会**静默命中设备系统库**。
本包按 R36 显式声明 `requires("libjpeg-turbo/3.2.0")`，并用上面这行日志回读解析出的
绝对路径确实落在 Conan 缓存内。

## 源码获取

- 父 tarball：`https://github.com/strukturag/libheif/archive/refs/tags/v1.23.0.tar.gz`
- sha256：`50ea4fbd1e19c7b8820271d6d0c73f2623fec5d659ce9fae57e48dbeb94fab9a`
  （设备实测值；`conan create` 时 `get()` 按 conandata 的同值再校验一次，未报失败）
- 同批 6 个 libheif 子包共用这一个 tarball。本任务用离线种子
  `OHC_INIT_BUILD_TARBALL=<同批已下好的 libheif 1.23.0 tarball>` 喂 `init-build`，
  并复算 sha256 与官方 tag 归档一致；`conan create` 阶段由 conan 自行按 URL 下载并校验。

## 构建步骤

```sh
. "$HOME/tmp/libheif-jpeg-1.23.0/env.sh"
conan create "$PACKAGE_DIR" -pr:h="$HOST_PROFILE" -pr:b="$HOST_PROFILE" -c tools.build:jobs=1
```

`conanfile.py` 的 `generate()` 经 `CMakeToolchain` 下发（R33：不依赖 shell 环境变量）：

- 交付面：`BUILD_SHARED_LIBS=ON`、`ENABLE_PLUGIN_LOADING=ON`、`WITH_JPEG_DECODER=ON`、
  `WITH_JPEG_DECODER_PLUGIN=ON`、`WITH_JPEG_ENCODER=ON`、`WITH_JPEG_ENCODER_PLUGIN=ON`；
- 其余 19 个后端开关 + `WITH_UNCOMPRESSED_CODEC`/`WITH_WEBCODECS`/`WITH_LIBSHARPYUV` 全部 OFF；
- 非交付面：`WITH_EXAMPLES=OFF`、`WITH_GDK_PIXBUF=OFF`、`BUILD_TESTING=OFF`、`BUILD_DOCUMENTATION=OFF`；
- OHOS 专用：`_LIBCPP_ENABLE_EXPERIMENTAL`（见下）；
- `build()` 只构建 `heif`、`heif-jpegdec`、`heif-jpegenc` 三个目标（其余目标不被 `install()`）。

配置期交付面自证（逐字摘自构建日志）：

```text
-- Found JPEG: /storage/Users/currentUser/.conan2/p/libjp48ea65bd29cfb/p/lib/libjpeg.so (found version "62")
=== Summary of compiled codecs ===
…
JPEG decoder                          : + separate plugin
JPEG encoder                          : + separate plugin
x264 AVC encoder                      : - disabled
OpenH264 decoder                      : - disabled
…
Compiling 'jpegdec' as dynamic plugin
Compiling 'jpegenc' as dynamic plugin
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `libheif/box.cc:4155/4156/4166: error: no member named 'all_of'/'find' in namespace 'std::ranges'` | 上游 `CMAKE_CXX_STANDARD 20` + 3 处 C++20 ranges **算法**；OHOS SDK 的 libc++15（`_LIBCPP_VERSION 15004`）在 `__config` 里用 `#if !defined(_LIBCPP_ENABLE_EXPERIMENTAL) && !defined(_LIBCPP_BUILDING_LIBRARY)` → `#define _LIBCPP_HAS_NO_INCOMPLETE_RANGES` 把这两个算法整段隐藏，`-std=c++20`/`-std=c++2b` 都编不过 | `generate()` 对 OHOS 下发裸编译期宏 `_LIBCPP_ENABLE_EXPERIMENTAL`（`preprocessor_definitions[...] = None` → `add_compile_definitions("_LIBCPP_ENABLE_EXPERIMENTAL")`，实测落在 `CXX_DEFINES`）。**不改上游源码、无补丁**。三个限定条件均实测：①公共头 0 处 `std::ranges`（`grep -rn "std::ranges" libheif/api/` → 0），宏不必传播给消费者；②全树 0 处 `<format>`，宏顺带放开的 `_LIBCPP_HAS_NO_INCOMPLETE_FORMAT` 无副作用；③ranges 算法是**模板**，纯编译期可见性，**不需要** `-lc++experimental`（与 libpqxx 8.0.1 / ladybug 0.18.2 缺 `std::format` **运行期**符号的情形不同）。另评估过「3 行源码补丁改成 `std::all_of`/`std::find`」的替代方案，同样实测可用（`patch_ng strip=0` 应用通过、box.cc 编译通过），但**未采用**：宏方案上游源码零修改、且仓库已有先例 |
| 2 | `init-build` 把本包构建系统探测成 autotools | tarball 里存在 `configure.ac` 残留，启发式优先命中 | `manifest.yaml` 按实写 `build_system: cmake`（上游根有 `CMakeLists.txt` + `CMakePresets.json`） |
| 3 | 插件装载后是否真的注册？`WITH_REDUCED_VISIBILITY` 保持上游默认 ON 会不会藏掉 `plugin_info`？ | 需实测而非推断 | `plugins/*.h` 用 `MAYBE_UNUSED LIBHEIF_API extern heif_plugin_info plugin_info;` 声明，`LIBHEIF_API` 展开为 `visibility("default")`，宏由 `plugin_compilation()` 注入 `LIBHEIF_EXPORTS`+`HAVE_VISIBILITY`；`test_package` 断言 `heif_have_decoder_for_format(JPEG)==1` / `have_encoder==1` 实测通过（见下） |
| 4 | 插件被宿主 `dlopen` 时是否会被加载器拒绝（`Permission denied`）？ | OHOS 上 clang/lld 产物自带 `.codesign` 段，而 `cmake --install` 会剥掉安装出的 .so 的 build rpath（**原地改写字节**）→ 原签名与新内容失配 → 加载器对 dlopen 与 DT_NEEDED 一律回 `Permission denied`（`readelf`/属主/权限位全部正常，极易误判为路径或权限问题）。ML-0043 / E544 / E077 面；本包两个插件正是靠 dlopen 工作，命中面 100% | `package()` 末尾 `_sign_shared_libs()`：对 `lib/**/*.so*` 中的**真实文件**（跳过软链）执行 `llvm-objcopy --remove-section .codesign` + `binary-sign-tool sign -selfSign 1` 四步法重签。与 `libjpeg-turbo/3.2.0`、`libvdpau/1.5` 同法；仓库内 **1102** 个配方同款处置（`git grep -l binary-sign-tool upstream/main -- 'archives/*/*/*/conanfile.py' \| wc -l`）。设备侧负对照（同一份文件剥掉 `.codesign` 后 `dlopen` 报 `Permission denied`，重签后恢复）见 §「插件装载验证」 |
| 5 | 宿主共享库没有 `DT_SONAME`，插件的 `DT_NEEDED` 被写成**相对路径** | 设备 `uname -s` = `HarmonyOS`，Conan 也把 `os=OHOS` 映射成 `CMAKE_SYSTEM_NAME=HarmonyOS`，但 SDK 的 CMake 只有 `Platform/OHOS.cmake`、**没有 `Platform/HarmonyOS.cmake`** → configure 落进"未知平台"回退（实测日志 `System is unknown to cmake, create: Platform/HarmonyOS to use this system`）→ 平台模块的 SONAME 开关全不生效：①`libheif.so` 不写 `DT_SONAME`、不产版本化文件名；②插件链接同构建树的 `heif` 时 ld 只能把相对路径记进 `DT_NEEDED`（含斜杠 → 按 CWD 解析）→ 宿主 dlopen 插件必然失败。仓库既有 `libheif/1.18.2` 的 notes.md「NEEDED 字段硬编码相对路径、未解决」即此 | `generate()` 里 `tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"`（`cache_variables` 才能落进 toolchain 文件、在 `project()` 之前生效）→ 走 `Platform/Linux.cmake` 拿到 SONAME 规则（`libheif.so.1`）；实际目标三元组仍由 profile 的 clang `--target=aarch64-unknown-linux-ohos` 决定，不改变产物架构。仓库内 693 个配方同口径（例 `archives/a/ableton-link/3.1.2`）。验证读数见 §「插件装载验证」（`readelf -d` 的 `SONAME` 与 `NEEDED`） |

## 上游测试清点（rule4：N 与差额归因）

**主 N = 217**。单位 = 父 tarball 全量注册面中「用例/注册类」候选口径的**最大值**：

| # | 候选口径 | 读数 | 取数命令（cwd = 解包后的 `libheif-1.23.0`） |
|---|---|---|---|
| a | Catch2 `TEST_CASE` 注册数 | **217**（主 N） | `grep -rho 'TEST_CASE' tests/*.cc \| wc -l` |
| b | CTest `add_test` 注册数（全开关上限） | 39 | `grep -c 'add_libheif_test(' tests/CMakeLists.txt` (38) + `add_heifio_test` (1) |
| c | 测试可执行目标（全开关上限） | 39 | 同 b，一一对应 |
| d | 测试源文件 | 41 个 `.cc` | `ls tests/*.cc \| wc -l` |
| e | 断言宏 | 4016 | `grep -rhoE '(REQUIRE\|CHECK)(_FALSE)?\(' tests/*.cc \| wc -l`（REQUIRE 3994 + CHECK 18 + REQUIRE_FALSE 4） |

> e 属**另一单位**，只披露、不并入 N（四类口径不得混用）。另有 `SECTION(` 5 处、
> `GENERATE(` 43 处，属运行期展开，不构成新的注册单位。

**本次实测 N′ = 0**：本包按 `BUILD_TESTING=OFF` 构建，上游 `tests/` 目标不被 `install()`、
不属交付面。**在交付配置下的可编译面**（逐项归因）：

| 分类 | 目标数 | 用例数 | 归因 |
|---|---|---|---|
| 交付配置下**可编译** | 13 | 43 | 10 个只用公共 API 的目标 + `mini_decode` + `omaf` + `heifio/tiffdecode` |
| 不能编译：需 `WITH_REDUCED_VISIBILITY=OFF` | 10 | 73 | 8 个内部符号测试（bitstream_tests/box_equals/conversion/idat/jpeg2000/avc_box/file_layout/image_description_metadata）+ `mini_box` + `omaf_boxes`；交付的库用上游默认 `WITH_REDUCED_VISIBILITY=ON`，**为凑数把它关掉会改变被测制品的符号可见性**，不可接受 |
| 不能编译：需 `WITH_UNCOMPRESSED_CODEC=ON` | 13 | 91 | ISO/IEC 23001-17 未压缩编解码器整组：`uncompressed_decode`（含 mono/rgb/rgb16/rgb565/rgb7/ycbcr/ycbcr420/ycbcr422，共 9 个目标）+ `uncompressed_encode` + `uncompressed_box`（另需 visibility OFF）+ `uncompressed_encode_multicomponent`（另需 experimental）+ `uncompressed_decode_generic_compression`（另需 zlib）；该开关不属本包交付面 |
| 不能编译：需 `ENABLE_EXPERIMENTAL_FEATURES=ON` | 1 | 6 | `pixel_data_types`（同时还要求 visibility OFF） |
| 不能编译：需 `OpenJPEG` / `OpenJPH` 后端 | 2 | 4 | `encode_jpeg2000` / `encode_htj2k`；本包未交付、依赖未发布（R36） |
| **合计** | **39** | **217** | 13+10+13+1+2 = **39**；43+73+91+6+4 = **217**（行值与合计自洽）；不可编译部分合计 26 目标 / 174 用例 |

**结论：217 项上游用例全部 `NOT_RUN`**（不是 PASS）。技术原因：可运行面要求放开
`WITH_UNCOMPRESSED_CODEC` / `ENABLE_EXPERIMENTAL_FEATURES` / `WITH_REDUCED_VISIBILITY=OFF`
三个**与本包交付面无关**的开关，且都不改变交付物；其中 `WITH_REDUCED_VISIBILITY=OFF`
还会改变被测制品本身。**不为凑数字放开无关开关**。上游测试的替代验证见下节
（覆盖的是本包真正的交付面：JPEG 插件装载与端到端往返）。

## 验证结果

### 上游测试

- 上游用例总数 N = **217**（Catch2 `TEST_CASE` 注册数，父 tarball 全量注册面）
- 本次实际运行 N′ = **0**
- `PASS = 0` / `FAIL = 0` / `SKIP = 0` / `NOT_RUN = 217`（`TOTAL = 217`，口径闭合）
- 未全部通过的**技术原因**逐条见上表（差额 174 项按条件编译逐项归因）
- 取数命令：`grep -rho 'TEST_CASE' tests/*.cc | wc -l`（cwd = `libheif-1.23.0`）

### test_package（消费者视角，鸿蒙特有）

`conan create` 的 test 阶段自动执行，25 项 `check()` 断言全通过，分三层：

1. **链接面/指纹**：`find_package(libheif)` + `libheif::libheif`；`heif_get_version()=="1.23.0"`
   且版本号分量 `1.23.0`；
2. **运行面**：`LIBHEIF_PLUGIN_PATH` == 编译期 `LIBHEIF_PLUGIN_DIRECTORY`；`heif_init`；
   `heif_have_decoder_for_format(heif_compression_JPEG)==1`、`heif_have_encoder_for_format(JPEG)==1`
   （**证明交付的两个插件模块被宿主 dlopen 并注册**，不是「仅在册」）；
3. **反证 + 端到端**：HEVC/AV1/JPEG2000 后端必须为 0（证明没命中系统/别的包的 libheif）；
   16x16 RGB 纯色图 → `heif_context_encode_image(JPEG)` → 写 `.jpg` → `heif_context_read_from_file`
   → 尺寸仍为 16x16 → 解码像素在 ±10 内。

## 插件装载验证（设备实测读数，逐字）

三条平台处理的判据全部来自设备实测，不是推断。以下命令均可直接复跑
（`$P` = `conan cache path libheif-jpeg/1.23.0:<pkgid>`；`$J` = libjpeg-turbo 的包目录）。

### 1) SONAME / DT_NEEDED（对应问题 5）

```text
$ readelf -d $P/lib/libheif.so.1.23.0 | grep SONAME
 0x000000000000000e (SONAME)             Library soname: [libheif.so.1]

$ readelf -d $P/lib/libheif/libheif-jpegdec.so | grep NEEDED
 0x0000000000000001 (NEEDED)             Shared library: [libjpeg.so.62]
 0x0000000000000001 (NEEDED)             Shared library: [libheif.so.1]
 0x0000000000000001 (NEEDED)             Shared library: [libc++_shared.so]
 0x0000000000000001 (NEEDED)             Shared library: [libc.so]
```

`NEEDED` 是 `libheif.so.1`（SONAME），**不是**相对路径——加 `CMAKE_SYSTEM_NAME=Linux`
之前 configure 会打 `System is unknown to cmake, create: Platform/HarmonyOS`，宿主不写 SONAME，
插件只能把构建树相对路径记进 `NEEDED`（即 `libheif/1.18.2` notes.md 记录的未解决问题）。

### 2) install 就地改写 → 签名失效（对应问题 4）

```text
# 同一份插件：构建树 vs cmake 安装后（sha256 不同 ⇒ 字节被就地改写 ⇒ 链接期自签失效）
build 树 libheif-jpegdec.so   c3a66517a844db1aab1f2cbd85b13ea0a6d1d41c3ee5f6f317d11a21833dc06b
安装后 libheif-jpegdec.so     ed5d73dabdd68fa6a6fb19b394b61374a11c23a43d92e13ffe33f043e527699d
# 宿主不受影响（只链了同构建树 target 的插件目标才被改写）——只看宿主会误判
build 树 libheif.so.1.23.0    edc96bcd8d56355629e27588747652c55082993ca47d0b82fc0087e0c47e00ba
安装后 libheif.so.1.23.0      edc96bcd8d56355629e27588747652c55082993ca47d0b82fc0087e0c47e00ba   ← 相同
```

**负/正对照（同一份已安装插件）**：

```text
$ python3 -c "import ctypes,sys; ctypes.CDLL(sys.argv[1])" $P/lib/libheif/libheif-jpegdec.so
dlopen FAIL: Error loading shared library .../libheif-jpegdec.so: Permission denied      # 改写后（签名失效）

$ llvm-objcopy --remove-section .codesign $P/lib/libheif/libheif-jpegdec.so
$ binary-sign-tool sign -inFile $P/lib/libheif/libheif-jpegdec.so -outFile $P/lib/libheif/libheif-jpegdec.so -selfSign 1
$ python3 -c "import ctypes,sys; ctypes.CDLL(sys.argv[1])" $P/lib/libheif/libheif-jpegdec.so
dlopen FAIL: Error loading shared library libjpeg.so.62: (needed by .../libheif-jpegdec.so)
        ↑ 签名这一关已过（失败原因变成纯 DT_NEEDED 解析，补上 LD_LIBRARY_PATH 即通过）
```

处置有两条路，本包**两条都上**：①`generate()` 置
`CMAKE_BUILD_WITH_INSTALL_RPATH=True` + `CMAKE_INSTALL_RPATH=""`，让 build rpath ==
install rpath == 空 → install 判定无需改写 → 逐字节相同、签名原样保留（**根因**）；
②`package()` 末尾 `_sign_shared_libs()` 重签（**仓库 1100+ 配方的标准兜底**，并覆盖
任何后续就地改写的场景）。①生效后②是幂等的加固，不再是唯一防线。

### 3) 消费者验证 25/25（`test_package`）

```text
$ LD_LIBRARY_PATH="$P/lib:$J/lib" LIBHEIF_PLUGIN_PATH="$P/lib/libheif" ./test_libheif_jpeg
=== libheif-jpeg 1.23.0 consumer test ===
heif_get_version() = 1.23.0
LIBHEIF_PLUGIN_DIRECTORY = …/p/lib/libheif
LIBHEIF_PLUGIN_PATH      = …/p/lib/libheif
heif_init() -> code=0 msg=Success
heif_context_get_encoder_for_format(JPEG) -> code=0
heif_context_encode_image() -> code=0
heif_context_read_from_file() -> code=0
decoded handle: 16x16
  roundtrip pixel[0,0] = RGB(198,101,50)      # 源 RGB(200,100,50)，有损 JPEG 偏差 2/1/0
RESULT: pass=25 fail=0
```

`heif_init()` 返回 0 且 `heif_have_decoder_for_format(JPEG)==1` /
`heif_have_encoder_for_format(JPEG)==1` ⇒ 两个交付插件都被宿主 `dlopen` 并注册；
HEVC/AV1/JPEG2000 全为 0 ⇒ 没有命中系统或别的包的 libheif。

## 交付物

| 文件 | 说明 |
|---|---|
| `lib/libheif/libheif-jpegdec.so`（+ `.so.1`/`.so.1.23.0`） | JPEG 解码插件模块（上游目标 `heif-jpegdec`） |
| `lib/libheif/libheif-jpegenc.so`（+ `.so.1`/`.so.1.23.0`） | JPEG 编码插件模块（上游目标 `heif-jpegenc`） |
| `lib/libheif.so`（+ `.so.1`/`.so.1.23.0`） | 插件宿主（`ENABLE_PLUGIN_LOADING=ON`） |
| `include/libheif/*.h` | 公共头 |
| `lib/pkgconfig/libheif.pc`、`lib/cmake/libheif/libheif-config*.cmake` | pkg-config / CMake 消费者元数据 |

## 注意事项

1. **包名 ≠ 消费者的 `find_package` 名**：Conan 包名 `libheif-jpeg`，但 `package_info()` 导出的
   是宿主 `libheif`（`cpp_info.libs=["heif"]`、`cmake_file_name`/`cmake_target_name`/
   `pkg_config_name` 全取宿主名）。插件是 MODULE 目标，**不能**进 `cpp_info.libs`。
2. **插件目录必须靠环境变量**：上游把 `LIBHEIF_PLUGIN_DIRECTORY` 编译期钉死成构建时的
   `${CMAKE_INSTALL_FULL_LIBDIR}/libheif` 绝对路径，跨缓存/跨机不可移植；本包用
   `runenv_info` 导出 `LIBHEIF_PLUGIN_PATH`（上游读**单数**；头文件注释里的复数 `PATHS` 是过期文档），
   消费者需经 `conanrun` 环境（`VirtualRunEnv`）运行。
3. **同族 6 个 libheif 子包共用同一 tarball**（libde265/openh264/openjpeg/svtenc/aom/dav1d），
   每个子包各自自包含交付同一份宿主；宿主 `libheif.so` 在多个包之间是**同源同版本同 ABI**，
   但 Conan 会各自装一份（互不冲突，只是不共享）。
4. **ranges 宏只对 OHOS 下发**：`_LIBCPP_ENABLE_EXPERIMENTAL` 只在 `settings.os == "OHOS"` 时
   定义，不影响其它平台；它对本包是「打开被 libc++15 隐藏的标准算法声明」，不改变 ABI。
5. **消费者互斥提示（重要）**：本包 `package_info()` 与已合入主线的
   `archives/l/libheif/1.22.2`（codec-free 核心）导出**完全同名**的消费者标识
   （`libs=["heif"]`、`cmake_file_name="libheif"`、`cmake_target_name="libheif::libheif"`、
   `pkg_config_name="libheif"`）——这是**有意为之**：六个 codec 子包对消费者是同构可替换的
   （链接面相同，差异只在运行期装载了哪些插件）。因此消费者**同一构建里只能 requires 其中一个**；
   同时 requires `libheif/1.22.2` 与本包会导致同名目标/同名 `libheif.so` 冲突（且 1.22.2 是
   `ENABLE_PLUGIN_LOADING=OFF`，即使不冲突也装不了插件）。需要其它后端时，改用对应的
   `libheif-<后端>` 子包，不要叠加。
