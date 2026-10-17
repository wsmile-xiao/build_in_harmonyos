# libheif-svtenc 1.23.0 适配笔记

## 交付面

上游 libheif 1.23.0 树内的 CMake 目标 `heif-svtenc`：

```
libheif/plugins/CMakeLists.txt:68-70
    set(SvtEnc_sources encoder_svt.cc encoder_svt.h)
    plugin_compilation(svtenc SvtEnc SvtEnc_FOUND SvtEnc SvtEnc)
→ libheif/plugins/CMakeLists.txt:1-50  macro(plugin_compilation …)
    add_library(heif-${name} MODULE …)      # 插件装载开启时
    install(TARGETS heif-${name} LIBRARY DESTINATION ${COMPUTED_PLUGIN_INSTALL_DIRECTORY})
```

产物 `lib/libheif/libheif-svtenc.so`（SVT-AV1 / AV1 编码后端插件模块）。
包名按仓库惯例取「交付库文件名去掉前后缀」= `libheif-svtenc`（同族：`archives/l/libhwy_test`
← 树内目标 `hwy_test` → `libhwy_test.a`；`libheif-libde265` ← `heif-libde265`）。

本包**自包含交付**三件（插件模块无法脱离宿主运行）：

| 交付物 | 来源 | 为什么必须一起交 |
|---|---|---|
| `lib/libheif/libheif-svtenc.so` | 树内 `libheif/plugins/encoder_svt.cc` | 本包命名产物 |
| `lib/libSvtAv1Enc.so*` | 包内树构建的官方 SVT-AV1 v3.1.2 | 插件的 `DT_NEEDED`（AV1 编码器本体） |
| `lib/libheif.so` + `include/libheif/*` + `lib/pkgconfig/libheif.pc` + `lib/cmake/libheif/*` | 同源同版本 `ENABLE_PLUGIN_LOADING=ON` 宿主 | 插件由宿主 `dlopen` 才能注册；仓库既有 `libheif/1.22.2` 是 `ENABLE_PLUGIN_LOADING=OFF` 的 codec-free 核心，**装不了插件**，跨版本插件 ABI 也不匹配 |

## 编译环境

- 构建系统：CMake（父 tarball 与内树构建的 SVT-AV1 都是）
- 编译器：clang/clang++ 15.0.4（`/data/service/hnp/bin/clang`，target `aarch64-unknown-linux-ohos`）
- profile：`ci/conan/profiles/ohos-aarch64`（`os=OHOS/6.0`、`arch=varmv8`、`compiler=clang/15`、`libc++`）
- conan：2.29.1；`-c tools.build:jobs=1`（设备 `os.cpu_count()=20` 但 `sched_getaffinity=8`）
- 构建日期：2026-09-20
- 状态: built

## 编译步骤

1. `conan create archives/l/libheif-svtenc/1.23.0 -pr:h=$HOST_PROFILE -pr:b=$HOST_PROFILE --build=missing --user=ohpcd --channel=stable -c tools.build:jobs=1`
2. `source()`：`get()` 父 tarball（libheif 1.23.0，strip_root）→ `get()` SVT-AV1 v3.1.2 到
   `source_folder/svt-av1` → `apply_conandata_patches()`（`base_path=svt-av1`）
3. `generate()`：`CMakeToolchain` 下发全部 `-D`（含 `WITH_SvtEnc`/`WITH_SvtEnc_PLUGIN`、
   其余后端 OFF、`SvtEnc_INCLUDE_DIR`/`SvtEnc_LIBRARY` 钉到私有 prefix）、
   OHOS 加 `_LIBCPP_ENABLE_EXPERIMENTAL`
4. `build()` 第 1 步：内树构建 SVT-AV1（`cmake -S svt-av1 -B <build>/svt-av1-build
   -DCMAKE_TOOLCHAIN_FILE=<generators>/conan_toolchain.cmake
   -DCMAKE_INSTALL_PREFIX=<build>/svt-av1-prefix -DBUILD_SHARED_LIBS=ON -DBUILD_APPS=OFF
   -DBUILD_TESTING=OFF -DSVT_AV1_LTO=OFF` → `cmake --build … --target install`）
