# rotix 0.83 适配笔记

## 概述

- 软件: rotix — 生成旋转混淆（ROT-x，如 ROT13）的命令行工具
- 上游: https://github.com/shemminga/rotix（官方仓库，作者 Sjoerd Hemminga）
- 版本: 0.83（上游最后一个版本，2002-04-03；GitHub 镜像于 2020 年导入）
- 许可: GPL-2.0-or-later
- 构建系统: 手写 POSIX shell `./configure` + GNU Makefile（**非** autotools；仓库内无 configure.ac/Makefile.am）
- 产物: 单个可执行文件 `rotix` + man 手册 `rotix.1`
- 目标平台: OpenHarmony / HarmonyOS PC (aarch64-linux-ohos)

## 时间/状态

- 适配日期: 2026-09-27
- 状态: **pending**（本机前置适配完成；`conan create` 与真机尚未执行）
- 分支: `feat/rotix-0.83`

## W0 依赖结论

```text
依赖数量：0（仅依赖 C 库，无第三方依赖）
已满足依赖：libc/libm（系统自带）
缺失依赖：无
是否需要拆分依赖适配：否
阻塞点：无
下一步：本机前置验证 → CI/真机
```

制品仓 `rotix` 不存在（本仓 archives 与知识库检索均无记录），属首次适配，
Conan 包版本 = 上游版本 = `0.83`，无需 R37 递增。

## 源码归档选择

- URL: `https://github.com/shemminga/rotix/archive/refs/tags/0.83.tar.gz`
- SHA256: `99967f9308859268c8c8fbfecc970faa9a98e5621f97951d8600be0bbe69e2e4`
- 上游 tag 归档（含完整源码与 po/），URL 以 `.tar.gz` 结尾，Conan 选 gzip 解压器
  （规避无扩展名 codeload URL 的 `BadZipFile`，见知识条目 E392）。
- 交叉核验：与 Debian `rotix_0.83.orig.tar.gz`
  （sha256 `2b398c7d44cc07a28aa706537b668418e69b844e041fbb76d81a1584c4afce22`）
  解压内容逐字节一致（`diff -rq` 无差异）。两者仅 tar 打包元数据不同。

## W1 源码与构建系统分析

源码规模很小：`rotix.c`(323) + `rot.c`(69) + `help.c`(62) + 头文件 2 个 + Makefile + configure。

| 观察点 | 结论 |
|---|---|
| 语言 | 纯 C（非 Python/C++/Rust/Go） |
| 构建入口 | 手写 `./configure`（写 Makefile.settings）+ `Makefile` |
| 系统调用 | 仅 stdio/stdlib/string/getopt/unistd/locale；无 glibc 专属 API，musl 无缺 API 问题 |
| getopt | `getopt_long` 在 OHOS getopt.h 中存在；configure 对非 Linux/GNU 平台会设 `NO_GETOPT_LONG=1` 回退 getopt |
| i18n | `rotix.c` 用 `#ifdef I18N` 守卫 `<libintl.h>`；`help.c` **无条件**包含并展开 gettext（缺陷） |
| 测试 | **上游无任何测试**（无 tests/、无 check/test 目标、无 ctest/pytest 注册） |

### 上游测试清点（R51）

- `Makefile` 目标：`all rotix po po/NL.mo clean cleanall distclean rmbin install uninstall` —
  **无** `test` / `check` 目标。
- 源码归档无 `tests/`、`t/`、`test*` 目录。
- README 仅给安装步骤，无验证步骤。
- **上游可运行测试数 = 0**。故本包以 test_package 消费者断言为验证主体，不虚报上游测试数。

### 构建系统踩坑（3 处）

1. **只探测 gcc/cc**：configure 依次 `type gcc` / `type cc`，命中即写 `CC=gcc`；
   OHOS sysroot 既无 gcc 也无 cc，configure 会 `Cannot find a C compiler, aborting.`。
2. **默认 `all` 目标依赖 msgfmt**：`all : rotix po`，`po/NL.mo` 规则调用 `msgfmt`
   （gettext 工具），OHOS 构建环境无该工具。
