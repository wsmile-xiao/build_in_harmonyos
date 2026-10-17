# cursynth 1.5 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-15
- 编译器: clang/clang++
- 状态: built

## 编译步骤

```bash
# W0: 依赖检查（ncurses/6.6 二进制已发布，conan download 实测）
conan download ncurses/6.6 -r=ohpcd --only-recipe

# 依赖注入（AutotoolsDeps 提供 CPPFLAGS/LDFLAGS/LIBS: -lformw -lmenuw -lpanelw -lncursesw）
# configure（配方 generate() 里由 AutotoolsToolchain 生成同样参数）
./configure --build=aarch64-unknown-linux-ohos --host=aarch64-unknown-linux-ohos \
            --with-oss --disable-nls --prefix=<prefix>
make -j1 MAKEINFO=true
make check MAKEINFO=true     # 上游无注册测试，实际执行 0 项
make install DESTDIR=<test-prefix> MAKEINFO=true
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `config.sub: machine 'aarch64-unknown-linux' not recognized` | 2014 年的 config.sub 不认识 `linux-ohos` 三元组（E007） | 顶层 + rtaudio + rtmidi 三处 config.sub 增加 `linux-ohos*`（1 处 KERNEL-OS 识别 + 1 处 OS 有效列表） |
| 2 | `config.status: can't create ./confXXXXXX/subs1.awk: Permission denied` | HMDFS 上 `(umask 077 && mktemp -d)` 生成的目录为 `drwx--S---`，构建用户不可写（E114） | 4 处 configure（顶层/mopo/rtaudio/rtmidi）移除 `umask 077` 包裹，保留真实临时目录创建 |
| 3 | `RtAudio.cpp: 'soundcard.h' file not found` | 捆绑的 RtAudio 用引号形式包含 OSS 头；OHOS sysroot 提供的是 `<sys/soundcard.h>` | 改为标准写法 `#include <sys/soundcard.h>` |
| 4 | `RtAudio.cpp: 'SNDCTL_SYSINFO'/'oss_audioinfo'/'PCM_CAP_*' undeclared`（20 处） | RtAudio 的 OSS 后端按 OSS4 API 编写；OHOS 只有经典内核 OSS 头（linux/soundcard.h） | 用 `#ifdef SNDCTL_SYSINFO` 区分，保留 OSS4 原路径，新增经典 OSS 回退（/dev/dsp 探测 + DSP_CAP_*/GETCAPS/GETFMTS/SPEED），并把 `SNDCTL_DSP_HALT`→`DSP_RESET`、24/32bit/float 格式标记为不可用 |
| 5 | `RtAudio.cpp: 'pthread_testcancel' undeclared` | OHOS musl 未提供 pthread 取消点 | `#ifdef __OHOS__` 下定义 no-op（R8 libc 探针例外，见 PR 说明；zam-plugins 已合入配方同款） |
| 6 | `RtAudio.cpp: call to 'abs' is ambiguous` | C++17/libc++ 下 `abs(unsigned)` 重载歧义（上游 `srate - sampleRate` 无符号相减） | 显式 `(int)` 转换 |
| 7 | `RtMidi configure: ALSA sequencer support requires the asound library!` | rtmidi 的 Linux 默认分支硬依赖 ALSA；OHOS 无 libasound | configure 默认分支改为「探测到 libasound 才启用 ALSA，否则生成 RtMidi 无 API 回退（stub）」，显式 `--with-alsa` 的硬错误保留 |
| 8 | `config.h: #define malloc rpl_malloc` 导致 libc++ 头文件编译失败 | 交叉语义下 `AC_FUNC_MALLOC` 的运行测试被跳过（E007 根因描述） | 配方用 `--build=--host=aarch64-unknown-linux-ohos`（native 语义，configure 运行测试真实执行），不再产生 rpl_malloc |
| 9 | `cursynth_gui.cpp: 'gettext' undeclared` | OHOS 的 `<libintl.h>` 是空桩（无原型）、无 libintl；源码直调 gettext/bindtextdomain/textdomain | 源码加 NLS 回退宏（`#if !defined(ENABLE_NLS)` 下 gettext→原字符串、textdomain 系 no-op），`--disable-nls` 构建 |
| 10 | `make install/check: makeinfo missing`（Error 127） | doc/ 的 texinfo 文档需 makeinfo，OHOS/CI 均无 texinfo | `make/make install/check` 传 `MAKEINFO=true`（adplug/autoconf 等已合入配方同款） |
| 11 | `make: jobserver mkfifo ... Operation not permitted` | HMDFS 不支持 make jobserver fifo（E074） | `make -j1`（配方内置） |
| 12 | `rtmidi: aclocal-1.13: inaccessible` | 改过 rtmidi/configure.ac 会触发 autotools 再生链（1.13 版工具不存在） | 只补丁生成的 `configure`（不触碰 configure.ac），归档先例 a52dec 0002 |

## 源码修改

补丁由 `refresh-patch --auto` 驱动的 per-file-difflib 管线生成（一源文件一补丁，见 conandata.yml；manifest.yaml 的 patch_generation 段记录 orig/work 哈希）：

- `config.sub`（顶层 + rtaudio/config + rtmidi/config）：接受 `linux-ohos` 三元组
- `configure`（顶层 + mopo + rtaudio + rtmidi）：移除 `umask 077` 包裹（E114）
- `rtaudio/RtAudio.cpp`：OSS 经典头兼容 + 无 MIDI API 回退 + `__OHOS__` pthread_testcancel + abs 修复；`#include "soundcard.h"` → `<sys/soundcard.h>`
- `rtmidi/configure`：ALSA 缺失时不硬失败（api 赋值移入探测成功分支）
- `src/cursynth_gui.cpp`：gettext/bindtextdomain/textdomain 的 NLS 回退

## 依赖版本

- ncurses/6.6（静态，宽字符版；提供 libncursesw/libformw/libmenuw/libpanelw）

## 验证结果

```bash
# W3 conan create（设备）
conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64   # → 全绿，test_package 通过

# 运行验证（打包二进制）
cursynth -V            # → "Cursynth 1.5"，rc=0
cursynth               # → "No audio devices found."，rc=0（OHOS 无 /dev/dsp，OSS 后端探测路径）

# 上游测试
make check MAKEINFO=true   # 上游无注册测试（N_static=0），实际执行 0 项
```

## 注意事项

- 音频输出为平台限制：OHOS 无 ALSA/PulseAudio/JACK/OSS 设备节点，仅能编译 OSS 后端并优雅报告无设备；
  真正的 OHOS 音频输出需要接入 OHOS AudioRenderer（超出本任务范围，未做）
- MIDI 输入同样不可用：RtMidi 以无 API 形编译（stub，`__RTMIDI_DUMMY__`），端口数为 0
- NLS 关闭：界面为英文原文（OHOS 无 libintl）
- 上游无自动化测试：全树无 TESTS/check_PROGRAMS/add_test 注册；rtaudio/rtmidi 的 tests/ 仅为手工示例且未纳入 SUBDIRS
---

**编译结束**: 2026-09-16 00:23
**最终状态**: built
