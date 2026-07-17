# unpaper 7.0.0 适配笔记

## 基本信息
- 软件：unpaper — 扫描纸张后期处理工具（去歪斜 / 裁剪边距 / 黑白化 / 去噪 / 方向校正）
- 版本：7.0.0
- 上游：https://github.com/unpaper/unpaper
- 许可证：GPL-2.0-only
- 适配日期：2026-07-14
- 产物类型：命令行工具（单一 `unpaper` 可执行文件）

## 上游构建系统

unpaper 上游是 **Meson** 项目（`meson.build`），核心要素：

- 5 个 C 源：`file.c imageprocess.c parse.c tools.c unpaper.c`，`c_std=c11`，全局加 `-D_POSIX_C_SOURCE=200809L`，编译器支持时加 `-Werror=int-conversion`。
- 依赖 `libavformat / libavcodec / libavutil`（FFmpeg），以及可选 `libm`。
- `version.h` 由 `version.h.in`（`#define VERSION_STR "@version@"`）经 `configure_file` 替换生成。
- **强依赖 `sphinx-build >= 3.4`** 生成 man 手册（`find_program(..., required: true)`，缺失则 configure 失败）。
- 测试为 `tests/unpaper_tests.py`，**强依赖 `pytest` + `PIL`** 做金标图像比对。

OHOS worker 上 sphinx-build、pytest、PIL 均不可用，故 **Meson 被整体绕过**：配方直接复刻 meson.build 的编译动作——生成 `version.h`，以相同源集合与相同标志编译 5 个 C 源，再静态链接为 `unpaper`。这样既不引入 Python 文档/测试工具链，又保证编译结果与上游一致。

## 关键决策：内联构建 FFmpeg

unpaper 通过 FFmpeg 的 `libavformat/libavcodec/libavutil` 读写 PBM/PPM/PGM/PNG 图像。OHOS 平台：

- 无 FFmpeg 的系统库；
- 仓库内 `archives/f/ffmpeg`（2.8.9 / 4.4.6 / 7.1.4 / 8.1.1）**均为失败归档**，无可用 conanfile.py，制品仓无可引用的 ffmpeg 包；
- `archives/f/ffprobe/8.1.2` 虽构建了 av 库，但其 configure 用了 `--disable-encoders --disable-muxers`，**不提供 unpaper 写出图像所需的 ppm/pgm/pbm/png encoder 与 image2 muxer**，无法满足 unpaper 的读写往返。

因此配方从 **官方 FFmpeg 8.1.2 tarball**（与 ffprobe 同源同 sha256）内联构建一套**最小静态 av 库**，只启用 unpaper 实际用到的图像编解码：

```
--disable-everything
--enable-decoder=ppm,pgm,pbm,png,rawvideo
--enable-encoder=ppm,pgm,pbm,png,rawvideo
--enable-demuxer=image2,image2pipe
--enable-muxer=image2,image2pipe
--enable-protocol=file
--enable-parser=png
--enable-zlib                       # PNG 编解码走 zlib（取自 conan zlib/1.3.1）
--disable-doc --disable-programs --disable-shared --enable-static
--disable-avdevice --disable-avfilter --disable-swscale
--disable-vulkan                    # 见下「Vulkan 关闭」
```

### Vulkan 关闭（CI #2224 修复）
FFmpeg configure 的 `--disable-everything` **不**阻止 hwaccel/外部库的 autodetect。真机 worker 的 OHOS SDK（`ohos-sdk_26.0.0.18`）sysroot 里有 `vulkan/vulkan.h` 但缺 `vulkan_beta.h`，于是 configure 把 vulkan 判为可用并编译 `libavcodec/vulkan.o`/`vulkan_video.o`，在 `vulkan.h:96 #include "vulkan_beta.h"` 处 `fatal error: 'vulkan_beta.h' file not found`。显式 `--disable-vulkan`（与 ffprobe 一致）即可跳过——unpaper 的 ppm/pgm/pbm/png 编解码纯软件，从不走 vulkan hwaccel。

> 本机构建容器 `hmbs-builder` 无 OHOS SDK 的 vulkan 头，故 vulkan 从未被 autodetect 选中、本地不复现该失败；这是典型的"容器通过、真机 worker 暴露"差异。

编译/链接标志通过 `pkg-config --static --cflags/--libs libavformat libavcodec libavutil` 获取，保证静态依赖顺序正确（avformat→avcodec→avutil，附带 `-lm -lz -pthread` 及 swresample）。最终 `unpaper` 为**全静态 ELF**（`file` 报告 `static`，无 `DT_NEEDED`）。

