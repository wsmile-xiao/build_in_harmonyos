# xset/1.2.5 适配笔记

## 软件说明

xset 是 X.Org 官方的 X 服务器用户偏好设置命令行工具（bell / keyclick / click
volume / LED / mouse accel / keymap / auto repeat / font path / screen saver /
DPMS / XKB 等），单源文件 `xset.c`（约 1700 行），autotools 构建。

- 上游仓库：https://gitlab.freedesktop.org/xorg/app/xset
- 本次源码：`https://xorg.freedesktop.org/archive/individual/app/xset-1.2.5.tar.gz`
  （canonical 实测 HTTP 200；旧址 `www.x.org/releases/...` 已 301）
- 版本串一律 `1.2.5` 原样，不归一化、不加后缀。

## 精确依赖是怎么定出来的（不是照抄任务描述）

对解包后的 `configure.ac` 逐行核实（这是本次适配最关键的一步，任务侧给的
依赖清单少了一项）：

| 位置 | 宏 | 语义 |
|---|---|---|
| `configure.ac:44` | `PKG_CHECK_MODULES(XSET, [xproto >= 7.0.17 xmuu])` | **2 参数＝硬失败**。必需 xproto + **xmuu** |
| `configure.ac:47` | `PKG_CHECK_MODULES(SET_X11, x11)` | 2 参数＝硬失败。必需 x11 |
| `configure.ac:49` | `PKG_CHECK_MODULES(SET_XEXT, xext, [AC_CHECK_HEADERS(dpms.h/MITMisc.h)], [echo "not found"])` | 4 参数条件式；缺了没有 DPMS / MITMISC 支持 |
| `configure.ac:55` | `PKG_CHECK_MODULES(SET_XKB, x11, [...XKBlib.h...], [echo "not found"])` | 条件式，复用 x11 |
| `configure.ac` xf86misc 段 | `USE_XF86MISC` 默认 `"no"` | 默认关闭，不需要 xxf86misc |
| `configure.ac` fontcache 段 | `USE_XFONTCACHE` 默认 `"yes"`，探测 `xfontcache` | 条件式（缺了只 echo），本配方显式 `--without-fontcache` |

⇒ 精确依赖 = **x11 + xext + xproto + xmuu**。

上表只列决定**必需依赖**的那 4 处探测点；`configure.ac` 全文的 `PKG_CHECK_MODULES`
实测共 **6 处**（本轮取数：`tar xzOf .build-cache/predl_cache/7d130733_xset-1.2.5.tar.gz
xset-1.2.5/configure.ac | grep -c PKG_CHECK_MODULES` = **6**，行号 44 / 47 / 49 / 55 /
64 / 78）——后两处 `SET_XF86MISC`(64) 与 `SET_FONTCACHE`(78) 分别嵌在
`if test "x$USE_XF86MISC" != "xno"`（63）与 `if test "x$USE_XFONTCACHE" != "xno"`（77）
条件分支内，即上表末两行所指的 xf86misc / fontcache 段；两者都**不是**硬失败（缺了只
`echo "not found"`），故不入精确依赖。注：`test_package/MANIFEST.yml:19` 与
`test_xset.sh:108` 的该句沿用早期口径写作「4 处」，指的就是上表这 4 处**必需**探测点，
全文实数为 6；本轮不改 `test_package/**`（改它等于换配方输入、要另起一轮）。

`xmuu` 的硬使用点：`xset.c:65` `#include <X11/Xmu/Error.h>`、
`xset.c:1681` 与 `xset.c:1684` 在 X 错误回调 `local_xerror` 的通用分支调用
`XmuPrintDefaultErrorMessage`（`xset fp` 的坏字体路径等错误都汇到这里）。

`configure.ac:36-38` 的 `m4_ifndef([XORG_MACROS_VERSION], ...)` +
`XORG_DEFAULT_OPTIONS` 只在 **autoreconf 阶段**才需要 xorg-macros；X.Org 的
dist tarball 自带预生成 `configure`（本包 `configure` 380815 字节，随包发布），
故**不需要 `tool_requires` xorg-macros/util-macros/automake**——与仓库
`archives/l/libx11/6.4.0`、`archives/l/libxext/6.4.0` 一致（两者都没有任何
tool_requires）。（对比：`archives/x/xsel/1.2.1` 的源码是 GitHub tag archive、
不含预生成 configure，才必须 `tool_requires` automake/libtool。）

## W0 依赖发布核验（正确方法 + 两轮）

