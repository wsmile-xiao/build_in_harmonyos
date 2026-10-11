## PR 信息

- **三方库名称**：libsigrokdecode
- **上游版本**：0.5.3
- **上游仓库地址**：git://sigrok.org/libsigrokdecode（官方发布包：https://sigrok.org/download/source/libsigrokdecode/libsigrokdecode-0.5.3.tar.gz）
- **适配路径**：路径 A（基础适配）+ 路径 B（贡献创新）
- **使用知识库**：既有 E007/E072/E122（Autotools 三元组）；本 PR 新增 `knowledge/drafts/E14840-draft-4E8A.kv` 与同 stem `.md`，沉淀 Conan 私有嵌入式 Python 运行闭包

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 39 | 官方 Check `make check`：`tests/core.c` 3、`tests/decoder.c` 24、`tests/inst.c` 4、`tests/session.c` 8 项 `START_TEST` 注册；清单见本任务 `upstream-test-inventory.txt`。 |
| 集成测试 | 0 | 上游发布包未注册独立集成测试。 |
| 其他测试 | 0 | 上游发布包未注册其他测试入口。 |
| **合计** | **39** | 官方发布包 SHA-256 `c50814aa6743cd8c4e88c84a0cdd8889d883c3be122289be90c63d7d67883fc0`；清单 39 项。 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|---------------:|------------|------|
| 单元测试 | 39 | 不变 | 完整保留并运行官方 `make check`，39/39 PASS。 |
| 集成测试 | 0 | 不变 | 未虚增集成测试。 |
| 鸿蒙特有测试 | 1 | +1 | `test_package/consumer.c` 使用安装后的共享库初始化嵌入式 Python 并加载 `i2c` 解码器，1/1 PASS。 |
| **合计** | **40** | **+1** | 39 项上游用例与 1 项新增消费端测试分别计数，不重复计分。 |

---

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

唯一源码补丁只扩展随发布包提供的 `autostuff/config.sub` 对 `linux-ohos` 的识别；测试源码、注册数及断言均保持原样。

---

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

此外新增一项安装包消费者验证，不替代上游 39 项测试；其源文件和 `MANIFEST.yml` 与配方一同提交。

---

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：39/39（100%）
- 新增测试用例通过率：1/1（100%）
- HarmonyOS PC arm64 真机事务 `libsigrokdecode-w3-20261003T150451Z`：完整 `conan create` 成功，12/12 回执验证为 `W3_PASS`，runner 已释放；原始构建日志 SHA-256 `0de24c3b80992b14497fc0f68010701a240b43c54e12f95be7cfd333a2a10cae`。
- 上游 Check 原始日志 SHA-256 `627a6417ac6c8b20a8fa94e8b07d9cd4217dbeb5640d3719d6ab5e66256d406a`，显示 `100%: Checks: 39, Failures: 0, Errors: 0`；消费端日志标记 `CONSUMER_1_OF_1_PASS`。
- 比赛 worker CI 尚未触发，创建 PR 后按实际构建号和当前 HEAD 跟踪。

---

## 补充说明

- 关联 Issue：#3724
- 队伍名称：诶，云朵
- 申请人显示标识：2501_91199785
- 源分支：OpenHarmonyPCDeveloper:feat/libsigrokdecode-0.5.3
- 目标分支：OpenHarmonyPCDeveloper/build_in_harmonyos:main
- 其他说明：任务 `contrib-14840`（本人已领取的依赖库候选）；源码与 SHA-256 固定，GLib、Python 和 Check 均使用已发布的 Conan 依赖。`HD1`–`HD4` 当前均未命中，按路径 B 申报。知识查重已覆盖 graph/drafts/doc/operations；E14840 的增量是私有 Python application 二进制保留、环境传播与实际消费运行的闭环。许可证按上游 README 对整库的声明设为 GPL-3.0-or-later。
