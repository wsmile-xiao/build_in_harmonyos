# 积分赛事 PR body — smtpping 1.1.4

- **三方库名称**：smtpping
- **上游版本**：v1.1.4
- **上游仓库地址**：https://github.com/halon/smtpping（原 halonsecurity/smtpping）
- **适配路径**：路径 A（基础适配）
- **使用知识库**：openharmony-compile-agent 技能库（SKILL.md v12.22 + iron-rules R1-R52；参考知识条目 E516（OHOS libc 解析器状态差异同族）/ E103、E187（CMake policy 版本）；新增知识草稿 E584）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 来源：源包 9 个文件，无 tests/ 目录；CMakeLists.txt 无 enable_testing()/include(CTest)/add_test() |
| 集成测试 | 0 | 上游无集成测试框架 |
| 其他测试 | 0 | smtpping.dev 为 Windows Dev-C++ 工程文件，非测试用例 |
| **合计** | **0** | 清点证据见 `test_package/MANIFEST.yml`（R51） |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 不变 | 上游无单元测试 |
| 集成测试 | 0 | 不变 | 上游无集成测试 |
| 鸿蒙特有测试 | 15 断言 | 新增 | `test_package/test.sh`：mock SMTP 服务器回环全事务 E2E（9 断言）+ CLI 契约（4 断言）+ 负路径控制（2 断言），`conan create` 自动执行 |
| **合计** | **15 断言** | **+15** | |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

> - **补全的测试范围**：消费者 E2E 15 条断言——CLI 契约（可执行性 / `-v` 版本 / 无参数退出码 2 + usage / `-h` 退出码 0）；mock SMTP 服务器回环完整事务（banner → HELO → MAIL FROM → RCPT TO → DATA → QUIT，统计输出与服务器端 transcript 双向对账）；负路径控制（关闭端口连接失败安全退出、`test@localhost` MX→A/AAAA 解析回退不崩溃）
> - **补全原因**：上游无自动化测试套件（无 tests/ 目录、CMakeLists 无测试注册），无任何可运行的上游用例
> - **新增测试文件清单**：
>   1. `archives/s/smtpping/1.1.4/test_package/test.sh` — 15 条断言主脚本（随包提交）
>   2. `archives/s/smtpping/1.1.4/test_package/mock_smtp_server.c` — 极简 SMTP 应答服务器，由 test_package 内编译（随包提交）
>   3. `archives/s/smtpping/1.1.4/test_package/conanfile.py`、`CMakeLists.txt` — 消费者测试驱动与构建定义

## 验证结果

- 编译状态：通过（同一配方经 `conan-verify` G2、本地 CI 门禁、`finish` W3 多次干净 `conan create`）
- 上游测试用例通过率：0/0（上游无测试套件；清点证据见 `test_package/MANIFEST.yml`）
- 新增测试用例通过率：15/15（100%，复跑 ≥3 次均通过）

## 补充说明

- **2 个补丁（OHOS 解析器 API 兼容，PF5 检查通过：无平台宏）**：上游 `resolver.cpp` 使用 glibc 重入解析器 API（`res_ninit`/`res_nquery`/`res_nclose` + `struct __res_state`），而 OHOS libc/NDK 只提供经典非重入 API（`res_query` + 全局 `h_errno` + `dn_expand`/`dn_skipname`；NDK `resolv.h` 无 `res_n*` 声明，设备 `libc.so` 无该符号）。补丁 0001/0002 将 Resolver 移植到 `res_query()`，响应解析逻辑零改动；smtpping 为单线程/`fork` 并发模型，进程级全局解析器状态安全。真机实测 `res_query` 的 MX/A/AAAA 查询与报文解析均可用。
- **CMake policy（零补丁）**：上游 `cmake_minimum_required(VERSION 2.8)` 被 CMake ≥4.0 拒绝（<3.5 兼容移除）；配方注入 `CMAKE_POLICY_VERSION_MINIMUM=3.5`，与上游 v1.1.5 的官方修法（PR #13）一致，源码保持原样。
- **OHOS 链接行为**：`CMAKE_SYSTEM_NAME=OHOS` 使上游 `IF (... STREQUAL "Linux")` 的 resolv 链接分支不生效；`res_query` 由 libc.so 导出，无需 `-lresolv`；`-lpthread` 解析到 NDK 的 `libpthread.a`。
- 本地 CI 门禁（与平台 CI 同源脚本）结果：L0 / L1 / L1a / L1b / L1e（破坏性负测试）/ L2 / L4 / L5 PASS，15/15 断言；日志见 `reports/w3-local-ci.log`。
- W4 独立审计：verdict=pass，P0=0 / P1=0 / P2=0（1 项 P3 为工具侧 conan-verify G4 解析限制，产物校验由 W3 L2/L4/L5 覆盖），详见 `reports/audit-result.json`。
- 知识沉淀：新增草稿 `knowledge/drafts/E584-draft-9C4A.{kv,md}`（OHOS 无 glibc 重入解析器 API 的移植范式，与 E516 同族）。
- 已知限制：真实邮件投递需要外部 SMTP 服务器（E2E 使用协议兼容的 mock 服务器覆盖全事务）；`-P` 多进程吞吐压测不在正确性验证范围。
