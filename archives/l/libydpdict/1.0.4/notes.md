# libydpdict 1.0.4 适配笔记

## 编译环境
- 构建系统: autotools（configure + libtool；`lib_LTLIBRARIES = libydpdict.la`）
- 编译日期: 2026-09-25
- 编译器: clang 15（OHOS SDK 26.0.0.18）
- 宿主三元组: aarch64-unknown-linux-ohos（交叉/本机构建均由 profile 指定）
- Conan profile: ci/conan/profiles/ohos-aarch64（`os=OHOS`，arch=armv8）
- 状态: built（G2 `conan create` rc=0：`test_package` 单元/边界断言 9/9 + 鸿蒙端到端消费者用例 14/14；待 CI 合并后由 release 流水线 upload）

## 编译步骤

```bash
# 1) 源码：官方 release tarball（conandata.yml 单 url，CI/验证工具按需注入镜像 fallback）
#    sha256=37dcbc12def981a20728bdcb6a5ff1eef8931f29a0f16852f0b2201ff8563528
#    上游 tarball 自带 configure / Makefile.in（无需 autoreconf）
# 2) 构建（R26：本包为系统同名库，默认 shared=False → 静态产物）
conan create archives/l/libydpdict/1.0.4 \
    -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
    --build=missing --user=ohpcd --channel=stable
```

实际 configure 调用（在 `build()` 内以命令前缀方式调用，见"问题 #1"与"源码修改"）：

```
CPPFLAGS="-I$PWD/include $CPPFLAGS" SHELL=/bin/sh CONFIG_SHELL=/bin/sh \
  <src>/configure --enable-static --disable-shared --prefix=/ \
    '--bindir=${prefix}/bin' '--sbindir=${prefix}/bin' '--libdir=${prefix}/lib' \
    '--includedir=${prefix}/include' '--oldincludedir=${prefix}/include' \
    '--datarootdir=${prefix}/res'
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `config.status: line 712: print: command not found`（×27）→ `config.status: error: could not setup config files machinery` | conan 用 `/bin/sh`（本平台 = MIRBSD KSH R59）启动 `configure`，其中 `ECHO` 探测得到 ksh 内建 `print -r --`；但 profile `[buildenv]` 导出 `SHELL`/`CONFIG_SHELL`=`/data/service/hnp/bin/bash`，config.status 由 bash 执行 → bash 无 `print` | `build()` 中以**命令前缀**调用 configure：`SHELL=/bin/sh CONFIG_SHELL=/bin/sh <configure> …`。POSIX 语义保证前缀赋值覆盖 profile `[buildenv]`（后者优先级高于配方 `buildenv_info`），整条链（configure → config.status → 生成的 libtool → Makefile 的 SHELL）统一到 `/bin/sh` |
| 2 | `../libtool[1249]: func_opt_split: inaccessible or not found`；`libtool: Version mismatch error. This is libtool 2.2.6b Debian-2.2.6b-2ubuntu1, but the definition of this LT_INIT comes from libtool 2.4.` | 上游发布包内 `ltmain.sh` 自称 libtool 2.2.6b（`package_revision=1.3017`），而 `aclocal.m4` 声明 LT_INIT 来自 libtool 2.4（`macro_revision=1.3293`）。configure 生成 libtool 时以 aclocal.m4 为准，而内建函数由 ltmain.sh 提供 → 生成的 libtool 缺 9 个 `func_*` 函数，第一次 `--mode=link` 即失败（解包字节数已核对，排除下载损坏） | `source()` 中取 GNU libtool 2.4 **官方**发行包（`ftpmirror.gnu.org/libtool/libtool-2.4.tar.gz`，`package_revision=1.3293`）内的 `libltdl/config/ltmain.sh` 覆盖上游残缺件（官方包不参与编译）。知识草稿：`knowledge/drafts/E543-draft-A443.kv` |
| 3 | `src/ydpdict.c:29:10: fatal error: 'ydpdict.h' file not found` | VPATH（源码外）构建：`ydpdict.h` 由 `ydpdict.h.in` 生成到 **top_builddir/include**，而上游 `AM_CPPFLAGS` 只含 `top_srcdir/include` | `configure` 时经 `CPPFLAGS` 补入构建目录（`-I$PWD/include`），随 config.status 进入生成的 Makefile 与 libtool 调用 |
| 4 | `config.status: …/subs1.awk: Permission denied` → `could not setup config files machinery`（仅本机 FUSE 环境） | `config.status` 用 `tmp=$(umask 077 && mktemp -d ./confXXXXXX)` 建临时目录（mode 0700）；本机挂载语义按 mode **组位**授权（进程 uid 与目录 owner 不同），0700 目录对构建进程不可写 | **本机规避，不进配方**：`mktemp` 垫片（`~/usr/local/bin/mktemp`，umask 002 + `chmod 2770`）置于 conan 构建 PATH 前部。CI worker 不受此限制 |
| 5 | `config.guess: unable to guess system type` / `Invalid configuration 'aarch64-linux-ohos'` | config.guess/config.sub 无 HarmonyOS 分支（E007） | `patches/0001-config.guess.patch`（+12）补 `*:HarmonyOS:*:*` 分支；`patches/0002-config.sub.patch`（+3/-3）接受 `linux-ohos` 三元组并补 aarch64 CPU 列表 |

## 源码修改

1. `patches/0001-config.guess.patch` — config.guess 增加 HarmonyOS 分支，输出 `aarch64-unknown-linux-ohos`（E007 模式，refresh-patch --auto 生成）。
2. `patches/0002-config.sub.patch` — config.sub 接受 `linux-ohos` 三元组、arm 列表补 `aarch64`（同上）。
3. `conanfile.py source()` — 用 GNU libtool 2.4 官方 `ltmain.sh` 覆盖上游残缺件（问题 #2，E543）。
4. `conanfile.py build()` — 命令前缀对齐 `SHELL`/`CONFIG_SHELL=/bin/sh`（问题 #1）；`CPPFLAGS` 补构建目录 include（问题 #3）。
5. 上游源码文件本身**未修改**（无 `#ifdef __OHOS__` 空壳、无平台宏注入）。

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| （运行时）无 | — | 本库不动态依赖任何三方库；libxml2 为可选（`LIBXML2... no`），本配方未启用 |
| GNU libtool（源码包） | 2.4 | 仅从官方发行包提取 `ltmain.sh`，不参与编译、不进 `requires` |

