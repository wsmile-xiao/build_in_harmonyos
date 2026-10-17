## PR 信息
- **三方库名称**：teseq
- **上游版本**：1.1.1
- **上游仓库地址**：https://ftp.gnu.org/gnu/teseq/（GNU 官方发布目录；项目主页 https://www.gnu.org/software/teseq/）
- **适配路径**：路径 A（基础适配）
- **使用知识库**：E129 / E112 / E136（HMDFS umask 077 → configure/config.status 临时目录不可写）、E547（libcheck 临时目录探测顺序）、DRAFT-11103（mdate-sh 无法解析 HarmonyOS ls 的 ISO-8601 日期导致 VTI 文档再生成链失败）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 2 | 来源：`src/test-ringbuf.c`、`src/test-inputbuf.c`（Makefile.am 的 `check_PROGRAMS`，由 `PKG_CHECK_MODULES([libcheck], [check])` 可选启用） |
| 回归测试 | 56 | 来源：`tests/run-tests`（28 个 teseq 用例）+ `tests/run-tests -r`（28 个 reseq 用例，`prompt-descript-only`、`hardstatus-color` 由上游 vars 声明 `run_reseq=false`，harness 记为 skipped） |
| 其他测试 | 1 | 来源：`exercise-seqs`（Perl 穷举脚本，逐字符组合喂给 teseq，无固定用例计数） |
| **合计** | **58 + exercise-seqs** | |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 2 | 不变 | 以 test_requires check/0.15.2 + PkgConfigDeps 使上游可选单测真实编译执行（TOTAL 2 / PASS 2 / FAIL 0；单程序内部 7 checks + 3 checks） |
| 回归测试 | 56 | 不变 | `make check` 在 OHOS 目标设备上原样运行：teseq 28/28、reseq 28/28 |
| 其他测试 | 1 | 不变 | `exercise-seqs`：`Results: All runs look okay.` |
| 鸿蒙特有测试 | 13 | 新增 | test_package 消费者回归（`self.run` 断言 13 条：二进存在/版本/--timings/SGR 描述/字段透传/reseq 往返 cmp/1.1.1 fuzz 回归输入） |
| **合计** | **58 + exercise-seqs + 13 断言** | **上游测试全量保留 + 新增消费者回归** | |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

> 上游 `tests/`、`exercise-seqs`、`src/test-*.c` 全部原样运行；两个 reseq 用例的 `(skipped)` 由上游 `vars` 文件自行声明，属上游预期行为。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）
- [x] **否**，上游已有测试用例覆盖

> 上游测试已完整覆盖 teseq/reseq 行为；适配仅额外增加 test_package 消费者视角回归（13 条 `self.run` 断言，验证包内二进制可用、SGR 描述生成、reseq 往返字节一致、1.1.1 fuzz 回归输入不再挂起）。该 test_package 为消费者验证，不替代、不修改上游测试统计。

## 验证结果

- 编译状态：**通过**（conan create 干净构建，G0–G4 全 PASS；`ohc-run.py clean-verify` 仅凭补丁集完成解包→configure→make→make install）
- 上游测试用例通过率：**58/58（100%）+ exercise-seqs 全通过**
  - `make check`：RUNNING TESEQ TESTS 28/28、RUNNING RESEQ TESTS 28/28、exercise-seqs `Results: All runs look okay.`、check-TESTS `# TOTAL: 2  # PASS: 2  # FAIL: 0`
- 新增测试用例通过率：**13/13（100%）**（test_package 断言逐条实跑于 OHOS 真机）
- W3 本地 CI 模拟：L0 pass / L1 pass / L1e R34 负向测试 pass（移除 bin/ 后断言确实失败）/ L2 pass / L4 pass / L5 pass
- 环境：HarmonyOS PC aarch64 真机，clang 15.0.4（aarch64-unknown-linux-ohos），Conan 2.29.1
- 产物：`bin/teseq`、`bin/reseq`、`share/info/teseq.info`、`share/man/man1/{teseq,reseq}.1`、`licenses/COPYING`

## 补充说明

- **适配方式**：仅 2 个补丁，不改任何 C 源码、不注入 `__OHOS__`：
  1. `patches/0001-Makefile.in.patch`：把 automake `stamp-vti` 规则改为 no-op。HarmonyOS `ls` 输出 ISO-8601 日期（无月份名），而 mdate-sh 依赖月份名解析，失败后裸 `set` 会把环境变量表写入 `doc/version.texi`，连锁触发 makeinfo（OHOS 无 texinfo）导致 `make install` 失败；禁用该规则后发行 tarball 自带的 info/man 原样安装（详见 DRAFT-11103）。
  2. `patches/0002-configure.patch`：`configure` 内两处 `umask 077` 改为 `umask 022`。HMDFS 对 umask 077 新建目录强制 setgid（`drwx--S---`），owner 亦不可写，`config.status` 建临时目录时报 `could not setup config files machinery`（E129/E112/E136；与已合入的 a52dec/0.7.4 同款修复）。
- **测试依赖**：check/0.15.2（test_requires，仅测试使用；使上游可选 libcheck 单测真实启用）。构建环境为其补充 `LD_LIBRARY_PATH`（包内同时含 .a/.so）与 `TEMP/TMPDIR`（libcheck 的 `P_tmpdir`=/tmp 只读优先级问题，E547）。
- **构建布局**：in-source 构建（同 a52dec/0.7.4）；`HELP2MAN/CHECKMK/MAKEINFO=true` 防止发行文档被重建。
- **已知限制**：无。teseq/reseq 为纯 POSIX 命令行工具，无运行时依赖。
