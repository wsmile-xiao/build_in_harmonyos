# libheif-openjpeg 1.23.0 适配笔记

> 软件：`libheif-openjpeg` 1.23.0（父 tarball `libheif` 1.23.0 的 OpenJPEG/JPEG 2000 编解码插件子包）
> worktree：`$HOME/ws/worktrees/libheif-openjpeg-1.23.0`；分支 `feat/libheif-openjpeg-1.23.0`
> 任务持久目录：`$HOME/tmp/libheif-openjpeg-1.23.0`（下称 `$TASK_DIR`，证据落这里）
> 构建系统：cmake（经 Conan `CMakeToolchain`）
> 状态：见 `manifest.yaml` 的 `status`

## 1. 交付面（本包到底装什么）

| 产物 | 上游来源 | 说明 |
|---|---|---|
| `lib/libheif/libheif-j2kdec.so`（+ VERSION/SOVERSION 软链） | CMake 目标 `heif-j2kdec` ← 树内 `libheif/plugins/decoder_openjpeg.cc` | JPEG 2000 **解码**插件模块（MODULE，运行期由宿主 dlopen） |
| `lib/libheif/libheif-j2kenc.so`（+ VERSION/SOVERSION 软链） | CMake 目标 `heif-j2kenc` ← 树内 `libheif/plugins/encoder_openjpeg.cc` | JPEG 2000 **编码**插件模块 |
| `lib/libheif.so`（+ 软链） | CMake 目标 `heif` | 宿主：插件以 `target_link_libraries(... heif)` 依赖它，且必须由它 `dlopen` 插件 |
| `include/libheif/*.h`、`lib/pkgconfig/libheif.pc`、`lib/cmake/libheif/*` | 同上 | 消费者编译/发现面 |

判定依据（解包上游 tarball 后原文，逐行）：

- `CMakeLists.txt:264-265` `plugin_option(OpenJPEG_ENCODER "OpenJPEG J2K encoder" OFF ON)` /
  `plugin_option(OpenJPEG_DECODER "OpenJPEG J2K decoder" OFF ON)`
  —— `plugin_option(optionVariableName displayName defaultEnabled defaultPlugin)`（`CMakeLists.txt:101-104`），
  两者的 `defaultEnabled` 都是 **OFF**。即上游不默认启用 OpenJPEG 后端，本包必须显式
  `WITH_OpenJPEG_{DECODER,ENCODER}=ON`。
- `CMakeLists.txt:266-279` `if (WITH_OpenJPEG_ENCODER OR WITH_OpenJPEG_DECODER) find_package(OpenJPEG 2)`
- `libheif/plugins/CMakeLists.txt:84-90`
  `plugin_compilation(j2kdec OPENJPEG OPENJPEG_FOUND OpenJPEG_DECODER OPENJPEG_DECODER)` /
  `plugin_compilation(j2kenc OPENJPEG OPENJPEG_FOUND OpenJPEG_ENCODER OPENJPEG_ENCODER)`
- `libheif/plugins/CMakeLists.txt:2-45` `plugin_compilation()`：
  `if (${foundName} AND WITH_${optionName})` 内再分两支——
  `PLUGIN_LOADING_SUPPORTED_AND_ENABLED AND WITH_<OPT>_PLUGIN` → `add_library(heif-${name} MODULE …)` +
  `install(TARGETS heif-${name} LIBRARY DESTINATION ${COMPUTED_PLUGIN_INSTALL_DIRECTORY})`；
  否则 `target_sources(heif PRIVATE …)` 静态编入宿主。

**为什么 encoder 与 decoder 都开**（不是为凑数字放开开关）：

1. 上游把「OpenJPEG 后端」定义为一对相邻开关（同一 `find_package` 门控、同一宏展开），
   包名就是该编解码库名（`openjpeg`）；只交付解码会让
   `heif_context_get_encoder_for_format(heif_compression_JPEG2000)` 无解；
2. 父 tarball 内**没有 J2K 语料**（`tests/data/` 无 J2K 样本；只有
   `fuzzing/data/corpus/j2k*.heif` 两个模糊测试输入），只有编码器在场才能对交付的**解码器**
   做真实往返验证——这正是上游 `tests/encode_jpeg2000.cc` 的 2 个用例与
   `test_package` 往返用例做的事。

## 2. 依赖边界（外部依赖，非内树捆绑）

```sh
cd "$TASK_DIR/upstream/libheif-1.23.0"
find . -iname '*openjp*' -o -iname '*openjpeg*' -o -iname '*j2k*'
# ./cmake/modules/FindOPENJPH.cmake            ← 另一个后端：OpenJPH / HT-J2K
# ./libheif/plugins/decoder_openjpeg.cc/.h     ← libheif 自己的适配层（非 OpenJPEG 本体）
# ./libheif/plugins/encoder_openjpeg.cc/.h
# ./fuzzing/data/corpus/j2k32.heif、j2k-siz-segment-undersized.heic   ← 测试语料
# ./tests/encode_htj2k.cc                      ← 用例（HT-J2K，与本包无关）
ls third-party/   # 只有 aom/dav1d/libpng/libsharpyuv/rav1e/svt 的 .cmd，无 OpenJPEG
```

