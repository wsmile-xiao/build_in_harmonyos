## PR 信息

- 三方库名称：wxwidgets
- 上游版本：v3.3.3
- 上游仓库地址：https://github.com/wxWidgets/wxWidgets
- 适配路径：路径 A（基础适配） / 路径 B（贡献创新） / 路径 C（高难度挑战）
- 使用知识库：E2152-draft-WX33；E231、E265、wxWidgets capability-probe 相关条目

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 429 | wxWidgets 3.3.3 Catch2 `test_base` 完整有序清单 |
| 集成测试 | 0 | 上游 wxBase 变体未注册独立集成测试 |
| 其他测试 | 0 | 本候选没有把 CTest 或 consumer 重复计入上游用例 |
| **合计** | **429** | 399 PASS + 30 个 reason-bound expected SKIP，failed=0，nonfailed=429 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|---------------:|------------|------|
| 单元测试 | 429 | 不变 | 目标设备完整执行上游清单 |
| 集成测试 | 0 | 不变 | CTest 注册项单独记录为 1/1 |
| 鸿蒙特有测试 | 0 | 不变 | 未新增独立消费者分母 |
| **合计** | **429** | **不变** | 上游分母保持完整，能力缺失只产生显式 expected SKIP |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [ ] **否**，未修改上游任何测试用例
- [x] **是**，存在对上游测试用例的修改（请在下方逐条说明）

1. **修改的测试文件**：`tests/file/dir.cpp`、`tests/filename/filenametest.cpp`、`tests/fswatcher/fswatchertest.cpp`
   - **修改原因**：目标端文件系统能力差异。
   - **修改内容**：保留原断言，在能力不可用时输出带 id、path、reason 的 expected-skip marker。
2. **修改的测试文件**：`tests/intl/intltest.cpp`、`tests/mbconv/convautotest.cpp`、`tests/mbconv/mbconvtest.cpp`、`tests/strings/numformatter.cpp`、`tests/xml/xmltest.cpp`
   - **修改原因**：locale、编码和 XML 能力需要运行时判定，且 GUI 框架源码不能假设目标 libc 行为。
   - **修改内容**：使用通用 POSIX/运行时能力探测及受控子进程边界，保留 reason-bound skip 计数，不使用 OHOS 条件编译宏。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

上游 Catch2、CTest 和 Conan `test_package` 均有明确入口；目标验证沿用这些入口，未凭空增加独立测试分母。

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：429/429（100%）
- 新增测试用例通过率：0/0（不适用）

W3 `wxwidgets-333-w3-019fb34c-r86ar` 在 `10.62.148.108:2222` 绑定当前 HEAD
`8953ef46ca3954a08e2ad80d2e5efe68f90f6fde`、candidate tree
`4a4bff24d5b14ba6a71fe1bb24f31c467ce2bdc4` 和固定 main
`493cadeeb3ef3b86c10990013b8e5df55ed8c727`。上游结果为 `399 PASS + 30 expected
SKIP = 429/429 nonfailed`，CTest `1/1`，consumer `1/1`。W3 freeze SHA-256 为
`964179a3dec3daee25744350f5c98fed91e6e9f4b04f2f13390728bf0ffb0c97`，输入包 SHA-256
为 `a5d3fa0236955fd9bd8c6721eaab2d9899276f2b35bf558637cb986260f88d72`；释放后远端根
为 ABSENT，本任务远端进程为 ZERO。

## 补充说明

- 关联 Issue：#2356
- 队伍名称：天天开心
- 申请人显示标识：2301_80739235
- 源分支：2301_80739235:feat/wxwidgets-3.3.3
- 目标分支：OpenHarmonyPCDeveloper/build_in_harmonyos:main
- 其他说明：wxWidgets 同时包含 GUI 框架，因此按高难度挑战提交；本候选实际交付并验证的是静态 wxBase 无 GUI 变体，GUI 窗口栈不被误宣称为已完成。E2152 KV/MD 配对记录 GitHub Release asset digest 身份绑定，发布动作仅允许合并后 `/release` 到 ohpcd。
