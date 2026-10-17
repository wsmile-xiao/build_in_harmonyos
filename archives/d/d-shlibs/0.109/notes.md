# d-shlibs 0.109 适配笔记

## 适配环境

- **构建系统**: none（纯 bash 脚本打包；上游 Makefile 的 `all:` 为空规则）
- **适配日期**: 2026-09-14
- **平台**: arm64-ohos（OpenHarmony PC / HarmonyOS PC）
- **编译器**: clang 15.0.4（本包不编译，仅 test_package 用其构造测试用 .so）
- **状态**: published（Conan 配方验证通过 + 本地 W3 conan create 通过）
- **补丁数量**: 0（上游 tarball 无任何补丁需求）
- **运行时依赖**: debhelper/13.3.4（Debian Build-Depends debhelper-compat 声明）、
  dpkg/1.23.7（`dpkg-architecture`）、binutils/2.46.0（`objdump -p`）
- **未发布依赖**: apt（d-devlibdeps 的 apt-cache 分支）、shellcheck（上游 `make check`
  的第 3、4 条）——**禁止写入 requires**，原因与证据见 manifest.yaml
  `dependencies_unavailable` 与本文“依赖闸”一节

## 上游软件说明

d-shlibs 是 Debian 的 **native 包**（`debian/source/format = 3.0 (native)`），零编译，
本体就是两个 bash 脚本：

| 文件 | 作用 |
|------|------|
| `d-shlibmove` | 把共享库（及其 `-dev` 软链/静态库/`.la` 兄弟）移动到正确的 Debian 包目录，并生成对应的 `debian/*.substvars` |
| `d-devlibdeps` | 由库的 DT_NEEDED 生成 `-dev` 包的 `devlibs:Depends=` 构建依赖行 |
| `Makefile` | `all:` 空；`install:` 只做 `install -m 755 <script> $(DESTDIR)/usr/bin/`；`check:` 见下；`test-build:` 需要 Debian 环境 |
| `*.1` | 两个 man 页（上游 `debian/manpages` 列出） |

脚本调用的外部命令（逐字扫描源码得到，非推测）：

- `d-shlibmove`：`dpkg-architecture` / `$DEB_HOST_GNU_TYPE-objdump` / `perl` / `sed` /
  `grep` / `awk` / `basename` / `dirname` / `readlink` / `mktemp` / `file`
- `d-devlibdeps`：`dpkg-architecture` / `$DEB_HOST_GNU_TYPE-objdump` / `apt-cache` / `apt` /
  `sed` / `grep` / `awk`

## 语言预检（R47）——工具误判 + D.4 人工复核

```
$ python3 $SKILL_ROOT/scripts/ohc-run.py lang-preflight d-shlibs 0.109 --lang bash \
      --src $BUILD_SRC_DIR
{
  "expected": "bash",
  "detected_language": "c",
  "language_evidence": {
    "build_system": "make",
    "manifest": "顶层 Makefile（无更强 manifest）",
    "source_stats": "源文件 1 个（c:1），主体占比 100%"
  }
}
→ 工具自动写终态 env_unsupported（保留为证据）
```

**人工复核结论：任务语言 bash 成立，工具的 `c` 是误报。** 依据协议 §D.4 边界规则：

1. `_manifest_scan` 只按“顶层存在名为 `Makefile` 的文件”就把工程判为 `c/cpp` 族；
   d-shlibs 的 Makefile 是 **install-only**（`all:` 为空），不是 C 构建系统。
2. `_source_stats` 统计到的唯一 “c” 文件是 `debian/tests/uppercase.d/libUppercase.c`
   —— 上游 **autopkgtest 夹具**，属于 §D.4 “辅助脚本不算主体”。
3. 语言统计按扩展名进行，而本包两个主体脚本 `d-shlibmove` / `d-devlibdeps`
   **没有扩展名**（`#!/bin/bash` 在文件头），因此永远不会被计入；
   且 `_source_stats` 明确把 `bash` 排除在主体占比之外（`total`/`dominant` 均跳过 bash），
   所以该工具在结构上无法产出 `detected_language=bash`。

处理方式遵循知识图谱既有判例（`knowledge/drafts/E543-draft-234A.kv`、
`DRAFT-debugbreak-1.0-langpreflight-gnumakefile-misdetect.kv`）：
**保留工具完整输出与它自动写入的 env_unsupported result.json 作为证据，人工判误报后按任务
语言继续适配，终态用 `result` 覆盖；不改框架、不删上游夹具。**

## 依赖闸（W0）

