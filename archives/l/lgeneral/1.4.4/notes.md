# lgeneral 1.4.4 适配笔记

## 编译环境
- 构建系统: autotools（configure + make；gettext 0.10.35 内嵌 intl）
- 编译日期: 2026-09-16
- 编译器: clang 15 (OHOS aarch64 native)
- 平台: HarmonyOS PC (arm64, OHOS 6.0, musl libc)
- 状态: published

## 软件概述

LGeneral 是 Panzer General 风格的回合制策略游戏（SDL 1.2 图形），构建产物为
4 个可执行文件：

| 文件 | 说明 | 依赖 |
|------|------|------|
| `usr/bin/lgeneral` | 游戏主程序 | SDL1.2(compat→SDL2) + SDL_mixer + 内嵌 intl |
| `usr/bin/lgc-pg` | Panzer General 数据转换器 | 同上 |
| `usr/bin/lged` | 关卡编辑器（终端工具） | 纯 libc |
| `usr/bin/ltrextract` | LTX 资源提取器（tools/） | 纯 libc |

游戏运行需 PG 数据包（`lgeneral --pg-data=<path>` 转换），无数据时干净报错退出。

## 上游测试申报（R51）

| 项 | 数量 | 说明 |
|----|------|------|
| tests/ 目录 | 0 | 上游无 tests/ 目录 |
| ctest/pytest 注册 | 0 | 非 cmake/meson 工程 |
| autotools check_PROGRAMS | 1 | `src/check_PROGRAMS = testfile`（file.c/list.c/misc.c 编译的目录枚举器） |
| make check 实测 | **1/1 通过** | 补丁 0007 修复链接后 `make check -j1` rc=0；testfile 对真实目录列出正确条目、对不存在路径报错 rc=1 |

上游 `make check` 只构建并运行 check_PROGRAMS（automake 无 TESTS 注册，
check 脚本即 testfile 本身的目录枚举输出）。实测：

```
$ src/testfile ../util        # 列出 util/ 全部文件，rc=0
$ src/testfile ..             # 列出顶层目录，rc=0
$ src/testfile /nonexistent   # "Error reading directory /nonexistent", rc=1
```

## 编译步骤

