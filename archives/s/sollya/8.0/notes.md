# sollya 8.0 适配笔记

## 编译环境
- 构建系统: autotools（`configure.ac` + `autogen.sh` → `autoreconf -i`；**归档不带预生成 `configure`**）
- 编译日期: 2026-09-23
- 编译器: clang / clang++ 15.0.4（`Target: aarch64-unknown-linux-ohos`，C++ 运行时 **libc++**）
- 状态: built

## 编译步骤

原生探索（阶段 C）在沙箱外的探索树 `$WORKSPACE_ROOT/tmp/builds/sollya-8.0.work` 逐轮「一跑一修」共 **R1→R7 七轮**收敛，最终成功形态如下（配方 `conanfile.py` 与此同构）：

1. **conan build env**（只补设备/CI 真缺的工具，**不 tool_requires autoconf**，理由见下）：
   ```sh
   conan install --requires=gmp/6.3.0 --requires=mpfr/4.2.2.1 --requires=mpfi/1.5.4 \
     --requires=libxml2/2.15.3.1 --requires=fplll/5.5.0 --requires=zlib/1.3.1 \
     --tool-requires=libtool/2.5.4 \
     -pr:h=$REPO/ci/conan/profiles/ohos-aarch64 -pr:b=$REPO/ci/conan/profiles/ohos-aarch64 \
     --build=missing -g VirtualBuildEnv -g VirtualRunEnv -g PkgConfigDeps -of <env>
   ```
   `-pr:h` 与 `-pr:b` **同用 `ohos-aarch64`**（CI `build_and_test.sh:316` 同构；残缺的 `default` profile 会让 tool_requires 全部 `Invalid`）。
2. **源文件补丁（在 autoreconf 之前）** → 3. `autoreconf -i` → 4. **剥生成物 `configure` 的 `umask 077`** →
5. `configure`（关键参数）：
   ```sh
   ./configure --build=aarch64-unknown-linux-ohos \
     --prefix=<PREFIX> \
     --with-gmp=<gmp pkgdir> --with-mpfr=<mpfr pkgdir> --with-mpfi=<mpfi pkgdir> \
     --with-xml2=<libxml2 pkgdir> --with-fplll=<fplll pkgdir> --with-z=<zlib pkgdir>
   ```