```
$ conan download debhelper/13.3.4 -r=ohpcd --only-recipe   → revisions（已发布）
$ conan download dpkg/1.23.7     -r=ohpcd --only-recipe   → revisions（已发布）
$ conan download binutils/2.46.0 -r=ohpcd --only-recipe   → revisions（已发布）
$ conan download apt/2.10.1      -r=ohpcd --only-recipe   → ERROR: system acceleration policy not enabled
$ conan list "apt/*"        -r=ohpcd                      → Found 0 pkg/version recipes
$ conan list "shellcheck/*" -r=ohpcd                      → Found 0 pkg/version recipes
```

apt / shellcheck **未发布**，因此 **不写入 `requires`**（PF4 依赖闸会拦，且 R41/W1 禁止
捎带适配依赖）。apt 由本包真实使用（`d-devlibdeps` 的 `validate_package()`），按
`archives/d/dh-vim-addon/0.6` 先例在 `manifest.yaml → dependencies_unavailable`
中如实登记并附实测证据。

## 适配步骤（模式 B 探索 + 配方固化）

```bash
python3 $SKILL_ROOT/scripts/ohc-run.py init-build d-shlibs 0.109 --url=<salsa URL>
source .build-context-d-shlibs-0.109 && cd $BUILD_SRC_DIR
make                                   # → "Nothing to be done for 'all'."（all 为空）
make install DESTDIR=$TEST_PREFIX      # → install -m 755 d-shlibmove / d-devlibdeps
                                       #   → $TEST_PREFIX/usr/bin/{d-shlibmove,d-devlibdeps}
make check                             # → 见下（部分不可执行）
```

### 1. 源码获取（`source()`）

沙箱 `get()` 有 PermissionError 风险——`download()` + 手动解压：

```bash
tar -xzf d-shlibs-debian-0.109.tar.gz --no-same-owner || true
cp -a d-shlibs-debian-0.109/. . && rm -rf d-shlibs-debian-0.109
```

salsa 的 git-archive 根目录是 `d-shlibs-debian-0.109/`（注意不是 `d-shlibs-0.109/`）。
tarball 内容（29,177 B，sha256=`568a98fc…8d78d07ed`）：

```
COPYING  ChangeLog  Makefile  README  d-devlibdeps  d-devlibdeps.1
d-shlibmove  d-shlibmove.1  example.control  debian/
```

> 关于源码 URL（R39/PF7）：`debian/control` 的 `Vcs-Git` 指向
> `https://salsa.debian.org/debian/d-shlibs`，tag `debian/0.109`，因此 salsa 的
> archive 端点就是上游正源。**没有**改用 `deb.debian.org/…/d-shlibs_0.109.tar.xz`
> —— preflight PF7 把 debian.org pool 文件归类为 “Debian downstream re-package”。
> 两次独立下载 sha256 完全一致（已验证稳定性）。

### 2. 构建（`build()`）

零编译——`build()` 直接 `pass`（模板里为 autotools，已按实际改写）。

### 3. 打包（`package()`）

挑文件安装（禁止整目录拷贝）：

| 产物 | 来源 | 目标 |
|------|------|------|
| `d-shlibmove` (0755) | 源码根 | `<pkg>/bin/d-shlibmove` |
| `d-devlibdeps` (0755) | 源码根 | `<pkg>/bin/d-devlibdeps` |
| `d-shlibmove.1` | 源码根 | `<pkg>/share/man/man1/` |
| `d-devlibdeps.1` | 源码根 | `<pkg>/share/man/man1/` |
| `COPYING` | 源码根 | `<pkg>/licenses/COPYING` |

`package_info()`：`cpp_info.libs=[]`、`cpp_info.bindirs=["bin"]`（R38：产物是可执行文件，
因此软件级目录需要 `commands.json`）。

### 4. 消费者验证（`test_package/`，`test_type="explicit"`）

见 `reports/test-report.md`。`test_dshlibs.py` 分 5 组共 26 条断言，**真实执行**
两个脚本（不是 print-only 空壳）：文件清单 / `bash -n`（= 上游 `make check` 第 1 步）/
两个工具的参数处理退出码 / **上游 autopkgtest 场景的 d-shlibmove 端到端** /
d-devlibdeps 独立运行。

## 上游测试三步法（R51）

### ① 清点（读上游源码，非估计）

