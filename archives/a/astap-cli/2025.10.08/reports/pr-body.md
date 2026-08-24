- **三方库名称**：astap-cli
- **上游版本**：2025.10.08
- **上游仓库地址**：https://salsa.debian.org/debian-astro-team/astap-cli
- **适配路径**：路径 A（基础适配）
- **使用知识库**：openharmony-compile-agent

## 测试用例对比

### 上游库测试用例统计

已核查 Debian `astap-cli 2025.10.08-1` 源码包、`debian/rules` 和完整源码目录。上游没有 `debian/tests` autopkgtest，也没有自动化测试目标。

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 0 | 上游无单元测试目录或测试目标 |
| 集成测试 | 0 | 上游无集成测试工程 |
| 其他测试 | 0 | 上游无可执行测试脚本 |
| **合计** | **0** | **上游无测试用例** |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------:|-----------|------|
| 单元测试 | 0 | 不变 | 未新增独立单元测试目标 |
| 集成测试 | 9 | +9 | 直接运行 Conan 制品，覆盖 CLI 接口和真实 FITS 分析 |
| 鸿蒙特有测试 | 0 | 新增 | 平台相关验证包含在 Conan 集成测试和 ELF 签名门禁中 |
| **合计** | **9** | **+9** | **9/9（100%）通过** |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改

上游没有测试用例，因此没有删除、跳过或替换上游测试。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无测试用例，适配后补全了测试

- **补全的测试范围**：新增 9 项 CLI 集成断言，包含版本身份、帮助选项、无参数用法、错误诊断和有效 FITS 图像分析。
- **补全原因**：上游仅提供 CLI Pascal 工程，没有正式自动化测试框架。
- **新增测试文件清单**：
  1. `archives/a/astap-cli/2025.10.08/test_package/test_astap_cli.sh` — CLI 和 FITS 集成断言。
  2. `archives/a/astap-cli/2025.10.08/test_package/generate_test_fits.py` — 确定性 FITS 星场生成器。
  3. `archives/a/astap-cli/2025.10.08/test_package/conanfile.py` — Conan 消费者测试入口。
  4. `archives/a/astap-cli/2025.10.08/test_package/MANIFEST.yml` — 测试清单和断言统计。

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：`0/0（N/A）`
- 新增测试用例通过率：`9/9（100%）`

验证环境：HarmonyOS PC arm64，Conan 2.29.1，Free Pascal Compiler 3.2.2。

```bash
conan create archives/a/astap-cli/2025.10.08 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=astap-cli/*
```

## 补充说明

- `astap-cli 2025.10.08` 是独立命令行工程，不依赖 Lazarus GUI、Qt Widgetset 或 LCL 运行时。
- 上游版本常量由 `2025.09.29` 同步为 `2025.10.08`，使用最小补丁并通过精确版本断言验证。
- FPC 构建工具和最终 `astap_cli` ELF 均完成 HarmonyOS 签名。
