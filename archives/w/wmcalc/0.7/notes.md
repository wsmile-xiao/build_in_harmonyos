# wmcalc 0.7 适配笔记

## 编译环境
- 构建系统: autotools（autoconf 2.69 + automake，release tarball 已含 configure/Makefile.in/aclocal.m4，无需 autoreconf）
- 编译日期: 2026-09-27
- 编译器: clang（profile `ci/conan/profiles/ohos-aarch64`，/data/service/hnp/bin/clang）
- 构建主机: B 机（HarmonyOS aarch64），worktree `~/qzy/主理-74-wmcalc-0.7`，分支 `feat/wmcalc-0.7`
- CONAN_HOME: `~/tmp/ch/home-wmcalc`；profile 一律显式 `-pr:h/-pr:b`（该 home 的 profiles/ 为空，缺省 profile 会让 conan install/create 直接 rc=1）
- 状态: built（本地 conan create 通过，未上传制品仓）

## 定源与 W0 依赖

- 任务台账给的 `www.dockapps.net/wmcalc` 是 WindowMaker 系聚合站，不是源码发布点。从该页
  grep 出下载 href `/download/wmcalc-0.7.tar.gz` ⇒ 官方址
  `https://www.dockapps.net/download/wmcalc-0.7.tar.gz`。
- 设备侧连采 3 次：HTTP 200、`size_download=119785`、
  sha256 `422705d41c2d3a7ff5b88da758a73003fb4dfbab8649e7146bde426cec784040`
  —— 与台账记录的 Debian 池件 `wmcalc_0.7.orig.tar.gz` 逐字节同值（同一文件）。
  conandata 只写官方址，池址按 PF7 不入配方。
- 依赖面一手读 `configure.ac`（不是台账描述）：
  `PKG_CHECK_MODULES(X11,[x11])`、`PKG_CHECK_MODULES(XEXT,[xext])`、
  `PKG_CHECK_MODULES(XPM,[xpm])`、`AC_SEARCH_LIBS([pow],[m])`；
  `Makefile.am` 用 `AM_CFLAGS = $(X11_CFLAGS) $(XEXT_CFLAGS) $(XPM_CFLAGS)`、
  `LIBS += $(X11_LIBS) $(XEXT_LIBS) $(XPM_LIBS)`。
  ⇒ 精确依赖 = libX11 + libXext + libXpm（+ xorgproto 头）+ libm（工具链自带）。
- W0 逐条 `conan install --requires=<ref> --build=never -pr:h -pr:b <ohos-aarch64>`
  （2026-09-27，B 机，同轮对照包 ncurses/6.5）：

  | 依赖 | rc | 关键日志行 |
  |---|---|---|
  | libx11/6.4.0 | 0 | `libx11/6.4.0: Retrieving package ... from remote 'ohpcd'` |
  | libxext/6.4.0.1 | 0 | `libxext/6.4.0.1 ... Downloaded (ohpcd)` |
  | libxpm/3.5.17 | 0 | `libxpm/3.5.17: Retrieving package e647863c487673f3505fad09e4305079038bb22d from remote 'ohpcd'` + `Package installed` |
  | xorgproto/2025.1 | 0 | 三个 X11 包的传递依赖，同一轮解析 |
  | ncurses/6.5（对照） | 0 | 判"未发布"的对照组，本轮无未发布项 |

  日志留在 `~/tmp/uc2/z74-wmcalc/log-*.txt`。未使用通配 `conan list`，也未把
  `--only-recipe` 命中当已发布。
- **依赖轨**：与已合入的 xeyes/1.3.1、libxpm/3.5.17 一致走 cmd-pkgs 6.4.0 轨
  （libxpm/3.5.17 自身 `force=True` libx11/6.4.0）；libxext 取最新已发布修订 6.4.0.1。
- **同族对照**：asmix/1.5 当年因 libxpm 未发布，只能打补丁把 XPM 图标改成纯 Xlib
  pixmap（见 `archives/a/asmix/1.5/conandata.yml` 的 0001 描述）。本包 libxpm 已发布，
  ⇒ backdrop/calcbuttons/charmap 三个 .xpm 与 mask.xbm 全部按上游原样编译，
  **未裁剪任何功能面**。

## 编译步骤

`conan create archives/w/wmcalc/0.7 -pr:h=<abs>/ci/conan/profiles/ohos-aarch64
-pr:b=<same>`，配方内部实际动作：

1. `get()` 解包（strip_root）到 source_folder。
2. `_generate_ohos_configure()`：把上游 `configure` 复制成
   `build_folder/configure-ohos`，在副本上做两处按字面命中数校验的改写
   （`umask 077`→`umask 022`；`ac_pwd=\`pwd\`` 失败回退 `$PWD`）。上游文件本身与
   automake 生成物都不打补丁（R6）。
