## PR 信息

- **三方库名称**：fontconfig
- **上游版本**：2.18.3（适配版本 2.18.3.3）
- **上游仓库地址**：https://gitlab.freedesktop.org/fontconfig/fontconfig
- **适配路径**：路径 A（基础适配） / 路径 B（贡献创新） / 路径 C（高难度挑战候选）
- **使用知识库**：E14723-draft-2301、E14915-draft-2301；参考 E471 的字体配置测试边界，新增生产者配置交付、应用缓存、目录视图与生命周期机制。

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 15 | 来源：Meson 注册的独立 C 测试程序 |
| 集成测试 | 485 | 来源：上游 test Python pytest 清单；含五项字体缓存目录视图测试 |
| 其他测试 | 0 | 无额外独立上游入口；一项 pytest 注册入口展开为 485 个真实用例 |
| **合计** | **500** | 15 C + 485 pytest，原始源码清单与当前正式 r26 JUnit 统计 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|---------------:|------------|------|
| 单元测试 | 15 | 不变 | 原生 C 用例全部通过，配置生命周期使用语义哨兵断言 |
| 集成测试 | 485 | 不变 | 保留原始字体/缓存/警告断言，五项使用显式目录视图后端，零跳过 |
| 鸿蒙特有测试 | 1 | 新增 | projected_config.py：投影归属存储的 UTF-8 XML/配置副本与实际签名字体 API 消费者 |
| **合计** | **501** | **+1** | 上游 500/500，独立鸿蒙特有测试 1/1；消费者另计 7/7 |

---

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [ ] **否**，未修改上游任何测试用例
- [x] **是**，存在对上游测试用例的修改（请在下方逐条说明）

> 若选择“是”，逐条填写修改文件、修改原因和修改内容。

1. `test/test-bz106632.c`：使用受界定的 TMPDIR 模板，初始化失败返回非零，避免目标只读临时目录及假通过。
2. `test/test-issue107.c`：有界 TMPDIR 路径；缺失/超长路径有真实失败负测。
3. `test/test-mt-fccfg.c`：释放后地址可复用，改为非默认配置哨兵检测清理；故意保留旧状态的负测必须失败。
4. `test/test_sandbox.py`：仅显式 FC_TEST_DIRECTORY_VIEW=1 时启用适配后的目录视图用例；默认 Linux bubblewrap 行为保留。
5. `test/fctest/__init__.py`：只在真实子进程执行期间切换任务私有目录，先检查归属/链接并在返回前恢复父视图，保留原先不可见占位目录及 remap-dir 语义。缓存数量、键、元数据、字体匹配和警告断言未删除；该适配不证明内核安全隔离。

五个补丁均由官方 refresh-patch --auto 生成，patch-ng 重放及精确源字节等价 5/5。修复前 r9/r10 的真实失败与后续负测保留。

---

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

> 若选择“是”，填写补全范围、补全原因和新增测试文件清单。

实际 fontconfig API 消费者 `test_package/test.c` 注册5项：完整XML加载、字体枚举、匹配文件可打开、缺失/坏配置拒绝；正式r26中5/5。独立consumer-r27使用r26实际包与相同消费者二进制执行完整七项合同，包括移动配置后匹配和应用私有缓存写入，共7/7。独立专属测试 `test_package/harmony_tests/projected_config.py` 在r26为1/1。两个事务各自完整，不把5项与另一事务局部结果相加为7项；不把消费者或重复执行计入上游500项分母。

---

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：500/500（100%）
- 新增测试用例通过率：8/8（100%）

编译状态指正式依赖闭包下 `fontconfig-2.18.3.3-finish-r26` 的两次真实原生Conan create和官方finish aggregate RC0，所有步骤均成功；不代表平台CI或发布通过。Fontconfig RREV=b730108b4ec2c35df0e0e57484a0e23b，PID=eb8a1377e7d30f9f68371d8f4bd2af8e42522628，PREV=9f3f7bb739778fbe21b3ec6fbce12a8f。