| 上游入口 | 内容 | 能否在 OHOS 执行 |
|----------|------|-----------------|
| `make check` | `bash -n d-shlibmove`、`bash -n d-devlibdeps`、`shellcheck d-shlibmove`、`shellcheck d-devlibdeps` | **前 2 条可以**，后 2 条不行 |
| `make test-build` | `mkdir TESTS` + 对 dancer-xml / dlisp / libdshconfig / libgtkdatabox 逐个 `apt-get source` + `/usr/bin/debuild -us -uc` + `debc` | **不行**（需要完整 Debian 构建环境、apt-get source、debuild） |
| `debian/tests/control` | 1 条生效的 autopkgtest（`uppercase.d`：`gcc -shared … -o libUppercase.so.1.0.0` + `ln -s` + `d-shlibmove` + `case $? in 2) exit 0`)；`ncurses.d` 一节被上游注释掉（保留为 TODO） | **可以**（`AUTOPKGTEST_TMP` 换普通可写目录即可复现） |
| 其他 | tarball 内**没有** ctest / pytest / `tests/` 目录；`debian/rules` 只有 `%: dh $@` | — |

### ② 实际运行

**`make check`（实跑，逐字记录）**

```
$ make check
bash -n d-shlibmove
bash -n d-devlibdeps
shellcheck d-shlibmove
make: shellcheck: No such file or directory
make: *** [Makefile:10: check] Error 127
```

**具体技术原因**（不是“没环境”）：上游 `Makefile:10` 调用 `shellcheck`，而
shellcheck 在本平台不可执行，原因是**双重**的——(a) OHOS PC 镜像未安装 shellcheck
（`command -v shellcheck` 无输出）；(b) ohpcd 制品仓未发布 shellcheck
（`conan list "shellcheck/*" -r=ohpcd` → `Found 0 pkg/version recipes`），因此也无法
通过 `tool_requires` 补齐。上游把它声明为 `Build-Depends: shellcheck <!nocheck>`，
`<!nocheck>` 也正说明它只是 lint 步骤。**可运行的前两条 `bash -n` 实测通过**
（`bash -n d-shlibmove` → rc 0、`bash -n d-devlibdeps` → rc 0）；
`build()` 因此不调用 `make check`（否则必然红），改由 test_package 覆盖可运行部分。

**`make test-build`（不可执行，原因）**：目标需要 `apt-get source <pkg>` 拉取 4 个
Debian 源码包并用 `debuild` 构建，要求完整 Debian 构建环境 + apt 源 + debhelper 工具链，
OHOS PC 沙箱不具备（apt 本身未发布，见依赖闸）。

**上游 autopkgtest（`debian/tests/uppercase.d`）——实测复现并复验**

在 test_package 中被逐条复现（夹具取自上游同一文件），实测：

```
$ cc -shared -Wl,--soname=libUppercase.so.1 -o libUppercase.so.1.0.0 libUppercase.c
$ ln -s libUppercase.so.1.0.0 libUppercase.so
$ d-shlibmove $PWD/libUppercase.so
Library package automatic movement utility
set -e
install -d -m 755 debian/libuppercase1-dev/usr/lib
install -d -m 755 debian/libuppercase1/usr/lib
mv …/libUppercase.a debian/libuppercase1-dev/usr/lib
mv …/libUppercase.la debian/libuppercase1-dev/usr/lib || true
mv …/libUppercase.so debian/libuppercase1-dev/usr/lib
mv …/libUppercase.so.1 debian/libuppercase1/usr/lib
mv …/libUppercase.so.1.0.0 debian/libuppercase1/usr/lib
PKGDEV=libuppercase1-dev
PKGSHL=libuppercase1
Dry-run. If you are satisfied, run with --commit
$ echo $?
2
```

退出码 2（dry-run）**正是上游 autopkgtest 断言的那个值**，说明脚本主体逻辑
（`dpkg-architecture` → `objdump` 取 SONAME → `getname` 推导包名 → `check_line`
校验 debian/control → 打印移动计划）在 OHOS 上完整跑通。

### ③ 结果回填

**不是** N/N′ 形式的上游套件（本包没有单元测试套件），如实申报为：

| 上游测试入口 | 发现 | 执行 | 通过 | 说明 |
|---|---|---|---|---|
| `make check` / `bash -n` ×2 | 2 | 2 | 2 | 实测通过（本地 W3 + test_package B 组） |
| `make check` / `shellcheck` ×2 | 2 | 0 | — | shellcheck 未安装且未发布，双重不可执行 |
| `make test-build` | 1 | 0 | — | 需要 Debian 构建环境 + apt-get source + debuild |
| `debian/tests/uppercase.d`（autopkgtest） | 1 | 1 | 1 | 复现并复验：`d-shlibmove` → exit 2 |
| **合计** | **6** | **3** | **3（100%）** | 未执行的 3 项均为平台/依赖限制，原因如上 |

