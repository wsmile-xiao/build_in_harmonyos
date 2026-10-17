# wmcore 0.0.4 适配笔记

## 编译环境
- 构建系统: autotools（autoconf 2.69 + automake，发布包内已带 `configure`/`Makefile.in`，无 `autogen`）
- 编译日期: 2026-09-26
- 编译器: clang 15.0.4（`/data/service/hnp/bin/clang`，Target `aarch64-unknown-linux-ohos`）
- 机器: B 机（HarmonyOS PC aarch64，HongMeng Kernel 1.12.0，8 核 / 31G）
- profile: `ci/conan/profiles/ohos-aarch64`（`-pr:h` 与 `-pr:b` 同一个）
- CONAN_HOME: `~/tmp/ch/home-wmcore`（本任务独立）
- 状态: built（conan-verify 通过，未 upload；upload 由合并后的 CI 做）

## 软件与构建面（读源码所得，不是猜测）

wmcore 是「每核 CPU 占用条形图」的 **X11 dockapp 应用程序**（`package_type = "application"`，不是库）：

- 发布包 17 个文件，C 源码只有 `wmcore.c`（215 行），另两个 `wmcore_SOURCES` 元素是
  `wmcore_master.xpm` / `wmcore_mask.xbm`（被 `#include` 进 .c）。
- `configure.ac:16` = `PKG_CHECK_MODULES([pkg_config], [x11 xext xpm dockapp])`
  ⇒ 必须出 `PkgConfigDeps`（只给 `AutotoolsDeps` 喂不到 pkg-config）。
- `Makefile.am`：`bin_PROGRAMS = wmcore`、`man_MANS = wmcore.1`（由 `wmcore.1.in` 经
  `AC_CONFIG_FILES([Makefile wmcore.1])` 做 `@PACKAGE_VERSION@` 替换生成）
  ⇒ **不需要** asciidoc/xmlto。
- `wmcore.c` 直引 `X11/Xlib.h`、`X11/xpm.h`、`X11/extensions/shape.h`、
  `libdockapp/wmgeneral.h` + `libdockapp/misc.h` ⇒ 四个直接依赖都要
  `transitive_headers=True` + `transitive_libs=True`。
- 运行期语义（消费者测试的依据）：`main()` 先 `fputs(PACKAGE_STRING ...)` 打横幅，
  再扫 `argv` 处理 `-d`（取延时）与 `-h`（打 usage 后 **exit(0)**，发生在连 X 之前），
  然后 `openXwindow()`（libdockapp）连 X。⇒ 无显示器时能真实执行的两条路径是
  `-h`（退出 0）与「X 连接失败」（退出 1 + libdockapp 诊断）。

## 编译步骤（配方实际做的事）

1. `source()`：`get()` 解 `https://www.dockapps.net/download/wmcore-0.0.4.tar.xz`
   （sha256 `ecefdd49…34d20`，77104 字节，`strip_root=True`）。
2. `generate()`：`AutotoolsDeps` → `PkgConfigDeps` → `AutotoolsToolchain`（顺序照已发布 libdockapp/0.7.3）。
3. `build()`：
   - `_fix_configure_umask()`：把发布包内 `configure` 的 `umask 077` 就地改写为 `umask 022`（实测命中 2 处）。
   - `_configure()`：**同一条 shell 命令内** `unset CONFIG_SHELL` + 内联 `LD_LIBRARY_PATH=<依赖 libdir>`
     后运行 `../configure <AutotoolsToolchain 写入的参数>`（参数取 `Autotools._configure_args`，不自己拼编译开关）。
   - `make -j1`，随后 `make -j1 check`（本包该目标为空，见下）。
4. `package()`：`Autotools.install()`（= `make install DESTDIR=<package_folder>`，`--prefix=/` 是
   AutotoolsToolchain 的默认，落包靠 DESTDIR）+ 拷 `COPYING` 到 `licenses/`。
