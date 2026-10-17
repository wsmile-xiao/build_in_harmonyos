## PR 信息

- **三方库名称**：wxWidgets
- **上游版本**：v3.3.3；适配修复版本 3.3.3.2
- **上游仓库地址**：https://github.com/wxWidgets/wxWidgets
- **适配路径**：路径 A（基础适配）+ 路径 B（贡献创新）+ 路径 C（高难度挑战）
- **使用知识库**：E336 USB HDC GUI 能力闭包配对草稿；GTK provider、client-area、fixture-root 和透明能力限制计数知识

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 897 | 当前实际构建配置的 Catch 清单：Base 429 + GUI 467 + Drawing 1；不是所有平台/可选功能的静态总数 |
| 集成测试 | 0 | 当前配置没有另列独立上游集成分母 |
| 其他测试 | 0 | 三套上游入口均纳入单元测试清单 |
| **合计** | **897** | USB r37 三份 --list-tests 原始清单和三份 XML |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|---------------:|------------|------|
| 单元测试 | 897 | 不变 | 完整执行且零失败；33 个 Base 测试项含明确原因的受限分支，40 个标记事件；GUI/Drawing 无能力标记 |
| 集成测试 | 0 | 不变 | 没有额外上游集成分母 |
| 鸿蒙特有测试 | 1 | 新增 | 签名 HAP Native 子进程身份/应用沙箱与结果逐字节闭包，USB r37 1/1 |
| **合计** | **898** | **+1** | 消费者 1/1、GUI 状态 3/3 单列，不重复增加上游分母 |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [ ] **否**，未修改上游任何测试用例
- [x] **是**，存在对上游测试用例的修改（请在下方逐条说明）

以下修复已通过22项生产补丁重放，并将全部19个受影响源码文件与原生二进制构建输入绑定；本轮正式 USB r37 执行该冻结候选，不把旧 r35 overlay 的结果拼接到本轮。

1. `tests/file/dir.cpp`、`tests/filename/filenametest.cpp`、`tests/fswatcher/fswatchertest.cpp`、`tests/intl/intltest.cpp`、`tests/mbconv/*`、`tests/strings/numformatter.cpp`、`tests/xml/xmltest.cpp`：保留精确 id/path/reason 的运行时能力分支；仅在前置能力实际不可用时标记，正常路径保留原断言。其实际触发情况在补充说明中逐项列出。
2. `tests/graphics/clippingbox.cpp`：修正父窗口 client-area 分配并使用有界 paint wait，保留原 clipping 比较与容差；仅真实尺寸不支持时产生单一原因。r37 未触发跳过，原断言实际运行。
3. `tests/graphics/bmpbundle.cpp`：GTK 入口按已选原生 art provider 的正尺寸 hint 验证，不把另一 provider 的固定 24 像素假设套用到 GTK；未直接证明 Tango fallback 的全部行为。`tests/events/clone.cpp`：显式构造 Keyboard-origin help 事件并验证克隆 origin/position/id，不宣称实现全局 F1 状态查询。`tests/toplevel/toplevel.cpp`：明确 Raise 后验证显示/激活、Hide 后失活；使用任务私有 Broadway 隐藏焦点通知修复，不修改系统 GTK。这三个 GUI 能力跳过已消除，完整 GUI 467 项执行、32916 个断言成功；断言数来自本轮 XML，不复用旧 r35 的32925。
4. `tests/drawing/drawing.cpp`：去掉无条件返回，使用真实换行及 renderer/context 条件守卫。旧崩溃发生于 Native child 的 reference-root 发现，不能称为已证明的 context 不支持。私有 HAP 显式传递上游 fixture-root；官方源码未附 portable basic-case PNG，因此仅该平台无关 basic case 采用独立源码规格的 800x600 不透明白色检查（维度/RGB/透明度），不以目标输出生成 golden、不放宽容差。参考存在及其他 case 保留原比较。r37 Drawing 1/1、4 个实质断言、无跳过。
5. 计数修正：FallbackMultibyte/StreamFallbackMultibyte 实际 XML owner 为 ConvAutoTestCase，不应合并至 MBConvTestCase。旧 r34 的 35 项应为 36 项（Base33+GUI3）；旧冻结证据保留不改。r35 已独立按真实 TestCase 祖先计数，Base33、GUI0、Drawing0。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

