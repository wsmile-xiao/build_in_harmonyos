# xauth 1.1.4 适配笔记

## 编译环境
- 构建系统: autotools（tarball 自带预生成的 configure / Makefile.in / config.h.in，无需 autoreconf）
- 目标平台: HarmonyOS PC / OHOS aarch64（profile `ci/conan/profiles/ohos-aarch64`）
- 编译器: clang/clang++（OHOS 系统自带）
- 状态: built（PR 阶段，未 upload）

## 编译步骤

```bash
# conan create 由 CI 在 HarmonyOS aarch64 真机执行
conan create archives/x/xauth/1.1.4 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

1. `source()`：下载 xauth-1.1.4.tar.xz（sha256 已校验），应用唯一的补丁
   `patches/0001-tests-ignore-locks-on-ohos.patch`（见「问题 10」），并把
   libXmu-1.3.1.tar.xz 展开到 `<source_folder>/vendor-libxmu/`
   （供就地编译 libXmuu，见下）。
2. `generate()`：
   - `AutotoolsToolchain` + `--build=aarch64-linux --host=aarch64-linux`
     让 configure 跳过 config.guess（OHOS 上 `uname -s` 返回 "HarmonyOS"，
     config.guess 认不出；config.sub 实测也不认 `linux-ohos`）。
   - 把 `XAUTH_CFLAGS` / `XAUTH_LIBS` 从 Conan 依赖目录 + vendored libXmuu 算出来，
     走 `PKG_CHECK_MODULES` 的 `AC_ARG_VAR` 逃生口完全绕过 pkg-config。
3. `build()`：
   - `_build_vendored_libxmuu()`：编译 libXmu 的 `src/GetHost.c` → `libXmuu.a`
   - `_relocate_dep_la_files()`：把 libXau.la 的 `libdir` / `dependency_libs`
     重定位到本机路径
   - `_patch_configure()`：`umask 077`→`022`；`ac_pwd=`pwd`` 追加 `$PWD` 兜底
   - `configure` → `make -j1` → `make check -j1`（上游回归套件实跑）
4. `package()`：`make install -j1` → `bin/xauth`，再按 E077 用
   `llvm-objcopy --remove-section .codesign` + `binary-sign-tool -selfSign 1`
   重新签名（鸿蒙内核只加载带有效 `.codesign` 段的 ELF）。

## 方案取舍：xmuu 从哪来

`configure.ac:53` 是

```
PKG_CHECK_MODULES(XAUTH, x11 xau xext xmuu xproto >= 7.0.17)
```

其中 `xmuu` 由 **libXmu 的子库** libXmuu 提供（上游 libXmu 一次构建发布
`libXmu.la` + `libXmuu.la`，`xmu.pc` 与 `xmuu.pc` 并列）。而 ohpcd 制品仓
既没有 libxmu 也没有 libxmuu：

```
$ conan list "libxmu/*"  -r ohpcd   # Found 0 pkg/version recipes
$ conan list "libxmuu/*" -r ohpcd   # Found 0 pkg/version recipes
```

三条路线：

| 路线 | 做法 | 判定 |
|------|------|------|
| A | 伪造 `xmuu.pc` 指向一个空库 | 链接期 undefined reference；且没有任何上游产物支撑，属伪造 |
| B | 手写 `XmuGetHostname` 桩（或等价实现） | 复制上游逻辑，产权不清（`xinit/1.4.4` 手写 `Xlib.h` + `x11_stub.c` 是这条的反面教材） |
| C | **从 libXmu 官方 tarball 取 libXmuu 的真实源码就地编译** | 源码本体即上游产物（sha256 官方值），零改写，静态随包携带 —— **采用** |

选 C 的依据是仓库既有的 E277 vendored 依赖模式（`xeyes/1.3.1` 内建
libICE/libSM/libXt/libXmu/libXi、`clinfo` 内建 OpenCL-ICD-Loader 同理）。

### 为什么只编一个 .c

libXmuu 有 5 个源文件（`ClientWin.c` / `CursorName.c` / `DefErrMsg.c` /
`GetHost.c` / `Lower.c`），但 xauth **全树对 Xmu 的引用只有一处符号**：

```
parsedpy.c:40  #include <X11/Xmu/SysUtil.h>
parsedpy.c:76  (void) XmuGetHostname (buf, maxlen);
```

`XmuGetHostname` 定义在 `src/GetHost.c`，非 WIN32 分支下只 include
`<X11/Xosdefs.h>` / `<string.h>` / `<unistd.h>` / `<X11/Xmu/SysUtil.h>`，
且 `config.h` 的引入被 `#ifdef HAVE_CONFIG_H` 守卫 —— 不定义就不需要 config.h，
也就完全不需要 libXmu 的 configure。

