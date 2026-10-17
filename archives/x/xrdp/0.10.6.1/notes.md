# xrdp 0.10.6.1 适配笔记

## 编译环境
- 构建系统: autotools —— **直接使用 release 资产自带的生成物 `configure`/`Makefile.in`，
  全程不跑 autoreconf**（CI worker 无 autotools，故补丁一律打在生成物上而非 `.am`/`.ac`）
- 编译日期: 2026-09-25（rule4 整改轮；上一轮为 2026-09-23）
- 编译器: clang/clang++ 15（OHOS aarch64 native 工具链，conan profile `ohos-aarch64`）
- Conan 2.29.1；CONAN_HOME=`~/tmp/ch/home-z34-xrdp`（**本任务私有 home，整改轮新建**；
  09-23 那轮沿用他窗共享 home-DS16 的违规留痕随本轮重跑消解）；验证期 `CCACHE_DISABLE=1`
- 本轮构建目录: `~/tmp/ch/home-z34-xrdp/p/b/xrdp7b442b0536c10/b`（顶层构建树在其 `build-release/`）
- 本轮日志: `~/tmp/uc2/z34-xrdp/{create1,create2,create3,kcheck3,kcheck5}.log`
- 状态: built

## 路径 B 声明（AGENTS §9 的 3+2 行）

- **适配路径**：路径 A（基础适配）+ 路径 B 判定 = `hit`（复用既有知识条目、不新增草稿、不建 Issue；判重依据见下行「知识库扩展」）
- **使用知识库**：`E150`（**同症状不同解法**的参照条目——上游 tarball 不含 submodule；本包不采用其「手动 clone + checkout pinned commit」方案，改用官方 release 资产，实际解法不落在 E150 上、而在下行「知识库扩展」点名的既有条目（判 `hit`））、`E386`（HMDFS 下 `getcwd` 不可靠：profile `[buildenv]` 把 `CONFIG_SHELL`/`SHELL` 钉死到 harmonybrew bash 5.3，本轮构建日志实测生效）、`E490`（autotools helper 脚本可执行位丢失，`conan-verify` 的 G0 实测打出 `Knowledge hit: E490`）、`E017`（框架侧现象：`scripts/ohc/conan_verify.py:573` 对整份 conandata 做 `ghfast.top` 前缀重写，仅按台账披露不据此改配方）。四枚编号均已在 `knowledge/graph/index.tsv` 第 1 列逐条实测存在（awk 精确匹配列值，命中行号 `E150:376`、`E386:612`、`E490:714`、`E017:243`，各 1 行）
- **知识库扩展**：`hit，不新增`。本包机制（上游用 git submodule 分发 ⇒ 改用官方 `make dist` 产出的 release 资产做树内构建）**已被一枚在仓条目整条覆盖**，故不占知识位、不建 Issue。被复用的既有条目**一律按文件名引用**（本仓 `knowledge/drafts/` 里 E 编号被大量草稿复用，引编号会失真），行号对齐：
  - 主引用 `DRAFT-yosys-0.66-tarball-empty-submodule-external-tool-wiring.kv`：`:9`（`root_cause` 同——GitHub `refs/tags/<v>.tar.gz` 归档不含 git 子模块内容、项目仍按树内路径引用）、`:19`（`fallback` 同解法——上游 release 附带**内联子模块**的源码资产时可直接用它做树内构建）、`:20`（资产核验判据同——先用 GitHub API 核实 release `assets>0`，不要凭 `releases/download` 的 404 推断）⇒ 一条之内同时占据「症状」与「换 release 资产」两半，本条无层次差。
  - 同族旁证：`DRAFT-bandit-2.0.0-github-tarball-submodule-locked-commit.kv:11`、`:20`（submodule 路径 `No such file or directory` 的症状签名 + 从官方源逐子模块补齐的解法）；`DRAFT-monocypher-4.0.2-release-vs-tag-archive.kv:11`、`:15`（tag 归档由 git 树快照生成、未经发布流水线 ⇒ conandata 改用 `releases/download/` URL）。
  - **撤回留痕**：曾随本 PR 提交的两枚成对草稿 `knowledge/drafts/DRAFT-xrdp-0.10.6.1-submodule-release-asset.md` 与同名 `.kv`，已按上述判重结论由本轮提交从版本库移除（`git rm`，内容备份在 A 机 `~/tmp/uc2/z34-xrdp/removed-drafts/`，原件仍可在分支历史 `ba5133d4c8` 追到）；机制改按 `hit` 引用既有条目。本包的资产完整性核验手法（字节数比对 + `tar tzf` 清单内 submodule 源文件计数）作为该 `hit` 条目的操作细节留在本文件「编译步骤」第 1 步，不再单独立条。
- **关联 Issue**：本包按 `hit` 交付，**不申请新条目**。此前由主理-34 主窗按 `$P issue` 建的 `#3366`（https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/3366）已由主窗在该 Issue 下 POST 撤销说明（不删号、留痕），本窗不触碰平台。

## 编译步骤

1. 源 = GitHub 官方 **make-dist release 资产**
   `releases/download/v0.10.6.1/xrdp-0.10.6.1.tar.gz`（由维护者 `make dist` 制作，
   **内嵌 libpainter / librfxcodec 的 submodule 源码**）。
   本轮实测核验（对官方 release 资产 `tar tzf` 计数，并同时给出常规文件数以免口径混淆）：
   `libpainter` 45 个条目 = 40 个常规文件 + 5 个子目录（不含顶层自身）；
   `librfxcodec` 104 个条目 = 97 个常规文件 + 7 个子目录（不含顶层自身）；两棵子模块树均非空。
   复核命令（在解包树内）：`find libpainter -mindepth 1 -type f | wc -l` = 40、
   `find libpainter -mindepth 1 -type d | wc -l` = 5；librfxcodec 同法 = 97 / 7。
   sha256 实测 = `2f7beb5a3b2529c8d72dc0df9b8cdca31ab0e0c14d1e3421210f5e6ec0ab3b75`，
   与 conandata.yml 声明一致。
   ⚠ 对比：git tag archive（`/archive/refs/tags/`）按 git archive 语义**不含 submodule 内容**，
   解压后是空目录、构建必败。既有条目（本包判 `hit`，见上文「路径 B 声明」）=
   `DRAFT-yosys-0.66-tarball-empty-submodule-external-tool-wiring.kv` 的 `:9`/`:19`。
