# xrefresh 1.1.0 适配笔记

## 编译环境
- 构建系统: autotools（上游**预生成** configure；本机 `~/usr/local/bin` 里的
  aclocal/automake/automake-1.16/libtool/libtoolize 6 个脚本 shebang 指向
  `~/usr/local/bin/perl`，而 perl 不存在 ⇒ 这些工具全部不可执行，也无法重跑
  autoreconf。补丁只打探测脚本本身，不需要再生成）
- 编译日期: 2026-09-24（适配段构建在 **B 机**；收口段的 `conan-verify` 与本地 W3 模拟在 **A 机**；两者同为 HarmonyOS aarch64 / HongMeng Kernel 1.12.0）
- 编译器: clang（`/data/service/hnp/bin/clang`，LLVM）
- 状态: built（`conan-verify` **B 机与 A 机均通过**（A 机 03:58 那轮的 `✅ conan-verify 通过` 出自 `finish` 的 **Step4「质量验证」**（段内 G1 PASS、G2 `conan create` PASS、G3 系统库隔离 PASS）；⚠ 同轮 **Step3「G0 干净构建验证」实报 `❌ G0: 找不到原始 tarball` 后非阻断放行**，其想验的“干净构建”实质由 Step4 的 G2 与 Step5 的本地 W3 覆盖；另注意 Step4 段内还有一个同名的“G0 预构建风险评估/知识图谱预查询”，与 Step3 的 G0 不是同一件事）；**本地 W3 模拟于 A 机 2026-09-24 04:00 通过**，`.ci-result.json` 读数 exit_code:0 / integrity_hash=734f39f584a0e2e3 / log_sha256=d7a276c35ed144727cea2cd75d121036378e306e10d7b1eab085fe61f4bec539，日志 `reports/w3-local-ci.log`；未 upload）。★首次 W3 尝试（B 机 03:15）**失败**于 JC1 全仓扫描，根因是 finish 跑在配方提交之前，见「注意事项」第 4 条——不是本包缺陷，也不需要改 `ci/`。

## 包本体（实证，不采信台账）
- 语言/规模：单文件 C —— `xrefresh.c`（405 行）+ `man/xrefresh.man`。
- 作用：映射一个全屏 override_redirect 窗口再取消映射，迫使 X server 重绘全部窗口。
- R47 lang-preflight：通过（`milestone=lang_checked`，rc=0）。任务语言与实测一致
  （c↔cpp 兼容族），不触发语言例外。
- 台账声明依赖 `[x11, xproto]` **已被证实**：configure.ac 只有一条
  `PKG_CHECK_MODULES(XREFRESH, [x11 xproto >= 7.0.25])`（第 44 行），模块逐个
  解析得动；**没有 xmu/xmuu/xt**，所以同族 xhost 卡住的那个停手条件（要未发布的
  libXmu 的 xmuu）在 xrefresh 上不成立，也**不需要内建任何第三方源码**。

## 编译步骤
```bash
export PATH="$HOME/.local/bin:$HOME/.harmonybrew/bin:/data/service/hnp/bin:/usr/bin:/bin"
# ⚠ 不要把 ~/usr/local/bin 放进 PATH：见"编译环境"第 3 行，会让 ohc 的
#   check_env._check_cmd 撞上它自己的 `str(e)` NameError 而整体崩掉 init-build。
ohc-run.py init-build xrefresh 1.1.0 --url=<archive 域 URL>   # 见下面的下载坑
source .build-context-xrefresh-1.1.0
cd $BUILD_SRC_DIR
python3 <task>/apply_ohos_guess.py  config.guess       # E007/E160
python3 <task>/apply_ohos_config.py config.sub         # E007/E072/E122
python3 <task>/apply_ohos_configstatus.py configure    # E136
XREFRESH_CFLAGS="-I<libx11>/include -I<xorgproto>/include" \
XREFRESH_LIBS="-L<libx11>/lib -lX11" ./configure --prefix=$DEFAULT_PREFIX   # rc=0
make -j1                                               # rc=0
make install DESTDIR=$TEST_PREFIX                      # bin/xrefresh + share/man/man1/xrefresh.1
```

