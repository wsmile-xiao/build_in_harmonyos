# ffmpeg 7.1.5 编译笔记（HarmonyOS PC · 原生 conan create）

## 定位

产出 FFmpeg 的七个动态库 + 两个命令行工具，供鸿蒙 PC 上依赖 ffmpeg 的 Python 库消费：

| 产物 | soname | 消费方 |
|---|---|---|
| `lib/libavutil.so.59` | avutil 59 | 全部 |
| `lib/libavcodec.so.61` | avcodec 61 | PyAV、OpenCV videoio |
| `lib/libavformat.so.61` | avformat 61 | PyAV、OpenCV videoio |
| `lib/libavdevice.so.61` | avdevice 61 | PyAV |
| `lib/libavfilter.so.10` | avfilter 10 | PyAV |
| `lib/libswscale.so.8` | swscale 8 | PyAV、OpenCV |
| `lib/libswresample.so.5` | swresample 5 | PyAV |
| `bin/ffmpeg`、`bin/ffprobe` | — | moviepy / pydub / openai-whisper / imageio-ffmpeg / ffmpeg-python 等**调 CLI** 的库 |

选 7.1 分支的理由：它是仍在回合安全修复的准 LTS，且 PyAV 14.x 精确钉 FFmpeg 7.1；
8.0（avcodec 62）Python 侧 binding 尚未普遍跟上，6.1（avcodec 60）则要长期背 5.1/7.0 两处 API 断层。

## 关键适配

### 1. FFmpeg 的 configure 不是 autoconf —— 不能用 AutotoolsToolchain

FFmpeg 自带手写 shell `configure`（仓内无 `configure.ac`/`Makefile.am`），只认自有选项名
（`--incdir` 而非 `--includedir`，无 `--build`/`--host`），遇未知选项走 `die_unknown` 直接退出。
`AutotoolsToolchain` 会传一串 autoconf 标准路径选项，必然当场失败。
故本配方 `generate()` 留空，全部参数在 `build()` 里按 FFmpeg 自己的选项名显式拼。

### 2. `--target-os=linux` 是硬要求

`configure` 第 4109 行 `target_os_default=$(tolower $(uname -s))`，设备上得到 `harmonyos`，
落到 `case` 分支外 → 第 5989 行 `die "Unknown OS 'harmonyos'."`。必须显式给 `--target-os=linux`
（OHOS 内核接口与 linux 一致，libc 为 musl）。这是 ffmpeg 版的「config.guess 不认 HarmonyOS」。

### 3. 签名：`.so` 与 `bin/` 都必须重签

`ffbuild/library.mak:82-83` 的安装动作是 `install -m 755` **复制** + `$(STRIP)` **剥离**已安装的 `.so`
——两步都会破坏链接器自签。因此：

- `--disable-stripping` 关掉 install 期 strip；
- `package()` 调 `_sign_binaries()`，对 `lib/*.so*` 与 `bin/{ffmpeg,ffprobe}` 统一 `binary-sign-tool` 重签。

### 4. `--disable-autodetect` + 显式补回 pthreads

设备 `.zshrc` 会把 `~/usr/local` 的头/库导进 `CFLAGS`/`LDFLAGS`/`PKG_CONFIG_PATH`，autodetect 会把它们
静默链进来，包就不自包含也不可复现。故关掉自动探测。
但 `AUTODETECT_LIBS` 含 `$THREADS_LIST`，一并关掉会**丢多线程解码**，必须 `--enable-pthreads` 补回。

### 5. zlib 走 `check_lib` 而非 pkg-config

`configure:6842` 是 `check_pkg_config zlib ... || check_lib zlib zlib.h zlibVersion -lz`。
本配方给 zlib 的是显式 `-I/-L`（见「接入外部编解码器」一节的 `_CHECKLIB_DEPS`），走 `check_lib` 分支。
> 初版曾在 `build()` 开头**清空** `PKG_CONFIG_PATH` 以绕开依赖包自带 `.pc` 里 prefix 烤死的问题；
> 接入外部库后改为**清空后只指向 conan `PkgConfigDeps` 生成的目录**——那些 `.pc` 路径本就是对的，
> 既隔离了设备环境污染，又让 openh264/vpx/opus 等的 `require_pkg_config` 能正常工作。
zlib 是带 `-fPIC` 的静态包，内链进 `libavcodec.so`/`libavformat.so`，不引入运行期 `libz.so` 依赖（R26）。

