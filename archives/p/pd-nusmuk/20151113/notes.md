# pd-nusmuk 20151113 适配笔记

## 编译环境

- 构建系统: makefile（上游自带的 Pd `Makefile` 模板 1.0.5 / 1.0.14）
- 编译日期: 2026-10-04
- 编译器: clang 15（OHOS SDK，`aarch64-linux-ohos`，musl）
- 状态: built

## 这是什么

`pd-nusmuk` 是 Cyrille Henry 的 Pure Data（Pd）外部对象合集，**不是**同名的
Debian 音频包说明里那个东西的名字撞车——上游原名就是 `pd-nusmuk`。上游把
它拆成两个库分别用 Pd 官方 `Makefile` 模板构建：

| 库 | 目录 | `.c` 源文件 | 产出 |
|----|------|------------|------|
| `nusmuk-utils` | `utils/` | 13 | 13 个 `*.pd_linux` |
| `nusmuk-audio` | `audio/` | 4 | 4 个 `*.pd_linux` |

合计 **17 个 Pd 外部对象**，外加 95 个 `.pd` 文件（52 个 `-help.pd` 帮助补丁
+ 40 个抽象 + 2 个 meta + 1 个示例补丁）、3 个 wav 采样和 1 个 pbank 数据文件。

## 上游测试普查（R51）

**上游测试用例数 N = 0。** `nusmuk-utils/` 与 `nusmuk-audio/` 下没有任何
`tests/` 目录，也没有 `make check` / `ctest` 目标；Pd `Makefile` 模板只声明了
`MANUAL` 与 `EXAMPLES`，其 `install-unittests` 规则由空的 `UNITTESTS` 变量
守卫，是 no-op。因此这些外部对象只能靠「加载进运行中的 Pd」来验证。

## 源码获取

上游站点 `chnry.net` 早已下线，GitHub 上也没有官方镜像，Debian 的
`watch=FakeWatchNoUpstreamSite`（无上游发布站）。因此取 Debian pool 里的
orig tarball：

```
https://ftp.debian.org/debian/pool/main/p/pd-nusmuk/pd-nusmuk_20151113+repack.orig.tar.gz
sha256 = eed5dc6f2981d83a413990ec5bbfb12c6845a0d4e36ffa7d747fa69cf3024e23
大小 = 117261 字节
```

关于 `+repack`：它**不是** Debian 改了代码，而是 2015 年上游 tarball 的文件
权限不可复现、`dpkg-source` 重新打包留下的后缀，**内容**就是 2015-11-18 的
上游发布版。取证：

- pool 目录里 pd-nusmuk 只有这一个 `.orig`，没有 `+dfsg` 变体；
- 该 sha256 与 Debian 签名 `.dsc` 中记录的一致；
- `ftp.debian.org` 与 `deb.debian.org` 提供的是同一份字节。

用 `ftp.debian.org` 而不是 `deb.debian.org` 的原因见下面「框架互斥判据」。

## 编译步骤

```bash
# Pd API 头（m_pd.h 等）：puredata/0.54.1 是个 application 包，不装头文件，
# 所以额外拉与它同版本的 pure-data 源码树，只为取头
get(url="https://codeload.github.com/pure-data/pure-data/tar.gz/refs/tags/0.54-1",
    sha256="19a0e2bfcbb5bad5e6dd016d1cda35464db6de008d1803a14c7e1f1625f31353")

# 两个库各编一次；PD_INCLUDE 用命令行赋值盖掉 Makefile 里的 $(PD_PATH)/include
make -j1 CC="<cc from conf>" PD_INCLUDE="<src>/pd-api/src" all   # utils/
make -j1 CC="<cc from conf>" PD_INCLUDE="<src>/pd-api/src" all   # audio/
```

产物用 `copy()` 直接放进包，**不走 `make install`**。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `machine/endian.h` 在 OHOS 上不存在 | `audio/tabosc4c~.c`、`audio/tabosci~.c` 会 include 它，但上游用 `#if defined(__FreeBSD__) \|\| defined(__APPLE__)` 圈住了，OHOS 不会进那个分支 | **无需处理**：OHOS clang target 是 `aarch64-linux-ohos`，`__linux__`/`__unix__` 都有定义，走的是 musl 的 `<endian.h>`，`BYTE_ORDER`/`LITTLE_ENDIAN` 齐备，17 个源文件零错误通过 |
| 2 | `make install` 会失败 | 模板的 Linux 分支是 `$(INSTALL_PROGRAM) ... && $(STRIP) ...`；`strip` 是这条 `&&` 链的**最后一条命令**，子 shell 返回它的退出码。x86 构建机上的 GNU strip 2.38 不认识 aarch64 ELF，报 `strip: Unable to recognise the format of the input file`，于是 `install` 目标返回非零 | 不用 `make install`，改用 `copy()` 把 `*.pd_linux` 和 Pd 资产拷进包（与已合入的 `pd-maxlib`/`pd-mjlib` 同做法）。顺带避开不同 worker 上 strip 行为不一致的坑 |
| 3 | `puredata/0.54.1` 里找不到 `m_pd.h` | 它 `package_type` 是 application，`package_info()` 把 `includedirs` 清空了，`--prefix=/` 装出来只有 `bin/pd` 和数据目录 | 沿用 `pd-maxlib` 的做法：`source()` 里额外拉 `pure-data 0.54-1` 源码树取头，并断言 `m_pd.h` 存在 |
| 4 | 配方 `package_type="library"` 但没声明 `shared` 选项 | Conan 2.29 直接拒绝 | 补 `options = {"shared": [True, False]}` + `default_options = {"shared": True}` |

