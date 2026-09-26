## 三方库信息

- **三方库名称**：instaloader
- **上游版本**：4.15.1
- **上游仓库地址**：https://github.com/instaloader/instaloader
- **适配路径**：路径 A（基础适配）
- **使用知识库**：openharmony-compile-agent；E540（构建环境临时目录规则）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 0 | 4.15.1 PyPI sdist 不含 tests/、pytest 配置或 unittest 测试模块 |
| 集成测试 | 0 | 上游 sdist 未提供集成测试入口 |
| 其他测试 | 0 | 上游 sdist 未提供测试脚本 |
| **合计** | **0** | 已核对完整 sdist 内容，非跳过已有测试 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------:|------------|------|
| 单元测试 | 0 | 不变 | 上游无单元测试 |
| 集成测试 | 0 | 不变 | 上游无集成测试 |
| 鸿蒙特有测试 | 9 | +9 | 安装后真实消费者测试：8 个包布局/API 断言 + 1 个安装 CLI `--version` 集成测试 |
| **合计** | **9** | **+9** | 全部新增消费者测试通过 |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改

上游 4.15.1 sdist 不包含测试目录或测试运行器，因此没有上游测试可修改；未伪造上游测试通过结果。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无测试用例，适配后补全了测试

- **补全的测试范围**：新增 8 个真实消费者 smoke 断言，并执行 1 个安装后的 `instaloader --version` 集成测试，共 9 个适配后测试。
- **补全原因**：上游 sdist 没有正式测试套件，需要验证 Conan 安装产物在 HarmonyOS Python 运行时中的真实可消费性。
- **新增测试文件清单**：
  1. `archives/i/instaloader/4.15.1/test_package/smoke.py` — 验证安装目录、版本、Instaloader 实例化和公开 API。
  2. `archives/i/instaloader/4.15.1/test_package/conanfile.py` — 运行 smoke 脚本并执行安装后的 CLI `--version`。
  3. `archives/i/instaloader/4.15.1/test_package/MANIFEST.yml` — 声明测试边界与断言数量。

## 验证结果

- **编译状态**：通过
- **上游测试用例通过率**：0/0（不适用；上游 sdist 无测试套件）
- **新增测试用例通过率**：9/9（100%）
- **Conan 验证**：`conan-verify instaloader 4.15.1` 通过，G1/G2/G3/G4/L2/L4/L5 通过
- **W3 本地 CI 模拟**：`build_and_test.sh instaloader/4.15.1` 通过
- **W4 独立审计**：通过，无 P0/P1 问题

## 补充说明

- 这是纯 Python setuptools 包，不引入 C/C++ 编译依赖。
- `requests>=2.25` 在 Conan `package()` 阶段安装到包私有 `site-packages`；可选 `browser_cookie3` extra 不随基础包安装。
- 归档状态为 `built`，表示本地 Conan 验证和 W3 已通过，但尚未执行制品上传。
- 源码 URL 为官方 PyPI sdist，SHA256 为 `323ee2015540e627df25535703f246dc39695b71f7f04dadfe67e239dadf3b55`。
