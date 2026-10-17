# yersinia 0.8.2 适配笔记

## 编译环境
- 构建系统: autotools（自带 `configure` 是 2013 年 `config.guess`，不识 OHOS → 配方走 `autoreconf -fi` 重生成辅助件）
- 编译日期: 2026-09-22
- 编译器: clang 15 / musl（profile `ci/conan/profiles/ohos-aarch64`，aarch64）
- 状态: built（conan-verify 与消费者测试全绿，尚未 release/upload）
- 依赖: `libpcap/1.10.6`、`libnet/1.2`、`ncurses/6.6`（require）；`automake/1.18`、`libtool/2.5.4`（tool_requires）
- 交付形态: 命令行程序 `bin/yersinia`（`package_type = "application"`、`cpp_info.bindirs = ["bin"]`、
  软件级 `commands.json` + `manifest.yaml` + `README.md` 齐备）。GTK2 界面经 `--disable-gtk` 关闭
  （`gtk+-2.0` 在 OHOS 未适配）。

## 编译步骤

```bash
autoreconf -fi                                                  # 换掉 2013 config.guess/sub
./configure --build=aarch64-unknown-linux-ohos \
            --host=aarch64-unknown-linux-ohos \
            --disable-gtk \
            --with-pcap-includes=<libpcap>/include \
            --with-libnet-includes=<libnet>/include \
            --with-ncurses=<ncurses 包前缀>
make -j1 check                                                   # 上游注册用例 0（见"测试账本"）
```
运行期/探测环境注入：`CPPFLAGS=-I<ncurses>/include`、`LDFLAGS=-L<私有 ncurses-shim> -L<各依赖>/lib`、
`TMPDIR=$HOME/tmp`；`build()` 内改写 conan 聚合 env 脚本绕开 hnp bash（E386）。

## 遇到的问题与解决方案

