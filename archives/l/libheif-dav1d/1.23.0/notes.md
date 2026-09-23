# libheif-dav1d 1.23.0 适配笔记

## 编译环境

- 构建系统: cmake
- 编译日期: 2026-09-20
- 编译器: clang/clang++（OHOS SDK `ohos-sdk_26.0.0.18`，`clang 15.0.4`，libc++ `15004`）
- profile: `ci/conan/profiles/ohos-aarch64`（`os=OHOS` / `arch=aarch64` / `build_type=Release`）
- 状态: built

## 本包是什么（交付面判定，依据逐字读上游 tarball）

`libheif-dav1d` 不是"另一个 libheif 变体"，而是 libheif 1.23.0 的
**AV1 解码插件**子包。上游把每个编解码后端做成「内置 / 独立插件」双形态：

```cmake
# CMakeLists.txt:101-104
macro(plugin_option optionVariableName displayName defaultEnabled defaultPlugin)
    option(WITH_${optionVariableName} "Build ${displayName}" ${defaultEnabled})
    option(WITH_${optionVariableName}_PLUGIN "Build ${displayName} as a plugin" ${defaultPlugin})
endmacro()
# CMakeLists.txt:219
plugin_option(DAV1D "Dav1d AV1 decoder" OFF ON)      # WITH_DAV1D 默认 OFF，WITH_DAV1D_PLUGIN 默认 ON
```

```cmake
# libheif/plugins/CMakeLists.txt:3-26  plugin_compilation()
if (${foundName} AND WITH_${optionName})
    if (PLUGIN_LOADING_SUPPORTED_AND_ENABLED AND WITH_${optionName}_PLUGIN)
        add_library(heif-${name} MODULE ${sources} ../api/libheif/heif_plugin.cc)
        target_link_libraries(heif-${name} PRIVATE ${${varName}_LIBRARIES} heif)   # ← DT_NEEDED 宿主
        install(TARGETS heif-${name} LIBRARY DESTINATION ${COMPUTED_PLUGIN_INSTALL_DIRECTORY})
    else ()
        target_sources(heif PRIVATE ${${optionName}_sources})                      # ← 静态编入宿主
```

于是交付面 = **`lib/libheif/libheif-dav1d.so`（MODULE 插件）+ 宿主 `lib/libheif.so`
+ `include/libheif/*.h` + `lib/pkgconfig/libheif.pc`**。插件不能单独交付：
链接期它 `DT_NEEDED` 宿主，运行期只有宿主 `heif_init()` 才会 `dlopen` 它。
宿主由本包在**同一棵树**里构建并随包交付，故自包含、无未发布前置依赖。

上游 configure 自证（`try3-conan-create.log`）：

```text
-- Found DAV1D: <dav1d package folder>/include
=== Summary of compiled codecs ===
Dav1d AV1 decoder                     : + separate plugin
libde265 HEVC decoder                 : - disabled
AOM AV1 decoder / AOM AV1 encoder     : - disabled
SVT AV1 encoder / Rav1e AV1 encoder   : - disabled
... 其余 15 个后端全部 - disabled
=== Supported formats ===
AVIF            YES        NO          ← 解码有、编码无（dav1d 是纯解码后端）
HEIC/AVC/JPEG/JPEG2000/VVC   NO   NO
```

## 依赖边界：dav1d 是外部包，不是内树捆绑

上游 `find_package(DAV1D)` 走 `cmake/modules/FindDAV1D.cmake`，内部是
`libfind_pkg_check_modules(DAV1D_PKGCONF dav1d)` + `find_path(NAMES dav1d/dav1d.h)`
+ `find_library(NAMES libdav1d dav1d)`。**树内没有 dav1d 源码副本**
（`-iname '*dav1d*'` 只命中该 Find 模块与 `libheif/plugins/decoder_dav1d.cc/.h`），
所以不存在"内树构建 dav1d"这条路。

复用仓库既有独立包 `archives/d/dav1d/1.5.0`。W0 实测（R35 口径，不用 `conan list`）：

```sh
conan install --requires=dav1d/1.5.0 --profile:host=ci/conan/profiles/ohos-aarch64 --build=never
# → dav1d/1.5.0:01d92cf349a0dd98ff915f4bd99a04430171517f Package installed（remote ohpcd）
#   包内实测有 include/dav1d/dav1d.h + lib/libdav1d.so + lib/pkgconfig/dav1d.pc
```

**不需要手工注入 `PKG_CONFIG_PATH`**：Conan 的 `CMakeToolchain` 默认带
`PkgConfigBlock`，会把 generators 目录前置进 `ENV{PKG_CONFIG_PATH}`
（`conan/tools/cmake/toolchain/blocks.py:731-736`），只要 `generate()` 里调过
`PkgConfigDeps(self).generate()`，`FindDAV1D.cmake` 的 `pkg_check_modules` 就能命中
Conan 生成的 `dav1d.pc`。