多编另外 4 个反而会引入 `DefErrMsg.c` 对 libX11 私有头 `<X11/Xlibint.h>` 的
依赖（制品仓确实有 Xlibint.h，但那是私有头，跨版本不保证），而 xauth 一个符号
都用不到。按实际需要取最小闭包。

产物命名为 `libXmuu.a`，与 `xmuu.pc` 的 `Libs: -L${libdir} -lXmuu` 对齐。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `PKG_CHECK_MODULES(XAUTH, … xmuu …)` 无解 | 制品仓无 libxmu/libxmuu，`xmuu.pc` 不存在 | 从 libXmu 官方 tarball 就地编译真实 `GetHost.c` → `libXmuu.a`，并用 `XAUTH_CFLAGS`/`XAUTH_LIBS` 走 AC_ARG_VAR 逃生口绕过 pkg-config（同 `libxp/1.0.4` 的 `XPRINT_*`） |
| 2 | `configure` 报 "cannot guess build type" / `config.sub` 不认 `linux-ohos` | OHOS 上 `uname -s` = "HarmonyOS"；xauth 1.1.4 自带的 config.sub 实测 `aarch64-unknown-linux-ohos` → "OS 'ohos' not recognized" | 显式给**本机三元组** `--build=aarch64-linux --host=aarch64-linux`（config.sub 规范化成 `aarch64-unknown-linux-gnu`），configure 走 non-cross 分支，conftest 真执行 |
| 3 | `libtool: cannot find the library .../libXau.so` | 发布的 libxau/1.0.11 里 `libXau.la` 的 `libdir=` 指向构建期临时目录，`dependency_libs` 残留 `-L/…/usr/local/lib` | `build()` 在 configure 前就地重写 `.la`（`_relocate_dep_la_files`，同 libxp/1.0.4） |
| 4 | 测试夹具写 `XAUTHORITY=${DATADIR:-/tmp}/.Xauthority`，OHOS `/tmp` 是 erofs 只读（E002） | 上游把临时目录当不变量 | `build()` 作用域内设 `DATADIR`/`TMPDIR` = `<build_folder>/test-scratch`，try/finally 恢复。本问题靠**环境注入**解决，不必动测试脚本（唯一改测试驱动的补丁见问题 10） |
| 5 | `configure` 报 "working directory cannot be determined" | HMFS 下 getcwd 不可达（`ac_pwd=`pwd`` 失败） | 重写为 `ac_pwd=`pwd` 2>/dev/null || ac_pwd="$PWD"`，并 `os.chdir(build_folder)` + 预置 `PWD`（同 aribb24/xsel） |
| 6 | `config.status` 用 `umask 077` 建临时目录，HMDFS 下不可执行 | E002/E114 | `configure` 内 `umask 077` → `umask 022` |
| 7 | 内核拒绝加载未签名 ELF（E077） | 鸿蒙要求 `.codesign` 段 | `package()` 内 `llvm-objcopy --remove-section .codesign` → `binary-sign-tool sign -selfSign 1` → `chmod 755` |
| 8 | 就地编 `GetHost.c` 报 `'X11/Xosdefs.h' file not found`（CI #53436） | 编译行只给了 `vendor/include`，而 `Xosdefs.h` 属于 **xorgproto**（已在 `requirements()` 里，只是没进 `-I`） | `_build_vendored_libxmuu()` 与 `_xauth_cflags()` 取同一份依赖 include 目录（`_dependency_dirs("include")`） |
| 9 | `make check` 5 个场景全体 FAIL，`test_xauth.log` 里 stderr 只剩 `Error loading shared library libX11.so.6: (needed by ../xauth)` / `Error relocating ../xauth: XCloseDisplay: symbol not found`，而夹具的 8 行期望输出一条都没产生（CI #53739/#53741，两个不同 worker 同现象） | `tests/test_xauth` **直接执行**刚链接出来的 `../xauth`，而 xauth 动态依赖 conan 包提供的 `libX11.so.6` → `libXau.so.6` → `libxcb.so.1` → `libXdmcp.so.6`，这些 .so 不在 OHOS 加载器的默认搜索路径里。进程在 `main()` 之前就被加载器判死，因此 5 个场景的输出全为空 → diff 全不匹配。**失败点看起来像「用例不通过」，实际是加载器限制** | `build()` 作用域内把 `_dependency_libdirs()`（整个依赖图的 lib 目录，含不参与链接但被递归 NEEDED 的 libxcb/libxdmcp）拼进 `LD_LIBRARY_PATH`，try/finally 恢复（同 `ezstream/1.0.2`、`aaphoto/0.45`）。本问题同样靠环境注入解决（唯一改测试驱动的补丁见问题 10） |
| 10 | 加载器修好后（问题 9），`make check` 仍 5 个场景全体 FAIL：`test_xauth.log` / `out.stderr` 里每个场景的 stderr 全是 `../xauth:  timeout in locking authority file `<build>/test-scratch/.Xauthority``（首个场景还伴随一次 `error in locking authority file`），`040-xauth-source` 的 `exits with` 实测 1、夹具期望 0，产物一条不产生（CI #62169，PR 11388 最新一次）。 | **OHOS 的 HMDFS 不支持硬链接**，而 libXau 的 `XauLockAuth()`（`libXau-1.0.12/AuLock.c`）加锁实现是：`open("<auth>-c", O_CREAT\|O_EXCL)` 后 `link("<auth>-c", "<auth>-l")`。`link()` 在 HMDFS 上必失败且 errno 既不是 ENOENT 也不是 EEXIST ⇒ 首次调用直接 `LOCK_ERROR`（`error in locking`），且 `<auth>-c` 已被留下 ⇒ 之后每次调用都撞 `O_EXCL` 的 EEXIST 分支，按 `XAUTH_DEFAULT_RETRIES(10)` × `XAUTH_DEFAULT_TIMEOUT(2s)` 睡满 20 秒后 `LOCK_TIMEOUT`（`timeout in locking`）。xauth 于是在**写授权文件之前**就退出，夹具里期望的输出一条都产生不出来。libXau **自带**的「文件系统不支持硬链接」兜底分支（`pathconf(creat_name, _PC_LINK_MAX) == 1` 时改用 `rename()`）在此**不触发**：musl 的 `pathconf` 对 `_PC_LINK_MAX` 恒返回 `_POSIX_LINK_MAX(8)`，不是 1。 | 用上游自己的逃生口 `xauth -i`（`xauth(1)`：`-i  ignore locks on authority file`；源码 `xauth.c:129` 置 `ignore_locks`，`process.c:753` 据此**跳过整个 `XauLockAuth()` 调用**）。打唯一一个补丁，只改**上游自带测试驱动** `tests/setup-sourced` 里两条真实执行的调用行 `../xauth "$@"` → `../xauth -i "$@"`（`echo "> xauth" "$@"` 那行不动，与 `.stdout` 夹具逐字节比对必须一致）。本测试是单进程顺序访问同一个 `$XAUTHORITY` 文件，锁不参与任何被断言的语义（夹具里没有任何锁相关文本），故纯属环境规避，产品行为与产物不变。 |

