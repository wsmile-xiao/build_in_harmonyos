# libheif-aom 1.23.0 适配笔记

> 软件：`libheif-aom` 1.23.0（父 tarball `libheif` 1.23.0 内的 aom/AV1 编解码后端插件子包）
> 设备：HarmonyOS PC aarch64（`uname -s`=HarmonyOS，clang 15.0.4，cmake 4.1.2，Conan 2.29.1）
> 任务：积分赛 / 全新包（`upstream/main` 无 `archives/l/libheif-aom/`，`task_init.sh --allow-unpublished`）

## 编译环境

| 项 | 值 |
|---|---|
| 构建系统 | CMake（上游 libheif 1.23.0 `CMakeLists.txt`；内树 libaom 3.9.1 亦 CMake） |
| 编译器 | `/data/service/hnp/bin/clang` 15.0.4（`--target=aarch64-unknown-linux-ohos`） |
| cmake / ninja | 4.1.2 / 1.13.1（本包用 Unix Makefiles，与设备原生探索一致） |
| Conan | 2.29.1（OHOS 适配版），profile `ci/conan/profiles/ohos-aarch64`（`os=OHOS`） |
| 并发 | `tools.build:jobs` 缺省 **2**（见下「构建并发」）；实测 `-j2`：内树 aom 5.5 min + 宿主 18 min |
| 编译日期 | 2026-09-20 |

## 交付面（本包交付什么，判据逐条给出）

上游 `libheif/CMakeLists.txt:226-227` + `libheif/plugins/CMakeLists.txt:60-66`：

```cmake
plugin_option(AOM_DECODER "AOM AV1 decoder" ON OFF)
plugin_option(AOM_ENCODER "AOM AV1 encoder" ON OFF)     # ← 注意 defaultPlugin = OFF
...
set(AOM_DECODER_sources decoder_aom.cc decoder_aom.h)
plugin_compilation(aomdec AOM AOM_DECODER_FOUND AOM_DECODER AOM_DECODER)   # → heif-aomdec
set(AOM_ENCODER_sources encoder_aom.cc encoder_aom.h)
plugin_compilation(aomenc AOM AOM_ENCODER_FOUND AOM_ENCODER AOM_ENCODER)   # → heif-aomenc
```

* 上游目标名带 `dec`/`enc` 后缀 → 产物 **两个** MODULE：
  `lib/libheif/libheif-aomdec.so`（AV1 解码插件）与 `lib/libheif/libheif-aomenc.so`（AV1 编码插件）。
  包名取任务卡/CI 分支名门禁（L0n：分支名去前缀 == 包目录名-版本）要求的 `libheif-aom`，
  即这两个同族插件的合并交付单元。
* aom 的 `WITH_AOM_*_PLUGIN` 默认值是 **OFF**（与 dav1d/svt/openjpeg 默认 ON 相反）：
  上游默认把 aom **静态编入宿主**；要拿到独立插件必须显式打开
  `ENABLE_PLUGIN_LOADING=ON` + `WITH_AOM_{DECODER,ENCODER}=ON` + `WITH_AOM_{DECODER,ENCODER}_PLUGIN=ON`
  五个开关，缺一则 `plugin_compilation()` 走 else 分支（只打印 `Not compiling …`），
  配置/构建/安装全绿但**包里没有插件**。
* 自包含交付**插件装载版宿主** `lib/libheif.so`（`ENABLE_PLUGIN_LOADING=ON`）：插件以
  `target_link_libraries(heif-aomdec PRIVATE aom heif)` 依赖宿主，运行期必须由宿主
  `heif_init()` `dlopen` 才会注册后端。仓库既有 `archives/l/libheif/1.22.2` 是
  `ENABLE_PLUGIN_LOADING=OFF` 的 codec-free 核心 → **不能**作为本包依赖（跨版本插件 ABI 也不匹配）。

交付物清单（`conan cache path libheif-aom/1.23.0:<pkgid>`）：

```
lib/libheif.so, lib/libheif.so.1, lib/libheif.so.1.23.0     # 宿主（插件装载开启）
lib/libheif/libheif-aomdec.so                                # AV1 解码插件（本包命名产物）
lib/libheif/libheif-aomenc.so                                # AV1 编码插件（本包命名产物）
include/libheif/*.h, lib/pkgconfig/libheif.pc, lib/cmake/libheif/*
```