其余可选后端全部显式 OFF。注意其中 `LIBDE265` / `X265` / `X264` /
`OpenH264_DECODER` / `AOM_DECODER` / `AOM_ENCODER` 上游默认 **ON**，
不显式关掉会去探测系统同名库；`WITH_LIBSHARPYUV` 默认 ON（会找 libsharpyuv），
本包也显式关掉以保持构建自包含。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `libheif/box.cc:4155/4156/4166` 编译报 `no member named 'all_of'/'find' in namespace 'std::ranges'` | 上游顶层 `CMakeLists.txt:54` 声明 `CMAKE_CXX_STANDARD 20`（实际编译行确为 `-std=c++20`），而 OHOS SDK 的 libc++ 是 15004：`__config:247-254` 在 `!defined(_LIBCPP_ENABLE_EXPERIMENTAL) && !defined(_LIBCPP_BUILDING_LIBRARY)` 时定义 `_LIBCPP_HAS_NO_INCOMPLETE_RANGES`，`<__algorithm/*.h>` 的 ranges 重载全部 gated 在该宏上——**算法已实现但被隐藏** | 配方 `generate()` 里对 OHOS 加编译期宏 `_LIBCPP_ENABLE_EXPERIMENTAL`（不改上游源码、不需要 `-lc++experimental`、不需要补丁）。设备探针：同一文件不加宏报上述两条 error，加宏即通过。不污染消费者：`libheif/api/libheif/` 下 `std::ranges|std::views` 共 0 处 |
| 2 | 插件目录在下载安装的消费者那里失效 | 宿主搜索顺序（`libheif/init.cc:51-66`）是 `LIBHEIF_PLUGIN_PATH` 优先、为空才回退编译期宏 `LIBHEIF_PLUGIN_DIRECTORY`；而该宏是 **configure 期的构建目录绝对路径**（Conan 的 CMakeToolchain 在 configure 前把 `CMAKE_INSTALL_PREFIX` 设成构建期 package_folder，实测 `-DCMAKE_INSTALL_PREFIX=.../p/b/<hash>/p`），`conan create` 结束后包被搬到 `.../p/<name><hash>/p` | `package_info()` 用 `runenv_info.define_path("LIBHEIF_PLUGIN_PATH", <package>/lib/libheif)` 导出运行期路径；`test_package` 经 `conanrun` 取用，并断言该路径 == 产物实际所在目录（同批 openh264 / libde265 同口径） |
| 3 | 鸿蒙下 `dlopen` 插件可能失败 | 鸿蒙 PC XPM 要求被 `dlopen` 的 `.so` 带有效 `.codesign` 段，而 `cmake install` 的复制会破坏链接器自签 | `package()` 装包后重签 `lib/**` 的真实 ELF（`llvm-objcopy --remove-section .codesign` → `binary-sign-tool sign -selfSign 1 -signAlg SHA256withECDSA`），跳过版本化软链避免重复签。与仓库 1102 个配方、以及依赖包 `archives/d/dav1d/1.5.0` 的 `_sign_binaries` 同口径 |
| 4 | `install(TARGETS heif-dav1d ...)` 生成的无版本软链看似多余 | 宿主扫描插件目录时只认**以 `.so` 结尾**的文件名（`libheif/plugins_unix.cc:64-70`），`libheif-dav1d.so.1.23.0` 不命中 | 保留上游默认安装行为，不做裁剪；已在消费者测试里断言无版本名 `libheif-dav1d.so` 存在且为 ELF |
| 5 | 构建系统被 `init-build` 误探测为 autotools | 工具启发式；上游实际是 CMake（顶层 `CMakeLists.txt` + `project(libheif LANGUAGES C CXX VERSION 1.23.0)`） | `manifest.yaml` 的 `build_system` / `build.system` 人工核对为 `cmake`，`configure_options` 按 CMake 形态写 |
| 6 | **插件 `dlopen` 报 `Error loading shared library ../libheif.so`** | 设备 `uname -s` = HarmonyOS，而 SDK 的 CMake 只有 `Platform/OHOS.cmake`、**没有** `Platform/HarmonyOS.cmake`。Conan 为 `os=OHOS` 设 `CMAKE_SYSTEM_NAME=HarmonyOS` → CMake 落"未知平台"回退（configure 日志逐字：`System is unknown to cmake, create: Platform/HarmonyOS to use this system`）→ 宿主**不写 SONAME**、不出带版本的文件名（实测包里只有 `libheif.so`）→ 插件 MODULE 链接宿主时把**含斜杠的相对路径**记进 `DT_NEEDED`（实测 `readelf -d lib/libheif/libheif-dav1d.so` → `NEEDED [../libheif.so]`），含斜杠的 NEEDED 按 CWD 解析 → `heif_init()` 必然失败 | `generate()` 里 `tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"` 走 `Platform/Linux.cmake`。实测修后 configure 行含 `-DCMAKE_SYSTEM_NAME="Linux"`、不再出现 unknown platform；宿主 `SONAME = libheif.so.1`，插件 `NEEDED = [libheif.so.1]`（无斜杠）；包里同时出现 `libheif.so` / `libheif.so.1` / `libheif.so.1.23.0`。libheif 自身无 `CMAKE_SYSTEM_NAME` 平台分支（全树 grep 为空），故不影响其平台探测。仓库既有 693 个配方同口径 |
| 7 | **`cmake --install` 会就地改写 RUNPATH，破坏链接期代码签名** | CMake 默认 `BUILD_WITH_INSTALL_RPATH=OFF`，install 时把构建树 RUNPATH 改写/清空 → 产物字节变化 → 设备 clang launcher 在链接期写的 `.note.ohos.ident` 签名失效 → 加载器拒绝映射（错误是 `Permission denied`，不是 `not found`，极易误判为权限问题） | 本包用**装后重签**路线（同 3）：实测本包插件安装前后**同尺寸 68032 字节但 sha256 变**（`ee4ee2f8…` → `848fc43f…`），`RUNPATH` 从有（`<dav1d>/lib:<build>/libheif:`）变**完全消失**，安装后 `.codesign` 仍在；宿主 `libheif.so.1.23.0` 同样 `51cad762…` → `1d6762e4…` 且签名在。判据以**功能性证据**收口：`test_package` 的 `heif_init()` 与 `AV1 decoder registered` 两条断言 PASS，即插件确实被 `dlopen` 成功。同族另有"从源头不触发改写"路线（`CMAKE_BUILD_WITH_INSTALL_RPATH=True` + `CMAKE_INSTALL_RPATH=""`），本包未采用 |
| 8 | `test_package` 里用 `IMPORTED_LOCATION_RELEASE` 反推插件目录会静默取到假路径 | Conan 的 `CMakeDeps` 生成的 `<pkg>::<pkg>` 是 **INTERFACE IMPORTED** 目标（实测 `add_library(<pkg>_DEPS_TARGET INTERFACE IMPORTED)`），真实库路径在 `INTERFACE_LINK_LIBRARIES` 里，`IMPORTED_LOCATION_RELEASE` / `IMPORTED_LOCATION` **都未设置** | 改由 `test_package/conanfile.py` 的 `generate()` 用被测包真实 `package_folder` 注入 cache 变量 `HEIF_PLUGIN_FILE`，并在 `CMakeLists.txt` 里 `if(NOT DEFINED HEIF_PLUGIN_FILE) message(FATAL_ERROR …)` 让"没注入"硬失败。实测修后测试打印 `plugin artifact under test : <package_folder>/lib/libheif/libheif-dav1d.so`，产物断言由 6 条 FAIL 变 3 条 PASS |