5. `build()` 第 2 步：`cmake.configure()` + `cmake.build(target=["heif", "heif-svtenc"])`
6. `package()`：`cmake.install()` + 把 `libSvtAv1Enc.so*`（含 SONAME 软链）搬进 `<pkg>/lib`
7. `test_package`：`conan create` 自动执行（真跑一次 AV1 编码）

## W0 依赖判定（本包最关键的一步）

**结论：SVT-AV1 是外部依赖，且制品仓没有任何可用版本 → 本包不声明 Conan 依赖，改为包内树构建。**

### 1) 依赖边界：外部依赖，非内树捆绑

```sh
grep -n 'svt' libheif-1.23.0/CMakeLists.txt
#   240:# svt
#   242:plugin_option(SvtEnc "SVT AV1 encoder" OFF ON)
#   243:if (WITH_SvtEnc)
#   244:    find_package(SvtEnc)                 ← 走外部查找
find libheif-1.23.0 -iname '*svt*'
#   ./cmake/modules/FindSvtEnc.cmake         ← 只有 Find 模块
#   ./libheif/plugins/encoder_svt.cc/.h      ← 只有适配层
#   ./third-party/svt.cmd                    ← Windows 辅助脚本，不是源码树
#   ⇒ 树内**没有** SVT-AV1 源码，不存在"libheif 自带 svt"这条路
sed -n '1,20p' libheif-1.23.0/cmake/modules/FindSvtEnc.cmake
#   libfind_pkg_check_modules(SvtEnc_PKGCONF SvtAv1Enc)
#   find_path(SvtEnc_INCLUDE_DIR NAMES svt-av1/EbSvtAv1Enc.h …)
#   find_library(SvtEnc_LIBRARY NAMES SvtAv1Enc libSvtAv1Enc …)
```

### 2) 制品仓实测（R35 口径：真实 `conan install`/`download`，不用 `conan list/search`）

```sh
conan install --requires=svt-av1/4.1.0 --build=never -pr:h="$HOST_PROFILE" -pr:b="$HOST_PROFILE"
#   → rc=1  ERROR: Package 'svt-av1/4.1.0' not resolved: Unable to find 'svt-av1/4.1.0' in remotes

for v in 4.1.0 4.0.0 3.1.2 3.1.0 3.0.0 2.3.1 2.3.0 2.2.0 2.1.0 2.0.0 1.8.0 1.7.0 \
         1.6.0 1.5.0 1.4.1 1.3.0 1.2.0 1.1.0 1.0.0 0.9.0 0.8.0; do
  conan download --only-recipe "svt-av1/$v" -r=ohpcd >/dev/null 2>&1 && echo "$v FOUND" || echo "$v not found"
done
#   → 21 个版本全部 "not found"
# 别名同样 not found：SVT-AV1/4.1.0、svt_av1/4.1.0、svtav1/4.1.0、SvtAv1/4.1.0、
#                      libsvtav1enc/3.1.2、svtav1enc/3.1.2、svt-av1-enc/3.1.2
# 对照组（证明探针本身有效）：
conan download --only-recipe libde265/1.0.18 -r=ohpcd   # rc=0  FOUND（同批兄弟包的真实依赖）
conan download --only-recipe libde265/9.9.9  -r=ohpcd   # rc=1  not found（负对照）
conan install --requires=libSvtAv1Enc/3.1.2 --build=never -pr:h="$HOST_PROFILE"
#   → rc=1  error:invalid name（大写不是合法 Conan 包名）+ 远端无此包
```

### 3) `archives/` 里有目录 ≠ 制品仓里有包（元数据孤儿）

```sh
git ls-tree -r --name-only upstream/main archives/s/svt-av1/
#   archives/s/svt-av1/4.1.0/conanfile_test.py     ← 注意：conanfile_**test**.py
#   archives/s/svt-av1/4.1.0/manifest.yaml
#   archives/s/svt-av1/4.1.0/notes.md
#   archives/s/svt-av1/README.md
#   archives/s/svt-av1/manifest.yaml
git ls-tree -r --name-only upstream/main archives/l/libSvtAv1Enc/
#   archives/l/libSvtAv1Enc/3.1.2/{manifest.yaml,notes.md,patches/0001-…patch}（同样没有 conanfile.py）
```

