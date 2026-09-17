- **三方库名称**：miniupnpc
- **上游版本**：v2.3.3
- **上游仓库地址**：https://github.com/miniupnp/miniupnp
- **适配路径**：路径 A（基础适配）
- **使用知识库**：无

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 5 | `validateminixml`、`validateupnpreplyparse`、`validateportlistingparse`、`validateigddescparse1`、`validateigddescparse2` |
| 集成测试 | 2 | `validateminiwget` 使用源码树内置 loopback HTTP 服务；`validateaddr_is_reserved` 验证地址分类行为 |
| 其他测试 | 0 | 上游没有其他测试 |
| **合计** | **7** | `UPNPC_BUILD_TESTS=ON` 时由上游 CMake/CTest 注册 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 5 | 不变 | 上游测试原样执行 |
| 集成测试 | 2 | 不变 | loopback 测试不依赖外部网关或 Internet |
| 鸿蒙特有测试 | 1 | 新增 | `test_package` 调用 `ParseNameValue()` 与 `GetValueFromNameValueList()` 验证安装产物 |
| **合计** | **8** | **+1** | |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

## 验证结果

- 编译状态：待本 PR 的 OpenDesk/CI 验证
- 上游测试用例通过率：待本 PR 的 OpenDesk/CI 验证（7/7）
- 新增测试用例通过率：待本 PR 的 OpenDesk/CI 验证（1/1）

## 补充说明

- 适配版本为 `2.3.3.1`，源码仍使用上游 `miniupnpc_2_3_3`，未修改上游源码或测试。
- `generate()` 已启用 `UPNPC_BUILD_TESTS=ON`，`build()` 执行全部 7 个上游 CTest。
- 消费者测试使用固定 SOAP 响应解析，不依赖外部 UPnP 网关。
