## PR 信息

- **三方库名称**：scdoc
- **上游版本**：1.11.3
- **上游仓库地址**：https://git.sr.ht/~sircmpwn/scdoc
- **适配路径**：路径 A（基础适配） + 路径 B（贡献创新）
- **使用知识库**：openharmony-compile-agent；E2171 OHOS target execution needs signer, mode, and exact-marker closure；E2177 OHOS CI workers may lack a host compiler；E2178 OHOS target linker runtime libraries need compiler-relative LD_LIBRARY_PATH

本 PR 为 `scdoc` 1.11.3 增加 OpenHarmony PC aarch64 Conan 配方、命令行工具元数据和消费者测试入口。配方保留上游 Make 构建与 `make check`，并把 Windows host 的工具链绑定、host generator 与 OHOS target ELF 的边界显式化；当平台 worker 没有宿主编译器时，使用与上游输入绑定的预生成 man 页面完成打包。

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 44 | `test/` shell cases invoked by `make check` |
| 集成测试 | 0 | 上游未提供独立集成套件 |
| 其他测试 | 0 | 无 |
| **合计** | **44** | 完整清单见 `archives/s/scdoc/1.11.3/reports/upstream-test-inventory.txt` |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 44 | 不变 | 上游 `make check` 完整通过 |
| 集成测试 | 0 | 不变 | 无新增独立集成套件 |
| 鸿蒙特有测试 | 1 | 新增 | 真机 signed ELF consumer 生成 man page |
| **合计** | **45** | **+1** | 44 项上游测试加 1 项目标机消费者验证 |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

上游测试源码和断言未修改。MinGW `%F` 与 Windows `find.exe` 差异仅通过验证目录 shim 隔离，未进入配方或上游测试提交。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

消费者测试用于验证目标平台打包和执行闭包，不是对上游缺失测试的补全。

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：44/44（100%）
- 新增测试用例通过率：1/1（100%）

W3 r004 在 `10.62.150.125:8022` 完成唯一 launch，目标退出码为 0、stderr 为 0、输出为 338 字节且生成 `.TH "scdoc" "1"`，使用目标机 native self-sign 并完成 postrelease PASS。r001-r003 的失败证据均已独立冻结并释放，不与 r004 拼接。

## 补充说明

- **关联 Issue**：#2639（https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/2639）
- **队伍名称**：天天开心
- **申请人显示标识**：2301_80739235
- **源分支**：feat/scdoc-1.11.3
- **目标分支**：main
- **发布边界**：合并后按平台流程执行 `/release` 发布到 ohpcd；PR 阶段不上传制品。
