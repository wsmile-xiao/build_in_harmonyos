## PR 信息

- **三方库名称**：pslib
- **上游版本**：0.4.8
- **上游仓库地址**：https://pslib.sourceforge.net/ （源码采用 Debian 官方镜像中的上游原始 tarball）
- **适配路径**：路径 A（基础适配） + 路径 B（贡献创新）；本 PR 按 B 类申请
- **使用知识库**：新草稿 `E6402-draft-8B7F`；参考现有 E565 与 E129，分别明确 NLS/Perl ABI 边界及复用 HMDFS 临时目录修复

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 0 | 0.4.8 发行包没有注册的单元测试目标 |
| 集成测试 | 0 | `Makefile.am` 和各子目录未注册集成测试 |
| 其他测试 | 0 | `make check -j1` 执行并成功，但只运行 `po` catalog 检查，不构成注册测试用例 |
| **合计** | **0** | 完整清单见 `reports/upstream-test-inventory.txt`；0/0 为不适用 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|---------------:|------------|------|
| 单元测试 | 0 | 不变 | 未改上游测试入口 |
| 集成测试 | 0 | 不变 | 未改上游测试入口 |
| 鸿蒙特有测试 | 1 | +1 | Conan `test_package/test.c` 在安装后编译、链接、运行，生成并检查一页内存 PostScript 文档 |
| **合计** | **1** | **+1** | 上游 0 项，新增消费者测试 1/1 PASS |

---

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改

仅在配方构建阶段对旧 `configure` 的 XML 检查守卫、`config.sub` 的 OHOS 平台表和 `config.status` 两条临时目录创建分支进行精确受控转换；未删除、屏蔽或修改上游测试文件与 `make check` 入口。

---

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无测试用例，适配后补全了测试

发行包 `Makefile.am` 及子目录没有注册 `TESTS` 或 `check_PROGRAMS`，因此新增 `archives/p/pslib/0.4.8/test_package/test.c` 和相应 Conan/CMake 测试入口，对公开版本 API、内存文档生成及 PostScript 页数/结束标记做一次安装后验证。仍完整执行上游 `make check -j1`；不把它的成功冒充成上游用例 100% 覆盖。

---

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：0/0（不适用）
- 新增测试用例通过率：1/1（100%）

目标机 HarmonyOS aarch64 / OHOS 6.0，Conan 2.29.1。针对平台 CI #61625 暴露的 HMDFS `subs1.awk: Permission denied`，不再使用固定创建 0700 目录的 `mktemp -d`，而在预生成 `configure` 中以原子 `mkdir` 和 `umask 007` 创建组可访问的临时目录。新候选在实机上 `conan create` 与安装后消费者均返回 0；独立冻结事务 `pslib-w3-20260926T082400Z` 完成 12/12 回执，验证器 `W3_PASS`，原始日志 SHA-256 `6e0fb01f926e98bf9315f5a274effbec244824ab68d5f8bb1ab6b05737494161`。`configure` 检测 PNG/JPEG 均启用；`make check -j1` 返回 0。详细证据见 `reports/test-report.md` 与 `reports/upstream-test-inventory.txt`。此候选仍待平台 CI 与 AI Review 回读，不预称通过。

---

## 补充说明

- 关联 Issue：#3450
- 队伍名称：诶，云朵
- 申请人显示标识：2501_91199785
- 源分支：2501_91199785:feat/pslib-0.4.8
- 目标分支：OpenHarmonyPCDeveloper/build_in_harmonyos:main
- 其他说明：知识查重结论为 `NO_EQUIVALENT_REUSABLE_KNOWLEDGE`，新增 `knowledge/drafts/E6402-draft-8B7F.{kv,md}`。适用范围限于可关闭 NLS 且不需要 XML 翻译合并的旧 intltool 项目；保留真实 intltool/gettext。GIF/TIFF 可选能力未启用。合并后才按平台流程执行 `/release`，此 PR 不上传制品。
