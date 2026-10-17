- **三方库名称**：di
- **上游版本**：6.2.2.2
- **上游仓库地址**：https://downloads.sourceforge.net/project/diskinfo-di/
- **适配路径**：路径 A（基础适配）
- **使用知识库**：无

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 97 | 来源：dimathtest（45 个数学精度/转换/比较用例）+ getoptn_test（52 个选项解析用例） |
| 集成测试 | 4 | 来源：tests/localtest.sh（di --version、di -X 1、di -n /、DI_ARGS="-f SMbuvp" di -n /） |
| 其他测试 | 0 | |
| **合计** | **101** | |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 97 | 不变 | dimathtest 45/45 + getoptn_test 52/52 在 conanfile.py build() 中完整执行 |
| 集成测试 | 4 | 不变 | localtest.sh 保留全部 4 项并执行；2 项通过，2 项因 OHOS 无 /etc/mtab 失败 |
| 鸿蒙特有测试 | 4 | 新增 | OHOS 替代验证：di --version、di -?、di /、libdi consumer；用于替代 localtest.sh 中依赖 /etc/mtab 的 2 项检查 |
| **合计** | **105** | **+4** | |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：99/101（98.0%，2 项为 di -n / 和 DI_ARGS="-f SMbuvp" di -n /，因 OHOS 无 /etc/mtab 输出为空）
- 新增测试用例通过率：4/4（100%），覆盖 di --version、di -?、di /、libdi consumer 链接/API 调用测试

## 补充说明

- di 是一个轻量 C/CMake 磁盘信息工具库，构建使用 CMake，设置 `DI_USE_MATH=DI_INTERNAL` 避免可选 GMP/libmpdec/libtommath 依赖
- ELF NEEDED：di → libdi.so + libc.so；libdi.so → libc.so，无额外运行时依赖
- NLS 自动禁用（_enable_nls=0），无需 msgfmt 构建工具
- 无第三方 Conan 前置依赖，路径 A（基础适配）
- 分支信息：feat/di-6.2.2.2  →  di-6.2.2.2
- 替代验证原因：OHOS 无 Linux /etc/mtab，导致上游 localtest.sh 中依赖挂载表输出非空的 2 项检查无法原样通过（di -n / 和 DI_ARGS="-f SMbuvp" di -n /）
- 本 PR 不修改上游测试，不将替代验证计入上游通过率
- 替代验证单独统计为 4/4（100%），仅作为 OHOS 平台基础功能验证
- 上游测试仍如实记录为 99/101（98.0%），不能写 100%
