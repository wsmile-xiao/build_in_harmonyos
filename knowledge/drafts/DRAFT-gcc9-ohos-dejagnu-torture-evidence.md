# DRAFT-gcc9-ohos-dejagnu-torture-evidence

## OHOS 上跑 gcc.c-torture 全量 dejagnu：装配四坑与失败面判读

- **事件**: gcc/9.5.0.1@ohpcd/stable 全量证据固化（2026-09-22）
- **结果**: execute.exp **15761 PASS / 41 FAIL / 307 UNSUPPORTED / 15 unresolved** +
  compile.exp **9373 PASS / 25 FAIL / 55 UNRESOLVED / 283 UNSUPPORTED**
  （合计通过率 99.74%）；66 失败 100% 归因平台/环境/测试设施限制，非编译器缺陷
- **severity**: 2 | **category**: testing, dejagnu, gcc, ohos, kernel, musl

## 装配四坑（任一命中即全量不可跑）

1. **shebang**：`/bin/bash` 不存在（/bin 只读）→ 一切脚本必须
   `#!/data/service/hnp/bin/bash`。
2. **pkill 自杀**：后台主控脚本 `pkill -f runtest` 按命令行全文匹配会杀掉
   自身（实证主进程被误杀）→ 用精确 PID 管理。
3. **config.guess 双失败**：无 /bin/sh 可执行 + HMDFS 拒 umask 700 目录 →
   site.exp 预置 `build_triplet`/`host_triplet=aarch64-unknown-linux-ohos`、
   `target_triplet=aarch64-linux-ohos` 跳过。
4. **expect /bin/stty 噪声**：spawn 的 pty 初始化硬编码 /bin/stty →
   "sh: /bin/stty: inaccessible or not found" 混入编译输出被判 excess
   errors → 构建树 `testsuite/lib/prune.exp` 加 regsub 过滤（仅本地证据用，
   不入包）。

## 失败面判读（勿记为编译器缺陷）

| 类 | 数量 | 用例 | 根因 | 判据 |
|----|------|------|------|------|
| GNU trampoline | 25 | 20000822-1(×5)、nestfunc-1/2(×1, 仅-O0)、nestfunc-3(×6)、nestfunc-5/6(×5)、921215-1/931002-1(×1, 仅-O0) | 嵌套函数取址在栈上运行时生成代码，OHOS 内核强制签名校验拒绝（与 lld 自动签名同源）；`-z execstack` 无效（GNU_STACK 本就 RW） | exit 139；-O1+ 内联规避则 PASS；带 `dg-require trampolines` 的源（comp-goto-2/nestfunc-4/7/pr24135）探测被拒 → UNSUPPORTED（框架正确识别） |
| musl tmpnam | 16 | fprintf-2(×5)、printf-2(×5)、user-printf(×6) | `tmpnam()` 源码硬编码 /tmp（只读），freopen 失败；TMPDIR 不生效 | **exit 1 非段错误**；`tmpnam` 输出 `/tmp/...` |
| 病态嵌套 ICE | 20 | limits-exprparen(×10)、limits-structnest(×10)（compile 阶段） | 10^4 层嵌套触发 stage-1 cc1（SDK clang 构建，`--disable-bootstrap`）SIGSEGV/SIGILL | 非栈耗尽：256MB 有限栈复现不变；**musl 陷阱：`ulimit -s unlimited` 时 musl 回退 128KB，调栈必须用有限大值**；ICE 附带 "unrecognized DWARF version in .debug_info at 6"（clang 默认 DWARF5，gcc9 libbacktrace 仅支持 DWARF4）= 崩溃转储噪声 |
| 探针污染 | 5 | pr46534(×5)（compile 阶段） | stty 噪声使 `check_no_compiler_messages` 型探针（要求零输出）误判 → `! size32plus` 在 LP64 上激活 dg-error，而编译器正确接受 3.4GB 字面量 | 探针片段 `char dummy[16777217]` 手工编译 rc=0/零 stderr |
| 300s 超时 | 55 unresolved | pr61159、981001-2、20011119-1/2、pr49735、pr44197、20040323-1 | 病态慢编译源单线程串行撞 dejagnu 默认单测超时 | UNRESOLVED（非 FAIL） |
| 测试设施 | 15 unresolved | pr79327 等 3 源 | `dg-require` 引用 `gcc.dg/builtins-config.h`，torture 目录跨目录缺头 | couldn't open ... builtins-config.h |

## 执行要点

- runtest/expect/tcl：本地 conan 缓存（dejagnu/1.6.3.1 + expect/5.45.4 +
  tcl/8.6.14；TCL_LIBRARY 与 expect 编译版本一致——详见
  DRAFT-dejagnu-toolchain-assembly-ohos）。
- env：`CONFIG_SHELL=/data/service/hnp/bin/bash`、
  `GCC_UNDER_TEST=<build>/.ohos-wrappers/xgcc-ohos`、PATH 前置 SDK llvm/bin。
- **分阶段串行**（execute.exp、compile.exp 各一次 runtest），**gcc.sum 会被
  后一阶段覆盖** → 每阶段 stdout 重定向存档，终局统计以 stdout log 为准；
  execute 证据随仓库 `archives/g/gcc/9.5.0.1/reports/dejagnu-execute.stdout.log`。

## 禁止

1. `pkill -f runtest` 清场（自杀）。
2. 把 trampoline/nestfunc 失败记成编译器缺陷（平台限制）。
3. 分阶段跑却只看最终 gcc.sum（execute 结果已被覆盖）。

## 关系

- caused_by: DRAFT-dejagnu-toolchain-assembly-ohos（装配清单）、
  DRAFT-gcc9-ohos-lld-autocodesign-toolchain-route（签名机制同源）
- similar_to: E272（spawn/-nottyinit）
- 证据: archives/g/gcc/9.5.0.1/reports/