## 依赖边界（aom 是外部依赖还是内树捆绑 —— 判定依据）

**结论：aom 本体在 libheif 树内不存在，只能内树自包含构建（`requirements()` 为空）。**

| # | 判据 | 命令与读数 |
|---|---|---|
| 1 | libheif 树内**没有** aom 源码 | `find <src> -iname '*aom*'` → 只有 `cmake/modules/FindAOM.cmake`、`libheif/plugins/{decoder,encoder}_aom.{cc,h}`、`third-party/aom.cmd`（MSVC 辅助脚本，内容是 aom 的 git URL） |
| 2 | 探测机制要求外部提供 libaom | `FindAOM.cmake`：先 `find_package(AOM QUIET CONFIG)`，否则 `libfind_pkg_check_modules(AOM_PKGCONF aom)` + `find_path(AOM_INCLUDE_DIR …)` + `find_library(AOM_LIBRARY NAMES libaom aom)`，再 `find_package_handle_standard_args(AOM REQUIRED_VARS AOM_INCLUDE_DIR AOM_LIBRARY)` 硬失败；编码器另有 `check_symbol_exists(AOM_USAGE_GOOD_QUALITY aom/aom_encoder.h …)` |
| 3 | 仓库里的 `aom` 目录**不是** Conan 包（元数据孤儿） | `git ls-tree -r --name-only upstream/main archives/a/aom/` → `3.9.1/{manifest.yaml,notes.md,patches/0001-harmonyos-build-config.patch}` + `README.md`；**无 `conanfile.py`/`conandata.yml`**，manifest 的 `source.url` 是 `file:///…/aom-3.9.1.tar.gz`（ARCHIVE-SPEC v2.0 / cmd-pkgs tarball 渠道） |
| 4 | 制品仓没有该 ref（R35 真探针，非 `conan list`） | `conan install --requires=aom/3.9.1 --build=never -pr:h=<绝对 profile>` → `ERROR: Package 'aom/3.9.1' not resolved: Unable to find 'aom/3.9.1' in remotes.`；`conan download --only-recipe aom/3.9.1 -r=ohpcd` → `ERROR: error:system acceleration policy not enabled.`（**误导文案**：与"策略未开"共用；负对照 `conan download --only-recipe libde265/1.0.18 -r=ohpcd` → rc=0 / `Download completed`，证明是 ref 缺失）；另 `conan list "aom/*"`、`"libaom/*"`、`"*aom*" -r=ohpcd` 均 `Found 0` |
| 5 | 设备上也没有系统 libaom 可退 | `/usr/local/lib/libaom*` 不存在、`pkg-config --exists aom` 为 NO |

处置：按**已合并先例** `archives/h/handbrake/1.11.2/conanfile.py` 的口径内树自包含
（原文："All 33 contribs (ffmpeg/x264/x265/libvpx/libass/dav1d/svt-av1/…) are built in-tree
by HandBrake's own build system, so there are no Conan package dependencies
(R36: nothing to publish beforehand)"），`requirements()` 留空。
与 handbrake 的差别如实写明：handbrake 是**上游构建系统自己**编 contrib，本包是**配方**
在 `build()` 里先编 libaom 再编宿主；共同判据是"没有可 `requires()` 的已发布 ref"。

内树 aom 接法（不改上游源码）：