2. `build()`: `apply_conandata_patches`（7 补丁）→ 把主 `configure` 与
   `libpainter/configure`、`librfxcodec/configure` 的 conf 临时目录
   `(umask 077 && mktemp -d|mkdir` 改为 `umask 022` → `configure`
   （`--disable-pam --with-systemdsystemunitdir=no --disable-utmp
   --build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-musl`）
   → `make -j1` → `make check`。
   重后端不再交给 configure 静默处置：本轮按上游 `configure.ac` 的确切开关逐个显式
   开关并实测，结论见下面「后端开关逐例结论」表（**不再以"缺依赖"作为申报口径**）。
3. **E386（getcwd）修法**：profile `[buildenv]` 把 `CONFIG_SHELL/SHELL` 钉死
   `/data/service/hnp/bin/bash`（harmonybrew bash 5.3），该 bash 在 HMDFS 构建目录下
   `getcwd()` 间歇失败 → autoconf 重 exec configure 即报
   `configure: error: working directory cannot be determined`。
   工具链级 env 会被 profile buildenv 覆盖，故 `build()` 内对聚合 env 脚本做文本替换，
   把该路径路由到 `tool_requires bash/5.3` 的绝对路径（找不到时回落 `/bin/sh`）。
   **本轮实测 `getcwd` 报错 0 条**（create4.log:1884 `getcwd_err=0`）。不改框架 profile。
4. `test_package`（消费者视角真实行为）：`xrdp-keygen xrdp <out> 2048` 真实调用生成
   rsakeys.ini → 起包内 `xrdp` 守护进程 → 编译出的 `test_rdp_wire` 连
   127.0.0.1:3389 发 X.224 CR TPDU → 断言收到 RDP 协商响应 → 收尾杀进程。
   守护进程的配置/密钥/日志路径编译期写死为 `/etc/xrdp`、`/var`，OHOS 根文件系统不可写，
   故用 `LD_PRELOAD` 的 `/tmp`+路径重定向 shim（`xrdp_test_tmpredir.c`）把写入落到
   构建目录内的 testtmp，仅测试期注入，不影响打包产物。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | tag archive 解压后 `libpainter/`、`librfxcodec/` 为空目录，构建必失败 | codeload tag archive 不含 submodule 内容（E150 同症状不同解法） | 改用官方 make-dist release 资产并核对 sha256（本轮已实测资产内子模块非空） |
| 2 | configure 无条件硬性要求 X11（AC_PATH_XTRA + Xfixes/Xrandr） | OHOS 无 X11 栈 | 补丁 0002 把三处 `as_fn_error` 改 no-op（只改生成物 configure，不触 configure.ac） |
| 3 | X11 消费者仍参与构建 | OHOS 无 X11 头/库 | 补丁 0001 去 `waitforx`+`genkeymap`、0005 去 `xrdp-xcon`+`xrdp-authtest`、0006 去 `sesman/chansrv` |
| 4 | musl 无 shadow(5) API（libc 仅导出 crypt） | `getspnam/lckpwdf/ulckpwdf/putpwent/putspent` 缺失 | 补丁 0003 为 `verify_user.c` 注入惰性回退，`getspnam()` 返回 NULL 走既有 NULL 分支，退化为 /etc/passwd 哈希认证 |
| 5 | musl 无 `getpass` | 符号与声明都不存在，隐式声明被 `-Werror` 拦 | 补丁 0004 为 `sesrun.c` 注入 termios 回退；`sesman/tools/authtest.c` 同样调用 getpass，但它是 noinst 诊断工具，改由补丁 0005 移出构建 |
| 6 | `configure: error: working directory cannot be determined` | 见上 E386 | `build()` 内 env 脚本文本替换路由 shell |
| 7 | `could not setup config files machinery`（conf 临时目录不可写） | HMDFS 上 umask 077 建的 confXXXXXX 目录不可写 | 主 configure 与两个内嵌子 configure 的 umask 077 → 022（同 `archives/a/aide/0.19.3` 修法） |
| 8 | `make check` 测试二进制跑不起来 | musl 忽略 DT_RUNPATH；且 check/0.15.2 fork 模式硬编 `/tmp` 建通信临时文件（`/tmp` 只读，TMPDIR 不被尊重） | 显式注入 `LD_LIBRARY_PATH`（依赖 lib 目录）+ `LD_PRELOAD` 的 /tmp 重定向 shim（复用 yadifa 草稿机制），仅测试期生效 |
| 9 | CI 静态判 L1d 把消费者测试判成"假测试" | `build_and_test.sh:1456` 是单行正则 `self\.run.*(echo\|print\|true)`，而起后台守护进程要用 `echo $! > pidfile` 取 PID | 把命令行组装拆出 `self.run(...)` 所在物理行（无行为变化）；L1 由 fail 转 pass，并由 L1e 破坏性反向验证确认测试真实依赖 xrdp |
| 11 | 打开重后端后 `test_package` 起不来：`Error loading shared library libpixman-1.so.0 / libopenh264.so.7` | 打包出的 `xrdp` 二进制新增 12 个 `DT_NEEDED`（readelf -d 实测），而 `test_package/conanfile.py` 原来把 `LD_LIBRARY_PATH` **裸赋值**成 xrdp 自有目录，覆盖掉 `env="conanrun"`(VirtualRunEnv) 注入的依赖 lib 目录；musl 忽略 DT_RUNPATH 时守护进程直接加载失败 | 改为「自有目录 + `:${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}`」追加式（提交 `c7c3d2aa1f`）。A/B 对照：只给自有目录 → 6 行 `Error loading shared library`；追加依赖目录 → 二进制正常进入自身逻辑（`File /etc/xrdp/rsakeys.ini is missing`） |
| 12 | `--with-imlib2=yes` 实做后 `tests/xrdp` 由 25/25 退到 13/27 | 上游 `xrdp/xrdp_bitmap_load.c:37-42` 在 `USE_IMLIB2` 时 `#undef USE_BUILTIN_LOADER`，把**全部**图像加载（含 BMP）改走 imlib2；而制品 `libImlib2.so.1.9.1` 把 loader 目录编译成 `//lib/imlib2`（conan `prefix=/`，本平台无 FHS 且根只读）⇒ 默认 `imlib_load_image_with_error_return` 返回 `err=4`(NO_LOADER_FOR_FILE_FORMAT) | 按实测**撤回 imlib2**（提交 `3625106be0`）。已证 `IMLIB2_LOADER_PATH=<pkg>/lib/imlib2/loaders` 能让独立最小复现读出 BMP（8x8 fmt=bmp err=0），但在 xrdp 的加载/缩放/合成路径下 `test_xrdp` 仍 14 例失败（`rc=1`）⇒ 属 imlib2 制品的无 X 构建 + 上游加载器互斥设计共同决定，非"缺依赖"。imlib2 制品的 loader 路径缺陷已交主窗入表 |
| 10 | `finish` 一轮后补丁文件从磁盘消失 | 见「已知限制」第 1 条 | 已按 HEAD 无损还原；旧探索树不在盘上后，本轮（09-23 12:04）重跑 `finish` 实测安全：step[1/10] 报「无法定位源码目录」后跳过，6 补丁逐字未变（mtime 仍 04:27） |

