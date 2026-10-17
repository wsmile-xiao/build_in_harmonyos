# medianfilter 1.0.0 适配笔记

## 编译环境
- 构建系统: makefile（上游 Makefile，仅构建测试/示例；配方改为直接编译静态库 + 三个测试可执行文件）
- 编译日期: 2026-09-28
- 编译器: clang 15.0.4 / clang++（OHOS arm64, /data/service/hnp/bin/clang）
- Conan: 2.29.1（OHOS 适配版）
- 状态: published

## 编译步骤

```bash
# init-build（下载/解压/骨架）
python3 scripts/ohc-run.py init-build medianfilter 1.0.0 --url https://github.com/accabog/MedianFilter/archive/refs/tags/v1.0.0.tar.gz --auto
# 官方 v1.0.0 tarball SHA-256（已核验）
#   cd38d8e811a29384b108bb244d7ba9e71532f2e682eb7dfea747a469149db280

# 配方构建 + 上游测试 + test_package（2/2 ctest 通过）
conan create . -pr:h ohos-aarch64 -pr:b ohos-aarch64 --build=missing

# 鸿蒙专项测试（test_ohos，6/6 断言通过）
conan test archives/m/medianfilter/1.0.0/test_ohos medianfilter/1.0.0 -pr:h ohos-aarch64 -pr:b ohos-aarch64

# 消费者验证（独立业务用例，模拟 ADC 传感器去噪上层组件）
CC=/data/service/hnp/bin/clang bash archives/m/medianfilter/1.0.0/consumer/run_consumer.sh <package_folder>
```

配方 build() 关键命令（R33：编译器来自 Conan conf）：

```bash
clang -O2 -std=c11 -Wall -Wextra -Werror -fPIC -I<src> -c <src>/MedianFilter.c -o MedianFilter.o
llvm-ar rcs libmedianfilter.a MedianFilter.o
clang  ... tests/stress_test.c MedianFilter.c -o stress_test   && ./stress_test    # 140/140
clang  ... tests/circular_test.c MedianFilter.c -o circular_test && ./circular_test  # 51/51
clang++ ... tests/test_cpp.cpp -o test_cpp                      && ./test_cpp       # 12/12
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan create 失败 `tools.build:archiver` 不存在 | 该 conf 不在 Conan 配置列表中 | 改用 `shutil.which("llvm-ar") or "ar"`（与 m1ddc/m4 等归档一致） |
| 2 | test_package 编译失败 `MedianFilter_t` 未定义 | 上游 v1.0.0 头文件实际类型名为 `sMedianFilter_t`/`sMedianNode_t`（README 中 `MedianFilter_t` 别名未在头文件中提供） | test_package/消费者改用公开的实际类型名 |
| 3 | test_ohos H2 解析失败 | llvm-readelf Data 行为 `2's complement, little endian` | awk 改为整行匹配 `little endian` |
| 4 | consumer 首满窗口断言初始值错误 | 窗口未满时上游以 0 填充槽位，warming 语义与满窗不同 | 修正断言：首满窗口 {1005,1000,4095,1002,1008} 中值=1005 |

## 源码修改

无源码修改、无补丁（纯配方/测试/交付文件，符合上游原样适配）。

## 依赖版本

无第三方编译/运行依赖（仅 `<stdint.h>`/`<cstdint>` 标准头）。

## 验证结果

### 上游测试双口径台账（source_declared_total 口径）

source_declared_total = 203；configured_executable_total = 3（stress_test / circular_test / test_cpp）；
executed_passed_total = 203，失败 0，未运行/未实例化 0。

逐项映射（源码声明 -> 构建条件 -> 构建目标 -> 注册/可执行 -> 实际运行）：

| 测试源 | 分类 | 源码声明数 | 理由 | 构建目标 | 注册项 | 实际运行 | 结果 |
|--------|------|-----------|------|---------|--------|----------|------|
| tests/stress_test.c | 独立上游用例（TEST_SUITE_BEGIN/RUN 宏） | 140 | 14 种输入模式 × 10 个窗口大小（3..99），each RUN = 1 用例 | stress_test | make test 目标，配方直接编译 | ./stress_test | 140 passed, 0 failed |
| tests/circular_test.c | 独立上游用例 | 51 | 9 个分组覆盖窗口 3..15、极端值、warmup、链完整性自检；用户测试源中的真实用例 | circular_test | 同上 | ./circular_test | 51 passed, 0 failed |
| tests/test_cpp.cpp | 独立上游用例 | 12 | C++ 模板 int/float/double × 窗口 3..21 共 6 节 × 2 模式 | test_cpp | 同上 | ./test_cpp | 12 passed, 0 failed |
| tests/test_harness.h | 框架头（宏） | 0 | 仅输出宏，不计为独立用例 | — | — | — | 不计数 |
| examples/ 01..05 | 样例 | 0 | 非测试，不计 | — | — | — | 不计数 |
| benchmarks/ | 基准 | 0 | 非测试（callgrind 基准），不计 | — | — | — | 不计数 |

