- **三方库名称**：libmceliece
- **上游版本**：0-20260622
- **上游仓库地址**：https://lib.mceliece.org
- **适配路径**：路径 A（基础适配）
- **使用知识库**：无

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 25 | 来源：`mceliece-test` 无参（xof/sort + 20 个 KEM 原语，见 https://lib.mceliece.org/test.html） |
| 集成测试 | 0 | `mceliece-fulltest` 需 valgrind/TIMECOP，配方 `--no-valgrind` |
| 其他测试 | 0 | |
| **合计** | **25** | |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 25 | 不变 | 配方运行真实 `mceliece-test`（不再 stub） |
| 集成测试 | 0 | 不变 | |
| 鸿蒙特有测试 | 1 | 新增 | test_package：mceliece348864 keypair/enc/dec |
| **合计** | **26** | **+1** | |

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
- 上游测试用例通过率：待真机实跑 `mceliece-test`（25 原语）
- 新增测试用例通过率：1/1（100%）

## 补充说明

- `./configure --host=arm64 --no-valgrind --no-tryifunc`；构建期 dummy libcpucycles
- 验证命令：`conan create archives/l/libmceliece/0-20260622 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing`