→ 树内**没有 OpenJPEG 本体源码**，只能来自外部包。复用仓库既有独立包
`openjpeg/2.5.4`（`archives/o/openjpeg/2.5.4`，有 `conanfile.py`+`conandata.yml`，
manifest `status: built`；仓库内 5 个已合并包在用：imagemagick-full/7.1.2-23、leptonica/1.85.0、
opencv/4.12.0、poppler/25.12.0.2）。**不选** `openjpeg2/2.5.4` 的判据见 §3。

W0 真跑（R35：不用 `conan list/search` 判 binary）：

```sh
$ conan install --requires=openjpeg/2.5.4 -pr:h=<绝对 profile> -pr:b=<绝对 profile> --build=never
Requirements
    openjpeg/2.5.4#9f4e31751289e8fdf8faec21932895ed - Downloaded (ohpcd)
    openjpeg/2.5.4#…:30a828c3393c8a79c509dc8bed859f16757b162f#98a1e2430800b5723e771b77da9f2a0f - Download (ohpcd)
openjpeg/2.5.4: Package installed 30a828c3393c8a79c509dc8bed859f16757b162f
--- W0 OK: openjpeg/2.5.4
```

（逐字日志：`$TASK_DIR/pipeline-logs/s1-08-w0-deps.log`；清单与判据：`$TASK_DIR/w0-deps.txt`。）

## 3. CMakeDeps 对接（本包最容易踩的假绿点）

libheif 的 `plugin_compilation()` 用**全大写** `OPENJPEG_FOUND` / `OPENJPEG_LIBRARIES` /
`OPENJPEG_INCLUDE_DIRS` 判断与链接（宏体 `libheif/plugins/CMakeLists.txt:2-45`，`:21/:22` 用 `${varName}_INCLUDE_DIRS`/`${varName}_LIBRARIES`；j2kdec/j2kenc 两处注册在 `:86,90`），
而 CMakeDeps 在 **config 模式**只 set 与 `find_package` 同名大小写的 `OpenJPEG_*`；
且 CMakeToolchain 默认 `CMAKE_FIND_PACKAGE_PREFER_CONFIG=ON`
（`conan/tools/cmake/toolchain/blocks.py:678`）。二者叠加 → `OPENJPEG_FOUND` 未定义 →
`Not compiling 'j2kdec' backend` → **configure/install 全程 rc=0、包能建出来但没有插件**。

配方里的处置（`generate()`，不改上游源码）：

```python
deps = CMakeDeps(self)
deps.set_property("openjpeg", "cmake_find_mode", "module")
deps.set_property("openjpeg", "cmake_additional_variables_prefixes", ["OPENJPEG"])
```

另一层名字不一致：conan 包名是 `openjpeg`，仓库里另有同一上游库的 `openjpeg2/2.5.4`
（`cmake_file_name="openjpeg2"`，**命中不了** `find_package(OpenJPEG 2)`，且只有 1 个已合并包在用）。

设备实测**三态对照**（同机同依赖，只改 `set_property`；原始读数逐字留在
`$TASK_DIR/cmakedeps-three-way-evidence.txt`，逐字日志在
`$TASK_DIR/dep-wiring-evidence/probe-{config,both,openjpeg}-cmake.log`）：

| CMakeDeps 配置 | 生成的发现文件 | `OpenJPEG_FOUND` | `OPENJPEG_FOUND` | `OPENJPEG_LIBRARIES` | libheif 的后果 |
|---|---|---|---|---|---|
| 默认（config，无 `set_property`） | `OpenJPEGConfig.cmake` | 1 | **（空）** | **（空）** | `Not compiling 'j2kdec' backend` 静默降级 |
| `cmake_find_mode=both` + 前缀 | Config + Find 两套 | 1 | **（空）** | `OPENJPEG::OpenJPEG` | 仍静默降级（`PREFER_CONFIG=ON` 让 config 先赢） |
| `cmake_find_mode=module` + 前缀（本包采用） | 仅 `FindOpenJPEG.cmake` | 1 | **1** | `OPENJPEG::OpenJPEG` | `Compiling 'j2kdec' as dynamic plugin` ✅ |

三态的 `conan install` 与 `cmake configure` **退出码都是 0**——这就是"包能建出来但功能不在"
的假绿来源。`cmake_additional_variables_prefixes` 在 config 模式**不补 `_FOUND`**
（Conan config 模板里 `set(<PREFIX>_FOUND 1)` 只在 module 分支），故 `both` 形态下
`OPENJPEG_LIBRARIES` 有值而 `OPENJPEG_FOUND` 仍为空。

module 形态下逐字读数（`$TASK_DIR/probe-openjpeg/`）：

```text
FindOpenJPEG.cmake:35  set(OPENJPEG_INCLUDE_DIRS ${openjpeg_INCLUDE_DIRS_RELEASE} )
FindOpenJPEG.cmake:37  set(OPENJPEG_LIBRARIES ${openjpeg_LIBRARIES_RELEASE} )
FindOpenJPEG.cmake:63  set(OPENJPEG_FOUND 1)
-- PROBE OpenJPEG_FOUND=1
-- PROBE OPENJPEG_FOUND=1
-- PROBE OPENJPEG_INCLUDE_DIRS=…/p/openj175ac3bcf1357/p/include/openjpeg-2.5
-- PROBE OPENJPEG_LIBRARIES=OPENJPEG::OpenJPEG
-- PROBE OpenJPEG_VERSION=2.5.4
-- PROBE OPENJPEG_MAJOR_VERSION=        ← 空；首轮 find_package(OpenJPEG 2) 已命中，上游 2.x 兜底分支不执行
```

