- **三方库名称**：locarna
- **上游版本**：2.0.1
- **上游仓库地址**：https://github.com/s-will/LocARNA
- **适配路径**：路径 A（基础适配）
- **使用知识库**：E490（G0 预检命中：autotools 助手脚本可执行位）；同类根因既有条目 E419（target plain-char 有符号性）与草稿 DRAFT-8543（plain char 承接 `getc()/fgetc()` 返回值再与 EOF 比较 → 文件末尾死循环）。本 PR 是该类问题在 `getopt_long()` 上的新实例，修复手法一致（接收变量改 `int`）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 22 | 来源：`src/Tests/test_locarna_lib.cc`（Catch2，175 断言，覆盖 sequence/rna_data/alignment/rna_ensemble/zip 等） |
| 集成测试 | 12 | 来源：`src/Tests/test_programs`（bash 驱动）＋ 12 个 `*.testresult` 参考比对（exparna_p、locarna-local、locarna-normalized、locarnate、mlocarna-archaea-alifold/bed-anchors/haca-constraints/probabilistic-ext/probabilistic/realign/sparse/threads） |
| 其他测试 | 0 | 上游无 examples/ 测试 |
| **合计** | **34** | |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 22 | 不变 | `make check`（命令行覆盖 `TESTS=test_locarna_lib`）实测 **22 test cases / 175 assertions，0 failed** |
| 集成测试 | 0 | -12 | 上游 `test_programs` 需 `/bin/bash` 与 `MLocarna.pm`（→`MLocarna::threaded`→`use threads`）；OHOS PC 镜像自带 Perl 未编译线程支持（`This Perl not built to support threads`），平台不具备，已在下方补充说明披露 |
| 鸿蒙特有测试 | 3 | 新增 | ①`test_package/test_liblocarna.cpp`：链接安装后的静态库构造 `LocARNA::Sequence`，断言 `name()`/`seq().str()` 往返（消费者 API）②`locarna --version` 精确输出 ③`locarna a.fa b.fa` 真实成对比对（`Score: 2928` + 两条比对序列断言）。另 W3 本地 CI 的 L2 对包内全部 8 个二进制逐一 `--version` 冒烟 |
| **合计** | **25** | **-9** | 22 单元 + 0 集成 + 3 鸿蒙特有 |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

> 上游 `src/Tests/*` 未作任何改动；仅在 `make check` 命令行覆盖 `TESTS=test_locarna_lib`，
> 使不可在 OHOS 运行的 `test_programs` 不参与执行（属"不运行"而非"修改用例"）。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

> - **补全的测试范围**：消费者视角的库 API 冒烟 + 安装后 CLI 的运行时端到端验证（本 PR 核心修复的回归）
> - **补全原因**：上游单元套件是库内视角，且完全不覆盖 `locarna` 可执行文件的启动路径——而本 PR 修复的
>   AArch64 `getopt_long` EOF 死循环恰好只在可执行文件启动时暴露（修复前 `--version` 即 100% CPU 空转/超时 124），
>   上游测试无法发现该类缺陷，必须由消费者侧的 CLI 运行时用例回归
> - **新增测试文件清单**：
>   1. `archives/l/locarna/2.0.1/test_package/test_liblocarna.cpp` — 库消费者 API 断言（`LocARNA::Sequence` 构造 + `seqentry(0).name()`/`seq().str()` 往返）
>   2. `archives/l/locarna/2.0.1/test_package/conanfile.py` — `_cli_smoke()`：运行安装后的 `bin/locarna`（`--version` + 真实双序列比对并断言 `Score:` 与比对结果）

## 验证结果

- 编译状态：通过（W3 本地 CI 100%：`L0/L1/L2/L4/L5` 全 pass）
- 上游测试用例通过率：22/22（100%）——上游单元套件全通过；上游集成 12 项因平台不具备未运行（详见补充说明）
- 新增测试用例通过率：3/3（100%）——另 W3 L2 对 8 个二进制 `--version` 冒烟全部 OK

## 补充说明

