# ptask 1.0.0 适配笔记（HarmonyOS PC / OpenHarmony aarch64）

## 结论摘要

- 上游：`ptask` 1.0.0（Jean-Philippe Orsini），**GTK+ 3 的 taskwarrior 图形客户端**。
- 源码：发行包 `configure` 已随包分发，**无需 autoreconf**；7 个补丁后
  `conan create` 全绿（`test_package` 14/14 条断言、`--selftest` 23/23 条检查）。
- 产物：`bin/ptask`（已自签名）+ `share/ptask/ptask.glade` + `share/glib-2.0/schemas/`
  （schema + `gschemas.compiled`）+ `share/applications/ptask.desktop` + 图标 + man page。
- 平台限制：鸿蒙 PC 无 X server，GUI 窗口无法打开；容器内做的是**无头验证**
  （CLI 契约 + `--selftest` 生产代码检查 + 无显示失败路径）。

## 上游身份与源码可得性（W0 实核）

平台任务 `ptask` / `1.0.0` 来自 Debian 源包清单（同批 `ptpd 2.3.1-debian1`、`pspp 2.1.1`
等 30+ 条与 sources.debian.org 逐条精确命中）。`ptask 1.0.0` 的唯一上游是
Jean-Philippe Orsini 的 GTK 任务管理器：

- Debian `ptask` 源包版本 `1.0.0-1.2`（`sources.debian.org/api/src/ptask/`）；
- AUR `ptask 1.0.0-2`，`Description: GTK+ task managing application`，
  `Depends: gtk3 json-c task=2.5.3`；
- 上游 `configure.ac`：`AC_INIT([ptask], [1.0.0], [jeanfi@gmail.com], [ptask], [http://wpitchoune.net/ptask])`。

**注意**：另有同名项目 `glipari/ptask`（Periodic Real-Time Task interface to pthreads），
其 README/CHANGES 最高版本为 **0.5**（2019-02），仓库无任何 tag/发行物
（`git ls-remote --tags` 为空，2026-05 已迁 Codeberg）——不存在 1.0.0，与本任务版本号不合，
故本包不是该项目。

### 官网已失效下的源选择

`wpitchoune.net` 已下线（curl 空响应 `000`），Debian `d/watch` 标记 `Untrackable`，
作者自己的 Launchpad PPA（`ppa:jfi/ptask`、`ppa:jfi/ptask-daily`）最高只到 0.0.9 / 0.0.5。
存世的原始发行物只有各发行版池中的 `ptask_1.0.0.orig.tar.gz`：

| 来源 | sha256 |
|---|---|
| deb.debian.org `ptask_1.0.0.orig.tar.gz`（Debian 另附上游签名 `.asc`） | `b8cde0f7994bd91410a13284188c865e255621bcfd23f6051f7b25b14eced18e` |
| archive.ubuntu.com（**本配方使用**） | 同上 |
| mirrors.kernel.org/ubuntu | 同上 |
| http.kali.org（https） | 同上 |

四源 sha256 完全一致 ⇒ 该 tarball 是未经 repack 的上游原始发行物（Debian 亦未加 `+dfsg`），
仅主机不同。配方因此使用 `https://archive.ubuntu.com/...`（https、权威发行版档案，
非 PF7 黑名单域名），并在 PR 正文说明来源与四源同 sha256 的核对结果。

## 编译环境

| 项 | 值 |
|---|---|
| 构建系统 | autotools（发行包已带 `configure`/`Makefile.in`，**无需 autoreconf**） |
| 编译器 | clang 15.0.4 / clang++（`/data/service/hnp/bin/clang`） |
| 目标 | `aarch64-unknown-linux-ohos`（`os=OHOS 6.0`, `arch=armv8`, `libc++`） |
| 依赖 | gtk/3.24.43、libx11/6.4.0、libxext/6.4.0、json-c/0.18、task/2.6.2（运行期 taskwarrior） |
| configure | `--prefix=/ --disable-nls` |
| shell | `CONFIG_SHELL=/system/bin/sh SHELL=/system/bin/sh /system/bin/sh ./configure …` |

## 编译步骤