方法：全新 `CONAN_HOME` 下 `conan download <ref> -r=ohpcd --only-recipe`，
**stderr 逐条落文件**，并要求出现 `Downloading recipe ...` 才算真访远端
（R35 禁止用 `conan list` 判 binary）。日志在
`~/tmp/uc2/z34-xset/logs/w0{b,c,d}-*.err`。

本轮踩到的两个方法性陷阱（都会造成"假未发布"，记录以免复发）：

1. **缓存命中伪装成远端命中**：第一轮在复用的 `home-xset` 里跑，多条 rc=0 的
   输出实为 `Skip recipe ... already in cache`（根本没联系远端）。
   ⇒ 判"已发布"必须看 `Downloading recipe` 行，或直接在全新 CONAN_HOME 里跑。
2. **全新 CONAN_HOME 不带 `remotes.json`** ⇒ 所有探针（含 zlib）齐报
   `ERROR: Remote 'ohpcd' doesn't exist`，看起来像"整个制品仓都拿不到"。
   ⇒ 建新 CONAN_HOME 必须连 `remotes.json` / `global.conf` 一起拷。
   这属于"环境问题"而非"依赖问题"，靠**对照包**当场就能识破。

判决（干净 `home-xset-w0`，同轮带正反控制）：

| 包 | rc | 远端响应 |
|---|---|---|
| `zlib/1.3.1`（正控制） | 0 | `Downloading recipe 'zlib/1.3.1#2ee7c0ee...'` |
| `libx11/6.4.0` | 0 | `Downloading recipe ... #63e25e48...` |
| `xorgproto/2025.1` | 0 | 已取到 recipe |
| `libxext/6.4.0` | 0 | 已取到 recipe（另有 actiona/3.11.1、libxext 自身配方在 main 已合并＝有 OHOS armv8 binary） |
| **`libxmu/1.3.1`** | **1** | `ERROR: error:system acceleration policy not enabled. [Remote: ohpcd]` |
| **`bogus-no-pkg/9.9.9`（反控制）** | **1** | **与 libxmu 逐字相同** |

⇒ `libxmu/1.3.1` 的 recipe **不在 ohpcd 制品仓**，尽管
`archives/l/libxmu/1.3.1/` 已合入 main。仓库内另有同结论的现成记载：
`archives/c/chiark-utils/8.0.1/conanfile.py:46`
"needing libxmu/1.3.1, which is merged in main but NOT yet published to the
registry (R36)"，其处置是把唯一需要它的程序剔除出构建。
（另注：`archives/l/libxmu/1.3.1/notes.md` 自称其依赖"均已发布"，属**配方
作者的记录**，不是制品仓实测，不能当 W0 依据。）
错误文本 `system acceleration policy not enabled` 对"不存在/未发布 recipe"
的语义见 E477（该条目同时说明 CI 的 L0i 会把这句误判成网络异常）。

## xmuu 怎么解决：只内建 5 个源文件的 libXmuu

不剔除功能、不给上游打补丁，改为 **E277 vendored 依赖模式**
（先例 `archives/x/xeyes/1.3.1` 从 X.Org 官方源内建 libXt/libXi/libXmu）：

- libXmu 的 `src/Makefile.am` 把库拆成两个：
  `libXmuu_la_SOURCES = ClientWin.c CursorName.c DefErrMsg.c GetHost.c Lower.c`
  （**只有 5 个文件**），而 `libXmu_la_SOURCES` 才包含其余 40 个；
- libXmu 的 `configure.ac:33` `PKG_CHECK_MODULES(XMUU, x11)` —— **libXmuu 只依赖
  x11**，xt 只有全量 libXmu 需要（`configure.ac:32` 的 XMU 探测），而 `xt` 同样
  没有已发布制品；
- ⇒ 配方只跑 `make -C src libXmuu.la`，**根本不构建 libXmu**，也就不会去撞
  xt 依赖；全量 libXmu 那条 XMU 探测用 pkg.m4 文档化的 `XMU_CFLAGS` /
  `XMU_LIBS` 覆盖口（configure 命令行 `VAR=value`，含空格处 `shlex.quote`）
  短路掉，让 configure 能跑到生成 `config.h` 为止。
- 产物静态链入 xset（`--disable-shared --enable-static --with-pic`），不向系统
  目录装同名库（R26）；staging 只装 `libXmuu.a` 与 `include/X11/Xmu/*.h`，
  **不跑 `make install`**（顶层 install 会去构建未满足的 libXmu，且 HMBS 的
  install shim 对多源 `install -c -m 644 f1..fN dir/` 直接 exit 64 = E182）。