```bash
# 依赖（W0 核验已发布）：sdl12-compat/1.2.68, sdl2_mixer/2.8.1, sdl2/2.30.10
# 1. 打 7 个补丁 + 替换 config.guess/sub（2023 savannah 版，识别 aarch64-ohos）
# 2. 生成 sdl-config 包装脚本（上游 AM_PATH_SDL 探测需要；见 conanfile.py generate()）
# 3. configure + make + make check + make install

CC=clang ./configure --prefix=$PREFIX --disable-sdltest LDFLAGS="-L<sdl-wrap-dir>"
make -j1                 # -j1: jobserver FIFO 在 HMDFS 上失败
make check -j1           # 上游 testfile 测试
make install
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `config.guess` 输出 `aarch64-unknown-linux-gnu` 而非 ohos | 上游 2011 年脚本无 OHOS 支持 | patches/config.guess+sub 换 2023 savannah 版（先例：E007） |
| 2 | configure 找不到编译器 | autoconf 2.69 默认只探测 gcc/cc/cl | `CC=clang` 显式传入 |
| 3 | configure 卡死在临时目录创建 | `(umask 077 && mktemp -d ...)` 子壳在 HMDFS 失败 | 补丁 0005 去掉 umask 子壳 |
| 4 | `intl/libgettext.h` 用未探测的 `HAVE_LOCALE_H`，`LC_MESSAGES` 编译失败 | 上游 configure 是 autoconf 2.69 再生版，丢失 gettext 0.10.35 的 m4 探测 | 补丁 0002 无条件含 `<locale.h>`（0001 同理修 dgettext.c） |
| 5 | `util/localize.h` 含 `<libintl.h>` 后 gettext 调用隐式声明崩溃 | OHOS sysroot 的 libintl.h 是空壳 stub | 补丁 0003 改用内嵌 `intl/libgettext.h`（同名 include guard 不冲突） |
| 6 | `make` 报 `No rule to make target 'libintl.@l@a'` | gettext 0.10.35 的 `l = @l@` libtool 后缀变量在 autoconf 2.69 config.status 下不被替换 | 补丁 0004 硬编码空后缀 `l =`（非 libtool 静态归档本就不用后缀） |
| 7 | `make` 报 `No rule to make target 'intlh.inst'` | 上游 tarball 未随附 intl/intlh.inst.in 模板 | 补丁 0004 移除该目标（外置 gettext 用户才需要，本包静态链接 libintl.a） |
| 8 | `make -j8` 失败 `unhandled syntax error: (mkfifo ...)` | GNU make jobserver 在 HMDFS 创建 FIFO 失败 | `make -j1`（先例：abook 等） |
| 9 | 时间戳偏移触发 automake 再生失败 | OHOS SDK 无 aclocal/automake | 补丁 0006 将 ACLOCAL/AUTOCONF/AUTOHEADER/AUTOMAKE 置为 `true` |
| 10 | `make check` 的 testfile 链接失败：`undefined symbol: dcgettext__` | 上游 `testfile_LDADD` 缺 `$(INTLLIBS)`；glibc 上 libc 提供 dcgettext__ 掩盖此 bug，musl 显形 | 补丁 0007 补上 `$(INTLLIBS)`，testfile 由此可构建并运行 |
| 11 | `configure` 探测 `-lSDL_mixer` 失败（sdl12-compat 不带 mixer） | SDL1.2 的 mixer 实际由 sdl2_mixer 包提供 | recipe 注入 `LIBRARY_PATH` 指向 sdl2_mixer/lib（libSDL2_mixer.a 提供 -lSDL_mixer 符号） |
| 12 | 上游 AM_PATH_SDL 探测需要 `sdl-config` | sdl12-compat 只装 pkg-config 文件 | recipe generate() 生成 sdl-config 包装脚本（--cflags/--libs 拼合 SDL1.2 头 + SDL2 后端库） |

## 源码修改

7 个补丁（见 conandata.yml）+ config.guess/config.sub 替换。全部补丁无
`__OHOS__` 平台宏（OHOS 专项均以注释说明，通用修复保持上游语义）。

## 依赖版本

| 依赖 | 版本 | 角色 |
|------|------|------|
| sdl12-compat | 1.2.68 | SDL 1.2 API 兼容层（SDL2 后端），提供 libSDL-1.2.so.0 |
| sdl2 | 2.30.10 | sdl12-compat 的运行时后端（libSDL2-2.0.so.0） |
| sdl2_mixer | 2.8.1 | 音频（libSDL2_mixer.a 提供 SDL_mixer 符号） |

## 验证结果

```bash
# 干净树（verify5）+ 7 补丁全流程：
$ ./configure ... && make -j1        # rc=0
$ make check -j1                     # rc=0（testfile 构建链接成功）
$ make install                       # rc=0

$ usr/bin/lgeneral --version        # LGeneral 1.4.4, rc=0
$ usr/bin/lgeneral --help           # 用法清单（上游 "Syntax:" 格式）, rc=0
$ usr/bin/lgc-pg --version          # rc=0
$ usr/bin/lged --help               # 帮助文本（上游约定 rc=1），lged/ltrextract 同
$ usr/bin/ltrextract --help         # 帮助文本, 同上
$ SDL_AUDIODRIVER=dummy SDL_VIDEODRIVER=dummy usr/bin/lgeneral
                                      # 无 PG 数据包：干净报错退出（环境限制，非崩溃）

# ELF 检查（readelf）：
lgeneral:  ELF64 AArch64 PIE, INTERP=/lib/ld-musl-aarch64.so.1
           NEEDED: libSDL-1.2.so.0, libSDL2-2.0.so.0, libc.so
lgc-pg:    同上
lged/ltrextract: NEEDED: libc.so（纯工具）
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| usr/bin/lgeneral | 1145280 B | 游戏主程序 |
| usr/bin/lgc-pg | 219648 B | PG 数据转换器 |
| usr/bin/lged | ~100 KB | 关卡编辑器 |
| usr/bin/ltrextract | ~60 KB | LTX 提取器 |
| usr/bin/testfile | ~100 KB | 上游 check_PROGRAMS（目录枚举器），随包分发供消费者验证 |
| usr/share/lgeneral/ | 图形主题/战役等 | 游戏资源（INSTALLDIR 编译期内嵌） |
| usr/share/locale/*.mo | 多语言 | NLS 目录（内嵌 intl 实际生效） |

## 注意事项

- 运行时图形/音频依赖桌面环境；无头验证用 `SDL_VIDEODRIVER=dummy
  SDL_AUDIODRIVER=dummy`。
- `--version` 首次运行会在 `$HOME/.lgames/lgeneral.conf` 缺失时打印
  `file not found` 提示——这是上游路径初始化的正常行为，非错误。
- test_package 不依赖图形环境：覆盖 `--version`/`--help`/错误路径退出码
  与 testfile（上游测试程序）目录枚举。
