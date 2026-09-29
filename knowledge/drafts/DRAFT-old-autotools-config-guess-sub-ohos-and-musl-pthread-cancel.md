# DRAFT-old-autotools-config-guess-sub-ohos-and-musl-pthread-cancel（草稿）

- **软件**：SDL 1.2.15（https://github.com/libsdl-org/SDL-1.2，2012 年最终版）
- **构建系统**：autotools（自带 2009 年代 config.guess/config.sub）
- **平台**：HarmonyOS PC / aarch64，`clang 15.0.4`
- **状态**：DRAFT

## 现象

1. configure 无法识别平台：

```
Invalid configuration `aarch64-unknown-linux-ohos': machine `aarch64-unknown-linux' not recognized
```

2. configure 生成的 config.status 写不进临时目录：

```
rm: ./confXxj8IP/stdin: Permission denied
./config.status[2073]: can't create ./confXxj8IP/out: Permission denied
```

3. 链接期线程符号缺失：

```
ld.lld: error: undefined symbol: pthread_setcanceltype
>>> referenced by SDL_systhread.c:94
ld.lld: error: undefined symbol: pthread_cancel
>>> referenced by SDL_systhread.c:113
```

## 根因

1. **老版辅助脚本不认识 HarmonyOS 与 aarch64**：SDL 1.2.15 自带
   `config.guess`（timestamp `2009-09-18`）与 `config.sub`（`2009-10-07`）。
   设备 `uname` 输出 `HarmonyOS aarch64`，而 config.guess 的 case 分派无对应
   分支，一直落到脚本尾部的 "unable to guess" 诊断并 `exit 1`；config.sub
   既不认识 `aarch64` 机器名，也不认识 `linux-ohos` 系统名。

   ⚠️ **老版与新版的插入格式不同**：老版各分支自行 `echo` + `exit`（没有新版
   的统一 `GUESS=` 变量），所以照搬"新版 patch 模式"会不生效。

2. **hmdfs 上的 umask 077**：`config.status` 用
   `tmp=`(umask 077 && mktemp -d "./confXXXXXX")`` 建临时目录；在 setgid hmdfs
   卷上得到 `drwx--S---`，磁盘属主与构建进程 uid 不一致，连创建者都写不进。
   `umask 022` → `0755` 即可（与 inn2 同款结论）。

3. **musl 不实现 POSIX 线程取消**：SDL 的 `PTHREAD_CANCEL_ASYNCHRONOUS` 分支
   调用 `pthread_setcanceltype` / `pthread_cancel`，musl 未提供该族函数。

4. 沙箱内 configure 的 conftest 链接不可靠，需预置 `ac_cv_prog_cc_works`。

## 适配做法（4 个补丁）

| 补丁 | 内容 |
|------|------|
| `0001-config-guess-ohos.patch` | 在 case 分派**首部**插入 `*:HarmonyOS:*:*) echo ${UNAME_MACHINE}-unknown-linux-ohos; exit ;;` |
| `0002-config-sub-ohos.patch` | 机器列表加 `aarch64`；`maybe_os` 与 os 合法列表加 `linux-ohos*`；加 `-linux-ohos*) os=-linux-ohos ;;` 特判（否则被 `-linux*)` 改写为 `linux-gnu`） |
| `0003-configure-umask-022.patch` | 两处 `umask 077` → `umask 022` |
| `0004-systhread-ohos-no-pthread-cancel.patch` | `pthread_setcanceltype` 调用包 `#ifndef __OHOS__`；`SDL_SYS_KillThread` 条件改 `#if defined(PTHREAD_CANCEL_ASYNCHRONOUS) && !defined(__OHOS__)` 走 `pthread_kill` 回退 |

configure 参数另加 `ac_cv_prog_cc_works=yes` + `ac_cv_prog_cc_cross=yes`；
**不要**传显式 `--build=<gnu triplet>`（会报 `C compiler cannot create executables`）。

补丁自证（不依赖 configure）：

```sh
sh build-scripts/config.guess                              # aarch64-unknown-linux-ohos
sh build-scripts/config.sub aarch64-unknown-linux-ohos     # 同样回显
```

## 验证

`conan create archives/s/sdl/1.2.15`（ohos-aarch64）通过，test_package 8 项断言
全过（`SDL linked version: 1.2.15` / `SDL video driver: dummy` /
`SDL_GetTicks advanced by 20 ms` / `SDL-CONSUMER-OK`），覆盖
`SDL_Init(VIDEO|TIMER)` → `SetVideoMode` → `FillRect`/`BlitSurface` → `Flip` →
计时子系统的完整调用链。

## 相关

- `archives/s/sdl/1.2.15/patches/000{1,2,3,4}-*.patch`
- `archives/s/sdl2/2.30.0/patches/0001-src-thread-pthread-SDL_systhread.c.patch`（musl 守卫同源先例）
- `archives/i/inn2/2.7.4/patches/0001-configure-umask-022.patch`（umask 同款）
- `knowledge/drafts/DRAFT-inn-mktemp-umask022-hmdfs.kv`
