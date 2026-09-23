【依赖项】feat(attica): 6.14.0 适配 HarmonyOS PC

## PR 信息

- **三方库名称**：attica
- **上游版本**：6.14.0
- **上游仓库地址**：https://invent.kde.org/frameworks/attica
- **基线 OID**：aaa82da1f5a292969dffeaab88c503f461c358ee（v6.14.0 tag，download.kde.org 官方 release tarball 与之对应）
- **许可证**：LGPL-2.1-only OR LGPL-3.0-only OR LicenseRef-KDE-Accepted-LGPL
- **SHA-256**：7c3556afeb0ae0e932c2e4d309df4905f3e2f41af3e3b38051b49d9f279357c1
- **适配路径**：路径 A（基础适配）
- **使用知识库**：E207（HarmonyOS CMake SONAME 缺失模式，DT_SONAME 注入方案来源）；新增草稿 E429（KDE ECM qtpaths 缺 OHOS libc++ 运行时）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 3 | 来源：autotests/CMakeLists.txt（CTest 注册：configtest / persontest / providertest，均为 Qt6Test 单测） |
| 集成测试 | 0 | 上游无独立集成测试目录 |
| 其他测试 | 0 | tests/projecttest 为 ecm_mark_as_test 标记的手工 Qt Widgets GUI（非 CTest 条目）；autotests/privatedatatest.cpp 为未注册死文件 |
| **合计** | **3** | |

### 适配后测试用例统计（设备端实测）

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 2 个 PASS | 实测运行上游测试 | configtest + persontest 设备端实测全部 PASS（2/2，100% tests passed, 0 tests failed out of 2） |
| 单元测试（未运行） | 1 个 | 需外网 OCS 排除 | providertest 依赖 live OCS 端点（autoconfig.kde.org / invalid-url.org），OHOS runner 上会挂起，按 6.18.0/6.28.0 同款策略 ctest `-E ^providertest$` 排除，写 N/A（未运行） |
| 鸿蒙特有测试 | 1 | 新增 | test_package/test.cpp：构造 Attica::Person / Attica::Config 值对象验证访问器往返（7 断言，R34 实质依赖，L1e 破坏性反向验证通过） |
| **合计** | **2 PASS + 1 未运行 + 1 新增** | | |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

> 未对任何上游测试文件做修改。上游 3 个 CTest 注册目标中 2 个（configtest / persontest）以 BUILD_TESTING=ON 在设备端实测全部 PASS（2/2）；providertest 因需 live 外部 OCS 网络端点（https://autoconfig.kde.org/ocs/providers.xml 与 https://invalid-url.org/ocs/providers.xml，后者依赖 DNS/网络失败行为）在 OHOS runner 上会挂起，与 6.18.0/6.28.0 先例一致以 ctest `-E "^providertest$"` 排除，未运行。projecttest 是 ecm_mark_as_test 标记的手工 Qt Widgets GUI 辅助程序，上游本身不注册为 CTest 条目（只构建不运行）。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

> 上游已有 CTest 测试覆盖（configtest / persontest / providertest），无需补全上游测试。新增 test_package/test.cpp 为满足 R28（conanfile.py 必须有 test_package/）与 R34（test 必须实质依赖被测包）要求的消费者测试，调用 Attica::Person / Attica::Config 真实 API 验证值对象访问器往返（Person: isValid/firstName/lastName/avatarUrl；Config: isValid/version/ssl），7 个断言。L1e 破坏性反向验证：移走 lib/ 后测试失败，证明真实依赖被测包。

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：2/2（100%）—— 本机 OHOS PC (aarch64) W3 conan create 实测（BUILD_TESTING=ON）：CTest 目标 configtest（0.10s）、persontest（0.08s）全部 PASS（100% tests passed, 0 tests failed out of 2），providertest 1 个未运行（N/A（未运行），需 live 外部 OCS 端点）
- 新增测试用例通过率：1/1（100%）—— 实测：CTest 目标 test_attica Passed（100% tests passed, 0 tests failed out of 1），程序输出 PASS: Attica value objects OK
- W3 本地 CI 模拟：JC pass / L0 pass / L1 pass / L4 pass / L5 pass（含 SONAME 质量门禁：DT_SONAME=libKF6Attica.so），.ci-result.json exit_code=0

## 补充说明

1. **平台任务指定版本**：本任务为平台任务卡 contrib-3595（积分赛-依赖）指定的 6.14.0 版本。制品仓已有 attica 6.18.0/6.28.0，6.14.0 为早于两者的历史版本首次适配（R37 首次适配用上游版本号原样）。底稿为 archives/a/attica/6.18.0（zxyAtom），6.28.0 归档仅作对比。
2. **无需补丁**：attica 6.14.0 顶层 CMakeLists 要求 `find_package(ECM 6.14.0 NO_MODULE)`，已发布的 ecm/6.26.0 满足最低版本语义（6.26.0 ≥ 6.14.0），无需 6.28.0 所需的 ECM 降级补丁。conandata.yml patches 为空。
3. **configure 阶段 qtpaths 运行时修复**（相对 6.18.0 底稿的新增适配）：KDEInstallDirs6/ECMQueryQt 在 configure 时执行 qtbase 的 qtpaths（OHOS 二进制，依赖 libc++_shared.so/libunwind.so，qtbase conan 包不含），本机/CI 环境直接构建会报 `Qt6 qtpaths call failed: 127`。修复为 conanfile build() 内用 Environment 包装 cmake.configure()，LD_LIBRARY_PATH 前置 OHOS SDK llvm lib 目录（_ohos_sdk_lib_dirs() glob 探测，R33 合规不裸用 shell env）。6.18.0 当年在远程 runner（环境自带 LD_LIBRARY_PATH）构建，未暴露此问题。已沉淀知识草稿 E429。
4. **DT_SONAME 注入**：HarmonyOS 不是 CMake versioned-SONAME 平台，默认构建的 libKF6Attica.so 无 DT_SONAME（CI L5 soname gate fail）。采用 attica5/5.116.0 平台验证过的模式注入 `CMAKE_PLATFORM_NO_VERSIONED_SONAME=TRUE` + `CMAKE_SHARED_LIBRARY_SONAME_C/CXX_FLAG="-Wl,-soname,"`，修复后 readelf 确认 DT_SONAME=libKF6Attica.so（对应知识条目 E207 模式）。
5. **已知限制**：KF_IGNORE_PLATFORM_CHECK=TRUE 为防御性设置（attica 6.14.0 实际未包含 KDEMetaInfoPlatformCheck）；reuse 工具缺失导致 ECMCheckOutboundLicense 的 SPDX license 测试不注册；Qt6Tools 缺失导致 API 文档生成跳过（BUILD_QCH 默认 OFF，均不影响构建与测试）。
6. **W4 Pre-PR 审计**：verdict=pass（P0=0 / P1=0），报告在 archives/a/attica/6.14.0/reports/audit-result.json。
