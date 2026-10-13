# notes.md — tetradraw 2.0.3

## 构建信息

| 项目 | 值 |
|------|-----|
| 构建系统 | autotools (autoconf 2.57, automake 1.4, 手写 Makefile) |
| 状态 | built |
| 编译日期 | 2026-10-03 |

## 编译步骤

1. 源码: `https://deb.debian.org/debian/pool/main/t/tetradraw/tetradraw_2.0.3.orig.tar.gz`
   (sha256 `0fec43eea9ff3622547bccb602f52c4241f675921967cd46446de833fe67450a`,
   与 GPG 签名的 `.dsc` 一致; 上游站 tetradraw.sourceforge.net 只发 2.0.2 的
   `tetradraw-2.0.2.ane.diff.gz`, 2.0.3 tarball 由 Debian pool 权威再分发)
2. 补丁 5 个: `config.sub`/aarch64+linux-ohos、`Makefile` ncursesw 静态链接 +
   LDFLAGS 注入、`interface.c` opaque MENU 的 `item_index()`、`load.c`
   `rindex→strrchr`、`network.c` 的 `FD_SET`。
3. 配置: `AutotoolsToolchain` 生成的 `./configure --host=aarch64-linux-ohos --prefix=<package_folder> --build=... --disable-shared`(package_type=application 时 Conan 不加 `--enable-static`); ncurses 的 include/lib 由 `generate()` 以 CPPFLAGS/LDFLAGS 注入其 package_folder
4. 编译: `make -j1`（构建前 `_fix_timestamps()` 重置 byproduct 时间戳）
5. 安装: `make install DESTDIR=`（`autotools.install`）

## 依赖

- ncurses/6.6 (Conan 制品仓已发布, 仅供 `libncursesw.a`/`libmenuw.a` 静态链接)

## 关键适配点

1. **config.sub**: 2003 年版本不认识 `aarch64` / `linux-ohos`, 须注入以
   归一化到 `aarch64-unknown-linux-ohos`
2. **ncurses 6.6**: 提供的只有 `libncursesw.a`/`libmenuw.a` + `menu.h` 中的
   **opaque** `struct tagITEM`; 上游 Makefile 其实链 `-lncurses -lmenu`, 须
   改为 `-lncursesw -lmenuw`, 同时源码里 `items[]->index` 改用 `item_index()`
   (Debian `06_fix-ftbfs-with-opaque-ncurses` 同款修法)
3. **`src/Makefile.am` 自行 `LDFLAGS` 赋值会覆盖同名环境变量**: 改为
   `LDFLAGS = @LDFLAGS@ -L$(top_srcdir)/src`, 让 conan 注入的 LDFLAGS 透传。
   由于 automake 1.4 既不在 OHOS 也不在 CI 里(且会触发下面的时间戳连锁),
   `src/Makefile.in` 必须同步手改 —— 这是"改生成文件"的**唯一**例外,
   R6 的取舍记录在此: 重新生成需要 automake-1.4, 而它 `command not found`
4. **musl 已移除 rindex**: 改 `strrchr`
5. **automake 1.4 时间戳连锁**: 任何改动后须按 `configure.in` → `aclocal.m4`
   → `Makefile.am` → `configure` → `Makefile.in` 顺序递增 touch, 否则
   `Makefile.in` 的重跑规则会去调 `automake-1.4` 直接 Error 127。
   配方里由 `_fix_timestamps()` 固化(用 0/1/2/3 秒的相对序列而不是真实
   mtime, 保证与解包顺序无关的确定性)
6. **OHOS 的 `<sys/select.h>` 不符合 POSIX —— 最隐蔽的一个坑**:
   ```c
   void __fd_chk(int fd);                       /* OHOS 私有 libc 符号 */
   #define FD_SET(d, s) do { __fd_chk(d); ... } while (0)
   ```
   只要源码里出现 `FD_SET`, 产物就会引用 `__fd_chk`。这个符号**只有** OHOS
   sysroot 自带的 `libc.so` 才导出; 换任何别的 libc 装载(交叉执行沙箱、
   通用容器镜像、glibc/musl 宿主)就直接
   `Error relocating ...: __fd_chk: symbol not found`(exit 127)。
   表现是"编译链接全绿、跑起来就死", 而且链接期无任何警告。
   排查手法: `nm -u <binary> | grep chk` 逐个 `.o` 回溯到引用者
   (`find <build> -name '*.o' | xargs nm -u`), 本例定位到 `network.c` 的两处
   `FD_SET(STDIN/remote, &fds_read)`。
   patch 0005 把 `FD_SET` 还原成经典 POSIX 位运算 —— 这里监控的只有 STDIN
   和一个已 accept 的 socket, OHOS 那句 fd<1024 越界检查不可能触发,
   去掉它不损失任何东西, 换来的是产物只依赖标准 `select()` ABI。
   ⚠️ 注意: 一开始怀疑是 `_FORTIFY_SOURCE`, 加了 `-U_FORTIFY_SOURCE` 后
   `__fd_chk` 依旧存在 —— 因为它跟 FORTIFY 无关, 是平台头文件注入的。
   `_FORTIFY_SOURCE` 的等价开关在本 SDK 里对这个问题完全无效。