两个条目都**没有 `conanfile.py`/`conandata.yml`**，即没有可构建配方；`svt-av1/4.1.0/notes.md`
明写来源是另一个仓库 `gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs` 的 **tarball 交付**
（`libSvtAv1Enc/3.1.2/manifest.yaml` 里 `source.url` 指向的是本机绝对路径
`/storage/Users/currentUser/tmp/SVT-AV1-v3.1.2.tar.gz`，交付物是
`libSvtAv1Enc.so / SvtAv1EncApp / pkgconfig / include`），不是 Conan 制品，也不是可复现的官方源。
全仓库 11821 个 `archives/*/*/conanfile.py` 中 `conanfile_test.py` 只有这 1 个文件——
它是另一条流水线（cmd-pkgs 移植归档）的元数据，**不能作为"依赖已发布"的依据**。

### 4) 处置与先例

R36 是**机械门禁**：`finish` step [5/10] 与 CI L0i 都对 `conanfile.py` 里每个
`requires()`/`tool_requires()` 跑 `conan download --only-recipe`，未发布即 HANDOFF/红。
所以写 `self.requires("svt-av1/4.1.0")` 是必然失败路径，而不是"可能失败"。

因此本包 `requirements()` 为空，SVT-AV1 在**包内树构建**。该形态在本仓库有**已合并先例**：
`archives/h/handbrake/1.11.2/conanfile.py`——

```
def requirements(self):
    # All 33 contribs (ffmpeg/x264/x265/libvpx/libass/dav1d/svt-av1/...) are
    # built in-tree by HandBrake's own build system, so there are no Conan
    # package dependencies (R36: nothing to publish beforehand).
    pass
```

逐点对照：①同样在包内编译 svt-av1（handbrake 走它自己的 contrib 系统，本包直接调
SVT-AV1 的 CMake）；②同样 `requirements()` 为空、因此 R36 门禁无事可拦；③源码都来自
官方源。

## 内树构建 SVT-AV1 的接线

```yaml
# conandata.yml（独立键：sources 是父 tarball 的身份，不能被第二个源污染）
svt_av1:
  url: [ "https://gitlab.com/AOMediaCodec/SVT-AV1/-/archive/v3.1.2/SVT-AV1-v3.1.2.tar.gz",
         "https://github.com/AOMediaCodec/SVT-AV1/archive/refs/tags/v3.1.2.tar.gz" ]
  sha256: "d0d73bfea42fdcc1222272bf2b0e2319e9df5574721298090c3d28315586ecb1"
```

- **为什么必须写在 `conandata.yml`**：CI 的 mirror-fallback 与 pre-download 只扫描
  `conandata.yml` 里的 URL（`ci/conan/build_and_test.sh:1021` 与 `:1175`），硬编码进
  `conanfile.py` 就失去预下载与镜像回退；
- **url 用列表**：Conan 2 的 `get()` 对列表逐个尝试（官方 GitLab 主源 + 同组织官方
  GitHub 镜像），CI 的 `github.com` 镜像改写也会作用到列表项；
- **sha256 自算**：设备实测下载后 `sha256sum`（`d0d73bfe…ecb1`，10,909,754 字节），非抄录；
- **补丁定向**：`apply_conandata_patches()` 的 `base_path: "svt-av1"` 把补丁作用到
  `source()` 里第二次 `get(destination=<source_folder>/svt-av1)` 的落点，**父 tarball 一行未改**；
- **子构建复用自己的 Conan toolchain**：`_build_svt_av1()` 用
  `-DCMAKE_TOOLCHAIN_FILE=<generators>/conan_toolchain.cmake`（R33：编译器来自 profile，
  不读 shell 的 `CC`/`CFLAGS`），`-DCMAKE_INSTALL_PREFIX=<build_folder>/svt-av1-prefix`
  （R49：私有 prefix，不写共享 `/usr/local`）；
- **只构建库**：`BUILD_APPS=OFF`（不构建 `SvtAv1EncApp`，本包不交付可执行文件 → 无 `commands.json`）、
  `BUILD_TESTING=OFF`、`SVT_AV1_LTO=OFF`（规避交叉工具链 LTO/`llvm-ar` 链路风险）；