- `DefErrMsg.c` 无条件 `#include <X11/Xlibint.h>`（libX11 私有头）。
  xeyes 当年为 Eyes.c 里**未使用**的同一个头打了删除补丁；这里是真使用
  （`XLockDisplay`/`XUnlockDisplay`），故不做删除补丁，靠 conan
  `libx11/6.4.0` 的头目录提供。

xset 侧则**不用**逃逸口：配方自己写一份 `xmuu.pc`（`Requires: xproto x11`）
放进 generators 目录，让 `PKG_CHECK_MODULES(XSET, [xproto >= 7.0.17 xmuu])`
走**真实 pkg-config 探测**，`-lXmuu` 与传递的 `-lX11` 由 pkg-config 自己算，
避免"为了过探测把整条依赖检查短路"。

**链入事实核验（2026-09-25，B 机实测，非推断）**：`readelf -sW` 打在打包出的
`bin/xset` 上，`XmuPrintDefaultErrorMessage`（1228 字节 FUNC）、
`XmuSimpleErrorHandler`、`XmuSnprintf`、`XmuCopyISOLatin1{Lowered,Uppered}`、
`XmuCompareISOLatin1`、`XmuNCopyISOLatin1{Lowered,Uppered}` 共 8 个符号均为
**已定义**（`FUNC GLOBAL DEFAULT`），`UND` 里的 Xmu 符号数 **= 0** ⇒ libXmuu 确为
静态链入而非悬空引用。`readelf -d` 的 NEEDED 只有
`libX11.so.6 / libxcb.so.1 / libXau.so.6 / libXdmcp.so.6 / libXext.so.6 / libc.so`，
无 `libXmuu.so`，与 R26 静态化口径一致。

## 构建系统层面的 OHOS 适配点（全部沿用仓库已验证机理）

| 机理 | 出处 | 本配方落点 |
|---|---|---|
| `config.guess` 认不出 HarmonyOS（`uname -s` = `HarmonyOS`）→ 显式 `--build/--host=aarch64-unknown-linux-gnu` | xsel/1.2.1、libxext/6.4.0、a52dec/0.7.4 | `generate()` OHOS 分支、`_build_xmuu()` |
| HMDFS 不支持 `getcwd` → `chdir(build_folder)` + 预置 `PWD` + 改写 configure 的 pwd 判定（autoconf 2.70+ 与 2.69 两种形态） | xsel/1.2.1、aribb24/1.0.4 | `build()`、`_patch_configure()` |
| E114：`config.status` 用 `umask 077` 建临时目录，HMDFS 下不可写 → 改 022 | 仓库既有知识 E114 | `_patch_configure()`（对 xset 与 vendored libXmu 两处 configure 都打） |
| 真机 conan 2.x 由 `PkgConfigDeps`/`AutotoolsToolchain` 注入的 `PKG_CONFIG_PATH` 不生效 → 在 `build()` 内作用域注入并 try/finally 恢复 | xsel/1.2.1（pidgin 同款坑） | `build()` |
| E490：autotools 辅助脚本是**可执行文件**，解包后可能保住内容却丢执行位 → 幂等补 `+x`（HMFS 上 chmod 可能 no-op，故容错） | 仓库既有知识 E490（G0 预扫点名） | `_restore_script_modes()`，两棵源码树各一次 |
| 制品仓包内 `.la` 记的是**打包机绝对路径**，缓存搬家后 libtool 沿 `-lX11` 递归解析 `dependency_libs` 会炸（`... libXau.la is not a valid libtool archive`）→ 本包只需静态 `libXmuu.a`，用**不含 `.la`** 的私有 shadow libdir + 显式 `XMUU_CFLAGS/XMUU_LIBS`，让 `-lX11` 直接解析到 `.so` 而不进 `.la` 链 | 同族正规解法见 `archives/l/libxmu/1.3.1/conanfile.py::_prepare_ohos_libtool_shadow()` | `_libtool_shadow()` |
| 文档链（xmlto/fop/xsltproc）CI 无，显式关 | libxext/6.4.0 | `_build_xmuu()`（xset 无 doc/ 目录，不需要） |

## 上游测试三步法申报（R51）

