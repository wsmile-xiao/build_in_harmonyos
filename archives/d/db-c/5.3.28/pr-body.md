## PR 信息

- **三方库名称**：db-c
- **上游版本**：5.3.28
- **上游仓库地址**：https://download.oracle.com/berkeley-db/db-5.3.28.tar.gz
- **适配路径**：路径 A（基础适配） / 路径 B（贡献创新）
- **使用知识库**：E1001 C API handle lifecycle；E1002 Windows-hosted OHOS tool identity

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 0 | C-only Conan 闭包通过 --disable-test 关闭官方可选 harness，未将上游测试组件打包 |
| 集成测试 | 0 | C-only 配方不构建 Tcl/C++/Java/SQL 及其集成测试入口 |
| 其他测试 | 0 | 上游 harness 属于包外组件，候选包没有可执行的上游测试入口 |
| **合计** | **0** | 清单审计见 F:/HarmonyPC/db-c-5.3.28-20260912/evidence/upstream-inventory-r005.txt |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|---------------:|------------|------|
| 单元测试 | 0 | 不变 | 未新增单元测试框架 |
| 集成测试 | 1 | 新增 | CMake/Conan consumer 覆盖 db_create、open、put、get、close |
| 鸿蒙特有测试 | 1 | 新增 | HarmonyOS PC AArch64 native self-sign target probe |
| **合计** | **2** | +2 | 清单与运行证据绑定到 W3 r005 |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

补全范围为 1 个 C API consumer 和 1 个 HarmonyOS PC target probe。原因是官方可选 harness 不属于 C-only 包闭包，但目标平台仍需有真实 API 与运行时验证。新增文件为 archives/d/db-c/5.3.28/test_package/test_package.c 和 archives/d/db-c/5.3.28/test_package/harmony_tests/harmony_db_test.c。

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：0/0（不适用）
- 新增测试用例通过率：1/1（100%）

- HarmonyOS PC 特有测试：1/1（100%，device-150125，唯一 launch）
- 历史 W3 证据：F:/HarmonyPC/db-c-5.3.28-20260912/evidence/w3-r003-summary.json 曾通过，但绑定旧 recipe（HEAD 24baa722cfad61fc0a203b70cc977a0fac1a0cf1），仅保留为历史证据
- 当前 W3 证据：F:/HarmonyPC/db-c-5.3.28-20260912/evidence/w3-r005-summary.json，payload 绑定代码 HEAD ab21342182ce3c245a2e86650742e6cb345792d4；当前 HEAD 13323e531d453e442e4d4bcc48bad4e363a73826 仅增加本 PR 正文绑定文档，消费者 RC=0，HARMONY_TEST_PASS=1/1，DB_C_W3_TESTS=2/2 PASS，3 个 ELF self-sign，唯一 launch，postrelease PASS
- 本地 OHOS Conan 复验：F:/HarmonyPC/db-c-5.3.28-20260912/evidence/conan-create-ohos-r015-summary.json，RC=0；configure、library_build、package、AArch64 consumer 和 Harmony 专测目标构建均 PASS，跨编译主机执行按边界不适用
- 上游闭包审计：候选 recipe 明确关闭官方可选测试组件；一次独立 harness 观测曾在 `Test008.b` 处停止，未被计入通过率或用于替代包级证据
- Windows Conan、WSL Conan、OHOS AArch64 cross build 和消费者构建均有任务证据；平台 CI #47985 在当前 HEAD 上 PASS，最新平台 AI Review 为“✅ 未发现问题”

## 补充说明

- 关联 Issue：#2989
- 队伍名称：天天开心
- 申请人显示标识：2301_80739235
- 源分支：2301_80739235:feat/db-c-5.3.28
- 目标分支：OpenHarmonyPCDeveloper/build_in_harmonyos:main
- 其他说明：本候选的新增知识为 E1002，记录 Windows-hosted OHOS 下 Autoconf 与 CMake 必须分离绑定原生工具身份、相对 configure 路径和目标 linker 参数的通用边界，并补充目标 worker 共享 TMPDIR 不可写时将其绑定到 Conan build 目录。旧 CI #45709 为 worker 缺少 libz.so 的基础设施失败；CI #47677 曾定位到共享 TMPDIR 的配置阶段权限问题，修复后的本地 OHOS Conan r015 已 RC=0。W3 successor r005 的 payload 绑定代码 HEAD ab21342182ce3c245a2e86650742e6cb345792d4；当前 HEAD 13323e531d453e442e4d4bcc48bad4e363a73826 仅为文档绑定提交，平台 CI #47985 在该 HEAD PASS，最新 AI Review 为“✅ 未发现问题”，满足提审前技术门禁。
