- **三方库名称**：strict-variant
- **上游版本**：v0.5
- **上游仓库地址**：https://github.com/cbeck88/strict-variant
- **适配路径**：路径 B（贡献创新）
- **使用知识库**：openharmony-compile-agent；复用 E195、E035/E099、E413；新增 `DRAFT-strict-variant-0.5-nested-source-selection`

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 33 | `test/`：`variant.cpp` 27、`compare.cpp` 2、`hash.cpp` 2、`alloc.cpp` 1、可选 `spirit.cpp` 1；其中 spirit 在本设备按上游条件预期 SKIP，不计为 PASS |
| 集成测试 | 0 | 上游没有独立集成测试 |
| 其他测试 | 2 | `tutorial_basic.cpp`、`tutorial_advanced.cpp` 两个上游示例可执行目标 |
| **合计** | **35** | 7 个上游目标库存；OHOS 实际执行 6 个，1 个 optional spirit 目标有据跳过 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 33 | 不变 | 32 个注册单元用例全部通过；`spirit` 1 个目标因缺少 Boost 头文件按上游条件 SKIP |
| 集成测试 | 1 | +1 | `test_package` 真实通过 CMakeDeps 发现、编译、链接并运行消费者 |
| 鸿蒙特有测试 | 0 | 不变 | 无需伪造 OHOS 专有行为；设备矩阵和工具链事实在验证记录中给出 |
| 其他测试 | 2 | 不变 | 两个上游 tutorial 目标均执行通过 |
| **合计** | **36** | **+1** | 库测试库存 35 + 1 个消费者测试；实际终态为 35 个目标 PASS、1 个目标 expected SKIP |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改

配方只复现 `test/Jamroot.jam` 的编译选项。由于设备 Clang 15 对两项已定位的
上游诊断与 `-Werror` 不兼容，仅对 `deprecated-copy-with-user-provided-copy`
和 `return-type` 使用 `-Wno-error`；未改测试源码、注册项或断言。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试

`test_package` 是独立的 Conan 消费者集成门禁，不替代或改写上游测试。

## 验证结果

- 编译状态：通过（HarmonyOS PC arm64，OHOS 6.0，clang 15.0.4，Conan 2.29.1）
- 上游测试用例通过率：32/32 注册单元用例通过；2/2 tutorial 目标通过；`spirit.cpp` 1/1 为上游条件 expected SKIP（缺少 `/usr/include/boost/version.hpp`），没有把 SKIP 写成 PASS
- 新增测试用例通过率：1/1（100%，8 个消费者断言）

官方入口 `bash test/run_tests.sh` 实际返回：`Require b2 or bjam but it was not found. Aborting.`
这是设备未安装上游 Boost.Build 执行器的工具限制。随后按 `test/Jamroot.jam` 的
原始参数直接编译和运行 6 个默认目标，结果为 6/6 PASS。首次严格 `-Werror`
失败的具体诊断为 `test/variant.cpp:1035,1049` 经
`include/strict_variant/variant.hpp:148` 实例化的 deprecated copy warning，
以及 `test/tutorial_basic.cpp:156` 的 return-type warning；仅降级这两项后通过。

## 补充说明

- 构建方式：header-only / custom；打包 28 个 `.hpp` 和 `LICENSE`，无 `bin/`、`lib/`，不创建 `commands.json`。
- 无源码补丁；官方归档 `include/strict_variant/version.hpp` 的宏值仍为 `0.4.0`，按上游 v0.5 tag 原样保留，Conan 版本仍为任务指定的 `0.5`。
- `conan-verify` G1/G2/G3/L2/L4/L5 通过；其 G4 正则不能提取带连字符的 package ID，已用完整 Conan package reference 手工复核头文件、许可证和空 lib 目录边界。
- 定向 zsh CI 门禁：`L0_RESULT=pass`、`L1_RESULT=pass`、`L4_RESULT=pass`；`L2` 因无 `bin/` 按规则 skip，`L5` 因无 `bin/lib` 仅告警。
- 路径 B 新增知识草稿：`knowledge/drafts/DRAFT-strict-variant-0.5-nested-source-selection.kv` 及配套说明，主题是顶层 header-only 公共目录优先于无关嵌套 benchmark 的源码选择，以及完整 upstream inventory / expected SKIP 计数。
- 路径 B Issue 将与本 PR 互链提交；最终编号、CI 和 AI Review 以远端最新提交为准。