1. **核心修复（AArch64 `getopt_long` EOF 死循环）**：上游 `src/LocARNA/options.cc` 的 `process_options()`
   用 `char c` 承接 `getopt_long()` 的 `int` 返回值。AArch64 的 plain `char` 默认**无符号**（AAPCS / 预定义
   `__CHAR_UNSIGNED__`），EOF(−1) 被截断为 255，主循环 `while ((c = getopt_long(...)) != EOF)` 永不退出：
   `optind` 已过末尾，`getopt_long` 反复返回 −1，进程 **100% CPU 空转且不产生任何输出**，`timeout` 返回 124。
   修复前实测 `locarna`/`locarna_p`/`exparna_p`/`sparse`/`locarnap_fit`/`locarna_rnafold_pp` 全部复现
   （`locarna_deviation`/`ribosum2cc` 不使用该函数，故正常）。补丁 `patches/0001-src-LocARNA-options.cc.patch`
   仅把接收变量改为 `int c`（`getopt_long` 的文档返回类型），算法与平台宏均未改动；修复后 8 个工具全部正常，
   `locarna a.fa b.fa` 输出 `Score: 2928` 与正确比对。该补丁由 `ohc-run.py refresh-patch --auto` 生成
   （`patch_generation.method=per-file-difflib`，orig/work 基线 hash 见 `manifest.yaml`；
   `patch_classification: type=portability, platform_only=false, guard=none`——`int` 在包括 x86 在内的
   各平台都是正确写法，无需 `__OHOS__` 守卫）。同一根因的既有知识：E419（数值语义）、
   `DRAFT-8543-plain-char-eof-sentinel-infinite-loop`（控制流丢失）。
   **定位手段（可复用）**：OHOS 沙箱禁用 ptrace（`gdb`/`lldb` 报 `ptrace: Permission denied`），改用
   `LD_PRELOAD` 注入 `ITIMER_PROF`+`SIGPROF` 采样器（读 `ucontext_t.uc_mcontext.pc`），再以 `llvm-addr2line`
   把采样 PC 反查为符号，直接定位到 `LocARNA::process_options(int, char**, LocARNA::option_def*)`。
2. **Perl 前端不交付**：`lib/perl` 的 `MLocarna.pm` 经 `MLocarna::threaded` 使用 `threads`，
   而 OHOS PC 镜像自带 Perl 未编译线程支持。故禁用 `lib/perl` 子目录，并在 `package()` 中剔除 `bin/` 内
   23 个非 ELF 助手脚本（mlocarna、locarnate、`*.pl`、`RNAz.pm`、`benchmark-plot.R` 等），只交付可执行的
   ELF 工具——避免交付"存在但无法执行"的可执行文件。上游集成测试 12 项因此不可运行（已在上表披露）。
3. **依赖与构建适配**：硬依赖 `viennarna/2.7.2`；其 `RNAlib2.pc` 的 `prefix=/` 在 OHOS 解析到宿主 `/lib`，
   配方在 `generate()` 内重写为 viennarna 包目录并注入 `PKG_CONFIG_PATH`。老版 `config.sub`(2014) 不识别
   `ohos`，采用 libuuid 模式显式传 `--build/--host=aarch64-unknown-linux-gnu`。`configure` 的
   `umask 077`→`022` 与 `ac_pwd` 回退解决 HMDFS 沙箱问题（E011）；`make install` 走上游 bundled
   `config/install-sh` 绕过宿主 install 包装器（Error 64）；`--disable-shared` 静态构建（R26）。
   **按 R6，全部对预生成 autotools 文件（`config.sub`/`config.guess`/`configure`/`lib/Makefile.in`）的
   内容锚定改写都在 `generate()` 内完成，`build()` 不再改写任何生成文件**。
4. **交付 .pc 的可移植性与依赖声明**：`LocARNA-2.0.pc` 原样携带构建机的绝对 `-L`/`-I`（viennarna 的 Conan
   缓存目录、共享的 `~/usr/local`）。`package()` 现在（a）把 `prefix` 改写为可重定位的 `${pcfiledir}/../..`，
   （b）删除所有不落在包目录内的绝对 `-L`/`-I` 词元（含 `.private` 变体与 `-L /path` 空格形式），
   （c）补上上游缺失的 `Requires: RNAlib2`。注意 **`libLocARNA-2.0.a` 并不内嵌 ViennaRNA**——它保留 8 个
   未定义 `vrna_*` 符号，且 5 个已安装公共头 `include <ViennaRNA/...>`，故 ViennaRNA 是公共（编译+链接）
   依赖；上游 `.pc` 里裸的 `-lRNA` 没有配套搜索路径，直接 `pkg-config --libs` 的消费者原本链不上。
   Conan 消费者（CMakeDeps/PkgConfigDeps）本就走 `cpp_info` + `requires()`，不受影响。
5. **已知限制**：Perl 驱动层（`mlocarna` 多重比对前端、`locarnate`）与上游 12 项集成参考比对在 OHOS 上不可用；
   多重/成对结构比对仍可由 C++ 工具 `locarna_p`/`exparna_p`/`sparse` 直接完成。
6. **交付物**：8 个 CLI 工具（`bin/`）＋静态 `libLocARNA-2.0.a` ＋ C++ 头文件 ＋ `LocARNA-2.0.pc`。
   库消费端包含路径需双根 `include` + `include/LocARNA-2.0`。
7. **本地 preflight 说明（PF9 已知误报）**：本地以 `preflight.py "$PWD" origin/main HEAD` 逐闸核验，
   PF1–PF8 全部无 finding；唯一命中的 PF9 是"软件级 `archives/l/locarna/{README.md,commands.json,manifest.yaml}`
   缺版本目录层"——这三者恰是 `finalize-archive` 与 R38/PF8（CLI 包必须有 `commands.json`）强制要求的合法结构
   （shed/oscpack/racon 等已合入 main 的包同结构），PF8 与 PF9 对新包首入库存在必然冲突，故以
   `gitcode_pr.py create-pr --no-preflight` 创建本 PR 并在此披露。
