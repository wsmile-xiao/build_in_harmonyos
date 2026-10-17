# E624 — 交付 dlopen 插件模块的 Conan 子包：导出面拆分与消费者双面验证

- 来源任务：`libheif-jpeg` 1.23.0（HarmonyOS PC / OHOS aarch64，2026-09-20）
- 同族：`libheif-libde265` / `-openh264` / `-openjpeg` / `-svtenc` / `-aom` / `-dav1d`
- 相关条目：`E618`（判类：任务名 → 父 tarball 内子模块；本条管判类**之后**的导出面与验证面）

## 1. 问题形态

上游 libheif 把编解码后端做成**运行期 dlopen 的 MODULE 插件**：

```cmake
# libheif/plugins/CMakeLists.txt
plugin_compilation(jpegdec JPEG JPEG_FOUND JPEG_DECODER JPEG_DECODER)
plugin_compilation(jpegenc JPEG JPEG_FOUND JPEG_ENCODER JPEG_ENCODER)
# → add_library(heif-jpegdec MODULE ...) / add_library(heif-jpegenc MODULE ...)
#   install(TARGETS heif-jpegdec LIBRARY DESTINATION ${COMPUTED_PLUGIN_INSTALL_DIRECTORY})
```

于是这个 Conan 包的交付面**分成两层**，而 Conan 的导出机制也正好分两处：

| 层 | 是什么 | 导出到哪 | 混错会怎样 |
|---|---|---|---|
| 链接面/发布面 | 宿主 `libheif.so` | `cpp_info.libs` / `includedirs` / `cmake_file_name` / `pkg_config_name` | 不导出 → 消费者 `find_package` 失败；导出成插件名 → 下游链接 MODULE 直接失败 |
| 运行面 | `lib/libheif/libheif-jpegdec.so`、`libheif-jpegenc.so` | `runenv_info` 导出的 `LIBHEIF_PLUGIN_PATH` | 不导出 → 宿主只在**构建期绝对路径**下找插件，换缓存/换机即「后端不可用」 |

两个具体的坑：

1. **包名 ≠ 消费者的 find_package 名**。Conan 包名是 `libheif-jpeg`（任务卡权威包目录
   名，CI 分支门禁按它匹配），但消费者写的是 `find_package(libheif)` / `pkg-config libheif`
   ——所以 `cmake_file_name`/`cmake_target_name`/`pkg_config_name` 必须取**宿主**名。
   这样六个 codec 子包对消费者是**同构可替换**的：链接面相同，差异只在运行期装载了哪些插件。
2. **插件目录被编译期钉死**。`heif_version.h` 里
   `#define LIBHEIF_PLUGIN_DIRECTORY "@PLUGIN_DIRECTORY@"`，其值是构建时
   `${CMAKE_INSTALL_FULL_LIBDIR}/libheif`（即那一次构建在 Conan 缓存里的绝对路径）。
   跨缓存/跨机必然失效，只能靠 `runenv_info` 注入环境变量兜底
   （`plugins_unix.cc` 读**单数** `LIBHEIF_PLUGIN_PATH`；上游头文件注释里的复数
   `LIBHEIF_PLUGIN_PATHS` 是过期文档）。

## 2. 依赖探测：CMake 内建 MODULE 包也能被 Conan 满足

libheif 找 JPEG 用的是 **CMake 内建 MODULE 包** `find_package(JPEG)`
（树内 `cmake/modules/` 没有 `FindJPEG.cmake`）。配方里既没有 `CMakeDeps` 也没有手钉
`JPEG_INCLUDE_DIR`/`JPEG_LIBRARY`，却仍然命中 Conan 依赖，机制是
**CMakeToolchain 把依赖的目录写进了搜索路径**：

```cmake
# <build>/generators/conan_toolchain.cmake（实测生成物）
list(PREPEND CMAKE_LIBRARY_PATH "/…/.conan2/p/libjp…/p/lib")
list(PREPEND CMAKE_INCLUDE_PATH "/…/.conan2/p/libjp…/p/include")
```

