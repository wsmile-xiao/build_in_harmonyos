# libstrato 1.0.19 适配笔记

## 编译环境

- 构建系统: cmake（上游 CMakeLists.txt，`cmake_minimum_required(VERSION 3.18)`）
- 编译日期: 2026-09-23
- 编译器: aarch64-unknown-linux-ohos-clang / clang++（clang 15.0.4，包装器自带
  `-target aarch64-linux-ohos --sysroot=<bindir>/../sysroot -fuse-ld=lld -Wl,--code-sign`）
- CMake: 4.1.2　│　Conan: 2.29.1（设备 OHOS 适配版）
- 状态: built

## 上游与目标

StratoHAL 是 ONScripter 系游戏引擎的 HAL 抽象层（图像 / 字形 / 音频 / GL 渲染后端）。
上游**自带** OpenHarmony 目标开关：

- `CMakeLists.txt` 有 `option(STRATO_TARGET_OPENHARMONY "Build for OpenHarmony (OpenGL)" OFF)`
- `target_compile_definitions(strato PUBLIC HAL_TARGET_OPENHARMONY)`
- `target_link_libraries(strato PUBLIC m GLESv2 OpenSLES librawfile.z.so)`
- 源集切换为 `image.c glyph.c wave.c glrender.c slsound.c ohmain.cpp ohfile.cpp`
  （即 `enable_language(CXX)`，需要 C++ 编译器）

但 `cmake/toolchains/` 只有 ios / linux / macos / mingw / openwatcom / unity 共 17 个
工具链文件，**没有 openharmony** ⇒ 交叉工具链需自建。

## 编译步骤

1. `conan create` → `source()` 取官方 tarball（codeload，SHA256 见 conandata.yml）
2. `build()`：
   a. 生成私有 include 前缀（见问题 2）
   b. 生成 OHOS 交叉工具链文件到 build_folder（见问题 1）
   c. 裸 `cmake -S <src> -B <build> -DCMAKE_TOOLCHAIN_FILE=... -DSTRATO_TARGET_OPENHARMONY=ON
      -DSTRATO_ENABLE_SHARED=ON -DSTRATO_ENABLE_DIST=ON -DSTRATO_ENABLE_INSTALL=OFF
      -DCMAKE_SHARED_LINKER_FLAGS="-lEGL -lGLESv3 -lhilog_ndk.z -lace_ndk.z -lace_napi.z"
      -D<各依赖的 Find 结果变量>` → `cmake --build -j2`