## 源码修改

**无**。本包不改上游任何源码、不带 `patches/` 目录（`conandata.yml` 为 `patches: {}`）。
配方里保留了 `export_sources()` / `build()` 的 `export_conandata_patches()` /
`apply_conandata_patches()` 调用——在 `patches: {}` 下它们是 no-op，保留是仓库既有惯例
（同族先例 `archives/l/libheif/1.22.2` 同样保留），也是 `conan_verify` G1 配方完整性门禁
所检查的结构落点；补丁内容本身为零。
问题 1 由配方内的编译期宏解决，问题 2/3 由配方自身的 `package_info()` / `package()`
处理，均不触碰上游文件。

## 依赖版本

| 依赖 | 版本 | 形态 | 说明 |
|------|------|------|------|
| dav1d | 1.5.0 | 外部 Conan 包（`archives/d/dav1d/1.5.0`） | 唯一直接依赖；插件 `DT_NEEDED` 它，宿主不 NEEDED |

上游其余后端（libde265 / x265 / x264 / kvazaar / uvg266 / vvdec / vvenc /
OpenH264 / AOM 解码与编码 / SvtEnc / Rav1e / JPEG 解编码 / OpenJPEG 解编码 /
OpenJPH / FFmpeg / uncompressed / WebCodecs）全部显式 OFF，不进依赖集。

## 上游测试（R51 三步法）

### 1) 清点（N，父 tarball 完整注册面，用例类口径取最大值）