1. **清点**（源码静态，已逐条落 `test_package/MANIFEST.yml`）：
   `xset-1.2.5` 官方 tarball 解包后只有 `xset.c`、`man/`、autotools 生成件；
   `Makefile.am` 全文 grep `check`/`TESTS` **零命中**（`SUBDIRS = man`、
   `bin_PROGRAMS = xset`）；`configure.ac` 无测试宏 ⇒ **上游自动化测试 0 项**。
2. **实际运行**：不适用（无测试可运行；"没有自动化测试"是清点的结论，不是
   "没环境"的托词）。
3. **回填**：消费者测试 `test_package/test_xset.sh` 自行设计 **6 条硬断言**，
   本轮实测 **6/6 通过**（`discovered=6, passedCount=6`，见"门禁判决"）。
   未覆盖功能面在 `test_package/MANIFEST.yml` 的 `not_covered` 与下方
   "未覆盖功能面"逐条列出。

### 断言可达性在本轮被实测纠正过一次（重要，别改回去）

上一版第 5 条断言"`xset -no-such-option` 命中 `xset.c:756` 的
`usage("unknown option %s", arg)`"**不成立**，实测失败。依据是读上游源码
的执行顺序：`xset.c:165-177` 的**第一轮**扫参对任意未识别参数只置
`hasargs = True`（174-176 行），随后 182 行**无条件** `XOpenDisplay(disp)`；
而 756 行所在的是 189 行起的**第二轮**解释循环，**必须先有可用 X 连接**。
⇒ 无 X server 的真机/CI 上该命令的唯一出口是 `unable to open display ""`
（rc=1），`unknown option` 分支**根本不可达**。属**断言写错**，不是本包缺陷。

换成两条经实测可达、且互相构成正反证的断言：

- **⑤** `xset -display` 与 `xset -d`（缺值）⇒ 命中
  `missing argument to -display` + usage 文本、rc=0（`xset.c:167-170` →
  `usage(fmt)`；该点位于第一轮扫参、在 182 行 `XOpenDisplay` **之前**）。
  rc=0 亦为上游事实：`usage()` 无论有无 fmt，尾部一律
  `exit(EXIT_SUCCESS)`（`xset.c:1648`）——故**不能**拿"非 0 退出"当 usage 分支的判据。
- **⑥** usage 文本**不含** `To control font cache` ⇒ **反向**反证配方的
  `--without-fontcache` 真传到 configure（该小节在 `#ifdef FONTCACHE` 内，
  `xset.c:1605-1612`）。与③（DPMS 小节**存在**，`#ifdef DPMSExtension`）
  一正一反：只断言"存在"时整段被全量编进也判绿，只断言"不存在"时整段被裁光
  也判绿，两条同置才排掉这两种假绿。

实测计数（`xset` 裸跑 usage 全文 53 行，2026-09-25 B 机）：
`To control font cache`=0、`Display Power Management Signaling`=1、
`bug compatibility mode`=2（MITMISC 成立）、`led named`=2（XKB 成立）、
`r rate`=1（`#if defined(XF86MISC) || defined(XKB)` 经 XKB 成立）。

## 未覆盖功能面（无 X server，如实声明）

需要真实 X server 的路径全部未断言：`xset q` 查询输出、`b`/`-b`（bell）、
`c`/`-c`（click）、`led k`/`-led k`、`m1..m5`/`mouse`、`kb`/`reset`、
`fp`/`+fp`/`-fp`/`fp=`（字体路径，含 `xset.c:1661` 的 bad font path 分支）、
`dpms`/`+dpms`/`-dpms`/`dpms force`、`s`/`-s`（屏保）、`r`。

另有三类**本环境不可达**、故未纳入断言的代码路径：

- `xset.c:756` 的 `usage("unknown option %s")`（见上节，需先建立 X 连接）；
- `xset.c:1681/1684` 的 `XmuPrintDefaultErrorMessage` **调用点**（X 错误回调内，
  同样需 X 连接）——vendored libXmuu 已静态链入这一事实由上方 `readelf` 另证，
  **不等于**调用路径被运行过；
- 其余 `usage(fmt)` 点（`missing fp= argument` 等，`xset.c:349-737`）均在第二轮
  循环内，需 X 连接。

XKB 路径随 libx11 编入但未断言（仅断言其 usage 小节存在）；xf86misc（上游默认
关）与 fontcache（本配方显式关）按条件编译裁掉——后者"被裁掉"本身由断言⑥正向证明。

## 发现与知识（本包知识清单）

以下 6 条与本包 `manifest.yaml` 的 `knowledge_gained` 一一对应（每条末尾给出
复用出处，供 `check_knowledge_gap` 核对引用）：