- 下游: `ydpdict` 通过 `PKG_CHECK_MODULES([YDPDICT],[libydpdict >= 0.99.3])` 硬依赖本包
  （无 fallback），因此本包必须先发布（R36）。

## 上游测试清点（R51 三步法）

| 项 | 结果 | 清点依据 |
|----|------|----------|
| 上游 `tests/` 目录 | 0 个 | 发行 tarball 全量成员清单：40 个文件，目录为 `src/`、`include/`、`misc/`、`pkgconfig/` 及其余 autotools 文件，无 `tests/`/`test/`/`t/` |
| ctest/pytest 注册项 | 0 个 | 无 `CMakeLists.txt`；无 `pytest.ini`/`tox.ini`/`conftest.py` |
| autotools 测试目标 | 0 个 | `grep -n 'TESTS\|check_PROGRAMS\|check-local' src/Makefile.am include/Makefile.am misc/Makefile.am` 无命中（Makefile.in 中亦无测试目标） |
| 上游可运行测试总数 N | **0** | 无测试框架、无测试目标 → 上游测试无法运行（"没环境"不适用，此处是上游确无测试） |

清点命令（可复现）:

```bash
tar -tzf libydpdict-1.0.4.tar.gz | wc -l          # 40
tar -tzf libydpdict-1.0.4.tar.gz | grep -iE 'test|check'   # 无命中
grep -rn 'TESTS\|check_PROGRAMS' <src>/Makefile.am <src>/*/Makefile.am   # 无命中
```

适配后测试 N′=23（`test_package/`，见 `reports/test-report.md` §2 与 `reports/conan-create.log`）：
单元/边界断言 **9 项**（`test.c`，实测 9/9）+ 鸿蒙端到端消费者用例 **1 个**（`test_ydpdict_e2e.c`，
14 项断言实测 14/14，真实生成词典文件对 → open → 查询/取释义 → close），通过率 **23/23 = 100%**。
两者都由 `test_package/conanfile.py` 的 `test()` 真实执行（非仅编译）。

## 验证结果

```bash
# W3 本地 CI（finish step [5/10] 内执行，结果落 .ci-result.json）
conan create archives/l/libydpdict/1.0.4 -pr:h=…/ohos-aarch64 -pr:b=…/ohos-aarch64 \
    --build=missing --user=ohpcd --channel=stable
# → rc=0；test_package 9/9 断言通过（test libydpdict 1.0.4: OK）

# conan-verify（G0-G4 + L2/L4/L5）
python3 scripts/ohc-run.py conan-verify libydpdict 1.0.4
# → Verdict: PASS（G0 PASS 命中 E540；G1/G2/G3/G4 PASS；L2/L4/L5 通过）
```