- **把路径钉进 `FindSvtEnc.cmake` 的 cache 变量**：`SvtEnc_INCLUDE_DIR` /
  `SvtEnc_LIBRARY` 指向私有 prefix。上游 Find 模块是 MODULE 模式（pkg-config + 无 HINTS 的
  `find_path`/`find_library`），不认 CMakeDeps 生成的 config，钉路径既避免命中设备系统库，
  也不依赖 pkg-config 是否可用。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 制品仓无 `svt-av1`（21 个版本 + 7 个别名全 not found） | 该包从未 conan 化；`archives/` 里的两个条目是 cmd-pkgs 流程的元数据孤儿 | `requirements()` 为空 + 包内树构建官方 v3.1.2（handbrake 1.11.2 已合并先例） |
| 2 | 宿主 `libheif` 编译报 `box.cc:4155: error: no member named 'all_of' in namespace 'std::ranges'`（4156/4166 是 `find`） | 上游 `CMAKE_CXX_STANDARD 20`；设备 libc++（`_LIBCPP_VERSION 15004`）在未定义 `_LIBCPP_ENABLE_EXPERIMENTAL` 时定义 `_LIBCPP_HAS_NO_INCOMPLETE_RANGES`，把 `<algorithm>` 里的 `std::ranges::all_of/find` 隐藏（**不是**标准没生效、也不是缺头文件） | `generate()` 里对 OHOS 加 `tc.preprocessor_definitions["_LIBCPP_ENABLE_EXPERIMENTAL"] = None`（编译期宏即可，不需要 `-lc++experimental`；libheif 公共头 0 处 `std::ranges`，不必向消费者传播）。先例 `archives/l/libpqxx/8.0.1`、`archives/l/ladybug/0.18.2` |
| 3 | SVT-AV1 在 OHOS 链接 `pthread_setaffinity_np` 不可用 | OHOS clang **同时定义** `__linux__` 与 `__OHOS__`（`clang -E` 实测两行都命中），`svt_threads.h` 的 `EB_CREATE_THREAD` 因此选走 `#if defined(__linux__) && !defined(__ANDROID__)` 分支 | 复用仓库既有归档的 OHOS 补丁（见下节），把 `__OHOS__` 排除到"建线程但不设亲和"的分支 |
| 4 | 插件装好后宿主仍找不到插件（跨缓存/跨机） | 上游把默认插件目录编译期钉死在 `heif_version.h` 的 `LIBHEIF_PLUGIN_DIRECTORY`（= 构建时的 `<prefix>/lib/libheif` 绝对路径） | `package_info()` 的 `runenv_info` 导出 `LIBHEIF_PLUGIN_PATH`（上游 `libheif/plugins_unix.cc:37` 读**单数**变量；`heif_library.h:182` 注释里的复数 `LIBHEIF_PLUGIN_PATHS` 是过期文档） |
| 5 | 全新包 `init-build --auto` 必然 rc=1（4 个同名异源候选字节校验不过） | registry 无该包，search_url 只探测不下载；且工具把构建系统误探测成 autotools | 用官方 tag 归档 URL：`--url https://github.com/strukturag/libheif/archive/refs/tags/v1.23.0.tar.gz` + `OHC_INIT_BUILD_TARBALL` 离线种子；manifest/build_system 人工核对为 **cmake** |
| 6 | 共享库不带 SONAME（本机实测 `readelf -d libSvtAv1Enc.so` 只有 `NEEDED libc.so`、**没有 SONAME 行**），插件 MODULE 会把构建期路径写进 `DT_NEEDED` → 运行期宿主 `dlopen` 插件必失败、G2/test_package 必红 | 设备 `uname -s` 报 `HarmonyOS`，而 SDK 的 CMake 只有 `Platform/OHOS.cmake`、**没有** `Platform/HarmonyOS.cmake` → CMake 落「未知平台」回退（配置期打印 `System is unknown to cmake, create: Platform/HarmonyOS`），`CMAKE_SHARED_LIBRARY_SONAME_*` 未定义。仓库既有 `archives/l/libheif/1.18.2/notes.md` 记的「NEEDED 硬编码相对路径、未解决」就是同一病链 | `generate()` 里 `tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"`（用 `variables` 而非 `cache_variables`：这样它落进 `conan_toolchain.cmake`，**父子两个工程共用同一份 toolchain 时一并生效**）；内树子工程另外显式再传 `-DCMAKE_SYSTEM_NAME=Linux` 兜底。仓库 693 个配方同口径（先例 `archives/a/ableton-link/3.1.2`）。修复后实测：`libSvtAv1Enc.so.3.1.2` 带 `SONAME libSvtAv1Enc.so.3`，插件 `DT_NEEDED` 是裸名 `libheif.so.1` / `libSvtAv1Enc.so.3`（见「设备验证读数」） |
| 7 | 插件装进包后宿主 `dlopen` 报 **`Permission denied`**（EACCES，不是 not found）→ `heif_init` 失败 → 插件永远注册不上，而构建期全绿 | OHOS 的 clang launcher 在链接期给 ELF 写 `.note.ohos.ident` 签名；CMake 默认 `BUILD_WITH_INSTALL_RPATH=OFF`，install 阶段会把插件里的**构建树 RUNPATH** 改写成安装 RPATH（本机实测构建树插件的 `RUNPATH` = `<build>/svt-av1-prefix/lib:<build>/libheif`）→ **同尺寸但字节变** ⇒ 签名失效。同批 aom/libde265 已在设备实测该现象（插件 sha256 `eb04f0f6…`→`abb4b2be…`、`cmp -l` 182 字节差、RUNPATH 由有变无；**宿主 sha256 安装前后相同**，只查宿主必误判） | 两条并用：①`generate()` 里 `CMAKE_BUILD_WITH_INSTALL_RPATH=True` + `CMAKE_INSTALL_RPATH=""`（**从源头**不触发改写；内树子工程同样显式传这两个 `-D`）；②`package()` 末尾对包内**所有**真实 ELF 共享库装后重签（`llvm-objcopy --remove-section .codesign` + `binary-sign-tool sign -selfSign 1`，覆盖 install 之外的任何改写；已合并先例 `archives/o/openh264/2.6.0`、`archives/f/ffmpeg/8.1.2`）；③`package()` 里逐文件记安装前后 sha256 并把差异写进构建日志（`[install-sha256]` 行），使「是否被改写」每轮都有原始读数 |
| 8 | 可能静默链到设备 `~/.harmonybrew` 的库（**设备全绿而干净 CI worker 必红**） | `CMakeToolchain` 会写 `CMAKE_FIND_PACKAGE_PREFER_CONFIG=ON`，而配方未调 `CMakeDeps` 时上游 `find_package(ZLIB)` 可能去设备前缀找 config | **本包实测未成形（如实记录）**：libheif 的 `CMakeCache.txt` 只有一行搜索路径记录 `ZLIB_DIR:PATH=…/.harmonybrew/lib/cmake/ZLIB`，既无 `ZLIB_FOUND` 也无 `ZLIB_LIBRARY`；`readelf -d <pkg>/lib/libheif.so.1.23.0` 的 NEEDED 只有 `libc++_shared.so`/`libc.so`（**无 libz**）；内树 SVT-AV1 子工程的 CMakeCache 命中数 0。判据留档：`grep -c harmonybrew <build>/CMakeCache.txt`（本包 1，但如上属搜索路径记录） |

