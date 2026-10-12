# pd-zexy 2.4.4 功能测试报告

**测试日期:** 2026-09-29
**测试环境:** HarmonyOS (HongMeng Kernel 1.13.0, aarch64)
**编译器:** clang 15 (OHOS SDK, target `aarch64-unknown-linux-ohos`)
**构建系统:** Makefile（上游 vendored pd-lib-builder 0.7.0）
**测试宿主:** `puredata/0.54.1` 的 `bin/pd`（zexy 正是为它编写的引擎）

## 1. 编译测试

### 1.1 编译状态

✅ 完整构建成功：89 个 `.c` → **单一** `zexy.pd_linux`（350528 B，ELF shared object，aarch64）。

```
lib/pd-externals/zexy.pd_linux     350528 B   sha256 75e716cab4b9005d…（前 16 位）
```

构建命令（配方 `build()`）：

```
make -j1 CC="<clang from tools.build:compiler_executables>" \
         PDINCLUDEDIR="<puredata package>/include/pd" with-lpt=no
```

### 1.2 源码修改

无。上游 `*.c` / `*.h` / `Makefile` / `tests/` 未改动，`patches/` 为空。
平台专属对象（x86 并口 `src/lpt.c`）由**上游自带开关** `with-lpt=no` 关闭。

### 1.3 包内容清点

| 路径 | 数量 | 说明 |
|------|------|------|
| `lib/pd-externals/zexy.pd_linux` | 1 | 插件本体（Pd 宿主 `dlopen`，非可链接库） |
| `share/pd-zexy/`（根级） | 15 | `zexy-meta.pd` 等 12 个根级抽象/别名 + `README.txt` / `ChangeLog` / `LICENSE.txt` |
| `share/pd-zexy/abs/` | 51 | zexy 自身抽象（含无扩展名的 `alias`） |
| `share/pd-zexy/reference/` | 78 | 参考补丁（含 `0.INTRO.txt`、`test.mtx`） |
| `share/pd-zexy/tests/` | 47 | **上游回归套件**（36 个可运行补丁 + `testrunner.sh` + `msgfile/*.txt` 等数据） |
| `share/pd-zexy/src/` | 1 | `noisi-test.pd`（上游源码树自带的开发补丁，非构建副产物） |
| `licenses/` | 1 | `LICENSE.txt`（GPL-2.0-or-later） |

合计 194 个文件 + 2 个 Conan 元数据文件（`conaninfo.txt` / `conanmanifest.txt`）= 196（与 §4 一致）。

## 2. 上游测试（R51 三步法）

### 2.1 第 1 步：清点

zexy **有**上游回归套件（不同于同族的 pd-vbap）：

| 项 | 值 |
|----|-----|
| 驱动脚本 | `tests/testrunner.sh`（收集 `find tests -mindepth 2 -name '*.pd'`） |
| 用例总数 | **36** 个可运行补丁，分布在 16 个测试目录 |
| 预期失败 | **4** 项（`fail*.pd`，`testrunner.sh -X` 记为 XFAIL） |
| 断言模型 | 每个补丁向 outlet 送 `1` 表示通过，其他值/超时为失败 |

### 2.2 第 2 步：在可运行环境实际运行

✅ **CI 可运行**（本库与 pd-vbap 的关键差别）：套件经 `puredata/0.54.1` 包内真实 `pd`
宿主驱动，test_package 在 `conan create` 中**完整跑了一遍上游套件**（非抽样、非手写冒烟）。

| 轮次 | TOTAL | PASS | FAIL | XFAIL | 说明 |
|------|-------|------|------|-------|------|
| 首跑（未处理并口对象） | 36 | 13 | 19 | 4 | 宿主报 `Error relocating …: ioperm: symbol not found`，整库不可加载 |
| 加 `with-lpt=no` 后 | 36 | **32** | **0** | 4 | 4 项 XFAIL 为上游预期失败 |

### 2.3 第 3 步：通过率如实回填

