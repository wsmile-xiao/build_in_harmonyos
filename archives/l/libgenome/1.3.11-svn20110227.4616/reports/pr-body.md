## PR 信息

- **三方库名称**：libgenome
- **上游版本**：1.3.11-svn20110227.4616
- **上游仓库地址**：https://sourceforge.net/projects/libgenome/ （源码采用 Debian 官方镜像中的上游原始 tar.xz）
- **适配路径**：路径 A（基础适配） + 路径 B（贡献创新）；本 PR 按 B 类申请
- **使用知识库**：新增 `E8211-draft-2501_91199785`（Libtoolize GREP）与 `E8212-draft-2501_91199785`（CI Perl XS 权限）；参考 E521、E514、E212、E729 草稿区分各自边界

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 1 | `libGenome/Makefile.am` 的 `check_PROGRAMS = TestRevComp`；原 `TESTS` 漏登记，修复后由 Automake 自动执行 |
| 集成测试 | 0 | 未注册自动集成测试 |
| 其他测试 | 0 | 七个 `EXTRA_PROGRAMS` 是未纳入 `make check` 的手工/交互原型，单列于清单，不充当已执行用例 |
| **合计** | **1** | 完整清单见 `reports/upstream-test-inventory.txt` |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------:|------------|------|
| 单元测试 | 1 | 不变 | 修复并登记原 `TestRevComp`，真机 `make check` 1/1 PASS |
| 集成测试 | 0 | 不变 | 无上游集成测试 |
| 鸿蒙特有测试 | 1 | +1 | `test_package/test.cpp` 安装后检查序列、spec 和反向互补，共四个断言，1/1 PASS |
| **合计** | **2** | **+1** | 上游 1/1；新增消费者 1/1 |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [ ] **否**，未修改上游任何测试用例
- [x] **是**，存在对上游测试用例的修改（如下）

1. **修改的测试文件**：`libGenome/TestRevComp.cpp`（配方补丁 `0002-libGenome-TestRevComp.cpp.patch`）
   - **修改原因**：原测试引用发行包中不存在的 `gnDNXSource.h`，并等待 stdin，无法在无人值守的 `make check` 中执行。
   - **修改内容**：保留上游反向互补验证语义，改为固定输入 `ATGCC`、预期 `GGCAT` 的确定性断言。
2. **修改的测试入口**：`libGenome/Makefile.am`（补丁 `0001-libGenome-Makefile.am.patch`）
   - **修改原因**：只定义 `check_PROGRAMS` 而未定义 `TESTS`；链接目标仍指向不存在的旧静态归档。
   - **修改内容**：登记 `TESTS = TestRevComp` 并链接真实 `libGenome-1.3.la`。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试

上游已有反向互补用例，本次修复其可运行性；另新增独立的 Conan 安装包消费者验证，不将它冒充上游测试。

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：1/1（100%）
- 新增测试用例通过率：1/1（100%）

OHOS AArch64 真机 `conan create` 返回 0。修复后冻结事务 `w3-libgenome-20260928T081735Z` 经完整 12 阶段回执验证为 `W3_PASS`，单次启动、无残留任务进程并完成释放。原始日志 SHA-256：`9e19a02a683676dd9cec8b1dc83a93d36c87cdfd66a2ae665288d630c154bb06`。`make check` 显示 `PASS: TestRevComp`、`TOTAL: 1`、`PASS: 1`、`FAIL: 0`；安装后消费者输出 `libgenome reverse-complement consumer: PASS`。详细清单与方法见 `reports/upstream-test-inventory.txt` 和 `reports/test-report.md`。先前 CI #63612 因 Conan 缓存中的 Perl `Cwd.so` 加载被拒而失败；本次修复后的 CI 与最新 AI Review 尚待重新触发和回读。

## 补充说明

- 关联 Issue：#3484
- 队伍名称：诶，云朵
- 申请人显示标识：2501_91199785
- 源分支：2501_91199785:feat/libgenome-1.3.11-svn20110227.4616
- 目标分支：OpenHarmonyPCDeveloper/build_in_harmonyos:main
- 路径 B 知识草稿为 `knowledge/drafts/E8211-draft-2501_91199785.{kv,md}` 和 `knowledge/drafts/E8212-draft-2501_91199785.{kv,md}`；查重记录见 `reports/knowledge-dedup-result.json`。合并后再按平台 `/release` 流程发布制品，本 PR 不上传。
