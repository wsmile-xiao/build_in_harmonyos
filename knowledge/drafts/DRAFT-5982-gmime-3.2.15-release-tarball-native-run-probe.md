# DRAFT-5982-gmime-3.2.15-release-tarball-native-run-probe

> 草稿知识项 — autotools 依赖先判「release tarball 是否自带预生成产物」再决定是否自举；
> OHOS 原生构建用**等值**双三元组 `--build=aarch64-linux --host=aarch64-linux` 保留
> `AC_RUN_IFELSE` 运行探测。
> 来源：gmime 3.2.15 Conan 配方化（feat/gmime-3.2.15，task 5982，2026-09-13）
> 同 stem 配对：`knowledge/drafts/DRAFT-5982-gmime-3.2.15-release-tarball-native-run-probe.kv`

## 问题（现象 / error_signature）

- 依赖库的同一软件，**不同来源包**决定配方复杂度：
  - GitLab/GitHub 的 **git-archive 快照**只带 `configure.ac` / `Makefile.am`，
    配方必须自举 `aclocal/autoconf/autoheader/libtoolize/automake`，
    还常要补 `gtk-doc.m4`、`ChangeLog`、`gtk-doc.make` 等 automake 缺失输入；
    并因此需要 `automake`/`libtool` 的 `tool_requires`。
  - **上游 release tarball**（`make dist` 产物）自带 `configure`、各层 `Makefile.in`、
    `aclocal.m4`、`ltmain.sh`、`config.guess`、`config.sub`、`compile`、`missing`、
    `install-sh`、`depcomp`、`gtk-doc.make`，配方**无需自举、无需 automake/libtool
    tool_requires**。
- 交叉/原生判定不清时，configure 的 `AC_RUN_IFELSE` 运行探测（gmime 的
  `iconv-detect.c`，枚举目标 libc 支持哪些 charset 别名）会报
  `cannot run test program while cross compiling`，或被迫接受
  `ac_cv_have_iconv_detect_h=yes` 导致 `config.h` 与真机能力不符。

## 根因（root_cause）

1. 是否自举取决于**源码包是否已含生成物**，而非软件本身。gmime 3.0.5（旧配方）
   取自 GitLab git-archive，故需自举；3.2.15 改取上游 GitHub release tarball
   `gmime-3.2.15.tar.xz`，`configure`/`Makefile.in` 全在包内，自举步骤纯属冗余。
2. `AC_RUN_IFELSE` 是否可执行由 **build 与 host 三元组的相等性**决定：configure 在
   `build == host` 时按**原生**处理，运行探测真实执行；`build != host` 进入交叉模式，
   `AC_RUN_IFELSE` 走交叉分支报错或跳过。
   OHOS PC 的 CI 在**真机上原生构建**（`ci/conan/profiles/ohos-aarch64`，aarch64 OHOS），
   因此给出**等值**的 `--build=aarch64-linux --host=aarch64-linux` 即保持原生，
   让 iconv 探测正常跑完。（E007 所述「用 --build/--host 会误判为交叉编译」只在
   build≠host、或只给单一/不同三元组时成立。）

## 可复用方案（rec_approach: autotools-tarball-pregen-detect + native-equal-triplet）

1. **动手写自举前先查包内是否已有 `configure`**：
   ```bash
   tar -tJf gmime-3.2.15.tar.xz | grep -E '/(configure|ltmain\.sh|aclocal\.m4)$'
   ```
   有 → 配方不写 `aclocal/autoconf/automake/libtoolize`，也不加
   `tool_requires("automake/…")`、`tool_requires("libtool/…")`，只加
   `--disable-maintainer-mode` 关掉 `AM_MAINTAINER_MODE` 的重建规则即可。
2. **OHOS 原生构建显式传等值双三元组**：
   ```python
   tc.configure_args += ["--build=aarch64-linux", "--host=aarch64-linux"]
   ```
   保持 `build == host` → 原生模式 → `AC_RUN_IFELSE` 真机执行。
3. 原生模式下 configure 的 `umask 077` 临时目录在 HMDFS 首写被拒（E114）仍需
   改写为 `umask 022`；该点与三元组无关，独立保留。

## 适用条件

- 上游发布 **release tarball**（非 git 快照）的 autotools 软件；
- CI 目标为 **OHOS PC 真机原生构建**（build==host==aarch64-linux）；
- 存在依赖运行结果决定 `config.h` 的 `AC_RUN_IFELSE` 探测。

## 反例（不适用场景）

- 源码来源为 git-archive / `git clone`：无 `configure`，仍必须自举；
- 真·交叉编译（如 x86 主机构建 OHOS 目标）：build≠host，运行探测确实不可跑，
  此时才需 `ac_cv_*` 预置或按目标特性硬编码；
- 自带 tarball 但 `configure.ac` 比 `configure` 新（维护者模式会重生成）：
  仍须 `--disable-maintainer-mode`。

## 验证证据（真实命令 + 结果）

- `tar -tJf gmime-3.2.15.tar.xz | grep -c 'Makefile.in'` → 命中多份，包内自带生成物；
- 配方以 `--build=aarch64-linux --host=aarch64-linux --disable-maintainer-mode` 在
  OHOS aarch64 profile 下 `configure` 通过，`iconv-detect` 运行探测正常执行；
- 上游 `make check` 的 11 个 `AUTOMATED_TESTS` 全量执行。

## 限制与恢复条件

- 结论绑定该版本 tarball 结构；升级大版本须重新确认 `configure` 是否仍在包内；
- 若未来 CI profile 改为真交叉（build≠host），需撤掉等值三元组，改用
  `ac_cv_have_iconv_detect_h` 等缓存变量或按目标 libc 预置。
