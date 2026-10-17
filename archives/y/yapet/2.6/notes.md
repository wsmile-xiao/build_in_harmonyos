# yapet 2.6 适配笔记

## 编译环境
- 构建系统: autotools（发布版 tarball 自带 configure，无需 autoreconf）
- 编译日期: 2026-09-24
- 编译器: clang 15 / clang++ 15（profile `ci/conan/profiles/ohos-aarch64`，cppstd=17，Release）
- 状态: built

## 编译步骤

1. `conan create`（`-pr:h`/`-pr:b` 均传绝对路径 `ci/conan/profiles/ohos-aarch64`）：
   - `source()`：`get()` 官方 `yapet-2.6.tar.xz`（`strip_root=True`）
   - `build()`：`apply_conandata_patches`（9 个补丁：4 个 config.guess/sub 整文件 + 2 个 configure `umask 077` 剥离 + 1 个 `crypto.cc` 幂等守卫 + 2 个 /tmp 夹具双面（`Makefile.am`/`Makefile.in`））
     → `AutotoolsToolchain`（`fPIC`、`PKG_CONFIG_PATH` 前置 generators 目录；**不传 `--disable-shared`/`--enable-static`**——上游硬编码 `-shared` 与 libtool 缺陷，理由见问题 11）
     → `AutotoolsDeps`（依赖 -I/-L 注入，覆盖 `AX_CHECK_OPENSSL` 与捆绑 libyacurs 的 `ax_with_curses` 纯链接探测）
     → `PkgConfigDeps.set_property('argon2','pkg_config_name','libargon2')`（模块名对齐上游 `PKG_CHECK_MODULES`）
     → `VirtualBuildEnv`（gettext tool_requires 的 msgfmt 进 PATH）
     → `./configure && make -j1`
   - `package()`：`make install`（-j1），删 libtool `*.la`，`LICENSE` → `licenses/`
