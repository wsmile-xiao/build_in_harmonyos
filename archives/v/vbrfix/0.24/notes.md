# vbrfix 0.24（vbrfixc）适配笔记

## 项目信息
- **软件名称**: VBRfix / vbrfixc（命令行 MP3 VBR 头修复工具）
- **版本**: 0.24（版本证据：`configure.in` 中 `AM_INIT_AUTOMAKE(vbrfixc,0.24)`、`vbrfixc.lsm` Version 0.24）
- **上游作者**: William Pye <will@willwap.co.uk>，GPL-2.0-or-later
- **源码**: 官方原站 `http://www.willwap.co.uk/Programs/vbrfix.php` 已失效（域名被抢注，
  HTTP 301 → guidenetworth.com，原始 tarball 不可达，web.archive.org 本机/CI 均不可达），
  改用 Debian 官方仓库 salsa.debian.org/debian/vbrfix 的 pristine upstream 标签 `upstream/0.24`
- **SHA256**: `bc770e24fd56f209292c69aea40e245c7472c80bf4f2211bfc896dc9c3ad51f5`
- **构建系统**: autotools（KDE/KDevelop 生成的 configure + make）

## 编译环境
- **目标平台**: HarmonyOS PC aarch64（uname -s = HarmonyOS，HongMeng Kernel 1.12.0）
- **编译器**: clang 15.0.4 / clang++（libc++），`/data/service/hnp/bin/clang`
- **Conan Profile**: `ci/conan/profiles/ohos-aarch64`（os=OHOS, arch=armv8, compiler=clang 15, libc++）
- **构建日期**: 2026-09-30

## 依赖
**无第三方依赖**：源码仅 `main.cpp` / `vbrfix.cpp` / `vbrfix.h` / `wputil.h`，
使用 C++ 标准库 + 由 configure 生成的 libtool 链接，无外部库。

W0 依赖发布检查（R36）：`conanfile.py` `requirements()` 为空，无待发布依赖。

## 编译过程

```bash
# 探索阶段（真实命令）
setopt ...; cd $BUILD_SRC_DIR
./configure --prefix=$DEFAULT_PREFIX
make -j4
make check            # 上游测试入口（空套件）
make install DESTDIR=$TEST_PREFIX
```

### 首个真实错误（E1）——config.guess 不认识 HarmonyOS

```
checking build system type... admin/config.guess: unable to guess system type
This script, last modified 2002-10-21, has failed to recognize
the operating system you are using.
configure: error: cannot guess build type; you must specify one
        （退出码 1）
```
- **根因**：上游 `admin/config.guess` / `admin/config.sub` 时间戳分别为 2002-10-21 /
  2002-09-05，不认识 HarmonyOS（`uname -s` 返回 `HarmonyOS` 而非 `Linux`），
  config.sub 也不认识 aarch64 CPU 与 `-linux-ohos` OS。
- **修复**（补丁 0001 / 0002）：为 config.guess 增加 `*:HarmonyOS:*:*` 分支，输出
  `aarch64-unknown-linux-ohos`；为 config.sub 增加 `aarch64` / `aarch64-*` CPU 与
  `linux-ohos` OS 白名单。**不用 `--build=`/`--host=` 绕过（R1）**。
- **重新验证**：`./admin/config.guess` → `aarch64-unknown-linux-ohos`；
  `./admin/config.sub aarch64-unknown-linux-ohos` → `aarch64-unknown-linux-ohos`；
  configure 输出 `checking build system type... aarch64-unknown-linux-ohos`（退出码 0）。

### 第二个真实错误（E2）——HMDFS 临时目录不可写

```
./config.status[582]: can't create ./confstathOcmbA/subs.files: Permission denied
./config.status[773]: can't create ./confstathOcmbA/config.h: Permission denied
./config.status[869]: can't open Makefile: No such file or directory
```
- **根因**：configure / config.status 用 `(umask 077 && mktemp -d ...)` 建临时目录；
  HMDFS 上该目录权限落为 `drwx--S---`（setgid 但无 group x），创建者自身也无法写入。
  命中知识库 **E011（edit-umask-in-configure）**。
- **修复**（补丁 0003）：`umask 077` → `umask 022`（configure 内 2 处 ×2 形态，共 4 行）。
- **重新验证**：configure 退出码 0，`Permission denied` 计数 0，成功生成
  `config.h` / `Makefile` / `vbrfixc/Makefile`。

### 第三个真实错误（E3）——现代 C++ 不可编译

```
./wputil.h:202:12: error: no viable conversion from returned value of type
    'std::ostream' to function return type 'bool'
    return out << in.rdbuf();
vbrfix.cpp:298:36: error: unknown type name 'uint'; did you mean 'int'?
    bool e=false;unsigned char c;uint correctv1=0,correctv2=0,p=0;
```
- **根因**：(a) libc++ 已移除 `std::ostream` 隐式 `operator void*`（`operator bool` 为
  explicit），老式 `return out << in.rdbuf();` 不再能隐式转 bool；(b) `uint` 是非标准
  类型（老 BSD `<sys/types.h>` 提供），libc++ 无此类型。