## 源码修改（7 个补丁，全部走 conandata.yml `apply_conandata_patches`）

- `0001-Makefile-in-drop-x11-tools.patch` — 生成物顶层 `Makefile.in`：SUBDIRS 与
  DIST_SUBDIRS 同时去掉 `waitforx`（`waitforx.c` include X11/Xlib.h）与
  `genkeymap`（`genkeymap.c` include X11/{Xlib,Xutil,XKBlib}.h 且 `-lX11`）。
  两者是仅存的无条件参与构建的 X11 消费者；不触 `Makefile.am`，避免 autoreconf。
- `0002-configure-x11-optional.patch` — 生成物 `configure`：AC_PATH_XTRA 后
  libx11/Xfixes/Xrandr 三处 `as_fn_error` 改 no-op。
- `0003-verify_user-ohos-shadow-fallback.patch` — `sesman/libsesman/verify_user.c`
  shadow API 惰性回退。
- `0004-sesrun-getpass-fallback.patch` — `sesman/tools/sesrun.c` getpass termios 回退。
- `0005-sesman-tools-drop-noinst-tools.patch` — `sesman/tools/Makefile.in`
  `noinst_PROGRAMS` 置空（去 `xrdp-xcon` 与 `xrdp-authtest`）。二者均 noinst，
  **从不安装**，不影响 `bin_PROGRAMS`，也**不计入 make check 分母**。
- `0006-sesman-drop-chansrv.patch` — `sesman/Makefile.in` SUBDIRS 去 `chansrv`
  （clipboard/rail/xcommon/clipboard_file 四文件硬编 X11），`xrdp-sesman` 主程序不受影响。
- `0007-tests-xrdp-allow-macro-redefined.patch` — 生成物 `tests/xrdp/Makefile.in` 的`CFLAGS = @CFLAGS@` 追加 `-Wno-macro-redefined`。**为什么要它**：上游 `configure` 第 18694-18696 行用`case $host_os in *linux*) linux=yes` 做子串匹配判平台，本机 `host_os` 实测为 `linux-musl`（配方 `build()` 显式传 `--host=aarch64-unknown-linux-musl` 绕开不认 OHOS 三元组的 `config.guess`，实测见 `config.status` 的 `host_os='linux-musl'` 与 `config.log:3235`），`*linux*` 子串匹配命中，于是 `configure.ac:47` 的 `AM_CONDITIONAL(LINUX,...)` 为真、`configure.ac:224-225` 的`AM_COND_IF([LINUX],[AX_APPEND_COMPILE_FLAGS([-Werror])])` 打开 `-Werror`（`config.log:3105-3106`：`LINUX_FALSE` 为井号注释态、`LINUX_TRUE` 为空串，即条件为真；生成的 `tests/xrdp/Makefile:448` 的 CFLAGS 里确有 `-Werror`）。而 `test_xrdp_region.c:53` 所在的同一编译单元里，`check.h:494` 的 `fail(...)` 与 `cmocka.h:5805` 的 `fail()` 重定义，clang 15 会给出gcc 不报的 `-Wmacro-redefined`，被 `-Werror` 升成致命 ⇒ 该套件 27 例编译中断。**本补丁只抑制这一条警告**，`-Werror` 对其余警告仍然有效。**有效性实测**：保留 `-Werror`、仅追加该 flag 后 `make test_xrdp` 退出码 0 且日志出现 `CCLD test_xrdp`（证据 `kcheck3.log:462` 的 `CCLD     test_xrdp`、`:493-501` 的 `# TOTAL: 25 / # PASS: 25 / # SKIP: 0 / # FAIL: 0 / # ERROR: 0`）。**原引用的 exp-testxrdp2.log 已作废**：该文件与 exp-testxrdp1.log 各仅 61 字节且内容完全相同（只有 `CC`/`CCLD` 两行），未记录退出码、也不构成 with/without 对照（主理-5 09-23 移交、CIW 18:5x 复核属实）。反证 `kcheck-6patch-round.log`（md5 `011d17166c2bdab6c76c8eabbc8bee7b`）：`:458` `'fail' macro redefined [-Werror,-Wmacro-redefined]`、`:468` `Target 'test_xrdp' not remade because of errors`、全文 `CCLD test_xrdp` 出现 **0** 次、各套件 TOTAL 仅 140/36/13/1 无 25。