## 上游测试

xauth 1.1.4 **有**可自动执行的回归套件，本配方在 `build()` 内**实跑**：

```
tests/Makefile.am:  TESTS = test_xauth
tests/test_xauth:   遍历 ${srcdir}/*.script，逐个执行并与同名 .stdout/.stderr diff
```

| 场景脚本 | 覆盖内容 |
|----------|----------|
| `010-xauth-add-inet.script` | 带主机名的 add / list / nlist / remove 全链路 |
| `020-xauth-add-local.script` | 本地显示名（`unix:0`、`127.0.0.1:1`、`:2`、`:3.5`）匹配与 `wc`/`awk` 计数 |
| `030-xauth-extract.script` | `extract` 跨文件抽取 + `merge` 合并 |
| `040-xauth-source.script` | `source` 从命令文件批量读入 |
| `090-xauth-bad-usage.script` | 8 种非法显示名必须失败且 stderr 与夹具一致 |

**产品源码零改动**：补丁只落在上游自带的**测试驱动** `tests/setup-sourced`
上（问题 10），不碰任何产品源码、也不碰 `.stdout`/`.stderr` 夹具。其余两处
外部干预都在测试运行期、且都是环境注入而非用例改写：

- `DATADIR`/`TMPDIR` 指向可写目录（问题 4）；
- `LD_LIBRARY_PATH` 补上 conan 依赖的 lib 目录（问题 9），否则加载器根本
  起不来 `../xauth`，5 个场景的输出会全为空 —— 这与「用例断言不通过」是两回事。