复现脚本（含 W0、探测、交付面 `readelf`/日志判据）：`$TASK_DIR/verify-openjpeg-dep-wiring.sh`。

## 4. 版本口径（两条轴，别混）

| 维度 | 值 | 判据 |
|---|---|---|
| 包 ref | `libheif-openjpeg/1.23.0` | 版本 = **父 tarball**（libheif 1.23.0）的版本（**已合并真先例**：`archives/l/libheif-tools/1.23.0` —— 同一 libheif v1.23.0 tarball、同 sha256；`archives/l/libhwy_contrib/1.3.0` ← highway 1.3.0） |
| `conandata.yml` url/sha256 | `https://github.com/strukturag/libheif/archive/refs/tags/v1.23.0.tar.gz` / `50ea4fbd1e19c7b8820271d6d0c73f2623fec5d659ce9fae57e48dbeb94fab9a` | 设备实算：`sha256sum $TASK_DIR/upstream/libheif-1.23.0.tar.gz`；同批 6+1 个子包共用这一份 tarball |
| OpenJPEG 本体版本 | `requires("openjpeg/2.5.4")` | 只在这里出现 |

推论：`init-build --auto` 按包名找源必然失败（设备实测 4 个同名异源/停放页候选全部被字节校验否决，
`$TASK_DIR/pipeline-logs/s1-09-init-build.log`）；正确做法是
`--url <父 tarball 官方 tag URL>` + `OHC_INIT_BUILD_TARBALL` 离线种子复用同批 tarball。

## 5. 上游测试清点（rule4）与执行台账

### 5.1 取数命令（设备可直接执行，全部在解包父 tarball 内）

```sh
cd "$TASK_DIR/upstream/libheif-1.23.0"
grep -rho 'TEST_CASE(' tests/*.cc | wc -l                            # a) Catch2 用例数
grep -hoE '^\s*add_(libheif|heifio)_test\(' tests/CMakeLists.txt | wc -l   # b) CTest 注册点
grep -l 'TEST_CASE(' tests/*.cc | wc -l                              # c) 含用例的测试源文件
ls tests/*.cc | wc -l                                                # d) tests/*.cc 总数
grep -rhoE '\b(REQUIRE|CHECK)(_[A-Z]+)?\(' tests/*.cc | wc -l        # e) 断言数（另一单位）
grep -rho 'SECTION(' tests/*.cc | wc -l                              # f) SECTION 数
grep -c 'add_executable' fuzzing/CMakeLists.txt                      # g) 模糊测试目标
```

### 5.2 候选口径（**不混用**，逐项读数）

| # | 口径 | 单位 | 读数 | 说明 |
|---|---|---|---|---|
| a | Catch2 `TEST_CASE` 用例 | 个用例 | **217** | 框架注册的用例数（`TEST_CASE_METHOD` 0 处、`SCENARIO` 0 处、无模板用例宏） |
| b | CTest `add_test` 注册点 | 个注册点 | 39 | `tests/CMakeLists.txt` 的 38 个 `add_libheif_test` + 1 个 `add_heifio_test`；**全开关上界**（本包配置实际注册 14 个，见 5.3） |
| c | 测试源文件（含用例） | 个文件 | 39 | 与 b 一一对应 |
| d | `tests/*.cc` 文件总数 | 个文件 | 41 | = 39 个含用例文件 + `main.cc` + `test_utils.cc` 两个无用例文件（Catch2 的 `catch_amalgamated.cpp` 是 `.cpp`，不被 `tests/*.cc` 这个 glob 覆盖，不在这 41 里） |
| e | 断言 `REQUIRE*`/`CHECK*` | 个断言 | 3998 + 18 = 4016 | **另一单位，只披露、不并入 N** |
| f | `SECTION` | 个分节 | 5 | 运行期在同一用例内展开，不构成新的注册单位 |
| g | 模糊测试目标 | 个目标 | 6 | `fuzzing/CMakeLists.txt` 的 `add_executable`，**不是** CTest 注册项（`WITH_FUZZERS` 单独门控） |

**主 N = max(a…d) = 217**（用例/注册类最大值，最保守，防少报）。
下界印证：父 tarball 全开关上界 39 个注册可执行测试、本包配置实际注册 14 个。

### 5.3 上游测试执行台账（TOTAL = PASS + FAIL + SKIP + NOT_RUN，用例单位）

本包 `BUILD_TESTING=ON`，14 个可执行测试随 `conan create` 真机执行。读数取自日志的
`HMBS_UPSTREAM_TEST_LIST=`（逐二进制 JSON）与 `HMBS_UPSTREAM_TEST_RESULT=`（合计）：

| 测试二进制（= CTest 注册项） | 用例数 | PASS | FAIL | SKIP | 断言 |
|---|---:|---:|---:|---:|---:|
| `entity_groups` | 1 | 1 | 0 | 0 | 3 |
| `grid_tile_missing` | 3 | 3 | 0 | 0 | 24 |
| `cxx_wrapper` | 1 | 1 | 0 | 0 | 0 |
| `encode_jpeg2000`（真编码 J2K） | 2 | 2 | 0 | 0 | 16 |
| `tiffdecode`（无 libtiff 时的 dummy 用例） | 1 | 1 | 0 | 0 | 0 |
| `encode` | 1 | 0 | 0 | 1 | 3 |
| `encode_grid` | 5 | 0 | 0 | 5 | 0 |
| `extended_type` | 1 | 0 | 0 | 1 | 3 |
| `tai` | 1 | 0 | 0 | 1 | 4 |
| `text` | 2 | 0 | 0 | 2 | 0 |
| `component_descriptions` | 6 | 0 | 0 | 6 | 0 |
| `mini_decode` | 2 | 0 | 0 | 2 | 0 |
| `omaf` | 4 | 0 | 0 | 4 | 20 |
| `region` | 7 | 0 | 6 | 1 | 21 |
| **合计** | **37** | **8** | **6** | **23** | **94** |