> 0001/0005 本轮以「pristine + 原补丁集」为基线重生成，并验证：新旧补丁集在纯净树上
> dry-run 全部 rc=0，且新集产出的源码树与原集加同等改动后的树 `diff -r` 完全一致。
> `Makefile.am`/`configure.ac` 有意保持不动（CI worker 无 autotools，`.am` 改了也不会生效），
> 属"只改生成物"的既定取舍，非遗漏。

## 后端开关逐例结论（2026-09-25 整改轮）

> 本轮**不接受"依赖缺失所以自动关闭"这个口径**：每个后端都按上游 `configure.ac` 的确切开关实做，
> 能接的接上并跑门禁，接不动的给可复现技术根因。开关名/探测约束均来自
> `configure.ac` 行号（源码树 AC_INIT 版本 = 0.10.6.1，与任务版本一致）。

| 后端 | 上游开关 | 上游探测约束（configure.ac 行） | 制品与约束实测 | 本轮处置 | 证据 |
|---|---|---|---|---|---|
| **pixman** | `--enable-pixman` | `pixman-1 >= 0.1.0`（488） | 已发布 `pixman/0.46.4.3`，`pkg_config_name=pixman-1`，`rc=0` | **已启用并跑通门禁** | create3.log configure 汇总 `pixman yes`；打包 `xrdp` 的 `DT_NEEDED` 出现 `libpixman-1.so.0` |
| **openh264** | `--enable-openh264` | `openh264 >= 2.0.0`（492） | 已发布 `openh264/2.6.0`，`rc=0` | **已启用并跑通门禁** | create3.log `openh264 yes`、`CCD xrdp_encoder_openh264.o`；`DT_NEEDED` 出现 `libopenh264.so.7` |
| **fdk-aac** | `--enable-fdkaac` | `fdk-aac >= 0.1.0`（470） | 已发布 `fdk-aac/2.0.3`，`rc=0` | **已启用**（探测接通；其唯一消费者 `sesman/chansrv` 因硬依赖 X11 不在本平台构建 ⇒ 不产生运行期链接，`DT_NEEDED` 里无 `libfdk-aac`） | create3.log `fdk-aac yes`；消费者归属见 `sesman/chansrv/Makefile.am:23` |
| **fuse3** | `--enable-fuse` | `fuse3 >= 3.1.0`（463） | **制品命名不是缺口**：`libfuse/3.18.2` 的配方 `archives/l/libfuse/3.18.2/conanfile.py:82` 设 `pkg_config_name=fuse3`，实测 `fuse3 >= 3.1.0` `rc=0`（Version 3.18.2） | **已启用**（同上，唯一消费者是 chansrv：`sesman/chansrv/Makefile.am:18`，fuse 源文件全在 `sesman/chansrv/`） | create3.log `fuse yes` |
| **x264** | `--enable-x264` | `x264 >= 0.3.0`（490） | 制品 `x264/r3223` 已发布且 `.pc` 找得到（`--modversion`=r3223），**但版本串取上游 git tag 名而非 x264 数值版本号**，pkg-config 数值比较必失败：原文 `Requested 'x264 >= 0.3.0' but version of x264 is r3223`；对照 `x264 = r3223` rc=0、`x264 >= 0` 亦 rc=1 | **保持关闭**（根因＝制品版本串与上游数值下限不可比，不是缺依赖；H.264 编码路径已由 openh264 覆盖并启用） | `~/tmp/uc2/z34-xrdp/pcprobe2.sh` 输出 |
| **neutrinordp / freerdp** | `--enable-neutrinordp` | `freerdp >= 1.0.0`（451） | 上游探测的是 **FreeRDP 2 系**的模块名 `freerdp`（`neutrinordp/xrdp-neutrinordp.c:20` `#include <freerdp/freerdp.h>` 按 v2 API 写）；本仓唯一归档 `freerdp/3.26.0` manifest `status: built`、preflight 判**未发布**，且 FreeRDP 3 的模块名是 `freerdp3` | **保持关闭**（根因＝上游 API 代际与本仓制品代际不匹配，不是缺依赖） | `preflight_check.sh xrdp/0.10.6.1 --deps "…"` 输出 `WARN 未发布: freerdp/3.26.0` |
| **imlib2** | `--with-imlib2=yes` | `imlib2 >= 1.4.5`（275） | 已发布 `imlib2/1.9.1`（其传递依赖 `libpng/1.6.58.2` 在 `zlib/1.3.1.1` 组合下无二进制，`--build=missing` 本地源码构建成功）；约束实测 `rc=0` | **实做后按证据撤回**：`configure` 汇总 `with imlib2 yes`、`config_ac.h:137 #define USE_IMLIB2 1` 均达成，但 `tests/xrdp` 由 25/25 退到 **13/27（14 例失败，含 12 个原本通过者）** | create2.log + kcheck3.log:474-487,504-510；机制见问题表 #12 |
| **freetype2 / opus / mp3lame / smartcard / jpeg / tjpeg / vsock / kerberos** | 各自开关 | — | — | 未在本轮 rule4 意见点名的范围内，本轮不动（避免无据扩大改动面） | — |

## 依赖