## 遇到的问题与解决方案

| # | 症状 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `./config.guess[1572]: can't create /storage/.../tmp/cgDGdikH/dummy.c: Permission denied`，随后 `configure: error: cannot guess build type; you must specify one` | GNU config.guess(2023-01-01) 无 HarmonyOS 分支；落入需要编译器探测的路径，而 `set_cc_for_build()` 用 `(umask 077 && mktemp -d "$TMPDIR/cgXXXXXX")` 建的目录在 HMDFS 上落成 `drwx--S---`，创建者自己写不进去 | 在顶层 `case $UNAME_MACHINE:$UNAME_SYSTEM:...` 开头加 `*:HarmonyOS:*:*` 分支直接输出 `aarch64-unknown-linux-ohos`（E007/E160），**顺带短路掉 dummy.c 探测**，不必再改 config.guess 的 umask |
| 2 | config.guess 已能猜出三元组，但 `configure: error: /bin/sh ./config.sub aarch64-unknown-linux-ohos failed`，具体报 `Invalid configuration ...: Kernel 'linux' not known to work with OS 'ohos'` | config.sub(2023-01-21) 三处白名单都不认 ohos | 三处都补（E007+E072+**E122**）：`ohos-linux)` 映射、`gnu* \| android* \| ohos*` OS 白名单、kernel-OS 组合白名单加 `linux-ohos*`。**少第三处必失败**，且前两处补完后的报错文案长得像"config.sub 根本没打补丁"，容易误判为补丁没生效 |
| 3 | `configure: creating ./config.status` 后 `./config.status[784]: can't create ./confgLgppG/subs1.awk: Permission denied` / `config.status: error: could not setup config files machinery` | E136：configure 写进 config.status 的临时目录引导用 `umask 077`，在 SGID（父目录 `drwxrws--x`）下建出的目录 HMDFS 不给创建者写 | 删两处 `umask 077`（**路径形态不动**）；同一枚补丁的第二 hunk 把 `ac_pwd=\`pwd\`` 改成 `pwd` 失败时回退 `$PWD`（HMDFS 会拒绝直接 `getcwd()`，属 **E386** 家族；已合并先例 `archives/x/xeyes/1.3.1/conanfile.py` 用的就是同一条字符串替换） |
| 4 | 直接照抄同族补丁会 hunk 失败 | `archives/x/xvinfo/1.1.5` 的 0001/0002/0003 与 xrefresh 的行号/上下文不同：0001 干净应用，0002 三 hunk 挂两个，0003 整块挂 | 一律按锚点文本重做，最后由 `finish` 的 `refresh-patch --auto` 从 `.orig`↔`.work` 差异重生成补丁（不手抄别人的 .patch） |
| 5 | `ohc-run.py init-build` 下载失败：`<urlopen error [SSL: UNEXPECTED_EOF_WHILE_READING]>` / `RemoteDisconnected` | ohc 自带下载器用裸 urllib，对 xorg 域**间歇性**被链路掐断（换 UA 时好时坏 ⇒ 不是 UA 封锁，是抖动）；同一 URL 用 curl 稳定 200/163767B | 把 curl 下好的包预置到 `$TMPDIR/builds/xrefresh-1.1.0.tar.gz`（init-build 见文件已存在即跳过自己的下载器），并用 `EXPECTED_SHA256` 让它继续校 sha256。**conan 自己的 downloader 同 URL 实测成功**（`conan source` 探针 rc=0 且校验收通过）⇒ `conan create` 不受影响，这只是 ohc 侧的框架摩擦 |
| 6 | 未打补丁前 pkg-config 依赖：`xorgproto` 的 `xproto.pc` 落在 `share/pkgconfig/`（不是 `lib/pkgconfig/`），且 CI worker 未必有可用 pkg-config | — | 走 autoconf/pkg.m4 的**文档化逃逸口**：`XREFRESH_CFLAGS`/`XREFRESH_LIBS` 非空即直接采用、不调用 pkg-config（configure 第 11681/11697 行；实测 `checking for XREFRESH... yes`）。与已合并的 `archives/x/xeyes/1.3.1` 同款 |
| 7 | 运行期 `Error loading shared library libXdmcp.so.6 (needed by libxcb.so.1)` + `Error relocating ... XdmcpWrap: symbol not found`，rc=127 | 闭包漏了一环：libX11.so.6 → libxcb.so.1 → libXau.so.6 + **libXdmcp.so.6**；且已发布 libxcb.so.1 的 RUNPATH 写死构建机 `/storage/.../.conan2/p/...` 绝对路径，换 CONAN_HOME 即失效 | 主配方把 libxcb/libxau/libxdmcp 显式声明为 `run=True` 依赖（conanrun 注入 libdir）+ test_package 用依赖包内 `.so` 绝对路径 `LD_PRELOAD` 兜底（优先实体文件，HMDFS symlink 物化不可靠 E050） |