2. 设备侧上游测试：沙箱 `HOME=$TASK_DIR/test-home` 下 `make check`（详见「验证结果」）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure` 直接报 `config.guess: unable to guess system type`（2018-08-29 件，rc=1） | `uname -s=HarmonyOS` 不在旧件分派表；顶层与捆绑 `libyacurs` 各自带一份 aux，且两个 configure 都在无 `--build/--host`（R1）时调 `config.guess` 求 build alias | 新件（2026-05-17，savannah config.git 官方 plain 下载）**整文件补丁**×4 + 在新 `config.guess` 主 case 注入 `*:HarmonyOS:*:*` 分支输出 `aarch64-unknown-linux-ohos`（新 `config.sub` 实测认收该三元组）。注：新件本机也会失败——先落 HMDFS `umask 077` 草稿目录不可写（§一.10 同族）再打回，故分支必须在编译探针**之前**命中。经 `refresh_patch` 两面登记（E007 族，先例 cdcd/simstring/coinor-dylp） |
| 2 | `PKG_CHECK_MODULES([ARGON2], [libargon2])` 找不到模块（conan argon2 配方无 `pkg_config_name` 属性 → 默认产 `argon2.pc`） | 上游 pkg-config **模块名**与 conan 包**默认 .pc 文件名**不一致 | **三案取舍**：A. `ARGON2_CFLAGS/ARGON2_LIBS` 环境覆盖（pkg.m4 官方出口，但要在 toolchain env 里手工拼 -I/-L/-l 串，与 cpp_info 双源易漂移）；B. `PkgConfigDeps.set_property('argon2','pkg_config_name','libargon2')` **采用**——conan 官方文档化的消费者侧改名，产 `libargon2.pc`，与 `cppunit.pc` 共用同一条 `PKG_CONFIG_PATH` 机制，零环境双源；C. 手写 `libargon2.pc` 垫片文件（文件面最大、字段要手工同步 soname/-l 序）。B 最小面且机制单一 |
| 3 | `PkgConfigDeps` 只写 `.pc` 不扩 `PKG_CONFIG_PATH`，`PKG_CHECK_MODULES([CPPUNIT],…)` 同样会漏（E468 已知） | conan 设计如此 | `tc.environment()` 里 `prepend_path("PKG_CONFIG_PATH", self.generators_folder)` 后 `tc.generate(env=…)` |
| 4 | `msgfmt` 设备侧可用（harmonybrew）、CI worker PATH 无（设备全绿 ≠ CI 绿，§一.4） | `AM_GNU_GETTEXT([external])` 无条件要 msgfmt | `build_requirements` 加 `tool_requires("gettext/0.22.5.1")` |
| 5 | `tests/converters/check-local` 的 `csv2yapet … /tmp/yapettestimport.pet` 在只读 `/tmp` 上创建夹具失败 → `make check` 红 | 上游把交互外的集成夹具也硬编码到 `/tmp`；OHOS `/tmp` 只读（E002/§一.1） | 补丁 `0008/0009（Makefile.am + Makefile.in 双面）` 把三处 `/tmp/` 路径迁到 `$(builddir)`；**已在 PR 模板「上游测试用例修改」声明** |
| 6 | `tests/preload/check-local` 在无 tty 环境整块不执行 | 上游自身门控：`istty` 非 tty exit 1 → `if` 不成立；其内部 5 项（yapet -i ×2、checktestpwrecord、yapet -i masterpwchange、checkmasterpwchange）本就依赖真终端与 `/tmp` 写入 | 按上游语义计 **SKIP**（NOT_RUN 归因 tty 缺失），不计 PASS、不修上游（§2.17 跳过为准） |
| 7 | `config.status: line 919: ./confXXXXXX/subs1.awk: Permission denied` → `config.status: error: could not setup config files machinery`（configure 红） | HMDFS 强制 setgid，`(umask 077 && mktemp -d "./confXXXXXX")` 落盘 `drwx--S---(2700)`，进程 euid 非属主、other 位无 w ⇒ 写 subs1.awk 被拒 | **A/B 探针实证**：umask077→2700 不可写 / 去 umask→2771 可写。对顶层与 `libyacurs/configure` 生成物剥 `umask 077 && `（E678 正解；`configure` 为 autoconf 生成物且本配方不跑 autoreconf ⇒ 生成物+可复现+每次重建三条件成立免登记，经 refresh_patch 落 0003/0006） |
| 8 | `curs.cc:198: error: use of undeclared identifier 'bindtextdomain'`（build 红） | 上游 tarball 自带 **in-source 陈旧生成物** `libyacurs/include/libyacurscfg.h`（`#define ENABLE_NLS 1`，上游打包机产物、上游 git 未跟踪、`.orig`/`.work` IDENTICAL 证非本方残留）；`curs.cc` 先 include build 树 `config.h`（NLS undef），随后 `yacurs.h:52` **引号包含**优先命中源码树同目录陈旧件把宏翻回 1，而 `gettext.h` 更早已按 undef 决定不 include `<libintl.h>` ⇒ 符号无声明 | `build()` 删除该陈旧源码件（`os.path.isfile` 判在删 + 删除后回读自证）；build 树由 config.status 生成正确副本（quote-include 回退 `-I` 命中） |
| 9 | Blowfish 三用例 `Error initializing cipher`（check 红） | `libcrypto.a` 内嵌 `MODULESDIR` 指向**已被清理的 conan build 缓存**（`~/.cache/conan2/p/b/opens…/ossl-modules` 实测不存在），host 包 `legacy.so` 不在默认搜索路径 ⇒ `OSSL_PROVIDER_load("legacy")` 返 NULL（OpenSSL 3 把 Blowfish 移入 legacy provider） | 测试期 `OPENSSL_MODULES=<openssl包>/lib/ossl-modules`（仓库先例 ppp/2.5.2、encfs/1.9.5；探针实证 load 成功 + `EVP_CipherInit_ex rc=1`）；另在 `package_info()` 以 `runenv_info.define_path("OPENSSL_MODULES", <openssl包>/lib/ossl-modules)` 注入**消费者 conanrun 运行期环境**（ppp `:119-120` 同构；配套把 openssl requires 标 `run=True`（ppp `:35` 同构），否则消费图跳过 openssl、`package_folder` 为 None 直接 G2 红——首轮实测）；A/B 实证：无变量 `Error initializing cipher` rc=1，设变量后 `OK (4 tests)` rc=0，日志 `$TASK_DIR/evidence/openssl-modules-ab-{without,with}.log` |
| 10 | provider 修好后仍 `Error encrypting data`（`EVP_CipherUpdate` 返 0） | 上游 `crypto.cc` 先 `EVP_CipherInit_ex(带key)`（按 BF 默认 16 字节建 key schedule）**之后**才 `set_key_length(56)`；OpenSSL 3 legacy BF 下 post-init 改长使 schedule 失效 ⇒ Update 直接失败。**且上游 fixture 是 16 字节语义**（改按 56 派生后 `foreign` 解密报 `Invalid password`，padding 错） | 保留上游 init 顺序，`set_key_length` 仅在 `keySize == EVP_CIPHER_CTX_key_length()` 幂等时应用（AES-256 默认 32=Key256 32 ⇒ 不受影响且 Aes256 有独立 `initializeOrThrow`；BF 16≠56 ⇒ 跳过，保持与 1.1.x/fixture 字节兼容）。三探针：order0 在 OpenSSL3 上 Update=0、order1 按 56 派生、同16前缀异尾判据证 16/56 差异。上游 TRACKED 源文件 ⇒ refresh_patch 落 0007 |
| 11 | `make` 红：`../../libtool: line 2639: func__fatal_error: command not found` + `libtool: error: cannot find name of object for 'testpreload.lo'` | **两层叠加**：①上游 `libyacurs/tests/preloadlib/Makefile.am:16` 把 `-shared` 硬编码进 `libtool --mode=compile` 规则，而配方曾传 `--disable-shared` ⇒ libtool `build_libtool_libs=no` ⇒ compile 见 `-shared` 即 `func_fatal_configuration "cannot build a shared library"`；②libtool 2.4.6 自身缺陷——`func_fatal_configuration()` 调用**从未被定义**的 `func__fatal_error`（双下划线；只有 `func_fatal_error` 单下划线在行 1303 定义）⇒ 真错误被 "command not found" 完全掩盖（手工逐字复现同一命令，rc=0 但无产物 `.libs/`） | 去掉 `--disable-shared`/`--enable-static`，让 configure 与**已验证的探索路径**逐字一致（explore 实测 shared=yes/static=yes 五步全绿）；`--disable-install` 本就使 libyacurs 走 noinst、不安装，shared/static 对交付物零影响（`readelf` NEEDED 仅 libc）。教训：**libtool 报 `func__fatal_error: command not found` 时先查 `build_libtool_libs` 与上游硬编码 `-shared`，不要被掩盖的文案带偏** |