**32/36 = 88.9%**；扣除上游标定的 4 项预期失败后，**可运行用例 32/32 = 100%**。

## 3. 鸿蒙专项测试（test_package）

`test_package/` 不用手写冒烟测试，而是**在 CI 中运行上游套件本身**（R51 的同源保证）：

- `test_package/conanfile.py`（94 行）：每轮 `rmtree` 重建全新 staging
  （`build/upstream-suite`）→ 从**被测包**拷入 `zexy.pd_linux` + `share/pd-zexy` 全树 →
  显式断言 `zexy.pd_linux` / `tests/testrunner.sh` / `tests/run1.pd` 存在 →
  调 `run_upstream_suite.sh <stage> <pd>` → 解析 `Testsuite summary` →
  **硬断言 `FAIL == 0` 且 `TOTAL >= 36` 且 `PASS >= 32`**。
- `test_package/run_upstream_suite.sh`（36 行）：`cd "$STAGE"` 后用**相对路径**收集补丁
  （等价上游 `make check`），`TMPDIR`/`HOME` 指向 staging（目标机 `/tmp` 只读），
  `PD=<puredata>/bin/pd LIBDIR=$STAGE ABSDIR=$STAGE/abs bash tests/testrunner.sh -v -Xls`。

### 3.1 结果

```
TOTAL        36
PASS         32
FAIL         0
XFAIL        4
（conan test 内部断言 FAIL==0 && TOTAL>=36 && PASS>=32 → 通过）
```

### 3.2 关键实现点

- **符号层检查**：`nm -uD zexy.pd_linux` 精确计数 `ioperm|iopl|inb|outb` → **0**
  （并存 119 个由 Pd 宿主在加载时提供的引擎符号，属正常插件形态）。
  对**单产物插件库**而言，「链接成功」不构成验收依据，必须补这一步或真实 `dlopen` 冒烟。
- **补丁路径必须相对**：绝对路径会让 `tests/absgn~/abs.pd` 报
  `can't load abstraction within itself`（同一产物实测：绝对 FAIL=1 / 相对 FAIL=0）。
- **破坏性反向验证（L1e/R34）**：staging 每轮清空且显式断言产物存在，
  移走包的 `lib/` 后测试必然失败，不会复用上一轮残留产物。

### 3.3 端到端验证的真实性

test_package 跑的是**上游自己的 36 项回归**（同一份 `tests/` 随包分发），
消费者即真实 Pd 引擎 —— 覆盖 Pd 引擎初始化、`zexy.pd_linux` 装载、
约 90 个类中的 36 项行为用例（列表/符号/消息处理/时间与随机/文件与 MIDI 辅助）。

## 4. 产物核查

| 项 | 结果 |
|----|------|
| `readelf -d` | `NEEDED = libc.so`；`RUNPATH = $ORIGIN`（自包含，无绝对路径 rpath） |
| 未解析符号 | 119 个，全部为 Pd 引擎 API（`gensym` / `pd_error` / `class_new` …，由宿主提供） |
| `ioperm` 族 | 0 |
| 补丁 | 0 |
| 包内文件总数 | 196 |

## 5. 门禁结果

| 门禁 | 结果 |
|------|------|
| 本地 W3（`conan create` 全流程，含 test_package 跑上游套件） | ✅ `rc=0`（`Package … created`） |
| G3 系统同名库隔离 | ✅ 无冲突（仅 `libc.so`） |
| G4 产物完整性 | ✅ `lib/` + `share/` + `licenses/` 齐备 |
| L1e 破坏性反向验证（R34） | ✅ 全新 staging + 产物存在性断言 |
| L2 `--version` 类可执行性 | N/A（插件库，无可执行文件；以 `pd` 宿主装载 + 上游套件代替） |
| L4/L5 与 G0-G4 其余项 | 由 `finish`/CI 流水线复核 |

> 本库为**插件式共享库**（Pd 宿主 `dlopen` 的对象），无 `bin/` 可执行文件 →
> 依 R38 不需要 `commands.json`。
