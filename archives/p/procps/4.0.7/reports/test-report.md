# Test Report — procps 4.0.7

**日期**: 2026-09-04
**环境**: OHOS 6.0 / aarch64（armv8），clang 15.0.4，conan 2.29.1（OHOS 适配版）
**结论**: conan-verify G0-G4 + W3 L 门禁 PASS（L4=warn 已披露）；上游测试 7 PASS / 1 FAIL（环境性）；test_package 全部断言通过

---

## 1. 上游测试（make check，8 程序）

来源：`make check` 于探索构建（前任）、conan create G2 干净构建（本轮）
与 W3 本地 CI（reports/w3-local-ci.log 693-708 行，最近一次完整原文）
多次执行，**统计完全一致**：

```
PASS: library/tests/test_escape
PASS: library/tests/test_pids
PASS: library/tests/test_uptime
PASS: library/tests/test_sysinfo
FAIL: library/tests/test_version
PASS: library/tests/test_namespace
PASS: src/tests/test_fileutils
PASS: src/tests/test_strtod_nol
# TOTAL: 8   # PASS: 7   # FAIL: 1   # SKIP: 0   # XFAIL: 0   # ERROR: 0
```

### test_version 失败定性：环境性（OHOS 限制，非适配缺陷）

- 失败子用例：`procps_linux_version()`
- 根因：OHOS `/proc/sys/kernel/osrelease` = `"HongMeng Kernel 1.12.0"`
  （非标准 a.b.c 版本串）、`/proc/version` 不可读（cat 返回 Permission
  denied）→ 库内 sscanf 解析失败
- 同程序 `LINUX_VERSION` macro 子用例 **PASS**
- 处置：**未修改上游断言**，build() 中 try/except 记录后继续构建；
  已沉淀知识草稿（HongMeng 内核版本串影响 sscanf 版本解析类测试）

## 2. conan-verify 门禁（G0-G4）：PASS（含警告披露）

| 门禁 | 结果 | 说明 |
|------|------|------|
| G0 预构建风险评估 | PASS | 命中 E490（autotools 脚本可执行位风险提示，非阻塞：conan get 保留权限位，两次构建 + W3 未触发） |
| G1 配方完整性 | PASS | 字段/结构/test_package/MANIFEST 齐全 |
| G2 conan create | PASS | ci/conan/profiles/ohos-aarch64 干净构建 |
| G3 系统同名库隔离 | PASS | 无系统同名 .so 冲突（R26，静态） |
| G4 产物完整性 | PASS | bin 18 / lib libproc2.a / include 8 头（附警告：无法找到程序包 ID，不影响判定） |

verify 侧 L2/L4/L5 因无 cache 路径跳过，实际 L 门禁由 W3 本地 CI 执行
（reports/w3-local-ci.log 1105-1140 行）：

| W3 L 门禁 | 结果 | 说明 |
|------|------|------|
| L0/L1 | pass | 配方检查 + 上游测试与 test_package 执行 |
| L2 smoke | pass | 18 个二进制 --version 冒烟全过 |
| L4 安全扫描 | **warn** | 0003-config.guess.patch 内 NetBSD 注释英文单词 targets 命中扫描器危险函数模式 gets\b（无前置锚定的子串误匹配；补丁实际不含危险调用）——warn 非 fail，abook/aspell 同类补丁同性质 |
| L5 产物基线 | pass | bin/ has content |
| L1e 负测试 | pass | 移除产物后测试真实失败（R34 反证） |

报告：`conan-verify-report.md`；W3 完整日志：`w3-local-ci.log`。

## 3. test_package 实测（消费者视角，R34 实质测试）

### 3.1 C API 层（test_procps.c，链接打包 libproc2）

w3-local-ci.log 1089-1092 行（W3 完整运行）：

```
procps_uptime: up=1573638.6s idle=26872690.6s
procps_loadavg: 20.78 20.54 20.48
pids API: 52 PIDs fetched via PIDS_ID_PID
libproc2 C API: all checks passed
```

conan-create.log 136-138 行（最终缓存命中复核运行）实测 up=1573470.6s /
61 PIDs——uptime 与 PID 计数为系统实时状态，各次运行数值自然不同，
断言语义不变全部通过。

断言明细（12 个，语义与上游 testsuite 一致——成功调用返回 0）：

| API | 断言 | 结果 |
|-----|------|------|
| `procps_uptime(&up,&idle)` | rc==0 ∧ up>0 ∧ idle>0 | ✅ up=1573638.6s（W3） |
| `procps_loadavg(&a1,&a5,&a15)` | rc==0 ∧ av1≥0 | ✅ 20.78/20.54/20.48（W3） |
| `procps_pids_new(&info,{PIDS_ID_PID},1)` | rc==0 | ✅ |
| `procps_pids_get(info,PIDS_FETCH_TASKS_ONLY)` | PIDS_VAL(0,s_int,stack)>0 计数>0 | ✅ 52 PIDs（W3） |
| `procps_pids_unref(&info)` | rc==0 | ✅ |

### 3.2 二进制层（can_run=True，conanrun 环境执行打包产物）

| 命令 | 断言 | 结果 |
|------|------|------|
| `ps --version` | 输出含 "procps-ng" | ✅ |
| `free` | 输出含 "Mem" | ✅ |
| `uptime` | 输出含 "load average" | ✅ |

交叉构建场景（can_run=False）：编译+链接成功即验证 API 可消费，运行时
在 OHOS 设备验证（acr 同款模式）。

## 4. 前后一致性核查

| 指标 | 前任探索构建 | conan create（G2） | W3 本地 CI | 一致 |
|------|-------------|--------------------|-----------|------|
| 上游测试 | 7 PASS / 1 FAIL / 0 SKIP | 7 PASS / 1 FAIL / 0 SKIP | 7 PASS / 1 FAIL / 0 SKIP | ✅ |
| test_version 失败 | 环境性（版本串） | 环境性（版本串） | 环境性（版本串） | ✅ |
| 产物 bin 数 | 17+sysctl | 18（conan 包内） | 18（conan 包内） | ✅ |
