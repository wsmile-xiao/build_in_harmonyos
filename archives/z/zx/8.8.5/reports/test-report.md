# zx 8.8.5 测试报告

> **项目**: zx（google/zx）
> **测试日期**: 2026-09-30
> **测试环境**: HarmonyOS PC（OHOS aarch64）· node v24.13.0 · Conan 2.29.1
> **测试类型**: 上游官方测试套件（node:test，12 文件 / 259 用例）+ test_package 消费者断言（4 项）

---

## 一、测试摘要

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 总测试数 | 259 | 100% |
| 通过 (PASS) | 235 | 90.7% |
| 失败 (FAIL) — 平台豁免 | 23 | 8.9% |
| 跳过 (SKIP) — 上游自带 | 1 | 0.4% |

**核心功能通过率**: ✅ **90.7%**（豁免项均为平台环境限制，非 zx 功能缺陷）

**test_package 消费者断言**: ✅ **4/4 通过**

---

## 二、测试结论

### 2.1 总体评价

✅ **通过**。完整上游套件实际执行（断言未删改），清单外失败为 0：
`UPSTREAM_TESTS_POLICY tolerated=23 unexpected=0`。

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| 无外网出口 | 8 例（https 脚本、fetch） | 🟡 环境限制，不阻塞发布 |
| `/tmp` 只读 erofs | 3 例（cd/tmp 路径用例） | 🟡 环境限制 |
| OHOS `ps -lx` 无列边界 | 7 例（kill/timeout 系） | 🟡 环境限制 |
| `--jitless` 输出交错 | 5 例（顺序性/流交错） | 🟢 部分单独运行可通过 |

### 2.3 可用功能清单

```
✅ CLI 与脚本执行：zx --version / -e / 脚本文件 / stdin 脚本
✅ 命令执行与捕获：$`cmd`、管道 pipe()、stdout/stderr 捕获、错误与退出码
✅ 内建工具函数：cd/within/echo/sleep/retry/spinner/question/tempfile/tempdir
✅ 内置 vendor API：YAML / globby / minimist / which / fs-extra / dotenv / chalk
✅ 依赖解析 API：parseDeps / import、require 解析（deps 10/10 全通过）
✅ 错误格式化：Fail 退出码表 / errno 消息 / 调用点定位（error 10/10 全通过）
✅ markdown 代码块抽取：transformMarkdown（md 1/1 通过）
⚠️ fetch()/https 脚本：设备无出网路由 + `--jitless` 禁用 wasm llhttp，本环境不可用
⚠️ 子进程强杀（timeout/kill/killSignal）：依赖 @webpod/ps 解析本机 ps 表，本环境不可用
❌ 无
```

### 2.4 已知限制

1. 本机 node 必须 `--jitless`（否则 Signal 5 core dump）；该参数关闭 WebAssembly，
   直接导致 TS transform（amaro）与 undici 的 llhttp 解析器不可用。
2. 上游测试中依赖 `/tmp` 字面量路径的用例无法运行（`/tmp` 为只读 erofs 挂载）。
3. OHOS toybox `ps -lx` 输出不满足 `@webpod/ps` 的 unix-grid 解析要求，`kill()`/`timeout()` 系断言失败。

---

## 三、测试详情

### 3.1 通过的测试（逐文件实测）

| 测试文件 | 用例数 | 通过 | 失败 | 跳过 | 说明 |
|----------|------:|-----:|-----:|-----:|------|
| test/cli.test.js | 39 | 34 | 5 | 0 | CLI 参数与脚本执行（5 例网络相关豁免） |
| test/core.test.js | 133 | 116 | 16 | 1 | `$`/管道/超时/`cd` 核心（豁免见下） |
| test/deps.test.js | 10 | 10 | 0 | 0 | **全通过**：依赖解析 API 与 CLI |
| test/export.test.js | 3 | 3 | 0 | 0 | **全通过**：三入口导出面（含颜色断言，FORCE_COLOR=1） |
| test/global.test.js | 2 | 2 | 0 | 0 | **全通过** |
| test/index.test.js | 2 | 2 | 0 | 0 | **全通过** |
| test/util.test.js | 12 | 12 | 0 | 0 | **全通过**：工具函数 |
| test/vendor.test.js | 7 | 6 | 1 | 0 | 内置 vendor API（1 例 fetch 豁免） |
| test/error.test.ts | 10 | 10 | 0 | 0 | **全通过**：错误格式化（tsc 编译后运行） |
| test/goods.test.ts | 29 | 28 | 1 | 0 | 工具函数集（1 例 fetch 豁免） |
| test/log.test.ts | 11 | 11 | 0 | 0 | **全通过**：日志格式（含颜色断言） |
| test/md.test.ts | 1 | 1 | 0 | 0 | **全通过**：markdown 抽取 |
| **合计** | **259** | **235** | **23** | **1** | |

### 3.2 失败的测试（平台豁免 23 例，按 TAP 路径登记）