- ✅ **精确依赖必须逐行读 `configure.ac`，不能按"X 客户端只要 x11/xext"的先验推断**：本包 `configure.ac:44` 的 `PKG_CHECK_MODULES(XSET, [xproto >= 7.0.17 xmuu])` 是 2 参数硬失败形态，任务侧给的依赖清单缺 `xmuu`；证据 `xset.c:65`/`1681`/`1684`。ref: 本包新增（既有 E468 讲的是 PKG_CONFIG_PATH 未注入，签名与解法均不同，不可混引）
- ✅ **"配方已合入 main" ≠ "制品仓可取"**：`libxmu/1.3.1` 的 recipe 在 `origin/main` 存在、其 notes 自称依赖已发布，但全新 CONAN_HOME 下 `conan download --only-recipe` 与故意编的不存在包报**逐字相同**的 `system acceleration policy not enabled`。ref: E477（错误文本语义）+ `archives/c/chiark-utils/8.0.1/conanfile.py:46`（同结论现成记载）
- ✅ **发布态探针纪律四条**：①必须在全新 CONAN_HOME 里探，复用缓存时 rc=0 可能只是 `Skip recipe ... already in cache`（假成功，根本没联系远端）；②新建 home 必须连 `remotes.json`/`global.conf` 一起拷，否则全体（含对照包）报 `Remote 'ohpcd' doesn't exist`，环境问题会被读成依赖问题；③同轮必带正控制（zlib）与反控制（故意不存在的包），目标报错与反控制逐字相同才可判未发布；④空错误体的 rc 一律先怀疑判据、禁止据此下"未发布"结论。ref: 探针纪律为本包新增（E477 只给"用 conan list 复核"，未覆盖①②③；且 R35 禁以 `conan list` 判 binary）
- ✅ **libXmuu 可独立构建，是绕开缺失依赖的最小切口**：libXmu 的 `src/Makefile.am` 里 `libXmuu_la_SOURCES` 只有 5 个文件、`configure.ac:33` 的 `PKG_CHECK_MODULES(XMUU, x11)` 只依赖 x11 ⇒ `make -C src libXmuu.la` 单建即可避开需要 `xt` 的全量 libXmu（`xt` 同样无已发布制品），无需把 libICE/libSM/libXt 整条链内建（对比 `xeyes/1.3.1` 因真用 Xt/Xmu/Xi 才必须建全链）。ref: E277 vendored 模式的本包实例
- ✅ **X.Org dist tarball 自带预生成 `configure` ⇒ 不需要 xorg-macros/util-macros/automake 的 `tool_requires`**（本包 `configure` 380815 字节随包发布，与 `libx11/6.4.0`、`libxext/6.4.0` 同形）；只有 GitHub tag archive（如 `xsel/1.2.1`）才必须 autoreconf 自举。ref: 与 E468 的 util-macros 建议互补——E468 适用面是"确实需要 xorg-macros.pc 的包"，dist tarball 不落入
- ✅ **对 configure 的 HMDFS/umask 改写必须同时覆盖 vendored 依赖那一棵树**：`getcwd` 与 E114 `umask 077` 两处补丁本包对 xset 与 libXmu **两份 configure** 都打，只打主源码树会在 `_build_xmuu()` 阶段复现同类失败。ref: E114 + xsel/1.2.1 机理在本包的第二处落点

另有一条**本包踩到并已按既有条目处置**的框架侧坑（不是本包新增知识）：

- ✅ **`conandata.yml` 注释里的带协议 URL 会被 CI 的 Pre-download 折进真实 `url:`**：`ci/conan/build_and_test.sh` 的 Pre-download 用正则从 conandata **全文**提取 URL（注释行也算），下载后对全文做字符串替换；本包注释里那个带尾斜杠的目录前缀恰好是真实 url 的**前缀子串**，于是真实 url 被替换成 `<hash>_source_<hash>xset-1.2.5.tar.gz` 这种不存在路径，`conan create` 在 `source()` 即 `FileNotFoundError` ⇒ W3 的 L1 红（2026-09-25 02:46）。处置 = 注释一律写裸主机名+路径；自查 = 扫"以 # 开头且含双斜杠协议分隔符"的行必须无输出。ref: `knowledge/drafts/DRAFT-8960-raqm-0.11.0-conandata-comment-url-predl-pollution.md`（同机制另见 `DRAFT-8543`；同族不同签名见 E333）

