# cdcd 0.6.6：20 世纪末 autotools 老包在 OHOS+conan 下的四类探测失配（草稿，预留条目 E688）

- **软件**：cdcd 0.6.6（http://libcdaudio.sourceforge.net/ ，SourceForge 项目 libcdaudio 下的 command line CD player）
- **构建系统**：上游自带 autoconf-2.59 / automake-1.8 生成物（configure + Makefile.in），不跑 autoreconf
- **平台**：HarmonyOS PC / aarch64，clang 15.0.4，conan 2.29.1，profile `ohos-aarch64`
- **状态**：DRAFT（预留编号 E688，`tools/knowledge_id.py --claim` 回查未占用）
- **路径**：路径 B（知识库扩展）

## 现象

四类失配在同一次适配里依次爆（全部设备实测）：

```
① configure: Invalid configuration `aarch64-unknown-linux-gnu': machine `aarch64-unknown' not recognized
   configure: error: .../config.sub aarch64-unknown-linux-gnu failed
② checking for tputs in -lcurses... no
   configure: error: cannot find the curses library. Check the INSTALL file...
③ cmd_cdcd.c:1269:52: error: use of undeclared identifier 'CPPFunction'
   rl_attempted_completion_function = (CPPFunction *) cdcd_completion;
④ （预判面，承重）AC_PATH_PROG 找不到 libcdaudio-config；
   即使找到也输出 -I//include -L//lib（包内脚本 prefix=/ 烘焙死）
```

外加：config.status 自建 confstat 临时目录（`umask 077`）在 HMDFS 上
落 `drwx--S---`，写 `subs.sed` 即 `Permission denied`（E011/E206 族本例实测）；
`cdcdrc_read()` 先于 getopt 执行，缺 `$HOME/.cdcdrc` 的无头测试会进
交互式首启向导**永久挂起**。

## 根因

1. **config.sub/config.guess 世代过老**：随包 config.sub（1996）CPU 清单无
   aarch64 → `--build/--host` 校验一步即死；config.guess 在 HarmonyOS PC
   上 rc=1 空输出。且 conan `build==host` profile 时 `cross_building()` 为
   False，**AutotoolsToolchain 不注入三元组**——两处缺口都要配方自己补。
2. **探测名与 conan 交付物失配**：conan ncurses 只交付宽字符库名
   （libncursesw/formw/menuw/panelw，nm 实测 tputs/tgoto 在
   libncursesw.a），**没有 libcurses**；老 configure 的
   `AC_CHECK_LIB(curses, tputs,, AC_MSG_ERROR)` 必然 no → 硬失败。
   同根的编译期代际失配：readline ≥ 6 移除 `CPPFunction` typedef，
   2003 年源码的强转在 clang+readline 8 下报 undeclared identifier。
   **上游假设的库名/类型名 ≠ conan 制品仓实际交付的东西**。
3. **config-script 探测宏两处承重都靠 `--with-*-prefix`**：conanbuild
   PATH 只带 build 依赖 bindir、不含 host 依赖 bin/ → AC_PATH_PROG 找不到
   `libcdaudio-config`；且包内脚本 `prefix=/` 烘焙死 →
   `-I//include -L//lib` 假路径。一个
   `--with-libcdaudio-prefix=<package_folder>` 同时解决（宏内直接置绝对
   LIBCDAUDIO_CONFIG + 把 `--prefix=<pkg>` 传给脚本重推 -I/-L）。
4. **配置读取先于参数解析的老 CLI**：`cdcdrc_read()` 在 getopt 之前跑，
   缺 rc 文件直接进交互向导（stdin 提问 + 可能写回 HOME）→ 无头测试挂死；
   首行 revision 不匹配则 `exit(1)` + `Your .cdcdrc file is invalid.`
   （后者正好可当负路径用例）。

## 修法（5 补丁 + 2 个 configure 参数 + test_package 一个定式）

| 面 | 修法 | 补丁/参数 |
|---|---|---|
| config.sub 认 aarch64 | CPU 清单两处加 `aarch64` / `aarch64-*` | 0001 |
| config.guess 猜不出 | 显式 `--build/--host=aarch64-unknown-linux-gnu`（build==host 保原生、AC_TRY_RUN 真跑；linux-gnu 走 `*linux*` 分支定 HAVE_CDAUDIO —— cdck 0.7.0 先例；conan build==host profile 不注入所以必须自己给） | 配方 generate() |
| confstat 0700 不可写 | `umask 077`→`000`（mktemp 与 mkdir 回退两处都改，E011/E206 族） | 0002 |
| -lcurses 探测必死 | `AC_CHECK_LIB(curses→ncursesw)`，**configure 与 configure.ac 同改**（防 autoreconf 回退） | 0003+0004 |
| CPPFunction 未声明 | `RL_READLINE_VERSION >= 0x0600` 守卫切 `rl_completion_func_t *`，else 保留原分支——两代 readline 都能编 | 0005 |
| config-script 找不到/假路径 | `--with-libcdaudio-prefix=<package_folder>`（generate() 里取 `self.dependencies[...].package_folder`） | 配方 generate() |
| 无头测试挂死 | test_package 先在**隔离 HOME** 写出工具自己会写的配置文件（首行+键值逐字对齐其 write 函数），再跑用例；畸形配置做负路径用例 | test.sh |

## 复现命令（全部落 $TASK_DIR，设备可直接执行）

```sh
# ① config.sub 补丁前后对照（0001 存在理由实证）
sh $TASK_DIR/explore-src/config.sub aarch64-unknown-linux-gnu    # rc=0
# ② readline 代际（0005 存在理由实证）
grep -n CPPFunction $TASK_DIR/explore-src/cmd_cdcd.c             # 守卫两分支各一行
# ③ 三项探测承重读数（--with-libcdaudio-prefix 生效证据）
grep -E '^(checking for tputs in|checking for rl_completion_matches|checking for libcdaudio)' \
  $TASK_DIR/explore-build/configure.log                          # 全 yes
# ④ 硬依赖在架（真实 --build=missing 组合 rc=0 见 w0/combo-install2.log）
conan list -r=ohpcd 'libcdaudio/*' 'readline/*' 'ncurses/*'
```

## 验证

原生探索五读数全绿（`$TASK_DIR/explore-evidence.md`）：configure rc=0 →
make rc=0（ELF arm64 PIE，NEEDED 仅 libc.so，四库全静态）→ make check
rc=0（上游 0 用例空目标）→ make install DESTDIR rc=0（bin+man+info 三件）；
运行三路径 `-v` rc=0 / `-h` rc=0 / 坏设备 rc=1（cannot initialize）；
toybox `/bin/sh` 直跑 configure+make 双 rc=0（conan run 的真实 shell 语义）。
5 补丁干净树串行 dry-run 5/5 全过。

## 边界（不收录）

- 不是 glibc `printf.h`/ISA 专属头/内联 asm 面（W0-3 三证据 0 B，libvecpf 先例不适用）。
- 不是缺依赖止损面（三硬依赖 ohpcd 全在架，组合安装 rc=0）。
- E007/E011/E206 已覆盖「config.sub 认 aarch64」「mktemp 0700 HMDFS」
  主体；本条的增量是 **config.guess rc=1 + conan 不注入三元组**、
  **conanbuild PATH 不含 host bindir 与 config-script prefix=/ 烘焙**、
  **-lcurses vs 宽字符交付名**、**CPPFunction 代际**、
  **配置读取先于 getopt 的无头挂死** 五点。
