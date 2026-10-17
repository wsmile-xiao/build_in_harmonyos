# E619（草稿）：libheif 编解码插件子包的交付面裁剪与依赖边界判定

- **触发实例**：`libheif-openh264` 1.23.0 全新包适配（2026-09-20，分支 `feat/libheif-openh264-1.23.0`）
- **同族实例**：`libheif-libde265` / `-openjpeg` / `-svtenc` / `-aom` / `-dav1d` / `-jpeg`（同源 tarball，同构）
- **类别**：CMake 子包（父 tarball 内子模块）/ MODULE 插件 / 依赖边界 / OHOS 平台缺口
- **严重度**：2（判定错会得到「包能装、装完不可用」的假绿；平台缺口必现且可确定性复现）

> 实测读数已回填（2026-09-20，`conan create` 真机逐字输出 + 复现脚本
> `$HOME/tmp/libheif-openh264-1.23.0/repro-e619-libheif-plugin-surface.sh`）；
> 逐字输出留档 `$HOME/tmp/libheif-openh264-1.23.0/repro-e619-output.txt`。
> **本条只写交付面与依赖边界的判定方法**；上游 N 清点见同批另一条；通用「同 tarball 子包配方形态」
> 见 E614（OpenFST 家族，静态注册表路线，与本条的动态 MODULE 插件路线不同）。

## 症状（四类，全部实测）

1. **包能装、装完没有本包命名的产物**：只开 `WITH_<CODEC>` 不开 `WITH_<CODEC>_PLUGIN`
   （或漏 `ENABLE_PLUGIN_LOADING`）时，后端被**静态编入宿主** `libheif.so`，
   包目录里根本没有 `lib/libheif/libheif-<codec>.so`——但 `conan create` 全绿。
2. **产物在、宿主也装得上，运行期却装载失败**（本任务首轮真实命中）：
   ```text
   dlopen: Error loading shared library ../libheif.so: (needed by .../lib/libheif/libheif-openh264dec.so)
   heif_init(NULL) -> code=11 (Cannot open plugin (dlopen).)
   heif_have_decoder_for_format(AVC) == 0
   ```
3. **装完报 `Permission denied`（EACCES）而不是 not found**：鸿蒙 PC XPM 要求被 `dlopen` 的 `.so`
   有代码签名，而 `cmake --install` 会就地改写 RUNPATH → 字节变 → 链接器自签失效。
4. **宿主编不过**（追根因时才会撞到，与交付面无关）：
   `libheif/box.cc:4155: error: no member named 'all_of' in namespace 'std::ranges'`。

## 根因

### A. 交付面：三件套开关，且插件不能脱离宿主

libheif 1.23.0 的每个编解码后端由两个宏决定形态（逐字）：

```cmake
# CMakeLists.txt:101-104
macro(plugin_option optionVariableName displayName defaultEnabled defaultPlugin)
    option(WITH_${optionVariableName} "Build ${displayName}" ${defaultEnabled})
    option(WITH_${optionVariableName}_PLUGIN "Build ${displayName} as a plugin" ${defaultPlugin})
endmacro()

# CMakeLists.txt:200（注意 OpenH264 的大小写形态：OpenH264_DECODER，不是 OPENH264_DECODER）
plugin_option(OpenH264_DECODER "OpenH264 decoder" ON OFF)

# libheif/plugins/CMakeLists.txt:2-9 / 31-35（plugin_compilation 宏的二分）
if (PLUGIN_LOADING_SUPPORTED_AND_ENABLED AND WITH_${optionName}_PLUGIN)
    add_library(heif-${name} MODULE ${${optionName}_sources} ...)   # ← 独立插件
    target_link_libraries(heif-${name} PRIVATE ${${varName}_LIBRARIES} heif)   # ← DT_NEEDED 宿主
    install(TARGETS heif-${name} LIBRARY DESTINATION ${COMPUTED_PLUGIN_INSTALL_DIRECTORY})
else ()
    target_sources(heif PRIVATE ${${optionName}_sources})            # ← 静态编入宿主
```

结论：**交付面 = `ENABLE_PLUGIN_LOADING` + `WITH_<CODEC>` + `WITH_<CODEC>_PLUGIN` 三者同时为真**。
上位还要求宿主是共享库（`BUILD_SHARED_LIBS=ON`）——插件是 `MODULE`，只能被宿主 `dlopen`。

树内目标名带 `dec`/`enc` 后缀（`heif-openh264dec`、`heif-j2kdec`、`heif-aomdec`），
与仓库包名 `libheif-<codec>` **不同名**；判定交付面必须看**上游目标名**，不能按包名猜产物名。

### B. 依赖边界：树内 0 份编解码器源码，`find_package` 走 MODULE 模式

