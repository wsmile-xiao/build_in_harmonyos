## PR 信息

- **三方库名称**：geogram
- **上游版本**：1.10.1
- **上游仓库地址**：https://github.com/BrunoLevy/geogram
- **适配路径**：路径 A（基础适配） / 路径 B（贡献创新）
- **使用知识库**：E549；HMDFS executable mode semantic readback；OHOS ELF native signer

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 11 | `src/tests` 中可在 Windows MinGW host 复现的 11 个可执行测试，清单见 `evidence/upstream-test-inventory.txt` |
| 集成测试 | 0 | 上游 RobotFramework 场景需要未随 release asset 发布的数据目录，未将缺失数据伪装为通过 |
| 其他测试 | 0 | `test_locks` 的 MinGW 线程测试和 `test_geofile` 的超大文件测试保留在排除证据，见 `evidence/upstream-test-exclusions.md` |
| **合计** | **11** | 完整执行并通过 `11/11`，原始日志见 `evidence/upstream-tests.log` |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|---------------:|------------|------|
| 单元测试 | 11 | 不变 | 上游 host 测试保持原样执行 |
| 集成测试 | 0 | 不变 | release asset 未提供 RobotFramework 数据闭包 |
| 鸿蒙特有测试 | 1 | +1 | `test_package/test_package.cpp` 通过 `geogram::geogram` 调用 `GEO::initialize` 与 `GEO::vec3` |
| **合计** | **12** | +1 | 新增消费者测试与目标机运行证据绑定在 `evidence/w3-run-003` |

---

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改

没有改动 release asset 中的 `src/tests` 或 RobotFramework 场景；只为 host 验证生成了任务私有最小输入文件。

---

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无可直接验证的 Conan consumer 入口，适配后补全了测试

新增 `test_package` 使用真实 Geogram API 编译并链接，目标端 AArch64 consumer 在 `run-003` 返回 `RUN_RC=0`。

---

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：11/11（100%）
- 新增测试用例通过率：1/1（100%）

本地 MinGW 静态构建和 consumer 均返回 0；目标端 `10.62.150.125:8022` 完成 exact-byte transfer/readback、AArch64 shared library 生成、原生 `binary-sign-tool -selfSign 1` 重签、消费者编译和唯一运行，`run-003` 的 `RESULT_FROZEN`、释放和 `POSTRELEASE_PASS` 收据链完整。HMDFS 将产物模式投影为 770，最终可加载性以目标消费者真实返回值为准。

---

## 补充说明

- 关联 Issue：#2743（https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/2743）
- 队伍名称：天天开心
- 申请人显示标识：2301_80739235
- 源分支：2301_80739235:feat/geogram-1.10.1
- 目标分支：OpenHarmonyPCDeveloper/build_in_harmonyos:main
- 其他说明：上游 release asset `geogram_1.10.1.tar.gz`（SHA-256 `30033340a0dfd86f9e15a8ffdd7c1e6d49b967d3f26fb96cf3dfd1a502d8eba2`）包含 vendor 源码，W0 无 Conan 依赖。补丁新增 `OHOS-clang` 平台配置，复用 Linux clang 选项但不带 x86-only `-m64`；OHOS recipe/test recipe 对构建与安装过程使用任务内 `umask(0)` 以适配 HMDFS 创建权限，安装后的非链接 `.so` 使用设备原生 signer 重签。平台 CI/AI Review/提审状态以当前 HEAD 的远端权威回读为准。