全量通过率 = 203/203 (100%)；当前配置可执行集合通过率 = 203/203 (100%)。
无未实例化项（三个测试入口均被配方纳入正确构建目标并实际运行）。

### test_package（L1 官方测试）
- test_medianfilter_c: 消费者通过公开 Header + libmedianfilter.a，median(10..70, w=7)=40 -> PASS
- test_medianfilter_cpp: MedianFilter<int,5> 模板 median(1..5)=3 -> PASS
- ctest: 2/2 tests passed, 0 failed

### test_ohos（鸿蒙专项，6/6 断言）
- H1a/H1b/H1c 包结构（.a + 两个头文件）| H2 对象 ELF64 LE AArch64 |
- H3 对象无宿主构建路径字符串 | H4 端到端消费者在 OHOS 上编译链接运行并通过中值断言

### 消费者验证（独立业务用例）
- 文件: archives/m/medianfilter/1.0.0/consumer/consumer_sensor.c
- 命令: CC=/data/service/hnp/bin/clang bash run_consumer.sh <pkg>
- 调用公开 API: MEDIANFILTER_Init / MEDIANFILTER_Insert
- 验证结果: 模拟 12-bit ADC 序列中 4095/0 尖峰被窗口 5 中值滤波完全消除，
  全窗口输出落在 [1000,1010]，首满窗口中值=1005，exit 0（"ADC spike removed ... OK"）

### conan-verify（G1-G4 + L2/L4/L5 全 PASS）
G1 配方完整性 PASS / G0 预构建风险评估 / G2 conan create 干净构建 PASS /
G3 系统同名库隔离 PASS / G4 产物完整性 PASS / L2 平台功能矩阵 PASS /
L4 静态安全扫描(checksec) PASS / L5 产物基线对比 PASS。

## 交付物

| 文件 | 说明 |
|------|------|
| archives/m/medianfilter/1.0.0/conanfile.py | Conan 配方（静态库 + 上游测试 hard gate） |
| archives/m/medianfilter/1.0.0/conandata.yml | 官方 v1.0.0 URL + SHA-256 |
| archives/m/medianfilter/1.0.0/test_package/ | L1 测试（C API + C++ 模板消费者） |
| archives/m/medianfilter/1.0.0/test_ohos/ | 鸿蒙专项交付验证（6 断言） |
| archives/m/medianfilter/1.0.0/consumer/ | 独立业务消费者用例（ADC 去噪） |
| archives/m/medianfilter/1.0.0/manifest.yaml | 版本元数据 |
| archives/m/medianfilter/README.md | 软件级说明（见软件级目录） |

## 注意事项

1. 上游 v1.0.0 头文件类型名为 `sMedianFilter_t`/`sMedianNode_t`；README 提到的
   `MedianFilter_t` 别名在头文件中未提供，消费者必须用实际类型名。
2. 窗口未满时上游以 0 填充滑动窗口槽位（warmup 语义），断言需对齐该语义。
3. 库类型无 CLI 产物（仅 .a + 头文件），按 R38 不需要 commands.json。
4. 无第三方依赖（纯标准库），无 registry 解析阻塞。

## 基线隔离复验审计（baseline_isolation_audit）

W3 本地 CI（full 整仓扫描模式，git ls-files 枚举）命中 3 个**其他库**的既有基线
状态文件（均为空文件，提交前已存在于 main，不在当前库允许范围，未被我修改/提交/PR）：

| 字段 | 值 |
|------|-----|
| path × 3 | archives/c/cloog/0.21.1/.build-closed；archives/c/cloog/0.21.1/.staging-verified；archives/k/kics/2.1.20/.staging-verified |
| pre_sha256（逐文件） | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855（空文件） |
| isolation_command | `mv <path> $TMPDIR/mf-baseline-isolation-*/cloog|kics/` + `git rm --cached <path>`（index 级临时隔离） |
| rerun_command | `CI_PACKAGES=archives/m/medianfilter/1.0.0 CI_REPO_ROOT=<worktree> zsh ci/conan/build_and_test.sh archives/m/medianfilter/1.0.0` |
| rerun_exit_code | 0（隔离状态下 W3 全绿：conan create 通过、L1 上游测试+test_package 执行、L4 patches 干净、L5 lib/ 有内容、L1e 破坏性反证通过、1/1 success） |
| restore_command | `cp <iso>/cloog|kics/* <path>` + `git add -f <path>`（.gitignore 拦截故用 -f） |
| post_sha256（逐文件） | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855（== pre_sha256） |

隔离复验结论：pre_sha256 == post_sha256；恢复后 `git status` 对这三个路径干净、
`git diff HEAD` 为空；当前库 diff/staged/PR 均不包含这些路径。隔离复验通过，继续
当前库审计与交付；这些基线文件未修改、未提交、未写入知识库或 PR。远程 CI 采用
PR diff 模式（仅扫描 PR 内文件），不会命中这些整仓基线噪声。
---

**编译结束**: 2026-09-28 10:01
**最终状态**: built