## 最小复现（任一条都能在鸿蒙 PC 上重演）
```bash
# 问题 1（config.guess + HMDFS dummy.c）
tar xzf xrefresh-1.1.0.tar.gz && cd xrefresh-1.1.0 && ./configure --prefix=/tmp/p
#   → can't create $TMPDIR/cgXXXXXX/dummy.c: Permission denied → cannot guess build type

# 问题 2（config.sub 三处）
sh config.guess                          # aarch64-unknown-linux-ohos（打过 guess 补丁后）
sh config.sub "$(sh config.guess)"       # 未补 #3 → Kernel 'linux' not known to work with OS 'ohos'

# 问题 3（umask 因果，四向对照）
cd <构建树>
for u in 077 022; do d=$( (umask $u && mktemp -d "./conf${u}XXXXXX") ); \
    ls -ld "$d"; touch "$d/probe" 2>&1 || echo "umask=$u WRITE_FAIL"; done
# 同目录下：umask 077 → drwx--S--- 写不进；umask 022 / 不给 umask → drwxr-s--x 可写；
# 把模板换成 "$TMPDIR/confXXXXXX" 绝对路径 + umask 077 依然写不进 ⇒ 因果只在 umask。
```

## 已试过的失败方案（别再走）
1. **抄同族 .patch**：`archives/r/rgb`、`archives/l/libfontenc`、`archives/x/xvinfo` 的
   config.guess/config.sub/configure 补丁对 xrefresh 树 hunk 失败（0002 挂 2/3、
   0003 挂 1/1）。只有 0001 恰好能套上。⇒ 一律按锚点重做 + `refresh-patch --auto`。
2. **只补 config.guess**：configure 会在下一步被 config.sub 拒（症状 2），看着像 guess
   补丁没生效，容易回退去改 guess，实际缺的是 config.sub 的 kernel-OS 白名单。
3. **把 `--build/--host` 三元组当解法**：E007/E205 明确禁止——那会把 native 构建误判成
   交叉编译，`AC_RUN_IFELSE` 全跳过、config.h 生成错（本包 `AC_CHECK_FUNCS([strcasecmp])`
   就会被瞎猜）。且 `archives/x/xeyes/1.3.1` 里传三元组是**补丁之外的历史遗留**，
   不是可复制的理由。
4. **改走绝对 `$TMPDIR` 来治 E136**：实验证明无效（对照 D 组：umask 077 + 绝对
   `$TMPDIR` 仍 `drwx--S---` 写不进）。
5. **靠 pkg-config 解析 `xproto.pc`**：该 `.pc` 在 `share/pkgconfig/` 而非
   `lib/pkgconfig/`，默认 PKG_CONFIG_PATH 扫不到，且 CI worker 的 pkg-config 可用性
   不该成为前提。

## 最终方案
`patches/` 三个补丁（探测脚本 + config.status 引导）+ `XREFRESH_CFLAGS/LIBS` 逃逸 +
conan 依赖 `libx11/6.4.0` / `xorgproto/2025.1`（构建期）、`libxcb/libxau/libxdmcp`
（运行期）。补丁新增行**零平台宏**（R8/PF5：不给 `__OHOS__` 开后门，能力由
config.guess/sub 的探测决定）。配方 `package_type="application"` ⇒ 附软件级
`commands.json`（R38/L0k）。

