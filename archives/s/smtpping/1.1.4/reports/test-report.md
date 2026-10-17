# smtpping 1.1.4 测试报告

> **项目**: smtpping（SMTP 服务器延迟/抖动/吞吐测量工具）
> **测试日期**: 2026-09-20
> **测试环境**: HarmonyOS 6.1.0.117（HongMeng Kernel 1.12.0，aarch64 HAD-W32），OHOS SDK clang 15.0.4，Conan 2.29.1（OHOS 适配版），profile `ohos-aarch64-device`
> **测试类型**: 消费者 E2E（test_package：mock SMTP 服务器回环全事务）+ CLI 契约 + 负路径控制

---

## 一、测试摘要

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 上游自动化用例总数 | 0 | —（上游无测试套件，R51 证据见 3.1） |
| 适配后消费者测试断言（test_package） | 15 | 100% |
| 通过 (PASS) | 15 | 100% |
| 失败 (FAIL) | 0 | 0% |

**核心功能通过率**: ✅ **100%（15/15）**

---

## 二、测试结论

### 2.1 总体评价

✅ **通过**。正式 `conan create`（W3/CI 同源）在真实鸿蒙 PC 设备上完成
configure/build/install，并以 mock SMTP 服务器回环验证了完整 SMTP 事务
（banner → HELO → MAIL FROM → RCPT TO → DATA → QUIT）与各阶段 RTT 统计输出；
CLI 契约与两条负路径（关闭端口、MX 解析回退）均通过。

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| OHOS 无 glibc 重入解析器 API（res_n*） | 上游 resolver.cpp 无法编译 | 🟡 已修复（补丁 0001/0002 移植到 res_query） |
| CMake ≥4.0 拒绝 `cmake_minimum_required(VERSION 2.8)` | configure 阶段 | 🟡 已修复（配方注入 `CMAKE_POLICY_VERSION_MINIMUM=3.5`，上游 v1.1.5 同款修法） |
| HMDFS 下 make jobserver mkfifo 报 `Operation not permitted` | 仅告警 | 🟢 平台特性，make 自动串行继续，产物正确 |

### 2.3 可用功能清单

```
✅ DNS 解析: MX 查询 + A/AAAA 回退（res_query 真机实测，halon.io MX 2 条答案）
✅ 完整 SMTP 探测事务: banner/HELO/MAIL FROM/RCPT TO/DATA/QUIT
✅ 统计输出: connect/banner/helo/mailfrom/rcptto/data/datasent/quit min/avg/max
✅ CLI 契约: -v/-h/无参数（退出码与 usage 输出）
✅ 负路径: 连接失败安全退出、解析失败安全退出（不崩溃）
⚠️ 吞吐/并发（-P/-r）: 代码路径基于 fork + mmap 共享计数，本报告未做多进程压测
```

### 2.4 已知限制

1. 上游无自动化测试套件（无 `tests/`、无 `enable_testing()/add_test()`），
   适配后以消费者 E2E 补全（15 条断言）。
2. 补丁将解析器改为进程全局态；smtpping 并发模型为 `fork()`（非线程），
   不存在数据竞争；多线程复用该代码需另行加锁。
3. 真实邮件服务器投递不在 CI 范围；E2E 使用协议兼容的 mock SMTP 服务器。

---

## 三、测试详情

### 3.1 上游测试用例清点（R51）

| 检查项 | 结果 |
|--------|------|
| 源包内 `tests/`、`test/`、`unittests/` 目录 | 无（源包共 9 个文件） |
| `CMakeLists.txt` 中 `enable_testing()` / `include(CTest)` / `add_test()` | 无 |
| 测试框架依赖 | 无 |
| 唯一测试性产物 | 无（`smtpping.dev` 为 Windows Dev-C++ 工程文件，非测试） |
| **上游自动化用例数** | **0**（清点证据同步记录于 `test_package/MANIFEST.yml`） |

### 3.2 适配后测试（补全，`test_package/test.sh`，15 断言）

| 分组 | 断言 | 验证内容 | 结果 |
|------|:---:|----------|------|
| CLI 契约 | A1-A4 | 二进制可执行；`-v` 输出 1.1.4；无参数退出码 2 + stderr usage；`-h` 退出码 0 + stdout usage | ✅ 4/4 |
| 回环 E2E | A5-A13 | mock SMTP 服务器就绪；对 mock 的完整探测退出码 0；统计输出 "1 e-mail messages transmitted" 与 "SMTP ping statistics"；服务器端 transcript 含 HELO/MAIL FROM/RCPT TO/QUIT；mock 服务器完成会话退出码 0 | ✅ 9/9 |
| 负路径 | A14-A15 | 关闭端口（127.0.0.1:1）→ `connect() failed` + `no pings were sent` 且退出码 0；`test@localhost` MX→A/AAAA 解析回退路径不崩溃（退出码 0） | ✅ 2/2 |
| **合计** | **15** | | **✅ 15/15（100%）** |