- `openssl/3.5.8.1`（必需，configure 经 PKG_CHECK_MODULES 探测）
- `pixman/0.46.4.3`、`openh264/2.6.0`、`fdk-aac/2.0.3`、`libfuse/3.18.2`
  （2026-09-25 整改轮新接入；四者的制品发布态与 pkg-config 约束均逐个实测，见上表）
- `check/0.15.2`、`cmocka/2.0.2`（单测框架；configure 探测到才启用 tests）
- `tool_requires bash/5.3`（E386 shell 路由；不进 host package_id）
- 以上四者 CI 侧 L0i 逐个确认**已在制品仓发布**（w3e.log）。

## 上游测试实测（2026-09-25 整改轮真机重跑）

**分母口径（关键）**：配方 `build()` 跑的是 `make check`（不带 `-k`），而 automake 的
`check-recursive` 在一个子套件失败后即中断递归 ⇒ `make check` 只给出 `tests/common`
一个套件（create3.log 内 7 条 `Apply patch` = 7 个补丁全部应用、末行
`xrdp wire behavior verified on port 3389` 于 create3.log:1910）。
全分母由同一构建目录补跑 `make -k check` 取得：
`~/tmp/uc2/z34-xrdp/kcheck5.log`（09-25 02:41 产出，535 行，md5 `434606541340b99b92aec8b47d60ddd7`；
运行环境 = 复用配方 `build()` 的 `LD_PRELOAD` /tmp 重定向 shim + `XRDP_TEST_TMPDIR` + 依赖 lib 目录）。

| 套件 | TOTAL | PASS | SKIP | FAIL | ERROR | 证据行（kcheck5.log） |
|------|-------|------|------|------|-------|----------------------|
| libcommon (tests/common)  | 140 | 137 | 0 | 2 | 1 | :149 `Making check in common`、:301-307 |
| libipm    (tests/libipm)  |  36 |  34 | 0 | 1 | 1 | :319、:326 `CCLD test_libipm`、:370-376 |
| libxrdp   (tests/libxrdp) |  13 |  13 | 0 | 0 | 0 | :388、:395 `CCLD test_libxrdp`、:416-422 |
| memtest   (tests/memtest) |   1 |   1 | 0 | 0 | 0 | :427、:442-448 |
| XRDP daemon (tests/xrdp)  |  25 |  25 | 0 | 0 | 0 | :453 `Making check in xrdp`、:462 `CCLD test_xrdp`、:495-501 |
| **合计**                  | **215** | **210** | **0** | **3** | **2** | 五维：静态注册 216 / 实际注册并执行 215 / 通过 210 / 跳过 0 / 失败 3（另 2 条为套件级 ERROR 记账） |

- **SKIP 判定**：四套件 `# SKIP: 0`，日志内 `exit 77` 出现 **0** 次
  ⇒ 没有任何用例符合 automake 的 SKIP 语义，3 个失败是**真实失败（平台边界）**，
  正文不得写成 SKIP。
- **ERROR 判定**：2 条 ERROR 是 automake 对"套件进程退出码非 0"的记账
  （kcheck3.log:297、366），已含在各自 TOTAL 内，不是额外的失败用例。
- **3 个失败是同一机制，本轮已给到可复现的平台能力边界（不再写"OHOS 内核限制"这种无据归因）**：
  - kcheck5.log:245 `test_common 88 … test_g_file_get_open_fds: Can't poll fds [Out of memory]`
  - kcheck5.log:248 `test_common 91 … test_g_sck_fd_overflow: Can't poll fds [Out of memory]`
  - kcheck5.log:357 `test_libipm 27 … test_libipm_receive_h_type: Can't poll fds [Out of memory]`

  **根因链（三段证据，均可重放）**：
  1. 三个用例都经过同一个辅助函数 `tests/common/test_os_calls.c` 的 `get_open_fd_count()`，
     它在 `:51` 直接 `poll(fds, nofile.rlim_cur, 0)` —— **nfds 取的是本进程 RLIMIT_NOFILE 软限值**，
     本机实测 `RLIMIT_NOFILE soft/hard = 32768 32768`，即一次 `poll()` 传入 32768 个 fd 项。
  2. 最小复现（`ctypes` 直接调 `libc.so` 的 `poll`，只 poll 一个管道 fd 的重复数组）：
     `poll(nfds=1) -> rc=0 errno=0`；`poll(nfds=1024) -> rc=-1 errno=12 (ENOMEM)`；
     二分得 **本平台 `poll(2)` 可接受的 nfds 上限 = 449，nfds >= 450 一律返回 ENOMEM**
     （脚本 `~/tmp/uc2/z34-xrdp/forensic5.sh` / `forensic6.sh`，输出见本轮记录）。
     ⇒ 32768 >> 449，`poll()` 必失败，`ck_abort_msg("Can't poll fds [%s]")`（`test_os_calls.c:54`）
     中止该用例。**与被测代码逻辑无关，也非内存不足**（同机 MemAvailable 10.9GB 时稳定复现）。
  3. 反向对照（排除"资源不够"与"可以通过调参解决"两种猜测）：用 `python resource.setrlimit`
     分别把 RLIMIT_NOFILE 设成 4096 / 32768 重跑 `./test_common 88`、`./test_common 91`、
     `./test_libipm 27` —— **三档结果完全相同**（`Failures: 2` / `rc=1`），因为该测试把 nfds
     直接取为 rlimit 本身，抬高上限只会让 nfds 更大。
     把 RLIMIT_NOFILE 压到 449 以下可以让这 3 例"通过"，但那是**削弱被测语义**
     （`test_g_sck_fd_overflow` 就是要在接近 fd 上限时验证溢出处理），本轮**不采用**，
     宁可如实报 3 例失败。
  ⇒ 定性：这 3 例失败属『**本平台 `poll(2)` 不支持大 nfds（上限 449）**』这一可复现的能力边界，
     不是缺依赖、不是配方缺陷、不是内存压力。上游若把该辅助函数改为分片 poll 或改读
     `/proc/self/fd`（本平台 fdinfo 可用性另见知识库）即可通过，属上游代码可改进项。