### 唯一的补丁：`patches/0001-tests-ignore-locks-on-ohos.patch`

只改 `tests/setup-sourced` 里两条**真实执行**的调用行：

```diff
-  ../xauth "$@"
+  ../xauth -i "$@"
```

`echo "> xauth" "$@"` 那一行**保持原样**——它与各场景的 `.stdout` 夹具逐字节
比对，改它会立刻引入 diff 失败。`-i` 是上游文档化选项（见问题 10），语义是
「跳过授权文件的加锁」，正好绕开 HMDFS 无硬链接导致的 `XauLockAuth()` 必败。
补丁体只有两处 `-i` 加一段说明性注释，`patch -p1 --dry-run` 无 fuzz 通过。

同一原因也适用于 **test_package**：`test_package/test_xauth.sh` 的 4 条涉及授权
文件的调用（add / list / remove / 再 list）都带 `-i`。CI #62240 实测该脚本 5 项里
4 项失败，日志逐条是

```
xauth:  error in locking authority file <scratch>/.Xauthority
xauth:  timeout in locking authority file <scratch>/.Xauthority
```

——正是问题 10 里那套 `XauLockAuth()` 在 HMDFS 上的必败形态（首次 `link()`
失败留下 `<auth>-c`，之后每次都撞 `O_EXCL` 的 EEXIST 分支睡满重试）。断言本身
（授权文件的增/查/删）与锁无关，所以用上游自己的逃生口即可，产品行为不变。
脚本开头的 `rm -f` 同时清掉 `-c`/`-l` 两个锁残留，保证跨次运行的确定性。

用例是纯文件的（只操作 `$XAUTHORITY` 指向的授权文件），不需要 X server，
因此在无 X display 的 CI worker 上可原样执行；实测结果见 CI 构建日志的
`Testsuite summary`（`tests/test_xauth` = 1 个 automake 用例 × 5 个场景）。

## 依赖

- `libx11/6.4.0`、`libxext/6.4.0.1`、`xorgproto/2025.1`：ohpcd 已发布 OHOS armv8 binary。
- `libxau/[>=1.0.11]`：**写范围不钉死**。libxau 同时被 `libx11/6.4.0` →
  `libxcb/1.16` 传递引入，而制品仓里 libxcb 一侧的 libxau 诉求在
  1.0.11 / 1.0.12 之间变过；钉死任一侧都会撞 version conflict
  （`libxp/1.0.4` CI 实证）。
- `libxcb/1.16`、`libxdmcp/1.1.5`：**run 依赖**，只为 test_package 运行时
  定位 `libX11.so.6` 的 DT_NEEDED，不进 `-I`/`-L` 链接行。

## 已知限制

- libXmuu 只编入 `XmuGetHostname` 一个符号。若将来有消费者需要 libXmuu 的
  其他符号（`XmuStringToPixel`、`XmuNCopyISOLatin1Lowered` 等），应改为给
  `libxmu/1.3.1` 出独立配方，而不是在本配方里加源码（届时 `libxaw` 的阻塞
  也会一并解除）。
- `make check` 依赖 worker 上的 `diff` / `awk` / `xargs` / `wc` / `ls` / `sort` /
  `basename`。这些同属 CI 自身脚本使用的 coreutils 集合，判定为可用；若某个
  worker 缺失，表现为 5 个场景全 FAIL 而非静默跳过。
