## PR 信息

- **三方库名称**：libpagemaker
- **上游版本**：0.0.4
- **上游仓库地址**：https://wiki.documentfoundation.org/DLP/Libraries/libpagemaker
- **适配路径**：路径 A（基础适配） + 路径 B（贡献创新）
- **使用知识库**：E545-draft-PM11；参考E344, E572, DRAFT-E564-oldstyle-config-guess-ohos-reanchor, DRAFT-autotools-config-sub-silent-ohos-triplet

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 0 | 指定发布包无注册TESTS/check_PROGRAMS；保留make check且RC0。上游通过率0/0（不适用），不是100%。 |
| 集成测试 | 0 | 发布包无独立注册集成用例；不计LibreOffice应用级集成套件 |
| 其他测试 | 0 | 无其他注册程序，未删注册测试 |
| **合计** | **0** | 精确发布源码注册清单与原始日志绑定；无跳过 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|---------------:|------------|------|
| 单元测试 | 0 | 不变 | 未修改上游断言 |
| 集成测试 | 0 | 不变 | 消费者功能与平台检查合为一个程序 |
| 鸿蒙特有测试 | 1 | +1 | 独立1/1消费者程序，14个断言，不将断言冒充多个程序；实际文档识别、解析并导出1页SVG，以及HarmonyOS uname身份、TMPDIR写入/pread/unlink生命周期。 |
| **合计** | **1** | **+1** | 上游用例与独立新增程序分开；断言数不重复累计 |

---

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

未修改上游测试断言、数据或注册；仅平台识别与配方构建/链接适配。

---

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

独立1/1消费者程序，14个断言，不将断言冒充多个程序；实际文档识别、解析并导出1页SVG，以及HarmonyOS uname身份、TMPDIR写入/pread/unlink生命周期。 新增test_package内conanfile.py、CMakeLists.txt、测试C++与MANIFEST.yml。未修改的 LibreOffice writerperfect 回归素材 shapes.pmd，96256字节，Git blob 40e7df8b2f745986ea87653cb276487c36f92f95，SHA-256 70e683a3c10c0d8a90bdb44fa534f531a72427ae9f77ad06c552cc8b2fbe68c8；来源及项目许可说明见test_package/FIXTURE-NOTICE.md。 无发布库注册测试不等于全球不存在外部应用集成套件；LibreOffice writerperfect_draw依赖UNO/VCL完整应用服务，并非本库make check入口；未运行，不申报其全部通过。

---

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：0/0（不适用）
- 新增测试用例通过率：1/1（100%）

正式libpagemaker-finish-20261011-r1原生conan-verify及finish W3 PASS，事务已释放。原W3 SHA-256 3bba791cb0a75115f46bda63971df3c259d7689119bae886edd45d5763c07ddb，官方ci-result integrity dbabc432e493a7b0，保持生成器原始字节。整个finish RC1仅step5b/step8后置readiness/staging，不宣称全流程PASS；比赛worker CI尚未触发。指定发布包无注册TESTS/check_PROGRAMS；保留make check且RC0。上游通过率0/0（不适用），不是100%。

---

## 补充说明

- 关联 Issue：#3917
- 队伍名称：诶，云朵
- 申请人显示标识：2501_91199785
- 源分支：OpenHarmonyPCDeveloper:feat/libpagemaker-0.0.4
- 目标分支：OpenHarmonyPCDeveloper/build_in_harmonyos:main
- 其他说明：旧式 config.sub 的额外 OHOS rewrite 保护应按 shell case 首匹配可达性选择；较早白名单以 ;; 截住时后续 Linux 改写不可达。新增 E344 三 hunk 建议的控制流适用边界，不重复双锚点修复。 任务#15054依赖活动5火种；路径B候选以审核为准，HD1–HD4否定。合并后/release。素材源文件与原始失败日志不修改；源码补丁由官方流水线生成并干净源码dry-run。


### 2026-10-13 当前 CI 修复

A large mostly sparse binary sample can be transported as compressed text while preserving its original bytes. Bound decompression to expected_size+1 and require end-of-stream, no unused/trailing input, exact size and SHA256 before writing the consumer fixture.

当前真机事务 `libpagemaker-ci-repair-w3-20261013-r1`：12阶段和释放 PASS，官方本地CI子步骤 exit0；原始CI日志 SHA256 `d2cfda0b1ee12575dd553744b1446523666da45827f4d46744e2d13bb4a87b61`。上游 0 项和消费者 1 程序的声明与断言未减少。配套草稿补充上述可复用边界。完整finish旧归档/格式/就绪标记失败保留，不宣称整个finish RC0；比赛worker CI、最新AI检视、审核和发布仍需针对修复提交确认。


### 2026-10-14 当前 CI 修复

Autoconf creates config.status scratch directories in two branches with owner-only masks. On HMDFS, changing file modes later or repairing PR transport cannot establish creation-time access. Replace both creation branches with exclusive mkdir under the recipe-private TMPDIR, use umask 022 at creation, restore configure timestamps, and prefix TMPDIR after Conan environment activation. Preserve cleanup and every original test.

当前真机事务 `libpagemaker-ci-repair-w3-20261013-r101`：12阶段和释放 PASS，官方本地CI子步骤 exit0；原始CI日志 SHA256 `1169a21695c87b42adb547dbb16a60903bc712dc9465eb75cf91b429533081d8`。上游 0 项和消费者 1 程序的声明与断言未减少。配套草稿补充上述可复用边界。完整finish旧归档/格式/就绪标记失败保留，不宣称整个finish RC0；比赛worker CI、最新AI检视、审核和发布仍需针对修复提交确认。