## 源码修改

| 补丁 | 文件 | 内容 |
|------|------|------|
| 0001-build-aux-config.guess.patch | build-aux/config.guess | 整文件升级 2018-08-29 → 2026-05-17 + 注入 `*:HarmonyOS:*:*` 分支输出 `aarch64-unknown-linux-ohos` |
| 0002-build-aux-config.sub.patch | build-aux/config.sub | 整文件升级 2018-08-29 → 2026-05-17（认收 `linux-ohos`） |
| 0003-configure.patch | configure | 剥 `umask 077 && `（HMDFS 2700 不可写，问题 7） |
| 0004-libyacurs-build-aux-config.guess.patch | libyacurs/build-aux/config.guess | 同 0001（AC_CONFIG_SUBDIRS 子配置树自带副本） |
| 0005-libyacurs-build-aux-config.sub.patch | libyacurs/build-aux/config.sub | 同 0002 |
| 0006-libyacurs-configure.patch | libyacurs/configure | 同 0003（子 configure 有自己的 config.status） |
| 0007-src-libs-crypt-crypto.cc.patch | src/libs/crypt/crypto.cc | `set_key_length` 仅在与 ctx 当前键长幂等时应用（OpenSSL 3 + 上游 fixture 16 字节语义，问题 10） |
| 0008-tests-converters-Makefile.am.patch | tests/converters/Makefile.am | check-local 夹具 `/tmp/…` → `$(builddir)/…`（只读 /tmp） |
| 0009-tests-converters-Makefile.in.patch | tests/converters/Makefile.in | 同 0008 的**预生成 .in 面**——不改它则 make 触发 automake 再生成，而 CI worker 无 automake（§一.4）⇒ 设备绿 CI 红；双面齐改后无需 automake |

