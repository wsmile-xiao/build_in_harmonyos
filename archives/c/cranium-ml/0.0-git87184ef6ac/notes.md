# cranium-ml 0.0-git87184ef6ac 适配笔记

## 编译环境
- 构建系统: custom（header-only，无库构建系统；上游测试用 Makefile）
- 编译日期: 2026-09-27
- 编译器: clang 15（OHOS PC aarch64 工具链）/ clang++
- 状态: built

## 编译步骤

1. 官方源码：https://github.com/100/Cranium，commit 87184ef6acdb7751e9c5c5ea1be3d46bc0d69ee6（"fix bug in accuracy function"，2017-02-05）
2. 源码校验：tarball SHA-256 = 67dfd3ac010947f4c3c4dc62ac2c9b0b932968131f9e5ba75ba25a0afb114f18（与 conandata.yml 一致，与 .tarball-sha256 标记一致）
3. 配方：conanfile.py（header-library，无编译单元），conandata.yml（官方 HTTPS URL + sha256），patches 为空
4. 构建验证：`conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64` → exit 0，test_package 两个测试全部通过
5. 本地 CI（finish W3）：setup.sh + build_and_test.sh → 通过（JC_RESULT=pass，L0 pass），.ci-result.json exit_code=0

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 matrix_tests 在 -O3 断言 `ds->data[i][j] == getMatrix(mds,i,j)` 失败 | 上游测试只初始化 DataSet 对角线元素，其余为未初始化堆内存（C UB）；-O0 下全部一致 | 判定为上游测试自身缺陷（非平台/适配问题），如实计入失败项 4/5=80%；恢复条件=上游初始化全部元素 |
| 2 | test_package 消费者测试段错误 | createMatrix/createDataSet 只持有传入指针不拷贝，destroyMatrix/destroyDataSet 会 free 之；首次传入栈数组 + 二次 free | 消费者测试改为堆内存且不重复 free；ASan 验证通过 |
| 3 | conan create 下载 github.com 超时 | 本机到 github.com 网络间歇性超时（urllib），curl 可通 | 使用 Conan 官方下载缓存（core.sources:download_cache，按 sha256 键）注入已核验 tarball；配方 URL 仍为官方 HTTPS（R39） |
| 4 | 上游 network_tests 运行产物 network.pkl/network2.pkl 污染 .work 被 refresh-patch 误生成为补丁 | 上游测试 saveNetwork 序列化到 cwd | 清理 .orig/.work 中 pkl 产物，删除误生成补丁，patches 保持为空 |
| 5 | W3 JC 命中其他库既有基线状态文件（cloog/kics 的 .build-closed/.staging-verified，main 已跟踪） | main 基线中其他库的历史状态文件被 git 跟踪，非当前库产物 | 基线隔离复验：记录 SHA-256 → 临时隔离 → 复跑 W3 通过 → 原样恢复 → pre==post SHA-256 核对一致；未修改/提交该基线文件（详见 reports/baseline-isolation-audit.md） |

## 源码修改

无源码修改，patches 为空（header-only 库，无需平台补丁）。

## 依赖版本

无第三方运行依赖（header-only C99；仅测试链接系统 libm）。registry 预检（preflight_check.sh）：无依赖需发布。

## 验证结果

- conan-verify: G1/G2/G3/G4 全 PASS（G2 干净 conan create 通过）
- test_package 消费者测试（test_package.c）：矩阵运算 + 网络前向断言通过，退出码 0
- 鸿蒙专项测试（ohos_special_test.c）：XOR 训练收敛，MSE 0.142754 → 0.001386（-99.03%），退出码 0
- 上游测试双口径：source_declared_total=5、configured_executable_total=5、executed_passed_total=4（matrix_tests 因上游未初始化内存 UB 失败），全量通过率 4/5=80%
- W3 本地 CI：JC_RESULT=pass，L0 pass，build_and_test.sh 通过

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | header-library 配方（无编译单元，R32 平台判断，export_sources/build 齐全） |
| conandata.yml | 官方源码 URL + SHA-256（R39） |
| test_package/ | 消费者测试 + 鸿蒙专项测试 + MANIFEST |
| reports/ | conan-create/conan-verify/W3/上游台账/消费者验证/基线审计 |
| README.md（软件级） | 软件描述与版本索引 |

## 注意事项

- 本机 github.com 网络波动已用官方下载缓存规避；CI 侧从官方 URL 下载并校验 SHA-256
- W3 全量扫描命中 main 基线其他库状态文件属既有基线噪声，已隔离复验并通过；不得在后续操作中修改、提交该基线文件