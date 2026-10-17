- **三方库名称**：trimal（trimAl）
- **上游版本**：v1.5.1
- **上游仓库地址**：https://github.com/inab/trimal
- **适配路径**：路径 A（基础适配）
- **使用知识库**：无（首次适配；零源码补丁、测试原样复用上游 dataset 回归，未使用知识库处方）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 上游无 tests/ 目录、无 ctest/pytest 注册、Makefile 无 check 目标 |
| 集成测试 | 504 | 来源：.github/workflows/build.yml 的 test job —— scripts/generate_trimmed_msas.sh + scripts/compare_trimmed_msas.sh（84 个 dataset 比对输入 × 6 种修剪模式，逐一 diff dataset/trimmed_msas/ 参考输出） |
| 其他测试 | 0 | — |
| **合计** | **504** | |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 不变 | 上游无单元测试 |
| 集成测试 | 504 | 不变 | 同一套上游 dataset 回归已集成进 conanfile.py 的 build()，conan create 时自动复跑；实机 504/504 通过 |
| 鸿蒙特有测试 | 10 | 新增 | test_package 消费者断言，运行于 HarmonyOS PC aarch64，调用安装后的 trimal/readal/statal |
| **合计** | **514** | **+10** | |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

上游 `scripts/generate_trimmed_msas.sh` 与 `scripts/compare_trimmed_msas.sh` 原样执行，内容零改动；仅以 bash 显式解释器运行（脚本无 shebang，且 OHOS /system/bin/sh 不能执行 ELF）。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无单元测试用例，适配后补全了消费者/边界测试（请在下方说明）

- **补全的测试范围**：打包后二进制的消费者视角调用路径，共 10 项断言
- **补全原因**：上游 dataset 回归只覆盖 trimal 主程序的正常路径；仓库无单元测试框架，也未覆盖 readal/statal 与失败路径
- **新增测试文件清单**：
  1. `test_package/test.sh` —— 10 项断言：版本冒烟；`-nogaps`/`-gt 0.6` 期望输出逐字节 diff；缺失输入负向控制（非零退出 + ERROR）；`readal -info` 统计；`statal -sgc` 列缺口率
  2. `test_package/tiny.fasta`、`test_package/expected_nogaps.fasta`、`test_package/expected_gt.fasta` —— 手工核对的小型比对夹具与期望输出

## 验证结果

- 编译状态：通过（本地 conan-verify G0–G4 + L2/L4/L5 全部 PASS；W3 本地 CI L0/L1/L1e/L2/L4/L5 PASS；平台 CI 结论以 PR 页面为准）
- 上游测试用例通过率：504/504（100%）
- 新增测试用例通过率：10/10（100%）

## 补充说明

- 零源码补丁：手写 Makefile 通过 `make CC=<tools.build:compiler_executables.cpp> -j1` 覆盖编译器（R33），无 `__OHOS__` 注入、无 `patches/`。
- 上游回归套件已集成进 `conanfile.py` 的 `build()`，因此平台 CI 的 `conan create` 会复跑 504 用例（本地实测约 20 分钟，默认 3600s 预算内）。
- `test_package/test.sh` 在私有临时目录中运行：Conan 在本地路径场景会就地在 test_package 目录执行脚本，避免测试产物写入配方树。
- 上游 `-gt V` 的实际语义为“删除缺口比例 > (1-V) 的列”（main.cpp: `gapThreshold = 1 - atof(argv[i])`，与帮助文本字面相反），该行为已被 dataset 参考输出固化，适配未做改动。
- 交付二进制：`bin/trimal`、`bin/readal`、`bin/statal`；release 包：`packaging/trimal-1.5.1-ohos-aarch64.tar.gz`。
