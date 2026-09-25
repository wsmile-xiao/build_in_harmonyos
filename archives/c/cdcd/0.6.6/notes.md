# cdcd 0.6.6 适配笔记

## 编译环境
- 构建系统: autotools（上游自带 autoconf-2.59/automake-1.8 生成的 configure + Makefile.in，不跑 autoreconf；AM_MAINTAINER_MODE 默认关闭，生成物不重建）
- 编译日期: 2026-09-23
- 编译器: clang 15.0.4 / clang++（profile `tools.build:compiler_executables` 注入）
- 状态: built（原生探索全绿，采信轮 conan-verify 回填 manifest `quality_gates`）
- 依赖: libcdaudio/0.99.12p2 + readline/8.3 + ncurses/6.6（全部 ohpcd 在架，真实 `--build=missing` 双 profile 组合 rc=0）

## 编译步骤

1. `conan create archives/c/cdcd/0.6.6 -pr:h=<ohos-aarch64> -pr:b=<ohos-aarch64> --build=missing`
2. `generate()` 注入：
   - `AutotoolsToolchain`：`--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu`
     （1996 config.guess 在本机 rc=1 猜不出；conan 因 build==host profile 不注入三元组；
     `linux-gnu` 走 configure 的 `case "$host_os" in *linux*` 分支定义 HAVE_CDAUDIO/DEFAULT_DEVICE，cdck 0.7.0 先例）
   - `--with-libcdaudio-prefix=<libcdaudio package_folder>`（承重，见问题表 #3）
   - `AutotoolsDeps`：CPPFLAGS/LDFLAGS/LIBS 注入三依赖的 -I/-L/-l
3. `build()`：`apply_conandata_patches`（5 补丁）→ `Autotools.configure()` → `make` → `make check`
   （上游 0 用例，真跑空目标作机器证据）→ 输出 `HMBS_UPSTREAM_TEST_RESULT no_tests`
4. `package()`：`Autotools.install()`（`--prefix=/` + conan 注入 `DESTDIR=<package_folder>`）
   → `bin/cdcd` + `man/man1/cdcd.1` + `info/cdcd.info`，另拷 `COPYING` → `licenses/`
   （install 面原生实测 rc=0：staging 恰为这三件，`install-info` 缺失被 configure 的 `else :` 分支守卫跳过）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `sh config.sub aarch64-unknown-linux-gnu` → `Invalid configuration … not recognized`；configure 首跑即死 | 1996 版 config.sub 的 CPU 清单无 aarch64 | 补丁 0001（裸名与带厂商两处清单）；已实测补后 rc=0 |
| 2 | config.status 建 `confstat` 临时目录后写 `subs.sed` EACCES | `umask 077` 落 HMDFS 为 `drwx--S---`（0700 组位不可写，E011/E206 族）；`umask 000` 落 `drwxrws--x` 可写（探针对照实测） | 补丁 0002（configure 两处 077→000） |
| 3 | `checking for tputs in -lcurses… no` → configure AC_MSG_ERROR；且 `libcdaudio-config` 找不到、`-I//include -L//lib` 假路径 | ① conan ncurses 只交付宽字符库名（libncursesw/formw/menuw/panelw），无 libcurses；② conanbuild PATH 不含 host 依赖 bindir，AC_PATH_PROG 找不到 config 脚本；③ 包内 config 脚本 `prefix=/` 烤死 | ① 补丁 0003+0004（configure 与 configure.ac 源头同步 `-lcurses`→`-lncursesw`）；②③ 一个 `--with-libcdaudio-prefix=<package_folder>` 同时解决（宏内直接设绝对 LIBCDAUDIO_CONFIG + 按 prefix 重推 -I/-L） |
| 4 | `cmd_cdcd.c:1269: error: use of undeclared identifier 'CPPFunction'` | readline ≥ 6 移除 `CPPFunction` typedef；本任务链 readline/8.3，目标类型是 `rl_completion_func_t *` | 补丁 0005：`RL_READLINE_VERSION >= 0x0600` 守卫切 `rl_completion_func_t`，老 readline 分支保留 |
| 5 | 未传 CC 时 configure 找 `aarch64-unknown-linux-gnu-gcc/cc` 失败 | 传了 `--host` 后 autoconf 走 cross 命名探测；探索 shell 未带 profile 的 compiler_executables | conan `AutotoolsToolchain` 自动注入 `CC=/data/service/hnp/bin/clang`（profile conf），配方无需手动；探索期显式 export CC 后过 |
| 6 | 缺省 `$HOME/.cdcdrc` 会挂死无头测试 | `cdcdrc_read()` 在 getopt **之前**执行，文件缺失即进 `cdcdrc_manual_configuration()` 交互向导（stdin 提问循环） | test.sh 预置 revision-3 rc 文件（逐字对齐 `cdcdrc_write` 输出格式）并用隔离 HOME，真实 HOME 永不触碰；畸形 rc 分支恰好成为第 4 条负路径用例 |

## 源码修改

| 补丁 | 文件 | 修改内容 |
|------|------|----------|
| 0001 | config.sub | CPU 清单两处加 `aarch64` / `aarch64-*` |
| 0002 | configure | `umask 077` → `umask 000`（confstat 临时目录，两处） |
| 0003 | configure | `-lcurses` → `-lncursesw`（AC_CHECK_LIB 探测，四处） |
| 0004 | configure.ac | `AC_CHECK_LIB(curses,` → `AC_CHECK_LIB(ncursesw,`（源真值同步） |
| 0005 | cmd_cdcd.c | `CPPFunction *` 按 `RL_READLINE_VERSION >= 0x0600` 守卫切 `rl_completion_func_t *` |