3. `package()`：收 `libstrato.so*` + `include/strato/*.h` + LICENSE，并做 ELF 自签名
4. `test_package`：`find_package(StratoHAL)` → 编译链接 → 运行断言（22 条）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `cmake` 完全不认平台：宿主 `uname -s` 返回 **HarmonyOS**，而 CMake 4.1.2 的 `Modules/Platform/` 420 个平台模块里**没有 HarmonyOS/OHOS** | OHOS 设备上 CMake 的默认 `CMAKE_SYSTEM_NAME`=HarmonyOS，无对应 platform module；conan 的 `CMakeToolchain` 在 `os=OHOS` 下 `generic_system` 块为空、不写 `CMAKE_SYSTEM_NAME`/`CMAKE_SYSROOT` | 配方自建交叉工具链文件，显式 `set(CMAKE_SYSTEM_NAME Linux)` + `CMAKE_SYSTEM_PROCESSOR aarch64` + 编译器/`CMAKE_SYSROOT`；CMAKE 走裸 `cmake`，不用 conan_toolchain（仓库既有约定，同 aevol/assimp） |
| 2 | `src/image.c:1486: fatal error: 'png/png.h' file not found` | 上游 `image.c`/`glyph.c`/`wave.c` 按其**自带** `lib/build-libs.sh` 安装出的头文件布局写死 `#include <png/png.h>` / `<jpeg/jpeglib.h>`（该 `#if` 分支只认子目录形式，另一分支要求 `HAL_USE_EXTDLL`），而 conan 包的 libpng/libjpeg-turbo 头文件是**平铺**在 `include/` 下 | 配方在 `build_folder` 建**私有 include 前缀** `deps-prefix/include/{png,jpeg}/`，把依赖的 `*.h` 复制进对应子目录，再把 `PNG_INCLUDE_DIR`/`JPEG_INCLUDE_DIR` 指向该前缀（不改依赖包、不动上游源码） |
| 3 | configure 失败：`install TARGETS given target "stratopack" which does not exist` | 上游 install 块无条件 `install(TARGETS stratopack ...)`，而 `stratopack` 只在 `STRATO_ENABLE_PACK=ON` 时创建 | 关 `STRATO_ENABLE_INSTALL`，由 `package()` 自己收产物（且上游用 `RUNTIME DESTINATION` 装 `.so`，Linux/OHOS 下 `.so` 是 LIBRARY 制品，本就装不出来） |
| 4 | `libpng/1.6.58` 报 `Missing binary`（package_id `f9792081...`） | 制品仓里 `libpng/1.6.58.1/.2/.3` 均 **pin `zlib/1.3.2`**，而 `1.6.58` 的已发布 binary 与 `zlib/1.3.1.1` 组合不匹配 | 依赖组合改为 `libpng/1.6.58.2` + `zlib/1.3.2`（7 个依赖全量解析通过） |
| 5 | 链接期 `undefined symbol: hal_get_image_width / _height / _pixels` | 头文件用 `HAL_DLL` 声明了这三个访问器，但 tag v1.0.19 **全源码树没有实现**（无定义符号） | 消费者改读 `struct hal_image` 的公开成员 `width` / `height` / `pixels`（头文件已标注 public） |
| 6 | 加载期 `Error relocating libstrato.so.1: eglGetDisplay / OH_LOG_Print / OH_NativeXComponent_* / napi_* : symbol not found` | 上游 OHOS 分支的链接集合不完整：`egl*` 需 libEGL、`OH_LOG_Print` 需 libhilog_ndk.z、`OH_NativeXComponent_*` 需 libace_ndk.z、`napi_*` 需 libace_napi.z——上游示例 App 是在 **App 层**补这几个库的 | 库自身声明：`-DCMAKE_SHARED_LINKER_FLAGS` 追加 `-lEGL -lGLESv3 -lhilog_ndk.z -lace_ndk.z -lace_napi.z` |
| 7 | 加载期 `Error relocating libstrato.so.1: glGenVertexArrays / glBindVertexArray / glDeleteVertexArrays: symbol not found`（其余 gl\* 已解析） | OHOS 的 `libGLESv2.so` 是**单地址转发桩**（675 个符号全指向同一地址），只导出 **OES 后缀**名 `glGenVertexArraysOES…`；**核心 ES3 名**只在 `libGLESv3.so` 里（上游 `glrender.c` 用的正是核心名） | 同上追加 `-lGLESv3`（上游示例 App 也是 `EGL GLESv3 OpenSLES`） |
| 8 | 加载期 `Error relocating libstrato.so.1: VIEWPORT_WIDTH / VIEWPORT_HEIGHT: symbol not found` | 上游 `ohmain.cpp` 用 `extern int VIEWPORT_WIDTH/HEIGHT;` 引用视图尺寸，由**消费者**定义（上游示例 App 在 `resources/projects/openharmony/entry/src/main/cpp/napi_init.cpp` 里定义为 1280x720） | 消费者必须导出这两个符号：test_package 定义变量 + `-rdynamic`（`CMAKE_EXE_LINKER_FLAGS`），并使用 `-Wl,--disable-new-dtags` 走 DT_RPATH（musl 下 DT_RUNPATH 不作用于传递依赖） |
| 9 | 本地 `conan-verify` G2 必然失败（`source()` 下载失败） | 本机（新鸿蒙 PC）**ghfast.top 不可达**（实测 rc=000 / 20s 超时 twice；同机 gh-proxy.com 200、github.com 302 均正常），而 `conan_verify.py` 的 E017 预防会**无条件**把 `https://github.com` 前缀成 `https://ghfast.top/https://github.com` | conandata.yml 改用 GitHub 官方归档端点 `https://codeload.github.com/<owner>/<repo>/tar.gz/refs/tags/<tag>`（= `github.com/.../archive/` 的 302 落地点，SHA256 已双向核对一致；仓库内已有 286 个配方采用）。该 URL 不含字面量 `https://github.com`，注入 replace 变成 no-op，下载走官方 |
| 10 | 用 codeload URL 后 `source()` 报 `BadZipFile: File is not a zip file` | codeload URL 末段是 tag 名而不是 `.tar.gz`，conan 无法从 URL 推断压缩格式 | conandata.yml 显式加 `filename: "StratoHAL-v1.0.19.tar.gz"`（仓库内 ad2vcf/adbtuifm/add-determinism 等同样写法） |
| 11 | `make: jobserver mkfifo: .../GMfifoNNNNN: Operation not permitted`（警告，不阻塞） | 设备 `TMPDIR` 在 HMDFS 上，不支持 `mkfifo` | 忽略；make 继续正常执行（已知平台限制） |
| 12 | CI（`conan create` 首步 try_compile）失败：`ld.lld: error: cannot open Scrt1.o/crti.o` `unable to find library -lc`，链接行带 `--sysroot=/data/service/hnp/sysroot` | 配方 `_toolchain_file` 按 `bindir/../sysroot` 推导 sysroot：设备布局 wrapper 在 `~/usr/local/bin`、`../sysroot` 有效 ⇒ 本地全绿；CI worker 的 wrapper 落 `/data/service/hnp/bin`，推出的 `/data/service/hnp/sysroot` 是空壳，且配方把它显式写进 `CMAKE_SYSROOT` **覆盖了 wrapper 自带默认 sysroot** ⇒『本地绿/CI 挂』的单一环境假设盲区（与问题 1 的 CMAKE_SYSTEM_NAME 规避是两条独立机制） | 改为校验制候选链 `_pick_sysroot`（判据=sysroot 的 usr/lib 树内存在 musl 启动对象 crti.o）：`../sysroot` → `~/usr/local/sysroot` → `/data/service/hnp/ohos-sdk.org/*/ohos/native/sysroot`；全部无效则**省略 CMAKE_SYSROOT**、交回 wrapper 自带默认（与其余过 CI 包同路径）。设备行为不变（候选 1 命中） |

