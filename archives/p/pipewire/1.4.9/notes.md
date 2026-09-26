# pipewire 1.4.9 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-09-23
- 编译器: clang 15.0.4 (aarch64-linux-ohos)
- 状态: built

## 编译步骤

```bash
# 官方源码 tarball（GitLab 归档）
# https://gitlab.freedesktop.org/pipewire/pipewire/-/archive/1.4.9/pipewire-1.4.9.tar.gz

# meson 最小化配置（关闭所有外部可选依赖，保留核心库 + spa 插件 + 测试）
meson setup build -Dtests=enabled -Dspa-plugins=enabled \
  -Dexamples=disabled -Ddocs=disabled -Dman=disabled \
  -Dgstreamer=disabled -Dsystemd=disabled -Dlogind=disabled \
  -Dselinux=disabled -Dpipewire-alsa=disabled -Dpipewire-jack=disabled \
  -Dpipewire-v4l2=disabled -Dalsa=disabled -Dbluez5=disabled -Djack=disabled \
  -Dv4l2=disabled -Ddbus=disabled -Dsndfile=disabled -Dlibpulse=disabled \
  -Dffmpeg=disabled -Dvulkan=disabled -Dlibcamera=disabled -Dlibcanberra=disabled \
  -Dsdl2=disabled -Dlibusb=disabled -Dflatpak=disabled -Dgsettings=disabled \
  -Dreadline=disabled -Dsession-managers=[] -Dpw-cat=disabled -Dudev=disabled \
  -Devl=disabled -Dvideoconvert=disabled -Dvideotestsrc=disabled -Daudiotestsrc=disabled \
  -Dcontrol=disabled -Dtest=disabled -Davahi=disabled -Draop=disabled -Dlv2=disabled \
  -Dlibffado=disabled -Dsnap=disabled -Dx11=disabled -Dx11-xfixes=disabled \
  -Dinstalled_tests=disabled -Droc=disabled -Dopus=disabled -Dcompress-offload=disabled \
  -Debur128=disabled -Decho-cancel-webrtc=disabled -Davb=disabled \
  -Dgstreamer-device-provider=disabled
ninja
meson test
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `pthread_cancel` 未声明 | OHOS libc (musl 系) 不提供 POSIX 线程取消 API | meson `cc.has_function('pthread_cancel')` 特性检测；data-loop.c 在缺失时回退为 SIGUSR1 + `pthread_exit` 信号取消（对应 E513 guarded-signal-thread-exit 模式），并在 do_loop 线程内安装 handler |
| 2 | `pthread_setaffinity_np` 未声明 | OHOS libc 无该 API | 特性检测 + thread_setaffinity 回退为忽略（返回 0 并 warn） |
| 3 | `dgettext`/`dngettext`/`bindtextdomain`/`bind_textdomain_codeset` 未声明 | OHOS libc 无 gettext 实现（libintl.h 仅头文件宏，无库） | 特性检测 + pipewire.c i18n 函数回退为原样返回 msgid |
| 4 | `rindex` 未声明 (test-config.c) | OHOS libc 无 POSIX 遗留 rindex | 改用标准 `strrchr` |
| 5 | open_memstream fseek 覆盖写不生效（test-spa-json.c `[[],` vs `[[]]`） | musl 的 open_memstream 在 fclose 时不保证缓冲同步；fseek 覆盖写需要显式 fflush | validate_strict_json 的 done 标签处加 `fflush(f)`；json_data 测试 fclose 前显式 fflush |
| 6 | open_memstream 无 fflush 时 fclose 后 free 触发 SIGTRAP (double-free) | musl open_memstream fclose 后内部缓冲状态与 glibc 不同，未 flush 时释放外部指针导致 double-free | json_data 测试在 fclose 前显式 fflush(fres)，保证缓冲所有权正常交接 |
| 7 | memfd `fstat` 返回 EACCES（test-pw-utils mempool_issue4884） | OHOS memfd 不支持 fstat（返回 EACCES），pw_memblock_map 因 fstat 失败返回 NULL | mem.c 在 fstat 失败时回退使用已知 block size 做边界校验 |
| 8 | logger 文件输出立即读不到（test-support logger_truncate_long_lines 等） | musl 的 line buffering (setlinebuf) 仅对终端生效，普通文件流不自动 flush | logger.c 非 trace 路径 fputs 后显式 `fflush(impl->file)` |

## 源码修改

共 8 个文件（相对官方 tag 1.4.9）：
1. `meson.build` — check_functions 增加 pthread_cancel / pthread_setaffinity_np / dgettext / dngettext / bindtextdomain / bind_textdomain_codeset 特性检测
2. `src/pipewire/data-loop.c` — pthread_cancel 缺失时 SIGUSR1 信号取消回退
3. `src/pipewire/thread.c` — pthread_setaffinity_np 缺失守卫
4. `src/pipewire/pipewire.c` — gettext 系列缺失守卫
5. `src/pipewire/mem.c` — memfd fstat 失败回退 block size
6. `test/test-config.c` — rindex → strrchr
7. `test/test-spa-json.c` — open_memstream 显式 fflush（done 标签 + fclose 前）
8. `spa/plugins/support/logger.c` — fputs 后显式 fflush

## 依赖版本

无外部 conan 依赖（核心库只依赖 libc/dl/pthread/m；可选外部依赖全部禁用）。

## 验证结果

```bash
meson test  # 48/48 全部通过 (Ok: 48, Fail: 0)
```

## 注意事项

- OHOS libc 为 musl 系，与 glibc 的 open_memstream / setlinebuf / fstat(memfd) 行为不同，已在测试与 logger 中显式 flush 适配
- 特性检测优先于平台宏（不用 `__OHOS__`），保证可移植性
- 会话管理器 (session-managers) 默认 wireplumber 依赖外部，配置时显式禁用 `-Dsession-managers=[]`
---

**编译结束**: 2026-09-23 05:20
**最终状态**: built
