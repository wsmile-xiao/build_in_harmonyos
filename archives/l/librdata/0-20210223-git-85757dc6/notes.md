# librdata 0-20210223-git-85757dc6 — 适配笔记

> 档案创建时间: 2026-09-20
> 最后更新: 2026-09-20
> 任务: 积分赛 · 设备单端工作区

## 一、基本信息
| 项目 | 值 |
|------|-----|
| 软件 | librdata（读写 R data.frame / RDS 的 C 库） |
| 版本 | 0-20210223-git-85757dc6（= 版本 0，日期 2021-02-23，git 短哈希 85757dc6） |
| 状态 | built（verify 通过；未 upload，故不标 published） |
| 构建系统 | autotools（GitHub archive 快照，树内无 `configure`，须 autoreconf 自举） |
| 源码 | https://github.com/WizardMac/librdata/archive/4a80bf3894c9250195a564017f2136fd85757dc6.tar.gz |
| 快照 commit | 4a80bf3894c9250195a564017f2136fd85757dc6（2021-02-23 "Improve support for MSVC"） |

**版本串形态说明**：上游无 release tag，只有 master 提交；`0-20210223-git-85757dc6` 的
日期取提交日、`85757dc6` 取该 commit 的**末 8 位**（不是前 8 位）。清点源码前先按
`git log --since/--until` 与 `git rev-list | grep '^…'` 双向核对，避免取错源。

## 二、编译阶段

### Phase 1: 环境准备
- [x] ✅ `task_init.sh librdata 0-20210223-git-85757dc6 --allow-unpublished`
      （`archives/l/librdata` 不在 `upstream/main`，**全新包**）
- [x] ✅ `init-build`（overlay；`--url` 权威源 + `--tar tar.gz`）→
      `$TMPDIR/builds/librdata-0-20210223-git-85757dc6.work`；
      sha256 = `b5d7745a41857c9d8658fa723dfd5fa7f0aecb9dd6de205c772779673780e23b`
      （gzip magic 1f 8b、顶层目录已核）
- [x] ✅ `lang-preflight`：task=cpp, detected=c → 语言匹配（C/C++ 兼容族），继续
- [x] ✅ 预扫描：发现问题列表为空；注意预扫描报 `has_tests: false` 是**假阴性**——
      上游 `Makefile.am` 有 `check_PROGRAMS = test_rdata` / `TESTS = test_rdata`，
      以 `make check` 的 `test-suite.log` 读数为准（见 Phase 3）

### Phase 2: 编译（autoreconf → configure → make）
- [x] ✅ `autoreconf --force --install`（tool_requires: automake/1.18 + libtool/2.5.4）
- [x] ✅ configure（`/system/bin/sh` 前缀 + `--build/--host=aarch64-unknown-linux-ohos`）
- [x] ✅ `make`（`-j2` 显式自限，避免 conan 默认 20 路超订）

### Phase 3: 测试验证
- [x] ✅ `make check` → `test-suite.log`：`# TOTAL: 1` / `# PASS: 1` / `# FAIL: 0`
- [x] ✅ 消费者测试（`test_package`）：23 处断言全通过（`.RData` + `.rds` 往返、
      错误串指纹、缺文件负向路径）

## 三、遇到的问题与解决方案

| # | 问题（原始报错） | 根因 | 解决方案 |
|---|------------------|------|----------|
| 1 | `configure.ac:17: error: possibly undefined macro: AM_ICONV`（autoreconf rc≠0） | `AM_ICONV` 宏来自 GNU gettext 的 `iconv.m4`；conan `gettext/0.22.5.1` 只装 bin/lib/include 不装 m4，HNP 也不带 → `aclocal` 找不到 | 补丁 `0001-configure.ac.patch`：改直接探测 libc 的 `iconv.h` 与 `iconv_open/iconv/iconv_close`（OHOS musl libc 自带），保留 `AC_MSG_ERROR` 硬失败 |
| 2 | `config.status[N]: can't create ./confKCKaCD/subs1.awk: Permission denied` → `could not setup config files machinery` | 生成的 `configure` 用 `(umask 077 && mktemp -d "./confXXXXXX")` 建临时目录；HMDFS 强制 setgid + 属主映射 ⇒ 落成 `drwx--S---`（mode `0o42700`，owner 20001006）而进程 euid 是 20020085 ⇒ 不可写（E114） | `build()` 在 `autoreconf` **之后**就地改生成 `configure`：去掉 `umask 077 &&` 前缀（含 fallback 分支），改后目录为 `drwxrws--x`；模式匹配不上就 `raise`（防静默失效） |
| 3 | `config.guess: can't create .../dummy.c: Permission denied` → `unable to guess system type` | 同一个 HMDFS 目录问题，由 `AC_CANONICAL_HOST` 触发 | configure 显式传 `--build=aarch64-unknown-linux-ohos --host=aarch64-unknown-linux-ohos`（automake 1.18 的 `config.sub` 已接受并规范化；build==host ⇒ 原生构建，`AC_CHECK_LIB` 做真实链接探测） |
| 4 | `Can't load .../perl5/5.42.2/.../Cwd.so for module Cwd: Perl_my_cxt_init: symbol not found`（autoreconf rc=255） | `tool_requires("autoconf/2.72")` 带出 conan `perl/5.42.2`，其 buildenv 把 `PERL5LIB` 指向自己的 XS 模块；而 `autoreconf` 解析到 `/data/service/hnp/bin/autoreconf`（shebang 钉死 HNP perl 5.42.0）⇒ 两套 perl 混用 | `tool_requires` 只放 `automake/1.18` + `libtool/2.5.4`；HNP 自带 autoconf 2.72 + m4 1.4.20 + perl 5.42.0。实测同一命令由 rc≠0 变 rc=0 |
| 5 | `AC_CHECK_LIB([z],[deflate])` 会命中 sysroot 的 `libz.so` | OHOS sysroot 的 `libz.so` 是 stub（13888 B、符号同址、SONAME=`libz.so`），而 `/system/lib64` 下无该文件、运行期只有 `/usr/lib/libz.so.1` ⇒ 命中就写进 `DT_NEEDED`，运行期装载失败 | 三个压缩后端走 Conan（`zlib/1.3.1.1`、`bzip2/1.0.8.2`、`liblzma/5.8.1`），并显式 `AutotoolsDeps(self).generate()` 注入 `CPPFLAGS/LDFLAGS/LIBS`（`AutotoolsToolchain` 自身不注入依赖 `-I/-L/-l`）；三者均静态制品，交付 `.so` 的 `DT_NEEDED` 只剩 `libc.so` |
| 6 | `make: jobserver mkfifo: …: Operation not permitted` | 设备拒绝 `mkfifo`（SELinux/HMMAC），make 自动退化 pipe jobserver，**并发未退化**（已知噪声） | 不处理；`make` 显式 `-j2` 自限（conan 默认 `os.cpu_count()`=20，本机 affinity 更小） |

