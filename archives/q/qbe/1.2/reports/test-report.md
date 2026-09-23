# qbe 1.2 测试报告

> **项目**: qbe 1.2（编译器后端：SSA → amd64/arm64/rv64 汇编）
> **测试日期**: 2026-09-16
> **测试环境**: HarmonyOS PC 真机（HongMeng Kernel 1.12.0 aarch64 / HAD-W32），clang 15.0.4（OHOS SDK LLVM），Conan 2.29.1（OHOS 适配版），profile `ohos-aarch64-device`
> **测试类型**: 上游官方测试套件（`tools/test.sh all`）+ 消费者端到端测试（`test_package`）

---

## 一、测试摘要

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 上游套件执行总数 | 50 | 100% |
| 通过 (PASS) | 49 | 100%（按可执行项 49/49） |
| 失败 (FAIL) | 0 | 0% |
| 跳过 (SKIP) | 1 | 上游首行声明跳过（dark.ssa, arm64） |
| 消费者 E2E 断言 | 12 | 12/12（100%） |

**核心功能通过率**: ✅ **100%**（49/49，按未声明跳过的可执行用例；含 1 项上游声明 SKIP 后为 49/50，原因见下文）

---

## 二、测试结论

### 2.1 总体评价

✅ **通过**：arm64 后端在设备内完成完整闭环（SSA → arm64 汇编 → OHOS clang 汇编链接 → 原生执行 → 输出/返回码比对），
上游 50 项默认用例中 49 项通过、0 项失败、1 项为上游自身为 arm64 声明的跳过。

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| OHOS `/tmp` 只读 vs 上游驱动硬编码 `tmp=/tmp/qbe.zzzz` | 原样运行 49/50 用例在写临时汇编失败（`cannot open '/tmp/qbe.zzzz.s'`），端到端验证无法进行 | 🟡（已修复：补丁 0001，`${TMPDIR:-/tmp}`） |

### 2.3 可用功能清单

```
✅ qbe -t?                     默认目标自描述（设备输出 arm64）
✅ SSA → arm64 汇编             上游 49 项用例覆盖算术/内存/控制流/ABI/浮点/varargs/TLS
✅ 汇编 → 可执行（OHOS clang）  内嵌 driver 与独立用例均可编译链接
✅ 原生执行 + stdout diff       13 项输出比对用例全部一致
✅ 原生执行 + 返回码检查        36 项返回码用例全部正确
✅ 非法 SSA 拒绝                qbe 以非零码退出，无崩溃
⚠️ amd64/rv64 后端            仅随源码编译通过；无对应目标执行环境，未做运行验证（不属于本平台验证范围）
```

### 2.4 已知限制

1. `dark.ssa` 为上游首行 `# skip arm64 arm64_apple rv64` 声明跳过，非适配裁剪（跳过逻辑由上游脚本执行）。
2. `test/` 中 14 个下划线前缀 `.ssa`（`_alt/_bf99/_bfmandel/_chacha20/_dragon/_fix1..4/_live/_rpo/_spill1..3`）不在上游 `[!_]*.ssa` glob 内，不属于 `make check` 范围（上游设计）。
3. 上游 tarball 不含发布物 `qbe.ref`，汇编参考比对分支按上游逻辑自然跳过；本适配不将"汇编文本差异"作为失败，亦不掩盖任何真实错误。
4. `qbe --version/--help` 非上游接口（仅 `-h` 等短选项）；CI L2 冒烟为非阻塞告警（同 crasm 等 CLI 先例）。

---

## 三、测试详情

### 3.1 通过的测试（49 项，`tools/test.sh all`）

输出比对 13 项：`abi1 abi3 abi4 abi5 abi6 abi8 echo load2 mandel puts10 tls vararg1 vararg2`
返回码检查 36 项：`abi2 abi7 align cmp1 collatz conaddr cprime cup double dynalloc env eucl euclc fixarg fold1 fpcnv isel1 isel2 isel3 ldbits ldhoist load1 load3 loop max mem1 mem2 mem3 philv prime queen rega1 spill1 strcmp strspn sum`

