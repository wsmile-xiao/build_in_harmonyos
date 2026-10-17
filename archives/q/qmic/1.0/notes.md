# qmic 1.0 适配笔记

## 编译环境
- 构建系统: makefile（上游手写 Makefile，无 configure / 无 CMake）
- 编译日期: 2026-09-27
- 编译器: clang 15.0.4（OHOS aarch64，`--target=aarch64-linux-ohos`，OHOS SDK sysroot）
- 状态: built（本地 conan create 通过 + test_package 两项全绿；未 upload）

## 库与目标确认
- 目标库: **qmic** —— QMI IDL 编译器（Qualcomm MSM Interface 接口描述语言 → C 代码生成器）。
- 上游仓库: https://github.com/linux-msm/qmic
- 上游 tag: `refs/tags/v1.0`（`v0.1` 亦存在；分支名 `feat/qmic-1.0` 对应 1.0）
- 源码 tarball: https://github.com/linux-msm/qmic/archive/refs/tags/v1.0.tar.gz
- SHA-256: `e2797c85a2b617b2b35024566105f4d8e998ef576f0f96f7923abf3717d12e86`（实测，写入 conandata.yml）
- 命名口径: 任务给出的库名 `qmicC++` 中 `C++` 为语言标注（与 `serializeC++` → `serialize` 同一写法）；全网检索不存在名为 qmic 的 C++ 版库，唯一有 `v1.0` tag 的 qmic 即本库（C 实现），故 Conan 包名取上游工程名 `qmic`。
- 工具行为: 从 stdin 读 `.qmi` IDL，`-a` 选 accessor 后端 / `-k` 选 kernel 后端，在当前目录生成 `qmi_<package>.c` 与 `qmi_<package>.h`。

## 依赖与查重
- 依赖: **无**（仅 C 标准库；未使用 TLV 编解码路径 `qmi_tlv.c`，该文件不参与工具编译）。
- 查重: `git ls-remote --heads origin|upstream` 无 `qmic` 分支；`find archives -iname '*qmic*'` 无命中；制品仓 `conan list "qmic/*" -r=ohpcd` 与 `conan list "*qmi*" -r=ohpcd` 均 0 条。非重复适配。

## 编译步骤
```bash
# OHOS 交叉编译（本机 OHOS SDK clang 15）
make -j1 CC=<ohos-sdk clang> CFLAGS="-pipe -O2 -Wall"
#   → bin/qmic（ELF aarch64-linux-ohos）

# conan 配方验证（配方内 build() 走同一 make 命令，CC 取自
# tools.build:compiler_executables，R33）
python3 scripts/ohc-run.py conan-verify qmic 1.0
```

## 上游测试（R51 三步法）

**计数口径（全仓统一，本任务唯一口径）：以「独立命令行场景数量」计，即上游 `tests/` 目录中
18 个 `.qmi` IDL 语料，每个文件用 `qmic -a` 跑一次并按退出码判定 accept/reject，共 18 项。**

上游**没有测试运行器**——这不是"上游无测试"，而是"有语料、无 runner"：
- `Makefile` 只有 `all`(默认) / `install` / `clean`，无 `check`/`test` 目标（`grep -n 'test' Makefile` 零命中）
- 无 CI 工作流、无测试脚本、无 gtest/pytest/criterion 绑定（`find . -name '*.sh' -o -name '*.expected'` 零命中）
- `tests/` 下 18 个 `.qmi` 纯语料，无期望产物（`.c`/`.h` golden 文件）

因此期望值必须自行实测确立，本任务在上游**未修改源码**上用 glibc gcc 与 OHOS musl clang 双平台各跑一遍，
得到完全一致的基线：

| 判定 | 数量 | 文件 |
|------|------|------|
| accept（rc=0） | 7 | `bad_X` `fixed` `comments` `hexdigits` `num_large` `single_digit_decimal` `symbolic_values` |
| reject（rc=1） | 11 | `bad_decimal` `bad_hex` `bad_octal` `duplicate_const` `duplicate_message_name` `duplicate_message_val` `duplicate_struct_name` `no_package` `num_too_big` `two_packages` `very_long_token` |

> ⚠️ `tests/bad_X.qmi` 是**历史误称**，实为 accept 用例：上游提交 `parser: properly support hexadecimal
> numbers` 之后 `0X` 已成为合法十六进制前缀，文件内注释即写明 "Previously 0X was not allowed to
> indicate a hexadecimal value"。初版测试按文件名把它当 reject 用例，实测才发现判反——已修正，
> 并在 test_package 脚本里留注释说明。