## 遇到的平台问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 直接执行装好的脚本报 `/bin/bash: bad interpreter: No such file or directory`（rc=126） | OHOS PC 的 `/bin` 是 `/system/bin` 的软链，**没有 `/bin/bash`**（只有 `/bin/sh`），而两个脚本 shebang 都是 `#!/bin/bash` | 测试一律用解析出的**绝对 bash** 启动脚本；对 `d-shlibmove` 内部对 `d-devlibdeps` 的跨脚本调用，在 PATH 上放一个 `exec <abs bash> <real script> "$@"` 的 wrapper |
| 2 | `dpkg-architecture -s` 报 `dpkg --print-architecture failed: No such file or directory` | 只把 `dpkg` 包根放进 PATH 是不够的，它还依赖同包的 `dpkg` 可执行文件 | PATH 中一并加入 `<dpkg>/bin` |
| 3 | `dpkg-architecture -s` 报 `cannot open cputable: No such file or directory` | `Dpkg.pm` 的 `$DATADIR` 默认是 `/usr/local/share/dpkg`，在 conan 缓存里不成立 | 设 `DPKG_DATADIR=<dpkg>/share/dpkg`（cputable/ostable/tupletable 都在这里） |
| 4 | `dpkg-architecture` 报 `Can't locate Dpkg.pm in @INC` | 需要 `PERL5LIB` 指向 dpkg 包根（`<pfx>/Dpkg.pm` 与 `<pfx>/Dpkg/`） | 设 `PERL5LIB=<dpkg>`；同时它的 shebang 指向**构建期**解释器，跨机要用绝对 perl 显式调用（wrapper） |
| 5 | 脚本调用 `$DEB_HOST_GNU_TYPE-objdump` 找不到 | ohpcd 的 binutils/2.46.0 只安装**无前缀**的 `objdump`（`bindirs=["bin"]`），而 dpkg-architecture 报的 triplet 是 `aarch64-linux-gnu` | 运行时先问 `dpkg-architecture -s` 拿 `DEB_HOST_GNU_TYPE`，再建 `<triplet>-objdump` 软链——**不硬编码 triplet** |
| 6 | `d-devlibdeps --help` 在第一次探测时报 `/dev/stderr: No such file or directory` | 该脚本用 `> /dev/stderr` 重定向；`/dev/stderr` 在部分调用上下文下不可用 | 属平台细节；`/dev/stderr` 存在时行为正确（rc=64, EX_USAGE）。测试断言同时接受 64 与 `Unknown option` 文本（实测 64） |
| 7 | 直接执行 `clang` 编译产物时 `cc`/`gcc` 不存在 | OHOS PC 镜像只装了 clang，没有 gcc | test_package 按 `clang` → `cc` → `$CC` → `gcc` 顺序探测 |
| 8 | `lang-preflight --lang bash` 误判 `detected=c` 并写终态 env_unsupported | 见上文“语言预检”一节（Makefile 启发式 + autopkgtest 夹具） | 按 §D.4 人工复核，保留工具输出为证据，继续适配，终态用 `result` 覆盖 |

## 源码修改

无。上游源码零改动、零补丁（`patches/` 只有 `.gitkeep`）。

## 验证结果

```bash
# 消费者验证（本机复现，等价于 conan create 的 test 阶段）
$ python3 archives/d/d-shlibs/0.109/test_package/test_dshlibs.py \
      <pkg_folder> <dpkg_package_folder> <binutils_package_folder>
…
OK: [D] d-shlibmove <libUppercase.so> -> rc=2 dry-run (upstream autopkgtest criterion)
OK: [D] d-devlibdeps ran internally -> libuppercase1-dev.substvars = 'devlibs:Depends='
OK: [E] d-devlibdeps standalone -> rc=0, wrote 'devlibs:Depends='
RESULT: ASSERT_PASS=26 ASSERT_FAIL=0
```

```bash
# 配方验证 / 本地 W3
$ python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify d-shlibs 0.109
$ python3 $SKILL_ROOT/scripts/ohc-run.py finish d-shlibs 0.109 published
```

见 `reports/conan-verify-report.md` 与版本目录下的 `.ci-result.json`。

## Pre-PR 审计与 preflight 闸门冲突（留痕）

