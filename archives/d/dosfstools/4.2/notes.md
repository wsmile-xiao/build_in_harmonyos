# dosfstools 4.2 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-10-08
- 编译器: clang 15.0.4（OHOS SDK，aarch64），GNU Make 4.4.1，conan 2.29.1
- 状态: built

## 源码获取（R39 端点级实测，2026-10-08）

- **主源 = Debian pristine**：`https://deb.debian.org/debian/pool/main/d/dosfstools/dosfstools_4.2.orig.tar.gz`
  - HTTP **200**，**320917** 字节，sha256 `64926eebf90092dca21b14259a5301b7b98e7b1943e8a201c7d726084809b527`
  - 与 `dosfstools_4.2-1.dsc` 的 `Checksums-Sha256` 行**逐字节一致**；同池目录带上游 `.asc` 签名
    ⇒ 即上游 release tarball 的 pristine 副本（非 repack）
  - 同端点 http 形态实测 200 / 320917 B，sha256 相同；conandata.yml 采用 HTTPS 标量、**不加镜像前缀**
- **端点对照（分开报，超时 ≠ 不可达）**：
  | 端点 | 实测 |
  |---|---|
  | `github.com/dosfstools/dosfstools/releases/download/v4.2/dosfstools-4.2.tar.gz` | **HTTP 000**（连接级失败，connect-timeout 10s ×3 次） |
  | `download.savannah.nongnu.org/releases/dosfstools/dosfstools-4.2.tar.gz` | **HTTP 404**（236 B 错误页） |
  | `waterlan.home.xs4all.nl/dosfstools/dosfstools-4.2.tar.gz` | **HTTP 200** 但 12477 B，内容为软 404 页面（"Pagina niet gevonden"） |
- 结论：官方直链在本机不可取 ⇒ 按 R39 用 Debian pristine 作源并在正文/本笔记披露。

## 编译步骤

1. `preflight_check.sh dosfstools/4.2` → RC=0（未找到依赖声明 = 零三方依赖）。
2. `recipe-search dosfstools` → 语料 8245 条无相似配方，首稿走 conan-init 模板后手工定稿。
3. 框架裸构建（Step3–Step8 全绿）：
   `sh <src>/configure --prefix=$HOME/usr/local --build=aarch64-unknown-linux-gnu
   --sbindir=$HOME/usr/local/bin --enable-compat-symlinks` → `make -j1` →
   DESTDIR 安装 → `make -j1 check`（同一套上游测试）。
4. conan 配方构建（`conan-verify` G2 = `conan create`）：
   `configure --prefix=/ '--bindir=${prefix}/bin' '--sbindir=${prefix}/bin'
   --build=aarch64-unknown-linux-gnu CC=<clang> CXX=<clang++>
   --enable-compat-symlinks` → `make -j1` → `make -j1 check` →
   `make -j1 install DESTDIR=<package_folder>` → test_package（文件镜像断言链）。

## 遇到的问题与解决方案

| # | 问题（第一条真实错误） | 根因 | 解决方案 |
|---|---|---|---|
| 1 | `configure: error: cannot guess build type; you must specify one` | 2021 版 config.guess 不识 `HarmonyOS` uname（E007 族） | configure 传 `--build=aarch64-unknown-linux-gnu`（设备原生 aarch64） |
| 2 | `configure: error: no acceptable C compiler found in $PATH` | 设备只有 clang（无 gcc/cc），autoconf AC_PROG_CC 只探 `gcc`/`cc` | 先读 conf `tools.build:compiler_executables`、回退 `clang`，显式传 `CC=`/`CXX=`（R33 口径） |
| 3 | `config.status[750]: can't create ./confXXXXXX/subs1.awk: Permission denied` | HMDFS 下 `umask 077` 产生的 `drwx--S---` 临时目录属主写不进（E011/E114） | 配方 `replace_in_file(configure, "umask 077", "umask 022")`（保留真实临时目录创建，不改上游提交内容） |
| 4 | `xxd: Max 1 argument (see "xxd --help")` → 上游 40 条测试全 ERROR | 设备 `xxd` 是 toybox 简版（只收 1 个文件参数），上游测试按 vim 约定调 `xxd -r <in> <out>` | **环境层** wrapper 写入构建目录 `env-bin/` 并前置 PATH（把 stdout 重定向成第二个参数）；实测该逆变换与按地址寻址的参考实现**逐字节一致**（1000000 B）；⛔ 不打补丁、不改上游测试 |
| 5 | `cmp: Unknown option 'bytes=1M'` → 5 条 mkfs 基准测试 ERROR | toybox `cmp` 无 `--bytes`/`-n` 选项 | 同 4：`env-bin/cmp` wrapper 实现前 N 字节比较，无 --bytes 时原样转发设备 cmp |
| 6 | `make install`: `/bin/sh: install: inaccessible or not found`（Error 127） | 设备不带 `install`，GNU coreutils 装成 `ginstall`（E098 族） | 同 4：`env-bin/install` wrapper 优先转发 `ginstall`，否则内置 POSIX 拷贝实现 |
| 7 | 3 条 `check-{fat12,fat16,fat32}_first_cluster` FAIL：`Both FATs appear to be corrupt. Giving up.` | 上游 `test-fsck` 用 CWD 相对路径读 `<test>.args`（未加 `$srcdir`），VPATH 构建树里没有该文件 ⇒ 缺 `-F 1` 参数 | 把 3 个 `.args` 数据文件**复制**进构建树 `tests/`（上游文件原件未改）；修后 40/40 预期一致 |
| 8 | G2 `configure: error: working directory cannot be determined` | host profile `[buildenv]` 把 `CONFIG_SHELL`/`SHELL` 指到设备 hnp bash，该 bash 全目录 `getcwd()` 失败（E386）；`os.environ` 首钉无效（profile buildenv 后置覆盖） | 配方内 configure/make/install 每条命令都以 `env -u CONFIG_SHELL SHELL=/bin/sh …` 执行 |
| 9 | 框架 Step9 `conan-init --force` 用模板覆盖手写配方，导致 Step10 对模板建红 | 经验 12.60① 已记录该机制（libnewuoa 三轮假失败） | 配方定稿后按同一经验改走**独立 `conan-verify`**（其 create 不触发 init），提交前 `git show HEAD:<path>` 核对配方归属 |
| 10 | test_package 断言 `mkfs.vfat`/`fsck.vfat` 别名缺失 | 上游 `configure.ac` 的 `--enable-compat-symlinks` **默认 false** | 启用该上游开关（配方与 manifest 同步），别名由上游 install-exec-hook 生成，不做事后补链 |