```text
$ find <src> -type f -iname '*openh264*'
cmake/modules/FindOpenH264.cmake
libheif/plugins/decoder_openh264.cc
libheif/plugins/decoder_openh264.h          ← 文件匹配数 = 3，无任何第三方源码副本
$ grep -n 'find_package(OpenH264)' CMakeLists.txt
203:    find_package(OpenH264)
```

`cmake/modules/FindOpenH264.cmake` 是 `libfind_pkg_check_modules(openh264)` + 无 HINTS 的
`find_path(NAMES wels/codec_api.h)` / `find_library(NAMES libopenh264 openh264)` ——
**MODULE 模式，不读 CMakeDeps 生成的 `openh264-config.cmake`**。在 Conan 里必须把依赖包的
实际路径钉进 cache 变量（`OpenH264_INCLUDE_DIR` / `OpenH264_LIBRARY`），否则可能命中设备系统库，
或取决于构建环境里 pkg-config 是否可用。

### C. 宿主来源：不能依赖已有的 codec-free 核心包

仓库既有 `archives/l/libheif/1.22.2` 是 `ENABLE_PLUGIN_LOADING=OFF` 且 `WITH_*` 全 False 的
codec-free 核心——**运行期根本不装载插件**，且 1.22.2 与 1.23.0 的插件 ABI 不匹配。
1.23.0 又没有已发布的 base 包，所以插件子包只能**自包含交付同源同版本的宿主**。

### D. 插件目录被编译期钉死

`libheif/heif_version.h.in` → `#define LIBHEIF_PLUGIN_DIRECTORY "@PLUGIN_DIRECTORY@"`，
`@PLUGIN_DIRECTORY@` = 构建时的 `${CMAKE_INSTALL_FULL_LIBDIR}/libheif` **绝对路径**（Conan 缓存路径），
跨缓存/跨机不可移植。`libheif/init.cc:62` 的逻辑是「环境变量给出的目录为空时才回退到该编译期默认值」，
所以 `package_info()` 必须用 `runenv_info` 导出 **`LIBHEIF_PLUGIN_PATH`**（单数！头文件注释里的
复数 `LIBHEIF_PLUGIN_PATHS` 是过期文档，代码读的是单数）。

### E. OHOS 平台缺口 1：宿主无 SONAME → 插件 DT_NEEDED 写成构建树相对路径

设备 `uname -s` = `HarmonyOS`，而 CMake 4.1.2 只有 `Platform/OHOS.cmake`、**没有**
`Platform/HarmonyOS.cmake`（配置期逐字 `System is unknown to cmake, create: Platform/HarmonyOS`），
于是 `CMAKE_SHARED_LIBRARY_SONAME_<LANG>_FLAG` 未定义 → 宿主既没有 `DT_SONAME`，也不生成版本化软链；
CMake 给插件链接时用的是**构建树里的文件路径**，链接器就把这个相对路径写进 `DT_NEEDED`：

```text
$ readelf -d <pkg>/lib/libheif/libheif-openh264dec.so | grep NEEDED
  (NEEDED)  Shared library: [libopenh264.so.7]
  (NEEDED)  Shared library: [../libheif.so]        ← 含斜杠 ⇒ 按 CWD 相对路径解析 ⇒ dlopen 必失败
```

**修法**（`generate()`，不改上游源码）：

```python
if str(self.settings.os) == "OHOS":
    tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
    tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
```

修后：`lib/libheif.so` → `libheif.so.1` → `libheif.so.1.23.0` 三件套、宿主 `SONAME = libheif.so.1`、
插件 `NEEDED = libheif.so.1`（包内存在，运行期由 `LD_LIBRARY_PATH` 解析）。
`MODULE` 插件自身仍是单个 `libheif-openh264dec.so`（插件加载器按 `*.so` 扫描，不受影响）。
等价路线是把 `CMAKE_SYSTEM_NAME` 改成 `Linux`（走 `Platform/Linux.cmake`，仓库 693 个配方同口径）；
两条都能解，但后者会改变 `CMAKE_SYSTEM_NAME`，影响上游 `if(CMAKE_SYSTEM_NAME STREQUAL "Linux")`
分支与查找路径——**优先选更窄的 SONAME 变量注入**。

### F. OHOS 平台缺口 2：libc++ 15 把 C++20 ranges 算法藏在 `_LIBCPP_HAS_NO_INCOMPLETE_RANGES` 后面

上游 `CMakeLists.txt` 设 `CMAKE_CXX_STANDARD 20`，`libheif/box.cc:4155-4166` 用了
`std::ranges::all_of` / `std::ranges::find`；设备 OHOS SDK 的 libc++（`libcxx-ohos`，
`_LIBCPP_VERSION 15004`）在 `__config` 里：