```python
# source()
get(self, **self.conan_data["sources"], strip_root=True)                       # 父 tarball
get(self, url=…["aom"]["url"], sha256=…["aom"]["sha256"],
    destination="aom", strip_root=True)                                        # 官方 libaom
# generate()：把 FindAOM 的 MODULE 模式探测结果钉死（R49 私有 prefix）
tc.cache_variables["AOM_INCLUDE_DIR"] = <build_folder>/aom-prefix/include
tc.cache_variables["AOM_LIBRARY"]     = <build_folder>/aom-prefix/lib/libaom.a
# build()：先编静态 libaom（PIC + generic CPU），再编 heif + 两个插件目标
cmake -S <src>/aom -B <build_folder>/aom-build -G "Unix Makefiles" \
      -DCMAKE_TOOLCHAIN_FILE=<generators>/conan_toolchain.cmake \
      -DCMAKE_BUILD_TYPE=Release -DCMAKE_SYSTEM_NAME=Linux \
      -DAOM_TARGET_CPU=generic -DCONFIG_AV1_ENCODER=1 -DCONFIG_AV1_DECODER=1 \
      -DENABLE_TESTS=0 -DENABLE_EXAMPLES=0 -DENABLE_TOOLS=0 -DENABLE_DOCS=0 \
      -DBUILD_SHARED_LIBS=0 -DCONFIG_PIC=1
cmake --build <…>/aom-build -j2 && cmake --install <…>/aom-build --prefix <…>/aom-prefix
cmake --build <build_folder> --target heif heif-aomdec heif-aomenc -j2
```

* `AOM_TARGET_CPU=generic`：关掉 ARM 汇编（与 `archives/a/aom/3.9.1/notes.md` 的设备实测结论一致）；
* `CONFIG_PIC=1`：libaom 静态库默认非 PIC，链进 MODULE 会失败；
* 显式点名 `heif-aomdec heif-aomenc`：`find_package(AOM)` 失败时目标不存在 → 构建硬失败，
  不允许交付"没有插件的成功包"；
* 内树 libaom 的静态库与头文件**不安装进包**（它不是本包交付面，也不冒充已发布的 aom 包）。

两源 sha256 都是本任务设备实测下载后自算（不是抄录）：

* 父 tarball `https://github.com/strukturag/libheif/archive/refs/tags/v1.23.0.tar.gz`
  → `50ea4fbd1e19c7b8820271d6d0c73f2623fec5d659ce9fae57e48dbeb94fab9a`；
  与同族 `libheif-libde265` / `libheif-openjpeg` 任务目录里的副本三方独立比对一致。
  ⚠️ 同一 tag 的 `releases/download/v1.23.0/libheif-1.23.0.tar.gz` 是**另一个制品**
  （实测 `4c9182b18897617182eed12ab5eb9f9d855b3aa3a736d6bdb31abc034ec7d393`）——
  conandata 的 url 与 sha256 必须同一次下载配对；
* 内树 libaom `https://storage.googleapis.com/aom-releases/libaom-3.9.1.tar.gz`
  → `dba99fc1c28aaade28dda59821166b2fa91c06162d1bc99fde0ddaad7cecc50e`；
  与官方 googlesource tag 归档
  `https://aomedia.googlesource.com/aom/+archive/refs/tags/v3.9.1.tar.gz` 解开后
  **逐文件 sha256 全等**（1353 个文件，聚合 `31a4baa21259e61643259973f83cf7fef018069b68fe3fc5fccdc514628d2ce5`），
  两个独立官方端点互证（GCS 与 googlesource 的 tarball 字节不同、内容相同）。

## 遇到的问题与解决方案