| # | 问题（逐字签名） | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `AttributeError: 'AutotoolsToolchain' object has no attribute 'cpp_flags'`（generate() 即挂） | conan 2.29 的 AutotoolsToolchain 只有 `extra_cflags/extra_cxxflags/extra_ldflags` 追加槽 | 改 `tc.extra_cflags/extra_ldflags`；同时把 `--with-*-includes`、`--with-ncurses` 与依赖 include/lib 全部经 `package_folder` 拼成**绝对路径**（`cpp_info` 返回的是相对路径，§12.2） |
| 2 | dlcache 命中失败：`The requested URL(s) are not listed in backup-sources metadata for this SHA256 cache entry` → 回源 `https://ghfast.top/...` connect timeout | 预置 sidecar 登记的是**旧注入镜像** `gh-proxy.com` 的 URL，而 conan-verify 的 E017 预防当前注入 `ghfast.top`；URL 集合不匹配 ⇒ 缓存判 dirty 并**删掉预置文件**（§12.39 预言的行为） | 用已核对 sha256 的本地 tarball 重新播种 `<dlcache>/s/<sha256>`，并把 sidecar 的 references 写成 `[官方 URL, ghfast URL, gh-proxy URL]` 三元素；缓存与 sidecar 都是本机私有，**绝不进 PR** |
| 3 | `configure.in:828: error: possibly undefined macro: AM_GLIB_GNU_GETTEXT` → `autoreconf` 失败 | 该宏由 glib 的 m4 提供，OHOS 侧无 glib 开发态 m4；且它虽写在 `if test $use_gtk = yes` 分支内，**autoconf 是 m4 期展开**，`--disable-gtk` 救不了 | 补丁 `0002`：把该行降级为 `dnl`（m4 注释）。依据：本包 `ALL_LINGUAS=""` 且无 `po/` 目录，`ENABLE_NLS` 仅被已禁用的 gtk UI 源码引用（`src/gtk-support.h:35`、`src/gtk-gui.c:153`）⇒ 不丢任何功能 |
| 4 | `checking for BPF device sending support... configure: error: cannot run test program while cross compiling` | 把 `--build` 写成 `aarch64-unknown-linux-gnu`（`--host` 为 ohos）后，autoconf 判定 `cross_compiling=yes`；该探测是裸 `AC_TRY_RUN`，既无 `ac_cv_*` 兜底也无 `--disable-bpf` 开关 ⇒ 直接 fatal。鸿蒙 PC 上构建即发生在目标机，两者本应相同 | 补丁前状态：`--build=gnu` → configure 死在探测；改回 `--build=aarch64-unknown-linux-ohos`（与 host 一致）后同一位置读数 `checking whether we are cross compiling... no`，探测正常给出结果。已作为知识草稿提交：`DRAFT-yersinia-0.8.2-build-host-mismatch-flips-cross-compiling-fatal`（含与 E467/E007/E159 的区分） |
| 5 | `ld.lld: error: duplicate symbol: protocols / interfaces / info_window / pointer` | 上游头文件里是**暂定定义**（`src/protocols.h:210`、`src/interfaces.h:70`），老 gcc 的 `-fcommon` 会合并，clang 默认 `-fno-common` 视为重复符号。另：`configure.in:17` 对 `CFLAGS` 是**整行硬赋值**，因此 `tc.extra_cflags` 与 `os.environ["CFLAGS"]` 两条注入通道都被丢弃（实测 `grep -c fcommon` 均为 0） | 补丁 `0003`：在唯一的 CFLAGS 赋值处补 `-fcommon`（一处改动、零语义漂移；E491 处方为 extern+单点定义，需动 4+ 头文件，此处按 W0b 记录偏离理由） |
| 6 | `checking for panel.h... no` + `checking for use_default_colors in -lncurses... no` ⇒ `error: unknown type name 'PANEL'` | 两条独立成因：① autoconf 的 `AC_CHECK_HEADERS` 走 `$CPP $CPPFLAGS`（预处理探测），此前 `-I` 只进了 `CFLAGS`；② conan `ncurses/6.6` 只发布宽字符归档名（`libncursesw.a`/`libpanelw.a`，无 `libncurses.a`/`libpanel.a`），而上游探测与链接写死 `-lncurses`、`src/Makefile.am:22` 写死 `-lpanel` | 配方 `build()` 内建私有 shim 目录（`libncurses.a→libncursesw.a`、`libcurses.a→libncursesw.a`、`libpanel.a→libpanelw.a`）并把其绝对路径加入 `LDFLAGS`，同时把 `<ncurses>/include` 注入 `CPPFLAGS`（先例 `acedb/4.9.62`、`4ti2/1.6.10`）。实测：`checking for panel.h... yes`、`use_default_colors in -lncurses... yes` |
| 7 | `ld.lld: error: undefined symbol: pthread_cancel / pthread_setcancelstate / pthread_setcanceltype` | OHOS libc 既未声明也未定义该组符号（独立探针实测：`clang --target=aarch64-unknown-linux-ohos` 编 `pthread_cancel(pthread_self())` → `call to undeclared function` + `undefined symbol`；而常量 `PTHREAD_CANCEL_ENABLE` 存在） | 补丁 `0004`：`configure.in` 增 `AC_CHECK_FUNCS([pthread_cancel pthread_setcancelstate pthread_setcanceltype])`（E407 的 configure-feature-probe 处方，探测期临时把 `-lpthread` 并入 LIBS）；补丁 `0005`：`thread_destroy_cancel()` 在无取消支持时改 `pthread_detach()`（唯一调用点是 `yersinia.c:784` 关机路径上的 uptime 线程，该线程无清理钩子、随进程退出），并把 `setcancelstate/setcanceltype` 调用点用 `static inline` 空操作收敛（源码零改写调用形态） |
| 8 | `make: jobserver mkfifo: ...: Operation not permitted`；`config.status: subs1.awk: Permission denied` | E074（HMDFS jobserver fifo）与 E114（HMDFS 强加 setgid 使 `umask 077 && mktemp -d` 造出不可写目录） | 全程 `make -j1`；`build()` 内就地改写 `configure` 的 `umask 077`（生成文件，按 R6 不产 `patches/`） |

依赖发布性：`libpcap/1.10.6`、`libnet/1.2`、`ncurses/6.6`、`automake/1.18`、`libtool/2.5.4` 均经
`conan download --only-recipe` 与首轮 `conan install --build=never` 实测已发布（R35：不用 `conan list` 判 binary）。

## 源码修改（补丁清单，均经 `git apply --check` 预验并按序应用）