```c
#  if !defined(_LIBCPP_ENABLE_EXPERIMENTAL) && !defined(_LIBCPP_BUILDING_LIBRARY)
#    define _LIBCPP_HAS_NO_INCOMPLETE_RANGES
#  endif
```

于是这两个 ranges 算法从 `<algorithm>` 里被隐藏（**不是**头文件缺失、也不是 `-std=c++20` 没生效——
编译命令行逐字带 `-std=c++20`，`box.cc` 也已 `#include <algorithm>`）。修法：

```python
if str(self.settings.os) == "OHOS":
    tc.preprocessor_definitions["_LIBCPP_ENABLE_EXPERIMENTAL"] = None   # 裸定义
```

（该 conan 版本的 `CMakeToolchain` 没有 `extra_defines`，用 `preprocessor_definitions` 渲染成
`add_compile_definitions`。仓库同口径先例：`archives/l/libpqxx/8.0.1`、`archives/l/ladybug/0.18.2`。
libheif 的**公共 API 头 0 处** `std::ranges`，所以不需要向消费者传播这个宏。）

### G. OHOS 平台缺口 3：`cmake --install` 改写 RUNPATH 破坏代码签名 → dlopen EACCES

鸿蒙 PC XPM 要求被 `dlopen` 的 `.so` 有代码签名（clang launcher 链接期写 `.note.ohos.ident`）；
而 install 会就地改写 RUNPATH → 文件字节变 → 自签失效 → 加载器拒绝映射（报 `Permission denied`，
与「not found」形态完全不同）。**修法：`package()` 在 `cmake.install()` 之后重签**
（`lib/**/*.so*`，跳软链）：

```python
self.run(f'{objcopy} --remove-section .codesign "{path}" 2>/dev/null || true')
self.run(f'{signer} sign -inFile "{path}" -outFile "{path}" -selfSign 1')
```

实测自证（本任务，安装前后 sha256 必然不同，但安装后仍带 `.codesign`）：

```text
build-tree : sha256 6e1eef9b52d2c7e6b3f89dfa9e16ca99ba4f15fe42c00086842bac5d98cae9da
installed  : sha256 f85ef8bcee2138dce40991a5aa16a00e09291038527979f33263f11549c46757
宿主       : build-tree 3ff4a519… → installed f0e42600…
节表       : 构建树与安装后都含 .codesign + .note.ohos.ident
```

**装后重签比 `CMAKE_BUILD_WITH_INSTALL_RPATH`/`CMAKE_INSTALL_RPATH` 更稳**：后者只是不触发失效，
前者连 install 之外的任何改写也能覆盖（仓库 1442 个配方用重签，其中 `archives/o/openh264/2.6.0`、
`archives/f/ffmpeg/8.1.2` 是直接先例）。

### H. 附带发现：CMakeDeps 对「未被直接依赖 re-export 的传递依赖」不写 `includedirs`/`libs`

插件子包的 `test_package` 若要用依赖包自己的 API 做功能验证（R40 多媒体类要求），
**不能**靠 `find_package(openh264)`：同一份 CMakeDeps 数据文件在直接 `requires` 时含
`INCLUDE_DIRS`/`LIBS`，经 `libheif-openh264` 传递时为空（`--build=never` 两次独立复现）：

```text
# 直接 requires openh264/2.6.0
set(openh264_INCLUDE_DIRS_RELEASE "${openh264_PACKAGE_FOLDER_RELEASE}/include")
set(openh264_LIBS_RELEASE openh264)
# 经 libheif-openh264/1.23.0 传递
set(openh264_INCLUDE_DIRS_RELEASE )
set(openh264_LIBS_RELEASE )
```

处置：`test_package` 在 `generate()` 里从 `self.dependencies["openh264"]` 解析实际
include/libdir 并作为 cache 变量下发给 CMakeLists（被动包的交付面仍走标准 CMakeDeps
`find_package(libheif)`）；口径与既有先例 `archives/o/openh264/2.6.0/test_package/conanfile.py` 一致。
（**不要把 `cpp_info.requires` 当解法**：宿主 `libheif.so` 在插件模式下并不链接 openh264
（上游 `CMakeLists.txt:462-464` 显式从 `REQUIRES_PRIVATE` 排除），声明 re-export 会向所有消费者
错误地传播依赖包的 include 与链接项。）

## 判定清单（五问，任一答错即「包能装、装完不可用」）

1. **交付面是哪三件套？** `ENABLE_PLUGIN_LOADING` + `WITH_<CODEC>` + `WITH_<CODEC>_PLUGIN`；
   产物名看**上游目标名** `heif-<name>`（可能带 `dec`/`enc` 后缀），不是包名。