另有一处**源码树删除**不产生补丁（refresh_patch 跳过已删文件）：`libyacurs/include/libyacurscfg.h`
（上游 in-source 陈旧生成物，问题 8）—— 由配方 `build()` 删除并回读自证。

（0001–0009 由 `refresh_patch` 生成，两面登记 conandata `patches:` 与本 manifest `patches_applied`；9 个补丁均过 `git apply --check` 对 pristine 树自检）

## 依赖版本

| 依赖 | 版本 | 角色 |
|------|------|------|
| openssl | 3.0.21 | 硬依赖（AX_CHECK_OPENSSL 必需；EVP Blowfish/AES-256/SHA/RIPEMD160 符号探测） |
| argon2 | 20190702 | 硬依赖（PKG_CHECK_MODULES libargon2；密钥派生） |
| ncurses | 6.5 | 硬依赖（捆绑 libyacurs 的 ax_with_curses 探测） |
| cppunit | 1.15.1 | 硬依赖（PKG_CHECK_MODULES 无条件；make check 用例链接） |
| gettext | 0.22.5.1 | tool_requires（msgfmt） |

## 验证结果

上游 `make check`（沙箱 `HOME=$TASK_DIR/test-home`，探索树 out-of-source，全量重链接轮）：
- 声明 N = **102**（automake TESTS 注册 75 + check-local 块 27，逐项归因见 `reports/test-report.md`）
- 实跑 = PASS **35** + FAIL **6** + SKIP **56** + NOT_RUN **5** = **102**
- 6 条 FAIL 全部为 HMDFS 权限语义（`hasSecurePermissions` 要求 `st_mode==0600` 且 uid/gid 匹配，
  实测恒 `0660` + 共享属主映射 ⇒ 恒假，全设备可写路径遍历无一例外）
- 5 条 NOT_RUN = `tests/preload/check-local` 的 istty 门控 5 项（`istty` 返 1 ⇒ 上游 `if` 整块不进）
- `test_package` 消费者 8 例全绿（CLI 4 + 加密往返 2 + 负向 2）

```bash
# conan-verify：见 reports/conan-verify-report.md
```

## 注意事项

- 三种压缩格式（tar.xz/tar.gz/tar.bz2）sha256 天然不同，conandata 钉 **tar.xz** 面并在文件头披露双域同源证据。
- **产物实物（`make install DESTDIR=…` 清点 20 文件）= 仅 `bin/` + `share/`**：捆绑 `libyacurs` **不安装** —— 顶层 `configure.ac:143-144` 无条件向子配置注入 `--disable-install` ⇒ 走 `noinst_LTLIBRARIES`/`noinst_HEADERS`。故 `package_type = "application"`、`cpp_info.libs=[]`/`libdirs=[]`/`includedirs=[]`（G4 package_info↔产物树一致），三个 CLI 由 commands.json 软件级声明（R38）。
- `make check` 的 UI 交互套件（libyacurs `ui-interactive`）靠上游 preloadlib 返回 77 计 skip，实际读数以设备日志为准。
---

**编译结束**: 2026-09-24 22:15
**最终状态**: built