3. `_configure_ohos()`：`/system/bin/sh <build>/configure-ohos
   --build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-ohos
   --srcdir=<source> <conan 的 --prefix/--bindir… >`，
   经 `env="conanbuild"` 与 `Environment()`（TMPDIR / SHELL / CONFIG_SHELL /
   MKDIR_P / 六个 `X*_CFLAGS`、`X*_LIBS`）执行。
4. `make -j1`，随后 `make -j1 install DESTDIR=<package_folder>`。
5. `package()` 复制 COPYING 到 licenses/，对 `bin/` 逐文件剥 `.codesign` + 自签
   （OHOS 内核拒执行未签名 ELF），最后硬校验五个交付件存在：
   `bin/wmcalc`、`share/man/man1/wmcalc.1`、`etc/wmcalc.conf`、
   `share/icons/hicolor/48x48/apps/wmcalc.png`、`share/applications/wmcalc.desktop`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 第 1 轮 create：`configure: error: working directory cannot be determined`（create-1.log:145），前面刷满 bash 的 `shell-init/job-working-directory: error retrieving current directory: getcwd` | profile [buildenv] 把 `SHELL/CONFIG_SHELL` 设成 `/data/service/hnp/bin/bash`，autoconf 用 CONFIG_SHELL 重新解释自己；conan 缓存目录下 getcwd() 沿父链上溯失败，`ac_pwd=\`pwd\`` 判定即断 | 按 libXpm/3.5.17 的 `_run_ohos` 姿势：显式用 `/system/bin/sh` 跑 configure/make 并 export `SHELL=CONFIG_SHELL=/system/bin/sh`；另在 configure-ohos 里给 `ac_pwd` 加 `$PWD` 回退（E386、HMBS [shell_getcwd]） |
| 2 | 第 2 轮 create：`fatal error: 'X11/Xlib.h' file not found`，但编译行里明明有 `-I` | `PKG_CHECK_MODULES` 的 AC_ARG_VAR 变量以 `X11_CFLAGS='-I/a -I/b'` 形式写进 **configure 命令行**时，引号被 config.status 原样烘进 Makefile ⇒ make 展开后 clang 收到**单个带引号参数**而静默忽略 | 改由 **build 环境变量**注入同名变量（pkg.m4 的 `if test -n "$X11_CFLAGS"` 分支同样命中，configure 第 3647 行实拍），conanbuild.sh 会正确加引号、config.status 按值无引号写入 Makefile |
| 3 | HMDFS 上 config.status 的 `umask 077` 临时目录不可写 | E114/E129：HMDFS 新建目录恒带 setgid，`umask 077` 产出 `drwx--S---` 连 owner 都写不进 | configure-ohos 副本里 `umask 077`→`umask 022`（命中数 2 已按字面校验），并 `MKDIR_P=/system/bin/mkdir -p`、`TMPDIR=<build>/.tmp` |

## 源码修改

无补丁：`patches/` 不存在，`conandata.yml` 无 `patches` 段，
`create-3.log` 里 `apply_conandata_patches(): No patches defined in conandata`。
上游 .c/.h 一字未改；只在 build 目录内改 configure 的**生成物副本**。

## 依赖版本

- libx11/6.4.0（cmd-pkgs 轨）、libxext/6.4.0.1、libxpm/3.5.17、xorgproto/2025.1
- 传递：libxcb/1.16、libxau/1.0.11、libxdmcp/1.1.5、xtrans/1.6.0（由 libx11 图带出）
- 构建工具：工具链 clang 15 + `/system/bin/sh` + 设备 make；
  **未** tool_requires pkgconf（走 AC_ARG_VAR 逃逸口，见问题 2）

## 验证结果

```bash
$ conan create archives/w/wmcalc/0.7 -pr:h=... -pr:b=...
CREATE_RC=0                                   # 第 3 轮
wmcalc/0.7: Calling build()                   # 真跑判据（非 "- Cache"）
...
PASS A1 binary-present
PASS A2 help-exit0
PASS A3 banner-app-name
PASS A4 banner-version                        # 输出 " wmcalc 0.7"，来自 configure DEFS
PASS A5 usage-option-panel                    # -g/-d/-f/-v/-h 五选项面板
PASS A6 headless-display-failure (rc=81)      # ERR_X_DISPLAY：Could not open display
SUMMARY assertions=6/6 passed, 0 failed
```