```text
-- Found JPEG: /storage/Users/currentUser/.conan2/p/libjp48ea65bd29cfb/p/lib/libjpeg.so (found version "62")
```

**这条链是「目录搜索」而不是「目标解析」**，所以它有两个方向的风险，都必须留证据：

- 依赖**漏声明**时会静默命中设备系统库（构建照样过、制品却链到 `/usr/lib`）；
- 依赖**声明了**则必须回读解析出的绝对路径**落在 Conan 缓存内**，不能只看 `JPEG_FOUND=TRUE`。

对照：上游自带 Find 模块（如 `FindLIBDE265.cmake`）走 pkg-config + 无 HINTS 的
`find_path`/`find_library`，同一机制也能命中，但更依赖环境里 pkg-config 是否可用/是否污染，
所以同族 libde265 子包改用 cache 变量直接钉路径。两者都对，判据是「解析出的路径可回读」。

## 3. 消费者验证（test_package）必须三层

只有「装上了」不算验证；`heif_have_decoder_for_format()` 返回 1 才是 dlopen +
`dlsym(handle,"plugin_info")` 成功的实证。libheif-jpeg 的 test_package 断言 25 项，分三层：

1. **链接面**：`find_package(libheif REQUIRED)` + `target_link_libraries(t libheif::libheif)`（CMakeDeps 产出）。
2. **运行面**：`self.run(<exe>, env="conanrun")`，在 VirtualRunEnv 注入的
   `LIBHEIF_PLUGIN_PATH` 下断言
   `heif_have_decoder_for_format(heif_compression_JPEG) == 1` 且
   `heif_have_encoder_for_format(heif_compression_JPEG) == 1`，并额外核对
   `getenv("LIBHEIF_PLUGIN_PATH") == LIBHEIF_PLUGIN_DIRECTORY`（编译期宏 vs 运行期环境变量）。
3. **反证 + 端到端**：本包**没交付**的后端必须为 0（HEVC/AV1/JPEG2000 == 0，
   否则说明命中的是系统/别的包的 libheif，或插件被静态编入宿主）；再做一次
   编码→写 `.jpg`→解码→尺寸与像素（±10）往返，证明后端「可用」而非「仅在册」。

> `WITH_REDUCED_VISIBILITY` 保持上游默认 ON 也能装载插件：`plugins/*.h` 用
> `MAYBE_UNUSED LIBHEIF_API extern heif_plugin_info plugin_info;` 声明，`LIBHEIF_API`
> 展开为 `visibility("default")`，宏由 `plugin_compilation()` 注入
> `LIBHEIF_EXPORTS` + `HAVE_VISIBILITY`。**但这条必须有断言②的实测读数**，不接受推断。

## 4. 复现命令（设备可直接执行）

```sh
. "$HOME/tmp/libheif-jpeg-1.23.0/env.sh"

# 构建 + 自动跑 test_package（消费者验证）
conan create "$PACKAGE_DIR" -pr:h="$HOST_PROFILE" -pr:b="$HOST_PROFILE" -c tools.build:jobs=1

# ① 依赖来自 Conan 而非系统库
grep -n "Found JPEG" "$TASK_DIR/logs/w3-create-"*.log
# ② 交付面形态（两个后端都必须是 separate plugin）
grep -n -A3 "Summary of compiled codecs" "$TASK_DIR/logs/w3-create-"*.log
# ③ 消费者断言逐条结果
grep -n "RESULT:\|\[FAIL\]" "$TASK_DIR/logs/w3-create-"*.log
```

## 5. 反面样例（禁止）

```python
# ✗ 把 MODULE 插件当链接面导出 —— 下游 target_link_libraries 直接失败
self.cpp_info.libs = ["heif", "heif-jpegdec", "heif-jpegenc"]
```

```python
# ✗ 只导出宿主、不导出插件目录 —— 换缓存/换机即「后端不可用」，
#    且失败现场没有任何权限/路径线索，只表现为 heif_have_decoder_for_format == 0
self.cpp_info.libs = ["heif"]
# 缺：self.runenv_info.define("LIBHEIF_PLUGIN_PATH", …)
```