**台账（用例单位）**：TOTAL 217 = PASS 8 + FAIL 6 + SKIP 23 + **NOT_RUN 180**。
（217 = 父 tarball 全量注册面；37 = 本包配置下实际运行的用例数 N′；180 = 未注册/未运行的注册面用例。）

**逐项归因**：

- **FAIL 6（全部在 `region`）**：`region.cc:64/249/374/474/598/730` 直接调用
  `heif_context_get_encoder_for_format(ctx, heif_compression_AV1, &enc)`（**不经**上游的
  `get_encoder_or_skip_test()` 跳过助手）→ 本包不交付 AV1 编码后端 → 返回
  `heif_error_Unsupported_filetype`(3) → `REQUIRE(err.code == heif_error_Ok)` 报 `3 == 0`。
  让它们通过需要 AV1 编码后端（aom / svt-av1 / rav1e），而：① 属兄弟包
  `libheif-aom`/`libheif-svtenc` 的交付面；② 同批实测 `aom` 与 `svt-av1` **在制品仓不可得**
  （`conan install --build=never` rc≠0），R36 禁止声明未发布依赖；③ 改判据需改上游测试代码，
  本包不改上游测试。**替代验证**：J2K 方向的真实覆盖由 `encode_jpeg2000`（2 用例真编码，PASS）
  与 `test_package` 的 lossless 往返（真编码 + 真解码 + 保真度断言）承担。
- **SKIP 23**：全部由上游自己的跳过机制产生——`get_encoder_or_skip_test(HEVC/AV1)`
  （`test_utils.cc:180-197`，`SKIP("Encoder for HEVC/AV1 not found…")`）与用例内的
  `if (!heif_have_decoder_for_format(...)) return;` 守卫；本包不含 HEVC/AV1 编解码后端，
  属交付面裁剪的正确结果。**不影响本包交付面的任何功能**。
- **NOT_RUN 180**：见 §6 的门控逐项归因。

> ⚠️ **判读警告（本任务实测）**：只看 `ctest` 的汇总会**把上面 6 个 FAIL 掩蔽成 Skipped**——
> 上游 `tests/CMakeLists.txt:22,31` 给每个测试设了
> `SKIP_REGULAR_EXPRESSION "[1-9][0-9]* skipped"`，CTest 命中该正则即把整条测试标成 Skipped 并
> **忽略退出码**，于是"6 FAIL + 1 SKIP"被折成 Skipped、`ctest` 报
> `100% tests passed, 0 tests failed out of 14`。用例级台账（上表）才是真读数；
> 两者逐字对照见 `reports/test-report.md` 与 `$TASK_DIR/dev-build3.log`。


## 6. 本包配置下注册／未注册的用例（逐项归因）

本包刻意保持上游默认的 `WITH_REDUCED_VISIBILITY=ON`（只导出公开 API；已合并的
`archives/l/libheif/1.22.2` 同口径），因此 `tests/CMakeLists.txt` 中「需要内部符号」的注册项
无法编译，按 **NOT_RUN** 记账，**不为凑数字把它关掉**：

| 门控（`tests/CMakeLists.txt`） | 注册项数 | 本包 | 技术原因 |
|---|---:|---|---|
| `if (WITH_REDUCED_VISIBILITY) … else()` 内部符号组 | 8 | NOT_RUN | `bitstream_tests`/`box_equals`/`conversion`/`idat`/`jpeg2000`/`avc_box`/`file_layout`/`image_description_metadata` 需要 `libheif/api_structs.h`、`image/pixelimage.h` 等内部符号 |
| `ENABLE_EXPERIMENTAL_FEATURES AND NOT WITH_REDUCED_VISIBILITY` | 1 | NOT_RUN | `pixel_data_types`；实验特性未启用 |
| `NOT WITH_REDUCED_VISIBILITY AND WITH_UNCOMPRESSED_CODEC` | 1 | NOT_RUN | `uncompressed_box` |
| `WITH_UNCOMPRESSED_CODEC` 组 | 12 | NOT_RUN | `uncompressed_*` 10 项 + `uncompressed_decode_generic_compression`（另需 zlib）+ `uncompressed_encode_multicomponent`（还需 `ENABLE_EXPERIMENTAL_FEATURES`）；不属交付面 |
| `WITH_OPENJPH_ENCODER AND SUPPORTS_J2K_HT_ENCODING` | 1 | NOT_RUN | `encode_htj2k`（HT-J2K 是 OpenJPH 后端，非 OpenJPEG） |
| `NOT WITH_REDUCED_VISIBILITY`（`mini_box`、`omaf_boxes`） | 2 | NOT_RUN | 同上，需内部符号 |
| 其余（10 个公开 API 用例 + `mini_decode` + `omaf` + `tiffdecode` + `encode_jpeg2000`） | 14 | 见 5.3 | 本包实际注册并执行（`ctest -N` = 14） |