1. **清点**：`ls tests/*.qmi | wc -l` → 18；`Makefile` 无 check/test 目标 → 无 runner。
2. **实跑**：18 个语料在 OHOS aarch64 musl 运行时逐个执行，accept/reject 与 glibc 基线完全一致。
3. **回填**：本文件与 MANIFEST.yml / PR 正文均按 18 项口径填写；通过率见「验证结果」。

## 测试计数口径
| 口径 | 数值 | 证据 |
|------|------|------|
| 上游 IDL 语料（`tests/*.qmi`） | 18 | `ls tests/*.qmi \| wc -l`（7 accept / 11 reject，双平台实测基线一致） |
| 上游测试运行器 | 0 | Makefile 无 check/test 目标；无 CI/脚本/框架绑定 |
| test_package 消费者断言 | 22 | `test_qmic.sh` 逐项断言（18 语料 accept/reject + Usage/退出码 + kernel 后端 + include guard） |
| 鸿蒙特有测试断言 | 9 | `ohos_qmic_test.sh`（9 项，详见下节） |

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `parser.c` 编译失败：`use of undeclared identifier 'program_invocation_short_name'` | 该符号是 glibc 专有扩展，OHOS musl 的 `<err.h>` 不声明它（本机 macOS 亦同） | 改用 `__progname`：glibc/musl/OHOS libc 都导出（OHOS sysroot `libc.so` 实测有 `__progname` 定义），且上游未改动的 `qmic.c` 本就用它打印 Usage，行为等价。知识命中 E203/E493（musl 缺 glibc 专有符号族） |
| 2 | 初版 test_package 把 `tests/bad_X.qmi` 断言为 reject，实测 rc=0 | 文件名是历史误称：上游早已支持 `0X` 十六进制前缀（提交 `parser: properly support hexadecimal numbers`） | 双平台（glibc gcc + OHOS musl clang）对上游未修改源码实测建立基线，确认为 accept 用例并修正断言 |
| 3 | **CI #62665（PR #13196）鸿蒙专项测试 3 项失败**：`renamed_qmic: Operation not permitted`，随后「generator produced no output」与「generated source looks like a stub」连带失败 | 初版把二进制 `cp` 成 `renamed_qmic` 再执行，以断言错误前缀跟随 argv[0]。鸿蒙只允许执行带有效 `.codesign` 签名的 ELF，副本越过签名边界被内核拒绝执行（E077/E452）；该次 exec 失败后再执行生成器检查时未拿到产物，属连带失败 | 删除「复制后执行」这一在 OHOS 上不可能成立的做法，改为断言「错误前缀 == 被调用的安装名 `qmic`」；生成器检查改到独立 scratch 目录并把 rc 与产物一起判定；同时清掉脚本里遗留的 `$(...)` 命令替换（OHOS `/bin/sh` 可能把它落在只读 `/tmp`）。本机 arm64 容器实跑：消费者 22/22、鸿蒙专项 9/9 |

## 源码修改
- **1 个可移植性补丁**：`patches/0001-parser.c.patch`
  - `yyerror()` 的错误前缀 `program_invocation_short_name` → `__progname`，并在文件作用域补 `extern const char *__progname;`
  - 该补丁**不含任何平台条件编译**（满足 R8「补丁不得引入 `__OHOS__`」），对 glibc/Linux/macOS 行为不变；已用 glibc gcc 编译同一补丁集并实跑验证

## OHOS 平台验证（鸿蒙特有测试）
`test_package/ohos_qmic_test.sh`，在 OHOS aarch64 musl 运行时实跑通过（9 项断言）。该测试针对的
正是本次唯一的平台适配点，覆盖三类只有适配后 OHOS 构建才成立的性质：

1. **运行时 `__progname` 真的解析成功**：非法 IDL 的错误前缀必须是真实程序名（正则断言
   `^[^ :][^:]*: parse error on line N:`），且不得渲染成 `(null)`——若 `__progname` 未被 OHOS libc
   填充，这两项会直接失败。
2. **错误前缀就是被调用的程序名**：以安装名调用时前缀必须是 `qmic:`——这是 `__progname` 契约的
   可验证部分。⚠️ 初版这里做的是「把二进制复制成 `renamed_qmic` 再跑，断言前缀跟随 argv[0]」，
   该做法**在 OHOS 上不可行**：鸿蒙只允许执行带有效 `.codesign` 签名的 ELF，`cp` 出来的副本越过了
   签名边界，内核直接拒绝执行（`Operation not permitted`，见知识 E077/E452；PR #13196 CI 失败即此）。
   现改为只执行已签名的安装产物，不再复制可执行文件。