### 问题 2 的最小复现（本机实测；说明根因不是"标准没生效"）

```sh
printf '#include <algorithm>\n#include <ranges>\n#include <vector>\nint main(){std::vector<int> v{1,2,3};\n  bool a = std::ranges::all_of(v, [](int x){ return x > 0; });\n  auto it = std::ranges::find(v, 2);\n  return (a && it != v.end()) ? 0 : 1;}\n' > ranges-probe.cc
/data/service/hnp/bin/clang++ -std=c++20 -c ranges-probe.cc -o /dev/null
#   ranges-probe.cc:5:25: error: no member named 'all_of' in namespace 'std::ranges'
#   ranges-probe.cc:6:26: error: no member named 'find' in namespace 'std::ranges'
/data/service/hnp/bin/clang++ -std=c++20 -D_LIBCPP_ENABLE_EXPERIMENTAL -c ranges-probe.cc -o /dev/null
#   rc=0（无输出）
grep -n '_LIBCPP_VERSION' /data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/include/c++/v1/__config | head -1
#   39:#  define _LIBCPP_VERSION 15004
```

上游使用点只有 3 处，全在同一文件（`grep -rn 'std::ranges::' libheif/`）：
`libheif/box.cc:4155`（`all_of`）、`:4156` 与 `:4166`（`find`）；全树无 `std::views::`、
无 `<format>`/`std::format`，故单个宏足以覆盖。

## 源码修改

只有 1 个补丁，且**不作用于父 tarball**：