**特别注意**：`jpeg2000.cc`（30 个 J2K 用例）落在 `WITH_REDUCED_VISIBILITY` 组内，
因此本包**没有**跑它们——根因是上游把 J2K 盒解析用例放在需要内部符号的组里，
而不是本包"跳过了最重要的测试"；本包对 J2K 后端的真实覆盖由
`tests/encode_jpeg2000.cc`（2 个用例，真编码）+ `test_package` 往返（真编码 + 真解码）承担。

## 7. 编译期平台问题与处置

### 7.1 OHOS libc++ 缺 C++20 ranges 算法（会直接编译失败）

现象（本任务实测，`$TASK_DIR/dev-build1.log`）：

```text
libheif/box.cc:4156:25: error: no member named 'find' in namespace 'std::ranges'
libheif/box.cc:4155:23: error: no member named 'all_of' in namespace 'std::ranges'
libheif/box.cc:4166:22: error: no member named 'find' in namespace 'std::ranges'
3 errors generated.
```

判据链（设备实测，逐条可复跑）：

```sh
C=/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/include/c++/v1/__config
grep -n '_LIBCPP_VERSION\b' "$C" | head -1   # 39:#  define _LIBCPP_VERSION 15004
sed -n '247,256p' "$C"                       # !_LIBCPP_ENABLE_EXPERIMENTAL && !_LIBCPP_BUILDING_LIBRARY
                                             #   → #define _LIBCPP_HAS_NO_INCOMPLETE_RANGES
grep -n '_LIBCPP_HAS_NO_INCOMPLETE_RANGES' \
  /data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/include/c++/v1/__algorithm/ranges_all_of.h
                                             # 25:#if _LIBCPP_STD_VER > 17 && !defined(_LIBCPP_HAS_NO_INCOMPLETE_RANGES)
```

处置（配方 `generate()` 的 OHOS 分支，上游源码零修改、无补丁）：

```python
tc.preprocessor_definitions["_LIBCPP_ENABLE_EXPERIMENTAL"] = None
```

范围判定：全树用 `std::ranges` 的只有 `libheif/box.cc`
（`grep -rln 'std::ranges' libheif/ tests/ heifio/ examples/`）；公共 API 头 `libheif/api/**`
命中 **0** 处 → **不需要向消费者传播**；本包不碰 `<format>` 运行期符号 →
**不需要** `-lc++experimental`。同族先例：`archives/l/libpqxx/8.0.1`、`archives/c/cdo/2.6.3`、
`archives/m/mrc/1.3.17`。

### 7.2 OHOS 平台文件缺失 → 宿主无 SONAME → 插件 DT_NEEDED 写成路径（会毁掉整包）

现象（本任务独立复现，`$TASK_DIR/dev-build2.log` 那一轮）：

```text
$ readelf -d <build>/libheif/libheif.so | grep -E 'SONAME|NEEDED'
 0x0000000000000001 (NEEDED)             Shared library: [libc++_shared.so]
 0x0000000000000001 (NEEDED)             Shared library: [libc.so]
                       ← 没有 SONAME 行
$ readelf -d <build>/libheif/plugins/libheif-j2kdec.so | grep NEEDED
 0x0000000000000001 (NEEDED)             Shared library: [../libheif.so]   ← 含斜杠的路径
 0x0000000000000001 (NEEDED)             Shared library: [libopenjp2.so.7]
```

后果链（每一步都有上面读数）：宿主不写 SONAME → 插件 MODULE 记录给宿主的 `DT_NEEDED`
落成**含斜杠的相对路径** `../libheif.so` → 动态加载器对含 `/` 的名字按 CWD 解析
（不是按 RPATH/LD_LIBRARY_PATH）→ `heif_init()` `dlopen` 插件失败 → 注册不到 JPEG 2000 后端。
CTest 里直接体现为 2 个测试 FAIL（`tai`、`encode_jpeg2000` 的两条
`REQUIRE(err.code == heif_error_Ok)` 报 `3 == 0`），装出来的包里则表现为
`heif_have_decoder_for_format(JPEG2000) == 0`。

根因：设备 `uname -s` = `HarmonyOS`，conan 把它映射成 `CMAKE_SYSTEM_NAME=HarmonyOS`，
而 SDK/hnp 的 cmake 都只有 `Modules/Platform/OHOS.cmake`、**没有 `HarmonyOS.cmake`**；
名字对不上时 cmake 只打一行 `System is unknown to cmake, create: Platform/HarmonyOS …`
就继续，把一批平台变量留空——其中就有 `CMAKE_SHARED_LIBRARY_SONAME_C_FLAG`。

处置（配方 `generate()`，OHOS 分支）：

```python
tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
```

平台文件存在 → SONAME 正常（`libheif.so.1`）→ 插件 `DT_NEEDED` 变成无斜杠的
`libheif.so.1`，经 RPATH（构建树）/ `LD_LIBRARY_PATH`（装出来的包，conanrun 提供）解析。
仓库同口径 693 个配方（`archives/o/openjpeg2/2.5.4`、`archives/a/ableton-link/3.1.2` 等），
本任务是其中一个实例；知识条目见
`knowledge/drafts/DRAFT-cmake-harmonyos-platform-soname-flag.kv`。

> 该行在 `dev-build2` 轮**缺失**，是那一轮 `ctest` rc=8（2 个测试 FAIL）的唯一原因；
> `dev-build3` 轮带上后，ctest 由 rc=8（2 项 FAIL）转为 100% 通过（ctest 口径），用例级台账见 §5.3。