修复既有上游 fixture 与能力审计，不虚增上游数量。图像规格断言仍属于原 Drawing case。另行验证真实 GUI consumer 和按钮/复选框/ASCII 文本回调；中文初始显示文本不等于中文 IME 输入已验证。

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：897/897（100%）
- 新增测试用例通过率：0/0（不适用）

上述100%仅表示当前配置的897项 Catch 框架用例均执行并成功结束，失败0、框架 SKIP 终态0；不是全功能覆盖率。Base33项仍有40个原因明确的能力受限分支事件，必须与框架用例终态分别记账，不能把受限分支写成功能 PASS。GUI/Drawing 无能力标记。鸿蒙特有测试1/1、消费者1/1与状态3/3另列，不增加上游分母。编译通过指已绑定的原生测试模块及本轮签名 HAP，非本轮重复全量编译。

本任务申请人于 2026-10-05 明确接受“有具体原因并在 PR 披露的能力限制”作为 W3 可接受结果。按此任务专属标准，正式 r37 **当前冻结候选**验收为 **W3 PASS_WITH_EXPLAINED_CAPABILITY_LIMITS**。这不是对未执行或真实失败的豁免，也不等于评审委员会已经批准。r35 原 overlay 证据仍保留为历史诊断。

r37 Base/GUI/Drawing 429/467/1 全部执行且零失败；成功断言分别为 1161894/32916/4，能力标记测试项为 33/0/0。普通消费者 1/1、button/checkbox/ASCII text 状态 3/3，`WX_GUI_EXIT rc=0`，RELEASED 和 POSTRELEASE_PASS 已独立回读。

W3 绑定提交前 HEAD `9858a2054bef5c15c7e80c349dae2089d8a572ca` 与 staged tree `278852b7f1caf695ae7f28b595ee9deade78ceb9`，产品输入均独立记录 SHA-256。最终提交的产品输入须与冻结输入逐项一致；知识与正文补充不改变执行行为，不重跑已消费的 launch。该候选仍需当前 HEAD 的合同、Review/CI及提审回读，不能用旧 CI 代替。

## 补充说明

### 能力限制的具体原因与实际范围

以下计数来自 r37 原始 XML 实际 TestCase 祖先；同一测试项可能在多个分支产生标记，所以 40 个事件不等于 40 个跳过用例。部分带标记测试项仍执行其他有效断言，不把 33 项统称为完全未运行。

| 冻结原因 | 实际测试项数 | 测试项及受限条件 |
|---|---:|---|
| `directory_fixture_unreadable` | 1 | `Dir::Exists`：目标测试进程无法读取该目录 fixture，无法验证其目录存在性分支；不等于所有目录 API 不可用 |
| `root_directory_unreadable` | 1 | `Dir::GetName`：签名应用子进程不能读取所需根目录；不改变系统/沙箱权限绕过此限制 |
| `system_tmp_unwritable` | 1 | `wxFileName::CreateTempFileName`：所需系统临时目录不可写；应用私有可写路径的成功不能代替此系统目录分支 |
| `symlink_unavailable` | 3 | `wxFileName::SameAs`、`wxFileName::Symlinks`、`wxFileSystemWatcher::Trees`：对应 fixture 符号链接创建能力不可用，原链接同一性/递归监控前置条件不成立；不宣称全系统不支持链接 |
| `encoding_unavailable` | 2 | `ConvAutoTestCase`、`MBConvTestCase`：目标闭包的具体编码转换能力探测不支持所需分支；保留可用编码的原断言，不将不支持的编码替换为假期望 |
| `xml_encoding_unavailable` | 1 | `XmlTestCase`：对应 XML 编码转换探测不支持，不能推断所有 XML 解析功能都不可用 |
| `locale_data_unavailable` | 1 | `wxUILocale::GetInfo`：所需 locale 数据不可获得，无法验证该本地化数据分支 |
| `locale_collation_unavailable` | 1 | `wxUILocale::CompareStrings`：所需 locale 排序规则不可获得，不以 C locale 排序结果冒充所要求的排序规则 |
| `locale_number_format_unavailable` | 22 | 所需 locale/数字格式数据不满足原测试前置条件。精确测试项：`FormatNumberTestCase::{PositiveIntegers,NegativeIntegers,PositiveReals,NegativeReals}`；`FormatNumberAlternateTestCase::{PositiveIntegers,NegativeIntegers,PositiveReals,NegativeReals}`；`NumFormatter::{DoubleFromString,DoubleToString,LongFromString,LongLongFromString,LongLongToString,LongToString,ULongLongFromString}`；`NumFormatterAlternateTestCase::{DoubleFromString,DoubleToString,LongFromString,LongLongFromString,LongLongToString,LongToString,NoTrailingZeroes}`。花括号逐项展开为实际 TestCase 名称 |
| **合计** | **33** | 24 项 locale/数字格式、3 项编码、6 项目录/临时目录/符号链接；GUI/Drawing 不在此限制集合中 |

