# puredata 0.54.1 适配笔记

## 编译环境
- 构建系统: autotools（configure.ac + automake/libtool，v2.72 autoreconf 再生成）
- 编译日期: 2026-09-18
- 编译器: clang 15.0.4 (OHOS SDK native llvm, aarch64-linux-ohos, musl)
- 状态: built

## 编译步骤

```bash
# 0) 前置（前两轮遗留的 HMDFS 怪癖规避）
export TMPDIR=<workspace>/.tmp-puredata/tmp   # configure/config.status 临时目录

# 1) 上游 tarball 未带生成的 configure（只有 configure.ac），需 autoreconf
autoreconf -fi

# 2) configure（R1 参数最少化；--without-alsa 因 OHOS 无 alsa-lib 头文件可用）
./configure --prefix=$HOME/usr/local/pd-test --without-alsa

# 3) config.status 需临时目录改写（见问题 #1），随后
make -j2
make check          # rc=0，无注册测试目标（见 R51 清点）
make install DESTDIR=<workspace>/.tmp-puredata/staging
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.status 崩溃 `can't create ./confXXXXXX/subs1.awk: Permission denied`（前两轮的崩溃点） | HMDFS 上 config.status 内嵌的 `mktemp -d "./confXXXXXX"` 创建的目录，随后同进程 `cat > $dir/subs1.awk` 写入被拒（mkdir/sed/heredoc 均可写，仅 shell 重定向创建+写入组合被拒，疑似 HMDFS 对 0700 目录新文件创建的怪癖） | 探针法定位：给 config.status 的 mktemp 打一行补丁 `mktemp -d "${TMPDIR:-.}/confXXXXXX"`，TMPDIR 指向普通 HMDFS 目录后 rc=0。awk 本身无问题（trace 证实 awk 只被调用读 subs.awk，不写临时目录） |
| 2 | `fatal error: 'alsa/asoundlib.h' file not found`（编 portaudio 的 pa_linux_alsa.c） | 上游 Makefile.am 在 `if LINUX` 下无条件把 ALSA hostapi 源文件编进 libportaudio.a，不看 --without-alsa | portaudio/Makefile.am 给该源文件加 `if ALSA` 守卫（仅当真正探测到 alsa 时才编译） |
| 3 | 链接 pd 失败 `undefined symbol: pthread_cancel` | OHOS (musl 系) libc 不提供 pthread_cancel，但 sysroot pthread.h 却定义了 `PTHREAD_CANCELED` 宏，portaudio 的 `#ifdef PTHREAD_CANCELED` 探测误判 | pa_unix_util.c 探测宏改为 `#if defined(PTHREAD_CANCELED) && !defined(__OHOS__)`（4 处），走上游自带的 Android 无 cancel 回退路径（pthread_join-only） |
| 4 | configure 探测 error_at_line=no / qsort_r=no / machine/endian.h=no | OHOS musl 无这些 glibc 扩展 | 非致命，configure 自带回退（STUPID_SORT=1、endian.h 主路径），无需处理 |

## 源码修改

探索阶段直接改源码（R5），未生成 patches/ 文件。三处：

1. `config.status`（生成文件内补丁，若走 conan create 需在 conanfile 中 post-configure 后重打）：mktemp 路径改用 `${TMPDIR:-.}`
2. `portaudio/Makefile.am`：ALSA hostapi 源文件包 `if ALSA ... endif`（原为 `if LINUX` 无条件）
3. `portaudio/portaudio/src/os/unix/pa_unix_util.c`：4 处 `#ifdef PTHREAD_CANCELED` → `#if defined(PTHREAD_CANCELED) && !defined(__OHOS__)`

## 依赖版本

全部使用上游 tarball 内嵌（bundled）源码：portaudio（included）、portmidi（unused in linux path）、libpd 源码树。无外部 conan 依赖需注入（tcl/tk 仅 GUI 运行时脚本依赖，未参与 C 编译；W0 已确认 tcl/8.6.16、tk/9.0.3.1、portaudio/19.7.0、fftw/3.3.10、alsa-lib/1.2.16 均已发布，见 w0-preflight.log）。

## 验证结果

```bash
$ staging/.../bin/pd -version
Pd-0.54.1 ("") compiled 11:32:29 Sep 18 2026

$ make check → rc=0（无实际测试注册，见下）
```

产物（staging/usr/local/pd-test/）：
- bin/pd（ELF 64-bit arm64, /lib/ld-musl-aarch64.so.1）、bin/pd-gui、bin/pdsend、bin/pdreceive、bin/pd-watchdog
- lib/pd/{bin,doc,extra,po,startup,tcl}，extra/ 各 externals 编出 .pd_linux（stdout、bonk~、fiddle~ 等约 20 个）

## 交付物

（本任务为探索编译验证，未走 conan create 打包，暂无 .conan 产物）

## 注意事项

- OHOS 无 alsa-lib 开发头可用（W0 显示 alsa-lib/1.2.16 已发布但本次未注入；--without-alsa 下 OSS+PortAudio 路径即可完成编译链接）。如需音频后端注入 alsa-lib/fftw conan 包，用 CPPFLAGS/LDFLAGS 指向私有 prefix（R49）再撤 --without-alsa。
- config.status 的 TMPDIR 补丁在任何 HMDFS 环境重跑 configure 都需要；建议正式配方中 conanfile 用 build_folder 子目录做 TMPDIR 并在 configure 后 sed 修 config.status，或整体在非 HMDFS 文件系统构建。