5. `package_info()`：不导出 `cpp_info.libs`；`bindirs=["bin"]`、`resdirs=["share"]`、
   `includedirs=[]`、`libdirs=[]`。命令行为由软件级 `commands.json` 声明（R38/L0k）。

## 遇到的问题与解决方案

| # | 问题（症状原文） | 根因 | 解决方案 |
|---|---|---|---|
| 1 | `configure: error: in '…/build-release': configure: error: cannot run C compiled programs.` 且 `See config.log` | **不是** 交叉编译问题、也不是签名问题：`AutotoolsDeps` 把整条依赖闭包的 `-l` 放进 `$LIBS`，autoconf 第一个「运行程序」测试（`checking whether we are cross compiling`）链接的 conftest 带 `-ldockapp -lXpm -lXext -lX11 … -lpthread`，而 configure 子进程没有运行库搜索路径 ⇒ 加载器拒载被 autoconf 误报成「编译器不能产出可运行程序 / 请用 --host」 | `_configure()` 内联 `LD_LIBRARY_PATH=<依赖闭包 libdir 列表>`（同一条命令里）。之后实测 `checking whether we are cross compiling... no`，`checking for x11 xext xpm dockapp... yes`，全部头/函数检查真实完成 |
| 2 | `./config.status[768]: can't create ./conffxDNxi/subs1.awk: Permission denied` ⇒ `config.status: error: could not setup config files machinery` | E011 / E114：autoconf 用 `(umask 077 && mktemp -d "./confXXXXXX")` 建 scratch 目录；HMDFS 上 0700 目录回读为 0660（无检索位），随后 `cat >"$ac_tmp/subs1.awk"` 直接 EACCES | `build()` 里把 `configure` 内 `umask 077` 就地改写为 `umask 022`（命中 2 处，与 1000+ 存量配方同形态）。生成文件按 CONTRIBUTING 补丁规范不走 `patches/`，未命中时打 warning |
| 3 | E386（`CONFIG_SHELL` 家族）——**本包实测会中招** | profile `[buildenv]` 有 `CONFIG_SHELL=/data/service/hnp/bin/bash`；conan 的 `conanbuildenv-release-armv8.sh:18` 确实 `export CONFIG_SHELL=…`（该轮构建目录内实文核对），而该 bash 在 HMDFS 构建目录里 `getcwd()` 失败；autoconf 2.69 的 configure 会用 `$CONFIG_SHELL` 重新 exec 自身（configure 第 139/154/255 行的 `_as_can_reexec` 块）⇒ 启动即死 | **同一条 shell 命令里** `unset CONFIG_SHELL`（`generate()` 期 `env.unset` 赢不过运行期重注入，sword/本包两侧实测同结论）。A/B 对照见「A/B 与反向验证证据」小节 |
| 4 | conan-verify 报告里 G4 只有 `⚠️ 无法找到程序包 ID`、L2/L4/L5 只有 `⏭️ 跳过（无 cache 路径）` | `package_type="application"` 的纯可执行包在 conan-verify 里定位不到包目录（框架既有缺陷，coolmail/1.3 同记录） | 按 coolmail 口径人工补测 G4/L2/L4/L5，逐条证据写在 `~/tmp/uc2/z63-wmcore/reports/conan-verify-supplement.md`；不要只看报告上的 `✅ PASS` |
| 5 | 上游测试为零 | 见下面「上游测试清点」 | `test_package/` 承担验证：9 条行为断言 + 4 条平台断言 = 13 条，全绿；`build()` 仍执行 `make -j1 check` 留执行痕迹（L1c） |

### 上游测试清点（三条实测证据，命令与输出）

```text
$ ls -d tests test
ls: tests: No such file or directory
ls: test: No such file or directory                     rc=1

$ grep -nE "TESTS|check_PROGRAMS" Makefile.am configure.ac
（无输出）                                                rc=1

$ find . -type f | wc -l   -> 17
$ find . -name "*.c" | wc -l -> 1        （只有 wmcore.c 本体）
$ find . -iname "*test*" -o -iname "*check*"
（无输出）

$ make -n check      # 已 configure 的构建目录内
…check/check-am 展开出的配方只有「clang -c wmcore.c」与「clang -o wmcore …」两条，
既没有 test-driver，也没有任何测试程序或 LOG_DRIVER 行 ⇒ automake 的 check 目标在本包为空
```

