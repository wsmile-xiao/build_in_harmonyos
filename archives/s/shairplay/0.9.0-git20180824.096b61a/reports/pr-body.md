## PR 信息

- **三方库名称**：shairplay
- **上游版本**：0.9.0-git20180824.096b61a
- **上游仓库地址**：https://github.com/juhovh/shairplay
- **适配路径**：路径 A（基础适配）+ 路径 B（知识库扩展）；本 PR 按 B 类申请
- **使用知识库**：参考 E160 / DRAFT-E656 处理鸿蒙平台识别与 Autotools 时间戳；新增 `DRAFT-shairplay-dlopen-dnssd-header-gate` 说明 DNS-SD 可选运行时的头文件检测边界

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 0 | 上游 `Makefile.am` 未注册 `TESTS` 或 `check_PROGRAMS`。 |
| 集成测试 | 0 | `src/test/` 有手动示例，但不在 `SUBDIRS`，需要 DNS-SD 服务或 libao，非 `make check` 自动用例。 |
| 其他测试 | 0 | `make check -j1` 已执行并返回 0，但没有注册测试项。 |
| **合计** | **0** | 完整审计见 `reports/upstream-test-inventory.txt`；0/0 不适用。 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|---------------:|------------|------|
| 单元测试 | 0 | 不变 | 未修改上游测试入口。 |
| 集成测试 | 0 | 不变 | 未修改上游测试入口。 |
| 鸿蒙特有测试 | 1 | +1 | 安装后消费者链接 `libshairplay`，调用 `dnssd_init` 并验证成功或明确的可选运行时缺失错误。 |
| **合计** | **1** | **+1** | 新增消费者 1/1 PASS。 |

---

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改

只修正 `configure.ac` 的 DNS-SD 头文件判断，并提供与固定源码匹配的预生成 Autotools 文件。引导归档以文本编码提交，配方解码后校验 SHA-256，避免 GitCode PR diff 丢失二进制补丁；没有删减或屏蔽测试。`make check` 照常运行。

---

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无自动注册测试用例，适配后补全了测试

新增 `test_package/test.c`、`CMakeLists.txt` 与 Conan 测试入口。消费者针对**安装后包**编译链接，并实际调用公开 DNS-SD API；缺少可选 DNS-SD 运行库时只接受明确的 `LIBNOTFOUND`/`PROCNOTFOUND` 状态，不将其伪装成服务启动成功。

---

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：0/0（不适用）
- 新增测试用例通过率：1/1（100%）

HarmonyOS PC aarch64 / OHOS 6.0，Conan 2.29.1；初始配方及补丁对应的冻结事务 `shairplay-w3-20260929T121145Z` 有 12 个完整回执，结果 `W3_PASS`，原始日志 SHA-256 `39b466743707fb77e8d768a9220e5692446c5f6a93914ab41abe832070382dbd`。文本引导归档修复后又完成独立真机 `conan create`、`make check` 和包消费测试，日志 SHA-256 `cfee4d8c32c0fe66909129e134a3ae05765c38287d5593ba8c4b987979de82b3`。产物包含共享库、两份公共头文件和许可。详细证据见 `reports/test-report.md`；平台 CI 与 AI Review 以当前 PR 最新结果为准，不预称通过。

---

## 补充说明

- 关联 Issue：#3605
- 队伍名称：诶，云朵
- 申请人显示标识：2501_91199785
- 源分支：2501_91199785:feat/shairplay-0.9.0-git20180824.096b61a
- 目标分支：OpenHarmonyPCDeveloper/build_in_harmonyos:main
- 其他说明：知识查重结论为 `NO_EQUIVALENT_REUSABLE_KNOWLEDGE`，新草稿仅涵盖 `dlopen` 分支与 DNS-SD 头文件检查错位，不重复申请已有的 HarmonyOS `config.guess`/Autotools 时间戳知识。`libao` 驱动的服务器可执行文件未纳入该库包；合并后才进行 `/release` 制品发布。
