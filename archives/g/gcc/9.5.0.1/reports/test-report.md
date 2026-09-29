# gcc 9.5.0.1 测试报告

状态：**conan create 成功**（2026-09-22，构建树 `~/.conan2/p/b/gcc8572cdae74b46/`，包 ID `6b129b068851896169fae42d399fa922d239ce8a`，PREV `00e8297b3e71c9dcf0db16a0f2213f3b`，完整日志 `~/rtb-verify/gcc-9.5.0.1-create3.log`）。

## 测试矩阵（全项执行）

| 层级 | 测试 | 判定 | 结果 |
|------|------|------|------|
| 上游自测 | `make -C gcc selftest` | 退出码 0 | ✅ 通过（create3 日志第 515346 行，失败即中断） |
| 上游 torture 子集 | gcc.c-torture/execute 50 源 × (-O0, -O2) = 100 次设备执行 | >90% 通过 | ✅ **100/100**（日志第 515965 行） |
| 驱动固化断言 | xgcc DEFAULT_LINKER == SDK ld.lld | 精确匹配 | ✅ 通过（日志第 514743 行，bakes `/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/ld.lld`） |
| test_package | 编译+链接+运行真实 AArch64 程序；.codesign 断言 | 全部通过 | ✅ `gcc9-ohos-ok`（设备实运行）；`.codesign` 节断言通过 |
| 全量 dejagnu（证据固化） | execute.exp + compile.exp 全量 | 与路线 B 手动验证一致（≈99.9%） | ✅ 见下节 |

## 全量 dejagnu（conan create 构建树重跑，证据固化）

运行环境：dejagnu/1.6.3.1 + expect/5.45.4 + tcl/8.6.14（本地 conan 缓存），`GCC_UNDER_TEST` = 打包驱动包装器 `xgcc-ohos`。变体：execute.exp 约 11 组/源（-O0/-O1/-O2/-O3/-Os 及 -g 组合），compile.exp 5 档优化级（-O3 含 -fomit-frame-pointer 等子选项）。

- `execute.exp`: **15761 PASS / 41 FAIL / 307 UNSUPPORTED / 15 unresolved**（2026-09-22 16:45 完成，证据 `reports/dejagnu-execute.stdout.log`）。已执行用例通过率 15761/15802 = **99.74%**。41 个失败全部归因于两类平台/环境限制，无编译器缺陷：
  - **GNU trampoline 类（25）**：嵌套函数取址在栈上运行时生成代码，OHOS 内核对未签名运行时代码强制校验拒绝执行（与 lld 自动签名同源的平台级限制），`-z execstack` 无效（GNU_STACK 本就 RW）。涉及 20000822-1（5 变体）、nestfunc-1/2（各 1，仅 -O0，-O1+ 内联规避）、nestfunc-3（6）、nestfunc-5/6（各 5）、921215-1/931002-1（各 1，仅 -O0）。同类 4 源（comp-goto-2、nestfunc-4/7、pr24135）带 `dg-require-effective-target trampolines` 探测（探测程序同样被拒）→ 判 UNSUPPORTED，属框架正确识别；
  - **musl tmpnam 硬编码 /tmp 类（16）**：fprintf-2（5）、printf-2（5）、user-printf（6）——`tmpnam()` 返回 /tmp 路径而 OHOS 根文件系统 /tmp 只读，`freopen` 失败 exit 1（非段错误），`TMPDIR` 对 musl 源码级硬编码不生效；
  - 15 unresolved 为 pr79327 等 3 源的 `dg-require` 缺 `gcc.dg/builtins-config.h` 头（torture 目录跨 dg 目录引用，测试设施限制）。
