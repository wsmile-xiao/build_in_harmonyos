# Quality Report — j4-dmenu 3.2

**Verdict**: PASS

**被测产物**: `<install-prefix>/bin/j4-dmenu-desktop`（`aarch64-unknown-linux-ohos`，OHOS 宿主可直接执行）
**宿主**: HarmonyOS PC aarch64
**生成命令**: `PYTHONPATH=scripts python3 -m ohc verify-build --software j4-dmenu --version 3.2 --install-prefix <prefix>`
**日期**: 2026-09-25（首版） / 2026-09-26（本次补审，含新增消费者测试）

## 门禁汇总（G1–G4）

| 门禁 | 结果 | ✅ | ⚠️ | ❌ |
|------|------|----|----|----|
| G1 Binary Integrity | PASS | 1 | 0 | 0 |
| G2 Functional | PASS | 0 | 1 | 0 |
| G3 Portability | PASS | 1 | 1 | 0 |
| G4 Archive | PASS | 0 | 0 | 0 |

补丁: **0 个**（零补丁适配）

> 两个 ⚠️ **均为工具侧限制，非产物缺陷**，逐条说明见下。判定维持 **PASS**。

---

## ⚠️ 项逐条说明

### ⚠️ G2 `j4-dmenu-desktop: --version failed` —— 门禁工具 bug，非真实失败

上面 G2 的 `⚠️ j4-dmenu-desktop: --version failed` 与事实不符。同一二进制直接执行：

```bash
$ <prefix>/bin/j4-dmenu-desktop --version
3.2            # rc=0
```

**根因**（`scripts/ohc/verify_build.py`，基础设施缺陷，本 PR 未修改）：

- `VerifyBuild._run()` 定义处已固定 `timeout=15`：

  ```python
  def _run(self, cmd, **kw):
      r = subprocess.run(cmd, capture_output=True, text=True, timeout=15, **kw)
  ```

- 而 `gate2_functional()` 第 129 行又传入 `timeout=5`：
  `self._run([str(b), "--version"], timeout=5)`

- 于是 `subprocess.run()` 收到重复的 `timeout` 关键字，抛
  `TypeError: got multiple values for keyword argument 'timeout'`，
  被同一函数的 `except Exception: return 1, ""` 静默吞掉，返回 `(1, "")`，
  再被判定为"--version failed"。

**复现**：

```python
v._run(["<bin>", "--version"])            # (0, '3.2\n')   ✅ 正常
v._run(["<bin>", "--version"], timeout=5) # (1, '')        ❌ TypeError 被吞
```

**影响**：G2（功能可用性）门禁对所有软件**恒为告警、永不通过**，
即该门禁实际上从未真正验证过任何二进制；`PASS` 判定中的
"✅0 ⚠️1" 不代表功能有问题。仅第 129 行传了 `timeout`，故 G1/G3/G4 不受影响。

**本次处置**：`scripts/` 属基础设施只读文件（角色约束 W2/铁律），
不在本 PR 修改；已另行以反馈形式上报该缺陷。
本版本的判定维持 **PASS**（依据：二进制实机执行 `--version`=3.2、`--help`=0，
见 `reports/test-report.md`）。

### ⚠️ G3 `not signed` —— 宿主 `file` 不识别 OHOS 签名节

G3 的可移植性检查分两项，本产物结果为 ✅1 ⚠️1：

| 检查 | 结果 | 证据 |
|------|------|------|
| RPATH / RUNPATH | ✅ PASS | `patchelf --print-rpath` = `$ORIGIN/../lib:$ORIGIN/../lib/external`，**基于 `$ORIGIN` 可重定位**，不含构建机绝对路径 |
| 签名（`file -b` 含 signed/signature） | ⚠️ WARN | `file -b` = `ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped` |

**为什么是告警而非缺陷**：G3 用宿主 GNU `file(1)` 判定签名，而 GNU `file`
**不认识 OHOS 的签名节**（OHOS 用 `.codesign` + `.note.ohos.ident`，GNU `file`
无法据此输出 "signed"）。本产物**确实带有鸿蒙签名节**，已用 `readelf` 独立证实：

```text
$ readelf -SW bin/j4-dmenu-desktop | grep -iE 'codesign|note.ohos'
  [ N] .note.ohos.ident   NOTE   ...   OHOS
  [ N] .codesign          PROGBITS ...
```

该证据已固化为 `test_package/test_ohos.sh` 的第 8、9 条断言（`.note.ohos.ident`
含 `OHOS` 标识、`.codesign` 节存在），在每次 `conan create` 的 test 阶段自动复验。
故此为**宿主工具识别能力限制**，不是打包缺陷。

---

## 本次补审新增：消费者端到端 + 鸿蒙平台特有测试（2026-09-26）

针对提审反馈「鸿蒙特有测试 N=0」，本次为 `test_package/` 新增两层真实消费者测试，
并纳入 `conan create` 的 test 阶段自动执行：

| 测试 | 结果 | 断言数 | 性质 |
|------|------|-------:|------|
| `test_package/test.sh` | PASS | 3 断言 + 2 前置检查 | 冒烟（原有） |
| `test_package/test_e2e.sh` | PASS | 9 个用例 / 14 条断言 | **完整消费者端到端用例**（真实 `execvp` 启动目标程序） |
| `test_package/test_ohos.sh` | PASS | 16 条断言 | **鸿蒙平台特有断言**（产物形态 + 平台约束行为） |

- `test_e2e.sh` 构造隔离的 XDG 桌面环境 + 伪 dmenu（复刻真实 dmenu 的 stdin/stdout 协议），
  驱动被测二进制走完 **扫描 `.desktop` → 解析 → 过滤 → 候选列表 → 选择 → 组装命令行 →
  `fork/execvp` 启动目标程序** 全链路，并以「目标程序是否真被启动、收到什么参数」验证结果，
  而非仅看退出码。
- `test_ohos.sh` 覆盖：ELF64 + AArch64 + PIE、musl 加载器 `/lib/ld-musl-aarch64.so.1`、
  `$ORIGIN` 可重定位 RUNPATH、动态依赖无 glibc 专有库、OHOS 专有节
  `.note.ohos.ident`/`.codesign`、无 TEXTREL、`/system/bin/sh`(mksh) 与 bash 双 shell 可执行、
  只读 `/tmp` 下 `Terminal=true` 优雅报错、无 dmenu 优雅退出、无 DISPLAY 无头可运行、
  免 `LD_LIBRARY_PATH`、产物完备（bin + man + bash/zsh/fish 补全）。
- 三层测试已由 `test_package/conanfile.py` 的 `test()` 串行调用；
  逐项结果与原始输出见 `reports/test-report.md` 第 3 节。

> 新增测试**未修改上游任何测试用例**（`patches_applied: []`），
> 也不属于「上游无测试用例的补全」——上游自带 Catch2 79 项 + pytest 12 项测试套件，
> 本次新增属**鸿蒙特有测试**类别，已在 PR 正文「适配后测试用例统计」中单列。

---

## 结论

- **Verdict: PASS** —— G1/G2/G3/G4 四项门禁均无 ❌；两处 ⚠️ 已逐条定位为工具侧限制
  （G2 门禁自身 `TypeError`、G3 宿主 `file` 不识别 OHOS 签名节），非产物缺陷。
- 零补丁适配（`patches_applied: []`），上游源文件一字未改。
- 新增消费者端到端与鸿蒙平台特有测试全部通过（9 用例 / 14 断言 + 16 断言），
  已纳入 CR 流水线自动复验。