详细测试记录见 `reports/test-report.md`，原始日志见 `reports/conan-create.log`、
`reports/conan-verify-report.md`。

产物: `lib/libydpdict.a`（静态，R26）、`include/ydpdict/ydpdict.h`、
`lib/pkgconfig/libydpdict.pc`、`licenses/COPYING`。

## 评审修复记录（rule12：鸿蒙特有测试必须是完整消费者用例）

平台评审连续两轮对同一规则判 FAIL，原文：

> 规则 12: 鸿蒙特有测试行只有断言（N=1），不算完整消费者用例——至少要有一个完整消费者用例
> （真正跑通功能/流程的端到端用例），纯断言不行

根因两条：

1. **描述未更新**：上一轮只把新增用例写进 PR *评论*，描述「适配后测试用例统计」表中的
   `鸿蒙特有测试 | 1 | 新增 +1 | 交叉编译 + CMake 构建 + 运行二进制断言` 与「合计 9 项断言」
   原样保留。rule12 读的是**描述表格**（不看代码），因此两轮读到同一行，FAIL 文本逐字相同。
2. **用例从未真实执行**：`test_package/conanfile.py` 的 `test()` 原先只运行 `test_libydpdict`，
   新增的 `test_ydpdict_e2e` 只被编译、从未执行（上一轮仅做 `clang -fsyntax-only`）。
   把 e2e 接入 `test()` 后**首跑即挂 2 条断言**——上一版断言本身写错了。

### API 语义实证（本轮修好用例的依据，已核对上游 `src/ydpdict.c`）

| 函数 | 真实语义 | 依据 |
|------|----------|------|
| `ydpdict_get_word(dict, def)` | 返回**词目**（headword）；UTF8 模式下 open 时已由 windows-1250 转码 | `src/ydpdict.c:400-408`（`return dict->words[def].word;`） |
| `ydpdict_read_rtf(dict, def)` | 返回**释义正文**（RTF 原文，**不做**字符集转换，调用方负责 free）；越界返回 NULL 且置 `EINVAL` | `src/ydpdict.c:313-349` |
| `ydpdict_find_word(dict, w)` | **前缀匹配 + 大小写不敏感**（`strncasecmp(words[i].word, w, strlen(w))`），返回词目下标，未命中 -1 | `src/ydpdict.c:359-373` |

上一版 e2e 把 `ydpdict_get_word()` 当成"取释义正文"（期望值写成 dat 中的定义），故必然失败。

### 修复后的用例与本机真跑结果

用例文件格式与上游 `misc/mkdict.py` 逐字段对齐（idx 头 `<LLHHLL236s>`、条目
`<BBHL>`+word+`\0`、dat 条目 `<L>`+正文），并新增 windows-1250 高位字节词目
（`słowo`，`0xb3`）验证 open 期词目转 UTF-8 通路、`read_rtf` 验证 dat 偏移/长度与
"释义不转码"语义。`conan create` 真跑（`reports/conan-create.log`）：

```
======== Testing the package: Executing test ========
libydpdict/1.0.4@ohpcd/stable (test package): RUN: ./test_libydpdict
  [ok] ×9                                             → test libydpdict 1.0.4: OK
libydpdict/1.0.4@ohpcd/stable (test package): RUN: ./test_ydpdict_e2e
  [ok] ×14（生成真实文件对 → open → find_word/get_word → read_rtf → close） → e2e: OK
```

## 注意事项

- 本包是 **系统同名库**（`ydpdict` 是独立程序，库名与系统无冲突但按 R26 取静态），
  默认 `shared=False`；下游 `ydpdict` 需静态链接 ncursesw 并将本库静态链入。
- `ltmain.sh` 覆盖必须在 `configure` 之前（`source()` 内完成）；若将来升级到
  aclocal.m4 声明 2.5.x 的上游版本，需同步更换对应官方 `ltmain.sh`。
- `SHELL`/`CONFIG_SHELL` 的**命令前缀**写法不可换成 `env`/`export`：profile
  `[buildenv]` 的导出优先级高于配方环境，只有 POSIX 前缀赋值能稳定覆盖。
- 本机 `$TMPDIR` 只读限制（E002）与 mktemp 垫片属环境私有处理，不应进入配方。

---

**编译结束**: 2026-09-25
**最终状态**: built