本次实际修复：移除Meson test的--no-rebuild以构建原test-only字体夹具；按实际编译器解析OHOS绝对ar/ranlib并保留显式配置与缺工具失败；安装后对实际ELF工具及共享库重新签名并设置执行模式，非ELF不签、包外路径拒绝。目标CLI必须另行激活真实VirtualRunEnv；冷环境十个CLI均RC127、实际生成的运行环境激活后10/10 RC0，完整stderr控制保留，不把存在.codesign等同于可运行。

2026-10-10 fresh isolated官方依赖 download --only-recipe、graph info/install --build=never均PASS，全图info_invalid为空、Missing=0、实际binary retrieval成功：expat/2.8.5 RREV=91ce755eda4598aa3fe3d74f1fecc4f3，PID=01d92cf349a0dd98ff915f4bd99a04430171517f，PREV=9863572526a6c76f8bffed4e4a2aed48；freetype/2.14.3 control RREV=7e95a2b2401fd12dcbdd2bf748f56b19，同PID，PREV=333a87c0272a09afc1e8cbadd8de3ac6。旧Expat缺失记录只保留为历史。

当前r26每次create各自15C+485pytest=500/500、零失败/错误/跳过，不累计分母；官方消费者5/5、专属1/1、CLI10/10。r26冻结产品candidate tree=5ee65bf3cf3ac1744ad445aa9dc318e374ffe79d；后续只更新事实文档、清单和知识，不修改已验证的产品/配方/补丁/消费者执行输入。两次JUnit SHA256为47c6016edb02ef1d6c0c02bea7054fe1d70fa89328c172edd071932a5b65e6c4、796695a48a9666d8d8d9c7bb6b04636e0345076026e9ea66d6bfb3cdbd53855b。官方生成.ci-result.json SHA256=b70861676a69caf67cd1a2a7214a88d4bc493a9d1f95ced73fb1029c405d478e，未手工创建或修改；12条回执及两次自有进程清零/原控制器单次release PASS，末回执efa49046d657414535c4bf5140bdb5fa6e03b00b5c84d2ea6cfd584546379ec1。

完整七项消费者由独立consumer-r27以r26实际package字节验证7/7；该事务不执行上游或专属测试，不能替代r26结果。其12条回执及两次自有进程清零/单次release PASS，末回执f845d07b8f9a0115392e39f963eef383d8bda33ad4888706052c43d7e84563a9。

完整证据保留于 F:/HarmonyPC/spatialite-provider-audit-20261006/finish-native-20261011-r12 和 consumer-native-20261011-r27。历史r19-r25真实FAIL/未launch保留，不升级为PASS。当前修改后的HEAD仍须平台最新AI Review、精确完整Buildbot成功和提审回读；旧HEAD的CI/Review不能迁移。

> 三条固定结果之后可追加命令、日志哈希、消费者测试、CI 和限制等证据。
>
> 鸿蒙特有测试是独立硬门禁：至少 1 项，必须在 HarmonyOS PC 目标环境真实执行并达到 N/N（100%）。仅因为测试在鸿蒙 CI 上运行，不能把普通消费者测试计为鸿蒙特有测试。

---

## 补充说明

- 关联 Issue：#3824
- 队伍名称：天天开心
- 申请人显示标识：2301_80739235
- 源分支：2301_80739235:feat/fontconfig-2.18.3.3
- 目标分支：OpenHarmonyPCDeveloper/build_in_harmonyos:main
- 其他说明：为 GUI 字体消费者交付可重定位 XML、启用模板与应用私有缓存；HD1 私有 Linux 命名空间测试布置的目标语义适配已真实验证，候选高难以委员会为准。E14723/E14915 是跨库机制增量，不把字体库介绍或测试数量作为创新。参考知识 E471 不覆盖生产者交付三契约与目录视图/生命周期负测。全局知识图谱 E013/E019/E037/E465 的既有 schema 错误未改动，本次不宣称全局图谱 validate PASS。没有制品仓 upload，不接管其他人的 PR，不提前提审。
