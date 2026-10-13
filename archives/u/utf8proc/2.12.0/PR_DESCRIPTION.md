# 【积分赛】chore(utf8proc): upgrade to 2.12.0

## PR 信息

- **三方库名称**：utf8proc
- **上游版本**：2.12.0（官方正式 Release `v2.12.0`）
- **上游仓库地址**：https://github.com/JuliaStrings/utf8proc
- **适配路径**：路径 A，已有配方的版本升级
- **使用知识库**：`harmonyos-pc-utf8proc-ctest-default-off.md`（本次问题闭环）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
| --- | ---: | --- |
| 单元测试 | 10 | `CMakeLists.txt` 在非 Windows 平台注册的 CTest：case、custom、iterate、misc、printproperty、valid、maxdecomposition、charwidth、graphemetest、normtest；后两项使用 Unicode 18 官方数据。 |
| 集成测试 | 0 | 上游未另列。 |
| 其他测试 | 0 | `fuzzer` 是构建目标，不计入 CTest 通过数。 |
| **合计** | **10** | **目标 OHOS 平台真实注册并运行十项。** |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
| --- | ---: | --- | --- |
| 单元测试 | 10 | 不变 | 真机原生 Conan 构建中 CTest 10/10。 |
| 集成测试 | 0 | 不变 | 未另计。 |
| 鸿蒙特有测试 | 1 | +1 | `test_package/test.c` 从已安装包调用版本、NFC、iterate、grapheme break、property API，一个消费者程序含 11 个 CHECK。 |
| **合计** | **11** | **+1** | 消费者程序只计一个测试用例，不把 11 个断言误计成 11 个测试。 |

## 上游测试用例修改说明

- [x] **否**，没有修改上游测试源文件。
- [ ] **是**，存在上游测试文件修改。

## 补全测试用例说明

- [x] **否**，上游已有十个 CTest 用例。
- [ ] **是**，上游原本没有测试。

新增的已安装包消费者程序验证 Conan 包的对外 API 与链接行为，不替代上游测试。

## 验证结果

- **编译状态**：通过。授权 OHOS PC 的两个全新私有根中，static/shared 原生 `conan create` 均 RC0；Windows SDK 直接交叉构建 static/shared RC0，交叉模式没有执行目标 ELF。
- **上游测试用例通过率**：10/10（100%）；两次原生 Conan 构建均先确认 CTest 注册十项，再实际运行。
- **新增测试用例通过率**：1/1（100%）；已安装包消费者程序 11/11 CHECK，通过 static/shared 两种包的原生运行。
- **原始证据**：static 构建日志 SHA-256 `82e54369453d17c0c4537815392bfcdfc2d5c1313517887c850d1b7c7ef48d6b`，shared `4b2c17c8a25c1a36987726abf6ce806b373d5d17daf90c6842958095e107d7fb`；逐文件上传与独立完整回读记录留在本地 D 盘任务目录。

## 补充说明

- 上游 `UTF8PROC_ENABLE_TESTING` 默认关闭；旧版配方只运行 `ctest`，无法证明十项测试曾被注册。本版原生构建显式开启测试，并在执行前拒绝空测试列表。
- `LICENSE.md` 原样打入包内，同时保留 MIT 和 Unicode 数据许可声明。
- 上述是真机私有验证，**不是正式 W3 回执、平台 CI、维护者批准或比赛积分**；这些状态需在 PR 与平台流程中另行确认。