### 6. `--disable-debug` 控体积

不关则七个 `.so` 带完整调试信息，制品体积会逼近制品仓单文件上限（历史上 LLVM 踩过 413）。

### 7. prefix 在 configure 时就要给最终路径

FFmpeg 在 **build 期**生成 `lib*.pc` 并把 prefix 烤进去，不是 install 期。所以 `--prefix` 必须直接指
conan 包目录。已核对 conan 2.20 `internal/graph/installer.py:143`：`set_base_package()` 在 `_build()`
**之前**调用，`self.package_folder` 在 `build()` 里可用。

### 8. `.pc` 的 libdir/includedir 必须重定位（PyAV 试链时实测暴露）

`ffbuild/pkgconfig_generate.sh` 生成 `.pc` 时写的是：

```sh
prefix=$prefix
libdir=$libdir          # ← configure 时的绝对路径字面量
includedir=$incdir      # ← 同上
Libs: -L\${libdir} ...  # 引用变量
```

`libdir`/`includedir` 是**绝对路径字面量**而非 `${prefix}` 相对，只有 `prefix=` 一行能被
`usr_local` deployer 重写。后果：部署到 `~/usr/local` 后 `pkg-config --cflags --libs libavcodec`
仍吐 conan cache 路径，消费方（PyAV）会照着去链 cache 里的库，部署形同虚设。

`package()` 里加 `_relocate_pc()` 改写成 `${exec_prefix}/lib` / `${prefix}/include`，
deployer 改 `prefix=` 后即整体跟随。修复前 7 个模块全部误指 cache，修复后为 0。

> 这个坑对**任何用 `--libdir`/`--incdir` 显式指定绝对路径的 autotools 类库都通用**，不限于 ffmpeg。

## 许可

按 **LGPL-2.1** 构建：未启用 `--enable-gpl` / `--enable-nonfree` / `--enable-version3`，
不含 x264/x265 等 GPL 组件。如后续需要 H.264 **编码**，用 openh264（BSD）而非 x264，以免许可传染。

## 已知限制

- **无硬件加速**：鸿蒙 PC 无 VAAPI/VDPAU/NVDEC，FFmpeg 也无 OHOS hwaccel 后端，全为软编软解。
  走系统 AVCodec Kit（`OH_AVCodec` NDK）硬解需要另写 hwaccel 后端，属独立课题。
- **无 iconv**：字幕字符集转换不可用（iconv 属 autodetect）。
- **无 ffplay**：需 SDL2，设备无。

> 「无外部编解码库」这一条已不再成立——见下「接入外部编解码器与功能库」，现已接入
> openh264/libvpx/opus/lame/openssl/freetype/harfbuzz/fontconfig/libxml2/bzip2/xz。

## 真机验证结果（2026-07-25，设备 3QC0124C11000718）

裸 `conan create . -pr ohos-native`（不带 `-c:h`，模拟 CI）**rc=0，real 4m52s**，包体积 **25M**。

### 产物

| 文件 | 大小 | SONAME | DT_NEEDED |
|---|---|---|---|
| `libavutil.so.59.39.100` | 776 KB | libavutil.so.59 | libc.so |
| `libswresample.so.5.3.100` | 117 KB | libswresample.so.5 | libavutil, libc |
| `libswscale.so.8.3.100` | 674 KB | libswscale.so.8 | libavutil, libc |
| `libavcodec.so.61.19.101` | 13.3 MB | libavcodec.so.61 | libswresample, libavutil, libc |
| `libavformat.so.61.7.103` | 2.7 MB | libavformat.so.61 | libavcodec, libavutil, libc |
| `libavfilter.so.10.5.100` | 3.9 MB | libavfilter.so.10 | libswscale, libavformat, libavcodec, libswresample, libavutil, libc |
| `libavdevice.so.61.3.100` | 72 KB | libavdevice.so.61 | libavfilter, libavformat, libavcodec, libavutil, libc |
| `bin/ffmpeg` | 347 KB | — | 七个 libav* + libc |
| `bin/ffprobe` | 261 KB | — | 同上 |

`include/libav*/`、`lib/pkgconfig/lib{avcodec,avdevice,avfilter,avformat,avutil,swresample,swscale}.pc` 齐全。