`conan create` 实测输出（节选）：

```text
  [PASS] A1 binary present and executable: .../p/bin/smtpping
  [PASS] A2 smtpping -v reports 1.1.4 (got: 1.1.4)
  [PASS] A3 no-argument invocation exits 2 with usage on stderr (rc=2)
  [PASS] A4 smtpping -h exits 0 with usage (rc=0)
  [PASS] A5 mock SMTP server listening on 127.0.0.1:39270
  [PASS] A6 smtpping probe against mock server exits 0 (rc=0)
  [PASS] A7 statistics report 1 transmitted message
  [PASS] A8 statistics header present
  [PASS] A9-A12 transcript contains 'HELO '
  [PASS] A9-A12 transcript contains 'MAIL FROM:'
  [PASS] A9-A12 transcript contains 'RCPT TO:'
  [PASS] A9-A12 transcript contains 'QUIT'
  [PASS] A13 mock server completed the session and exited 0 (rc=0)
  [PASS] A14 closed-port negative control: rc=0, connect() failed + no pings sent
  [PASS] A15 resolver fallback path completes without crash (rc=0)
test_smtpping: 15/15 assertions passed
test_smtpping: ALL TESTS PASSED
```

### 3.3 设备侧手工冒烟（.work 源码，独立于 conan）

```text
smtpping -v                          -> 1.1.4 (rc=0)
smtpping -h                          -> Usage 输出 (rc=0)
mock SMTP 回环（端口 2525）           -> PING ... / seq=1 connect=0.55ms ... /
                                        "1 e-mail messages transmitted" (rc=0)
关闭端口 2599                         -> "seq=0: connect() failed 127.0.0.1" +
                                        "--- no pings were sent ---" (rc=0)
test@localhost（MX 解析路径）         -> "no mx, failling back on A/AAAA record" +
                                        解析到 127.0.0.1/::1（res_query 真机可用）
```

### 3.4 跳过的测试

| 测试项 | 跳过原因 |
|--------|----------|
| 真实 SMTP 服务器投递 | 需要外部邮件服务器；协议链路已由 mock SMTP 回环 E2E 覆盖 |
| `-P` 多进程吞吐压测 | 非正确性验证必需；`-P` 为 fork 并发，无共享可写状态（除 mmap 计数器） |

---

## 四、关键问题分析

### 问题1: OHOS 缺 glibc 重入解析器 API（补丁 0001/0002）

**现象**：`res_ninit`/`res_nquery`/`res_nclose` 未声明（编译失败）；NDK
`resolv.h` 只声明经典 API，设备 libc.so 亦无 `res_n*` 符号。
**根因**：OHOS libc 为 musl 系，不实现 glibc 的重入解析器接口。
**解决方案**：移植到 `res_query()` + 全局 `h_errno`（响应解析原语
`HEADER`/`GETSHORT`/`dn_expand`/`dn_skipname` OHOS 齐备，解析逻辑零改动）；
smtpping 单线程/fork 并发，全局态安全。已沉淀知识草稿 E584。

### 问题2: CMake 4.x 拒绝旧 policy（配方级修复，零补丁）

**现象**：`cmake_minimum_required(VERSION 2.8)` 在 CMake ≥4.0 报
"Compatibility with CMake < 3.5 has been removed"。
**解决方案**：配方 `generate()` 注入 `CMAKE_POLICY_VERSION_MINIMUM=3.5`
（上游 v1.1.5 通过 PR #13 用提升 policy 版本的同款修法），源码保持原样。
知识参考 E103/E187。

---

## 五、测试环境

```
设备: HarmonyOS PC 6.1.0.117 / HongMeng Kernel 1.12.0 aarch64 (HAD-W32)
工具链: OHOS SDK 26.0.0.18 native clang/clang++ 15.0.4 (aarch64-linux-ohos)
Conan: 2.29.1 (OHOS 适配版), profile ohos-aarch64-device
构建: CMake 4.4.3 + Unix Makefiles, Release
包: smtpping/1.1.4@ohpcd/stable
产物: bin/smtpping, man/man1/smtpping.1, licenses/LICENSE
源码: https://github.com/halon/smtpping/archive/refs/tags/v1.1.4.tar.gz
      sha256 beca8c44133b91ebe9fdfd044d8dee0947aa7683cba7b0e509ce15cda8fef74a
```

---

*报告生成时间: 2026-09-20*