⇒ 上游静态测试总数 0，可执行 0，实测执行 0，跳过 0，失败 0。**没有拿「无 X 环境」当 0 执行的理由**
（rule4 口径：那样写一律驳回）；本包确实一个用例都没有。窗口绘制部分明确记为未覆盖。

### 假信号（前任已推翻，本包未据此改动，留此防复踩）

- 全树 `-Werror` 只出现在 `aclocal.m4:550` 的宏注释里 ⇒ 不需要 `-Wno-error` 类补丁。
- 树内**没有** `config.guess`/`config.sub`，`configure.ac` 也没有 `AC_CANONICAL_HOST`
  ⇒ config.* 家族补丁与 E160 在本包不适用。
- `configure` 里的 `/usr/local` 只是 autoconf 默认 prefix（conan 传 `--prefix=/` 覆盖）⇒ 不是宿主路径注入。
- **E490**（Autotools 脚本可执行位）被 G0 预扫命中并打印「未在配方中处理」，但实测
  `get()` 解出来的 `configure`/`install-sh`/`compile`/`depcomp`/`missing` 在 HMDFS 上是
  `-rwxr-x---`（mode 保留），本包三轮构建均无 `Permission denied … cannot execute`
  ⇒ **有意不加** 预防性 `chmod`（R1 最少化）。若 CI 侧真报该症状，按 E490 处方补即可。

### 未采纳的方案（含原因，别再试第二遍）

1. **`generate()` 里 `env.unset("CONFIG_SHELL")`** —— 已被 sword 与本包共同证伪：conan 在
   `self.run` 前 source `conanbuild.sh`，`[buildenv]` 在运行期重注入。
2. **`--host=aarch64-linux-ohos` 让 configure 认定交叉编译**（已发布 libdockapp/0.7.3 的形态）
   —— 本包不照搬：`configure` 里没有 `AC_CANONICAL_HOST`（实测 grep 无命中），`--host` 能否把
   `cross_compiling` 置成 `yes` 未实证；而本包真实阻塞点是运行期库搜索路径，注入
   `LD_LIBRARY_PATH` 后 autoconf 的 native 探测全部真实完成（更准，也不会把
   `AC_CHECK_FUNCS(strstr)` 一类判成交叉盲猜）。若将来上游改用 `AC_CANONICAL_HOST` 可再评估。
3. **写进 conandata 的 Debian 池 URL / 任何镜像** —— PF7 黑名单（`deb.debian.org` 属 Debian 重打包源），
   官方直链已核：与 `wmcore_0.0.4.orig.tar.xz` 逐字节相同（同一 sha256）。
4. **给二进制做 self-sign**（tabbed/libdockapp 形态）—— 实测不需要：OHOS clang 链接阶段已写入
   `.codesign` 段（`llvm-readelf -SW` 有该段，且二进制能直接执行），配方不重复签名。

## A/B 与反向验证证据（都在 B 机实测）

