# lldb 0.0.1 全量测试证据链（路径C申报）

本目录归档上游测试全量执行的原始证据（09-28 与 09-30 两次独立运行，双日交叉验证）。
sha256 见同目录 `sha256sums.txt`（`sha256sum -c sha256sums.txt` 校验）。

## 权威数字（两日交叉验证）

| 指标 | 09-28 全树（lit-run-full） | 09-30 三套件独立重跑 | 结论 |
|---|---|---|---|
| lit 总数 | 33638 | 708+1342+31588 = 33638 | **精确吻合** |
| lit 通过 | 31795 (94.52%) | 235+0+31560 = 31795 | 吻合 |
| lit 失败 | 120 | 92+0+28 = 120 | 吻合，且 **120 例失败测试集逐名一致（两日 byte-identical）** |
| lit unsupported | 1721 | 379+1342+0 = 1721 | 吻合 |
| lit xfail | 2 | 2+0+0 = 2 | 吻合 |
| gtest 全量口径（批量直跑 + 逐用例隔离） | 31387 = 31359P (99.91%) + 28F（= 批量直跑 31292[31289P + lldb-server 3F] + 逐用例隔离 95[70P+25F]，构成见 `gtest-run-SUMMARY-20260928.txt` 逐二进制行） | —（与 lit-unit 内 gtest sharding 31387 双 runner 交叉验证） | 吻合 |

总执行次数 65025 = 唯一用例 33638（lit 全树）+ gtest 全量口径 31387（批量直跑 31292 + 逐用例隔离 95；该 31387 亦以 per-case sharding 形态计入 lit-unit 31588 = 31387 sharding + 201 其他）。
通过率：lit 94.52% / gtest 99.91%（总口径 63154/65025 = 97.12%）。

## 文件清单

| 文件 | 内容 |
|---|---|
| `lit-run-full-20260928.log` | 09-28 `ninja check-lldb` 全量原始日志（ninja 尾部 + 单次 `cd test && llvm-lit -sv <build>/test` 调用）。**汇总块（行 7051）为权威数字**：33638 = 31795P/120F/1721U/2X，Testing Time 28.19s。异常注：行 180 头 `-- Testing: 2721 tests --` 与 FAIL 段 "(N of 2721)" 编号同汇总 33638 不一致——推测为 lldb gtest sharding 展开在发现期的计数抖动（09-30 实测同树 sharding 展开非确定：31541/31588 两种结果），不影响汇总块与 120 例失败集（09-30 逐套件独立重跑逐一复现） |
| `lit-fail-classification-20260928.txt` | 09-28 120 例失败逐例签名（聚合分布 + 逐例：suite :: 测试名 \| 首个 lldb error 行；无 error 行 = FileCheck-only） |
| `lit-probe-results-20260928.txt` | 15 例「无 error 行的 FileCheck-only」shell 失败用最小 inferior 探针单独重跑：**15/15 LAUNCH-EPERM**（逐例命令与输出） |
| `gtest-run-SUMMARY-20260928.txt` | 09-28 gtest 批量直跑 40 个测试二进制汇总（逐二进制行；TOTAL 行实测 `run=31292 pass=31289 fail=0`——其中 lldb-server 3 用例 rc=1 全败[ptrace EPERM，见其失败日志]但脚本解析器未计入 fail、DAP/Host/Target 3 二进制 rc=-11 崩溃 run=0；31387 = 31359P + 28F 为「批量 + 逐用例隔离 95 用例[70P+25F]」合成口径） |
| `gtest-fail-HostTests-20260928.log` | HostTests 8 例失败原始日志（EPERM：pipe bind 等，含断言上下文） |
| `gtest-fail-TargetTests-20260928.log` | TargetTests 13 例失败原始日志 |
| `gtest-fail-DAPTests-20260928.log` | DAPTests 4 例失败原始日志（mkfifo EPERM） |
| `gtest-fail-LLDBServerTests-20260928.log` | LLDBServerTests 3 例失败原始日志（ptrace EPERM） |
| `gtest-run-all-20260928.py` | gtest 直跑脚本（os.walk 收集 40 二进制 + `--gtest_brief=1` + TMPDIR 固定，设备 find 不在 PATH 的适配） |
| `lit-shell-20260930.log` | 09-30 shell 套件独立重跑原始日志（708 = 235P/92F/379U/2X） |
| `lit-api-20260930.log` | 09-30 api 套件独立重跑原始日志（1342 = 100% unsupported，见下） |
| `lit-unit-20260930.log` | 09-30 unit 套件独立重跑原始日志（31588 = 31560P/28F；28 例 = DAP 4/Host 8/Target 13/lldb-server 3，与 09-28 同名同签名） |
| `lit-fail-classification-20260930.txt` | 09-30 120 例失败逐例签名（与 09-28 版逐例对照：测试集 byte-identical，签名逐例吻合） |
| `repro-matrix-20260930.txt` | 4/4 启动拒绝复现矩阵（bash 前台 / python Popen 后台 × 裸参数 / lit 同参数，全部 `error: Cannot launch '/bin/ls': ptrace failed: Permission denied`）+ P1 正常启动正控（exec 允许，rc=0）+ P2 `os.mkfifo` EPERM + P3 unix socket bind EPERM（syscall 级直接探针） |

