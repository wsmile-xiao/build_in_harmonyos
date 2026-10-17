# ffmpeg 8.1.2 编译笔记（HarmonyOS PC · 原生 conan create）

## 定位

FFmpeg 当前功能主线（`release/8.1`）的点版本，与本仓 `archives/f/ffmpeg/7.1.5/` 的准 LTS 配方**并存**：
两代 soname 完全不同，可同时装在设备上互不冲突，由消费方按需选择。

| 产物 | 8.1.2 soname | 对应 7.1.5 |
|---|---|---|
| `libavutil` | **60** | 59 |
| `libavcodec` | **62** | 61 |
| `libavformat` | **62** | 61 |
| `libavdevice` | **62** | 61 |
| `libavfilter` | **11** | 10 |
| `libswscale` | **9** | 8 |
| `libswresample` | **6** | 5 |
| `bin/ffmpeg`、`bin/ffprobe` | — | — |

### 该选哪一代

- **调 CLI 的 Python 库**（moviepy / pydub / openai-whisper / imageio-ffmpeg / ffmpeg-python）：
  两代都行，命令行接口十几年稳定。
- **按 soname 链 libav\* 的**（PyAV、源码编译的 OpenCV videoio）：**必须版本对齐**。
  PyAV 14.x 明确要求 FFmpeg 7（其 `setup.py` 写着 "REQUIRED to use ffmpeg 7"），
  而 PyAV 18.x 源码里已出现 `FFmpeg 8.1` 的 API 注记 —— 主线已转向 8.x。
  故 **8.1.2 对应较新的 PyAV，7.1.5 对应 PyAV 14.x**。

## 关键适配

本配方**由已在真机验证通过的 7.1.5 配方派生**，仅改版本号与 sha256。派生前对 8.1.2 源码逐条复核了
七个适配点，**全部一致**：

| # | 适配点 | 8.1.2 中的证据 |
|---|---|---|
| 1 | configure 是手写 shell 脚本、非 autoconf | 仓内无 `configure.ac`/`Makefile.am` |
| 2 | 未知 OS 会 die | `configure:6300` `die "Unknown OS '$target_os'."` |
| 3 | install 复制 + strip 破坏签名 | `ffbuild/library.mak:98-99` `$(INSTALL) -m 755` + `$(STRIP)` |
| 4 | `.pc` 的 libdir/incdir 是绝对字面量 | `ffbuild/pkgconfig_generate.sh:32-33` `libdir=$libdir` / `includedir=$incdir` |
| 5 | `AUTODETECT_LIBS` 含 `THREADS_LIST` | configure 中该变量定义未变 |
| 6 | zlib 走 `check_pkg_config \|\| check_lib` | `configure:7185` |
| 7 | 路径选项名为 `--incdir` 而非 `--includedir` | configure 帮助段 |

因此各项处理与 7.1.5 相同，详细机理见 `archives/f/ffmpeg/7.1.5/notes.md`：

1. `generate()` 留空，不用 `AutotoolsToolchain`，在 `build()` 里按 FFmpeg 自有选项名显式拼参数
2. 显式 `--target-os=linux --arch=aarch64`
3. `--disable-stripping` + `package()` 对 `lib/*.so*` 与 `bin/` 下真实 ELF 统一重签
4. `package()` 的 `_relocate_pc()` 把 `.pc` 的 libdir/includedir 改写为 `${exec_prefix}`/`${prefix}` 相对
5. `--disable-autodetect` + `--enable-pthreads` 补回多线程
6. `build()` 开头清 env 污染；zlib 走 `check_lib` + 显式 `-I/-L`（接入外部库后 `PKG_CONFIG_PATH`
   改为只指向 conan `PkgConfigDeps` 生成目录，见下节）
7. `--disable-debug` 控体积

### 8.1.2 相对 7.1.5 的一处新增观察

`configure:7190` 多了一条 `enabled zlib && test_exec $zlib_extralibs ... && enable zlib_gzip`，
是**运行期 exec 探测**。原生构建（build == host）下 conftest 由 clang 直链、自签有效，可正常执行；
即便失败也只是不启用 `zlib_gzip` 这一可选特性（`&&` 短路），不影响构建成功。

## 许可

按 **LGPL-2.1** 构建：未启用 `--enable-gpl` / `--enable-nonfree` / `--enable-version3`，
不含 x264/x265 等 GPL 组件。

## 已知限制