3. **`--strip=1` 与 STRIP=0 语义冲突**：configure 在找不到 strip 时写 `STRIP=0`，
   而 Makefile 对已定义变量直接执行 `$(STRIP) rotix` → 变成执行命令 `0 rotix` 而失败。

## W2 配方设计

`conanfile.py` 要点：

- `package_type = "application"`，`settings = os/compiler/build_type/arch`。
- `source()`：`get(self, **self.conan_data["sources"], strip_root=True)`。
- `build()`：
  1. `apply_conandata_patches(self)`；
  2. R33：编译器取自 `self.conf.get("tools.build:compiler_executables", {}, check_type=dict)`；
  3. 在 `self.build_folder/build-bin/` 写一个 `gcc` shim（`exec "<target-clang>" "$@"`）
     并前置到 PATH，使 configure 探测通过（不改上游源码）；
  4. `bash ./configure --prefix=... --i18n=0 --strip=0`（R5：OHOS 无可用 /bin/sh）；
  5. `make CC="<clang>" STRIP=true -j1 rotix`（钉住 CC、中和 STRIP、只构建 rotix 目标）。
- `package()`：bin/rotix、share/man/man1/rotix.1、share/rotix/doc/README、licenses/COPYING。
- `package_info()`：`cpp_info.bindirs = ["bin"]`。

## patches

| 补丁 | 类型 | 说明 |
|---|---|---|
| `0001-help-i18n-guard.patch` | portability | 把 `help.c` 的 `<libintl.h>` 包含与 `_()` 宏改为与 `rotix.c` 一致的 `#ifdef I18N` 守卫；关闭 i18n 时展开为恒等宏 |

**根因**：OHOS musl 的 `/usr/include/libintl.h` 是**空壳头**（只有 `__USE_GNU_GETTEXT`
等宏，不声明任何函数）。`help.c` 无条件展开 `gettext` → 隐式 int → 14 处
`incompatible integer to pointer conversion`（-Wint-conversion）编译失败。
`rotix.c` 同处已有 `#ifdef I18N` 守卫，补丁使两者一致，属最小、平台无关修复。
与知识草稿 DRAFT-13410（trueprint libintl 空壳头）、
DRAFT-desktop-file-utils-0.28-libintl-header-prototype-inject 同族，但本处采用
「对齐上游已有的守卫」而非新增原型头，因为 rotix 本就把 i18n 作为可选项。

## W3 test_package

- `test_package/conanfile.py`：`test_type="explicit"`、`generators="VirtualRunEnv"`，
  经 `bash test.sh` 调用已安装二进制（OHOS 的 /system/bin sh 不能执行 ELF）。
- `test_package/test.sh`：**13 项**确定性断言——
  默认 ROT13、ROT13 往返、rotor 0/26 恒等、左旋、大小写、-v、-h 退出码、
  stdin 默认、`-f -`、`-t`/`-f` 冲突拒绝、`-a` 的 ROT-13 行、`-a` 行数=25。
- `test_package/MANIFEST.yml`：如实申报「上游测试 = 0」。

序列基于对上游 `rot.c rotate()` 的忠实移植计算（ASCII 字母 A-Z/a-z 旋转，
非字母字节原样输出）：`Hello, World!` → `Uryyb, Jbeyq!`；`AbC` →(r13) `NoP`；
`abc` →(r3 -L) `xyz`；`rotix -a -t Hello` 第 13 行为 `ROT-13: Uryyb`。

## W4 本机前置验证