6. `make -j4`（原生探索用 `-j4` + 注入 pipe jobserver；配方 `build()` 用 `-j1`，理由见「注意事项」）→
7. `make install DESTDIR=<staging>` → 8. `HOME=<sandbox> . <env>/conanrun.sh && make check`（**必须载入 `conanrun`，否则 0 PASS**，见发现 4）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `conan install` 的 tool_requires 全部 `- Invalid: 'settings.os.version' value not defined`（补 os.version 后又报 `'settings.compiler'` not defined） | 用了残缺的 `--profile:build=default`（只有 `arch/build_type/os`），而 tool_requires 在 **build context** 解析 | `-pr:h=<ohos-aarch64> -pr:b=<ohos-aarch64>` 同一双用（CI `build_and_test.sh:316` 实测同构；该 profile 含 `os.version=6.0/compiler=clang/15/libc++/cppstd=17`） |
| 2 | 未经 `tool_requires autoconf` 则无毒；一旦引入，`autoreconf` 有崩溃风险 | conan 的 `autoconf/2.72` 拉 `perl/5.42.2` 并 `export PERL5LIB` 指向它，与 HNP 自带 perl **5.42.0** ABI 错配 ⇒ `Perl_my_cxt_init` 崩溃（device-facts §一.23 毒丸）。实测 `conanbuildenv-*.sh:35` 确有该 `export` | **只 `tool_requires(libtool/2.5.4)`**（设备已有 harmonybrew autoconf 2.73/automake 1.19/aclocal）；脚本内加 `case` 防护：`PERL5LIB` 含 `.conan2/p/perl` 即 `unset`。实测只给 libtool 时 build requirements 仅 `libtool/2.5.4`、不拉 perl |
| 3 | `make: jobserver mkfifo: … Operation not permitted` | device-facts §一.13 噪声；**且** `tools/make_jobserver.sh` 只**定义** `make_pipe_jobserver()`（注释「被 source，不单独执行」）——只 `source` 未**调用**是噪声照报的真因 | `. make_jobserver.sh` 后**调用** `make_pipe_jobserver`（注入 `--jobserver-style=pipe`）；实测 `step0_makeserver_pipe=0`、`MAKEFLAGS` 得 pipe 形态 |
| 4 | `configure: error: cannot guess build type; you must specify one`；给了 `--build` 后又报 `config.status: error: could not setup config files machinery`（`./confXXXXXX/subs1.awk: Permission denied`） | **两道关叠加**：① 上游 `config.guess` 不认 `uname -s=HarmonyOS` / `uname -r=HongMeng Kernel 1.12.0` ⇒ 转 fallback 自编译探测；② fallback 与 `config.status` 都用 `(umask 077 && mktemp -d "./confXXXXXX")`，HMDFS 强制 setgid 使其落盘 `0o2700`（A/B 实测：同法 `0o2700` **WRITE FAIL**；普通 `mkdir 0700` 落盘 `0o2771` **可写**），而进程 `euid=20020085` 非属主、目录 `gid=1006` 不含该 egid ⇒ other 位无 w（= **E114**，§一.10 变体） | ① `configure --build=aarch64-unknown-linux-ohos`（取值=本机 clang `Target`，`config.sub` 实测认识；给后 `config.guess` 完全不再调用，自证 `config.guess`/`cannot guess` 命中 **0**、走到 `creating ./config.status` **1**、`configure: error` **0**）② 剥生成物 `configure` 两处 `umask 077`（`_drop_umask_077()`，每次 `build()` 执行） |
| 5 | `ld.lld: error: unable to find library -lstdc++`（`libsollya.la` 链接失败） | 三层叠加：① libtool 链 `.so` 必加 **`-nostdlib`** ⇒ clang driver 不再注入标准库处理、**不做 `-lstdc++→libc++` 内部映射**；② 上游硬编码 `-lstdc++` **排在 SDK `-L` 之前**，而 **lld 按位置向左解析 `-L`**；③ 文件系统**无 `libstdc++` 实体**（`find -name 'libstdc++*'` 空；SDK 只有 `libc++*`）。上游 `configure.ac:678-690` 用 `AC_COMPILE_IFELSE`（**只编译不链接**）测链接选项 ⇒ `LIBS` 恒保留 `-lstdc++`（生成 `Makefile:425` 可证）；改 `AC_LINK_IFELSE` 也修不了（configure 阶段走裸 clang、无 `-nostdlib`，探测恒过） | 两个**上游源文件补丁**（`refresh-patch` 登记）：`ADD_LSTDC="yes"→"no"`、`tests-lib/Makefile.am` `LDADD` `-lstdc++→-lc++` |
| 6 | **`make check` 0 PASS**（`tests-tool` 32/32 FAIL）+ **tests-lib 根本没跑**（N′ 缺主体 348） | **编译期 `-L` 只作用于链接，运行期 loader 只看 `RPATH`/`LD_LIBRARY_PATH`/默认路径** ⇒ 找不到 `libfplll.so.9`/`libxml2.so.16`/`libmpfi.so.0`（6 条 `Error loading shared library` + 292 条 `symbol not found`）⇒ `.output` 恒空（`diff` 形如 `0a1,269`）；tests-tool 失败使**顶层 `check-recursive` 直接退出** ⇒ tests-lib 未执行 | `make check` 前 `. <env>/conanrun.sh`（conan 标准，与配方 `autotools.make(target="check", env=["conanbuild","conanrun"])` 同构、不产生本地绿 CI 红）。直读 rc 三 case：无 env **rc=127**；`conanrun` **rc=0**、输出 84 行；手动 LDP 亦 rc=0 |
| 7 | **CI（PR #12419 构建 #59839）`conan-build-test` ❌**：`make check` 在 `tests-tool` 链接步爆 `Error loading shared library libxml2.so.16: (needed by …/llvm/bin/lld)` + 17 条 `Error relocating … xml*: symbol not found` → `clang-15: error: unable to execute command` → `make[3]: *** [Makefile:1287: libraryexample.a] Error 1` → `conanfile.py:277` | `env=["conanbuild","conanrun"]` 的 wrapper **先 source `conanbuildenv`（profile 注入 SDK `llvm/lib`）再 source `conanrunenv`**，而 runenv 把 conan libxml2 等宿主依赖 libdir **前置到 `LD_LIBRARY_PATH` 最前** ⇒ SDK `lld` 首先撞上 worker 缓存里**存在但不可加载**的 conan `libxml2.so.16`；musl 命中同名不可加载条目即**硬失败、不回退**后面的 `llvm/lib` 与 RUNPATH（本地空文件复现**逐字同**：1 + 17 行、rc=127；本机 conan 副本可加载 `env -i LD=<conan libdir> lld --version` rc=0 ⇒ 设备采信轮绿、CI 红）。构建阶段仅 source `conanbuildenv`（`llvm/lib` 在最前）故 CI 走到 `make check` 才炸 | `make check` 命令**行内前置** SDK `llvm/lib`：`LD_LIBRARY_PATH="<sdk>/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" make -j1 check`（`_sdk_xml2_libdir()` 从 compiler realpath 推导并验 `libxml2.so.16` 实存；行内前缀在两份 env 脚本 source **之后**生效、追加语义保留 conan 运行期目录——`Environment().define` 会被 source 覆盖，cvsgraph 草稿实证）；`test_package/test()` 同法（`bin/sollya` 同样 `DT_NEEDED libxml2.so.16`）。本地探针：坏条目在前 rc=127 报错逐字、SDK 目录在前同条件 rc=0 |

