- **三方库名称**：plfit
- **上游版本**：0.9.6
- **上游仓库地址**：https://github.com/ntamas/plfit
- **适配路径**：路径 A（基础适配）
- **使用知识库**：openharmony-compile-agent（E298/E529 条目；zxcvbn-c 2.6 的 OHOS libm 处理先例）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 9 | 来源：上游 `test/` 目录 CTest 注册（test_discrete / test_continuous / test_real / test_sampling / test_underflow_handling / test_xmin_too_low / test_hzeta / test_kolmogorov / test_gss） |
| 集成测试 | 0 | 上游无独立集成测试 |
| 其他测试 | 1 | `test/test_python_module.py`（SWIG Python 绑定测试；本配方不构建 Python 模块，未计入运行数） |
| **合计** | **9（可运行）** | 数据驱动，测试数据在 `data/` 随源码分发 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 9 | 不变 | 上游 9 项 CTest 在 `conan create` 内全量执行，无跳过 |
| 集成测试 | 0 | 不变 | 上游无独立集成测试 |
| 鸿蒙特有测试（消费者用例） | 2 | 新增 | OHOS 平台产物消费者验证：`test_package/test.c` C 消费者 API 测试（11 项检查：调用 `plfit_rzeta`/`plfit_rpareto` 生成确定性样本，回拟合断言 alpha/xmin/D/L，另测 `plfit_moments` 与版本头）+ `test_package/test.sh` CLI 冒烟测试（8 项检查：运行打包的 `plfit`/`plgen` 生成 2000 样本并回拟合校验 alpha 区间） |
| **合计** | **11** | **+2** | 上游 9 + 鸿蒙消费者用例 2 |

## 上游测试用例修改说明

- [x] **否**，未修改上游任何测试用例

## 补全测试用例说明

- [x] **否**，上游已有测试用例覆盖（9 项 CTest 全量执行、全部通过）

> 适配新增 `test_package/` 消费者测试（补充验证，不替代上游测试）：
> 1. `test_package/test.c` — 调用 `plfit_rzeta`/`plfit_rpareto` 生成确定性样本并用 `plfit_discrete`/`plfit_continuous` 回拟合（断言 alpha/xmin/D/L），另测 `plfit_moments` 与版本头（11 项检查）
> 2. `test_package/test.sh` — 运行已打包的 `plfit`/`plgen` CLI：生成 2000 样本 → 拟合 → 校验输出格式与 alpha 区间（8 项检查）

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：9/9（100%）（`ctest --output-on-failure`，在 `conan create` 内执行）
- 新增测试用例通过率：19/19（100%）（C 消费者 11/11 + CLI 冒烟 8/8）
- 本地 CI 门禁：L0 / L1(a-c) / L1e / L4 / L5 全部通过；W3 本地 CI 模拟通过（`.ci-result.json` exit_code=0）
- W4 独立审计：verdict=pass（0 P0 / 0 P1；4 条 P3 非阻断建议）

## 补充说明

- **适配要点**：
  1. OHOS sysroot 无独立 `libm.so`（数学函数在 libc 中），CMake `FIND_LIBRARY(MATH_LIBRARY NAMES m)` 在 HarmonyOS 平台返回 NOTFOUND 并污染全部链接行；补丁 `0001-CMakeLists.txt.patch` 在 NOTFOUND 时空置该变量（zxcvbn-c 2.6 同款先例，无平台宏注入）。
  2. 上游 `install(TARGETS plfit LIBRARY ...)` 只声明动态库 artifact kind，默认静态构建不会安装 `libplfit.a`；补丁 `0002-src-CMakeLists.txt.patch` 追加 `ARCHIVE DESTINATION`。
- **依赖**：无第三方依赖（仅 C 运行库）。
- **已知限制**：
  1. SWIG Python 绑定未构建（`PLFIT_COMPILE_PYTHON_MODULE=OFF`，OHOS 无 SWIG 依赖链）；
  2. `plfit -p exact` 精确 p 值需约 2500 次重采样，耗时较长（上游行为，测试均使用默认 SKIP）。
- **产物**：`lib/libplfit.a`、`include/plfit/*.h`（5 个）、`lib/pkgconfig/libplfit.pc`、`bin/plfit`、`bin/plgen`（commands.json 已在软件级声明）。