### 7.3 装后重签：`cmake --install` 就地改写 RUNPATH → ELF 签名失效 → 插件 dlopen 报 EACCES

现象（`$TASK_DIR/dev-build3.log`，test_package 段逐字）：

```text
  heif_init(NULL) -> code=11 (Cannot open plugin (dlopen).)
dlopen: Error loading shared library …/p/lib/libheif/libheif-j2kdec.so: Permission denied
dlopen: Error loading shared library …/p/lib/libheif/libheif-j2kenc.so: Permission denied
LIBSHEIF_OPENJPEG_CONSUMER checks_total=18 checks_passed=11
```

注意是 **Permission denied（EACCES）**而非 "not found"——文件在、权限也够。

根因（安装前后逐项实测，原始读数 `$TASK_DIR/resign-ab-evidence.md`）：

| 产物 | 构建树 sha256 | 安装后 sha256 | 相同 | RUNPATH |
|---|---|---|---|---|
| `libheif-j2kdec.so` | `86158e32…` | `488821aa…` | **否**（`cmp -l` 231 字节差） | 有 → 无 |
| `libheif-j2kenc.so` | `54822c59…` | `942dcfc5…` | **否** | 有 → 无 |
| `libheif.so.1.23.0`（宿主） | `d3c5792d…` | `d3c5792d…` | **是** | — |

即**只有链了同构建树 target 的产物被改写**（两个插件都 `target_link_libraries(... heif)`）；
宿主只链外部库 → 字节不变，**只看宿主会误判成"没问题"**。OHOS 的 clang 在链接期写入 ELF
签名（`.note.ohos.ident` / `.codesign`），字节一变签名即失效，装载器拒载。

处置（配方 `package()` 的 `_resign_installed_plugins()`，同族已合并先例
`archives/o/openh264/2.6.0`、`archives/f/ffmpeg/8.1.2`）：

```python
self.run(f'{objcopy} --remove-section .codesign "{path}" 2>/dev/null || true')
self.run(f'{signer} sign -inFile "{path}" -outFile "{path}" -selfSign 1')
```

A/B 实测（同一产物副本，`$TASK_DIR/dev-plugin-{nosign,resign}/`）：
不重签 → ❌ `Permission denied`；重签 → ✅ `dlopen: OK`（宿主与 openjpeg 的 `lib` 在
`LD_LIBRARY_PATH` 上）。

> **未采用**"从源头不改写"路线（`CMAKE_BUILD_WITH_INSTALL_RPATH=ON` + `CMAKE_INSTALL_RPATH=""`）：
> 它会把 14 个上游测试可执行文件的构建期 RPATH 一并清空，而实测 `conanbuild.sh`/`conanrun.sh`
> **都不设 `LD_LIBRARY_PATH`**（测试可执行文件当前正是靠 RPATH `…/build/Release/libheif` 找到
> `libheif.so.1`），等于用"上游测试跑不了"换"安装不改写"。故采用装后重签，二者都保住。
> `binary-sign-tool` 没有 `verify` 子命令（实测 `not trust command`），故"签名有效"没有独立
> oracle——唯一能验签的就是**真装载**，本包把它写进 `package()` 自检
> （`_assert_plugins_loadable`，输出 `HMBS_INSTALLED_RUNTIME_LOAD_OK`）。

### 7.3.1 `package()` 装载自检必须是 **exec 形态**（CI 红根因，2026-09-23）

本自检最初实现是 `self.run(<python> check_plugin_dlopen.py …)`，用 **`sys.executable` 起解释器做
`ctypes.CDLL`**：设备上通过（采信轮 `HMBS_PLUGIN_DLOPEN_OK`），但 **CI worker 上必然失败**，
build #54215 / #56625 / #56627 三次逐字同报

```text
OSError: Error loading shared library /storage/Users/currentUser/.cache/conan2/p/b/…/p/lib/libheif.so: Permission denied
  File "…/check_plugin_dlopen.py", line 3, in <module>
    ctypes.CDLL(host, mode=ctypes.RTLD_GLOBAL)
```

**根因不是签名失效，是 `E212`（hmmac 路径标签面，`knowledge/doc/E212.md` 关键词即含 `ctypes CDLL`）**：
worker 的 conan 跑在 HNP 解释器 `/data/service/hnp/bin/python3` 下（hnp_file 上下文），hmmac 只允许该
上下文加载 **hnp_file 标签**的 `.so`；交付物在 `/storage/Users/…`（hmdfs 标签）⇒ 该解释器 `dlopen`
**任何**用户目录 `.so` 一律 EACCES，**与签名状态无关**（同族 barvinok/0.41.9 build #33869 连已发布的
release 签名 `libgmp` 都被拒，原文 "a platform boundary … not a recipe failure"）。三条"产物没问题"
的自证（同一次构建内）：

| 证据 | 读数 |
|---|---|
| ① 同构建 `build()` 阶段上游 ctest | 与设备逐字一致：`encode_jpeg2000` 2/2、37/8/6/23、assertions 94、not_run 180 ⇒ **被 `exec` 起来的进程（hmdfs 上下文）dlopen 用户目录 `.so` 正常**，被拒的只是解释器进程 |
| ② 宿主安装前后 sha256（G3 判据） | `bdf93631c96c3464…` **完全相同**（构建树 vs `p/lib`），`.codesign` 段 1 个、`GNU_STACK RW` ⇒ 宿主未被 `cmake --install` 改写、签名有效 |
| ③ 裸环境加载探针 | `env -u LD_LIBRARY_PATH python3 -c "ctypes.CDLL('<宿主>')"` → `HOST_DLOPEN_OK` |