```sh
conan create archives/p/ptask/1.0.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

`generate()` 用 `PkgConfigDeps` 生成 `gtk+-3.0.pc` / `x11.pc` / `xext.pc` / `json-c.pc`
（四者都声明了 `pkg_config_name`，configure.ac 的四个 `PKG_CHECK_MODULES` 全部命中），
并**就地修订三处 PkgConfigDeps 会丢失的信息**（详见下表「PkgConfigDeps 丢失项」）。
`package()` 依次：`make install DESTDIR=…` → 用自签名 host 工具编译 gsettings schema
→ 自签名 `bin/ptask` → 拷贝 `COPYING`。

### PkgConfigDeps 丢失项（三处，全部实测）

`PkgConfigDeps` 按依赖包的 `cpp_info` 重新生成 `.pc`，因此上游 `.pc` 里**不在 `cpp_info` 内**
的信息会丢失：

| 丢失项 | 症状 | 配方内的恢复动作 |
|---|---|---|
| `glib-2.0.pc` 的 `Libs:` 里没有它自带的 `libintl.so`（glib 在 OHOS 上自带一份 libintl，其公开头把 `gettext` `#define` 成 `g_libintl_gettext`） | 链接报 `undefined symbol: g_libintl_gettext`（log.o/main.o/ui.o 引用） | 把 glib 包内 `lib/libintl.so` 的**绝对路径**追加回生成的 `glib-2.0.pc` 的 `Libs:`（与 glib 自带 `.pc` 写法一致） |
| `json-c.pc` 的 `Cflags:` 只有 `-I${includedir}`（头文件实际在 `include/json-c/`） | `main.c`/`tw.c` 的 `#include <json.h>` 找不到头 | 给生成的 `json-c.pc` 追加 `-I"${includedir}/json-c"` |
| `gio-2.0.pc` 没有自定义变量 `glib_compile_schemas`（`PkgConfigDeps` 只导出 cpp_info，无法表达自定义变量） | `configure: error: glib-compile-schemas not found.`（`glib-2.0.m4` 的 `GLIB_GSETTINGS` 在非交叉编译分支用 `$PKG_CONFIG --variable glib_compile_schemas gio-2.0` 取值，为空即报错） | 在生成的 `gio-2.0.pc` 追加 `glib_compile_schemas=<build 树内自签名副本>` |

另外，`glib-compile-schemas` 在 conan 包里是**未签名 ELF**，OHOS 拒绝执行，故
`_prepare_ohos_host_tools()` 把它复制到 build 树并自签名；`package()` 里调用它编译 schema 时
必须处于 `_build_environment()` 的作用域内（需要依赖 libdir 在 `LD_LIBRARY_PATH` 上，
否则报 `Error relocating … symbol not found`）。

### gsettings schema 的实际归属（更正前一版笔记）

上游 `src/Makefile.am` 里确实有 `gsettings_SCHEMAS=ptask.gschema.xml` 与 `@GSETTINGS_RULES@`，
`configure` 会把 `GSETTINGS_RULES` 展开进 `src/Makefile`，因此 **`make install` 会自己安装
`ptask.gschema.xml`**；但该规则里编译步骤写作
`test -n "$(GSETTINGS_DISABLE_SCHEMAS_COMPILE)$(DESTDIR)" || $(GLIB_COMPILE_SCHEMAS)`，
**带 DESTDIR 打包时编译被跳过**。配方因此只在 `package()` 里补做「编译」这一步（安装 xml 交给上游），
不再重复拷贝 xml。（前一版笔记写的「`src/Makefile.in` 里没有 GSETTINGS_RULES」是错的：
`grep install-gsettings-schemas src/Makefile.in` 本来就该是 0，因为那串文本只在 `configure`/
`aclocal.m4` 里，`Makefile.in` 里是占位符 `@GSETTINGS_RULES@`。）

## 补丁说明（7 个）