## 四、源码修改清单

| 文件 | 原因 | 方式 | 补丁状态 |
|------|------|------|---------|
| `configure.ac` | `AM_ICONV` 需要 gettext 的 `iconv.m4`，工具链闭包内没有 | 补丁改 libc iconv 直接探测 | `patches/0001-configure.ac.patch` |
| 生成的 `configure` | E114：`umask 077 && mktemp -d` 在 HMDFS 上不可写 | conanfile 在 autoreconf 后就地改写 | 不进 `patches/`（configure 是 autoreconf 产物） |

## 五、依赖版本

| 包 | 版本 | 作用 | 制品形态 |
|----|------|------|---------|
| zlib | 1.3.1.1 | RData gzip 后端 | `libz.a`（静态） |
| bzip2 | 1.0.8.2 | RData bzip2 后端 | `libbz2.a`（静态） |
| liblzma | 5.8.1 | RData xz 后端 | `liblzma.a`（recipe 声明 shared=True，制品实为静态库） |
| automake | 1.18 | autoreconf 自举（aclocal/automake/config.sub） | tool_requires |
| libtool | 2.5.4 | `LT_INIT` / libtoolize / ltmain.sh | tool_requires |

## 六、验证结果

```bash
# 上游测试（build() 内，automake 框架；N=1 即框架注册数）
make check   # → # TOTAL: 1 / # PASS: 1 / # FAIL: 0

# 交付物
conan cache path librdata/0-20210223-git-85757dc6
#   shared=False（默认）: lib/librdata.a + include/rdata.h
#   shared=True         : librdata.so.0.0.0 + librdata.so.0 + librdata.so + include/rdata.h

# ELF 体检（shared 配置）
llvm-readelf -d librdata.so.0.0.0 | grep -E 'SONAME|NEEDED|RUNPATH'
#   (NEEDED)  Shared library: [libc.so]
#   (SONAME)  Library soname: [librdata.so.0]
#   （无 RPATH/RUNPATH）

# 裸环境装载（不注入 LD_LIBRARY_PATH，避免 conanrun 掩盖 RUNPATH 问题）
env -u LD_LIBRARY_PATH python3 -c "import ctypes; ctypes.CDLL('<path>/librdata.so.0.0.0')"
#   dlopen OK
```

## 七、注意事项

- **`test_rdata` 只在失败时写 `/tmp/rdata_test.RData`**：设备 `/tmp` 只读，该诊断
  落盘会静默失败（`open` 返回 -1 但未判错）。仅影响失败路径的取证，不影响判定；
  复核失败时请用 `$TMPDIR` 下的自建驱动，不要指望那个文件。
- **`liblzma/5.8.1` 的 recipe 声明 `shared=True`，制品却是 `liblzma.a`**：这是上游
  制品既有状态，本包未改它。效果是静态内链（`DT_NEEDED` 无 `liblzma.so`），符合
  R26 口径；不要为「名实相符」去改它的选项——ohpcd 只有这一个 binary，改选项会让
  W0（`conan install --build=never`）失败。
- **`prescan` 报 `has_tests: false` 是假阴性**：上游测试写在 `Makefile.am`（automake
  的 `TESTS`），prescan 不识别该形态。
- 采信轮与 CI 都走 `ci/conan/profiles/ohos-aarch64`（**绝对路径**）；相对名 `-pr`
  会先命中 `$CONAN_HOME/profiles/` 下的陈旧同名副本。
- **static 配置下 `make install` 会重跑 `ranlib`**，故交付 `librdata.a` 与 `.libs/librdata.a`
  的 sha256 不同属正常；`.so` 的安装前后 sha256 必须一致（本包实测一致，
  见 `reports/conan-verify-supplement.md`）。

---

**编译结束**: 2026-09-20
**最终状态**: built
