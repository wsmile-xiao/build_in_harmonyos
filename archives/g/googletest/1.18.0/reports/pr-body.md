## PR 信息

- **三方库名称**：googletest
- **上游版本**：1.18.0（官方 tag `v1.18.0`，commit `063de7e9578f82b369302001269680b4b1553359`）
- **上游仓库地址**：https://github.com/google/googletest
- **适配路径**：路径 A（基础适配）+ 路径 B（贡献创新）
- **使用知识库**：openharmony-compile-agent；E2189 Windows Conan OHOS toolchain closure

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 63 | OHOS CTest inventory from `archives/g/googletest/1.18.0/reports/upstream-inventory-ohos-w3-run-003.json` |
| 集成测试 | 0 | Upstream inventory has no separate integration group |
| 其他测试 | 0 | No additional upstream group in the frozen inventory |
| **合计** | **63** | Complete OHOS target CTest inventory |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 63 | 不变 | OHOS W3 completed the target inventory at 63/63 |
| 集成测试 | 0 | 不变 | No separate integration group |
| 鸿蒙特有测试 | 1 | 新增 | The separate Conan consumer passed 1/1 on the OHOS target |
| **合计** | **64** | **上游 63 + 鸿蒙特有 1** | No target-platform upstream test count reduction |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **是**，存在对上游测试用例的修改（请在下方逐条说明）
- [ ] **否**，未修改上游任何测试用例

- `googletest/src/gtest_help_test.py`：HarmonyOS 的 `uname` 返回值为 `HarmonyOS`，但该测试的 POSIX 选项行为与 Linux 一致；补丁只调整平台分支判定。
- `googletest/src/gtest-port.cc`：`CapturedStream` 在 OHOS 沙箱中不能写 `/tmp`；补丁改为优先使用 `TMPDIR`，保留 `/tmp/` 回退。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

上游 CTest 清单已完整执行；test_package 仅验证真实 Conan API 链接，不改变上游测试分母。

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：63/63（100%）
- 新增测试用例通过率：1/1（100%）

新增测试为独立 OHOS Conan consumer。

## 补充说明

- **关联 Issue**：#2651；当前 PR：#8439。
- **队伍名称**：天天开心
- **申请人显示标识**：@2301_80739235
- **源分支**：feat/googletest-1.18.0
- **目标分支**：main
- OHOS 交叉构建使用官方 `ohos.toolchain.cmake`、Ninja 和 `OHOS_ARCH=arm64-v8a`；r10 完成 161/161 构建目标并打包四个静态库，test_package 成功配置、编译和链接。
- Windows 主机上完成 62/62 上游 CTest 与 3/3 consumer tests。OHOS 真机 W3 run-003 唯一 launch 后完成 63/63 上游 CTest、1/1 consumer、68/68 自签制品，并通过 release/postrelease validator。
- 原始 recipe HEAD `d7d645f68487e7706c36fd4d045a7d7dcbb21702` 的平台 AI Review 报告“未发现问题”；本次只更新验证证据和知识文档，新完整 HEAD 仍需重新回读 AI Review。CI #40561 在源码下载前因 worker 缺少 `curl` 和 Python SSL 支持失败；新的当前完整 HEAD CI 必须 PASS 后才提审。