| # | 问题（逐字） | 根因 | 解决方案 |
|---|---|---|---|
| 1 | `libheif/box.cc:4155: error: no member named 'all_of' in namespace 'std::ranges'`（4156/4166 同族，共 3 errors） | OHOS libc++ 15（`_LIBCPP_VERSION` 15004）在未定义 `_LIBCPP_ENABLE_EXPERIMENTAL` 时通过 `_LIBCPP_HAS_NO_INCOMPLETE_RANGES` 隐藏 `std::ranges` 算法；上游 `CMAKE_CXX_STANDARD 20` + `box.cc` 用了 `std::ranges::all_of/find`。**不是缺头文件、不是 -std 没生效**（粗粒度宏 `__cpp_lib_ranges` 仍报 201811L，"宏说有≠实现有"） | 配方 `generate()`：`if str(self.settings.os) in ("Linux","OHOS"): tc.preprocessor_definitions["_LIBCPP_ENABLE_EXPERIMENTAL"] = None`。**不改上游源码、不需要 `-lc++experimental`**；先例 `archives/l/libpqxx/8.0.1`、`archives/l/ladybug/0.18.2`。逐字证据见 `reports/evidence-native-and-platform.md` §1 |
| 2 | 插件装载失败：`dlopen: Error loading shared library ../libheif.so: (needed by …/libheif-aomdec.so)` → `heif_init()` code=11、`heif_have_decoder_for_format(AV1)==0` | `CMAKE_SYSTEM_NAME` 缺省 → 设备 `uname -s`=`HarmonyOS` 而 SDK 的 CMake **只有 `Platform/OHOS.cmake`、没有 `Platform/HarmonyOS.cmake`** → 落到"未知平台"通用回退 → 共享库**不写 SONAME、也不产生带版本文件名** → 插件 MODULE 链接宿主时把**含斜杠的相对路径**写进 `DT_NEEDED`；该条目按 **CWD** 解析，装到 `<pkg>/lib/libheif/` 后必然找不到（`archives/l/libheif/1.18.2/notes.md` 记录的"NEEDED 字段硬编码相对路径、未解决"就是同一根因） | `tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"`（走 `Platform/Linux.cmake`，仓库 693 个配方同口径；设备侧 aom 归档 notes 亦用同一 workaround）。效果：宿主得 SONAME `libheif.so.1` + 版本化文件名，插件 `DT_NEEDED` 变成无斜杠的 `libheif.so.1`，由 conanrun 的 `LD_LIBRARY_PATH` 正常解析。可用性探针（同一 `add_library(SHARED)` 小工程三种取值）：不设 → 只有 `libfoo.so` 且**无 SONAME**；`Linux`/`OHOS` → `libfoo.so`+`.so.1`+`.so.1.2.3` 且 SONAME=`libfoo.so.1` |
| 3 | 装到包里的插件 `dlopen: Error loading shared library <pkg>/lib/libheif/libheif-aomdec.so: **Permission denied**`（不是 not found）→ `heif_init()` code=11、AV1 后端为 0、`test_package` 红；而**同一份未安装**的构建树插件 `dlopen → OK` | 设备 clang launcher 在**链接期**写入 `.note.ohos.ident` 代码签名；CMake 默认 `BUILD_WITH_INSTALL_RPATH=OFF`，`cmake --install` 会**就地改写**构建树 RUNPATH（本例清空）→ 文件字节变化（同尺寸、sha256 `921d231f…` → `d5f87929…`，`RUNPATH` 1 条 → 0 条）→ **签名失效** → OHOS 加载器拒绝映射（EACCES）。宿主 `libheif.so.1.23.0` 安装前后 sha256 相同（无需改写）故未命中，只看宿主会误判"交付物没问题" | 配方 `generate()`：`tc.variables["CMAKE_BUILD_WITH_INSTALL_RPATH"] = True` + `tc.variables["CMAKE_INSTALL_RPATH"] = ""` → 构建树直接使用安装 RPATH、安装期不再改写，安装前后**逐字节一致**；运行期搜索路径由 conanrun 的 `LD_LIBRARY_PATH` 提供。最小复现：`add_library(rp SHARED)`+`add_library(rpmod MODULE)` 链 rp + install，默认 `pre≠post`、加该对变量后 `pre==post`。**命中范围**：只有链接了**同一构建树内另一个 target**（如插件的 `… PRIVATE heif`）的目标才带构建树 RPATH、才会被 install 改写，故同族 7 个插件子包都会命中 |
| 4 | 内树 aom 子构建配置期刷上百行 `System is unknown to cmake, create: Platform/HarmonyOS …` | `tc.cache_variables` 只落 `generators/CMakePresets.json`（Conan 的 `CMake.__init__` 从那里取 cacheVariables 再以 `-D` 传给**主工程**），`conan_toolchain.cmake` 里没有该变量；子构建只用 toolchain 文件、不走 preset | 子构建命令行**显式再传一次** `-DCMAKE_SYSTEM_NAME=Linux`（与主工程口径一致，噪声归零） |
| 5 | `init-build` 直接以 `OSError: [Errno 39] Directory not empty: …/builds/libheif-aom-1.23.0.work` 的 traceback 结束 | 我把原生探索的构建树放在了 `$TMPDIR/builds/<软件>-<版本>.work`（编排的专属目录），`_create_dual_track()` 的 `shutil.rmtree` 未捕获异常 | 探索树改放 `$WORKSPACE_ROOT/tmp/aom-explore/`；已写 `feedback/pending/2026-09-20-libheif-aom-1.23.0.md` F2 |
| 6 | `OHC_INIT_BUILD_TARBALL` 离线种子"命中即复制"未生效（仍去联网搜 URL，最后 rc=1） | 全新包 `--auto` 在 URL 搜索阶段就失败，而种子只在 `_download()` 内被检查 | 同时传 `--url https://github.com/strukturag/libheif/archive/refs/tags/v1.23.0.tar.gz`，随即 `✅ 离线种子命中（未联网）` rc=0；已写 feedback F1 |
| 7 | `init-build` 骨架把构建系统写成 `autotools`、`manifest.yaml` 里 `software: "{software}"` 未替换、并创建了 O14 明令废弃的 `packaging/` | 全新包无同族先例可继承，探测与模板渲染退化 | 人工核对为 `build_system: cmake` 并重写 manifest；删除空 `packaging/`；已写 feedback F3 |