## 测试口径（rule4 五维账本）
| 维度 | 数 | 证据 |
|---|---|---|
| 上游静态可测（discovered） | **0** | Makefile.am/man/Makefile.am 无 TESTS/check_PROGRAMS/check-local；configure.ac 无测试宏；发布包无 tests/ 目录 |
| 上游可执行 | 0 | `make -n check` rc=0 只展开 check-recursive 骨架 |
| 上游实测通过 / 跳过 / 失败 | 0 / 0 / 0 | 真跑 `make check` rc=0，man 子目录 "Nothing to be done for 'check'" |
| 适配侧自造断言 | **6 条，全通过** | 关键读数已**内联**进本笔记「验证结果」小节（六条 rc/输出 + HMBS 两行原文，可逐行回查）；探针件 `explore/probe-C0*.out` 在设备本地任务目录、不随 PR 发布 |
声明数（MANIFEST `assertion_count: 6`）= 实测数，未虚报。
测量方法自证：先用同工具链编译并运行一个必然成功的 control 程序（`CONTROL_OK`，
rc=0）证明"本机可执行新编译 ELF + rc 捕获有效"，再谈 xrefresh 的读数。
**未覆盖**：真正的"让 X server 重绘窗口"（映射/取消映射全屏窗口）需真 X 会话，
无头环境下不做无证据声明；`DISPLAY=:99` 不可达时实测 rc=1 且 20s timeout 未触发
（不是挂住；超时会是 124，绝不当通过）。

## 依赖版本（本次实测）
| 包 | 版本 | 说明 |
|---|---|---|
| libx11 | 6.4.0 | 已发布，OHOS armv8 二进制实测可下（`Install finished successfully`）；104 个在档配方用这条版本线 |
| xorgproto | 2025.1 | 已发布；**2024.1 未发布**（与必然不存在的负对照同签名 `not resolved`） |
| libxcb / libxau / libxdmcp | 1.16 / 1.0.11 / 1.1.5 | 运行期闭包，均实测有二进制 |
| bzip2/1.0.8 | — | 正对照（rc=0），证明"探测面本身是好的" |
未使用 libxext（xrefresh 不链 Xext），因此**刻意不碰** X11 两条互不兼容的版本线之争。

## 验证结果
```
conan-verify: B 机 OHC_RC=0、G1/G0/G2/G3 PASS；A 机 03:58 重跑同样通过 —— 盘上 `reports/conan-create.log` 现属 **A 机那一轮**（`reports/` 被 `.gitignore` 挡住，不随 PR 发布）
本地 W3 模拟（A 机 04:00，**配方提交之后**重跑）: 通过 —— 见 .ci-result.json 与 reports/w3-local-ci.log
  w3-local-ci.log:455 HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"test_xrefresh.sh","discovered":6,"passedCount":6}
  w3-local-ci.log:457 HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests","framework":"none","command":"make -n check / make check (both register 0 cases)","discovered":0,...}
  w3-local-ci.log:482-485 Build Summary Total 1 / Success 1 / Failed 0 / Pass rate 100.0%；:487 All packages built and tested successfully
  两条非阻断告警如实记录：L2_RESULT=skip（框架冒烟用**长选项** --version/--help 探测，本包只认单短选项，故 skip；单短选项实测 rc 见上表，非缺陷）；L4_RESULT=warn（dangerous functions in patches —— 命中面是上游 config.guess 探测脚本自身的旧式函数，非本包新增代码）
  同轮日志末尾框架自打印：Pre-download: conandata.yml 已还原为官方 URL（本窗另独立核对提交态与活文件均无镜像/file:// 注入）
（首跑 B 机 03:15 失败于 JC1，原因见「注意事项」第 4 条）
探索阶段实测（B 机）：
  configure rc=0   make rc=0   make install rc=0
  -version -> "xrefresh 1.1.0" rc=0        -help  -> usage rc=0
  -v       -> "xrefresh 1.1.0" rc=0        未知参数 -> rc=1 "unrecognized argument"
  -delay   -> rc=1 "requires an argument"  无 DISPLAY -> rc=1 "unable to open display ''"
  DISPLAY=:99 + timeout 20 -> rc=1（未超时）
  llvm-readelf -d xrefresh -> NEEDED libX11.so.6, libc.so
```