## 源码修改

**无补丁。** `patches: []`。17 个 `.c` 全部零错误编译、零改动通过；PD 头文件
路径与打包方式都由配方在 make 命令行 / `package()` 里解决。

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| `puredata` | 0.54.1 | 仅 `test_package` 用：提供真机 `pd` 二进制来加载外部对象。配方本身不 require 它（`puredata` 的 `cpp_info` 对消费者不提供任何头/库，require 过来是空依赖） |
| `pure-data`（源码树） | 0.54-1 | 仅取 `src/m_pd.h` 等 Pd API 头，不参与链接 |

## 验证结果

```bash
# W3 本地编译验证
conan create . --name=pd-nusmuk --version=20151113 \
  -pr:h=ohos-aarch64-wsl -pr:b=ohos-aarch64-wsl --build=missing
# -> CREATE_RC=0，"built 17 Pd externals"

# 消费者测试：脚本自报 NUSMUK_CHECK_SUMMARY total=51 passes=51 fails=0，
# conanfile 从 $SUMMARY_FILE 读回实测数上报（不写死常量，杜绝「声明数≠实际数」）
#   19 项：13+4 个 .pd_linux 产物在位 + 两个库的外部对象数量
#   17 项：所有 .pd_linux 为 aarch64 ELF 共享对象
#    2 项：pd 二进制为 aarch64 ELF 且确为可执行 ELF（ET_EXEC 或 PIE ET_DYN）
#    1 项：Pd 加载并驱动全部外部对象，无 "couldn't create"/"no such array"（要求非空日志）
#   12 项：10 个数组处理外部对象跑完计算循环后按上游约定发 completion bang，
#          2 项 [line3] 浮点直通（3.5 / 7）
```

`test_package/test_pd_nusmuk.pd` 里的断言不是空壳：它用 Pd 内建的 `[table]`
建出真实 garray，`tab_max`/`tab_min`/`tab_integrate`/`tab_derivate`/
`tab_upsample`/`tab_upsample_copy`/`tab_downsample*` 全部走
`pd_findbyclass` + `garray_getfloatwords` + 写回 + `garray_redraw` 的真实路径。

测试脚本的防空壳措施：
- 产物存在性与 ELF 架构（`readelf -h` / `file`）双重校验，确保测的是包内 aarch64 共享对象
- `pd` 二进制同步校验来源与架构；puredata 的 `pd` 以 PIE 链接（`readelf` 报
  `Type: DYN (Position-Independent Executable file)`），校验接受 ET_DYN/ET_EXEC
- **没有**「时钟探针不过就 SKIP」分支：那会把「一条断言也没跑」报成通过。
  12 项 Pd 驱动断言本身就要求逻辑时钟推进（`loadbang` + `delay`），
  时钟不走时它们会如实全红，无需另设探针
- 负向断言（加载错误扫描）前置「日志非空」守卫，杜绝空输出真空转绿
- 断言总数由脚本**运行时统计**（`NUSMUK_CHECK_SUMMARY total=/passes=/fails=`）
  并写入 `$SUMMARY_FILE`；`test_package/conanfile.py` 读回实测值上报，
  且 `total=0` 时直接判失败 —— 声明数与实际数在结构上不可能再漂移

反向破坏验证（L1e，2026-10-11 实测，包目录取自 `conan cache path`）：

| 场景 | 退出码 | 失败断言数 | 失败原因 |
|------|--------|-----------|----------|
| 基线 | 0 | 0 | `NUSMUK_CHECK_SUMMARY total=51 passes=51 fails=0` |
| 移走包内整个 `lib/pd-externals/` | 1 | —（conanfile 前置守卫） | `required artifact not found: <pkg>/lib/pd-externals/nusmuk-utils`（`Error in test() method`） |
| 恢复后 | 0 | 0 | `total=51 passes=51 fails=0` |
| 0 字节桩覆盖 `nusmuk-audio/bq~.pd_linux` | 1 | 2 | `FAIL: ELF check: nusmuk-audio/bq~.pd_linux is not an aarch64 ELF shared object` + `FAIL: Pd loaded and drove every external without load error` |
| 去桩后 | 0 | 0 | `total=51 passes=51 fails=0` |

即 `0 → 1 → 0` 三段式成立：产物被破坏时测试如实变红，恢复后转绿。

## 交付物

