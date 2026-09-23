## PR 信息

- **三方库名称**：mapbox-variant
- **上游版本**：v1.2.0
- **上游仓库地址**：https://github.com/mapbox/variant
- **适配路径**：路径 A（基础适配）+ 路径 B（贡献创新）
- **使用知识库**：E1000-draft-A1B2（header-only Conan 接口目标与上游标志隔离）

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 97 | `make -j2 test` 的 90 个 Catch 用例与 7 个预期编译失败用例 |
| 集成测试 | 0 | 上游仓库没有独立集成测试入口 |
| 其他测试 | 0 | 无其他上游测试入口 |
| **合计** | **97** | 清单见任务证据 `reports-upstream-inventory.txt`，入口数为 2 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|---------------:|------------|------|
| 单元测试 | 97 | 不变 | 保留上游 Catch 与编译失败测试 |
| 集成测试 | 0 | 不变 | 该 header-only 库无独立运行时集成测试 |
| 鸿蒙特有测试 | 7 | +7 | CMake consumer 验证 variant、get、is、apply_visitor 与异常语义 |
| **合计** | **104** | +7 | Conan test_package consumer 真实调用被测头文件 API |

---

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

---

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

---

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：2/2（100%）
- 新增测试用例通过率：7/7（100%）

- 上游 `make -j2 test`：90 个 Catch 测试用例、654 个断言全部通过；编译失败脚本 7/7 全部符合预期。
- 本地 Conan `conan create`：6 个头文件和 2 个许可证文件打包，CMake consumer 执行 7 项断言通过。
- W0：无外部 Conan 依赖，目标二进制闭包为空。
- W3：`10.62.150.125:8022` 上唯一 launch 的自签 ELF 返回 0，7 项 consumer 断言通过，after-pass CLEAN_EXIT，release/postrelease PASS；证据 run_id 为 `mapbox-variant-1.2.0-w3-r001`。
- 平台 CI：将以当前提交 HEAD 的精确证据回读；平台 CI PASS 后才执行一次提审。

---

## 补充说明

- 关联 Issue：#2638
- 队伍名称：天天开心
- 申请人显示标识：2301_80739235
- 源分支：2301_80739235:feat/mapbox-variant-1.2.0
- 目标分支：OpenHarmonyPCDeveloper/build_in_harmonyos:main
- 其他说明：header-only recipe 仅复制公开头文件和许可证，显式导出 `mapbox::variant` CMake interface target；上游 `-march=native` 未进入 OHOS Conan 配方。知识查重覆盖 knowledge/graph、knowledge/drafts、knowledge/doc、knowledge/operations，结果与当前候选证据绑定。