- `patches/0001-svt-av1-3.1.2-ohos-no-thread-affinity.patch`
  - 目标：`svt-av1/Source/Lib/Codec/svt_threads.h`（包内树构建的 SVT-AV1 3.1.2）
  - 改动：`#if defined(__linux__) && !defined(__ANDROID__)` →
    `#if defined(__linux__) && !defined(__ANDROID__) && !defined(__OHOS__)`
  - 来源：与仓库既有归档 `archives/l/libSvtAv1Enc/3.1.2/patches/0001-Source-Lib-Codec-svt_threads.h.patch`
    **逐字节一致**（git blob `c05cd29fbb79a1554d4b3733e6dbbfcf87497efe`；本包文件的
    sha256 = `c8e9be53b239c77977ea6ad760f02863a4e5473cf93080511562a0a427f5db2c`），
    即本设备上已归档验证过的 OHOS 适配，按原样收录、不改一行（R8）
  - 适用性核对：该补丁针对 SVT-AV1 **3.1.2**，与本包选用版本一致（在解包后的
    `SVT-AV1-v3.1.2` 树内 `git apply --check -p1` 通过；`conan create` 日志出现
    `libheif-svtenc/1.23.0@ohpcd/stable: Apply patch (portability): OHOS 无 pthread_setaffinity_np…`）
  - **性质说明（不得写成"无影响"）**：排除后 `EB_CREATE_THREAD` 走 `#else` 分支，
    线程照常创建、只是**不再设置线程亲和**——属功能退化（SVT-AV1 不再把编码线程钉到
    指定核组）。其余编码功能不受影响，替代验证 = test_package 里真跑一次 AV1 编码
    （见「验证结果」）。

父 tarball（libheif 1.23.0）**未打任何补丁**。

## 依赖版本

| 依赖 | 版本 | 形态 | 说明 |
|---|---|---|---|
| （Conan 依赖） | — | — | **无**。`requirements()` 为空（R36 门禁下不能声明未发布的 `svt-av1`） |
| SVT-AV1 | 3.1.2 | 包内树构建（官方源，10,909,754 字节） | `libSvtAv1Enc.so.3.1.2` 随本包发布；插件 `DT_NEEDED` 它 |
| libheif | 1.23.0 | 父 tarball（同源同版本） | 宿主 `libheif.so` 与插件一起交付 |

工具链：cmake（设备 native）、clang/clang++ 15.0.4、conan 2.29.1。

## 上游测试清点（rule4：N = 父 tarball 全量注册面，取「用例/注册类」最大值）

**N = 217**（Catch2 `TEST_CASE` 注册数）。候选口径逐项读数（在解包后的
`$TASK_DIR/upstream/libheif-1.23.0` 下执行，全部可复算）：

| # | 口径（单位） | 读数 | 取数命令 |
|---|---|---|---|
| a | Catch2 用例注册数（`TEST_CASE`） | **217** ← 主 N（用例/注册类最大值） | `grep -rho 'TEST_CASE' tests/*.cc \| wc -l` |
| b | CTest `add_test` 注册数（全开关上限） | 39 | `grep -c 'add_libheif_test(' tests/CMakeLists.txt` → 38；`grep -c 'add_heifio_test(' tests/CMakeLists.txt` → 1 |
| c | 测试可执行目标（全开关上限） | 39 | 同 b（每个 `add_*_test` 一个 `add_executable`） |
| d | 测试源文件数（`.cc`） | 41 | `ls tests/*.cc \| wc -l`（含 `main.cc`/`test_utils.cc` 两个无用例文件 → 含用例文件 39 个） |
| e | 断言数（`REQUIRE(`/`CHECK(`/`*_FALSE(`） | 4016 | `grep -rhoE '(REQUIRE\|CHECK)(_FALSE)?\(' tests/*.cc \| wc -l` —— **另一单位，只披露不并入 N** |
| f | Catch2 运行期展开站点（`GENERATE(` / `SECTION(`） | 43 / 5 | `grep -rho 'GENERATE(' tests/*.cc \| wc -l` —— 运行期展开倍数，不构成新注册单位 |

**差额归因（为什么主 N 取 a 而不取 b/c/d）**：b/c 是"测试可执行目标"口径、d 是"文件"口径，
都小于 a；`TEST_CASE` 是 Catch2 的**用例注册**单位，一个可执行目标内可注册多个用例
（如 `tests/jpeg2000.cc` 单文件 30 个 `TEST_CASE`），因此按"用例/注册类最大值"取 217。
e（4016 条断言）属另一单位，按判读口径只披露、不并入。

