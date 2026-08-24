## PR 信息

- **三方库名称**：librasterlite2
- **上游版本**：1.1.0-beta1（官方预发布 beta1，不是稳定版）
- **上游仓库地址**：https://www.gaia-gis.it/gaia-sins/librasterlite2-sources/librasterlite2-1.1.0-beta1.tar.gz
- **适配路径**：路径 A（基础适配） + 路径 B（贡献创新）
- **使用知识库**：复用 E298、E319、E320；本 PR 提交 E2157、E2158、E2159 配对草稿

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 71 | 来源：`test/Makefile.am` 注册的 71 个 Automake 测试入口 |
| 集成测试 | 0 | 上游没有单独登记的集成测试入口 |
| 其他测试 | 0 | 上游没有单独登记的其他测试入口；1,379 个 SQL `.testcase` 是上述入口消费的数据场景，不重复计入独立测试分母 |
| **合计** | **71** | 完整执行 `make -j1 check`，71/71 PASS |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|---------------:|------------|------|
| 单元测试 | 71 | 不变 | 上游测试源码、清单和期望均未修改 |
| 集成测试 | 1 | +1 | 一个 Conan `test_package` 消费者流程，内部 14/14 断言 |
| 鸿蒙特有测试 | 0 | 不变 | 没有引入 OHOS 专属 API、宏或平台测试入口 |
| **合计** | **72** | **+1** | 71 个上游入口加 1 个独立消费者流程 |

---

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

> 未修改上游测试源码、清单、输入或期望；适配通过能力探测、工具链和可移植源码修复完成。

---

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

> 上游已有 71 个 Automake 测试入口；新增的 `test_package` 是包级消费者验证，不替代上游测试。

---

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：71/71（100%）
- 新增测试用例通过率：1/1（100%）
- 真机验证：OpenHarmony PC arm64 r196，`launch_count=1`，runner RC 0，cleanup PASS，ownership closed；未重跑。
- 消费者覆盖：一个 `test_package` 流程通过，内部 14/14 断言覆盖版本、CPU、编解码器、像素/调色板、raster 与 section 所有权 API。
- W0：24/24 活动 provider 具有 RREV/PID/PREV 且来自 `ohpcd`，一个合法 OpenSSL Skip，依赖策略为 `--build=never`。
- W4：R218 双路独立完整审计 canonical `PASS / NOT_STALE`，SHA-256 `37e7760e4d02de7d39943e9423cc7879c1ac9a1512e1c7963180111176ce2d93`，P0/P1/P2/P3=`0/0/3/0`；P2 均为非运行元数据与证据边界说明，不阻塞。
- E2159 验证边界：r196 同时包含 producer `runenv_info` 源码修复与 consumer 侧依赖 libdir 重建，因此证明组合运行闭包，不宣称 producer 单变量验证。
- 源码边界：五个补丁均无 OHOS/HarmonyOS 条件编译宏；未修改上游测试用例。

---

## 补充说明

- 关联 Issue：#2337
- 队伍名称：天天开心
- 申请人显示标识：2301_80739235
- 源分支：2301_80739235:feat/librasterlite2-1.1.0-beta1
- 目标分支：OpenHarmonyPCDeveloper/build_in_harmonyos:main
- 本库是 spatialite-gui（要求 RasterLite2 `>=1.1.0`）的真实前置依赖；当前上游输入是 `1.1.0-beta1` 预发布版。
- current-main 四范围查重结论为 `NO_EQUIVALENT_REUSABLE_KNOWLEDGE`。E2157/E2158/E2159 草稿分别覆盖严格 PowerShell 空字符串负例、plain-char signedness 和 Conan shared-package transitive runtime libdirs，并随本软件 PR 提交；复用 E298、E319 与 E320 的既有边界。
- 合并前不执行 `/release`，不从本机上传 Conan/CNB；仅允许合并后平台 release 到 `ohpcd`。