精确 marker id、源码路径、reason 和 XML owner 保留在冻结的配方/validator 输入及原始日志中；额外标记、原因漂移或真实失败不得用本任务例外解释为通过。Catch XML 的零直接 Section 聚合不能用于推断某个 case 零断言，整体断言总数使用根 OverallResults，不双重累加子 Section。

### 身份、来源与未覆盖范围

- 关联 Issue：[3444](https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/3444)
- 队伍名称：HarmonyPC
- 申请人显示标识：2301_80739235
- 源分支：feat/wxwidgets-3.3.3.2
- 目标分支：main
- r37 run_id `wxwidgets-3332-review-usb-r37`，USB serial `3QC0124C20000792`，launch_count=1；无 SSH。
- freeze SHA-256 `4aa3bbce5592660ff343353848ca4f20f48b71d74c543fd43aa75f322614fef9`；签名 HAP 131840585 bytes，SHA-256 `fb3ce579e5a3b39f5fa96e4efc0f02460c5d70be749738a649cc6ce36ed6ddaf`；fresh transfer 后两次独立逐字节回读一致。
- 15 个链式 receipt 完成至 POSTRELEASE_PASS；本轮冻结 controller/validator 未修改，旧事务证据不覆盖。
- Base/GUI/Drawing 原始 XML SHA-256 分别为 `e9f9633f1237150995d169a1ad83c3de849b5d6523cee17b58f91cb73ceb0cbb` / `b1921db35c34769a7dd8a4a2b2ac840773fd747d2ee4f3a1d179197d0f9c3f82` / `4c0b8716f146aec5efdeda14b2dfb6ea1dbb51daab0045a103f33fe67c53e60e`。
- 耐久证据根 `F:/HarmonyPC/wxwidgets-333/review-w3-r37`；完整冻结结果 `usb-result-frozen.json`；消费者截图 `consumer-1791216309415973700.png`（3120x2080）。这些本机路径不是公开附件 URL。
- Base/GUI/Drawing 复用与当前源码一致的精确原生构建输入和库；签名 HAP在 r37 重新打包。Windows 正式 Conan create 本轮未重跑，不冒充成功。
- Conan 配方仍为静态 wxBase、wxUSE_GUI=OFF；签名 HAP 的 GTK3 Broadway GUI 是独立补充验证，不是 HarmonyOS 原生窗口后端，也不表示 Conan 包启用了 GUI。WebView/Media/OpenGL 不在本轮配置内；中文 IME 未验证。
- 既有 CI PASS 仅绑定公开 HEAD，不替代本地未推送修复的 Review/CI；不宣称 Pre-PR、人工评审或提审已经闭环。
- 历史 r24 零断言 Drawing 结果、r30/r31 崩溃、r32 缺参考、r33 文本状态失败和 r34 旧计数均保留，不拼接不同事务证据。
- HD1/HD2/HD3 不命中；HD4 技术依据为 GUI provider/同 SONAME/AT_SECURE 签名 Native child 与多套件资源闭包的实际适配和验证，不以依赖数量、测试数或耗时单独申报。最终分值由评审委员会确认。
- 配对草稿 `knowledge/drafts/E336-draft-wxwidgets-usb-gui-capability.kv/.md` 已有本地候选；原始日志、签名材料、HAP 不加入 PR，不上传制品仓。