**修法（换判据形态，不是放松判据）**：`_assert_plugins_loadable` 改为拿构建树已建好的上游测试
可执行文件 `tests/encode_jpeg2000`（上游 `add_test(NAME encode_jpeg2000 COMMAND ./encode_jpeg2000)`、
无参数、cwd=tests 目录）指向**安装副本**再跑一次——`LD_LIBRARY_PATH=<本包 lib>+<依赖 lib>` 让它的
`NEEDED libheif.so.1` 按 ELF 规定先查 `LD_LIBRARY_PATH` 再查自身 `DT_RUNPATH`（⇒ 装出来的宿主真被
装载），`LIBHEIF_PLUGIN_PATH=<安装副本插件>` 让 `heif_init()` 绝对路径 dlopen 装出来的两个插件，
真 J2K 编码往返跑通。三项本机控制实验：

- **正**：安装副本宿主 + 安装副本插件 ⇒ `rc=0`、16 assertions / 2 用例；
- **反 1（宿主敏感性 + 搜索序）**：往 `LD_LIBRARY_PATH` 放一个坏的 `libheif.so.1` ⇒ `rc=127`
  `Error loading shared library libheif.so.1`（证明构建树 `DT_RUNPATH` **不会**兜底，装的确是安装副本）；
- **反 2（插件敏感性）**：`LIBHEIF_PLUGIN_PATH` 指向不存在目录 ⇒ `rc=42`、2/2 用例失败
  （证明换不掉、也不会退回构建树插件）。

### 7.4 `init-build` 生成物的人工审查（工具生成 ≠ 正确）

`worktrees/…/.build-context-libheif-openjpeg-1.23.0` 与骨架文件的实测缺陷（逐条已处理）：

1. `BUILD_SYSTEM="autotools"` —— **误判**，实际是 cmake（`prescan` 与 `lang-preflight` 都判 cmake）。
   `manifest.yaml` 的 `build_system` 按实测写 `cmake`。
2. 骨架 `manifest.yaml` / `notes.md` 里的 `{software}` / `{BUILD_SYSTEM}` / `{2026-09-20}`
   占位符**未被替换**就落盘；且 `status` 预填 `published`（口径应为 `built`）。已整体重写。
3. 骨架把 `source.sha256`、`build.configure_options` 留空占位 —— 已按实测补齐。
4. 骨架创建了 **ARCHIVE-SPEC v3.0 明文废弃的 `packaging/` 空目录**（另见 §7.3 的重签必需项）（AGENTS §1 O14）——
   已删除（空目录不进 Git，但保留会误导后续 finish/preflight 判读）。

## 8. 消费者验证（test_package，鸿蒙特有）

`test_package/test_libheif_openjpeg.c` 的显式检查覆盖四层，任一失败即 `conan create` FAIL：

1. **版本指纹**：`heif_get_version()=="1.23.0"` + major/minor/maintenance = 1/23/0（证明链接到本包交付的宿主）；
2. **插件装载**：`heif_get_plugin_directories()` 指向交付的 `<pkg>/lib/libheif`
   （`runenv_info` 导出的 `LIBHEIF_PLUGIN_PATH` 生效），
   `heif_have_decoder_for_format(heif_compression_JPEG2000)==1`、
   `heif_have_encoder_for_format(heif_compression_JPEG2000)==1`；
3. **反证**：`decoder(HEVC)==0`、`decoder(AV1)==0`、`encoder(HEVC)==0`（未启用其它后端，
   说明命中不是系统同名库）；
4. **真实往返**（功能层，R34）：自造 **64×48 YCbCr 4:2:0** 测试图 →
   `heif_encoder_set_lossless(1)` → `heif_context_encode_image(JPEG2000)` → `write_to_file` →
   `read_from_file` → `heif_decode_image(YCbCr 4:2:0)` → 逐平面比对（ispe 64×48 +
   保真度断言 MAE≤1 / 单点最大误差≤16，实测 0.0395 / 4）；另做一次 RGB 解码的结构判据
   （尺寸 + 平面可读，不设保真度阈值——RGB 形态实测 MAE 9.62 / max 164，见
   `$TASK_DIR/rtprobe/rt_probe.c` 与 `rt_probe2.c` 的对照）。

`test_package` 共 **35 项显式检查**（`check()` 调用数由程序自报
`LIBSHEIF_OPENJPEG_CONSUMER checks_total=… checks_passed=…`，配方不硬编码），
设备实测 **35/35 PASS**；其中最有分量的是第 6 组 **J2K lossless 真实往返**：

```text
heif_init(NULL) -> code=0 (Success)
decoder(JPEG2000)=1  encoder(JPEG2000)=1
heif_context_encode_image(JPEG2000) -> code=0 (Success)
roundtrip_j2k.heif = 800 bytes
heif_decode_image(YCbCr 4:2:0) -> code=0 (Success)
J2K lossless 往返保真度: MAE=0.0395 max=4（4608 个样本，阈值 MAE<=1 max<=16）
LIBSHEIF_OPENJPEG_CONSUMER checks_total=35 checks_passed=35
RESULT: PASS
```