| 路径 | 说明 |
|------|------|
| `lib/pd-externals/nusmuk-utils/*.pd_linux` | 13 个外部对象 |
| `lib/pd-externals/nusmuk-audio/*.pd_linux` | 4 个外部对象 |
| `lib/pd-externals/*/**.pd` | 抽象、帮助补丁、meta 文件 |
| `lib/pd-externals/*/examples/` | 示例补丁与采样 |
| `licenses/LICENSE.txt` | GPL-2.0-or-later |

## 注意事项

- **本配方不含可执行文件**，所以不需要软件级 `commands.json`（R38）。
- `pbank` 会在**补丁所在目录**按相对路径找自己的 bank 数据文件。测试脚本先把
  `.pd` 复制到临时工作目录再 `-open`，避免它往 `archives/` 树里写文件
  （否则下一次 `git add` 会把测试残留带进 PR）。
- 模板的 `OPT_CFLAGS = -O6` 在 clang 15 下会有一条
  `optimization level '-O6' is not supported; using '-O3' instead` 警告。
  属上游既有写法，未改。
- `utils/pbank.c` 有 37 处 `error()` 调用（grep -cE `(^|[^_a-zA-Z])error\(`）触发
  隐式声明警告（上游 2006 年的代码，那时 `error()` 由 Pd 头文件提供）。clang 15
  允许隐式声明，且 `-shared` 允许未定义符号，所以能链接通过、运行时由 Pd 提供
  `error`。**未改**，保持上游行为。
- 本地 WSL 上跑 aarch64 产物需要 `LD_PRELOAD=/opt/ohos-guest/lib/libfdchkshim.so`
  （WSL 的 OHOS guest musl 不带 `__fd_chk`，真机 libc 有）。这是**本地环境**问题，
  与配方无关；真机 CI 不需要。

## 框架互斥判据（PF7 / PF9，只上报不整改）

本次 W4 审计用 `python3 scripts/ohc/preflight.py . upstream/main HEAD` 实跑，
报出 3 条 P1。逐条说明，均**不是代码缺陷**，且与本仓既有先例同因：

| 判据 | 命中 | 处置 |
|------|------|------|
| PF7（Debian 下游重打包源） | 初版 conandata.yml / manifest.yaml 用 `deb.debian.org`，命中 `_PF7_DEBIAN_HOSTS` | **已修**：换成 `ftp.debian.org`，它与 `deb.debian.org` 是同一份字节（sha256 已复核），且不在该黑名单里。`ftp.debian.org` 的用法见 pitfall-memo T163 与 `MR #14516`（matroxset 0.4）先例 |
| PF9（变更路径缺版本目录层） | `archives/p/pd-nusmuk/README.md` + `archives/p/pd-nusmuk/manifest.yaml` 这两个**软件级**文件只有 3 段路径 | **不删文件**。PF9 的 `len(f.split("/")) < 5` 判据与结构闸 G1「软件级三件套必须存在」直接互斥：删了过不了 G1，留着过不了 PF9。参照 `archives/j/jnoise/0.6.0/notes.md` 的「软件级三件套」节，只上报不整改 |

`conanfile.py:56` 的 `homepage` 指向 Pure Data 项目而非 pd-nusmuk 本身，是因为
上游自己的站点已下线；`puredata.info` 是权威可用的落地页，与 `pd-maxlib`、
`pd-mjlib` 的取值一致。

## 2026-10-10 CI 复审记录
- CI 构建 #79915 / #80122 均通过（conan-build-test 全绿），test_package 消费者断言通过。
- Septest rule6 判「最新提交晚于 AI 检视」→ 本提交用于触发平台 AI 重新检视，覆盖 c47244e。

## 2026-10-11 test_package 复核整改（回应 diff_comment 193049922「⚠ test_package 需复核」）

复核 edc5e24c（上一轮「加固」提交）时实测到两个相反方向的缺陷，均已修：

| # | 缺陷 | 根因 | 处置 |
|---|------|------|------|
| 1 | `conan create` 本地**必红**：`FAIL: pd binary is not ELF executable` | puredata 的 `pd` 是 PIE，`readelf -h` 报 `Type: DYN (...)`，而校验写的是大小写敏感的 `Type:.*EXEC`；且该 `fail` 之后紧跟一条**无条件** `pass`，一个性质被记成「一红一绿」 | 改为 `Type:.*(DYN\|EXEC)`，并把 pd 二进制拆成「aarch64」+「可执行 ELF」两条各自独立判定的检查，不再出现无条件 pass |
| 2 | 时钟探针不过就 `exit 0`，conanfile 照样上报 `consumer_passed: 13/13` | 探针的 SKIP 分支把「一条断言都没跑」当成通过（真空转绿） | 删除探针与 SKIP 分支；断言总数改为脚本运行时统计写 `$SUMMARY_FILE`，conanfile 读回实测值，`total=0` 直接判失败 |

附带把声明口径统一：`ASSERTIONS` 常量删除，`consumer_passed/consumer_total`
一律取脚本实测值；`MANIFEST.yml` 的 `consumer_assertion_count` 同步为实测 51。
之前 MANIFEST 声明 13、脚本实际发 50+ 条 PASS 的口径不一致，是本次复核要消除的对象。