## 测试

- 上游**完全没有测试套件**(无 `make check` / `tests/` / ctest), 已在 pristine
  源码树上逐项确认; 因此适配侧补全 8 条断言(见 test_package/MANIFEST.yml):
  两个二进制存在且为 ELF、e_machine == EM_AARCH64、**真实执行**并穿透到程序
  自身 `setup_ncurses()`(src/term.c 在 `initscr()` 前无条件打印自己的 banner,
  只有真跑起来才会出现)、退出码排除 124(挂死)/127(loader 失败)/≥128(信号)。
  `TERM` 固定成一个任何机器都没有 terminfo 条目的名字, 保证确定性早退。
  测试不依赖任何宿主专有路径 / LD_PRELOAD shim。
- 反向验证: 门禁 L1e 把 `bin/` 移走后测试必须失败, 已实测通过。

## 已知限制

- ncurses 是**静态**链进去的, 且不打包 terminfo 数据库。tetradraw/tetraview
  是纯 TUI 程序, 要真正使用需要运行环境提供 `TERM` 对应的 terminfo 条目
  (系统 `ncurses-term` 或 `TERMINFO`/`TERMINFO_DIRS` 指向已有库)。

---

## 2026-10-11 修复 CI #80123：configure 猜不出 build type

真机日志（`OpenHarmonyPCDeveloper-CI-020`）：

```
checking build system type... config.guess[1331]: can't create
    /storage/Users/currentUser/.cache/tmp/cgDahGoC/dummy.c: Permission denied
config.guess: unable to guess system type
UNAME_SYSTEM  = HarmonyOS
configure: error: cannot guess build type; you must specify one
```

**根因**：CI 给 host 与 build 用的是同一个 OHOS profile（worker 本身就是
HarmonyOS PC），Conan 因此不认为这是交叉编译，`AutotoolsToolchain` 不会生成
`--host/--build`；configure 于是调用 tarball 自带的 `config.guess` —— 那是
autoconf 2.57（2003）的版本，既不认识 `uname -s` = `HarmonyOS`，写探测用的
`dummy.c` 时又被 worker 的临时目录挡掉（`Permission denied`），于是直接放弃猜测。

**修法**（`_autotools_toolchain()`）：当 `os == OHOS` 且 `not cross_building(self)`
时显式追加 `--build=aarch64-linux-ohos --host=aarch64-linux-ohos`（`wmtop/0.85`
先例），`config.guess` 不会再被调用；三元组能被接受，是因为 patch 0001 已经把
`aarch64` 与 `linux-ohos` 两种写法教给了这份老 `config.sub`。交叉构建
（host ≠ build）仍沿用工具链自己算出的三元组，互不影响。

同时给 configure/make（含诊断用的 `sh -x` 重跑）补上 `env="conanbuild"`：
真机 `config.log` 里 `CC=''`，说明此前是用配方进程的裸环境跑 configure，
编译器既不是 profile 指定的 OHOS clang，也没有 CFLAGS（与 R33 的口径不符）。
`env CONFIG_SHELL=/bin/sh SHELL=/bin/sh` 前缀保留，仍压过 profile 的
`CONFIG_SHELL=/data/service/hnp/bin/bash`，早前的 shell/getcwd 修复不受影响。

**本地复验**：`CONAN_PROFILE=ohos-aarch64-wsl`（host = build = OHOS，即真机同款
「非交叉」路径）跑 `ci/conan/build_and_test.sh`，`G0/KC/JC/L0/L1/L4/L5` 全通过；
configure 实测命令行：

```
env CONFIG_SHELL=/bin/sh SHELL=/bin/sh sh ./configure --prefix=/ ... \
  CPPFLAGS=-I<ncurses>/include LDFLAGS=-L<ncurses>/lib \
  --build=aarch64-linux-ohos --host=aarch64-linux-ohos
→ configure: creating libtool / config.status → make → test_package 正常执行
```

