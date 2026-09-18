- **三方库名称**：libredwg
- **上游版本**：0.13.3
- **上游仓库地址**：https://www.gnu.org/software/libredwg/
- **适配路径**：路径 A（基础适配）
- **使用知识库**：E007（--host/--build）、E011（umask 077→022）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 326 | 来源：test/unit-testing（check_minimal 8 + testobjects 245 + testdebug 72 + check-objects.pl） |
| 集成测试 | 0 | test-data 大 DWG 不作为 automake TESTS |
| 其他测试 | 0 | |
| **合计** | **326** | |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 326 | 不变 | 配方 `make -C test/unit-testing check`（`--enable-debug`） |
| 集成测试 | 0 | 不变 | |
| 鸿蒙特有测试 | 1 | 新增 | test_package：is_dwg_entity(LINE) + dwg_read_file 缺文件 |
| **合计** | **327** | **+1** | |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

鸿蒙特有测试为 Conan 消费者契约。

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：待真机实跑 326/326（配方已接入 `make -C test/unit-testing check`）
- 新增测试用例通过率：1/1（100%）

## 补充说明

- `--enable-debug` 含 testdebug；MAKEINFO=true
- 验证命令：`conan create archives/l/libredwg/0.13.3 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing`