## 三必修项与两条可选路线（同族通用口径）

本包（以及同批 7 个 `libheif-<codec>` 插件子包）必须同时跨过三道坎，**任何一道没过都表现为
"构建成功、产物不可用"**；每条的判据都落在**插件自身**，不能只看宿主或看日志全绿：

| # | 必修项 | 本包取值 | 备选路线 |
|---|---|---|---|
| ① | libc++ ranges 缺口 | `tc.preprocessor_definitions["_LIBCPP_ENABLE_EXPERIMENTAL"] = None` | 打补丁把 `std::ranges::all_of/find` 换成 C++17 算法（本包不采用：能用开关就不打补丁） |
| ② | 共享库 SONAME 缺失 | `tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"` | 窄路线 `tc.variables["CMAKE_SHARED_LIBRARY_SONAME_{C,CXX}_FLAG"] = "-Wl,-soname,"`（160 个配方；不动 `CMAKE_SYSTEM_NAME`，不翻转上游 `if(CMAKE_SYSTEM_NAME STREQUAL "Linux")` 分支、不进入 cross 语义；5 秒探针实测两条都能恢复 SONAME `libfoo.so.1` 与三个版本化文件名） |
| ③ | install 改写 RUNPATH 破坏 OHOS 代码签名 | `tc.variables["CMAKE_BUILD_WITH_INSTALL_RPATH"] = True` + `tc.variables["CMAKE_INSTALL_RPATH"] = ""`（**从源头不触发改写**） | 装后重签：`package()` 里 `cmake.install()` 之后对 `lib/**/*.so*` 跑 `llvm-objcopy --remove-section .codesign` + `binary-sign-tool sign -inFile f -outFile f -selfSign 1`（**失效后修复**，能覆盖 install 之外的任何改写；已合并先例 `archives/o/openh264/2.6.0:130-136`、`archives/f/ffmpeg/8.1.2:240-246`） |

命中范围判据：②③ 只命中**链接了同一构建树内另一个 target**（树内互链）的目标——
libheif 插件正是 `target_link_libraries(heif-<codec> PRIVATE … heif)`，所以 7 个同族子包全中；
只链 Conan 依赖的普通包不带构建树 RPATH、install 无需改写、不受影响。
详细机制、逐字读数、最小复现与验收四判据见知识草稿
`knowledge/drafts/DRAFT-E622-libheif-aom-1.23.0-plugin-switch-matrix-and-vendored-codec.{md,kv}`。

### ③ 的真实构建自证（本包采用路线 A，实测有效）

读数取自**采信轮（清缓存后全量重建）**的产物：构建树 `<build>/Release/...` 与安装树
`<pkg>/...` 逐字节对比（`sha256sum`）。

```text
插件 libheif-aomdec.so   build=831e474416c6c8aa…  installed=831e474416c6c8aa…  identical=YES  RUNPATH 0 条
插件 libheif-aomenc.so   build=5bfeddf2d387ae67…  installed=5bfeddf2d387ae67…  identical=YES  RUNPATH 0 条
宿主 libheif.so.1.23.0   build=f6d6c0862c539895…  installed=f6d6c0862c539895…  identical=YES  RUNPATH 0 条
readelf -d libheif-aomenc.so → NEEDED libheif.so.1 / libc++_shared.so / libc.so（无斜杠、无 libz）
test_package → LIBHEIF_AOM_CONSUMER checks_total=25 checks_passed=25 → RESULT: PASS
```