3. **glibc 专有符号彻底消失**：构建出的 OHOS ELF 符号表不含 `program_invocation_short_name`
   引用，同时可见对 `__progname` 的引用（符号转储工具按 `readelf`/`llvm-nm`/`nm` 依次探测，
   无 dump 工具时回退到 ELF 字符串表扫描）。

附加断言：适配后生成器仍能正常出码——合法 IDL 产出 `qmi_test.c`/`qmi_test.h`，生成的 `.c` 确实
`#include` 了自己的头文件，且头文件带 `__QMI_TEST_H__` include guard（证明是真实代码生成，
不是占位输出）。生成检查在独立 scratch 目录内进行，避免前一步的残留掩盖缺失产物。

```bash
# 实测输出（OHOS aarch64 musl 运行时）
  ok   adapted error path still rejects invalid IDL (rc=1)
  ok   __progname resolved at runtime (error prefix carries real program name)
  ok   error prefix is not a null pointer
  ok   error prefix is the invoked program name (qmic)
  ok   binary carries no glibc-only symbol reference
  ok   binary references __progname (OHOS libc export)
  ok   OHOS build still generates qmi_test.c/.h from valid IDL
  ok   generated source includes its own header (real codegen, not a stub)
  ok   generated header carries the package include guard

qmic OHOS-specific test: 9 passed, 0 failed
HMBS_OHOS_TEST_RESULT={"executed":true,"passed":true,"count":9}
```

## 验证结果
```bash
# 上游语料（OHOS aarch64 musl 实跑，18 项）
accept=7 reject=11 total=18   # 与 glibc 基线完全一致

# test_package 消费者测试
qmic consumer test: 22 passed, 0 failed
HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"discovered":22,"passedCount":22}

# conan verify
python3 scripts/ohc-run.py conan-verify qmic 1.0
```

## 交付物
| 文件 | 说明 |
|------|------|
| `conanfile.py` | makefile 工具配方：命令行注入 CC（R33）、直接 copy 二进制、`package_type=application` |
| `conandata.yml` | 官方 tag v1.0 URL + 实测 SHA-256 + 补丁声明 |
| `patches/0001-parser.c.patch` | glibc 专有符号 → `__progname`（无平台条件编译，R8） |
| `manifest.yaml`（软件级/版本级） | 编译元数据与跨版本 OHOS 适配知识 |
| `commands.json` | CLI 工具声明（R38） |
| `test_package/` | `test_qmic.sh`（22 断言）+ `ohos_qmic_test.sh`（8 断言）+ `corpus/`（18 个上游 .qmi 逐字副本）+ `MANIFEST.yml` + `conanfile.py` |
| `notes.md` | 本文件 |

## 知识查重判定（本地只读快照，knowledge @ upstream/main HEAD=c611f7d61b）
- 扫描范围: `knowledge/graph/E*.kv` + `knowledge/doc/E*.md` + `knowledge/drafts/*.kv`
- 最相关既有知识:
  - **E203**（OpenHarmony musl libc — `getprogname()`/`sys/poll.h` 适配）：命中同一族问题——
    musl 不提供 glibc 的 `getprogname()`/`program_invocation_name`，但提供 `__progname`。
    本任务的 `program_invocation_short_name` 属同一族，`__progname` 也是同一推荐替代。
  - **E493**（`use of undeclared identifier 'program_invocation_name'`，musl 无该 glibc 扩展符号）：
    错误签名与本任务报错几乎逐字一致，推荐方案同为 `__progname`。
  - **DRAFT-ohos-musl-glibc-specific-symbols**（musl 缺 glibc 特有符号族，需跨多文件统一处置）：
    本任务只命中 1 个文件、1 处引用，属该草稿描述族的最小实例。
  - **E077 / E452**（OHOS ELF 必须带有效 `.codesign` 签名；复制出的私有 ELF 副本会被加载器拒绝）：
    CI #62665 的失败正落在此族——test_package 复制的 `renamed_qmic` 无法执行。属既有知识已覆盖的
    平台契约，非新缺口。
- **knowledge_decision: reuse_existing（路径 A）**，不创建新草稿。
  编译期问题已被 E203/E493 覆盖，测试期问题已被 E077/E452 覆盖；本任务未引入新的通用模式
  （单文件单点符号替换 + 测试脚本去除「复制后执行」），故不作路径 B 候选。
---

**编译结束**: 2026-09-27 12:15
**最终状态**: built