**DT_NEEDED 里没有 `libz.so`** —— 证实 zlib 已静态内链，未引入运行期系统库耦合（R26 达标）。

### 签名

七个 `.so` + `bin/ffmpeg` + `bin/ffprobe` 共 9 个 ELF，`readelf -S` 均含 1 个 `.codesign` 段；
且 `bin/ffmpeg -version`、`ffprobe -version` 真跑 rc=0（不是只看段在不在——旧 qpdf 有段但自签无效仍
`Operation not permitted`）。

### 编译配置实测

`--enable-pthreads` / `--enable-zlib` / `--enable-shared` / `--disable-autodetect` 均生效；
`--enable-gpl`、`--enable-nonfree` 均为 0，LGPL 达标。
编码时打印 `too many threads/slices (16), reducing to 15`，反证多线程确实开着（探测到 16 线程）。

### 端到端闭环

lavfi 生成 320x240@10fps 视频 + 440Hz 正弦音频 → mpeg4/aac 编码 → mp4 封装（59,124 字节）→
`ffprobe` 解析出 `mpeg4/320x240` + `aac/44100Hz` → 解码回 null，**四步全部 rc=0**。

### 已知无害项

`.pc` 与 `bin/ffmpeg` 的 `configuration:` 串里烤着 conan cache 绝对路径。`.pc` 的 prefix 由
`usr_local` deployer 在部署时重定位；`configuration:` 串纯属版本信息展示，运行期不使用
（datadir 只用于 ffpreset 预设文件，本包不 ship 预设）。

## 消费验证：PyAV 14.4.0 源码编译试链（2026-07-25，真机）

本包的核心用途是喂给依赖 ffmpeg 的 Python 库，故除 test_package 外另做了真实消费方验证。
选 PyAV 14.4.0 是因为它的 `setup.py` 明确写着 *"You are **REQUIRED** to use ffmpeg 7"*，
是与 7.1.x 确定匹配的最后一个系列（PyAV 18.x 的源码里已出现 `FFmpeg 8.1` 的 API 注记，主线已转向 8.x）。

流程：`conan install --deployer=usr_local --deployer-folder=~/usr/local` → `pkg-config` 发现 →
隔离 venv → `pip install --no-build-isolation --no-binary :all: av-14.4.0.tar.gz`（源码现编）。

### 版本对账（PyAV 报告的库版本 vs 本包 soname）

| 库 | `av.library_versions` | 本包 |
|---|---|---|
| libavcodec | (61, 19, 101) | libavcodec.so.61.19.101 ✅ |
| libavformat | (61, 7, 103) | libavformat.so.61.7.103 ✅ |
| libavutil | (59, 39, 100) | libavutil.so.59.39.100 ✅ |
| libavdevice | (61, 3, 100) | libavdevice.so.61.3.100 ✅ |
| libavfilter | (10, 5, 100) | libavfilter.so.10.5.100 ✅ |
| libswscale | (8, 3, 100) | libswscale.so.8.3.100 ✅ |
| libswresample | (5, 3, 100) | libswresample.so.5.3.100 ✅ |

`av/*.so` 的 DT_NEEDED 确认链到本包七件套 + libpython3.12.so.1.0 + libc.so。

### 跨实现互验

- PyAV 解码 ffmpeg CLI 产的 mp4：视频 20 帧、音频 87 帧，首帧 320×240 yuv420p —— 全对
- PyAV 编码写出 mp4（19,186 字节）→ 用本包 `ffprobe` 反查 → `mpeg4 / 320×240` —— 正确

### 途中撞到的设备环境问题（非本包缺陷，但影响所有现编 C 扩展的 Python 库）

同一 Python 进程内：`shutil.which('pkg-config')` 能返回 `/data/service/hnp/bin/pkg-config`，
但 `subprocess(["pkg-config", ...])` 报 `FileNotFoundError`，换成绝对路径立刻正常。
PATH 里确实含 `/data/service/hnp/bin`，故不是 PATH 未配置；**机理未查明，此处只记录现象**。

影响面：设备 `sysconfig` 里 `CC = clang`（裸名）且 `which cc = None`，所以 setuptools 编任何
C 扩展都会撞上。绕法是把 `PKG_CONFIG`/`CC`/`CXX`/`AR`/`RANLIB`/`LDSHARED` 全部绝对路径化
（`LDSHARED` 从 `sysconfig` 取值后只替换首个 `clang` token，其余链接参数保持原样）。

