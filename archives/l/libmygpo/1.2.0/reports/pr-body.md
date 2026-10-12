## PR 信息

- **三方库名称**：libmygpo
- **上游版本**：1.2.0
- **上游仓库地址**：https://github.com/gpodder/libmygpo-qt；权威源码镜像为 Debian 官方 libmygpo-qt_1.2.0.orig.tar.gz
- **适配路径**：路径 A（基础适配）+ 路径 B（贡献创新）
- **使用知识库**：E8288-draft-2501；对比 DRAFT-kde-pim-testdata-iso-codes-tzdata

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 37 | UrlBuilderTest 32 + JsonCreatorTest 5，源头 tests/*.h 的 QtTest slots |
| 集成测试 | 0 | 官方归档无其他注册集成入口 |
| 其他测试 | 0 | initTestCase/cleanupTestCase 为生命周期，不计逻辑用例 |
| **合计** | **37** | 逐项 -functions 盘点，全部命名方法实际执行 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|---------------:|------------|------|
| 单元测试 | 37 | 不变 | 保留全部 slots/断言，仅声明 UTC fixture 与对应 JSON 精确格式 |
| 集成测试 | 6 | +6 | 链接安装库，检查 version/user-agent/base-URL/podcast 文本/计数/URLs |
| 鸿蒙特有测试 | 0 | 不变 | 原生构建/签名和真实 Qt 依赖是验证步骤，不虚增测试分母 |
| **合计** | **43** | **+6** | 上游 37/37、消费者 6/6 |

---

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [ ] **否**，未修改上游任何测试用例
- [x] **是**，存在对上游测试用例的修改（请在下方逐条说明）

tests/JsonCreatorTest.cpp：3 个无时区日期解析改为显式 UTC fixture；EpisodeActions 保留 UTC ISODate 的 Z 后缀，Settings 的 QVariant→QJsonDocument 日期期望保留 .000Z 毫秒格式。仍完整比较时间值、JSON 字符串和全部 5 项方法，不修改生产日期序列化规则，不删除或跳过测试，不修改设备 TZ。另 32 项 UrlBuilderTest 不变。

---

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

另在 test_package/test.cpp 新增 6 项实质安装消费者，经原生 Mygpo-qt5 config 链接真实安装库与 Qt5 Core/Network，调用公开 API。不把消费者作为原上游用例。

---

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：37/37（100%）
- 新增测试用例通过率：6/6（100%）

HarmonyOS PC 6.0 arm64 / Clang 15.0.4 / 已发布 Qt 5.15.19。完整原生 Conan 与官方 finish W3 子步骤实际执行；独立事务 libmygpo-full-finish-20261011T101500Z。原始 QtTest 命名结果、安装消费者和完整阶段回执绑定同一事务，安装消费者不依赖在线 gpodder 服务。

完整 finish 的旧知识/归档元数据限制单独保留，不能将整体非零收尾写成全部 PASS；不修改框架，不人工补造 .ci-result.json。比赛 worker CI 和平台 AI Review 尚无通过结论。

当前日志 SHA256 b2f2d5e64a5357546d22d8513ad657ec7f39c7dfd804d41f86492495f8665620，官方安装库 SHA256 8284694c09c22843ebffb243a4dfcd3ac94277b62bbf50b24412bfd2b95a6f3a；完整事务及 release/postrelease PASS。完整 finish 整体 RC1 / PARTIAL_POST_W3，仅 step5b/step8 失败，ConanVerifier L2/L4/L5 的 SKIP 保留原义。

---

## 补充说明

- 关联 Issue：#3910
- 队伍名称：诶，云朵
- 申请人显示标识：2501_91199785
- 源分支：OpenHarmonyPCDeveloper:feat/libmygpo-1.2.0
- 目标分支：OpenHarmonyPCDeveloper/build_in_harmonyos:main
- 基础库 #8288，路径 A+B；HD1–HD4 否，不申报路径 C。
- Qt 5.15.19 来自已发布原生制品，真实 moc 参与完整构建；不重建依赖，不上传制品。
- 配方保留全部生产对象、上游测试和真实 Network 依赖，原生可重定位 CMake config 不写入缓存绝对路径。
- 新知识从真实失败和全量恢复提炼 UTC fixture 与不同 JSON API 格式契约；四区查重、完整性与两阶段合同分别验证。