```text
A/B（脚本与日志：~/tmp/uc2/z63-wmcore/ab-config-shell.sh / ab-config-shell.log）
  arm A：CONFIG_SHELL=/data/service/hnp/bin/bash 导出去跑 ../src/configure
    shell-init: error retrieving current directory: getcwd: cannot access parent directories: Not a tty
    job-working-directory: error retrieving current directory: getcwd: …
    configure: error: working directory cannot be determined          ← E386 在本包真实复现
  arm B：同一条命令 unset CONFIG_SHELL
    越过该点（后续因该 A/B 脚本未注入 conan 工具链环境而停在 "no acceptable C compiler"，
    与本包适配无关；结论只取「A 死在启动期、B 不死」这一对比）
  同目录 shell 能力对照：/data/service/hnp/bin/bash -c pwd → rc=1；/bin/sh -c pwd → rc=0

反向验证（CI L1e 的本地等价，日志：~/tmp/uc2/z63-wmcore/reverse-verification.log）
  临时 mv <package_folder>/bin/wmcore <package_folder>/bin/wmcore.hidden
  conan test archives/w/wmcore/0.0.4/test_package wmcore/0.0.4 → rc=1
    FAIL: packaged wmcore binary missing: …/p/bin/wmcore
  随后已把文件 mv 回原位（ls -l 复核 55680 字节在位）⇒ 断言不是恒真

无头 dockapp 判据（实测原文，非推测）
  $ wmcore -h                 → 横幅 + usage，rc=0
  $ unset DISPLAY; wmcore     → "wmcore 0.0.4 by bitman@bitmania.de"
                                "wmcore: can't open display "                 rc=1
  $ DISPLAY=:99 wmcore        → "wmcore: can't open display :99"              rc=1
  $ env -u LD_LIBRARY_PATH wmcore -h
                              → "Error loading shared library libdockapp.so.3: (needed by …)"  rc=127
  ⇒ 区分点：能加载并执行、失败签名出现在 **X 连接层**（libdockapp 诊断），
     而不是 loader 层（Error loading shared library / rc 126/127 / No such file or directory）。
```

## 验证结果

```text
门禁链（B 机，命令逐字）：
  bash ci/scripts/preflight_check.sh wmcore/0.0.4                 → rc=0（4 依赖全部已发布；wmcore/0.0.4 版本号未被占用）
  python3 scripts/ohc-run.py recipe-search wmcore                 → 本基线无同类 dockapp 骨架（top1 即本包，score=0.45）
  python3 scripts/ohc-run.py graph validate                       → rc=0（540 条一致，仅既有 warning）
  conan create . -pr:h=… -pr:b=…                                  → rc=0，13/13 断言绿（三轮：探索轮 + 两轮 --build 干净轮）
  python3 scripts/ohc-run.py conan-verify wmcore 0.0.4            → rc=0，Verdict PASS（G0-G3 实 PASS，G4/L2/L4/L5 见补测）
未跑（按分工交主理窗）：ohc-run.py build / finish / submit，以及一切平台侧写操作。

五维测试账本：
  上游静态总数 0 / 可执行 0 / 实测通过 0 / 跳过 0 / 失败 0
  消费者（适配后新增）13 条：行为 9 + 平台 ELF 4，实测 13 通过 13 失败 0 跳过 0
  机器可读行：HMBS_TEST_PACKAGE_RESULT={"consumer_passed": 13, "consumer_total": 13, "executed": true, "passed": true}

产物基线（两轮独立干净构建 sha256 相同）：
  569e98f5fa944fc2f56ccdb0473312496b292aa248b7cb29fbe6fea838df4e71  bin/wmcore      (55680 B)
  8eeedc9242b9e8a703316315484d178d8e90350bf93e150e4af6402bd72decb9  share/man/man1/wmcore.1 (509 B)
  8177f97513213526df2cf6184d8ff986c675afb514d4e68a404010521b880643  licenses/COPYING (18092 B)
  （conanmanifest.txt 每轮不同属正常：内含打包时间戳）

L4 安全属性（人工补测，llvm-readelf）：
  Type: DYN (PIE)；FLAGS BIND_NOW + FLAGS_1 NOW PIE；无 TEXTREL
  GNU_STACK  RW（NX 生效）；GNU_RELRO 存在 ⇒ Full RELRO + PIE + NX
```

## 依赖版本（实测发布状态）