```sh
cd <解包后的 libheif-1.23.0>
grep -ho '^TEST_CASE' tests/*.cc | wc -l                                        # 217
grep -oE 'add_(libheif|heifio)_test\([a-z0-9_]+\)' tests/CMakeLists.txt | sort -u | wc -l   # 39
ls tests/*.cc | wc -l                                                           # 41
grep -hoE '\b(CHECK|REQUIRE|CHECK_FALSE|REQUIRE_FALSE)\s*\(' tests/*.cc | wc -l  # 4024（另一单位，不并入）
```

**N = 217**（Catch2 `TEST_CASE` 注册点，用例类；注册类为 39，取最大值）。
其余口径只披露不并入。四种口径（源码宏 / 框架注册 / assertion / 消费者断言）
不混用。

### 2) 实际运行（N′）

上游 ctest 在**独立的 `BUILD_TESTING=ON` 原生构建**里跑（与交付配置逐项同开关），
脚本：`$TASK_DIR/run-upstream-tests.sh`（可复现，沙箱 `HOME="$TASK_DIR/test-home"`）。

N′ = 本包配置下 ctest 实际注册 13 个目标、编译进二进制并可运行的用例数 = **35**：
**PASS 9 / FAIL 6 / SKIP 20**；未运行 **182**（未注册 174 + 编入排除 8）。
逐项归因、逐条技术原因与取数命令见 `reports/test-report.md`。

### 3) 如实回填

见 `reports/test-report.md`；未运行项逐条给技术原因，不写 PASS。

## 验证结果

采信轮（`tools/conan_verify_round.sh`，2026-09-20）**ROUND_RC=0**，判读为干净轮；
`conan-verify-report.md` 的 **Verdict: PASS**（G0/G1/G2/G3/G4/L4/L5 全 PASS；
L2 SKIP = 纯库包无 `bin/`，等价 smoke 见 `reports/conan-verify-supplement.md`）：

```text
Dav1d AV1 decoder                     : + separate plugin
AVIF            YES        NO          # 解码有、编码无（dav1d 是纯解码后端）
libheif-dav1d consumer contract: 13/13 assertions passed
```

构件读数（现存采信轮包，独立复核）：

```text
宿主  SONAME      : libheif.so.1
插件  DT_NEEDED   : libdav1d.so.7 / libheif.so.1 / libc++_shared.so / libc.so   （无斜杠路径）
宿主/插件 .codesign: 各 1 个 .codesign 段
lib/              : 3 个 .so（libheif.so / .so.1 / .so.1.23.0）+ lib/libheif/libheif-dav1d.so
include/          : 28 个头文件
交付库 zlib 符号   : 0（宿主既未动态链、也未静态链入 zlib）
```

上游用例（单位 = Catch2 用例）：声明 **N = 217**（父 tarball 完整注册面），
本包配置实际注册 13 个 ctest 目标、编入 **N′ = 35**，实测 **PASS 9 / FAIL 6 / SKIP 20**，
未运行 **182**（未注册 174 + 编入排除 8）。FAIL 6 全部在 `region`（上游缺编码器守卫）、
SKIP 20 全部为后端缺席；**Skipped 未计为 PASS**。逐条技术原因见 `reports/test-report.md`。

`finish` 的 Step 3 G0 干净构建验证**未通过且结构不适用**（裸 cmake 无 Conan toolchain →
`libheif/box.cc:4155/4156/4166` 的 `std::ranges` 三条 error），
按 SKILL.md Step 3「非阻塞、平台限制可跳过」如实登记，**不宣称通过**；实质门禁 W3/G2 已 PASS。

```bash
# 交付面
readelf -d  libheif-dav1d.so | grep NEEDED
readelf -d  libheif.so        | grep -i dav1d
readelf -S  libheif-dav1d.so  | grep -i codesign
# 消费者契约
./test_libheif_dav1d
```

## 注意事项

1. **本包只提供 AV1 解码**（dav1d 是纯解码后端），AVIF 编码需要 aom / rav1e / svtenc
   等编码后端，属同族其它子包的范围。
2. 插件依赖边落在**插件**上而不是宿主上：`readelf -d libheif.so` 看不到 libdav1d。
   后果是消费者只装宿主不会因缺后端而加载失败，只会**能力缺席**——所以消费者契约
   只能断言能力（`heif_have_decoder_for_format`），不能断言"链接成功"。
3. `WITH_REDUCED_VISIBILITY` 保持上游默认 **ON**。它与交付面无关，打开它只会让
   一部分上游单元测试能编译（`jpeg2000` / `bitstream_tests` 等需要内部符号），
   属于"为凑数字放开无关开关"，故不做。
4. 同批 6 个同构子包（libde265 / openh264 / openjpeg / svtenc / aom / jpeg）
   共用同一个上游 tarball，彼此**不互相依赖**；各自的产物名不同、插件不同。