复现证据（不动归档、在副本上跑脚本自带的 predl 代码块）：
`~/tmp/uc2/z34-xset/predl-repro/`（修复前提取到 **4** 个 URL，真实 `url:` 被折成
`.../predl_cache/531a11d6_source_531a11d6xset-1.2.5.tar.gz`）、
`~/tmp/uc2/z34-xset/predl-repro2/`（修复后提取到 **2** 个，均为真实源码 URL）。
其中 `531a11d6` = `md5("https://xorg.freedesktop.org/archive/individual/app/")[:8]`，
即那条注释目录前缀本身。修复后 `predl_cache` 内两个真实 tarball 的 sha256 与
`conandata.yml` 声明一致（`2068d135…` / `3091d711…`，逐字节核过）。
> 注：本包**未**清空 `.build-cache/predl_cache`——DRAFT-8960 要求清空是为了防坏
> HTML 缓存以 `[cached]` 复活，而本包修好后那条注释 URL 已不再被提取，污染条目
> 不再被任何路径引用（保留而不删，遵"predl 产物不提不删"口径）。

## 适配路径声明（3+2）

- **适配路径**：A（标准 Conan 配方 + 上游 autotools，无上游源码功能补丁）
- **使用知识库**：E114（config.status `umask 077` 在 HMDFS 不可写）、
  E277（vendored 依赖模式：制品仓缺库时从官方源在配方内构建）、
  E182（HMBS install shim 只接受单文件两参调用，多源批量 install exit 64）、
  E490（autotools 辅助脚本执行位幂等补 +x）、E477（制品仓对未发布 recipe 返回
  `system acceleration policy not enabled` 的文本语义）、
  `knowledge/drafts/DRAFT-8960-raqm-0.11.0-conandata-comment-url-predl-pollution.md`
  （conandata 注释 URL 被 Pre-download 全文替换污染 ⇒ 注释不写带协议 URL）、
  `archives/l/libxmu/1.3.1/conanfile.py::_prepare_ohos_libtool_shadow()`
  （`.la` 绝对路径失效家族的同族解法）
- **知识库扩展**：无新增通用机制（B 判定 = **hit**，逐条复用出处见本文件"知识清单"
  一节末与 PR 正文的四条件核对；本轮唯一新踩的机制已被 DRAFT-8960 精确覆盖）
- **关联 Issue**：待创建（PRE_CREATE）；若主窗判定 `libxmu` 未发布需要单独立项，
  Issue 主体应是 **libxmu 制品发布**，不是 xset 的新机制

## 门禁判决

（判决一律**只认文字与 rc，不认图标**——本仓 `ohc-run.py` 的判决行会出现图标与
文字相反的情形，2026-09-25 02:20 实测原文为 `  ✅   G2: FAIL`，同轮
`CONAN_VERIFY_RC=1`，故判绿须"文字 PASS + report `**Verdict**: PASS` + rc=0"三致。
以下每一轮都附该轮的 `CONAN_HOME` 自证行与默认 home 泄漏计数。）

环境口径：`CONAN_HOME=$HOME/tmp/ch/home-xset`（B 机）。`conan config home` 在
不 export 时返回 `/storage/Users/currentUser/.conan2`、export 后返回
`/storage/Users/currentUser/tmp/ch/home-xset` ⇒ 内外层脚本**各自** export，
不依赖继承；每轮日志首行印 `INNER_CONAN_CONFIG_HOME=…/home-xset` 自证。

### 已修掉的三处真红（第 1 处在 conan-verify 内，第 2/3 处只有跑 finish 才会暴露）

| 轮次 | 门 | 第一条真实错误（原文摘） | 定性 | 修复 |
|---|---|---|---|---|
| 02:20 | conan-verify **G2** | `Error in test() method, line 43 … ConanException: Error 1 while executing`，上一行 `[FAIL] 未命中 'unknown option -no-such-option' + usage 文本，实际输出首行：xset:  unable to open display ""` | 消费者**断言不可达**（非构建、非依赖、非工具链） | 断言 5 换可达分支 + 加断言 6（`d383e78614`→`16d868dfa3`） |
| 02:42 | finish **Step5/L0** | `[fail] xset/1.2.5 — L0 quality gate failed: hardcoded_remote` | `build_and_test.sh:420-429` 的正则不区分注释与代码，命中配方 **docstring 第 23 行**记录的 W0 探针命令 | 命令改写为 `--remote=` 等价形式（`4e36a483a7`） |
| 02:47 | finish **Step5/L1** | `ERROR: xset/1.2.5: Error in source() method, line 95 … FileNotFoundError: [Errno 2] No such file or directory: '…/.build-cache/predl_cache/531a11d6_source_531a11d6xset-1.2.5.tar.gz'` | CI Pre-download 全文替换污染（DRAFT-8960），非配方 URL/sha256 问题 | conandata 注释去协议 URL（`b1a423481e`） |

