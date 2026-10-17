# libpd

libpd 把 Pure Data（Pd）作为可嵌入的音频合成库提供给宿主程序：宿主通过
`z_libpd.h` 的 C API 打开 `.pd` patch、收发消息并逐块处理音频，无需启动 Pd 图形界面。

## 功能概述

- 以库的形式加载并运行 Pure Data patch（`libpd_openfile` / `libpd_closefile`）
- 音频块处理：`libpd_process_float` / `libpd_process_short` / `libpd_process_raw`
- 消息收发：`libpd_bang` / `libpd_float` / `libpd_symbol` / `libpd_message` / `libpd_list`
- 数组读写：`libpd_read_array` / `libpd_write_array` / `libpd_arraysize`
- MIDI 与打印回调：`libpd_set_printhook` / `libpd_set_noteonhook` 等
- 随包编译 Pure Data 内置与 extra 外部对象（bob~、bonk~、fiddle~、sigmund~、pd~ 等）

## OHOS 适配

- 上游构建系统是手写 Makefile（无 configure），直接用 `make libpd`（动态）或
  `make libs/libpd.a`（静态），`make install` 安装头文件与库。
- Makefile 的平台判定用 `uname -s` 分支；OHOS 上 `uname -s` 是 `HarmonyOS`，
  因此 Linux 分支的 `-DHAVE_ALLOCA_H` / `-DHAVE_LIBDL` 与 `-ldl` 不会自动加入。
  配方经 `ADDITIONAL_CFLAGS` / `ADDITIONAL_LDFLAGS` 显式补齐（`alloca.h`、`dlfcn.h`
  在 OHOS sysroot 中均存在；`libdl` 在 OHOS 上是空壳，`dlopen` 符号在 libc 中）。
- libpd 的 `pure-data` 子模块不在 GitHub 源码包内：`conandata.yml` 的 `submodules`
  段声明了 0.16.1 所固定的 pure-data 快照（commit `f009fd8d`），由 `source()` 注入。
- 交付物：`include/libpd/{z_libpd.h,m_pd.h,m_imp.h,g_canvas.h,*.hpp}`、
  `include/libpd/util/*.h` 与 `lib/libpd.so`（默认）或 `lib/libpd.a`（`-o shared=False`）。

## 依赖关系

- 编译依赖：无（仅 OHOS sysroot 的 libc/libm/pthread）
- 运行依赖：无

## 参考资料

- 上游仓库：https://github.com/libpd/libpd
- 版本说明：https://github.com/libpd/libpd/blob/master/CHANGES.txt