**本包实际运行情况**：`TOTAL = PASS + FAIL + SKIP + NOT_RUN = 217 = 0 + 0 + 0 + 217`。

- **PASS = 0 / FAIL = 0 / SKIP = 0 / NOT_RUN = 217**。
- **NOT_RUN 的技术原因**：本包交付面是上游树内的插件目标 `heif-svtenc`
  （源码只有 `libheif/plugins/encoder_svt.cc/.h`），**不含任何测试源码**；
  上游 `tests/` 下 39 个测试目标既不被 `install()`、也不构建（`BUILD_TESTING=OFF`）。
  启用上游测试需要额外打开 heifio 的 TIFF/JPEG/PNG/WEBP 可选探测与本包未适配、未发布的
  编码/解码后端（x265/aom/openjpeg/libde265…），属 R36 禁止面。
- **替代验证**：`test_package/`（消费者视角）真跑 14 项检查，含**真实 AV1 编码一次**；
  上游测试的覆盖缺口如实记为 NOT_RUN，不写成 PASS。

## 零构建预算预验（正式采信轮之前，用上一轮的构建树/安装树做消费者实测）

在花采信轮预算之前，先用已有产物把 `test_package` 真跑了一遍（`cmake --install` 的安装树
直接当"包"用）。这一步零成本地暴露了问题 7 的全链路读数，并在预验阶段抓出 1 个编译错误：

```sh
P=<conan 缓存>/p ; B=<conan 缓存>/b/build/Release
# ① 安装前后 sha256：插件被改写、宿主没有（只查宿主必误判）
sha256sum "$B/libheif/plugins/libheif-svtenc.so" "$P/lib/libheif/libheif-svtenc.so"
#   adca61335903bf1345b96fc46efbd48ef2ab8003572f28498508c3249c86fe41   ← 构建树
#   e904076bfea9e2086bbfdbcb03c48ba984681b5bb2addcb004f3fbd842196671   ← 安装树（变了）
sha256sum "$B/libheif/libheif.so.1.23.0" "$P/lib/libheif.so.1.23.0"
#   d69995c75d5718badd6e90712a6de4d500ab71eb4931c9e097a68c1b20007b61（两边**完全相同**）
readelf -d "$P/lib/libheif/libheif-svtenc.so" | grep -E 'RUNPATH|NEEDED'
#   安装后 RUNPATH 已消失（构建树里是 <build>/svt-av1-prefix/lib:<build>/libheif）；
#   NEEDED 为裸名：libSvtAv1Enc.so.3 / libheif.so.1 / libc++_shared.so / libc.so
# ② 未重签时：dlopen 直接 Permission denied（EACCES），插件永远注册不上
clang test_libheif_svtenc.c -I"$P/include" -L"$P/lib" -lheif -o test_svtenc
LD_LIBRARY_PATH="$P/lib" LIBHEIF_PLUGIN_PATH="$P/lib/libheif" ./test_svtenc
#   dlopen: Error loading shared library …/libheif-svtenc.so: Permission denied
#   heif_init error: Cannot open plugin (dlopen). (11/6000)
#   have_encoder(AV1)=0 … RESULT: 8/14 checks passed
# ③ 只对插件做装后重签，同一条测试立刻全绿
llvm-objcopy --remove-section .codesign "$P/lib/libheif/libheif-svtenc.so"
binary-sign-tool sign -inFile "$P/lib/libheif/libheif-svtenc.so" \
                      -outFile "$P/lib/libheif/libheif-svtenc.so" -selfSign 1
LD_LIBRARY_PATH="$P/lib" LIBHEIF_PLUGIN_PATH="$P/lib/libheif" ./test_svtenc
#   Svt[info]: [asm level selected : up to neon_i8mm]
#   Svt[info]: SVT [config]: width / height … : 128 / 128 … bit-depth / color format : 8 / YUV420
#   encoded output size = 476 bytes
#   RESULT: 14/14 checks passed
# 重签前后插件 sha256：e904076bfea9e208… → 732106c820e284d4…
```