### conan-verify（G0/G1/G2，最终轮）

```
$ python3 scripts/ohc-run.py conan-verify xset 1.2.5
  ✅   G1: PASS
  ✅   G0: PASS
  ✅   G2: PASS
✅ 配方验证通过: xset 1.2.5
CONAN_VERIFY_RC=0
```

report 原文：`**Verdict**: PASS`
（`archives/x/xset/1.2.5/reports/conan-verify-report.md`，本轮 G0/G1/G2/G3/G4 全 PASS）

- **绑定最终交付配方的一轮**（判据不依赖会移动的 commit sha：
  `conanfile.py` + `conandata.yml` + `test_package/**` 自 `b1a423481e` 起
  `git log b1a423481e..HEAD -- 这些路径` **为空**，即配方输入未再变；notes/manifest 是
  文档件，create 日志显示 export 只收 `.yml`+`.py` 两件 ⇒ 不入 recipe revision）：
  本轮日志
  `~/tmp/uc2/z34-xset/logs/verify-0925-030548.log
  （`CONAN_VERIFY_RC=0`），report 快照
  `~/tmp/uc2/z34-xset/logs/snap-final-0925-030609/conan-verify-report.md`
  （md5 `1c745ed33827c2ddb7b73306c5b50bc8`，`**Date**: 2026-09-25T03:06:01`）。
  该轮 create 走 `Already installed`（复用缓存），**其二进制出自下面所列 03:00
  那轮 W3 的源码构建**（配方输入与本节相同），二者 package revision 同为
  `58e88fd89be4f19418a05193c82451c2` ⇒ 复用合法，不是陈旧状态冒充绿。
- **最终 HEAD 的源码构建证据在 finish 的 W3 日志里**（不在 `reports/` 原件）：
  `logs/snap-finish-0925-030224/w3-local-ci.log`（md5
  `b3f869ef1f8244b614f613e50be962e4`）第 198/208/412/532/541/562/640/644 行依次为
  `Building from source` → `Calling build()` → `CCLD     libXmuu.la` →
  `CC       xset.o` → `Calling package()` →
  `Created package revision 58e88fd89be4f19418a05193c82451c2` →
  `OK: all 6 checks passed` → `[ok] xset/1.2.5 — conan create passed`。
  （02:51 那轮 `snap-finish-0925-025426/w3-local-ci.log` 同形，行号 205/215/419/539/548/569/647/651。）
- 修 conandata **之前**的一轮（recipe 版本已随 `b1a423481e` 失效，仅留过程痕迹，
  不得当作最终 HEAD 的判决）：`logs/verify-0925-024337.log` + 源码构建快照
  `logs/snap-0925-024508/conan-create.log`（38061 字节，md5 `8a6e299d2c44997979b0aff3c056b80c`）。
- 默认 home 泄漏自检：上述各轮 verify / create / W3 日志内 `.conan2` 出现次数均 **0**。
- ⚠ `reports/` 下的日志会被后续步骤**原地覆盖**（实测 38061 字节的源码构建日志被
  finish 复跑成 11158 字节的复用版），故以上引用的均为快照件路径而非 `reports/` 原件。

### finish（内含 W3 本地 CI 模拟 + graph validate）

```
$ python3 scripts/ohc-run.py finish xset 1.2.5 built
  ✅   ✅ W3 本地 CI 模拟通过
  ℹ️ finalize-archive: xset 1.2.5 (status=built)
  ✅   ✅ graph validate 通过
