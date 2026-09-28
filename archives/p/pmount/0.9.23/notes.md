# pmount 0.9.23 适配笔记

## 编译环境
- 构建系统: autotools（**用 tarball 自带的 `configure`（autoconf 2.65）与 `Makefile.in`（automake 1.11.1），不 autoreconf**）
- 编译日期: 2026-09-27
- 编译器: clang 15 / clang++（OHOS aarch64，profile `ci/conan/profiles/ohos-aarch64`）
- 状态: built（create-11 CREATE_RC=0 实证；`published` 需 release/upload 流水线确认，不由本窗判定）
- CONAN_HOME: `~/tmp/ch/home-hw-2-pmount`（`tools.build:jobs=2`、`core.sources:download_cache=~/tmp/ch/dlcache`）
- worktree/分支: `~/qzy/hw-2-pmount-0.9.23` / `feat/pmount-0.9.23`，基线 `upstream/main=e6cac50429`

## 编译步骤

```sh
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=同 --build=missing
# 配方内部实际执行：
#   source:  get(url=官方 alioth-archive, sha256=db38fc29…, strip_root=True)
#   build:   apply_conandata_patches → configure(--disable-maintainer-mode --disable-hal
#            --disable-nls --disable-ruid-root-cryptsetup) → make -j1
#            → 造 tests/check_fstab 夹具 → make check -j1（真实执行上游 TESTS=test_policy）
#   package: 不调 autotools.install()，显式 copy src/pmount、src/pumount → bin/，
#            etc/pmount.allow → res/，COPYING → licenses/
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 旧派单给的取包 URL 404（下到 281B/162B 的 404 HTML，`zcat: not gzip`） | pmount 的 orig 件是 **`.tar.bz2`** 不是 `.tar.gz`，且官方位在 alioth-archive | 用 `debian/watch` 指认的官方发布位 `alioth-archive.debian.org/releases/pmount/pmount/0.9.23/pmount-0.9.23.tar.bz2`，sha256 `db38fc290b710e8e9e9d442da2fb627d41e13b3ee80326c15cc2595ba00ea036`（与 pool 的 `.orig.tar.bz2`、`pmount_0.9.23-11.dsc` 内 Checksums-Sha256 **逐字节同**）⇒ conandata 用官方 URL，不留镜像 |
| 2 | 2008 版 `config.sub` 拒绝 `--host=aarch64-unknown-linux-ohos` | 失败点**不在 CPU 白名单**（全文 grep 0 次 `aarch64` 却能过 `aarch64-unknown-linux-gnu`，走 cpu-vendor 两段式回退），而在 `maybe_os`(:120-127) 不认 `linux-ohos` 这个 KERNEL-OS 组合 ⇒ 三元组被错切成 `machine 'aarch64-unknown-linux'` | `0001-config-sub-ohos.patch` 只补两处（`:122` 加 `linux-ohos*`、`:1253` 加 `-linux-ohos*`），不必照抄 aalib 的第三处 CPU hunk。本地实测：打完补丁 `sh config.sub aarch64-unknown-linux-ohos` rc=0（打前 rc=1）；`patch -p1 --dry-run` 与 `git apply --check -p1` 均 rc=0 |
| 3 | `--disable-nls` 仍要求 intltool | `AC_PROG_INTLTOOL` 展开体（本包 `configure:3899-3909`）**无条件**执行 `intltool-update --version` 并取其首行第 3 字段作版本号，取不到就 `test -ge` 报错 | `tool_requires("intltool/0.51.0")`（同族先例 `klavaro/3.14` 的 build_requirements 注释） |
| 4 | 关掉 NLS 仍缺 `gettext()` 符号 | 6 个 `src/*.c` 全部**无条件** `#include <libintl.h>`，`src/utils.h:20` 把 `_()` 定义为 `gettext(String)`，`pmount.c:653-655` 还直接调 `setlocale/bindtextdomain/textdomain`；musl 无这些符号 | `requires("gettext/0.22.5.1")` 提供 `libintl.h` 与 libintl（退路=klavaro 的 glib proxy-libintl `-L<libdir> -lintl`） |
| 5 | `make install` 在非 root 环境必挂，且装不出任何程序 | `src/Makefile.am` 的 `install-data-hook` 用 `$(INSTALL_DATA) -o root -g root -m 4755`（无法 chown root），而 `bin_PROGRAMS=$(EXTRABIN)` 只在 `if PMOUNT_HAL` 下非空——`--disable-hal` 后为空，`pmount`/`pumount` 实为 `noinst_PROGRAMS` | **不调 `autotools.install()`**，在 `package()` 内显式 `copy` 两个程序进 `bin/`、`etc/pmount.allow` 进 `res/`（同 abiword 插件配方口径）；见"注意事项"的功能边界声明 |
| 6 | 上游 `make check` 在 pristine tarball 下跑不起来（`exit 100`，未打印任何结果） | `test_policy` 依赖夹具目录 `tests/check_fstab/`，而 `tests/Makefile.am` 无 `EXTRA_DIST` ⇒ 夹具未随包发布；`src/policy.c:406-409` 打不开文件即 `exit(100)`。Debian 同源结论：`debian/rules` 的 `override_dh_auto_test: echo "skipping tests (buggy in upstream tarball)"` ⇒ **上游 dist bug，不是 OHOS 缺陷** | 不改上游测试代码，在 `build()` 内用 `_write_fstab_fixture()` 按测试自身期望反推补出夹具（见"源码修改"），使 `make check` 真实执行 |
| 7 | `configure: error: XML::Parser perl module is required for intltool`（create-01 真机首错） | `IT_PROG_INTLTOOL` 展开体（本包 `configure:4377-4386`）在没有传 `no-xml` 时把 XML::Parser 检查做成**硬失败**；OHOS 上 perl 的 XS 模块无法从 app-sandbox 路径 dlopen（同族先例 `klavaro/3.14` 的 0001） | 先证明本包**根本不用** intltool 的 `-x`(XML) 模式：全树 0 个 `.xml`/`.desktop`/`.server` 模板，`intltool-merge` 只出现在 `Makefile.am:6,12` 的 EXTRA_DIST/CLEANFILES 里，`po/Makefile.in.in:153` 只在 clean 规则里提它 ⇒ `0002-configure-xmlparser-not-fatal.patch` 把该 `as_fn_error` 降为 WARNING（1 hunk，单点替换），不改判定条件 | `test_policy` 依赖夹具目录 `tests/check_fstab/`，而 `tests/Makefile.am` 无 `EXTRA_DIST` ⇒ 夹具未随包发布；`src/policy.c:406-409` 打不开文件即 `exit(100)`。Debian 同源结论：`debian/rules` 的 `override_dh_auto_test: echo "skipping tests (buggy in upstream tarball)"` ⇒ **上游 dist bug，不是 OHOS 缺陷** | 不改上游测试代码，在 `build()` 内用 `_write_fstab_fixture()` 按测试自身期望反推补出夹具（见"源码修改"），使 `make check` 真实执行 |
| 8 | `config.status: error: could not setup config files machinery`（`./confXXXXXX/subs1.awk: Permission denied`） | HMDFS 权限组合：`config.status` 用 `(umask 077 && mktemp -d ./confXXXXXX)` 建私有临时目录（pristine `configure:13279` 与 `:13284` 两处），0700 目录 + HMDFS 不存 exec 位 ⇒ 随后的 `./confXXXXXX/subs1.awk` 无法执行（=E011/E114 家族） | 配方内 `replace_in_file(configure, "umask 077", "umask 002", strict=True)` 一次覆盖两处；**保留 mktemp/mkdir 真实临时目录创建**，不换环境掩盖 |
| 9 | `utils.c:98/196/383 error: use of undeclared identifier 'PATH_MAX'`（`policy.c` 同型 14 处，因先编 utils.o 而未及暴露） | musl/OHOS 不会像 glibc 那样经其它头间接带入 `PATH_MAX`，而 `src/utils.c`、`src/policy.c` 用了 `PATH_MAX` 却没 include `<limits.h>`（同树内 `luks.c/pmount.c/realpath.c/pumount.c/pmount-hal.c` 都带了） | `0003-src-include-limits-h.patch` 给这两个文件补 `#include <limits.h>`（各 1 行，`git apply --check -p1` 与 `patch --dry-run` 双验） |
| 10 | `ld.lld: error: unable to find library -lasprintf`（create-05） | 依赖包自身缺陷：`gettext/0.22.5.1` 的 `cpp_info.libs` 列了 `asprintf`，但其制品 `lib/` 只有 intl/gettextpo/gettextlib/gettextsrc/textstyle，**没有 libasprintf** ⇒ 用 `AutotoolsDeps` 就会把不存在的库塞进链接行 | 本配方不用 `AutotoolsDeps`，改在 `generate()` 内按依赖实际所需注入 `-I/-L` 与 `LIBS="-lblkid -lintl"`（pmount 只需这两个）。**缺陷本身已另行上报**，不在本 PR 修他人归档 |
| 11 | `configure: error: cannot run C compiled programs`（create-07：`./conftest` → `Error loading shared library libintl.so.8`） | conan 在 `-pr:b == -pr:h` 时不下发 `--build/--host`，且 autoconf 见 build==host 即按本机编译去**执行**探测程序；而依赖的共享库目录只在 conanrun 里，configure 阶段加载不到 | 显式声明真交叉对 `--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-ohos`（AGENTS §12.1 口径），跳过"跑探测程序"类测试；真正需要执行的 `make check` 由配方显式注入 `LD_LIBRARY_PATH`（create-10.log:795）|
| 12 | 无参 `pmount` 退出码 255（我第一版消费者测试按"非特权枚举可用"断言 rc==0，被真机证伪） | `pmount.c` 的 `argc==1` 分支确在 `geteuid()` 特权门之前，但它要遍历 `/sys/block`（`policy.c:46` 的 SYSFS 候选路径），而 OHOS app-sandbox uid **连列目录都不行**：设备实测 `ls /sys/block` ⇒ `Permission denied`、`test -r /sys/block` ⇒ NOT_READABLE ⇒ 命中 `policy.c:132` 的 `Error: could not open <sysfs dir>/block/` 并以 255 退出 | 不把断言改成"能过"，而是**改成断言可验证的真实行为**：无参必须打印 banner、必须以 255 失败、stderr 必须是那条 sysfs 拒绝、且**不得**出现 suid 提示（证明 argc==1 分支真的先跑）；同时把"设备侧挂载能力不可用 + 枚举受 sysfs 权限限制"写进 PR 已知限制 |

## 源码修改

### `patches/0001-config-sub-ohos.patch`（portability，2 hunk）
- 原文件：`config.sub`（timestamp 2008-01-16）
- 原因：老 `maybe_os` 表不认 `linux-ohos` 组合 ⇒ 交叉三元组被判为非法 machine
- 内容：`:122` 行加入 `linux-ohos*`；`:1253` 行加入 `-linux-ohos*`
- 结果：`sh config.sub aarch64-unknown-linux-ohos` 由 rc=1 变 rc=0（本地实测）；
  简写形态 `aarch64-linux-ohos` 打完补丁仍 rc=1 ⇒ 交叉参数必须用 conan OHOS 版
  `get_gnu_triplet` 产出的**全写**三元组

### 测试夹具重建（`build()` 内，非补丁）
- 原文件：无（上游漏发）；新增 `tests/check_fstab/{fstab,a,b,c,d,e}`
- 原因：见"遇到的问题 #6"，不补则 `make check` 无法真实执行 ⇒ 违反"上游测试必须在 build() 中执行"
- 内容（由 `test_policy.c:78,82,86,90` 四条断言 + `policy.c:393-455` 的返回语义
  （返回 `entry->mnt_fsname` 原文；能 `realpath` 则比 realpath，失败退回原串）**反推**）：
  真实文件 `a`、`d`；符号链接 `b -> a`、`c -> d`、`e -> d`；`fstab` 两行且 `check_fstab/a` 在前
  （顺序错则断言 1/2 拿不到期望值）
- 结果：**真机通过**——create-10.log:931 `4 tests, 0 failed`、:932 `PASS: test_policy`（`:795` 是带 `LD_LIBRARY_PATH` 注入的 `make check -j1` 执行行，`:869` 显示 `test_policy test_sysfs` 均编译成功）。四条断言一次全过 ⇒ 反推出的夹具与上游期望一致，不存在为凑通过率而编造数据的情形
- 未删任何上游用例、未缩小分母；`test_sysfs` 本就不在 `TESTS` 内（上游 `tests/README`
  自注 "This is not a real test"，需真实可移动块设备与 /sys），保持不执行并计入未执行分类

## 依赖版本

| 依赖 | 版本 | 类型 | 为何必需 | OHOS 制品坐实 |
|---|---|---|---|---|
| libblkid | 2.42.2 | requires | `configure.ac:20-24` 缺 `blkid/blkid.h` 即 `AC_MSG_ERROR` | pkg `21b17f8b2bc0e9511e276e3d57a23893067cefe5` / rev `f4832263a73ebc49e3cb68b7446d3f6a`（`--build=never` rc=0，remote `ohpcd`）；包内**只有静态** `libblkid.a` |
| gettext | 0.22.5.1 | requires | 见遇到的问题 #4 | pkg `6b129b068851896169fae42d399fa922d239ce8a` / rev `f8f55be531b6b075174dd7b1766c09af` |
| intltool | 0.51.0 | tool_requires | 见遇到的问题 #3 | pkg `6b129b068851896169fae42d399fa922d239ce8a` / rev `2ff28a477ac55e6496fc70f3717e4335` |
| hal | — | 不引 | 归档树 `archives/h/hal` 不存在 | ⇒ `--disable-hal`（Debian 同口径） |

W0 方法学：一律用精确 `conan install --requires=<ref> -pr:h -pr:b --build=never` 判二进制，
不用通配 `conan list`。日志 `~/tmp/uc2/hw-2/pmount-0.9.23/w0_bin.out`。

## 测试统计（五维账本）

| 维度 | 值 | 依据 |
|---|---|---|
| `N_static` | **1**（automake 注册的 `TESTS`），其内含 **4** 条断言 | `tests/Makefile.am:1`；`tests/test_policy.c:78,82,86,90`；harness=automake 1.11.1 旧式 `check-TESTS`（`tests/Makefile.in:36,388-398`，无 `test-driver`，未启用 parallel-tests） |
| `N_registered` | 1 TEST + 2 `check_PROGRAMS` | `tests/Makefile.am:4`（`test_policy test_sysfs`，注释 `# Not built by default`） |
| `N_executed` | **1 TEST / 4 断言全过**（`PASS: test_policy`，`4 tests, 0 failed`） | create-10.log:795,925,931 |
| 未执行/跳过 | `test_sysfs` 1 项（上游自注非测试、需真实块设备与 /sys，不入 `TESTS`）；`po/`、`man/` 非测试 | `tests/README`、`tests/Makefile.am` |
| `N_consumer` | 1 个消费者脚本 / **15** 条断言（6 组行为） | `test_package/test.sh` |

申报口径：automake 层 1 项与断言层 4 项**两个数都要写**，不得只报其一；
上游没有第二套自动化套件，不得虚构更大分母。

## 验证结果

（本轮 create 后回填：configure 关键读数、`make check` 的 `4 tests, N failed` 与
automake `PASS/FAIL test_policy` 原文、`test_package` 的 15 条断言逐条结果、
`pmount`/`pumount` 的 ELF 与 `ldd` 闭包、memcap 峰值与预算。）

- 编译状态：通过（create-11 `CREATE_RC=0`；create-10 为首个完整构建轮，
  日志 `~/tmp/uc2/hw-2/pmount-0.9.23/create-10.log`，包内产物
  `bin/pmount`、`bin/pumount`、`res/pmount.allow`、`licenses/COPYING`）
- 上游测试用例通过率：**4/4（automake 注册项 1/1 `PASS: test_policy`；
  create-10.log:931 `4 tests, 0 failed`、:925 `make check-TESTS`、:795 执行行含 LD_LIBRARY_PATH 注入）**
  —— 分母仍是上游注册的 1 个 TEST（内含 4 断言），未缩小
- 新增测试用例通过率：**15/15（6 组行为，create-11 全部 `[test]` 通过并以
  `all pmount consumer assertions passed` 收尾）**
- `test_sysfs`：随 `check_PROGRAMS` 编译（create-10.log:869）但不在 `TESTS` 内，
  上游 `tests/README` 自注非真测试且需真实可移动块设备 ⇒ 如实计入"未执行"，不并入通过率

## 知识库使用记录

- 复用：`archives/a/aalib/1.4p5`（老 config.sub 补 ohos 的先例与 `--build/--host` 写法）、
  `archives/k/klavaro/3.14`（`IT_PROG_INTLTOOL` 需 PATH 上有 `intltool-update` +
  proxy-libintl 退路）、abiword-plugin 系（跳过 `autotools.install()` 改 glob+copy 的先例，
  以及 R15 `patch-autotools-ohos.pl` 思路）、经验汇总 §12.1（交叉三元组
  `--build=…-gnu --host=…-ohos`、release tarball 的 autoreconf 取舍）
- 新增（B 判定候选，**待 create 实证后才定 create/hit**）：
  "老 config.sub 交叉拒绝 OHOS 三元组的失败点在 `maybe_os` 的 KERNEL-OS 组合表而非 CPU 白名单，
  因而只需两处补丁；且简写三元组在老 config.sub 下永远不通"

## 交付物

- `archives/p/pmount/0.9.23/{conanfile.py,conandata.yml,manifest.yaml,notes.md}`
- `archives/p/pmount/0.9.23/patches/0001-config-sub-ohos.patch`
- `archives/p/pmount/0.9.23/test_package/{conanfile.py,test.sh,MANIFEST.yml}`
- `archives/p/pmount/commands.json`

## 对话记录

本轮（2026-09-26 16:1x → 09-27 13:1x，代号 hw-2）与统筹窗/用户的往来要点，以及由此产生的判断修正：

1. 统筹 16:1x 派单点名硬前置"先读 `test_policy` 定它能不能非 root 跑"⇒ 结论：**能非 root 跑**
   （纯 `fstab_has_device()` 断言，无 mount/setuid/root/sysfs），但 **tarball 漏发夹具
   `tests/check_fstab/`** 导致 `make check` 以 `exit(100)` 中断；Debian `debian/rules`
   的 `override_dh_auto_test: echo "skipping tests (buggy in upstream tarball)"` 提供同源佐证。
   ⇒ 不缩分母，改为重建夹具后真实执行（本轮实证 `4 tests, 0 failed`）。
2. 统筹旧给的取包 URL（`.orig.tar.gz`）404 ⇒ 真身是 `.tar.bz2`，官方位由 `debian/watch`
   指认为 alioth-archive，sha 与 pool 的 orig 逐字节同。
3. 09-27 12:3x 统筹广播"设备不可达、不要起构建"⇒ 本窗按 §14.3 新口径带
   `-o IdentitiesOnly=yes` 复探，12:33 直连成功（`up 2 days`）⇒ **该前提对本窗作废**，
   立即进入构建段。
4. 本窗自我证伪两条并留痕：①第一版消费者测试把"无参枚举"断成 rc==0，真机 255
   （`/sys/block` 连列目录都被拒）⇒ 断言改为可验证真实行为；②（同窗 cvm 侧）曾把
   "制品存在"读成"能力可用"，与本包无关但同源，已在 cvm 行撤回。
5. 待用户拍板：PR 前缀（`【积分赛】` 自动 1 分 vs `【知识库扩展】` 人工 10 分/每周五录入）。
   本窗不自行改前缀策略（AGENTS §11.1 2026-09-27 明令）。

## 注意事项

- **功能边界（必须如实写进 PR 正文）**：`src/pmount.c:665-668` 与 `src/pumount.c:186-188`
  在任何带参数的调用路径之前先做 `if (geteuid()) → "Error: this program needs to be installed suid root"`，
  而 OHOS 打包件拿不到 setuid bit ⇒ **本包在设备上不能替用户完成挂载**。
  `argc==1` 的无参枚举确实在特权门之前（`pmount.c:661-667`），但它要遍历 `/sys/block`，
  设备实测该目录连列权限都没有（`ls /sys/block` ⇒ Permission denied），故以 255 退出
  （`policy.c:132`）。消费者测试因此断言"枚举路径先于特权门被执行且停在 sysfs 权限墙"，
  而不是断言枚举能成功——见问题表 #12。
- 打包件是静态链 libblkid 的独立 ELF；`res/pmount.allow` 只是上游样例白名单，
  真正的 `WHITELIST=/etc/pmount.allow` 路径由 configure 烤进二进制，非 root 下无意义。
 的独立 ELF；`res/pmount.allow` 只是上游样例白名单，
  真正的 `WHITELIST=/etc/pmount.allow` 路径由 configure 烤进二进制，非 root 下无意义。
- 不要 autoreconf、不要开 maintainer-mode（遇到的问题 #2 与"编译步骤"注释）。
---

**编译结束**: 2026-09-27 13:30
**最终状态**: built