## 接入外部编解码器与功能库（2026-07-25）

初版用 `--disable-autodetect` 只留内建能力，实测缺口集中在**编码侧与网络侧**（解码侧 502 个解码器本就齐全）。
本次接入 12 个已在制品仓的依赖补齐：

| 解锁能力 | 依赖 | FFmpeg 探测方式 |
|---|---|---|
| **H.264 编码** | `openh264/2.6.0` | `require_pkg_config libopenh264 "openh264 >= 1.3.0"` |
| **VP8/VP9 编码** | `libvpx/1.16.0` | `check_pkg_config libvpx_vp8_encoder "vpx >= 1.4.0"` |
| **Opus 编码** | `opus/1.5.2.1` | `require_pkg_config libopus opus` |
| **MP3 编码** | `lame/4.0` | `require ... -lmp3lame`（**不走 pkg-config**，lame 上游不装 .pc） |
| **https / tls** | `openssl/3.5.6` | `check_pkg_config openssl "openssl >= 3.0.0"` |
| **drawtext 滤镜** | `freetype/2.14.3` + `harfbuzz/14.2.0` | 两者**都要**，见下 |
| drawtext 字体选择 | `fontconfig/2.18.1.1` | `require_pkg_config libfontconfig fontconfig` |
| **dash 解封装** | `libxml2/2.15.3` | `require_pkg_config libxml2 libxml-2.0` |
| bzlib / lzma | `bzip2/1.0.8`、`xz/5.6.2` | `check_lib` |

**许可未变**：新接入的全是 BSD/LGPL。特意核对了 openssl —— `configure` 里「OpenSSL >=3.0 要求
`--enable-version3`」的分支**仅在 `enabled gpl` 时**成立（`! enabled gpl` 直接放行），我们不开 gpl 故无影响。
**选 openh264 而非 x264/x265**：后者在 `EXTERNAL_LIBRARY_GPL_LIST` 里，启用会强制 `--enable-gpl` 使整包变 GPL。

### 接线机制

走 pkg-config 的用 **`PkgConfigDeps`** 生成 `.pc`——关键是它按 conan 依赖的**真实路径**写，绕开依赖包自带
`.pc` 里 prefix 烤死的问题。`build()` 先清空环境污染，再把 `PKG_CONFIG_PATH` **只**指向 conan 生成目录，
使外部库探测完全不受设备 `~/usr/local` 影响。走 `check_lib` 的四个（zlib/bzip2/lzma/mp3lame）补 `-I/-L`。

### 这次踩的五个坑（其中两个已在上游依赖包修复）

1. **drawtext 需要 harfbuzz，不只是 freetype**：FFmpeg 6.1 起
   `drawtext_filter_deps="libfreetype libharfbuzz"`，少任一个滤镜就不编进去，且 configure **不报错**、
   只是静默不生成该滤镜。7.1.5 与 8.1.2 都是这条。

> **版本界限已实测校正**：harfbuzz 是 **6.1 引入**的，不是 7.0——`ffmpeg-6.0.1/configure` 里
> `drawtext_filter_deps="libfreetype"` 且**无 `libharfbuzz` 选项**；`6.1.6` 起才变成
> `"libfreetype libharfbuzz"`。故 6.1 / 7.x / 8.x 需要 harfbuzz，5.1 / 4.4 不需要
> （且给它们传 `--enable-libharfbuzz` 会被 `die_unknown` 打死）。
>
> 注：本目录 `conanfile.py` 里的同名注释仍写「7.0 起」，**未随本次一并更正**——修改
> `conanfile.py` 会改变 recipe revision，按 R37 需把已发布版本号递增后缀并重发制品，
> 为一句注释不值得。以本文件所述为准。


