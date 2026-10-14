## PR 信息

- **三方库名称**：chromaprint
- **上游版本**：1.6.1
- **上游仓库地址**：https://github.com/acoustid/chromaprint
- **适配路径**：路径 A（基础适配） + 路径 B（贡献创新）
- **使用知识库**：E545-draft-CP11；参考 E332

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 99 | library-only CMake完整注册；91个tests/和8个src/用例 |
| 集成测试 | 0 | 本配置无其他注册集成用例 |
| 其他测试 | 0 | fpcalc/FFmpeg范围未交付，上游BUILD_TOOLS=OFF不注册 |
| **合计** | **99** | 发布源码注册与实际CTest逐名相等 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|---------------:|------------|------|
| 单元测试 | 99 | 不变 | 全量CTest，无跳过 |
| 集成测试 | 0 | 不变 | API与平台检查在一个消费者中，不重复计 |
| 鸿蒙特有测试 | 1 | +1 | 实际PCM指纹API、OHOS uname及TMPDIR持久化往返，一个程序26断言 |
| **合计** | **100** | **+1** | 26个断言不重复计为26程序 |


---

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

未改上游任何测试断言或数据；环境修复仅覆盖构建后发现所需路径。

---

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

新增 test_package/test_chromaprint.c 与 MANIFEST.yml，验证实际库及OHOS平台行为，不替代上游测试。

---

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：99/99（100%）
- 新增测试用例通过率：1/1（100%）

正式 chromaprint-finish-20261011-r2 的 conan-verify 与 finish W3 本地 CI PASS；99/99和消费者1/1（26断言，75指纹项），12阶段释放完整。原W3 SHA-256 04fe2263282de7a877835981632112030a915d6845890a9408df2bf042dd185b。总finish RC1仅为旧后置readiness/staging，不宣称整个流程成功；比赛worker CI尚未触发。

---

## 补充说明

- 关联 Issue：#3908
- 队伍名称：诶，云朵
- 申请人显示标识：2501_91199785
- 源分支：OpenHarmonyPCDeveloper:feat/chromaprint-1.6.1
- 目标分支：OpenHarmonyPCDeveloper/build_in_harmonyos:main
- 其他说明：全局 BUILD_SHARED_LIBS 把 bundled GoogleTest 编为共享库，gtest_discover_tests 在 cmake --build 的构建后阶段就执行测试程序。Conan VirtualRunEnv 仅包含外部依赖，不自动含 build/lib；仅设置 ctest 环境太晚。修复是在 cmake.build 前加入任务私有 src/lib 输出目录并保留外部依赖环境，不关闭测试、不改系统加载器。 任务#15049本人已领取，依赖活动显示5火种；B候选以审核为准；HD1–HD4否定。仅库与FFTW、不含CLI。合并后/release。