- 消费者测试是**真执行被测二进制**：`wmcalc -h` 走 `show_usage()`（在 XOpenDisplay
  之前 exit(OKAY)），`wmcalc -d :99` 走 `XOpenDisplay` 失败分支
  → `error_handler(ERR_X_DISPLAY)` → `exit(81)`，输出含
  "Could not open display on :99"。⇒ 二进制在设备上可加载可执行，
  libX11/libXext/libXpm 的 `.so` 运行期解析正常（conanrun 的 LD_LIBRARY_PATH），
  **不是"编译冒充运行"**。
- 上游功能面的不可运行部分是结构性的：鸿蒙 PC 无真实 X display，dockapp 主路径
  （建窗、XPM 贴图、事件循环）不可能在无 X 服务器上运行。本包交付口径为
  "编译 + 静态交付件校验 + 真实失败形态（rc=81 的 Could not open display）"，
  申报范式同 `archives/b/bridge-utils/1.5/notes.md` 与 `archives/m/memdump/1.01`。

## 测试申报（R51）

- 上游测试清点：`grep -c check Makefile.am` = **0**；`find -type f` = **30** 个文件，
  无 tests/、test/、t/ 目录，无 `test_*` / `*_test` 源文件；`configure.ac` 无测试宏。
  ⇒ **上游真实测试数 = 0**（不写"上游测试全通过"）。
- `make check` 目标存在（automake 内建）但注册用例 0 条。
- 消费者测试（test_package）断言数 **6**，实测通过 **6/6**，汇总行
  `SUMMARY assertions=6/6 passed, 0 failed`。
- 同口径**三处**（本包不造 `reports/test-report.md`，写"四处"会指到盘上不存在的件）：
  `test_package/MANIFEST.yml`（`assertion_count: 6`）、本文件、版本级 `manifest.yaml` 的
  `verification.test_package.result`。`reports/` 下盘上实物只有 `conan-create.log`、
  `conan-verify-report.md`、`w3-local-ci.log` 三件，且都被仓根 `.gitignore` 的 `reports/` 通配排除。

## 交付物

| 文件 | 说明 |
|------|------|
| bin/wmcalc | 主程序（strip 后由配方逐文件自签 .codesign） |
| share/man/man1/wmcalc.1 | 上游手册页（dist_man_MANS） |
| etc/wmcalc.conf | 全局配置（dist_sysconf_DATA；烘进二进制的 `CONFIGGLOBAL=CONF"/wmcalc.conf"`，CONF=sysconfdir=`//etc`，与上游/发行版语义一致） |
| share/icons/hicolor/48x48/apps/wmcalc.png | 图标（dist_icon_DATA） |
| share/applications/wmcalc.desktop | desktop 入口（dist_desktop_DATA） |
| licenses/COPYING | GPL-2.0-only 全文 |

`package()` 对上述六项逐一 `is_file` 硬校验，缺任一项直接抛错。

## 注意事项

1. `wmcalcswitch.c` 的 `CONFTEMPFILE "/tmp/wmcalc.tmp"` 与
   `CONFIGGLOBAL "//etc/wmcalc.conf"` 都是上游硬编码路径；OHOS 上 `/tmp` 只读
   （SKILL §7 / E002）、`/etc` 不由包管理放置 ⇒ **保存配置**这条分支在本平台
   必然失败。属上游行为而非适配引入，未打补丁裁剪（保持上游语义），
   在此如实申报。
2. 主路径需要 X server；本设备无 ⇒ 计算器交互面（按钮、显示条、`-v` 调试输出）
   不可真机验证，只能到 `XOpenDisplay` 失败这一层。
3. profile 的 `os.version=6.0`、`arch=armv8`；换 profile 需重跑 create。
4. `~/tmp/ch/home-wmcalc/profiles/` 为空 ⇒ 任何 conan 命令都必须显式
   `-pr:h/-pr:b`，否则 rc=1 的报错会被误读成"依赖未发布"（本窗实拍）。

## 本地 CI / W3 证据

值全部由 `~/tmp/uc2/z74-wmcalc/fill_ci.py` 从盘上重算后写入（非手写）：

```text
reports/w3-local-ci.log        sha256(实算) = 655d6a6255a9d7f68a200a4aaee602913031847d2ee32a03ba2f30178ecbd0ed
.ci-result.json  exit_code      = 0
.ci-result.json  log_sha256     = 655d6a6255a9d7f68a200a4aaee602913031847d2ee32a03ba2f30178ecbd0ed
.ci-result.json  integrity_hash = ff83811d6752d58b
.ci-result.json  failed_step    = <无此字段>
log_sha256 与实算值一致         = True
```

判决与 junk 模式（同脚本从 w3-local-ci.log / finish-2.log 摘出的实物行）：

```text
无
JC 检查模式: 检查模式: incremental (10 个文件)
JC [FAIL] 命中: 无
```

## 发现与知识

