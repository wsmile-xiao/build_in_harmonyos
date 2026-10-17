# 测试报告

> **项目**: libforms 1.2.4  
> **测试日期**: 2026-09-28  
> **测试环境**: HarmonyOS PC（aarch64，clang 15 / musl，conan 2.29.1，B 机独立 CONAN_HOME）  
> **测试类型**: 手动功能测试（上游无官方测试套件；消费者证据按 E530 双可执行 test_package）

---

## 一、测试摘要

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 总测试数 | 2 | 100% |
| 通过 (PASS) | 2 | 100% |
| 失败 (FAIL) | 0 | 0% |
| 跳过 (SKIP) | 0 | 0% |

上游测试：发现 0、执行 0、通过 0、失败 0、跳过 0（configure.ac 与 20 个 Makefile.am 清点 TESTS=0、无 check 目标、无 gtest/pytest/criterion 绑定；demos/ 94 个 .c 为需 X server 的交互演示，不构成测试）。

**核心功能通过率**: ✅ **100%**（test_package 消费者用例 2/2）

---

## 二、测试结论

### 2.1 总体评价

✅ 构建产物与 API 表面在无 X server 的 HarmonyOS PC 平台上可链接、可加载、可运行；GUI 路径按 E530 口径不宣称可用。

### 2.2 用例明细

| # | 用例 | 内容 | 预期 | 结果 |
|---|------|------|------|------|
| 1 | libforms_api_surface | 32 个探针（22 libforms + 10 libflimage），`__typeof__(&name)` 编译期类型检查 + 链接期活重定位（probes=32，assertions=0） | 编译链接全通过、运行 rc=0 | PASS |
| 2 | libforms_abi_contract | _Static_assert 钉死 FL_PUP_ENTRY=32B 及字段偏移、FL_COLOR 宽度、FL_VERSION=1、FL_REVISION=2（static=8）；运行期 runtime=2 | 断言全过；XOpenDisplay(NULL) 按无 X 平台实测失败 | PASS |

运行输出（abi_contract）：
```text
ok: runtime: sizeof(FL_PUP_ENTRY) == 32
ok: XOpenDisplay(NULL) fails as measured on HarmonyOS PC
```

### 2.3 已知限制

- 本平台无 X server：forms/fdesign 的运行期 GUI 路径未验证，也不在本包宣称范围内（E530）。
- fd2ps 运行期读 `/usr/local/lib/X11/rgb.txt`（readxpm.c:348），缺文件时该转换路径受限，不影响库本体。

---

## 三、验证命令

```bash
conan create archives/l/libforms/1.2.4 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# Package 8d9ef4e61b71d7eadb8ebb1af0686664ac46c8b3 created；test_package 随 create 执行 2/2 PASS
python3 scripts/ohc-run.py conan-verify libforms 1.2.4   # G0-G3 PASS（reports/conan-verify-report.md）
python3 scripts/ohc-run.py finish libforms 1.2.4 built   # W3 本地 CI 模拟通过（reports/w3-local-ci.log）
```