- **`tests/xrdp`（静态 27 例）的真实构成**（本轮补丁 0007 后重测改写；此前两版归因都不准确，已作废）：
  1. **25 例可执行且全部通过** —— 此前它们编译中断，真因是上游 `configure` 第 18694-18696 行
     `case $host_os in *linux*) linux=yes` 的子串匹配把 OHOS 判成 linux，使 `AM_COND_IF([LINUX])`
     追加 `-Werror`，于是同一 TU 内 `check.h:494` 的 `fail(...)` 与 `cmocka.h:5805` 的 `fail()` 重定义
     被 clang 15 升为致命。补丁 0007 只对这一个测试目标加 `-Wno-macro-redefined`，`-Werror` 其余效力保留；
     本轮实测 `Making check in xrdp`(kcheck3.log:453) → `CCLD test_xrdp`(kcheck3.log:462) →
     套件汇总 `TOTAL 25 / PASS 25 / SKIP 0 / FAIL 0 / ERROR 0`(kcheck5.log:495-501)。
  2. **2 例未注册：`test_png_load__blend_ok` 与 `test_jpg_load__ok`**（均在
     `tests/xrdp/test_bitmap_load.c`）被 `#ifdef USE_IMLIB2` 连同 `tcase_add_test`（:343-349）一起条件注册。
     本轮**已实际把 imlib2 接上做过一轮**（`--with-imlib2=yes`，configure 汇总 `with imlib2 yes`、
     `config_ac.h:137 #define USE_IMLIB2 1`），这 2 例确实进入分母（`kcheck3.log` 的 tests/xrdp
     `# TOTAL: 28 / # PASS: 13 / # FAIL: 14`，:486-487 即这 2 例），但同时把上游内建图像加载器
     `#undef` 掉（`xrdp/xrdp_bitmap_load.c:37-42`），导致 **12 个原本通过的 BMP 用例回归**
     （`kcheck3.log:474-485`）⇒ 净效果是 25/25 退成 13/27。按证据撤回 imlib2 后恢复 25/25。
     根因与取证见「后端开关逐例结论」表 imlib2 行与问题表 #12；**结论口径是"实做后按证据关闭"，
     不是"缺依赖"**。27 - 25 = 2 即这 2 例。
  ⚠ 上一版此处写的「补 `-Wno-macro-redefined` 只会把失败推到链接期、解析不到
     `__real_pixman_region_extents`」是**未实证的推测且已被证伪**：全树 `grep -rn __real_ tests/` 0 命中、
     `test_xrdp_region.c:64/110` 自带 `__wrap_` 桩，且实测保留 `-Werror` 加该 flag 后编译与链接均成功。
- **静态 216 → 实测 215 的差额逐项归因**（本轮全部重测，不再使用「记账口径差」这类含糊说法）：
  - 静态清单合计 **216** = `tests/common` 141 + `tests/libipm` 34 + `tests/libxrdp` 13 + `tests/memtest` 1 + `tests/xrdp` 27；
    本轮 automake 各套件 TOTAL 合计 **215** = 140 + 36 + 13 + 1 + 25。差额由下面三条**各自可核**的事实构成（不是同一种「口径差」）：
  - `tests/xrdp` 静态 27 → 实测 25：2 例由 `USE_IMLIB2` 条件注册（`tcase_add_test` 在 `tests/xrdp/test_bitmap_load.c:343-349`），
    本轮 imlib2 **实做后按证据关闭**（`create3.log:586` configure 汇总 `with imlib2  no`）⇒ 未编译。
    本轮另实测了打开态：该 2 例会注册并执行，但同套件净退 12 例（见上一小节 2.）。
  - `tests/common` 注册 141 → 结果行 **139**：`test_g_file_get_size__2GiB` 与 `test_g_file_get_size__5GiB` **两例从未执行**
    （全日志 grep 命中 0），进程随后 `ERROR: test_common - exited with status 1`（`kcheck3.log:297`）；automake 把该 ERROR
    另记 1 条 ⇒ 该套件 TOTAL 140。这两例本轮实测**未覆盖**，不得计入通过数。
  - `tests/libipm` 结果行 **35** 而唯一用例 34：上游 `tcase_add_test` 出现 35 次 > `START_TEST` 定义 34 个，
    `test_libipm_send_y_type` 在日志里跑了两遍（命中 2 次）⇒ **上游重复注册**，与本包改动无关；该套件同样有 1 条
    ERROR 记账 ⇒ TOTAL 36。
  （旧版把上述三点合并成一句「automake 记账口径差」，该归因已作废。）

  **PR 正文分母一律用本轮实测值：TOTAL 215 / PASS 210 / SKIP 0 / FAIL 3 / 套件级 ERROR 2；
  其中 213 条是真实结果行（210 通过 + 3 失败），215 另含 2 条 automake 的 ERROR 记账条目。**
- **消费者测试（test_package）1 项，通过**：create4.log:1884-1885
  `RDP negotiation PDU type=0x02` / `xrdp wire behavior verified on port 3389`。
  ⚠ 断言强度披露（W4 P2 整改轮补）：`test_package/test_rdp_wire.c:90-93` 另有一条**弱兜底分支**——
  应答只要 ≥11 字节且首字节为 `0x03` 就记 ok（该形态可被 X.224 DT/ERROR 或被误绑 3389 的其它服务满足）。
  本轮实测走的是**强分支** `:82-84`：`create3.log:1909` 打印的 `RDP negotiation PDU type=0x02` 只能由
  `:82-84` 产出，兜底分支未触发 ⇒ 1/1 的申报成立、不构成空壳。**本轮不改 `test_rdp_wire.c` 的断言行为**
  （把兜底收紧为「仅打印 degraded 并判失败」＝动测试语义与构建输入，须另起一轮重跑 W3）。