阈值定值依据：先用同一往返逻辑写成独立探针 `$TASK_DIR/rtprobe/rt_probe2.c` 在设备上实测
（YCbCr 4:2:0 lossless：MAE 0.0395 / max 4；**RGB 交织形态实测 MAE 9.62 / max 164**，
因为多了 RGB↔YCbCr 转换与色度子采样的损失），故保真度判据取 **YCbCr 平面 + MAE≤1、max≤16**，
RGB 路径只作结构判据（尺寸 + 平面可读）。


## 9. 未运行 / 未覆盖（如实登记）

- 上游 `WITH_REDUCED_VISIBILITY` 组内注册项（含 `jpeg2000.cc` 的 30 个 J2K 用例）：
  NOT_RUN，技术原因见 §6；
- `WITH_UNCOMPRESSED_CODEC` / `WITH_OPENJPH_ENCODER` / `ENABLE_EXPERIMENTAL_FEATURES`
  相关组：不属本包交付面，NOT_RUN；
- 上游 `--version` 类 CLI 冒烟（conan-verify L2）：本包**不交付可执行文件**
  （`WITH_EXAMPLES=OFF`，交付面只有库与插件模块），L2 不适用；R38 的 `commands.json`
  也因此**不需要**；
- `WITH_GDK_PIXBUF` / `WITH_EXAMPLE_*` / `BUILD_DEVELOPMENT_TOOLS` / `WITH_FUZZERS` /
  `BUILD_DOCUMENTATION` / `ENABLE_COVERAGE`：非交付面，显式 OFF。
- **`finish` 的 G0 clean-verify 对本包结构上不适用**（如实登记，不为消告警改上游）：它自建裸
  cmake 工程、不带 profile/toolchain，既构建不出插件交付面（会退化成静态编入宿主），也会撞上
  §7.1 的 libc++ ranges 缺口。按"非阻塞 + 结构不适用"登记。
- **上游用例级的 FAIL 6 / SKIP 23 见 §5.3 与 §6**：FAIL 需要 AV1 编码后端（aom/svt-av1
  制品仓不可得、且属兄弟包交付面），不是本包功能缺陷；本报告不把它们写成 PASS 或 SKIP。
- **采信轮环境口径（与 AGENTS §3.5 的实现差异，如实登记）**：`tools/conan_verify_round.sh` →
  `conan-verify` 内部的 G2 用 `conan create`，**不设沙箱 HOME、也不注入 `tools.build:jobs`**。
  本包在配方里对 OHOS 显式 `self.conf.define("tools.build:jobs", 2)`（槽位纪律：2 槽 × j2 = 4 路
  ≤ affinity 8；同时也是为了在 G2 的 3600s 硬超时内跑完全量构建），因此实际是 2 路构建；
  但 `HOME` 是真实用户 HOME（本包的上游测试只写构建目录：`tests/test_utils.cc` 的
  `get_tests_output_dir()` = `current_path()/libheif_test_output`，无 HOME 写入路径）。
- **`transitive_headers` 不需要**（机械核对）：本包安装出的公开头 `include/libheif/*.h` 只
  include 标准库（`<cassert>` 等）与 `libheif/*` 自身头，**0 处** `openjpeg.h`/`openjp2`/`opj_`
  （证据：`grep -rn "openjpeg\|openjp2\|opj_" <pkg>/include/` 无命中）——OpenJPEG 只出现在
  插件模块的编译单元里（`libheif/plugins/{decoder,encoder}_openjpeg.cc`），不进公开头，
  故消费者的 `INCLUDE_DIRS` 不需要 openjpeg，`self.requires("openjpeg/2.5.4")` 保持默认
  `transitive_headers=False` 即可。
- **未声明依赖自检**（判据来自同批编排口径）：`grep -c harmonybrew <build>/CMakeCache.txt` 实测
  **1 处**，命中的是 `ZLIB_DIR:PATH=…/.harmonybrew/lib/cmake/ZLIB`——来自未被启用的可选 zlib 探测
  （`WITH_HEADER_COMPRESSION=OFF`/`WITH_UNCOMPRESSED_CODEC=OFF`）；交付产物的 `link.txt` 与
  `DT_NEEDED` **均不含 zlib/-lz 或 harmonybrew 路径**（宿主与两个插件只依赖 `libheif.so.1`/
  `libopenjp2.so.7`/libc++/libc），故不构成"链接到未声明依赖"。

## 10. 复现命令（设备可直接执行）

```sh
TASK_DIR=$HOME/tmp/libheif-openjpeg-1.23.0
TARGET_REPO=$HOME/ws/worktrees/libheif-openjpeg-1.23.0
PROFILE=$TARGET_REPO/ci/conan/profiles/ohos-aarch64

# 0) 依赖接线复现（W0 + CMakeDeps 形态 + 交付面日志/readelf 判据）
sh "$TASK_DIR/verify-openjpeg-dep-wiring.sh"

# 1) 配方干净构建 + 上游测试 + test_package（采信轮内部即跑这条）
conan create "$TARGET_REPO/archives/l/libheif-openjpeg/1.23.0" \
    -pr:h="$PROFILE" -pr:b="$PROFILE" --build=missing --user=ohpcd --channel=stable \
    -c tools.build:jobs=2

# 2) 采信轮固序（清缓存 → conan-verify → 证据副本 → 快照）
sh "$HOME/ws/tools/conan_verify_round.sh" libheif-openjpeg 1.23.0 \
    --repo "$TARGET_REPO" --task-dir "$TASK_DIR"
```
