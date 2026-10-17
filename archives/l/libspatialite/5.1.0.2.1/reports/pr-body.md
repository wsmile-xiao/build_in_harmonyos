## PR 信息

- **三方库名称**：libspatialite
- **上游版本**：v5.1.0
- **上游仓库地址**：https://www.gaia-gis.it/fossil/libspatialite
- **适配路径**：路径 A（基础适配） / 路径 B（贡献创新）
- **使用知识库**：E264；新增 `E544-draft-2301_80739235` 草稿

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 79 | 来源：上游 `test/Makefile.am` 基础测试 |
| 集成测试 | 29 | 来源：上游 `test/Makefile.am` GeoPackage 测试 |
| 其他测试 | 0 | 上游归档没有其他注册测试 |
| **合计** | **108** | 完整清单由配置后的 Automake `TESTS` 注册项审计 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|---------------:|------------|------|
| 单元测试 | 79 | 不变 | 上游基础测试完整执行 |
| 集成测试 | 29 | 不变 | 上游 GeoPackage 测试完整执行 |
| 鸿蒙特有测试 | 17 | +17 | 17 个 consumer 断言；依赖版本/二进制负测作为独立定向矩阵统计 |
| **合计** | **125** | **+17** | 上游 108 项与新增 17 项均完整通过 |

---

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [ ] **否**，未修改上游任何测试用例
- [x] **是**，存在对上游测试用例的修改（请在下方逐条说明）

> 1. `test/check_spatialindex.c`：将 `strcmp` 结果改为只比较符号，避免依赖 libc 返回幅度。
> 2. `test/sql_stmt_geos_tests/relations7.testcase`：同步 GEOS 3.13.1 的零长度 LineString 关系结果。
> 3. `test/sql_stmt_geos_tests/relations8.testcase`：同步 GEOS 3.13.1 的反向关系结果。
> 4. `test/check_libxml2.c`：统一允许目标 zlib/libxml2 实测的 books/opera/movies 压缩尺寸集合 432/433、425/426/427、577/557，并在失败信息中列出完整允许值，不再区分平台宏。

---

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

> 补全范围为 Conan 安装包和依赖图契约：`test_package/test.c` 提供 17 个公开 API、链接闭包和 SQLite 关闭失败清理断言；`test_package/conanfile.py` 及定向矩阵提供 4 个 canonical RTTOPO/GEOS 版本与 binary-folder 负测。

---

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：108/108（100%）
- 新增测试用例通过率：17/17（100%）
- 当前候选已完成 fresh OHOS/arm64 W3：正式 `librttopo/1.1.0` 以 `--build=never` 解析并取回 binary，完整 libspatialite build/test 通过；精确 HEAD、tree 和 snapshot 由 Pre-PR 合同与 W3 终态共同绑定。
- 上游测试统一计数 108/108；consumer 断言 17/17；依赖合同定向测试 4/4；`SQLITE_CLOSE_BUSY_SHUTDOWN=pass`。
- W3 的 runner/launch exit code 均为 0，结果归档通过独立 validator，远端唯一任务根已清理并回读不存在。
- 独立 W4 为 P0/P1/P2/P3=0/0/0/0；源码、配方和补丁中的 LLVM 工具绑定与平台无关尺寸集合已完成定向验证。
- `manifest.yaml` 保持 `status: built`，未手工创建或修改 `.ci-result.json`；PR 当前尚未触发 Review 或 CI。

---

## 补充说明

- 关联 Issue：#1699
- 队伍名称：天天开心
- 申请人显示标识：2301_80739235
- 源分支：2301_80739235:feat/libspatialite-5.1.0.2.1
- 目标分支：OpenHarmonyPCDeveloper/build_in_harmonyos:main
- 其他说明：Buildbot #37212 在 L0j 报告 `libspatialite/5.1.0.2` 已被不同 recipe 占用，因此本 successor 递增为 `5.1.0.2.1`；提供方修复保留正式 `librttopo/1.1.0` 并移除临时 `1.1.0.1`，不覆盖已合入的 `libspatialite/5.1.0.1`，也不改写旧 PR #7831 的证据。