## 适用边界
- 适用：鸿蒙 PC 上"上游预生成 configure 的 X.Org autotools 应用"（单包、只依赖
  libX11/xproto 这一类），以及一切 autotools 包的 E136 处置。
- 不适用：需要未发布 X 库（如 libXmu 的 xmuu）的包 —— 那是 xhost 的停手场景，
  必须转手等依赖，**不许 vendored 内建第三方源码**（属捎带适配未发布依赖）。
- 不适用：需要 autoreconf 再生成的包（本机 perl 缺失，automake 系不可用）。

## 交付物
| 文件 | 说明 |
|------|------|
| `conanfile.py` / `conandata.yml` / `patches/000{1,2,3}-*.patch` / `test_package/` | CI 输入 |
| `archives/x/xrefresh/{manifest.yaml,README.md,commands.json}` | 软件级（R38） |
| `1.1.0/{manifest.yaml,notes.md}` | AI 元数据（随 PR 发布） |
| `1.1.0/reports/` | 构建与 W3 日志——**被 `.gitignore` 挡住，不随 PR 发布**，仅设备本地留档 |

## 注意事项
1. `conandata.yml` 的 `sources.url` **必须保持列表形态**。`build_and_test.sh` 的 CI
   预下载 `get_mirrors()` 只改写单值 url，会把 xorg 域换成 404 的第三方镜像，且不校验
   HTTP 状态码 ⇒ 404 页被当 tarball 存下 → sha256 必败。verify/finish 之后、`git add`
   之前务必 `git diff -- archives/x/xrefresh/1.1.0/conandata.yml`（R39）。
2. 上游无 `Xrefresh` 库可链接，下游无 cpp_info，别给 `package_info()` 加 `libs`。
3. 本包在 CI 上如需 `/storage/.../usr/local` 之外的路径，一律走 conan 私有 prefix；
   配方里没有 `/usr/local` 字面量（PF6/R49）。
4. ★ **`finish`/本地 W3 模拟必须在配方提交之后跑**。`ci/scripts/junk_check.sh:52-56` 的
   回退规则是「`origin/main` 可解析但 `origin/main...HEAD` 为空 ⇒ 退回 `full` 全仓扫描」，
   未提交时必然触发，于是命中**基线上他人归档**的运行时状态文件（实测 `archives/c/cloog/0.21.1/.build-closed`、
   `archives/c/cloog/0.21.1/.staging-verified`、`archives/k/kics/2.1.20/.staging-verified`）而判 JC1 fail。
   提交后在同一 worktree 重跑同一脚本即 `检查模式: incremental (13 个文件) / JC_RESULT=pass / RC=0`。
   ⇒ 本包 03:15 那次 W3 失败属**顺序自伤**；**不要去清理他人归档、也不要改 `ci/`**。
   该回退判据本身建议反馈给 CI 维护者（full 模式至少应把 `archives/**` 的运行时状态文件从判定里排除）。

### 对话 #1
- 主代理简报的停手条件是"若结论是必须有真 X 会话才能做有意义验证 ⇒ 停手上报"。
  本包实测存在 6 条零成本且有意义的断言（含一条真正的运行期动态链接断言），且已合并
  同族 `xeyes 1.3.1` 正是在同一约束下用 -version/-help 口径过门禁的 ⇒ **判定为不必停手**，
  按家族先例推进，同时把"真 X 会话才能覆盖的重绘行为"如实写成本笔记的未覆盖项。
  若主代理认为必须做真 X 验证，需另开有图形会话的窗口，本包已留全部取证脚本。
---

**编译结束**: 2026-09-24 03:58
**最终状态**: built
