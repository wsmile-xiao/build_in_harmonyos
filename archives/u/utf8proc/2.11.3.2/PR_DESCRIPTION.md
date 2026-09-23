- **三方库名称**：utf8proc
- **上游版本**：v2.11.3
- **上游仓库地址**：https://github.com/JuliaStrings/utf8proc
- **适配路径**：路径 A（基础适配）
- **使用知识库**：无

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 8 | CTest: case/custom/iterate/misc/printproperty/valid/maxdecomposition/charwidth |
| 集成测试 | 2 | CTest 数据驱动: graphemetest/normtest，数据由 CMake configure 从 unicode.org 下载 |
| 其他测试 | 0 | |
| **合计** | **10** | `ctest --output-on-failure` 全部执行 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 8 | 不变 | 上游测试原样保留并在 `build()` 中执行 |
| 集成测试 | 2 | 不变 | 上游测试原样保留并在 `build()` 中执行 |
| 鸿蒙特有测试 | 1 | 新增 | test_package 消费者测试，共 11 个真实 API 断言 |
| **合计** | **11** | **+1** | |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改

> 上游 10 个 CTest 测试及 Unicode 数据文件均未修改，`build()` 通过 `ctest --output-on-failure` 原样执行。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试

> test_package 是消费者视角的安装产物验收，调用 version、NFC、iterate、grapheme_break 和 property API，不替代上游测试。

## 验证结果

- 编译状态：待本 PR OpenDesk/CI 重新验证
- 上游测试用例通过率：待本 PR OpenDesk/CI 重新验证；同源码 2.11.3.1 recipe 已实测 10/10
- 新增测试用例通过率：待本 PR OpenDesk/CI 重新验证

## 补充说明

- 适配版本为 `2.11.3.2`，源码仍使用上游 `v2.11.3`，未修改上游源码或测试。
- 本版本收敛为与 `2.11.3.1` 相同的 CMake/CTest 路径，并保留官方源码 sha256 不变。
- `generate()` 保留 OHOS SDK LLVM lib 注入；`build()` 测试阶段额外把构建目录加入 `LD_LIBRARY_PATH`，避免动态库加载失败。
- 本机无法替代 OHOS aarch64 真机验证，最终结果以 OpenDesk/CI 日志为准。
