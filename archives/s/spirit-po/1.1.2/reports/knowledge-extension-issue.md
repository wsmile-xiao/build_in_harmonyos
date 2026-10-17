**【申请人账号】** Awstme
**【队伍名称】** gogogo
**【申请日期】** 2026/09/03
**【库名称】** spirit-po

## 关联 PR

PR：!8012
PR 链接：`https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/8012`
分支信息：`feat/spirit-po-1.1.2` → `main`
当前提交：以 PR #8012 的 GitCode 最新 head SHA 回读为准（本 Issue 与 PR 同步更新）
PR 状态：开放中

## 申请路径 B 的理由

本任务发现并修复 spirit-po v1.1.2 **公开头文件本身**在严格 C++11/OHOS clang 下使用未限定 `uint` 而导致 `unknown type name 'uint'` 的可复现可移植性缺陷——这不是单个编译 patch，而是「公共 header 直接依赖标准头未提供的 typedef + 第三方本地化对照测试依赖运行时可选运行时」这类模式的组合诊断。适配过程中还需把断言级单元检查（126）、PO 数据驱动对照用例（206）与 Conan 消费者用例（1）分栏，并对因运行时欠 feature 而整体无法执行的对照套件保留完整分母、逐条给出越过原因，而不是压缩分母或伪造 PASS。

推广价值：可复用于需要引用 Boost.Spirit/解析本地化/多语言数据、同时带「官方单元套件」+「依赖 libintl 等运行时的对照套件」的 OHOS C++11(C++17) 库；其「公开头非标准 typedef」「缺可选运行时时的测试记账」规则可跨库迁移（GLib TAP/Json/Spirit/PO 等）。

## 知识库查重与新增价值

新增 draft：`knowledge/drafts/E543-draft-SP11.kv`、`knowledge/drafts/E543-draft-SP11.md`
拟提升编号：`E543`（最终编号由知识库主编确认）
条目主题：严格 OHOS C++11 下 header-only Spirit/PO 库公开头的 std::size_t 可移植性修复 + 上游 unit/libintl 对照/消费者测试的分栏记账与有据跳过证据
查重关键词：`spirit-po`、`Boost.Spirit`、`boost/spirit`、`unknown type name uint`、`std::size_t`、`header-only`、`libintl.h`、`Intl REQUIRED`、`asset/test count`、`po data-driven`、`SKIP 分母`
覆盖判断：`knowledge/graph/index.tsv`(767 行)、`knowledge/graph/`、`knowledge/doc/`、`knowledge/drafts/` 均无精确 `spirit-po`/`Boost.Spirit` 专题条目。E035/E099 只覆盖 Boost.Build/b2 平台检测；E257/E321/E322 只覆盖通用 header-only Conan 配方骨架；E307 覆盖无 CMake 消费者直编；E458/Boost-header-only vendor 草稿面向「curated Boost 缺头/组件」。没有条目覆盖「Spirit/PO 自有公共头的严格 C++11 未限定类型错误」与「assertion-level unit / PO data-driven integration / consumer executable 三种口径分栏 + 完整分母 + 运行时缺 libintl 时整组有据 SKIP」的证据合同，故本条目增量成立。

## 证据材料

| 项目 | 内容 |
| --- | --- |
| 原始失败 | OHOS clang 15 编译上游 `test/main.cpp`：`include/spirit_po/exceptions.hpp:24:3: error: unknown type name 'uint'`；放开后 debug-only `po_message.hpp` 同类。 |
| 修复方案 | 补丁 `0001-include-spirit_po-exceptions.hpp.patch`、`0002-include-spirit_po-po_message.hpp.patch`（均由规范 refresh-patch 生成，`uint→std::size_t`；不改上游测试、无 `#ifdef __OHOS__`）。 |
| 构建验证 | HarmonyOS PC / OHOS aarch64 / clang 15 / C++11-17 / Conan 2.29.1 适配 profile；`conan create`（该 build 内复现上游单元测试）成功。 |
| 上游测试 | `test/main.cpp`：126/126 assertion PASS（覆盖 12 正常 + 10 失败 PO fixture）。`test_libintl/main.cpp`：206 个 `po/*.po` 数据驱动 executable-level cases，**跳过**（技术原因：本 OHOS worker 有 `msgfmt 0.26` 但无 `libintl.h` 且无 `libintl.so/.a`，上游 `find_package(Intl REQUIRED)`+链接 `INTL_LIBRARIES` 无法构建；不能以 msgfmt 冒充运行时对照）。 |
| 消费者验证 | `test_package/test_spirit_po.cpp` 真实链接 `spirit-po::spirit-po`，`from_range/gettext/pgettext/ngettext/missing-key` 独立 1/1；L1e 破坏性反向验证通过。 |
| 审查证据 | 待 PR 建后 CI / AI review 结果回填。 |
| 当前 CI | PR + Exact-HEAD CI 建立后回填状态；W3 本地 `build_and_test.sh` 已通过（Success 1 / Failed 0）。 |

## 申请分值

**路径 B 贡献创新：10 分候选**

理由：草稿精确给出 "公共头 `uint→std::size_t` 可移植修复" 与「三种测试口径分栏、完整分母、无 libintl 时整组有据 SKIP、禁止 `msgfmt` 冒充运行时」的可审计测试记账，阻止虚报 100% 通过率，可复用于其他带运行时可选项对照套件的解析/本地化库。

*测试框架/工具链验证作为路径 B 证明材料，不重复申报额外分值。最终以官方审核为准。*

## 其他说明

- 本 PR 同时包含 spirit-po 的适配产出；路径 B 申报为随库的知识库扩散（非单独只申报知识的分值）。
- 依赖仓库内共享 `boost/1.90.0` 配方；本 PR 不修改共享 Boost 配方。
- 原始失败、修复、E543 与 evidence 均在 `feat/spirit-po-1.1.2` 提交 `7a252c69`。评审/CI 变化时本 Issue 证据将随 PR 提交更新。

## 需要官方确认的问题

1. 是否认可本 PR 按路径 B（贡献创新，10 分候选）评审
2. 是否认可该「公共头 std::size_t 可移植性 + 对照测试分栏/完整分母/有据 SKIP」诊断组合属于可跨库复用的适配知识
3. 是否认可修复 + 验证证据，并允许草稿以 E543 在主编审核时确定最终编号