即：装前后**逐字节一致**（签名未被破坏）、插件被宿主 dlopen 并注册、端到端 AV1 往返通过。
两个插件模块的哈希在两次独立构建间**可复现**（本任务 it3 轮与采信轮相同：
`831e4744…` / `5bfeddf2…`）；宿主的哈希随构建路径变化（it3 轮为 `dc933d37cda9…`、
采信轮为 `f6d6c086…`），但"安装前后一致"这一判据在两轮中均成立。
同族备选路线（装后重签）的证据格局见草稿——两条都实测可解，本包按"真实构建自证"保留 A。

### 宿主机静默回退核查（`harmonybrew` 污染）

判据：构建目录里不得有 `harmonybrew` 的**实际使用**痕迹。本包实测：

```text
CMakeCache.txt: 1 条 ZLIB_DIR=/storage/…/.harmonybrew/lib/cmake/ZLIB（探测残留）
heif 与插件的 link.txt：0 条            aom-build/CMakeCache.txt：0 条
交付物 DT_NEEDED：仅 libheif.so.1 / libc++_shared.so / libc.so（无 libz）
nm -D libheif.so.1.23.0 | grep -E ' (inflate|deflate|compress2|crc32)$' → 空
installed libheif.pc：Requires/Requires.private 均为空
```

结论：该 cache 行是"探测发生过"的残留（`WITH_HEADER_COMPRESSION=OFF`/`WITH_UNCOMPRESSED_CODEC=OFF`
时 `find_package(ZLIB)` 所在分支关闭），**没有**任何 brew 库进入交付物的链接面或元数据面；
`libaom` 侧同样 0 命中（内树构建用 cache 变量钉死路径）。

## 源码修改

**无补丁、零上游源码改动**（`patches: []`，`patches_applied: []`）：上面第 1、2 两条都用
**开关/变量**解决（R1：能用开关就不打补丁），第 3 条只影响本包子构建命令行。

## 依赖版本

| 组件 | 版本/来源 | 说明 |
|---|---|---|
| libheif | 1.23.0（官方 tag 归档，sha256 `50ea4fbd…`） | 父 tarball；宿主 + aom 插件源码都在其中 |
| libaom | 3.9.1（官方 release 归档，sha256 `dba99fc1…`） | 内树自包含构建（静态、PIC、`AOM_TARGET_CPU=generic`），**不是** Conan 依赖 |
| 其余上游后端 | 全部 `WITH_*=OFF` | x265/x264/dav1d/kvazaar/uvg266/vvdec/vvenc/ffmpeg/openh264/rav1e/svt/jpeg/openjpeg/openjph/libsharpyuv/未压缩/WebCodecs |
| Conan 依赖 | 无（`requirements()` 为空） | R36：没有需要事先发布的依赖 |

aom 选版依据：与仓库既有 `archives/a/aom/3.9.1` 同版本，可直接继承其设备实测配置结论
（`AOM_TARGET_CPU=generic` 关汇编、`CMAKE_SYSTEM_NAME=Linux`、tests/examples/docs 全关）。

## 上游测试清点（rule4 / R51）

**主 N = 217**（父 tarball `libheif` 1.23.0 全量注册面里「用例/注册类」候选口径的最大值）。
逐字取数命令与读数见 `reports/upstream-test-count.md`；五处（PR 正文 / `manifest.yaml` /
`test_package/MANIFEST.yml` / 本文件 / `reports/test-report.md`）同源同单位。

| 口径 | 读数 | 取数命令（父 tarball 根） |
|---|---:|---|
| Catch2 `TEST_CASE` 注册点（**主 N**） | 217 | `grep -rho "TEST_CASE" tests/*.cc \| wc -l` |
| （`TEST_CASE_METHOD`/`SCENARIO`/`SCENARIO_METHOD`） | 0/0/0 | 同族宏逐个数 |
| CTest `add_test`（全开关上限） | 39 | `grep -cE '^\s*add_(libheif\|heifio)_test\(' tests/CMakeLists.txt` |
| 测试可执行目标（全开关上限） | 39 | 与上一条一一对应（每个宏体一个 `add_executable`） |
| 测试源文件 | 41 | `ls tests/*.cc \| wc -l`（含 `main.cc`/`test_utils.cc` 两个公共文件） |
| 断言（**另一单位，只披露不并入**） | 4016 | `REQUIRE(` 3994 + `CHECK(` 18 + `REQUIRE_FALSE/CHECK_FALSE(` 4 |
| `GENERATE(` / `SECTION(` | 43 / 5 | 运行期再展开，不构成新的注册单位 |