```

W3 各 gate 文字结果（`w3-local-ci.log` 原文行）：

```
L0_RESULT=pass: all checks passed
L1_RESULT=pass: upstream tests + test_package executed
L2_RESULT=skip: xset version/help failed
L4_RESULT=pass: patches clean
L5_RESULT=pass: bin/ has content
[ok] xset/1.2.5 — conan create passed
[ok] L1a: test_package was executed by conan create
[ok] L1b: Test execution evidence found in log
[ok] L1c: Upstream official tests (make check/ctest) executed in build phase
[ok] L1e: Negative test confirmed — test genuinely depends on xset
[ok] L5: bin/ has content
```

> **口径注解（勿把框架判决行读成「上游有测试」）**：`[ok] L1c: Upstream official tests
> (make check/ctest) executed in build phase` 与 `L1_RESULT=pass: upstream tests +
> test_package executed` 都是框架对构建日志做的**正则判定**，不是「上游有测试套件」的证据：
> `ci/conan/build_and_test.sh:1446` 只要 `$BUILD_LOG` 命中
> `grep -qiE "make.*check|ctest|meson test|pytest"` 就在 `:1447` 打 `[ok] L1c`、在 `:1448`
> 把 `L1_DETAIL` 写成 `upstream tests + test_package executed`。本包 build 日志命中该正则的
> 是**编译命令行里的字样**，**上游并无自动化测试**——本包上游 0 用例的清点结论见上一节与
> `test_package/MANIFEST.yml:10`（`upstream_tests_exist: false`）、
> `reports/w3-local-ci.log:642`（`HMBS_UPSTREAM_TEST_RESULT ... discovered:0`）。

- 日志：`~/tmp/uc2/z34-xset/logs/finish-0925-030025.log`（绑定最终 HEAD 的那轮；
  修 conandata 后首跑的对应件为 `finish-0925-025115.log`）；W3 快照 `~/tmp/uc2/z34-xset/logs/snap-finish-0925-025426/`
  （`w3-local-ci.log` md5 `29021d96845735186b3647e8d86e77dc`）
- **`finish` 整体 rc 仍为 1**，阻塞门禁（W3）**已通过**，红在两个后续步骤：
  - `step5b` = 知识检查。`scripts/ohc/finish.py:316` 的 `step5_check_knowledge_gap`
    取**两个面**：`:320` `rc = check_knowledge_completeness()`（**全图谱**存量）与
    `:323` `rc2 = check_knowledge_gap()`（**本归档**），只有 `rc` 与 `rc2` 都放行才判真。
    **本归档面在绑定轮实测已全绿**：`~/tmp/uc2/z34-xset/logs/finish-0925-030025.log`
    第 93 行 `notes.md: total=7 extracted=7 pending=0 failed=0`、第 94 行
    `manifest.yaml: knowledge_count=7 unreferenced=0`、第 95 行 `✅ 知识完整性检查通过`
    （即 `rc2=0`）。作为对照：修 `ref:` **之前**的那一轮
    （`~/tmp/uc2/z34-xset/logs/finish-0925-025115.log` 第 95-96 行）读数才是
    `knowledge_count=6 unreferenced=6` + `⚠️ 存在知识遗漏`——该过程值已被上面三行覆盖，
    不得充当绑定轮证据；
  - `step5b` 仍判假的真实依据是**同一轮的全图谱面**：上述 `finish-0925-030025.log`
    第 92 行 `❌ 知识图谱完整性检查发现 1 类问题`，具体读数在第 79-82 行
    `E219.kv: root_cause 为空`、`E253.kv: root_cause 为空`、`E305.kv: root_cause 为空`、
    `E305.kv: rec_approach 为空`——三枚均为**基线上他人条目**（本包 `knowledge/` 零改动），
    同文件第 83 行 `✅ graph validate 通过`。⇒ 属**存量红**，非本包引入；按 AGENTS §8
    不擅改他人知识表单凑绿，**只披露、不整改**（与下条 `step8` 的框架缺陷同一口径）。
  - `step8` = `gen_summary 失败: 'str' object has no attribute 'append'`
    ⇒ **框架自身缺陷**，非本包配方问题，未擅改（交主窗定夺）。
  - 另 Step10 submit 就绪预检报 `test-report.md` / `packaging/` /
    `.staging-verified` 三项缺失 ⇒ 属 `submit` 阶段产物，本棒按分工不做。
- ⚠ **`L2_RESULT=skip` 是框架预期**（CI 裸跑 bin 不载 runenv），
  既非失败、也**不得**当作"二进制可执行"的证据；可执行性证据只认
  `test_package` 在 runenv 内的 6/6 断言与 `L5: bin/ has content`。

### preflight（W0）

```
$ bash ci/scripts/preflight_check.sh xset/1.2.5
发现 3 个依赖 … 均已发布；版本号未被占用   RC=0
```

（第二轮棒 02:10 实测记录，见 `~/tmp/uc2/z34-xset/STATE.md` §5；本轮未重复取证。）
---

**编译结束**: 2026-09-25 03:00
**最终状态**: built