预验同时抓出 1 个编译错误（正式轮前已修）：`heif_deinit()` 返回 `void`
（`heif_library.h:148`），测试里写成 `err = heif_deinit();` 会编译失败；改为
"再 `heif_init()` 一次仍成功"来证明生命周期闭合。

## 验证结果

## 设备验证读数（全部由最终采信轮日志复算，被验证 SHA = `9e276e7e1180383ca8025da45b61228bcbb02b97`）

### 1) 干净轮（`tools/conan_verify_round.sh`：清缓存 → conan-verify → 证据三副本 → finish 前快照）

```
✅ clean：构建标志计数 {'run_make': 14, 'calling_build': 2, 'apply_patch': 1}
```

- `calling_build: 2` = **父工程与内树 SVT-AV1 子工程各一次** `Calling build()`；
- `apply_patch: 1` = 本包唯一补丁（作用于内树 SVT-AV1）；
- `run_make: 14` = 子工程（SVT-AV1 的 CMake 用 Makefile 生成器）的构建调用；
- 证据三副本（`evidence-9e276e7/`）：`conan-create.log`、`conan-verify-report.md`、`w3-local-ci.log`——
  在 `finish` **之前**留存（`finish` 内嵌重跑会整文件覆盖）。

### 2) 交付面与能力（逐字读数）

| 读数 | 值 |
|---|---|
| 插件编译决策 | `Compiling 'svtenc' as dynamic plugin`（其余 **19** 个后端均为 `Not compiling`（干净轮日志实读 19 行 = 18 行 `Not compiling '<name>' backend` + 1 行无 `backend` 后缀的 `Not compiling 'libsharpyuv'`，`grep -c` 三读数为 19/18/1，与 `conanfile.py` 的 19 个禁用项逐项对齐）） |
| SVT-AV1 库 | `libSvtAv1Enc.so.3.1.2` + `SONAME libSvtAv1Enc.so.3`，随包安装到 `lib/` |
| 宿主 | `libheif.so.1.23.0` + `libheif.so.1` + `libheif.so`（`ENABLE_PLUGIN_LOADING=ON`） |
| 安装前后 sha256（插件） | **一致** `3960f9f1447f67d9b1c79548a202744516e4a0c188a9b44d4f5e2f6b077239f5`（RPATH 两行生效：未触发 install 就地改写） |
| 安装前后 sha256（宿主） | **一致** `2a82b837a538019f163021ac75996d52351400c0f1c86a6f36454ec56dc0f5e4`（注意：宿主 sha 逐轮不同——`LIBHEIF_PLUGIN_DIRECTORY` 把**构建时的缓存绝对路径**编进了宿主，这正是必须用 `LIBHEIF_PLUGIN_PATH` 运行期变量兜底的原因） |
| 装后重签（兜底） | `libSvtAv1Enc.so.3.1.2` → `1c58603666b24a547f1235f618b1e841eaea9e4700fe9d9d03b6ee7984265a5b`；`libheif.so.1.23.0` → `a78b49c87598a3d4da34b22a87aef6a4ca0e50d07b34fd7ca828e0f1949e34dd`；`lib/libheif/libheif-svtenc.so` → `aca2aba7ca8e20659cd370a7b0d4586c3b5f14eb8d68efd954151e94320935fb` |
| test_package | **`RESULT: 14/14 checks passed`**（`heif_init()` 成功 → 插件被 dlopen；`have_encoder(AV1)==1`） |
| 真实编码 | `encoded output size = 476 bytes`；SVT 实跑 `asm level selected: up to neon_i8mm`、`128 / 128`、`8 / YUV420`、`preset 10 / CRF 25` |
| `DT_NEEDED`（插件） | `libSvtAv1Enc.so.3` / `libheif.so.1` / `libc++_shared.so` / `libc.so`（**裸名**，非构建期路径） |
| W3 本地 CI 模拟（finish 内嵌） | ✅ `W3 本地 CI 模拟通过`（`build_and_test.sh` 全绿；`L0k`：库类型无需 `commands.json`） |

### 3) 上游测试

`TOTAL = 217 = PASS 0 + FAIL 0 + SKIP 0 + NOT_RUN 217`（原因与逐项归因见「上游测试清点」）。
鸿蒙特有测试（`test_package`）14/14 通过，单独成栏、不并入上游分母。
---

**编译结束**: 2026-09-20 22:52
**最终状态**: built