## 鸿蒙适配要点

### 1. FFmpeg configure harmonyos 补丁（0001-ffmpeg-configure-harmonyos.patch）
FFmpeg configure 经 `uname -s` 得到 `HarmonyOS`，lowercase 成 `harmonyos` 后不被识别（`Unknown OS`）。补丁在 configure 的 `case $target_os` 增加 `harmonyos)` 分支（映射为类 Linux 行为：`section_data_rel_ro`、aarch64 下 `linux_perf`、`-D_GNU_SOURCE`），并在两处架构/硬解判断里把 `harmonyos` 与 `linux` 并列。**该补丁与 ffprobe 8.1.2 的 `0001-configure.patch` 逐字节相同**，已在 ffprobe 验证可用。

### 2. coreutils PATH 问题（本次新发现）
FFmpeg configure 直接调用 `tr / uname / grep / mktemp`。OHOS rootfs 缺 `tr`，而 GNU coreutils（tr/grep 等）装在默认 PATH 之外的目录（本机构建容器为 `/root/usr/local/bin`，且不属 conanbuild 环境的 PATH）。表现为 configure 反复打印 `tr: inaccessible or not found` 与 `grep: Invalid argument`，最终 `Unknown OS ''`。

修法：配方 `build()` 开头用 `_extend_path_for_coreutils()` 探测这些目录并**前置**到 `PATH`（优先用 GNU 版 grep）。当工具已在 PATH（真实 OHOS worker）时为空操作，不影响 worker。此点对未来任何“配方内构建 FFmpeg/类似 autotools”的库都适用。

### 3. ELF 签名
HarmonyOS 执行 ELF 需签名。`_sign_elf()` 用 `/data/service/hnp/bin/binary-sign-tool` + `llvm-objcopy`：先移除旧 `.codesign` 段，再 self-sign 写回。签名工具**仅 CI/release worker 具备**，本地构建容器缺失——此时探测到工具缺失则**跳过并告警**（容器不强制签名，未签名 ELF 仍可运行以完成 test_package）；worker 上工具齐备，签名失败即 `raise`（未签名二进制在 test_package 无法运行）。

### 4. image2 单图写出警告（非阻塞）
FFmpeg 8.x 的 image2 muxer 写单张图时会打印 `does not contain an image sequence pattern ... use -update` 警告，但**实际写出了有效图像**。test_package 以“输出文件存在且非空”为断言，不受警告影响。

## 编译器获取（R33）
不裸用 `${CC}`。FFmpeg configure 与 unpaper 编译均通过 `--cc=` / 直接调用，编译器路径取自 profile 的 `tools.build:compiler_executables`（`_cc()` 读 `self.conf`），符合 R33。

## test_package（L1 消费者测试，R34）
test_package 为 application 类型，调用被测二进制而非链接库 API：
1. `unpaper --version` → 打印 `7.0.0`，验证参数解析与 av 库初始化；
2. 构造一张 8×8 PPM（P6），`unpaper --layout none in.ppm out.ppm` 做一次真实图像处理往返，验证 libavformat/libavcodec 读写链路；断言 `out.ppm` 存在且非空。

## 上游测试
上游 `tests/unpaper_tests.py` 为 pytest 金标图像比对套件，依赖 pytest + PIL + sphinx-build，OHOS worker 均无，故未在 build() 运行（与绕过 Meson 的原因一致）。test_package 的 PPM 往返覆盖了核心图像 I/O 路径。

## 验证结果（本机构建容器 `hmbs-builder`）

- conan create（`-pr:h/-pr:b=ci/conan/profiles/ohos-aarch64`）rc=0 ✅
- FFmpeg configure + make（最小图像编解码集）成功 ✅
- 5 个 C 源编译 + 静态链接成功 ✅
- test_package：`unpaper --version` → `7.0.0`；PPM 往返写出有效 out.ppm ✅
- 产物：`bin/unpaper`，`ELF 64-bit LSB arm64, static`（无动态依赖）
- av 库版本（FFmpeg 8.1.2）：libavutil 60.26.102 / libavcodec 62.28.102 / libavformat 62.12.102 / libswresample 6.3.102

## 依赖
- `zlib/1.3.1`（制品仓已发布，PNG 编解码用，已验证可下载）。
- FFmpeg 8.1.2 源码（配方内联静态构建，不作 conan 依赖）。

---
**最终状态**: built
