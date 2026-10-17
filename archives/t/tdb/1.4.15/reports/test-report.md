# tdb 1.4.15 测试报告

> **项目**: tdb 1.4.15（Samba trivial database，键值数据库库 + 命令行工具）
> **测试日期**: 2026-09-16
> **测试环境**: HarmonyOS PC aarch64（HongMeng Kernel 1.12.0，musl libc，clang 15.0.4）
> **测试类型**: 上游官方测试套件（waf `testonly`）+ Conan 消费者测试（test_package）

---

## 一、测试摘要

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 总测试数 | 40 | 100% |
| 通过 (PASS) | 40 | 100% |
| 失败 (FAIL) | 0 | 0% |
| 跳过 (SKIP) | 45（python 绑定测试，`--disable-python`） | — |

**核心功能通过率**: ✅ **100%（40/40）**

> 口径：37 个 TAP 单元测试（`wscript` 的 `tdb1_unit_tests` 列表）+ 2 个 shell
> 集成测试（`test_tdbbackup.sh` / `test_tdbdump.sh`）+ 1 个 `tdbtorture` 多进程
> 压力测试程序。另有 45 项 python 绑定测试（`python/tests/simple.py`）因本包
> 以 `--disable-python` 构建纯 C 库而未启用（技术原因见 §四）。

---

## 二、测试结论

### 2.1 总体评价

✅ **通过**。上游 C 测试套件在 OHOS 真机全量执行、全部通过；消费者测试
（`conan create` 的 L1 测试）真实调用公开 API 并断言行为，全部通过。

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| `lib/replace` mkstemp 运行探针在鸿蒙沙箱必失败且上游标 mandatory | configure 直接中断 | 🔴（已修复：补丁 0001） |
| python 绑定 pyembed 探针链接失败（`-lintl` 不存在） | 仅影响可选 python 绑定 | 🟡（已规避：`--disable-python`） |
| `--disable-python` 时上游仍误跑 python 测试 | `make test` 误判红 | 🟡（已修复：补丁 0002） |

### 2.3 可用功能清单

```
✅ libtdb 核心 API: tdb_open/tdb_store/tdb_fetch/tdb_delete/tdb_close（消费者程序实测）
✅ 事务/遍历/恢复/加锁等 37 个单测覆盖的功能路径（无 robust mutex 自动降级模式下全过）
✅ CLI: tdbtool / tdbdump / tdbbackup / tdbrestore（tdbdump 在消费者测试中实跑）
⚠️ robust mutex 模式: musl 未实现 pthread_mutexattr_setrobust，自动关闭（与上游非 robust 平台一致）
❌ python 绑定 pytdb: 未构建（平台 python3-config --embed 携带不存在的 -lintl）
```

### 2.4 已知限制

1. 本包为纯 C 库构建（`--disable-python`），不含 python 绑定；
2. robust mutex 锁模式不可用（平台 libc 限制），tdb 自动降级为普通进程共享锁。

---

## 三、测试详情

### 3.1 通过的测试

| 测试项 | 功能 | 结果 |
|--------|------|------|
| `make test` → 37 × `tdb1-run-*` | TAP 单元测试：基础读写、事务、遍历、恢复、deadlock、mutex 系列、corrupt/endian/oldhash 等 | ✅ PASS |
| `make test` → `test_tdbbackup.sh` | tdbbackup 正常/只读备份 + tdbdump 回读比对 | ✅ PASS |
| `make test` → `test_tdbdump.sh` | tdbdump 输出与预期文本比对 | ✅ PASS |
| `make test` → `tdbtorture` | 多进程并发压力（testsuite returned 0） | ✅ PASS |
| `conan create` → test_package | 消费者程序 `test_tdb`：9 处断言（open/store/fetch/delete/close，含防重复与删除后置空） | ✅ PASS |
| `conan create` → test_package | 包内 `tdbdump` 读取消费者创建的数据库 | ✅ PASS |

### 3.2 失败的测试

无。

### 3.3 跳过的测试

| 测试项 | 跳过原因 |
|--------|----------|
| `python/tests/simple.py`（45 项，pytdb 绑定接口测试） | 本包以 `--disable-python` 构建纯 C 库；pytdb 未构建时该测试无法运行（补丁 0002 显式跳过并打印原因，不再误报失败）。平台 `python3-config --embed` 输出含平台不存在的 `-lintl`，启用绑定的 pyembed 探针无法通过 |

---

## 四、关键问题分析

### 问题 1: mkstemp 运行探针导致 configure 中断

**现象**：
```
Checking for HAVE_SECURE_MKSTEMP ... : not found
from .../lib/replace: The configuration failed False
```

**根因分析**：`lib/replace/wscript` 的 mkstemp 探针需要运行程序，硬编码写
`/tmp/test.XXXXXX` 并断言文件权限为 `0600`。鸿蒙 `/tmp` 只读（E002），且 HMDFS
将文件权限归一化为 `0640`（chmod 不生效，E046）——探针**必然失败**，而上游将其标记为
`mandatory=True`，直接中断 configure。

**解决方案**：补丁 0001（`mandatory=True` → `False`）。检查仍如实运行并报告
`not found`，`lib/replace` 自动编译内置 mkstemp 替代实现（`REPLACE_MKSTEMP`）。
不在补丁中硬编码设备路径、不放宽 0600 断言语义。

### 问题 2: pyembed 探针链接失败（-lintl）

**现象**：
```
Asking python-config for pyembed '--cflags --libs --ldflags --embed' flags : yes
Testing pyembed configuration : Could not build a python embedded interpreter
err: ld.lld: error: unable to find library -lintl
```

**根因分析**：平台 `python3-config --embed` 输出 `-lintl`，而 OHOS/musl 无
libintl（`Checking for library intl : no`），试链接失败；waf 的 pyembed 探针为 fatal。

**解决方案**：本包定位为纯 C 库，使用官方 `--disable-python` 关闭可选 python
绑定，同时避免包与构建机 python ABI 耦合。

### 问题 3: `--disable-python` 下 python 测试仍被误跑

**现象**：
```
Running Python test with python3: python/tests/simple.py
Python test failed: PYTHONPATH=bin/python python3 python/tests/simple.py
python testsuite returned 1 → make: *** Error 1
```

**根因分析**：`SAMBA_CHECK_PYTHON` 即使在 `--disable-python` 下仍把 `python3`
记入 `python_interpreters`，`wscript` 的 `testonly` 无条件调用
`RUN_PYTHON_TESTS`，而 pytdb 未构建 → `import tdb` 失败 → `make test` 误判红。

**解决方案**：补丁 0002 在 `testonly` 中加 `env.disable_python` 守卫，显式打印
`python testsuite skipped (--disable-python)`；C 测试全部保留运行。

---

## 五、测试环境

```
设备: HarmonyOS PC（aarch64，HongMeng Kernel 1.12.0）
编译器: clang 15.0.4（OHOS SDK）
驱动: python3 3.14.7（waf）
Conan: 2.29.1（OHOS 适配版），test_package 构建配置 Release
配置: ./configure --prefix=<pkg> --disable-python
```

---

*报告生成时间: 2026-09-16*