2. **插件能不能只交付插件 `.so`？** 不能：`DT_NEEDED` 宿主 + 宿主 `heif_init()` 扫目录 `dlopen`。
3. **宿主从哪来？** 找一个 `ENABLE_PLUGIN_LOADING=ON` 且**同版本**的宿主包；没有就自包含构建。
   注意 codec-free 核心包（如本仓库 `libheif/1.22.2`）**装不了插件**。
4. **依赖是外部包还是内树？** `find <src> -type f -iname '*<codec>*'` 数一遍：只有 `Find*.cmake`
   与 `plugins/*.cc/.h` ⇒ 外部依赖；`find_package` 若是 MODULE 模式（`libfind_pkg_check_modules` +
   无 HINTS 的 `find_path/find_library`），用 cache 变量钉住依赖路径。
5. **插件目录怎么让消费者找到？** `runenv_info` 导出 `LIBHEIF_PLUGIN_PATH`（单数）。
   另需检查 OHOS 的三个平台缺口：SONAME（E）、libc++ ranges（F）、dlopen 目标签名（G）。

## 复现命令

```sh
TASK_DIR=$HOME/tmp/libheif-openh264-1.23.0
sh "$TASK_DIR/repro-e619-libheif-plugin-surface.sh"      # 四组读数 + SONAME 新旧对照
# 逐字输出留档：$TASK_DIR/repro-e619-output.txt
```

配方侧最小改动集（本任务实测可用，全部经 `CMakeToolchain`，零补丁）：

```python
tc.variables["BUILD_SHARED_LIBS"] = True
tc.variables["ENABLE_PLUGIN_LOADING"] = True
tc.variables["WITH_OpenH264_DECODER"] = True
tc.variables["WITH_OpenH264_DECODER_PLUGIN"] = True
tc.cache_variables["OpenH264_INCLUDE_DIR"] = <依赖包 include 绝对路径>
tc.cache_variables["OpenH264_LIBRARY"] = <依赖包 lib/libopenh264.so 绝对路径>
if str(self.settings.os) == "OHOS":
    tc.preprocessor_definitions["_LIBCPP_ENABLE_EXPERIMENTAL"] = None
    tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
    tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
# build(): cmake.build(target=["heif", "heif-<codec>"])   # 只建交付面两个目标
# package(): cmake.install() 之后再 _sign_binaries(lib/**/*.so*)
# package_info(): cpp_info.libs = ["heif"]; runenv_info LIBHEIF_PLUGIN_PATH=<pkg>/lib/libheif
```

## 实测读数

| 项 | 读数 |
|---|---|
| `conan create`（干净缓存轮） | rc=0 |
| `test_package` | `LIBSHEIF_OPENH264_CONSUMER checks_total=14 checks_passed=14` → `RESULT: PASS` |
| 宿主 | `lib/libheif.so` → `.so.1` → `.so.1.23.0`，`SONAME = libheif.so.1` |
| 插件 | `lib/libheif/libheif-openh264dec.so`，`NEEDED = libopenh264.so.7, libheif.so.1, libc++_shared.so, libc.so` |
| 插件导出符号 | `nm -D` → `00000000000069f8 D plugin_info` |
| 能力标识只在插件里 | 宿主含 `OpenH264` 行数 = 0；插件含 `OpenH264 %d.%d.%d` / `libopenh264.so.7` |
| 运行期能力 | `heif_have_decoder_for_format(AVC)==1`、`heif_load_plugins → loaded=1`、`have_encoder(AVC)==0` |
| R40 功能性 | libopenh264 编码 320x240 I420 → 360 bytes / 2 layers → 解码 `dsErrorFree` 出帧 320x240 |
| 依赖可用性（R35） | `conan install --requires=openh264/2.6.0 --build=never -pr:h=<绝对 profile>` rc=0 |

## 适用边界

- 适用信号（三条全中）：① 包名 ≠ 父项目名（子模块子包） ② 构建声明里有
  `plugin_option`/`add_library(... MODULE ...)` 或等价的「独立装载插件」开关
  ③ 交付产物 `readelf -d` 显示 `DT_NEEDED` 另一个**同源**库。
- 不适用：编解码器被**静态编入**宿主的包（此时交付面就是宿主本身）；也不同于 E614 的
  「同 tarball 扩展开关 + 静态注册表 + `--whole-archive`」路线（那条没有 dlopen 环节）。
- 本条 E~G 三个平台缺口对**任何**在 OHOS 上用 CMake 构建共享库/可执行文件的包都可能成立，
  与 libheif 无关；libheif 插件只是把它们一次性全踩齐了。