| 检查 | 结果 |
|---|---|
| YAML/JSON 结构（conandata/manifest/MANIFEST/commands.json） | 通过 |
| Python 语法（conanfile.py、test_package/conanfile.py） | 通过（py_compile） |
| Shell 语法（test.sh） | 通过（bash -n） |
| 补丁可用性 | 通过（对原始归档 `git apply --check` → OK） |
| configure 行为（真实执行） | 通过：无 gcc/cc 时 configure 退出 1（`Cannot find a C compiler`）；注入 `gcc` shim 后退出 0 并写出 `CC=gcc` + `STRIP=0`，实证 shim 与 `STRIP=true` 两项措施必要 |
| 源码 SHA256 复核 | 通过（= 99967f93…） |
| 与 Debian orig 一致性 | 通过（diff -rq 无差异） |
| **OHOS 交叉编译（真实）** | **通过**：DevEco OHOS clang 15.0.4，`-target aarch64-linux-ohos --sysroot=…`，打补丁后 3 个 .c 编译并链接成功 |
| 未打补丁复现 | 通过：help.c 14 处 -Wint-conversion（根因确认） |
| ELF 检查 | AArch64 ELF；`--dyn-syms` 无 gettext/textdomain；NEEDED 仅 libc.so |
| `conan create` | **未执行**（本机无 Conan） |
| 目标二进制运行 | **未执行**（本机无 OHOS 运行时；Windows 无法运行 aarch64-ohos ELF） |

> 说明：本机交叉编译证明源码与补丁在 OHOS 工具链/头文件下可编译链接，但不等于
> 目标包可运行；`conan create`、test_package 与真机运行待 CI/真机执行，故状态为 pending。
> 本机交叉编译**未**经 configure/Makefile，而是直接调用 clang，以在无 Conan 环境下
> 隔离验证补丁与头文件兼容性。

## 遗留与阻塞点

- 本机无 Conan，未执行 `conan create` / test_package（已由真机 shadow CI 补齐，见下节）。
- ~~无 OHOS 运行时，未运行目标二进制~~（真机已验证，见下节）。
- 真机窗口已使用：单包排队、错峰执行，r1 一次通过。

## W5 真机 shadow CI 结果（r1，2026-09-27）

按《真机CI自检模板》完成第一部分静态门禁自检（lang-preflight 通过、G0e/JC/KC 通过、
L0 逐项通过、L1e 负向模拟通过：无产物时 12/13 断言 FAIL → exit 1）后上真机。

| 项 | r1 |
|---|---|
| job 名 | rotix-0.83-20260927（隔离 job，--repo-source 复用设备已有 repo） |
| run 目录 | ohos-test-runs/codex-0.83-rotix-0.83-20260927-conan-<时间戳>-<pid> |
| 排队等待 | lock.txt: wait_seconds=6（全局 mkdir 锁，排队即得） |
| exit code | 0 |
| L0 / L1 / L4 / L5 | pass / pass / pass / pass |
| L1e | `Negative test confirmed — test genuinely depends on rotix` |
| L2 | **skip: rotix version/help failed**（non-blocking，根因见下） |
| 上游测试 | 0/0（上游确无测试，MANIFEST.yml 已附清点证据） |
| test_package | **13/13 assertions PASS**（真机实跑） |

传输走 scp + 设备端 sha256 校验，`find` 清点 11 文件齐全，未把 reports 传入。

### r1 实测记录（真机日志原文要点）

- CI 镜像 fallback 把源 URL 改写为 gh-proxy.com 前缀后下载成功（conandata 原件保持官方 URL）。
- configure 在真机上输出 `Compiling for: HarmonyOS` + `WARNING: This architecture is not
  tested!`，命中上游 configure 的 `*` 默认分支 → 写入 `NO_GETOPT_LONG=1`，编译走 POSIX
  getopt 回退（make 命令行可见 `-D NO_GETOPT_LONG=1`）。13 项断言全部只用短选项，行为正确。
- `make CC=<target clang> STRIP=true -j1 rotix`：链接后 `true rotix` 一行证明 STRIP=true
  中和生效（否则 Makefile 会把 STRIP=0 当命令执行）。
- 打包：`Packaged 3 files: COPYING, rotix, README` + `rotix.1`。

### L2 skip 根因（非阻塞，上游 CLI 惯例缺失）

CI 的 L2 冒烟固定执行 `--version` / `--help`（build_and_test.sh L2 步骤原文），而 rotix
上游 optstring 只注册短选项 `f:r:ao:t:LRhv`。真机取证：