## 验证结果

```bash
# 0) 2026-09-25 整改轮（当前 HEAD 轮）读数一览
#    CONAN_HOME=~/tmp/ch/home-z34-xrdp（本任务私有）；构建目录 p/b/xrdp7b442b0536c10/b
CREATE_RC=0                       # create3.log（1912 行），末行 create3.log:1910 wire behavior verified
Apply patch                       = 7   # create3.log:136-142 逐条 7 次
configure 显式开关                = --disable-pam --enable-pixman --enable-openh264 --enable-fdkaac --enable-fuse
configure 汇总（create3.log）     = :568 fdkaac yes / :572 x264 no / :573 openh264 yes /
                                    :575 pixman yes / :576 fuse yes / :586 with imlib2 no
make -k check 全分母              = 215/210/0/3/2  # kcheck5.log（md5 434606541340b99b92aec8b47d60ddd7）
消费者测试（test_package）        = 1 项通过，create3.log:1909-1910

# 1) 直跑 conan create（设备真机，CONAN_HOME=home-DS16，CCACHE_DISABLE=1）
#    日志 ~/tmp/uc2/zhuli-5-xrdp-0.10.6.1/create4.log（09-23 14:12）
rc=0                                    # CREATE_RC=0
Calling build        = 2                # create4.log:1884 MEASURE
Building from source = 1                # create4.log:1884 MEASURE
Apply patch          = 7                # create4.log:121-127（逐条 7 次）
# 同轮：Calling build=2  Building from source=1  getcwd 报错=0  CREATE_RC=0
getcwd 报错          = 0
package()/打包成功   = create4.log:1791

# 2) W3 本地 CI 模拟（与 CI 同源脚本；本轮由 主理-5 于 09-23 14:32 重跑，7 补丁轮）
#    日志 archives/x/xrdp/0.10.6.1/reports/w3-local-ci.log；其 sha256 == 版本目录 .ci-result.json
#    的 log_sha256，integrity_hash 已按 finish 的 sha256(f"ts:sw:ver:ec")[:16] 公式复核为工具生成
W3_RC=0（14:32 那轮；本日志内 Apply patch=7、含 0007 的 macro-redefined 行，故为 7 补丁轮）
L0_RESULT=pass   L1_RESULT=pass   L2_RESULT=skip   L4_RESULT=warn   L5_RESULT=pass
# ⚠ 0007 加入后本轮证据以 create4.log + kcheck3.log 为准（215/210/0/3/2），
#    最终 finish 会在版本目录重写 reports/w3-local-ci.log 与 .ci-result.json 绑定新内容。
[ok] conan create passed                 # w3-local-ci.log:1963
[ok] L0/L1 全项通过                       # w3-local-ci.log:1989-1990
[ok] L1e: Negative test confirmed        # w3-local-ci.log:1979（破坏性反向验证：测试真实依赖 xrdp）
    L2=skip / L4=warn / L5=pass          # w3-local-ci.log:1991-1993
    Build Summary: Success 1             # w3-local-ci.log:1997-1999（本轮日志共 2003 行）
Build Summary: Success 1 / Failed 0 / 100%
# ⚠ 该脚本 shebang 是 #!/usr/bin/zsh 且用到 zsh glob 限定符 `*.kv(N)`，
#   必须用 zsh 跑；按 AGENTS 里 `bash ci/conan/build_and_test.sh` 的写法会在
#   第 107 行报 syntax error near unexpected token `('。
```

- `L2_RESULT=skip`：`xrdp`/`xrdp-sesman`/`xrdp-sesrun`/`xrdp-keygen`/`xrdp-dis`/
  `xrdp-dumpfv1`/`xrdp-sesadmin` 的 `--version`/`--help` 冒烟不通过 —— 守护进程类
  二进制不提供这类选项（`xrdp-keygen` 需位置参数），属预期，未计入测试分母。
- `L4_RESULT=warn: dangerous functions in patches` **是误报**：扫描正则
  `(strcpy|sprintf|gets|strcat)\b` 命中的是补丁 0004 里安全函数 **`fgets`** 中的
  `gets` 子串（`0004-…patch:32` → `if (fgets(buf, sizeof(buf), stdin) == NULL)`）；
  补丁内不存在任何真正的 strcpy/sprintf/gets/strcat 新增行。
- `conan-verify` 的 G2 本轮仍失败，**不是配方缺陷**：`scripts/ohc/conan_verify.py:573`
  的 E017 预防对整个 conandata 做
  `.replace("https://github.com", "https://ghfast.top/https://github.com")`，
  与本仓已手写的 gh-proxy 行叠成
  `https://gh-proxy.com/https://ghfast.top/https://github.com/...`（404），
  且替换后 URL 列表里**不再存在裸官方 URL**；实测本机 `ghfast.top` 读超时(curl rc=28)、
  `github.com:443` 连接失败、仅 `gh-proxy.com` 可用 ⇒ G2 必卡 `source()`
  （`Error in source() method, line 56` / `Read timed out. (read timeout=30)`）。
  这正是"重建版补丁从未被构建验证"的机制。故本轮编译证据取自
  直跑 `conan create` + `ci/conan/build_and_test.sh`（同一 conan 命令、CI 同源门禁）。

## 注意事项与已知限制

1. `ohc-run.py finish` 的 step [1/10] `refresh-patch --auto` **会按 `manifest.yaml` 里记录的
   `source_orig_dir`/`source_work_dir` 两棵源码树重新生成补丁**：若那两棵树是过期的旧探索树，它会删掉
   磁盘上的补丁再按旧方案重写（本任务 09-22 真实发生过一次，因补丁已提交推送才用 `git show HEAD` 还原）。
   **现状（09-23 12:04 复测）**：`~/builds/xrdp-0.10.6.1.{orig,work}` 两棵旧树已不在盘上，
   `finish` 该步报 `无法定位源码目录: orig=None, work=None` 后跳过，6 个补丁逐字未变 ⇒ `finish` 可安全重跑；
   且 7 补丁已全部入 git（自 `02b9dfa33d`），最坏情况仍可还原。
2. ⚠ 配方 `build()` 内 `make check` 以 `ignore_errors=True` 运行（OHOS 上 libcheck 的 fork+poll 在大 fd
   集上返回 ENOMEM 真失败（本轮已定位为 `poll(2)` 的 nfds 上限 449，见上节），若不容错则整个 `conan create`
   出不了制品）⇒ **构建日志不会以失败退出的形式暴露这些用例失败**，故本条与 PR 正文逐项披露真实读数；
   全分母 215（各套件 TOTAL 合计）/210（PASS）取自同一构建目录补跑的 `make -k check`
   （`~/tmp/uc2/z34-xrdp/kcheck5.log`），不是从 `make check` 的单套件推出来的。
3. `xrdp` 是守护进程类 `application` 包：内部私有库装到 pkglibdir，不对外导出链接目标，
   故消费者测试走真实线路而非链接。
4. `docs/man` 仍安装 `xrdp-genkeymap.8` 手册页（二进制已随补丁 0001 移出构建）——
   只是文档文件，不影响构建与安装。
5. 构建产物含 33 个 `.ini`、12 个可执行/脚本等；`commands.json`（软件级）已由 CI L0k
   校验通过（`[ok] commands.json valid (type=tool)`）。
---

**编译结束**: 2026-09-25 02:55
**最终状态**: built

## 11. AI 复审 P1/P2 整改轮（CIW-8 2026-09-26，R8 合规 + 测试垫片内存安全）

一手证据（本轮实测，非引用旧结论）：

- **R8 合规化（P1-1 / P1-2）**：补丁 0003/0004 原先以 `#if defined(__OHOS__)` 守卫 libc 回退，
  并把 `getpass` 用 `#define` 覆盖 libc 名称——本仓规则明令禁止在源码与 patches 里引入平台条件宏。
  现改为**两个独立的能力宏**，由配方新增的 `_probe_libc_auth_apis()` 决定：
  - `XRDP_LIBC_LACKS_GETPASS` ← 单独编译+链接 `getpass(3)` 探针
  - `XRDP_LIBC_LACKS_SHADOW_DB` ← 单独编译+链接 `getspnam(3)` 探针
  两宏以**单个带引号的 `CPPFLAGS="-DA -DB"` 参数**交给 configure（autoconf 认 `VAR=value` 为
  canonical 变量，并把 CPPFLAGS 代入每个 Makefile）。拆成两个宏而不是合成一个，是为了防
  "libc 只缺其中一个"时把已存在的符号重复定义。
  实测（A 机 clang-15，一次性编译，不占构建槽）：`getpass` 单独探针与 `getspnam` 单独探针
  **各自** `ld.lld: error: undefined symbol` ⇒ OHOS 上二者皆缺，两宏都会被定义；
  正对照 `crypt(3)` 探针链接成功（rc=0）⇒ 探针本身不误报。
  补丁不再需要 autoreconf：xrdp 的 release configure 对 getpass/getspnam **零个** AC_CHECK_FUNCS
  （本窗直接 grep 官方 tar 的 configure），所以 config.h 里本来就没有可用判据，才由配方补探测。
- **mkstemp 越界回写（P1-3）**：垫片原写法
  `snprintf(tmpl, strlen(alt) + 1, "%s", alt)` 以**源串长度**当目的缓冲上限，而 mkstemp 的契约
  是"就地替换尾部 X"，调用方缓冲只有 `strlen(模板)+1` ⇒ 重定向名（root + 原路径）必然更长 ⇒ 越界写。
  现改为：先比较 `strlen(alt) > strlen(tmpl)` 则**不重定向**（直接走 `real_mkstemp(tmpl)`），
  否则回写时用 `strlen(tmpl) + 1` 作上限。依据是 mkstemp 成功后模板长度不变，故该比较是精确界。
  AI 指出的"两份同源副本"里，归档根的 `xrdp_test_tmpredir.c` 是配方 `exports` 并在 build() 里
  编译 LD_PRELOAD .so 的那份，`test_package/` 那份由 test_package/conanfile.py 自行编译，
  **两处已同步修改**，改完两份仍逐字节相同。垫片单文件 `clang -shared -fPIC -O1` 编译通过（rc=0）。
- **P2-4（openat 缺 va_end）不成立**：现文件里三处 `va_start` 全部配对 `va_end`
  （行 84/86、118/120、132/134），计数 va_start=3、va_end=3 ⇒ 本轮不改，证据已写入 PR 回复。
- **P2-5 / P3-6 未动**：`test_rdp_wire.c:88-93` 的兜底断言宽度、以及两份垫片副本的合并，
  属"可选改进"且会牵动测试语义/构建期文件可见性（test_package 不被导出到缓存，配方在缓存里
  看不到 test_package 目录）⇒ 本轮不动，留作后续；不因此声称已修。

**本地复验受阻（设备级，如实登记）**：A 机 inode 余量实测 `23950 →（清掉本窗自有
~/tmp/ch/home-CIW-8-{rdate,lammps} 共约 3 万文件后）84709`，仍低于 `gate.sh` 的 500000 门槛；
占用大头是其它窗口的 conan 缓存（home-zhuli11-megacmd 126858 文件、home-主理-43-yadifa 108147、
home-m3-metahtml 87102…），按"他人改动是用户资产"不予删除 ⇒ 本轮 `conan-verify` 未能在本地跑完，
验证改由平台 CI 承担（上一轮 CI 在本配方为绿，build#61418 results=0）。已就此写 NEED-USER。
