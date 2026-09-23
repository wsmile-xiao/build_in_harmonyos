# frozen 1.1.1 适配笔记

## 任务信息
- **任务号**: #5900（开源鸿蒙PC专项积分赛-依赖）
- **分支**: feat/frozen-1.1.1（基线 upstream/main 5f510c782b）
- **类型**: header-only C++14（无库编译，无依赖）
- **编译日期**: 2026-09-05
- **编译器**: clang 15.0.4（OHOS 交叉工具链，/data/service/hnp/bin/clang++）
- **平台**: arm64-ohos（OpenHarmony PC）
- **状态**: built

## 源码
- 官方 tag 1.1.1 tarball（codeload.github.com，HTTPS 官方源）
- sha256: f7c7075750e8fceeac081e9ef01944f221b36d9725beac8681cbd2838d26be45
- 注：GitHub archive URL（github.com/.../archive/refs/tags/1.1.1）在设备网络实测 404，
  改用官方 codeload.github.com 端点（内容同 tag tarball，同 1.2.0 归档先例）。

## 上游测试清点（三步法 · 静态）
- 测试框架：Catch2（tests/catch.hpp 随源码自带，无需网络）
- 静态声明：grep "TEST_CASE(" 逐文件计数 12 个 test_*.cpp = **56 个 TEST_CASE**
  （test_algorithms 2 / test_elsa_std 1 / test_map 10 / test_rand 1 / test_set 9 /
  test_str 7 / test_str_set 2 / test_unordered_map 11 / test_unordered_map_str 2 /
  test_unordered_set 9 / test_unordered_str_set 2；test_main.cpp 提供 main）
  注意：tests/catch.hpp 内部另有 48 处 TEST_CASE( 字样，为 Catch 库内部宏，不计入上游用例。
- ctest 注册：2 个条目（frozen.tests 56 用例 + no_exceptions 编译测试，WILL_FAIL 预期失败）
- 1.1.1 与 1.2.0 差异：测试开关名为 `frozen.tests`（CMAKE_DEPENDENT_OPTION，
  条件 NOT subproject；1.2.0 才改名 FROZEN_BUILD_TEST）；
  frozen.tests=ON 同时构建 examples/ 6 个示例可执行（额外编译验证）。

## 上游测试实测（rule 4，conan create 内 build() 集成）
```bash
cmake <src> -Dfrozen.tests=ON -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_CXX_COMPILER=/data/service/hnp/bin/clang++ -DCMAKE_CXX_FLAGS=-std=c++14
cmake --build <bdir> -j4
ctest --test-dir <bdir> --output-on-failure
```
- **56/56 通过（100%）/ 0 失败 / 0 跳过**（"All tests passed (3717 assertions in 56 test cases)"）
- ctest 汇总：100% tests passed, 0 tests failed out of 2（frozen.tests + no_exceptions 均 Passed）
- evidence: reports/w3-local-ci.log（W3 build_and_test 全量输出——ctest 汇总
  "100% tests passed, 0 tests failed out of 2" 及 test_package smoke 输出）；
  Catch2 汇总 "All tests passed (3717 assertions in 56 test cases)" 见构建目录
  LastTest.log（conan 缓存目录）。reports/conan-create.log 为后续缓存复跑日志，
  首轮完整构建证据以 w3-local-ci.log 为准。
- subprocess 调 cmake/ctest 用绝对路径（OHOS posix_spawn 不按 PATH 搜索相对名——
  与 rich/vc/1.2.0 同源教训）

## test_package（R34 消费者验证）
- test_frozen.py：检查 include/frozen/map.h 存在 + 用包头文件真实编译运行 smoke
  （frozen::map constexpr 构造 + find 查找断言 m[2]==20），实测输出
  "frozen smoke: m[2]=20" / "OK: frozen headers + real frozen::map usage works"。
- 消费者测试：1/1 = 100%（1 个真实 API 调用 smoke，2 个断言点：头文件存在 + 运行断言）。

## 验证结果
- conan-verify：G0/G1/G2/G3/G4 + L2/L4/L5 全 PASS（reports/conan-verify-report.md）
- **构建**: conan create 成功，frozen/1.1.1@ohpcd/stable Package created
- R26: header-only 无系统同名库冲突（cpp_info.libs=[]）
- R38: 纯库包，无 commands.json

## 与 1.2.0 归档的关系
- 配方骨架复用已合入的 archives/f/frozen/1.2.0（PR !6988，CI 已验证），
  按 1.1.1 实际差异修改：版本号、conandata URL/SHA256、测试选项名 frozen.tests、
  build() 测试失败改为抛 ConanException 阻断（比 1.2.0 更严格，测试真实作门禁）。
---

**编译结束**: 2026-09-05 00:35
**最终状态**: built