| 补丁 | 类型 | 内容 | 必要性（实测） |
|---|---|---|---|
| `0001-config.guess.patch` | portability | 新增 `*:HarmonyOS:*:*` 分支，输出 `<machine>-unknown-linux-ohos` | 发行包 config.guess 为 **2012-02-10** 版，不认 `uname -s=HarmonyOS`，configure 会得到不可用的主机三元组 |
| `0002-config.sub.patch` | portability | `maybe_os` 与 kernel-OS 两张表加入 `linux-ohos*` | 使上一步产出的 `aarch64-unknown-linux-ohos` 成为合法规范三元组 |
| `0003-configure.patch` | portability | config.status 临时目录 `umask 077` → `022`（两处） | HMDFS setgid 语义下 0700 目录不可用，configure 写 config.status 失败（与 a52dec/bluefish 同族） |
| `0004-src-Makefile.in.patch` | portability | `AM_LDFLAGS` 的裸 `-export-dynamic` → `-Wl,--export-dynamic` | 上游写法 GCC 驱动接受、**clang 驱动不接受**：`-export-dynamic` 被原样转给链接器并按 `-e xport-dynamic` 解析 ⇒ lld 只打 `cannot find entry symbol xport-dynamic` 警告、ELF 入口点留空 ⇒ **产物每次执行都在任何输出前 SIGSEGV（rc=139）**。这是本包最隐蔽的坑：构建全绿、产物齐全。只补丁生成物 `Makefile.in`（不动 `Makefile.am`，避免触发 automake 重生成） |
| `0005-src-main.c.patch` | test | 新增无头 `-S/--selftest`（GTK display 之前退出） | 鸿蒙 PC 无 X server，GUI 无法自动化；该入口覆盖 pstr/ptime 与**完整 taskwarrior 导入链路**（版本闸、`task export` JSON 解析、tags/project 抽取），由自建 stub `task` 驱动 |
| `0006-src-pstr.c.patch` | bugfix | `trim()` 的 `memmove(str, p, strlen(p))` → `strlen(p) + 1` | 上游漏拷结尾 NUL：`"  spaced  "` 变成 `"spaceded"`、纯空白串永远不为空。`trim()` 是 `task_get_version()` 处理 `task` 输出的路径。该缺陷由 0004 的无头自检发现，修掉后自检断言才代表文档化行为 |
| `0007-src-tw.c.patch` | portability | ①删除 json-c ≥0.13 已移除的 `is_error()` 守卫（原为 no-op）②taskwarrior 版本闸放宽到 2.x 系列 | ①json-c/0.18 无 `is_error`，原样编译**链接失败**；②制品仓里唯一的 taskwarrior 是 `task/2.6.2`，上游白名单只到 2.5.0（与 Debian 对该版本的处理一致） |

补丁验证（生成后三关）：`NUL=0`、`@@` hunk ≥1、对 `.orig` 真 apply 后与 `.work` **逐字节一致**
（`$TASK_DIR/patch-apply-verify/`）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|---|---|---|
| 1 | `configure` 认不出主机 | 2012 版 config.guess/sub 不认识 HarmonyOS / `linux-ohos` | 补丁 0001+0002 |
| 2 | `configure` 写 config.status 失败 | `umask 077` 临时目录在 HMDFS 上不可用 | 补丁 0003 |
| 3 | `configure: error: glib-compile-schemas not found.` | `GLIB_GSETTINGS` 经 `pkg-config --variable glib_compile_schemas gio-2.0` 取值，`PkgConfigDeps` 生成不出自定义变量 | 给生成的 `gio-2.0.pc` 补该变量（指向自签名副本） |
| 4 | `fatal error: 'json.h' file not found` | json-c 头在 `include/json-c/`，生成的 `.pc` 只给 `-I${includedir}` | 给生成的 `json-c.pc` 补 `-I"${includedir}/json-c"` |
| 5 | `src/tw.c` 链接失败（`is_error`） | json-c ≥0.13 移除了 `is_error`（0.18 头文件中已无） | 补丁 0007① |
| 6 | `undefined symbol: g_libintl_gettext` | glib 自带 libintl，其 `libintl.h` 把 `gettext` 宏成 `g_libintl_gettext`；上游 `glib-2.0.pc` 会显式链接该 `.so`，而 `PkgConfigDeps` 版本不会 | 把 `lib/libintl.so` 绝对路径补回生成的 `glib-2.0.pc` |
| 7 | 装好的 `task` 是 2.6.2，ptask 拒绝工作 | 上游版本白名单 2.0.0–2.5.0（早于 2.6） | 补丁 0007②（与 Debian 同口径） |
| 8 | `make install` 会调用 `help2man` 重生成 man page | 打了 `src/main.c` 后 `src/ptask.1` 变旧；发行包虽带 `ptask.1`，规则仍会触发 | `build()` 内 `os.utime()` 保持随包分发的 man page 为最新（不引入 help2man 依赖） |
| 9 | **产物每次运行 rc=139（SIGSEGV），在任何输出之前** | 补丁 0004 的根因（`-e xport-dynamic`，入口点为空） | 补丁 0004 |
| 10 | `--selftest` 有 2 条断言失败（`"spaceded"`） | `trim()` 漏拷 NUL（上游缺陷，被 0005 的自检抓到） | 补丁 0006 |
| 11 | `package()` 里跑 host 工具报 `Error relocating … symbol not found` | 自签名 host 工具需要在依赖 libdir 在 `LD_LIBRARY_PATH` 上的环境里执行 | 把该调用移进 `_build_environment()` 作用域 |

