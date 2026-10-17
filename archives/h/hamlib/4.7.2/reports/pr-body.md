## PR 信息

- **三方库名称**：hamlib
- **上游版本**：4.7.2
- **上游仓库地址**：https://github.com/Hamlib/Hamlib
- **适配路径**：路径 A（基础适配） / 路径 B（贡献创新）
- **使用知识库**：E603 草稿；openharmony-pc-pthread-cancel-cooperative-stop；autotools-install-source-folder-and-toybox-process-boundary

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 0 | 上游 Automake TESTS 未单独划分单元测试 |
| 集成测试 | 12 | 来源：tests/Makefile.am 的 11 个 TESTS/check_SCRIPTS 与 c++/Makefile.am 的 testcpp，r009 目标 harness |
| 其他测试 | 0 | 本版本无额外注册的逻辑测试 |
| **合计** | **12** | 清单：reports 外部证据 upstream-test-inventory.txt；支持程序不重复计入分母 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|---------------:|------------|------|
| 单元测试 | 0 | 不变 | 未改变上游测试分类 |
| 集成测试 | 12 | 不变 | r009 真机单次 launch，12/12 通过 |
| 鸿蒙特有测试 | 1 | +1 | Conan consumer 调用公开 API，4/4 assertions 通过 |
| **合计** | **13** | **+1** | 新增 consumer 不改变上游 12 项分母 |

---

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

r009 的目标 harness 仅在任务证据载荷中提供 `/system/bin/sh` 调用和 toybox `ps` 能力
适配，未修改提交到仓库的上游 tests 源文件或测试注册。

---

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

Conan test_package 的 consumer 是包消费契约，不是对上游缺失测试的补全。

---

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：12/12（100%）
- 新增测试用例通过率：1/1（100%）

本地 `conan create` r36 的完整日志为 `F:\HarmonyPC\hamlib-4.7.2-adapt-20260907\conan-create-r36.log`，
日志 SHA-256 为 `ccaf06e29d678ffadc24d2725cb6c786ea6c090165b7eb7993d9dbe3a5d99bec`，
返回 `CONAN_CREATE_RC=0`。r009 绑定当前 package reference
`hamlib/4.7.2#d2547c8d2e7cc66608d664b16381e788:21b17f8b2bc0e9511e276e3d57a23893067cefe5#a72c033b0d0f0251b0da64d3178c31c8`。
真机证据 `w3-r009/evidence/terminal.json` 记录 consumer RC=0、`rigctl -l` RC=0 且非空、
`TEST_SUMMARY=12/12 FAILED=0`；`w3-r009/evidence/postrelease.json` 记录远端根已为 `ABSENT`。
平台 AI Review 与 CI 在 PR 创建后按当前 HEAD 继续执行。

---

## 补充说明

- 关联 Issue：#2832
- 队伍名称：OpenHarmony PC Developer
- 申请人显示标识：2301_80739235
- 源分支：2301_80739235:feat/hamlib-4.7.2
- 目标分支：OpenHarmonyPCDeveloper/build_in_harmonyos:main
- 其他说明：Issue #2832 已全状态去重并保持 OPEN。HD1-HD4 当前均为 matched=false，使用路径 A+B 和唯一前缀 `【知识库扩展】`。E603 草稿新增了安装 helper 能力拆分、Conan source_folder 清理和 toybox 进程/Socket 验证边界；recipe 仍只使用任务闭包中的工具路径，不把本机绝对路径写入包元数据。
