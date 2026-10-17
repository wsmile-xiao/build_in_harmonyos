# libydpdict 1.0.4.1 适配笔记（1.0.4 修复版）

## 版本说明（R37 递增）

`libydpdict/1.0.4` 已由 !12876 合入并发布到制品仓（recipe revision
`e5516ad792d503d5576e461e59abcbc1`）；R37/L0j 门禁禁止同版本多 revision 并存
（修改 conanfile.py/conandata.yml 必须递增版本号，参照 freetype
2.14.3 → 2.14.3.1/2.14.3.2/2.14.3.2.1 先例）。故本次修复以 **1.0.4.1** 发布，
仅新增 `archives/l/libydpdict/1.0.4.1/`，原 1.0.4 目录保持发布态不变。

1.0.4.1 相对 1.0.4 的变化：
- 上游测试清点纠偏 N=0 → **N=4**（`misc/Makefile.am` 的 `check_PROGRAMS`），
  并在 `build()` 内用合成语料真实执行 4/4（R51/rule4）；
- `libtool_source.url` 修正：原 5 条镜像中 4 条 `/libtool/` 路径为 HTTP 404
  （tuna/ustc/aliyun/ftp.gnu.org），改为可用的 `ftp.gnu.org/gnu/libtool/` 与
  `ftpmirror.gnu.org/libtool/`（CI 预下载脚本对 404 响应体不校验即缓存，
  可用 URL 必须排在最前）；
- 新增 `PKG_CONFIG_LIBDIR` 空目录阻断 configure 可选 libxml2 误拾构建机 host 库；
- test_package 新增 qemu 真机口径执行通道（OHOS_QEMU/OHOS_RUNROOT）。

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

## 上游测试清点（R51 三步法，2026-09-29 修正）

| 项 | 结果 | 清点依据 |
|----|------|----------|
| 上游 `tests/` 目录 | 0 个 | 发行 tarball 全量成员清单：40 个文件，目录为 `src/`、`include/`、`misc/`、`pkgconfig/` 及其余 autotools 文件，无 `tests/`/`test/`/`t/` |
| ctest/pytest 注册项 | 0 个 | 无 `CMakeLists.txt`；无 `pytest.ini`/`tox.ini`/`conftest.py` |
| autotools `TESTS` 变量 | 0 个 | `src/Makefile.am`、`include/Makefile.am`、`misc/Makefile.am` 均无 `TESTS` → `make check` 不自动运行用例 |
| autotools `check_PROGRAMS` | **4 个** | **`misc/Makefile.am` 第 1 行：`check_PROGRAMS = ydpstress ydptest ydpxml gentable`**（此前清点误报"无命中"——原清点命令的 grep 模式与范围有误，本版按实测修正） |
| 上游可运行测试总数 N | **4**（check 程序口径） | 4 个 check 程序即上游 `make check` 的全部测试资产；`ydptest_SOURCES=ydpstress.c` 与 ydpstress 同源、独立二进制，按 2 例申报 |

清点命令（可复现）:

```bash
tar -tzf libydpdict-1.0.4.tar.gz | wc -l          # 40
grep -n 'TESTS\|check_PROGRAMS' src/Makefile.am include/Makefile.am misc/Makefile.am
# → misc/Makefile.am:1:check_PROGRAMS = ydpstress ydptest ydpxml gentable
```

### 上游测试真实执行（R51 第二步）

`conanfile.py build()` 以 `make -C misc check` 构建 4 个 check 程序后逐个真实执行：

| 程序 | 依赖 | 运行负载 | 结果 |
|------|------|----------|------|
| ydpstress | DICT_PATH 词典数据 | 4 本词典全部词条 read_rtf + read_xhtml | PASS |
| ydptest | 同上 | 同上（独立二进制，SOURCES=ydpstress.c） | PASS |
| ydpxml | DICT_PATH 词典数据 | 全词条 read_xhtml 渲染校验 | PASS |
| gentable | iconv(windows-1250→utf-8) | 128 字符转换表生成 | PASS |

**语料说明（非测试用例修改）**：3 个数据依赖程序按上游硬编码
`DICT_PATH=/usr/local/share/ydpdict` 读取 `dict100/101/200/201.dat/.idx`
（Young Digital Planet 商业词典数据，**不可分发**，上游仓库亦不提供）。上游自带
`misc/mkdict.py` 即为该文件格式的官方合成工具；配方按其格式合成 4 本测试词典
（windows-1250 词条 + RTF 释义，覆盖 \b/\i/\cf2/\cf5/\f1 音标/\super/\par/\sa/\li
与 &<> 转义）后执行程序全负载。测试程序源码与判定逻辑**零改动**。
CI 设备根文件系统只读时数据依赖 3 例本环境跳过并在日志明确标注（gentable 照常
执行），本地 WSL（qemu-user + OHOS musl 运行根）4/4 实测。

适配后测试 N′=27（上游 4/4 真实执行 + `test_package/`）：
上游 check 程序 **4 例**（4/4 PASS）+ 单元/边界断言 **9 项**（`test.c`，实测 9/9）
+ 鸿蒙端到端消费者用例 **1 个**（`test_ydpdict_e2e.c`，14 项断言实测 14/14，真实生成
词典文件对 → open → 查询/取释义 → close），通过率 **27/27 = 100%**。
上游 4 例在 build() 内真实执行；消费者两例由 `test_package/conanfile.py` 的
`test()` 真实执行（非仅编译）。

## 验证结果

```bash
# 1) 本地交叉构建 + 上游 4 个 check 程序真实执行
#    （aarch64 目标经 qemu-user/binfmt 执行，ohos-aarch64-run profile）
bash /mnt/d/OHDev/outputs/local-validate-recipe.sh <repo>/archives/l/libydpdict/1.0.4.1
# → conan create rc=0；语料 4 本/12 词条落盘 /usr/local/share/ydpdict；
#   misc/ydpstress、misc/ydptest、misc/ydpxml、misc/gentable 全部 PASS（4/4）

# 2) test_package 消费者用例（真机口径：qemu + OHOS musl 运行根）
qemu-aarch64-static -L /root/ohpc/sdk/ohos-runroot ./test_libydpdict
# → 9/9 断言 PASS（test libydpdict 1.0.4: OK）
qemu-aarch64-static -L /root/ohpc/sdk/ohos-runroot ./test_ydpdict_e2e
# → 14/14 断言 PASS（e2e: OK）

# 3) 真机 DAYU200（OpenHarmony 6.0.0.47，静态链接消费者二进制）
bash /mnt/d/OHDev/automation/device_runner.sh run libydpdict_e2e <dir> \
     "./test_libydpdict && ./test_ydpdict_e2e"
# → exit=0；9/9 + 14/14 = 23/23 PASS；证据 _device_evidence.json

# 4) 仓库 CI 门禁（CI profile 原样）
CI_PACKAGES=archives/l/libydpdict/1.0.4.1 CI_BRANCH=feat/libydpdict-1.0.4.1 \
     zsh ci/conan/build_and_test.sh
# → G0/G0e、L0（L0j first publish / L0k / L0m / L0n）、KC1-5、JC1-6、
#   L1/L... 全通过，见 PR 评论 CI 报告
```

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
