# exceptions4c 3.0.5 适配笔记

## 编译环境
- 构建系统: makefile（库本身为 src/e4c.c + src/e4c.h 双文件直编；test/ 含独立 Makefile 测试框架）
- 编译日期: 2026-09-21
- 编译器: clang 15.0.4 (OHOS SDK toolchain) / llvm-ar
- 状态: built

## 编译步骤

1. 官方 v3.0.5 tag tarball 下载并核验 SHA-256（98c72c8b...）两次一致。
2. 库编译：`clang -fPIC -O2 -I src -c src/e4c.c -o e4c.o && llvm-ar rcs libexceptions4c.a e4c.o`
3. 上游测试：`cd test && make CC=clang && ./e4c_test`（需要将 src/e4c.c、src/e4c.h、etc/e4c_rsc.c、etc/e4c_rsc.h 软链到 test/，Makefile 中的 wget 规则指向已失效的 googlecode URL）
4. conan 配方使用 `tools.build:compiler_executables` 字典形式获取编译器（直接取 `:c` 键会报 conf 不存在）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 嵌套源码提升误把 test/ 当源码根 | F068 提升逻辑：顶层无构建标记时递归找子目录提升，test/ 含 Makefile 被误选 | 手工重建 .orig/.work 完整源码树（README/doc/etc/src/test） |
| 2 | 上游测试 Makefile 走 wget 下载 e4c_rsc.h/c | Makefile 中 SRC 缺文件时触发 `$(WGET) URL/...` 规则，googlecode URL 早已失效 | 将 tarball 已有的 src/e4c.c、src/e4c.h、etc/e4c_rsc.c、etc/e4c_rsc.h 软链到 test/ |
| 3 | conan build() 报 `[conf] 'tools.build:compiler_executables:c' does not exist` | Conan 2 该 conf 是 dict，需整体取后按 key 获取 | `comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)` 后取 `comp_execs.get("c")` |
| 4 | 消费者用例 Uncaught ContextHasNotBegunYet | E4C_TRY 前必须启动异常上下文 | main 内 `e4c_context_begin(E4C_FALSE)` / 结尾 `e4c_context_end()` |
| 5 | 上游 g 套件 7 项失败 | 平台信号行为（SIGFPE/SIGSEGV 触发与映射）差异 | 属上游明示平台探测项，非库缺陷；如实计入台账 |

## 依赖版本

- 无第三方依赖（纯 C，仅 libc/pthread 可选特性）

## 验证结果

```bash
# 上游测试（work 源码树，r02 重枚举 + 全量实跑，含 Z 套件 12 项）
cd test && ln -sf ../src/e4c.c e4c.c && ln -sf ../src/e4c.h e4c.h \
  && ln -sf ../etc/e4c_rsc.c e4c_rsc.c && ln -sf ../etc/e4c_rsc.h e4c_rsc.h \
  && make CC=clang && ./e4c_test   # 60/69（87.0%）：50 unit passed + 10 requirement fulfilled；9 项平台信号行为差异（g02/g04-g09 + z05/z08），RC=0
# 消费者用例
clang -I src test.c libexceptions4c.a -o e4c_consumer && ./e4c_consumer   # PASS
# conan 配方验证
ohc-run.py conan-verify exceptions4c 3.0.5     # G1-G4 + L1/L1e/L2/L4/L5 全过
# W3 本地 CI
ohc-run.py finish exceptions4c 3.0.5 built     # L0/L1 pass, pass rate 100%
```

> r02 返工：上游测试完整重枚举，source_declared_total=69（官方 tag 源码 test/test_*.c 共 69 个独立用例文件，含 Z 套件 12 项 test_z01~z12.c）。Z 套件在 suite_z.c/run_z.c/Makefile SRC_TEST_SUITE_Z 中真实注册、随 e4c_test 实际执行：10 项 fulfilled（z01-z04/z06/z07/z09-z12）、2 项 NOT FULFILLED（z05 SIGFPE/z08 SIGSEGV 平台能力探测失败，与 G 套件 g02/g04-g09 7 项失败同源）。全量通过率 60/69=87.0%，修正 r01 声明 N=57 的少报。Z 套件 12 项逐项执行日志见 reports/test-report.md 台账。

## 结束标记

编译状态：built
COMPLETED