## 源码修改

无补丁（`patches/` 为空）。上游源码零改动：所有适配都在配方侧完成
（自建工具链、私有 include 前缀、显式依赖变量、链接集合补全）。

## 依赖版本

| 依赖 | 版本 | 说明 |
|---|---|---|
| libpng | 1.6.58.2 | `.1+` 系列 pin `zlib/1.3.2`（见问题 4） |
| libjpeg-turbo | 3.2.0 | JPEG 解码 |
| libwebp | 1.6.0 | WebP 解码 |
| libogg | 1.3.6 | |
| libvorbis | 1.3.7 | Ogg Vorbis 解码（vorbis + vorbisfile） |
| freetype | 2.14.3 | 字形渲染 |
| zlib | 1.3.2 | 与 libpng 1.6.58.2 对齐 |

上述 7 个依赖均取自 ohpcd 制品仓预编译 binary（未从源码构建）。

## 上游测试账本（五维口径）

| 维度 | 数值 | 依据 |
|---|---|---|
| `N_static`（上游静态声明） | **0** | tag v1.0.19 全源码树（347 文件）无 `enable_testing()` / `add_test()` / `include(CTest)`，无 `tests/`、`test/` 目录，未接入 Catch2/GoogleTest/ctest 等框架 |
| `N_registered`（构建系统注册） | **0** | 同上——无任何测试目标注册 |
| `N_executed`（实际执行） | **0** | 无可执行的上游套件；`make check` / `ctest -N` 均无目标 |
| 未执行分类数 | — | 不适用（上游 0 项） |
| `N_consumer`（新增消费者测试） | **1 个程序 / 22 条断言** | `test_package/test_libstrato.c`，`conan create` 中真实编译+链接+运行，`# ALL PASS` |

> `resources/projects/{android,ios,macos,openharmony}/` 下的 `*Test.ets`、`*Tests` 是上游
> **示例 App 的工程模板资产**（ArkTS / Xcode 工程，不经本库 CMake 注册、也不由本库构建
> 触发），不构成本库的上游测试，故不计入 `N_static`。

## 验证结果

```bash
# 设备：CONAN_HOME=~/tmp/ch/home-hw-3-libstrato，OHC_PROJECT_DIR=~/tmp/hw-3-shadow
python3 scripts/ohc-run.py conan-verify libstrato 1.0.19
# → G0 PASS / G1 PASS / G2 PASS / G3 PASS / G4 PASS / L2 PASS / L4 PASS / L5 PASS
# → ✅ 配方验证通过，可标记 status: published
# → R46 草稿已落盘: milestone=conan_verify_passed
# CIW 修复复验(问题12, 2026-09-23)：CONAN_HOME=~/tmp/ch/home-hw1-libstratofix OHC_PROJECT_DIR=~/tmp/hw-1-libstrato-shadow → conan-verify G0/G1/G2/G3/G4+L2/L5 全 PASS；conan test 复跑消费者 22 断言 # ALL PASS

# conan create 内 test_package 实测（22/22）：
#   ok   - hal_create_image(3,2) 返回 true
#   ok   - hal_create_image 写出非空句柄
#   ok   - 图像宽度 == 3
#   ok   - 图像高度 == 2
#   ok   - 图像像素缓冲非空
#   ok   - hal_clear_image 后 6 个像素值 32 位往返一致
#   ok   - PNG 入口解码 2x2 图像成功
#   ok   - PNG 解码宽度 == 2 / 高度 == 2 / 像素缓冲非空
#   ok   - JPEG 入口解码 2x2 图像成功
#   ok   - JPEG 解码宽度 == 2 / 高度 == 2 / 像素缓冲非空
#   ok   - WebP 入口解码 2x2 图像成功
#   ok   - WebP 解码宽度 == 2 / 高度 == 2 / 像素缓冲非空
#   ok   - PNG 首像素为不透明白 0xFFFFFFFF
#   ok   - 畸形数据经 PNG 入口返回 false
#   ok   - PNG 失败后句柄保持 NULL
#   ok   - 畸形数据经 WebP 入口返回 false
#   # ALL PASS
```