| 测试项 | 族 | 原因 |
|--------|----|------|
| cli: scripts from https 200 | A | 无外网 + wasm llhttp 不可用 |
| cli: scripts from https 500 | A | 同上 |
| cli: scripts (md) from https | A | 同上 |
| cli: scripts from stdin with explicit extension | A | 需 `--experimental-strip-types`（wasm amaro） |
| cli: scripts with non standard extension | D | 扩展名/TS 管线依赖 wasm；单独运行可通过（顺序抖动） |
| cli: supports `--cwd` option | D | 顺序抖动（单独运行通过） |
| core: fetch (stream) > $ | A | 无出网路由 |
| core: fetch (pipe) > $ | A | 同上（abort 时报 "Trying to abort a process"） |
| core: just works / applies custom signal / applies `$.killSignal` / expiration works / accepts a signal opt / handles `timeout` and `timeoutSignal` / propagates rejection / rejected piping | C | `@webpod/ps` 无法解析 OHOS `ps -lx` 网格（7 例） |
| core: can create a dir with a space in the name | B | `/tmp` 只读（EROFS） |
| core: works with relative paths | B | `/tmp` 只读（ENOENT） |
| core: does not affect parallel contexts | B | `/tmp` 只读（ENOENT） |
| core: lines() / accepts thenable arguments / several $ halted / keeps the cwd ref | D | `--jitless` 输出交错 / `getcwd: Not supported` 泄漏（4 例） |
| goods: fetch() | A | 无出网路由 |
| vendor: fetch() works | A | 无出网路由 |

> 断言未删除、未改写；`conanfile.py` 的 `EXPECTED_ENV_FAILURES` 按 TAP 路径逐条登记并打印技术原因，
> 清单之外的任何失败都会让 `conan create` 失败。

### 3.3 跳过的测试

| 测试项 | 跳过原因 |
|--------|----------|
| core: handles multiline literals | 上游自带 `skip`（syntax highlighting 相关，与平台无关） |

### 3.4 test_package 消费者断言（4/4）

| 检查项 | 命令 | 结果 |
|--------|------|------|
| 版本 | `zx --version` → 8.8.5 | ✅ PASS |
| 命令捕获 | `zx -e 'const o = await $\`echo zx-consumer-ok\`; ...'` → `ZX-CONSUMER-OK` | ✅ PASS |
| 脚本文件 | `zx consumer.mjs`（`$`/`fs`/`path`）→ `CONTENT=zx-consumer` | ✅ PASS |
| stdin 脚本 | `echo "console.log('STDIN_OK')" \| zx -` | ✅ PASS |

CI L1e 破坏性反向验证：移走 `bin/` 后 `conan test` 失败 → 确认测试真实依赖被测包（非空壳）。

---

## 四、关键问题分析

### 问题1: `--jitless` 与 WebAssembly 的连锁影响

**现象**：
```
4 个 .ts 测试文件: ReferenceError: WebAssembly is not defined
https 脚本用例:    TypeError: fetch failed [cause]: ReferenceError: WebAssembly is not defined
```

**根因分析**：本机 node v24.13.0 不加 `--jitless` 即 core dump（`Check failed: 12 == (*__errno_location())`）；
而 `--jitless` 关闭 WebAssembly，node 自带 TS transform（amaro）与 undici 的 llhttp 解析器都是 wasm 实现。

**解决方案**：`--jitless` 保持开启（否则无法运行）；4 个 `.ts` 测试文件改用包内 tsc 编译成 JS 后再跑
（实测 error 10/10、log 11/11、md 1/1、goods 28/29 通过）；依赖 fetch/TS transform 的少数断言按平台豁免登记。

### 问题2: `/tmp` 只读导致路径类用例失败

**现象**：
```
mkdir: '/tmp/foo bar': Read-only file system
Error: ENOENT: no such file or directory, lstat '/tmp/zx-cd-test'
```

**根因分析**：`mount` 显示 `/dev/block/dm-0 on /tmp type erofs (ro,...)`，即只读。

**解决方案**：上游测试中的 `/tmp` 是**字面量**，无法用 `$TMPDIR` 替换 → 3 例登记为平台豁免。

### 问题3: OHOS ps 表不可解析导致 kill/timeout 系失败

**现象**：
```
TypeError: Cannot read properties of undefined (reading 'spaces')
  at getBorders (build/vendor-core.cjs:825:38)
  at parseUnixGrid (build/vendor-core.cjs:834:19)
```

**根因分析**：zx 经 `@webpod/ps`（`ps -lx`）杀子进程；该库的 unix-grid 解析器要求各列有稳定边界，
OHOS toybox 的 `ps -lx` 输出不满足（且 `ps` 不支持 `-x`：`ps: Unknown option 'x'`）。

**解决方案**：7 例 kill/timeout 系断言登记为平台豁免（换标准 procps 环境预期可过）。

---

## 五、测试环境

```
OS:        HarmonyOS PC (OHOS 6.0, aarch64/armv8)
node:      v24.13.0 (/data/service/hnp/node.org/node_v24.13.0)   [必须 --jitless]
npm:       11.6.2（经 npm-cli.js 调用；wrapper 崩溃）
Conan:     2.29.1（OHOS 适配版）
Profile:   ci/conan/profiles/ohos-aarch64
套件:      node:test（node --test --test-concurrency=1 --test-force-exit）
TS 编译:   typescript 5.9.3（devDependency，tsc --skipLibCheck）
环境变量:  NODE_OPTIONS=--jitless --no-deprecation / FORCE_COLOR=1 / TMPDIR=<可写目录>
```

---

*报告生成时间: 2026-09-30*