| 补丁 | 文件 | 内容 | 类型 |
|---|---|---|---|
| `0001-configure-in.patch` | `configure.in` | `AM_INIT_AUTOMAKE(AC_PACKAGE_NAME, AC_PACKAGE_VERSION)` 双参旧式 → 无参现代形式（automake 1.18 已移除双参） | platform |
| `0002-configure-in-no-glib-gettext.patch` | `configure.in` | `AM_GLIB_GNU_GETTEXT` 降级为 `dnl`（OHOS 无 glib m4；本包无 `po/`、`ALL_LINGUAS=""`、NLS 仅已禁用的 gtk UI 引用） | platform |
| `0003-configure-in-fcommon.patch` | `configure.in` | 唯一的 `CFLAGS` 赋值处补 `-fcommon`（暂定定义族；见问题 5） | portability |
| `0004-configure-in-thread-cancel-probe.patch` | `configure.in` | 增 `AC_CHECK_FUNCS` 线程取消能力探测（见问题 7） | portability |
| `0005-thread-util-no-cancellation-fallback.patch` | `src/thread-util.h`、`src/thread-util.c` | 无取消支持时的兜底：detach + `static inline` 空操作（见问题 7） | portability |

补丁全部是"平台/工具链能力探测与兼容"性质，无功能删减、无 `__OHOS__` 平台宏注入（PF5 口径）。

## 测试账本（五维口径，AGENTS §10.1）

| 维度 | 数值 | 依据 |
|---|---|---|
| `N_static` 上游静态声明 | **0** | 全树 `Makefile.am` 无 `TESTS`/`check_PROGRAMS`；无 `test*/` 目录、无 `*RUNTEST*` 脚本、无示例/语料测试目录（按 §12.72 四种上游形态逐项自查，复算命令见下） |
| `N_registered` | **0** | 同上 |
| `N_executed` | **0**（`make -j1 check` 已真实执行，automake 无注册用例可跑，非人为跳过） | 配方 `build()` 内执行 `make check`，退出码 0 |
| 未执行/跳过 | **0** | 不存在"有条件未执行"的上游用例 |
| `N_consumer` 新增消费者测试 | **1 个测试程序（`test_package/test.sh`）/ 7 条行为断言** | 真实运行**已安装的** `bin/yersinia`：①无参输出含 `GNU yersinia 0.8.2` 版本横幅；②含 `Try 'yersinia -h'` 提示；③含上游 MOTD 行；④退出码 0；⑤~⑦ `-h`/`--version`/`-l` 三种入口在非 root 下均命中 root 门槛并打印 `You must be root to run yersinia 0.8.2`（root 环境走 SKIP 分支） |

复算命令（上游无测试的申报依据）：
```bash
grep -rn "^TESTS\|check_PROGRAMS" --include=Makefile.am .        # 空
find . -maxdepth 2 -type d -iname "*test*"                       # 空
find . -name "*RUNTEST*"                                         # 空
find . -maxdepth 2 -type d \( -iname "example*" -o -iname "*res" -o -iname data \)  # 空
```

## 验证结果

```bash
python3 scripts/ohc-run.py conan-verify yersinia 0.8.2
#   G0/G1/G2/G3/G4 全 PASS，VERIFY_RC=0
#   test_package: RUN: /bin/sh test.sh → PASS 1..7 → test yersinia 0.8.2: PASS
```

- 编译状态：通过（`conan create` 干净构建 + G3 系统同名库隔离 + G4 产物完整性）
- 上游测试用例通过率：0/0（上游注册用例为 0，`make -j1 check` 已真实执行且退出码 0；按 §10 以消费者测试补位）
- 新增测试用例通过率：7/7（100%，真实运行安装后的 `bin/yersinia` 并断言可观测输出）

## 已知限制

1. 运行需要 root 与 raw socket：非 root 环境下程序在门槛处即退出（rc=0），因此**攻击/抓包功能无法端到端验证**；
   本 PR 的实测面是包产物、链接闭合（`-lpcap -lnet -lpanel -lncurses`）与 CLI 可观测行为。
2. GTK2 界面关闭（`gtk+-2.0` 未适配），交付为 ncurses CLI。
3. 线程取消 API（`pthread_cancel`/`setcancelstate`/`setcanceltype`）在 OHOS libc 中不存在，
   关机路径按补丁 `0005` 走 detach 兜底（uptime 线程无清理钩子）。
4. `test_package` 的 root 门槛断言在 CI worker 以 root 运行时会打印 `SKIP 2` 而不失败（脚本内已分支处理）。
---

**编译结束**: 2026-09-22 02:54
**最终状态**: built