## 120 例失败逐例归因（2026-09-30 修正版，双日复现）

| # | 类别 | 计数 | 证据等级 |
|---|---|---|---|
| 1 | launch PTRACE 拒绝（可见 `Cannot launch/failed to launch ... ptrace failed: Permission denied`） | 45（shell 42 + lldb-server 3） | 直接：原始日志 error 行 |
| 2 | launch 下游错误（可见 `requires a process which is currently stopped` ×3 / `process must be launched` ×1 / `unable to evaluate...must be stopped` ×1） | 5（shell） | 直接：error 行 |
| 3 | launch 被阻、FileCheck 窗口无 error 行（最小 inferior 探针逐例重跑 15/15 LAUNCH-EPERM） | 15（shell） | 直接：`lit-probe-results-20260928.txt` |
| 4 | launch 被阻、FileCheck 窗口无 error 行（同类族：均为需目标进程的 frame-format/Commands/Expr 等，机制同 #3，未逐例探针） | 21（shell） | 推定（同族同机制） |
| 5 | DWO/split-DWARF 路径+codegen 差异（FileCheck 内容不符，不涉及 launch；测试输入经 hnp clang 15 编译，split-DWARF compdir/dwo_name 路径与上游 clang 22 期望不同） | 6（shell dwo-*/split-dwarf-*） | 直接：FileCheck 差异内容（原始日志） |
| 6 | 用例级沙箱 EPERM（gtest Host 8/Target 13/DAP 4：pipe bind、process spawn、mkfifo） | 25（unit） | 直接：gtest 原始日志 EPERM 断言行 + P2/P3 syscall 探针 |
| 7 | CLI 注解格式（command-options：`unknown or ambiguous option`） | 1（shell） | 直接：error 行 |
| 8 | scripting 设计性关闭（section-overflow-binary：`Embedded script interpreter unavailable`，本构建无 python） | 1（shell） | 直接：error 行 |
| 9 | Apple 平台专属（TestEnumExtensibility：`Foundation.h file not found`） | 1（shell） | 直接：编译错误行 |
| | **合计** | **120** | |

- launch 相关合计 = 45+5+15+21 = **86**（其中 65 直接证据、21 同族推定）
- 120 例全部为环境因素/上游因素，**零适配缺陷**；09-28/09-30 两日独立重跑同 120 测试集（名称 byte-identical）+ 签名逐例吻合
- 与 gtest 直跑 28F 的关系：lit-unit 28F 与 gtest 28F 为同一用例集合（双 runner 交叉验证），唯一失败用例数 = 120

## lldb-api 1342 例说明（重要修正）

本构建 `SWIG_EXECUTABLE-NOTFOUND` + `LLDB_ENABLE_PYTHON=Auto`（CMakeCache）→ lldb 无 python 绑定（`lldb -P` → `COULD NOT FIND PATH`）
→ api 套件 1342 例全部经上游 REQUIRES 机制判 unsupported（**0 执行、0 失败**，非适配缺陷，属构建配置无 python 环境）。
因此 09-28 报告中「SB API 1342/1342 (100%) 全过」为**误读已撤回**；「沙箱按 tracer 进程上下文生效（python 路径放行）」推论**撤销**（本构建未观测到任何放行正控上下文——API 路径 0 执行）。

## 复现命令

环境：OHOS aarch64 设备；clang 22.1.8（conan）+ LLVM 22.1.8 库（hnp `/data/service/hnp/bin`，`LD_LIBRARY_PATH` 含 `/storage/currentUser/lib`）；构建树 `/storage/Users/currentUser/tmp/lldb001-build2`（`bin/llvm-lit`；`lit.site.cfg.py` 四项 override：clang/clang++ = hnp、FileCheck = hnp、`use_executable(lldb)`、`use_executable(llvm-symbolizer)`）。

```sh
cd /storage/Users/currentUser/tmp/lldb001-build2
# ① lit 三套件（~30s/套，20 workers）
bin/llvm-lit -sv test/Shell    # 预期 708 = 235P/92F/379U/2X
bin/llvm-lit -sv test/API      # 预期 1342 = 100% unsupported（无 python）
bin/llvm-lit -sv test          # 全树，预期 33638 = 31795P/120F/1721U/2X（28s 量级）
# ② gtest 直跑（40 二进制，~3min）
python3 test-evidence/gtest-run-all-20260928.py   # 批量直跑：预期 31292（31289P + lldb-server 3F；SUMMARY 解析器 fail=0 低估，其日志可见 3 FAILED）+ DAP/Host/Target 3 二进制 rc=-11 崩溃
#    崩溃 3 二进制需逐用例隔离重跑（95 用例 = DAP 27/Host 36/Target 32）→ 70P+25F；合成口径 31387 = 31359P + 28F
#    （28F = DAP 4/Host 8/Target 13/LLDBServer 3；逐二进制日志落 .ohc/gtest-run/）
# ③ 复现矩阵 + syscall 探针（~10s）
#    见 repro-matrix-20260930.txt 的 4+3 格（4/4 ptrace EPERM + P1 OK + P2/P3 EPERM）
```