## 源码修改

**无补丁**（`patches: {}`，`patches/` 目录为空）。上述 10 处适配全部落在
配方与构建环境层：3 个 `env-bin` wrapper、configure 参数、`replace_in_file`
一处、构建树数据文件复制。上游源码、测试脚本、Makefile 一律未改。

能力面披露：`mkfs.vfat`/`fsck.vfat` 在**普通文件镜像**上完整可用（S_ISREG
路径，非特权）；块设备与挂载面 `losetup -f --show` 实测 rc=1
Permission denied、`mount -o loop` rc=32、`/dev/loop0` 读 rc=1 Permission
denied（uid 非 root）⇒ 该面在本平台对非特权用户不可用，**不属本交付断言面**，
如实记录、不写成可用。

## 依赖版本

零三方依赖（仅 libc/musl）。构建工具：clang 15.0.4、GNU Make 4.4.1、
autoconf 2.72（设备）、conan 2.29.1。

## 验证结果

```bash
# 上游测试（conan create 内 build() 的 `make -j1 check`，2026-10-08）
# TOTAL: 40  PASS: 39  XFAIL: 1  FAIL: 0  ERROR: 0  SKIP: 0
#   （XFAIL = check-huge：上游就预期其失败的超大镜像用例）
# 五维账本：上游静态 40 / 可执行 40 / 实测通过 39(+1 预期失败) / skipped 0 / 失败 0
# 消费者测试（test_package，文件镜像 mkfs→fsck→fatlabel 断言链）
CONSUMER ASSERTIONS: 10/10 passed
# 配方门禁（G0/G1/G2/G3）全 PASS：conan-verify 2026-10-08 VERIFY_RC=0
```

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/mkfs.fat`、`bin/fsck.fat`、`bin/fatlabel` | 上游 sbin_PROGRAMS（conan 将 `--sbindir` 收到 `${prefix}/bin`） |
| `bin/mkfs.vfat`、`bin/fsck.vfat` 等 7 个别名 | 上游 install-exec-hook（`--enable-compat-symlinks`） |
| `licenses/COPYING` | GPL-2.0-or-later |

## 注意事项

- 本包无平台任务号（外部候选），PR 正文按白名单章节撰写；
  上游测试与消费者测试数字在正文 / 本笔记 / 报告三处同源。
- 框架 `build` 一条龙的 Step9 会覆盖配方（12.60①），本包配方门禁以
  独立 `conan-verify`（G0/G1/G2/G3 全 PASS）为准。

### 对话 #1

2026-10-08：取源（R39 端点实测）→ 预检零依赖 → 原生编译探能力面（判甲：
文件镜像路径全通）→ 配方首稿 commit → 框架裸构建 Step3–8 全绿 → 逐步修复
上表 10 处适配 → 独立 `conan-verify` G0/G1/G2/G3 全 PASS（上游 40 条测试
39 PASS + 1 XFAIL、消费者 10/10）。
---

**编译结束**: 2026-10-08 15:05
**最终状态**: built