## 源码修改

无上游**源文件**的功能性改写（仅 0005 增加一个测试入口、0004/0007 的平台/依赖兼容修正、
0006 的 NUL 漏拷修复），所有修改都在 `patches/` 中，未修改任何生成的构建文件
（`src/Makefile.in` 由 0004 修正一处链接标志，`configure` 由 0003 修正 umask，
其余 `Makefile.in` 保持发行包原样）。

## 依赖版本

- gtk/3.24.43（镜像/后端：broadway；该包 `-Dx11_backend=false`）
- libx11/6.4.0、libxext/6.4.0（configure 的 `PKG_CHECK_MODULES` 需要；源码不调用 Xlib）
- json-c/0.18
- task/2.6.2（Taskwarrior，运行期被 `popen("task …")` 调用）

## 平台限制与替代验证

鸿蒙 PC 无 X server。另记录一条与本包无关的设备事实（POSIX 实时调度不可用，实跑原始读数）：
`sched_setscheduler(0, SCHED_FIFO/SCHED_RR)` → `rc=-1 errno=22 EINVAL`；
`pthread_create(attr=SCHED_FIFO,prio=10)` 与 `pthread_setschedparam(self,SCHED_FIFO,10)`
→ `rc=1`（EPERM，需特权）；`sched_setscheduler(SCHED_OTHER)`、`pthread_attr_setsched*`、
`sched_getaffinity`、`clock_gettime(CLOCK_MONOTONIC)` 正常（`CPU_COUNT=1`，`os.cpu_count()=20`）。
原始探针源码与输出见任务目录 `$TASK_DIR/rtprobe/`。

GUI 交互无法自动化：`ptask` 编译/链接完整（`readelf -d` 的 `NEEDED` 含 `libgtk-3.so.0`，
`.codesign` 恰好 1 个），无显示时以 GTK display 错误失败退出（fail-closed），
证明 GTK 栈确实被加载并初始化。

## 验证结果

见 `reports/test-report.md`（上游 N=0 的清点证据、`test_package` 断言明细与通过率）。

## 注意事项

- **必须**同时安装 taskwarrior（`task/2.6.2`），否则 ptask 启动后加载任务列表失败并弹出
  「verify that a supported version of taskwarrior is installed」错误对话框。
- 运行期需要 GLib schema 可见：安装到 `/` 后 schema 位于
  `/share/glib-2.0/schemas`（随 `XDG_DATA_DIRS` 默认搜索）；容器内可用
  `GSETTINGS_SCHEMA_DIR` 指向包内目录。
- 上游 1.0.0 的 taskwarrior 版本白名单停留在 2.5.0；本包按补丁 0007② 接受 2.x 全系，
  这是与 Debian 一致的处理，**不是**无条件的版本放开。
- 无头自检会把 stub `task` 与临时导出文件写进 `$TMPDIR`（探测顺序见 0005 的实现），
  跑完自行清理；`/tmp` 在本设备只读，因此不要把它硬编码到临时目录。