## 源码修改

两个补丁均为 **tarball 上游源文件**，经 `refresh-patch --auto` 生成并以 `patch --dry-run -p1` 对纯净副本核验可干净应用（`conandata.yml` 已登记）：

| 补丁 | 内容 | 分类 |
|---|---|---|
| `patches/0001-configure.ac.patch` | `ADD_LSTDC="yes"` → `"no"`（使生成的 `LIBS` 不再保留 `-lstdc++`） | `type: portability` / `platform_only: False` / `guard: none` |
| `patches/0002-tests-lib-Makefile.am.patch` | `LDADD = $(top_builddir)/libsollya.la -lstdc++` → `-lc++` | 同上 |

> 另有一处**生成物**改动不作为补丁登记：`_drop_umask_077()` 只改 `autoreconf` 生成的 `configure`（不进 git、每次重建、留痕在 `build()` 代码里）——符合本工作区 2026-09-23 裁定的免登记三条件；**动 tarball 上游文件则必须走 `refresh-patch`**（本次两补丁即如此）。

## 依赖版本

| 依赖 | 版本 | 类型 |
|---|---|---|
| gmp | 6.3.0 | 运行（`.a` 静态链入） |
| mpfr | 4.2.2.1（库版本 4.2.2） | 运行（`.a` 静态链入） |
| mpfi | 1.5.4 | 运行（`.so`） |
| libxml2 | 2.15.3.1（库版本 2.16.x） | 运行（`.so`） |
| fplll | 5.5.0 | 运行（`.so`，`--with-fplll` 注入） |
| zlib | 1.3.1 | 运行（`.a` 静态链入） |
| automake | 1.18 | 构建工具（`tool_requires`，CI 缺） |
| libtool | 2.5.4 | 构建工具（`tool_requires`，设备/CI 均缺） |
| autoconf | **未 tool_requires** | 用设备 harmonybrew 2.73（CI 用 `/data/service/hnp/bin` 自带）；引入 conan 版会触发 §一.23 perl 毒丸 |

**诚实口径（不得表述为「依赖全部预编译在档」）**：`fplll/5.5.0` 的唯一远端 binary 绑 `gmp/6.3.0`，而 `mpfi/1.5.4` recipe 是 `self.requires("gmp/6.3.0.1", force=True)`，二者互斥 ⇒ `--build=never` 下 **fplll 缺 binary、须 `--build=missing` 本地编译（+≈20min/干净轮）**；CI `build_and_test.sh:321` 同为 `--build=missing`，行为同构自愈。

## 验证结果

### 上游测试（AGENTS §3.5，两口径清点 + 实跑）

**N = 381**（框架注册数 `TESTS` 展开 348+33 与文件对数 348+33 **两口径一致、差额 0**；差额归因：`tests-lib/*.c` 349→348 的唯一差 = `libraryexample.c`，属 `check_LIBRARIES` 库链接示例、无 `.reference`、不进 `TESTS`，**不计入 N**）

**N′ = 381 = 380 PASS + 1 SKIP + 0 FAIL + 0 NOT_RUN**（`N′ == N`，无未运行 ⇒ 无需申报技术原因）

| 分类 | tests-lib | tests-tool | 合计 |
|---|---|---|---|
| TOTAL | 348 | 33 | **381** |
| **PASS** | 348 | 32 | **380** |
| **FAIL** | 0 | 0 | **0** |
| **SKIP** | 0 | 1（`timecheck.sh`） | **1** |
| NOT_RUN | 0 | 0 | **0** |

- 恒等式：`381 = 380 + 0 + 1 + 0` ✅　通过率：**380/381 = 99.74%**
- 唯一非 PASS = `timecheck.sollya`，上游以 `MAYFAIL` 声明、`RETURN_CODE_IN_CASE_OF_FAILURE=77` = **automake SKIP 码**（计入 N、判读归 SKIP，**非失败、非环境缺口**）
- 判读边界已核：输出写 **cwd 非 `/tmp`**（§一.1 不适用）；`diff` = **GNU diffutils 3.10** 非 toybox（§一.24 不适用）；`PERL5LIB` 未设（§一.23 不适用）
- 取数命令与逐字 `test-suite.log` 读数见 `$TASK_DIR/test-count.md`

