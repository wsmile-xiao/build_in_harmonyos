## PR 信息

- **三方库名称**：libwpg
- **上游版本**：0.3.4
- **上游仓库地址**：https://wiki.documentfoundation.org/DLP/Libraries/libwpg
- **适配路径**：路径 A（基础适配） + 路径 B（贡献创新）
- **使用知识库**：E545-draft-WG11；参考E072, E122, E268

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

独立1/1消费者程序，14个断言，不将断言冒充多个程序；实际文档识别、解析并导出1页SVG，以及HarmonyOS uname身份、TMPDIR写入/pread/unlink生命周期。 新增test_package内conanfile.py、CMakeLists.txt、测试C++与MANIFEST.yml。未修改的 LibreOffice writerperfect 回归素材 WPG1.wpg，79字节，Git blob 273089649c5a2bda843e4331ba5339cfee7fa447，SHA-256 10dbb1c7b6c81e87c69a971bc39ec5a7773e128812d2fc71d7b620d51d885dc3；来源及项目许可说明见test_package/FIXTURE-NOTICE.md。 无发布库注册测试不等于全球不存在外部应用集成套件；LibreOffice writerperfect_draw依赖UNO/VCL完整应用服务，并非本库make check入口；未运行，不申报其全部通过。

---

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：0/0（不适用）
- 新增测试用例通过率：1/1（100%）

正式libwpg-finish-20261011-r1原生conan-verify及finish W3 PASS，事务已释放。原W3 SHA-256 27cd0fe0d75da36f243203b87f60561d47fdce8541de267a8ec8bdc8de6d7686，官方ci-result integrity e45009925b46235a，保持生成器原始字节。整个finish RC1仅step5b/step8后置readiness/staging，不宣称全流程PASS；比赛worker CI尚未触发。指定发布包无注册TESTS/check_PROGRAMS；保留make check且RC0。上游通过率0/0（不适用），不是100%。

---

## 补充说明

- 关联 Issue：#3916
- 队伍名称：诶，云朵
- 申请人显示标识：2501_91199785
- 源分支：OpenHarmonyPCDeveloper:feat/libwpg-0.3.4
- 目标分支：OpenHarmonyPCDeveloper/build_in_harmonyos:main
- 其他说明：config.sub 组合表必须按 case 表达式的实际字段数选择 OHOS 模式尾缀；两字段 linux-ohos* 与三字段 linux-ohos*- 不能机械互换。新增边界反例，不重复已有 OHOS 白名单方案。 任务#15052依赖活动5火种；路径B候选以审核为准，HD1–HD4否定。合并后/release。素材源文件与原始失败日志不修改；源码补丁由官方流水线生成并干净源码dry-run。


### 2026-10-13 当前 CI 修复

Even a tiny valid binary parser fixture can be lost by a text-only PR diff. Text encoding does not permit replacing it with an empty or header-only sample: validate the complete decoded size/hash before the original positive parser test reads it.

当前真机事务 `libwpg-ci-repair-w3-20261013-r1`：12阶段和释放 PASS，官方本地CI子步骤 exit0；原始CI日志 SHA256 `dc8e1403b14e5241d94a7c523bb6d29f4c1bf93352f35357e350a7445dc1c42a`。上游 0 项和消费者 1 程序的声明与断言未减少。配套草稿补充上述可复用边界。完整finish旧归档/格式/就绪标记失败保留，不宣称整个finish RC0；比赛worker CI、最新AI检视、审核和发布仍需针对修复提交确认。


### 2026-10-13 当前 CI 修复

Autoconf creates config.status scratch directories in two branches with owner-only masks. On HMDFS, changing file modes later or repairing PR transport cannot establish creation-time access. Replace both creation branches with exclusive mkdir under the recipe-private TMPDIR, use umask 022 at creation, restore configure timestamps, and prefix TMPDIR after Conan environment activation. Preserve cleanup and every original test.

当前真机事务 `libwpg-ci-repair-w3-20261013-r101`：12阶段和释放 PASS，官方本地CI子步骤 exit0；原始CI日志 SHA256 `3feea958cb63877cd9f3feb927de09d3bb6f40511f156662593897ce00ab2fcd`。上游 0 项和消费者 1 程序的声明与断言未减少。配套草稿补充上述可复用边界。完整finish旧归档/格式/就绪标记失败保留，不宣称整个finish RC0；比赛worker CI、最新AI检视、审核和发布仍需针对修复提交确认。