- **修复**（补丁 0004 / 0005）：`uint` → `unsigned int`；拷贝函数改为
  `out << in.rdbuf(); return !out.fail();`（语义等价于原隐式转换 `!fail()`）。
- **重新验证**：`make -j4` 退出码 0，`error:` 计数 0，产出
  `vbrfixc/vbrfixc`（ELF 64-bit LSB arm64，interp `/lib/ld-musl-aarch64.so.1`）。

## 源码修改
| 补丁 | 文件 | 说明 |
|------|------|------|
| 0001-admin-config.guess.patch | admin/config.guess | 增加 HarmonyOS 分支（+12 行） |
| 0002-admin-config.sub.patch | admin/config.sub | 增加 aarch64 / linux-ohos 识别 |
| 0003-configure.patch | configure | 临时目录 umask 077 → 022（4 行） |
| 0004-vbrfixc-vbrfix.cpp.patch | vbrfixc/vbrfix.cpp | 非标准 `uint` → `unsigned int` |
| 0005-vbrfixc-wputil.h.patch | vbrfixc/wputil.h | 显式 `!out.fail()` 取代隐式 ostream→bool |

补丁由 `ohc-run.py refresh-patch --auto vbrfix 0.24` 生成（编辑追踪器精准模式），
全部通过 `patch -p1 --dry-run` 干净校验。

## 上游测试
- 上游 **无自动化测试**：全树无 `tests/`/`test/` 目录，`Makefile.am` /
  `vbrfixc/Makefile.am` 无 `TESTS =` 声明，无 ctest/meson/pytest 入口；
  `make check` 实测退出码 0 且输出 `Nothing to be done for 'check'`（空套件）。
- 亦无上游样例数据文件。故上游用例数为 0（详见 `reports/test-report.md`）。
- 消费者侧测试由 `test_package/test_vbrfixc.sh` 提供：9 项用例（含 1 项鸿蒙特有），
  实际运行被测二进制并校验产物结构。

## 已知事项
- 上游 tarball 内含 32 位 x86 Linux 预编译二进制 `vbrfixc/vbrfixc`（Debian 因此做
  `+dfsg` 重打包剔除）。本配方构建时 `make` 会覆盖该文件，打包只取新构建的产物。
- 程序运行时在 CWD 生成 `vbrfix.tmp`（中间文件）与 `vbrfix.log`（日志句柄），
  属上游行为，与适配无关；测试在独立临时目录中执行。
## 提交前置门禁的已知冲突（PF9 ↔ CI L0k）与处置

本包为**首次适配**，按 ARCHIVE-SPEC v3.0 §2.1 必须在软件级目录新增
`archives/v/vbrfix/{README.md,commands.json,manifest.yaml}` 三个文件。

- **PF9 分支/路径闸**（`scripts/ohc/preflight.py:570`）判定
  `len(f.split("/")) < 5` 即拦，包级文件只有 4 段 → 命中：
  `PF9: 变更路径缺版本目录层 …… archives/v/vbrfix/README.md, commands.json, manifest.yaml`
- **CI L0k（R38）** 强制要求软件级 `commands.json`：
  `ci/conan/build_and_test.sh` 取 `PKG_SOFTWARE_DIR="$(dirname "$(dirname "$CONANFILE")")"`，
  本包 `package_type = "application"` 且 `cpp_info.bindirs = ["bin"]` 必然触发检查。
  → **删除包级 `commands.json` 会直接导致 CI L0k Hard Fail。**

即两条门禁互斥，且 PF9 的立论（"防 No packages to build"）不成立：
CI 的包发现只 `find … -name conanfile.py`（`ci/conan/build_and_test.sh:247`），
包级元数据文件不参与；CI 侧真实分支门禁 L0n 只校验**分支名**，不校验路径段数。

**处置（与仓库既有惯例一致）**：保留包级三件套，`create-pr` 时使用工具提供的
显式逃生口 `--no-preflight`（`scripts/gitcode_pr.py:293-307`，官方注释"自担风险"）。
比对先例：`641407c393`（roblox-ts 3.0.0，2026-09-30 合并）含完全相同的包级三件套；
抽查 vis / kweathercore / roblox-ts / usbmuxctl，包级 `commands.json` 与版本目录
`conanfile.py` **均在同一提交落地**，无"拆提交"先例。

**验证证据**：仅 PF9 命中，PF1/PF2/PF3/PF3b/PF4/PF5/PF6/PF7/PF8/R52 全部 PASS
（只读调用 `ohc.preflight.run_preflight` 逐闸取证）。
---

**编译结束**: 2026-09-30 09:04
**最终状态**: built