### 鸿蒙特有测试（rule12，≥1）

**`test_package` 在 OHOS/aarch64/musl 目标平台直跑已安装 `bin/sollya --version`，断言 4 重「产物自报指纹」（`assertion_count: 4`）** —— 该运行时证据**只在鸿蒙目标平台产生**（上游 CI 与 x86 CI 均不产生），且同时实证本任务的三处鸿蒙适配：`--build=…-ohos` 与 `--with-*=<conan package_folder>` 注入生效（FPLLL 配置自报）、E114 剥离后 `config.status` 能完成、loader 经 `conanrun` 找到运行期共享库。

断言（逐字自 `sollya --version` 84 行输出）：

1. `This is sollya 8.0` —— `PACKAGE_STRING` 版本自报
2. `This build of sollya 8.0 is based on GMP 6.3.0, MPFR 4.2.2 and MPFI 1.5.4.` —— **一行同时自报三个实链依赖库版本**（非空壳）
3. `It uses FPLLL as:` + `fplll.h lies directly in the include directory, linkage with -lfplll is compatible, -std option is passed (-std=c++11), using standard API.` —— **`--with-fplll` 注入生效自证**
4. `CeCILL-C` —— license 自报，与配方 `license = "CeCILL-C"` 互证

### 构建与安装产物

- `libsollya.so.8.0.0`（+`.so.8`/`.so`/`.la`）、`libsollya.a`、`bin/sollya`、`include/sollya.h`、`include/sollya-messages.h`、`share/man/man1/sollya.1`
- `sollya` 在构建树中是 **libtool wrapper**（bash script），真二进制为 `.libs/sollya`（ELF arm64 174720B、`/lib/ld-musl-aarch64.so.1`）
- staging 形态为 `staging/<绝对 prefix>/…`（`DESTDIR` + 绝对 `--prefix` 的正常双层）；conan `package()` 用 `Autotools.install()` 装入 `package_folder`（单层，无此双层问题）

## 注意事项

1. **W0-1 版本偏差（须在 PR 正文与 final-report 单列）**：上游**无 `8.0` 正式 tag**（`git ls-remote --tags` 全量 25 行、最高 `sollya-7.0`）；源 = **分支 `sollya-8.0` 的 commit 归档**（commit `587cb7cf9375110c495934e08b5af06ede3aa9e3`），内证 `AC_INIT([sollya], [8.0], …)` + 两次独立下载 sha256 一致 `d592496394c3bd7d00a2f7fb17e8cf4da6d28b5bb284bbd9f79f441c15d588fe`。**分支可 force-push ⇒ 版本未冻结：sha256 不符即响亮失败，不静默。**
2. **依赖不得表述为「全部预编译在档」**：见上「依赖版本」的诚实口径（`fplll` 需 `--build=missing` 本地编译 +≈20min/干净轮，CI 同构）。
3. **原生探索与配方的 `make` 并行度不同**：探索用 `-j4`（注入 pipe jobserver），配方 `build()` 用 **`-j1`**（device-facts E074「HMDFS jobserver fifo EPERM」+ 参考配方 abiword 同款先例）。**并行度只影响 wall time、不改变测试语义**，非测试口径差异。
4. **工具版本差异（防 W4 误判文档不符）**：conan 档案 `autoconf=2.72`/`automake=1.18`，设备 harmonybrew `2.73`/`1.19` —— 原生探索阶段用 harmonybrew、配方阶段经 `tool_requires` 用 conan 版（**故意不用 conan autoconf**，见发现 2）。
5. **`sollya --version` 的 FPLLL 自报行含构建期依赖路径**（原生探索时为 `…/deps-deploy/…/armv8/…` 任务私有路径）—— 引用进 PR 正文/日志时须说明或脱敏，勿当作跨机可复核路径。
6. **`upstream/main` 在任务期间已前移**（建分支基线 `59eaed1f6` → 现 `3f2ab627`）；本分支落后**不阻塞**（AGENTS §3.1），`pr.diff` 用 `upstream/main...HEAD` 三点取 merge-base，故**只含本任务改动**。
7. **知识沉淀**：路径 B 草稿 `knowledge/drafts/DRAFT-E678-sollya-autotools-config-guess-status-hmdfs-harmonyos.{kv,md}`（`yaml.safe_load` 回读 OK、`error_signature` 5 子模式对 5 条真实原文 **5/5 命中零死签**、`prescan_pattern` 可 `re.compile` 且正向命中 `AC_INIT(`）；manifest `knowledge_gained` 两条均带行尾 `# knowledge_ref: E678`。
---

**编译结束**: 2026-09-24 14:58
**最终状态**: built