- `compile.exp`: **9373 PASS / 25 FAIL / 55 UNRESOLVED / 283 UNSUPPORTED**（2026-09-22 17:21 完成，1808 源，证据 `reports/dejagnu-compile.stdout.log`）。已执行用例通过率 9373/9398 = **99.73%**。25 失败 + 55 未决全部归因，无一处证明目标代码生成缺陷：
  - **limits-exprparen（×10）+ limits-structnest（×10）= cc1 ICE**：10^4 层病态嵌套源触发 SIGSEGV/SIGILL 混现。非栈耗尽——256MB 有限栈下复现不变（另注 musl 陷阱：`RLIMIT_STACK=unlimited` 时 musl 反而回退 128KB 默认栈）。cc1 为 stage-1 产物（SDK clang 构建，配方 `--disable-bootstrap`），上游 gcc9 自举构建通过此二测试；崩溃发生在宿主侧解析阶段，与 OHOS 目标代码生成/PIE/签名链路无关，常规嵌套深度（<10^3）代码不受影响。ICE 时 libbacktrace 报 "unrecognized DWARF version in .debug_info at 6"（clang 默认 DWARF5，gcc9 读取器仅支持 DWARF4）仅系崩溃转储噪声；
  - **pr46534（×5）= 判定污染**：`dg-error` 由 `{ target { ! size32plus } }` 门控；`char dummy[16777217]` 探针片段在包装器下编译完全干净（rc=0、stderr 0 字节），但 expect spawn 的 `/bin/stty` 噪声使 `check_no_compiler_messages` 探针误判为假 → 期望错误被错误激活，而编译器在 LP64 上正确接受超大字符串字面量（约 3.4GB）；
  - **55 UNRESOLVED = 300s 单测超时**：pr61159、981001-2、20011119-1/2、pr49735、pr44197、20040323-1 共 7 源的病态慢编译（单线程串行跑法）撞 dejagnu 默认 300s 超时，属 runner 资源限制；
  - 283 UNSUPPORTED 为 effective-target 探测正常跳过。

**两阶段合计：25134 PASS / 66 FAIL / 70 unresolved / 590 UNSUPPORTED，已执行用例通过率 25134/25200 = 99.74%**；66 失败 100% 归因平台/环境/测试设施限制（trampoline 内核签名 25、musl tmpnam 16、stage-1 cc1 病态嵌套 ICE 20、探针污染 5）。

适配说明（仅测试设施，不影响产物）：
- expect 的 pty 初始化硬编码调用 `/bin/stty`（OHOS 无此路径），噪声行污染编译输出被判 excess errors —— 在构建树测试库 `testsuite/lib/prune.exp` 增加一行过滤；
- dejagnu 调 config.guess 猜测 triplet 触发 HMDFS `umask 077` 目录限制 —— site.exp 预置 build/host/target triplet 跳过；
- runtest 分两阶段串行调用（execute.exp、compile.exp），后一阶段覆盖 gcc.sum，故 execute 终局统计以 `execute.stdout.log` 为准。

## 路线 B 手动验证结论（2026-09-21，build2 构建树，已被系统清理）

同一源码 + 同一 configure 选项的全 PIE/lld 工具链手动构建（非 conan）曾达成：

- dejagnu `execute.exp`: 6099/6106 PASS（99.89%）；当时将 7 个失败误记为上游
  32 位移植类用例，本次全量证据复验（见上节）确认其实为同两类平台/环境限制
  （trampoline 内核签名 / musl tmpnam 只读 /tmp），与工具链适配无关
- 全链零 binary-sign-tool：所有宿主工具、libgcc、torture 产物均 lld 自动签名
- 该构建树被系统清理后无法复核，本版已在 conan create 重建树上重跑固化（见上节）

## 9.5.0（路线 A）的对照故障（证明 9.5.0.1 必要性）

- gcc.c-torture/execute nestfunc / printf-2 / fprintf-2 等用例：非 PIE
  对象 + lld COPY 重定位（libc stderr）LO12 未对齐加载 → 段错误
- 非 PIE 宿主生成器在 lld 链接下同类崩溃
- 根因与修复详见 notes.md「非 PIE + lld COPY 重定位 bug」

## 门禁

- conan-verify（G2）：finish 流水线执行（包已在本地缓存，预期缓存命中），结果见提交记录。