| 依赖 | 版本 | recipe rev（ohpcd） | 说明 |
|---|---|---|---|
| libdockapp | 0.7.3 | `bb168856ac0f89767afffa6312d1a740` | dockapp.pc / `-ldockapp`；其自身 requires 定义 6.4.0 轨 |
| libx11 | 6.4.0 | `63e25e48c3af73db324ce61d0dba9cce` | `-lX11`；传递 libxcb/1.16、libxau、libxdmcp、xorgproto/2025.1、xtrans |
| libxext | 6.4.0 | `20942ab436730e84acb01dcf565fda68` | `X11/extensions/shape.h` + `-lXext`；⚠ 仓库 main 内另有 libxext/1.3.6、1.3.7 一套目录，**不得**混进图 |
| libxpm | 3.5.17 | `e08a81954eab886de9acc314b8bcd8bd` | `X11/xpm.h` + `-lXpm` |

B 机新 CONAN_HOME 已用 `conan install --build=never` 实拉全套 ohos-aarch64 二进制（含上述 4 个 + 7 个传递包）。

## 交付物

| 文件 | 说明 |
|---|---|
| `archives/w/wmcore/0.0.4/conanfile.py` | 配方（E386 / E011 / LD_LIBRARY_PATH 三处改写都在这里，含中文依据） |
| `archives/w/wmcore/0.0.4/conandata.yml` | 上游官方直链 + sha256（前任已定稿，本次未改动） |
| `archives/w/wmcore/0.0.4/manifest.yaml` | 版本级编译元数据（占位模板已填实） |
| `archives/w/wmcore/0.0.4/notes.md` | 本文件 |
| `archives/w/wmcore/0.0.4/test_package/conanfile.py` | 13 条断言的入口（4 条平台断言 + 行为断言条数对账） |
| `archives/w/wmcore/0.0.4/test_package/test_wmcore.sh` | 9 条行为断言（POSIX sh，toybox ash 实测可跑） |
| `archives/w/wmcore/0.0.4/test_package/MANIFEST.yml` | R51 上游测试清点 + 五维账本 + 消费者断言清单 |
| `~/tmp/uc2/z63-wmcore/reports/conan-verify-report.md` | conan-verify 工具原报告（该目录被 .gitignore 第 96 行的 `reports/` 忽略，不入 PR，作为交接证据留在盘上） |
| `~/tmp/uc2/z63-wmcore/reports/conan-create-log.md` | 干净构建日志逐字留档（原 `conan-create.log` 按仓库规则禁入 PR） |
| `~/tmp/uc2/z63-wmcore/reports/conan-verify-supplement.md` | application 包的 G4/L2/L4/L5 人工补测 + 反向验证 + E386 A/B |
| `archives/w/wmcore/commands.json` | R38/L0k 命令行声明（type=tool，versions.0.0.4.ref=wmcore/0.0.4） |
| `archives/w/wmcore/manifest.yaml` | 软件级元数据 + OHOS 适配要点 |
| `archives/w/wmcore/README.md` | 软件说明（ARCHIVE-SPEC 必填项） |

## 注意事项（适用边界）

1. **只适配到「程序能构建、能加载、能跑到 X 连接层」这个程度**。dockapp 的窗口/条形图绘制
   需要 X server 与一个支持 dock 的窗口管理器，本环境（设备与 CI worker）都没有 ⇒
   这部分是真实的**未覆盖**，不得写成「已验证功能正常」。
2. 配方依赖 `libdockapp/0.7.3` 的 6.4.0 X11 轨。若哪天有人把 wmcore 的 libx11 改成 1.8.13 轨
   （tabbed 用的那条），会与 libdockapp 的 `force=True` 冲突或 fork 出第二套闭包。
3. `umask 077` 改写依赖 autoconf 生成的字面量。上游若改用新 autoconf 重生成 configure，
   改写会打印 warning（`E011: 'umask 077' not found`）而不是静默通过。
4. wmcore 产物**无 RPATH/RUNPATH**：消费者必须带 Conan 运行库路径（`conan install` 的
   VirtualRunEnv / `conanrun`）。这也是 test_package 里 rc=127 对照组成立的前提。
5. `make check` 目标为空是上游事实（automake 无 TESTS/check_PROGRAMS），不是被关闭的选项；
   若上游以后加了测试，`test_package/MANIFEST.yml` 的账本要同步改。
---

**编译结束**: 2026-09-26 02:47
**最终状态**: built