- ✅ 自动工具链在 conan 缓存目录里最稳的执行姿势是显式 `/system/bin/sh` + `SHELL/CONFIG_SHELL` 覆盖，而不是让 autoconf 拿 profile 的 hnp bash 自重解释；bash 的 getcwd 诊断本身不改退出码，判"能不能跑"要看 configure 自己的 `working directory cannot be determined`  # knowledge_ref: E386
- ✅ HMDFS 新建目录恒带 setgid，`umask 077` 造出 owner 都写不进的 `drwx--S---`，config.status 的临时目录必须放宽到 022  # knowledge_ref: E114, E129
- ✅ OHOS 沙箱不能执行 conftest ⇒ autotools 必须靠 `--build/--host` 进交叉模式，运行型检查被跳过；wmcalc 的 configure 只有链接型 `AC_SEARCH_LIBS([pow],[m])` 与三个 PKG_CHECK_MODULES，跳过运行检查不改变判定结果  # knowledge_ref: E007
- ✅ PKG_CHECK_MODULES 的 `AC_ARG_VAR` 逃逸口要用**环境变量**传值；写成 configure 命令行参数时引号被 `config.status` 原样烘进 Makefile，编译器收到单个带引号参数并**静默忽略**（表现为 `X11/Xlib.h: No such file or directory`）。**未覆盖判定已按全树重扫**（⛔ 只扫 `knowledge/graph/*.kv` 就下结论）：`grep -rl AC_ARG_VAR knowledge/` = 2 个文件（12 行，全在 `knowledge/drafts/DRAFT-libxp-1.0.4-*`，其机制是 `printproto.pc` 元数据不可满足 ⇒ 同姿势不同因）；`grep -rlE 'config\.status.*引号|引号.*Makefile|静默忽略' knowledge/graph knowledge/drafts` 均 0 命中。⚠ 同**症状**家族确有既有条目：`knowledge/doc/E075.md`（`error_signature` 含 `pkg-config.*--cflags.*empty` 与 `fatal error:.*\.h: No such file`；先例见 `archives/a/actiona`、`archives/b/barrier`、`archives/b/baka`），但其 `root_cause` 是 `C_INCLUDE_PATH` 让 pkg-config 把 `-I` 当系统路径**过滤掉**、处方是移除 `C_INCLUDE_PATH`/`LIBRARY_PATH` ⇒ 同症状、不同因、不同处方，故升独立条目而非挂 E075  # knowledge_ref: DRAFT-WMCALC-0.7-AC-ARG-VAR-CONFIG-STATUS-QUOTE-BAKE-CFLAGS-LOST
- ✅ libxpm/3.5.17 已在 ohpcd 发布 OHOS armv8 二进制后，X11 dockapp 的 XPM 贴图面可原样保留，不必再走 asmix/1.5 的"剔 XPM 依赖"补丁路线  # knowledge_ref: 无（理由：非平台机制，是同族先例增量；对照 archives/a/asmix/1.5/conandata.yml 0001 描述）
- ✅ application 型 X11 包的无头交付口径：取 `XOpenDisplay` 之前的 `-h` 分支验功能，取 `-d :99` 分支验真实失败形态并记下 exit code（一手：上游 `wmcalc_err.h` 里 `ERR_X_DISPLAY=1105`，`wmcalc.c:895` 与 `wmcalc.c:153` 都走 `exit(err_code)` ⇒ 退出码被 shell 按 8 bit 截断，`1105 & 0xFF = **81**`，所以断言钉 81 而不是 1105，⛔ 为凑断言去改上游 exit 语义），比只报"编译通过"更可审  # knowledge_ref: 无（理由：交付口径先例见 archives/b/bridge-utils/1.5/notes.md、archives/m/memdump/1.01）
- ✅ 上游硬编码 `/tmp`、`/etc` 两条路径在 OHOS 上是结构性失败面（/tmp 只读、/etc 不由包放置），如实申报不改上游行为  # knowledge_ref: E002
- ✅ **E490 判真不适用（一手执行位实算，⛔ 无来源断言）**：`conan-verify-report.md:11` 的「已知风险 E490 未在配方中处理」不成立 —— 官方 tarball 解包后 configure=770、install-sh=770、missing=770、compile=770、depcomp=770（`tar xzf` 后 `stat -c %a` 实算），执行位本来就在；E490 的处方正是给这些 autotools 辅助脚本恢复 `+x`，本包既没丢位、也没走 `autoreconf` 重生成 ⇒ 无可作用载体。另 Makefile.in=660、aclocal.m4=660、configure.ac=660，本就不需要可执行位。  # knowledge_ref: E490
---

**编译结束**: 2026-09-27 03:52
**最终状态**: built