### 3.2 失败的测试

无。

### 3.3 跳过的测试

| 测试项 | 跳过原因 |
|--------|----------|
| dark.ssa | 上游首行 `# skip arm64 arm64_apple rv64`（该用例在 arm64 上不适用，属上游声明的平台边界） |

---

## 四、关键问题分析

### 问题 1: OHOS `/tmp` 只读导致上游测试驱动全部失败

**现象**（未打补丁、原样运行，故障先复现）：
```
$ sh tools/test.sh all
abi1.ssa...    cannot open '/tmp/qbe.zzzz.s'
[qbe fail]
...
49 of 50 tests failed!
```

**根因分析**：
`tools/test.sh` 第 7 行硬编码 `tmp=/tmp/qbe.zzzz`（临时 driver/汇编/可执行/输出文件均以此为前缀）。
HarmonyOS `/tmp` 只读（`touch /tmp/...` → `Read-only file system`），qbe 无法写出 `.s`，所有用例在**代码生成阶段**即失败，
被测后端的实际行为（正确与否）完全无法观测。

**解决方案**：
`patches/0001-tools-test.sh.patch`（最小改动 1 行）：
`tmp=/tmp/qbe.zzzz` → `tmp=${TMPDIR:-/tmp}/qbe.zzzz`；
默认行为保持 `/tmp` 不变，配方在 `build()` 中以 `TMPDIR=<build-folder>/qbe-test-tmp` 驱动测试。

**修复后**（同一环境）：
```
$ TMPDIR=<build>/qbe-test-tmp CC=<clang> sh tools/test.sh all
...
All is fine!    # 49 [ok] + 1 upstream skip, 0 fail
```

**在正式 `conan create` 内复验**（`conan-verify` G2，2026-09-16 18:15，`reports/conan-create.log`）：
```
qbe/1.2@ohpcd/stable: RUN: TMPDIR=".../qbe-test-tmp" CC=".../clang" sh tools/test.sh all
abi1.ssa... [ok]
...
vararg2.ssa... [ok]

All is fine!
qbe/1.2@ohpcd/stable: Package '6b129b0688...' created

======== Testing the package: Executing test ========
qbe/1.2@ohpcd/stable (test package): RUN: QBE_BIN=".../p/bin/qbe" QBE_TEST_CC=".../clang" bash test_qbe.sh
qbe consumer E2E passed: target=arm64 hello='hello from qbe' exit=42
```

> 注：上表为第一轮 `conan-verify`（18:15）的摘录。平台 CI 首轮暴露 `test()` 运行环境问题后，
> 配方已改为 `env="conanbuild"`（继承 profile `[buildenv]` 的 SDK `LD_LIBRARY_PATH`，CI worker 上 lld 需要它加载 libxml2）
> 并放宽 `pipefail` 依赖；修复后已复验——本地 CI 门禁（19:33）与 `finish` 内 `conan-verify`（19:36）均再次通过
> （`qbe consumer E2E passed: target=arm64 hello='hello from qbe' exit=42`），过程详见 `notes.md` 对话 #4。

---

## 五、测试环境

```
qbe 1.2 (release tarball, sha256 a6d50eb952525a234bf76ba151861f73b7a382ac952d985f2b9af1df5368225d)
HarmonyOS HongMeng Kernel 1.12.0 aarch64 (Toybox userspace)
clang version 15.0.4 (OHOS SDK LLVM)
Conan 2.29.1 (OHOS-adapted), profile ohos-aarch64-device
构建: make -j1 SHELL=sh CC=<clang> CFLAGS="-std=c99 -O2 -g -Wall -Wextra -Wpedantic"
配置: config.h 由 Makefile 依 uname -m 生成 → #define Deftgt T_arm64
验证: conan-verify G0-G4 PASS（G2 干净构建内全量复跑 + 消费者 E2E）
```

---

*报告生成时间: 2026-09-16*