```text
rotix -v        -> exit 0（输出 "Rotix version 0.82" —— 上游 help.c 未随 0.83 更新的陈旧文本）
rotix -h        -> exit 0
rotix --version -> exit 1（musl getopt: unrecognized option: '-' -> case '?' -> exit 1）
rotix --help    -> exit 1
rotix -t 'Hello, World!' -> Uryyb, Jbeyq!   # 功能正常
```

不加 `--version/--help` 支持属上游功能缺失而非平台适配缺口，故如实记录 L2=skip（CI 本身判定 non-blocking，总 exit=0）。
> 交叉引用：正式条目 **E503**（jshon 案例）覆盖同一门禁行为，其推荐方案是给 main()
> 开头补长选项拦截。本轮未采纳（r1 已整体通过，不为不阻塞门禁扩大补丁面）；如评审
> 要求 L2=pass，可按 E503 方案补丁后重跑。

### r1 后状态更新

版本级/软件级 manifest 状态由 pending → **built**（真机 conan create + test_package 通过）。
`commands.json` 的 `binary` 保持 false（制品仓发布在 PR 合并后的 release 流水线，届时改 true）。

## 知识草稿沉淀

本轮产出 1 条新知识草稿（`knowledge/drafts/`，.md + .kv 成对）：

- **DRAFT-rotix-0.83-handwritten-configure-gcc-probe-shim**：axel 系手写 configure 按
  可执行文件名探测编译器、找不到即中止（发生在生成 Makefile.settings 之前，`make CC=`
  无效）→ build 目录私有 gcc shim 满足探测 + make CC= 钉真实编译器；同族 `STRIP=0`
  被当命令执行需 `STRIP=true` 中和；`case $(uname -s)` 默认分支静默降级需审计。

查重结论（其余发现已有归属，不重复立条）：

| 本轮发现 | 既有条目 | 处置 |
|---|---|---|
| L2 冒烟 × 仅短选项 CLI | **E503**（jshon） | 引用，不立条 |
| OHOS musl libintl.h 空壳 → gettext 隐式 int | DRAFT-13410 / DRAFT-desktop-file-utils-0.28 | 引用（补丁方式不同：对齐上游自有 #ifdef 守卫） |
| `uname -s` 返回 HarmonyOS 平台分支 | E007 / E160 / DRAFT-ffc.h | 引用（作为草稿③的交叉引用，不独立立条） |
| Makefile 配方体硬编码 gcc | DRAFT-cnrbtree / DRAFT-cohomcalg / DRAFT-ffc.h | 作为草稿的 similar_to 边界 |

## 下一步（W6）

```bash
# 提交前终检后一键提交（内含门禁 + 审计 + push + PR + CI 监控）
python3 scripts/ohc-run.py submit rotix 0.83
```

issue 编号待补（任务下发时未提供，仓库内亦无 rotix 相关 issue 记录）。

## 真机验证入口（本机具备 OHOS conan 时的等价命令）

```bash
conan create archives/r/rotix/0.83 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

> 真机 shadow CI 已完成（见上文 W5 记录）；隔离 job 命名 `rotix-0.83-<日期>`，
> 经设备隔离脚本以 `--repo-source` 复用设备已有仓库创建，传输走 scp + sha256 校验。
> 敏感连接信息（IP/端口/用户/私钥）不入库。

## 交付物

| 文件 | 说明 |
|---|---|
| conanfile.py | application 型配方（手写 configure + make，gcc shim） |
| conandata.yml | 官方 URL + SHA-256 + 补丁声明 |
| patches/0001-help-i18n-guard.patch | help.c i18n 守卫（portability） |
| test_package/ | conanfile.py + test.sh（13 断言）+ MANIFEST.yml |
| commands.json | CLI 工具声明（R38，软件级） |
| manifest.yaml | 版本级元数据（status: pending + validation） |
| notes.md | 本文件 |

## issue 说明

本轮任务提示中「issue」要求先在项目内/会话上下文中确认；仓库内（archives、
knowledge、docs、git grep）**未找到 rotix 相关 issue 编号**。按任务兜底要求，
本包已继续完成本机前置适配，**issue 编号待补**（见交付报告）。