**未运行（NOT_RUN）217 项的技术原因**（逐项归因）：

1. 本包交付面 = 上游树内的 aom 编解码后端插件（CMake 目标 `heif-aomdec`/`heif-aomenc`），
   上游 `tests/` 的 39 个测试目标**不被 `install()`**、不属交付面（同族口径一致）；
2. 上游把 `BUILD_TESTING` 默认置 ON，但本包按 **`BUILD_TESTING=OFF`** 构建：启用它要额外
   构建 `heifio` 并触发 TIFF/JPEG/PNG/WEBP 可选探测，且 `tests/CMakeLists.txt` 里
   `encode_htj2k`/`encode_jpeg2000`/`uncompressed_*` 等用例要求本包未适配、未发布的后端
   （R36），**不为凑数字放开不属于交付面的上游开关**；
3. 因此本次实际运行 N′ = 0；替代验证 = `test_package` 消费者用例 25 项（见下），
   覆盖宿主装载、两个插件注册、AV1 编解码端到端往返。

**适配后合计 = 上游 217 + 鸿蒙特有 25 = 242**（与 PR 正文「适配后测试用例统计」表、
`manifest.yaml` 的 `test_package.adapted_total`、`test_package/MANIFEST.yml` 的
`adapted_total`、`reports/test-report.md` 同源同单位）。

## 构建并发

`conan_verify` 的 `conan create` **不传** `-c tools.build:jobs`，而 Conan 的 `CMake.build()`
默认按 `os.cpu_count()`（本设备 20，容器 affinity 8）传 `-j` → 不限制就超订。
本包在配方内限流：

```python
jobs = self.conf.get("tools.build:jobs", default=2, check_type=int)
```

默认取 `notes/device-facts.md` §一.7 给出的安全区间（2..4）下界 **2**：内树自包含 aom
使构建量翻倍（实测 `-j2`：aom 5.5 min + 宿主 18 min ≈ 24 min；`-j1` 约 47 min，
逼近 `conan_verify` 的 3600s create 预算），2 路既避免超订又给超时留余量；
调用方显式给 `tools.build:jobs` 时一律按调用方的值。

## 验证结果

见 `reports/test-report.md`（含原生构建、`conan create`/W3、`test_package` 逐字读数与统计）。

## 注意事项

1. **插件目录是编译期钉死的**：上游 `heif_version.h` 的 `LIBHEIF_PLUGIN_DIRECTORY` =
   构建时的 `${CMAKE_INSTALL_FULL_LIBDIR}/libheif`（Conan 包目录绝对路径，跨缓存/跨机不可移植）。
   配方 `package_info()` 用 `runenv_info.define("LIBHEIF_PLUGIN_PATH", <pkg>/lib/libheif)` 导出；
   上游 `libheif/plugins_unix.cc` 读**单数** `LIBHEIF_PLUGIN_PATH`
   （`heif_library.h` 注释里的复数 `PATHS` 是过期文档）。
2. 消费方必须走 `conanrun`（`VirtualRunEnv`）或自带等价环境：既要有 `LIBHEIF_PLUGIN_PATH`
   （插件目录），也要有 `LD_LIBRARY_PATH` 指向 `<pkg>/lib`（宿主 `libheif.so.1`）。
3. 本包**不**安装 libaom 的头文件/静态库：aom 只作为内树构建输入，静态链进两个插件模块；
   若下游需要 libaom 本体，应另立 `aom` 的 Conan 包任务（拓扑序在前），不要从本包取。
4. `test_package` 的端到端往返是有损 AV1（`q=90`）：判据取逐点平均绝对误差 < 12、
   单点最大 ≤ 48（合成渐变图 + 中性色度），既有判别力又不依赖任何外部夹具文件
   （提交面不含二进制）。