产物 ELF 核对：

```bash
llvm-readelf -d libstrato.so.1.0.0 | grep -E 'SONAME|NEEDED'
#   SONAME libstrato.so.1
#   NEEDED libEGL.so libhilog_ndk.z.so libace_ndk.z.so libace_napi.z.so
#          libGLESv3.so libGLESv2.so libOpenSLES.so librawfile.z.so
#          libpng16.so.16 libjpeg.so.62 libwebp.so.7 libvorbis.so libvorbisfile.so
#          libogg.so libfreetype.so.6 libc++_shared.so libc.so
llvm-readelf -S libstrato.so.1.0.0 | grep codesign
#   [40] .codesign  PROGBITS  ...   → ELF 自签名已写入
```

## 交付物

| 文件 | 大小 | sha256 / 说明 |
|------|------|---------------|
| `lib/libstrato.so.1.0.0` | 342592 B | `81a0d09a647ddac13742db84c7f7aded269e32265c53dd1dac94d0d6892cc19b`（含 `.codesign`，SONAME `libstrato.so.1`，导出 93 个 `hal_*` 符号） |
| `lib/libstrato.so.1` / `libstrato.so` | 软链 | → `libstrato.so.1.0.0` |
| `include/strato/strato.h` | 33501 B | 公开 API 头 |
| `include/strato/c89compat.h` | 17527 B | 兼容层头（`HAL_DLL` 可见性宏在此） |
| `licenses/LICENSE` | 866 B | Zlib 许可 |

## 路径 B（贡献创新）

- **使用知识库**：复用 E092（`cmake-toolchain`）、E078（musl BIND_NOW 立即重定位）、
  `DRAFT-ohos-gl-symbols-are-dispatcher-stubs`、`DRAFT-ohos-egl-headless-no-gles1-baseline`、
  `DRAFT-lld-shlib-undefined-host-contract`
- **新增草稿**：`knowledge/drafts/DRAFT-libstrato-1.0.19-ohos-glesv2-oes-only-core-es3-in-glesv3.{kv,md}`
  —— OHOS 的 `libGLESv2.so` 只导出 **OES 后缀**的 VAO 入口名，**核心 ES3 名**只在
  `libGLESv3.so`（两者符号互不包含）；叠加 BIND_NOW 立即重定位 ⇒ 只链 `GLESv2` 的库产物
  在消费者 **加载期** 即报 `symbol not found`，解法是库自身补 `-lGLESv3`
- **查重结论**：`draft-review` 预审 signature ✅ / root_cause ✅ / rec ✅；
  相似条目 TOP3 = E520(0.58) / E078(0.44) / E509(0.44)，预审建议 `merge-into → E520`；
  逐条比对判定 **create**（E520 是"构建期宿主工具缺 LD_LIBRARY_PATH"，本条是"产物 DT_NEEDED
  缺库"，触发对象/根因/解法/影响面四者全不同）；正式库 `index.tsv` 中 `GLESv3` 命中 **0**；
  组合型知识（BIND_NOW 模型 + GL 转发桩事实 + GLES 版本基线）组合后新增"核心 ES3 名 vs OES
  名"符号分工表与补链接路径 —— 详见草稿 `.md` 的查重结论章节
- **关联 Issue**：#3289（https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/3289）

## 注意事项 / 消费者契约

1. **消费者必须定义 `int VIEWPORT_WIDTH; int VIEWPORT_HEIGHT;` 并导出**（`-rdynamic`）。
   这是上游既有契约（示例 App 定义 1280x720），不是本适配引入的。
2. 消费者需能解析本库的 `DT_NEEDED` 系统库（libEGL / libGLESv3 / libGLESv2 /
   libOpenSLES / librawfile.z / libhilog_ndk.z / libace_ndk.z / libace_napi.z）。
   在 OHOS 设备上这些位于 `~/usr/local/sysroot/usr/lib/aarch64-linux-ohos`；
   musl 加载器下建议用 **DT_RPATH**（`-Wl,--disable-new-dtags`）而非 DT_RUNPATH。
3. 上游未实现 `hal_get_image_width/height/pixels`（问题 5），消费 `struct hal_image`
   的公开成员即可。
4. `hal_create_image_with_jpeg` 对畸形输入会走 libjpeg 的 `error_exit()` **终止进程**
   （上游既有行为，非本适配引入）；消费者若要健壮解码需自设 libjpeg error handler。
5. `make jobserver mkfifo` 警告是 HMDFS 不支持 `mkfifo` 的已知平台限制，不阻塞构建。
---

**编译结束**: 2026-09-23 17:52
**最终状态**: built
