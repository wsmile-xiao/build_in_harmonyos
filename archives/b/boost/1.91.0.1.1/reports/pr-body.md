## PR 信息

- **三方库名称**：boost
- **上游版本**：1.91.0（官方修订标签 `boost-1.91.0-1`；Conan 修复版 `1.91.0.1.1`）
- **上游仓库地址**：https://github.com/boostorg/boost
- **适配路径**：修复路径（补齐已发布 Boost 包的 Multiprecision 组件闭包）
- **使用知识库**：E005、E099、E127、E181、E183、E207、boost-selective-component-package-missing-header、openharmony-pc-cmake-soname-hmdfs、openharmony-pc-target-shell-heredoc-readonly-tmp

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 16 | Boost.ProgramOptions 14 个官方流程、Boost.Multiprecision 官方叶子和未修改的 Boost.Graph disjoint-set 叶子 |
| 集成测试 | 2 | Boost.Iostreams `test_fd` 与 Boost.Regex `quick` 官方 CMake 流程 |
| 其他测试 | 0 | shared/static 是同一清单的构建模式复核，不重复计数 |
| **合计** | **18** | `upstream-inventory.txt` 绑定 `INVENTORY_COUNT=18` |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|---------------:|------------|------|
| 单元测试 | 16 | 不变 | 原样执行全部上游单元测试入口 |
| 集成测试 | 8 | +6 | 两个上游集成入口加六个 Conan 组件消费者 |
| 鸿蒙特有测试 | 1 | +1 | Filesystem 回退与无 Thread interruption 的平台合同 |
| **合计** | **25** | **+7** | 上游 18/18，新增消费者 7/7 |

---

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

> 18 个入口均来自官方 CMake 测试注册、对应 Jamfile 或 Boost.Graph 精确标签。补丁只调整 OHOS 安装阶段的版本软链接生成条件，不修改测试源码、输入或判定。

---

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

> 上游已有 18 个被选择并完整执行的正式入口。新增七个消费者用于验证 Conan 导出的 CMake 组件、Redex 实际 API 形状和 OHOS 平台合同，不替代或重复计数上游测试。

---

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：18/18（100%）
- 新增测试用例通过率：7/7（100%）

- HarmonyOS PC AArch64 r4 在同一冻结候选上完成 shared/static 两种构建。两种模式分别执行完整 18 项上游清单和 7 项消费者清单，全部通过；变体不重复计数。
- 两个包均含 `boost/multiprecision/cpp_int.hpp` 和 `Boost::multiprecision` target，均有 12 个编译库、0 个 symlink；共享库为 AArch64 ELF 且含 `.codesign`。
- shared：`boost/1.91.0.1.1#a87a5f6c933b59858076703e53cff426:01d92cf349a0dd98ff915f4bd99a04430171517f#978f06a635235df28409196d5aefb699`。
- static：`boost/1.91.0.1.1#a87a5f6c933b59858076703e53cff426:21b17f8b2bc0e9511e276e3d57a23893067cefe5#d0c81c39274e78a17a81cfeb757d0ff8`。
- 原始 shared/static 日志 SHA-256 分别为 `0e848ee0395d193e31947e13b24ddc6d4a5f962658c44dca476d789a0028e5e1`、`e7a4be0db6f7dc791c6a7558a8d1ab2bb3263b080601882a34f818915b1a5298`；规范化上游日志 SHA-256 为 `f15bb093eac01ebcaa4d7ae3cc3a92a44407714ce91498b9929cdd50372b2477`。
- legacy `finish` 外层在真实 W3 通过后仍因 Conan 配方没有独立 `packaging/` 和 staging marker 返回 1。本 PR 未创建空 marker、伪造 tar 或上传制品；提交结论以独立 W4、Pre-PR 合同和当前 HEAD 的 PR CI 为准。

---

## 补充说明

- 关联 Issue：#1247
- 队伍名称：天天开心
- 申请人显示标识：2301_80739235
- 源分支：2301_80739235:fix/boost-1.91.0.1.1
- 目标分支：OpenHarmonyPCDeveloper/build_in_harmonyos:main
- 其他说明：这是已发布 `boost/1.91.0.1` 的后续修复，不覆盖旧版本。知识查重结论为 `REUSE_EXISTING`；本次复用已有 Boost CMake、OHOS pthread/SONAME/HMDFS 以及选择性组件闭包知识，不新增仓内知识草稿。PR 合并后必须执行 `/release`，并以全新隔离 OHOS/arm64 `--build=never` 回读确认制品仓发布后，Redex 才能更新依赖。
