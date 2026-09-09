## PR 信息

- **三方库名称**：gnome-autoar
- **上游版本**：0.5.2
- **上游仓库地址**：https://gitlab.gnome.org/GNOME/gnome-autoar
- **适配路径**：路径 A（基础适配） / 路径 B（贡献创新）
- **使用知识库**：`conan-meson-windows-cross-posix-prefix`、`conan-cmakedeps-relocated-prefix-consumer-matrix`、`ohos-elf-native-signer-selfsign`、`E6338-draft-2301_80739235`

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 22 | 来源：`tests/meson.build` 的 `test-extract-unit`，目标 TAP 清单 `1..22` |
| 集成测试 | 0 | OHOS 配置跳过依赖不可用的异步/环境相关入口；不计入目标清单 |
| 其他测试 | 0 | 无其他独立上游入口 |
| **合计** | **22** | 清单证据：`reports/upstream-inventory.txt` |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|---------------:|------------|------|
| 单元测试 | 22 | 不变 | 同一 `test-extract-unit` 目标清单，22/22 |
| 集成测试 | 0 | 不变 | 无额外上游集成入口 |
| 鸿蒙特有测试 | 10 | +10 | `test_package/test.c` 的消费者压缩、ZIP metadata 与回调断言 |
| **合计** | **32** | +10 | 上游 22 + 消费者 10 |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [ ] **否**，未修改上游任何测试用例
- [x] **是**，存在对上游测试用例的修改（请在下方逐条说明）

1. `patches/0002-skip-unavailable-ohos-tests.patch`：在 OHOS 目标上关闭依赖不可用平台能力的入口，保留 `test-extract-unit` 完整目标清单。
2. `patches/0003-install-upstream-test-for-ohos.patch`：安装目标上游测试二进制，供真实设备执行。
3. 官方 `tests/files` fixture 归档和原始源码保持不变；symlink 仅在任务私有 W3 fixture 准备阶段恢复。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

补全范围是 Conan `test_package` 的真实消费者：调用 gnome-autoar API 创建 ZIP，检查库注册、格式/filter、扩展名/MIME、同步完成/error 回调和生成归档文件属性。新增文件为 `test_package/test.c`、`test_package/meson.build` 与 `test_package/MANIFEST.yml`。

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：22/22（100%）
- 新增测试用例通过率：10/10（100%）

本地 `conan create` r16 RC 0，日志 SHA-256 `624aafdbb4203e04feae7cff3a6839ed408f4a76e2f2df3e9f8de53f7e8c9643`。同一 W3 `w3-r001` 单次 launch 在 `10.62.150.125:8022` 完成上游 22/22（2 个明确 crypto backend SKIP）和消费者 10/10，release/postrelease PASS。目标结果 SHA-256 `f52f1b7d46b5f0bb0aea75d7d701e880ac62467b390b1905f56d08efb174916a`。

## 补充说明

- **关联 Issue**：#2776
- **队伍名称**：天天开心
- **申请人显示标识**：2301_80739235
- **源分支**：2301_80739235:feat/gnome-autoar-0.5.2
- **目标分支**：OpenHarmonyPCDeveloper/build_in_harmonyos:main
- **其他说明**：Issue #2776 已唯一 OPEN，当前候选为 `dfe3d3ac77fa7afa801d0a7223122e63f43802c3`。HD1-HD4 均 `matched=false`，分类为路径 A+B；知识查重后新增 `E6338-draft-2301_80739235`。平台 AI Review 和 CI 结果以创建 PR 后的当前 HEAD 权威回读为准，CI PASS 前不提审。