同 7.1.5：无硬件加速（鸿蒙 PC 无 VAAPI/VDPAU/NVDEC，FFmpeg 亦无 OHOS hwaccel 后端）；无 iconv；无 ffplay。

> 「仅内建编解码器」已不再成立——见下「接入外部编解码器与功能库」。

## 真机验证结果（2026-07-25，设备 3QC0124C11000718）

裸 `conan create . -pr ohos-native` **rc=0，real 5m04s，一次通过**（无需迭代），包体积 25M。

| 库 | 大小 | SONAME |
|---|---|---|
| `libavcodec.so.62.28.102` | 13.4 MB | libavcodec.so.62 |
| `libavfilter.so.11.14.102` | 4.0 MB | libavfilter.so.11 |
| `libavformat.so.62.12.102` | — | libavformat.so.62 |
| `libavutil.so.60.26.102` | — | libavutil.so.60 |
| `libavdevice.so.62.3.102` | 76 KB | libavdevice.so.62 |
| `libswscale.so.9.5.102` | — | libswscale.so.9 |
| `libswresample.so.6.3.102` | — | libswresample.so.6 |

- **签名**：7 个 `.so` + `bin/ffmpeg` + `bin/ffprobe` 共 9 个 ELF 均含 `.codesign` 段，
  且 CLI 真跑 `-version` rc=0（不是只看段在不在）
- **配置核对**：`enable-pthreads` / `enable-zlib` / `enable-shared` / `disable-autodetect` 均为 1；
  `enable-gpl` / `enable-nonfree` 均为 0，LGPL 达标
- **端到端**：lavfi 生成视频+音频 → mpeg4/aac 编码 → mp4 封装（59,123 字节）→
  ffprobe 解析出 mpeg4 与 aac → 解码回 null，四步全部 rc=0
- **部署验证**：`usr_local` deployer 部署后 `.pc` 为 `libdir=${exec_prefix}/lib`、
  `includedir=${prefix}/include`，`pkg-config` 误指 conan cache 的模块数为 **0**
  （7.1.5 分三轮才发现的问题，本版在首轮脚本里就直接验掉）

### 关于那条新增的 `test_exec`

`configure:7190` 的 `zlib_gzip` 运行期探测未造成任何问题，构建全程无相关告警。

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

`conan create . -pr ohos-native` **rc=0，337s**，包体积 25M。
test_package 8 条断言全绿；另按**真实消费路径**（`usr_local` deployer 部署整个依赖图后从部署前缀跑 CLI）复验：

- **外部编码器**：libopenh264 / libvpx / libopus / libmp3lame 四个全部注册
- **协议**：https、tls 均在（openssl 接线成功）
- **滤镜**：drawtext 在（freetype + harfbuzz + fontconfig 接线成功）
- **封装**：dash 在（libxml2 接线成功）
- **真实转码 ①**：lavfi → **libopenh264 + libmp3lame** → mp4（42041 字节），
  `ffprobe` 反查 `codec_name=h264` / `mp3`、320x240
- **真实转码 ②**：lavfi → **libvpx-vp9 + libopus** → webm（15357 字节），
  反查 `codec_name=vp9` / `opus`
- **真实滤镜**：`drawtext` 用系统字体 `/system/fonts/DejaVuMathTeXGyre.ttf` 烧字出图（5797 字节）
- **签名**：7 个 `.so` + `bin/ffmpeg` + `bin/ffprobe` 共 9 个 ELF 均含 `.codesign` 段

### 仍缺的能力

- **subtitles / ass 滤镜**：需 `libass`，制品仓暂无
- **硬件加速**：鸿蒙 PC 无 VAAPI/VDPAU/NVDEC，FFmpeg 亦无 OHOS hwaccel 后端，为纯软编软解
- **iconv**：属 autodetect，未启用，字幕字符集转换不可用
- **ffplay**：需 SDL2，设备无

## 状态

built —— 真机 `conan create` + test_package(8 断言) + 外部编解码器接线 + 真实转码/滤镜全绿。

> 尚未做 PyAV 消费验证（7.1.5 已用 PyAV 14.4.0 验过）。若要验本版，需用支持 FFmpeg 8 的
> PyAV（18.x 源码中已见 `FFmpeg 8.1` 的 API 注记），且设备上现编 C 扩展须把
> `PKG_CONFIG`/`CC`/`CXX`/`AR`/`RANLIB`/`LDSHARED` 全部绝对路径化 —— 详见 7.1.5 的 notes。