五个补丁已在干净 tarball 树按 conandata 顺序串行 dry-run 应用全过（`$TASK_DIR/patchwork/final-verify`）。

## 依赖版本

| 依赖 | 版本 | 角色 | 判据 |
|------|------|------|------|
| libcdaudio | 0.99.12p2 | 硬（AM_PATH_LIBCDAUDIO，AC_MSG_ERROR） | ohpcd 在架；组合安装 binary Download 落地 rc=0 |
| readline | 8.3 | 硬（AC_CHECK_LIB rl_completion_matches，AC_MSG_ERROR） | ohpcd 在架；binary 已装 |
| ncurses | 6.6 | 硬（tputs 探测 + readline 静态 termcap 符号） | ohpcd 在架；readline/8.3 requires ncurses/6.6（首跑 6.5 冲突即由此来） |
| glib | — | 可选（vasprintf/vsnprintf 任一在即不需） | 设备 vasprintf 探测可用 → 缺省禁用继续（W0 口径） |

## 验证结果

### 采信轮 conan-verify 门禁读数（overlay 入口实跑 2026-09-23T23:35:48）

- Verdict: **PASS**；实跑 G4/L2/L4/L5 = **4/4，跳过 = 0/4**（首轮无 overlay 入口
  已按 §二.17 取更严一侧弃用重启——application 包走上游版必静默跳过仍打 ✅）
- G0/G1/G2/G3：全 PASS（G0 命中知识图谱 E007「config.guess 无 HarmonyOS 分支」
  且配方已按其处置——本包显式 --build/--host 正是该修法的实例）
- L2 smoke：`cdcd --version` → `Welcome to cdcd 0.6.6.` ✓（1 个二进制过）
- L4：门禁判 PASS 但带 **1 warning**，独立 readelf -lW/-dW 复核逐项：
  - `GNU_STACK = RW` → NX **实为 enabled**；门禁 `NX disabled` 是已知解析误报
    （conan_verify.py:1167 自注「窗口 repr 以 NOTE 结尾会误报」）
  - `BIND_NOW` + `FLAGS_1 NOW` ✓、PIE ✓、`GNU_RELRO = full` ✓、
    `.note.ohos.ident` + `.codesign` 段在 ✓
  - `STACK_CANARY = not found`：上游 2003 代码未开 -fstack-protector，
    门禁只 warning 不阻断——如实留档，**不写成无警告**
- L5：基线已更新（`bin/cdcd` sha16=`7bf67c02350d6df4`，size 829888）

### 干净轮四步读数（证据轮 = 第三轮 rc=0）

```bash
OHC_FRAMEWORK_OVERLAY=1 OHC_E017_MIRROR=off \
  sh tools/conan_verify_round.sh cdcd 0.6.6 --repo "$TARGET_REPO" --task-dir "$TASK_DIR"
# rc=0；干净轮三标志：Calling build=1、Apply patch=5、HMBS_TEST_PACKAGE_RESULT×3
# 三份固定证据（§7.2）全 ✅：conan-create.log / conan-verify-report.md / w3-local-ci.log
# （w3 份由 finish 的 W3 产出，capture --restore 刷新索引后 --verify rc=0）
# evidence-index sha=23f864725ed6，copy_sha256 双一致
```

### 原生探索（写配方前，$TASK_DIR/explore-evidence.md 8 行读数）

```bash
configure rc=0（tputs in -lncursesw=yes、rl_completion_matches=yes、
              libcdaudio version>=0.99.0=yes【AC_TRY_RUN 真跑】、
              vasprintf=yes、strcasestr=yes、socket=no【非致命】）
make     rc=0 → ELF arm64 PIE，NEEDED 仅 libc.so（cdaudio/readline/history/ncursesw 全静态链入）
make check rc=0（上游 0 用例=automake 空目标；mkfifo 噪声按 device-facts §一.13 判 pipe 退化正常）
运行: -v rc=0 "cdcd 0.6.6" + "Using libcdaudio 0.99.12p2."
     -h rc=0 "Usage: cdcd [options] [commands]" + 21 条命令表
     坏设备 rc=1 "cdcd: cannot initialize /dev/…: No such file or directory"
make install DESTDIR rc=0 → bin/cdcd + man/man1/cdcd.1 + info/cdcd.info
toybox /bin/sh 直跑 configure+make 亦 rc=0（conan run 的真实 shell 语义，单独探针）
```

## 注意事项

- **上游测试总数 N=0**（tarball 54 文件 + 上游 git HEAD 3fac243 双面 grep 零命中，N 下界与声明一致）；
  `make check` 是 automake 默认空目标，配方真跑并输出 `HMBS_UPSTREAM_TEST_RESULT no_tests` 机器证据。
- 鸿蒙特有测试 = test_package 4 条用例（真实二进制，非空壳）。
- 本包为 `application` 类型：`package_info` 只导出 `bin/`，无 lib/include。
- `commands.json` 已建于软件级 `archives/c/cdcd/commands.json`（R38/PF8）。
- 外部硬件（/dev/cdrom 光驱）与网络 CDDB 在设备/CI 均不可用，未覆盖范围如实记录：真实播放路径与 CDDB 查询未运行。