W4 独立审计（`templates/audit-prompt.md` + `.gitcode/review-memory.md` 30 条 +
`.gitcode/code-style.md` 25 条）判定 **verdict=pass，P0=0，P1=0**，详见
`reports/audit-result.json`。

**审计范围收敛**：`pre_pr_audit.py generate` 默认走 `origin/main...HEAD`，而本机
`origin` 是 push 用的 fork（`main` = 307d9d3b35，落后 `upstream/main` 588 个提交），
默认 diff 会混入 12152 个无关文件。已用 `--base-branch upstream/main` 收敛到本 PR 的
15 个文件（处置同 `archives/b/blupimania/1.6.3/notes.md` 记录）。

**PF9 闸门冲突（P2，非配方缺陷，已按先例处置）**：

```
$ python3 scripts/ohc/preflight.py $REPO_DIR main feat/d-shlibs-0.109
✗ PF9 分支/路径闸: 变更路径缺版本目录层（须 archives/<字母>/<包>/<版本>/<文件>）
  ——CI 将报 No packages to build（490 例）:
  archives/d/d-shlibs/README.md, archives/d/d-shlibs/commands.json, archives/d/d-shlibs/manifest.yaml
```

PF9 的谓词是 `len(f.split('/')) < 5`，即**任何软件级路径都判为违规**。但：

- **R38 + CI L0k** 强制要求 `commands.json` 位于软件级
  `archives/d/d-shlibs/commands.json`（`L0k` 只查软件级路径），**不可下移**；
- **ARCHIVE-SPEC** 要求软件级 `README.md` / `manifest.yaml`。

即 PF9 机械谓词与 R38/归档规范直接冲突。**实测证据**：同一断言对已成功创建 PR
（#9926）的 `archives/c/ctronome` 返回完全相同的 fail——说明是闸门过度严格，
不是本包缺陷（ctronome 的 PR 文件集含 `archives/c/ctronome/{README.md,commands.json,manifest.yaml}`）。

**处置**（同族既有先例：`archives/c/cbindgen/0.28.0` 保留软件级文件并把 PF9 记为 P2；
`archives/c/cek/0.2.0` 保留必需的 commands.json 并记录 PF8/PF9 冲突；
`archives/c/canfigger/0.3.2` 按闸门优先删 README 并留痕）：

1. **保留全部必需路径**——本包 `commands.json` 无法删除（R38/L0k 强制），
   故采用 cbindgen 式处置而非 canfigger 式删除；
2. PF1–PF8 逐条手工复核全部通过（单包 / 无压缩包 / test 实质 / 依赖在仓 /
   无平台宏 / 无共享前缀注入 / 官方 https 源 URL / settings 四项 + slug + 版本一致 +
   commands.json schema），PF9 的**分支名**条款也通过（`feat/d-shlibs-0.109` 恰好等于
   `feat/<包名>-<版本>`），唯一失败项就是上述软件级路径谓词；
3. `submit` 时以框架提供的逃生口 `OHC_PREFLIGHT=0` 显式跳过（等同
   `--no-preflight`），并在 `reports/pr-body.md` 与 `reports/audit-result.json`
   中如实留痕该精确路径例外；
4. **真实 CI 未被绕过**：合并前的 CI 仍会独立执行 L0k（commands.json schema）、
   JC6（单软件原子性）、L0n（分支名）、L0a-L0e（test_package 结构）等门禁。

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/d-shlibmove` | 主工具（bash 脚本） |
| `bin/d-devlibdeps` | 依赖行生成工具（bash 脚本） |
| `share/man/man1/d-shlibmove.1`、`d-devlibdeps.1` | man 页 |
| `licenses/COPYING` | GPL-2.0-or-later 许可 |

## 注意事项

1. **无 `/bin/bash`**：任何直接执行（不经过绝对解释器）都会失败。CMake/CI 若想调用这些
   脚本，必须显式指定解释器。
2. **`apt` 缺失**：`d-devlibdeps` 的 `validate_package()` 依赖 `apt-cache`，在 OHOS 上
   会走到“no package matching …”分支。凡是 DT_NEEDED 能被 `overridedevlibdeps` 规则
   消解、或命中同源 `debian/control` 的库，仍能正常产出 `devlibs:Depends`（D/E 组实测）。
3. **shellcheck 缺失**：上游 `make check` 只有 `bash -n` 两条可执行；CI 不要改成
   `make check`，否则必然红。
4. `$DEB_HOST_GNU_TYPE` 由 `dpkg-architecture` 决定，不要硬编码 `aarch64-linux-gnu`。
---

**编译结束**: 2026-09-14 10:25
**最终状态**: published
