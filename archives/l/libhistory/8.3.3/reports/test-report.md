# libhistory 8.3.3 测试报告

> **项目**: libhistory 8.3.3
> **测试日期**: 2026-09-19
> **测试环境**: HarmonyOS（HongMeng Kernel）aarch64，clang 15（OHOS SDK），Conan 2.29.1，profile ohos-aarch64
> **测试类型**: Conan test_package 消费者测试（ctest）+ W3 本地 CI 模拟（ci/conan/build_and_test.sh 同源）

---

## 一、测试摘要

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 总测试数 | 1（ctest 注册，含 9 项断言） | 100% |
| 通过 (PASS) | 1 | 100% |
| 失败 (FAIL) | 0 | 0% |
| 跳过 (SKIP) | 0 | 0% |

**上游测试**: 上游 readline 8.3 无自动化测试套件（`Makefile.in:347` 的 `check:` 目标为空，无 tests/ 目录，无 ctest/pytest 注册），上游测试入口 0/0。
**核心功能通过率**: ✅ **100%（1/1 用例，9/9 断言）**

---

## 二、测试结论

### 2.1 总体评价

✅ **通过**。libhistory 全部核心 API（历史记录增删查、统计、文件无关操作）在鸿蒙 PC aarch64 上功能正常；静态库（-fPIC）可正常链接，消费者测试程序编译、链接、运行全部成功。

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| 无（本轮无未解决问题） | — | — |

### 2.3 可用功能清单

```
✅ 历史记录管理: using_history / add_history / history_get / history_length
✅ 历史检索: history_search（子串）/ history_set_pos / next_history 遍历
✅ 历史条目维护: remove_history / free_history_entry / clear_history
✅ 历史统计: history_total_bytes
✅ 版本宏: HS_HISTORY_VERSION (0x0803)
✅ 静态库: libhistory.a（-fPIC，可链入共享库）
✅ pkgconfig: history.pc
```

### 2.4 已知限制

1. 本包只交付 history 组件（libhistory.a），不含 readline 行编辑库；需要行编辑的消费者应依赖 readline 包
2. 上游无测试套件，自动化验证完全依赖 test_package 消费者测试（9 项断言）

---

## 三、测试详情

### 3.1 通过的测试

执行方式：`ctest --output-on-failure -C Release`（test_package/test_libhistory）

| 测试项 | 功能 | 结果 |
|--------|------|------|
| Test 1 | HS_HISTORY_VERSION >= 0x0803（history.h 版本宏） | ✅ PASS（0x803） |
| Test 2 | using_history + 初始状态（history_length == 0） | ✅ PASS |
| Test 3 | add_history ×2 + history_get(history_base) 回读 "first command" | ✅ PASS |
| Test 4 | history_length == 2 | ✅ PASS |
| Test 5 | history_search("second", 1) 子串匹配 | ✅ PASS（pos=0） |
| Test 6 | history_set_pos(0) + next_history 遍历至第二条 | ✅ PASS |
| Test 7 | remove_history(0) + free_history_entry，history_length == 1 | ✅ PASS |
| Test 8 | history_total_bytes() > 0 | ✅ PASS（14） |
| Test 9 | clear_history 清理（history_length == 0） | ✅ PASS |

ctest 汇总：`100% tests passed, 0 tests failed out of 1`

### 3.2 失败的测试

| 测试项 | 原因 | 说明 |
|--------|------|------|
| 无 | — | — |

### 3.3 跳过的测试

| 测试项 | 跳过原因 |
|--------|----------|
| 无 | — |

---

## 四、验证链路

### 4.1 Conan 配方验证（conan-verify，G0–G4/L2/L4/L5）

`reports/conan-verify-report.json`：verdict **PASS**，G0–G4、L2、L4、L5 全部 passed；
G2 conan create 从干净源码构建成功，test_package 消费者测试通过（evidence.test_package.passed=true）。
报告由本轮工作目录验证器副本生成，runtime_sha256 与任务冻结快照绑定（哈希见
audit-input.json 的 validation_evidence，随验证轮次记录，不在本报告中复写）。

### 4.2 W3 本地 CI 模拟

`ci/conan/setup.sh` + `ci/conan/build_and_test.sh`（与线上 CI 同源脚本）在本轮 ws/tmp 私有
CONAN_HOME 内执行：L0 质量门禁通过（KC_ERRORS=0、JC_ERRORS=0），conan create +
test_package 通过。完整性以 `.ci-result.json`（exit_code=0，step=W3_local_ci，
integrity_hash 与 log_sha256 字段绑定本轮 `reports/w3-local-ci.log`）为准，
逐字节哈希由 audit-input.json 的 validation_evidence 固化，本报告不复写轮次哈希。

### 4.3 补丁应用验证

4 个补丁（readline83-001/002/003 unified 等价转换 + 0001-config.guess）在 conan create
的 Apply patch 阶段全部成功；config.guess 补丁生效证据：configure 输出
`checking build system type... aarch64-unknown-linux-ohos`。

---

## 五、测试环境

```
软件: libhistory 8.3.3（readline-8.3 + 官方补丁 readline83-001..003）
源码: https://ftp.gnu.org/gnu/readline/readline-8.3.tar.gz
      sha256 fe5383204467828cd495ee8d1d3c037a7eba1389c22bc6a041f627976f9061cc
目标: aarch64-unknown-linux-ohos（OHOS，os.version=6.0）
编译器: /data/service/hnp/bin/clang（clang 15），CFLAGS -fPIC -O2
构建: autotools，--enable-static --disable-shared，make -j1
产物: libhistory.a（静态）、history.pc、include/readline/ 头文件
```

---

*报告生成时间: 2026-09-19*