2. **`ERROR: opus not found using pkg-config` 报错具误导性**：pkg-config 其实找得到 opus
   （`--exists` rc=0、`--modversion` 返回 1.5.2），失败的是紧随其后的 `check_func_headers` 编译探测。
   根因是**当时制品仓的 `opus/1.5.2` 未设 `cpp_info.includedirs`**：opus 头装在 `include/opus/`，
   上游 `opus.pc` 写的是 `Cflags: -I@INCDIR@/opus`，故消费方按 `#include <opus_multistream.h>`
   （不带前缀）来写；而 conan 生成的 `opus.pc` 只给 `-I<pkg>/include`。
   > **已在上游包修复**：`opus/1.5.2.1` 补上了 `includedirs = ["include/opus", "include"]`
   > （参照 freetype 包的既有做法）。本配方遂改依赖该版本，并**移除了此前在消费方补
   > `-I<opus>/include/opus` 的绕行代码**。

3. **fontconfig 的二进制不可重定位（换环境才暴露）**：清空设备 conan cache 重建时，test_package
   运行期崩溃——`libfontconfig.so.1` 的 DT_NEEDED 里烤着 expat 的**绝对路径**
   `/…/p/expat<hash>/p/lib/libexpat.so`，expat 落到别的包目录哈希就 `Error loading shared library`
   加一串 `XML_* symbol not found`。
   根因在 `expat/2.8.2`：其配方用 conan `CMakeToolchain`，`os=OHOS` 下产物**无 SONAME**，
   而链接器遇到无 SONAME 的被链库时会把该库的**路径**写进消费方 DT_NEEDED。
   > **已在上游包修复**：`expat/2.8.2.1` 改用「自发现 ohos.toolchain + 裸 cmake」正常生成 SONAME，
   > `fontconfig/2.18.1.1` 重新链接后 DT_NEEDED 变为 `libexpat.so.1` 等纯 soname。
   > 本配方遂改依赖 `fontconfig/2.18.1.1`。

4. **用了 components 就必须登记每个直接依赖**：conan 校验 `package_info()`，任一直接依赖未被某个
   component 的 `requires` 引用即报 `The direct dependency 'X' is not used by any
   (cpp_info/components).requires`。本配方按实际用途分配（编解码器归 avcodec、协议/容器归 avformat、
   字体归 avfilter）。注意 **harfbuzz 自身带 components**，须引用 `harfbuzz::harfbuzz` 而非包名。

5. **产物不再自包含**：接入前 `bin/ffmpeg` 只 NEEDED libc 与自家 libav 系列；现在还 NEEDED
   `libopenh264.so.7` / `libvpx.so.12` / `libopus.so.0` / `libmp3lame.so.0` / `libfontconfig.so.1` /
   `libfreetype.so.6` / `libxml2.so.16`。**消费方必须部署整个依赖图**——`usr_local` deployer 会自动展开，
   裸拷 ffmpeg 单包会在加载期报 `Error loading shared library`。

## 真机验证结果（2026-07-25，设备 3QC0124C11000718）

`conan create . -pr ohos-native` **rc=0，306s**，包体积 30M。
test_package 8 条断言全绿；另按**真实消费路径**（`usr_local` deployer 部署整个依赖图后从部署前缀跑 CLI）复验：

- **外部编码器**：libopenh264 / libvpx / libopus / libmp3lame 四个全部注册
- **协议**：https、tls 均在（openssl 接线成功）
- **滤镜**：drawtext 在（freetype + harfbuzz + fontconfig 接线成功）
- **封装**：dash 在（libxml2 接线成功）
- **真实转码 ①**：lavfi → **libopenh264 + libmp3lame** → mp4（42040 字节），
  `ffprobe` 反查 `codec_name=h264` / `mp3`、320x240
- **真实转码 ②**：lavfi → **libvpx-vp9 + libopus** → webm（15410 字节），
  反查 `codec_name=vp9` / `opus`
- **真实滤镜**：`drawtext` 用系统字体 `/system/fonts/DejaVuMathTeXGyre.ttf` 烧字出图（4711 字节）
- **签名**：7 个 `.so` + `bin/ffmpeg` + `bin/ffprobe` 共 9 个 ELF 均含 `.codesign` 段

### 仍缺的能力

- **subtitles / ass 滤镜**：需 `libass`，制品仓暂无
- **硬件加速**：鸿蒙 PC 无 VAAPI/VDPAU/NVDEC，FFmpeg 亦无 OHOS hwaccel 后端，为纯软编软解
- **iconv**：属 autodetect，未启用，字幕字符集转换不可用
- **ffplay**：需 SDL2，设备无

## 状态

built —— 真机 `conan create` + test_package(8 断言) + 外部编解码器接线 + 真实转码/滤镜全绿。
