# vdt 0.4.6 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-18
- 编译器: clang/clang++ (OHOS SDK 26.0.0.18, clang 15.0.4)
- 目标平台: HarmonyOS PC (aarch64, os=OHOS)
- 状态: built

## 编译步骤

```bash
# 1. init（下载官方源码 v0.4.6.tar.gz，sha256=1820feae...）
python3 scripts/ohc-run.py init-build vdt 0.4.6 --url=https://github.com/dpiparo/vdt/archive/refs/tags/v0.4.6.tar.gz

# 2. 手动编译验证（DIAG=ON 构建全部上游单元测试）
cmake -S . -B build-ohos \
  -DCMAKE_SYSTEM_NAME=OHOS -DCMAKE_SYSTEM_PROCESSOR=aarch64 \
  -DCMAKE_C_COMPILER=/data/service/hnp/bin/clang -DCMAKE_CXX_COMPILER=/data/service/hnp/bin/clang++ \
  -DDIAG=ON -DNEON=ON -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_POLICY_VERSION_MINIMUM=3.5
cmake --build build-ohos -j4

# 3. Conan 配方验证（W3, ohos-aarch64 profile）
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  -o vdt/*:shared=True --build=missing

# 4. finish（W2 结构 + R36 依赖 + W3 本地 CI 模拟）
python3 scripts/ohc-run.py finish vdt 0.4.6 built
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | cmake configure 失败 "Compatibility with CMake < 3.5 has been removed" | vdt 声明 cmake_minimum_required 3.2，本机 CMake 4.1.2 不兼容 | 加 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`（conanfile 中 cache_variable 固化） |
| 2 | conan create 下载源码超时 | github.com 网络不可达 | 本地 W3 用 gh-proxy 镜像列表下载（sha256 与原官方源一致）；提交 conandata 保留官方单 URL，CI 构建时自动做 mirror fallback |
| 3 | test_package consumer 编译报 "no member named 'exp' in namespace 'vdt'" | vdt 公开 API 命名是 fast_exp/fast_sinf 等，非裸函数名 | 按 include/vdt/exp.h 等真实签名改用 vdt::fast_exp/vdt::fast_isqrt/vdt::expv |
| 4 | W3 JC 拦截 archives/c/cloog/0.21.1/.build-closed 等 2 个文件 | main 上 cloog PR(906cc59ae7) 混入的既有运行时状态基线文件 | 按基线隔离规则 `git rm --cached` 临时隔离→复跑 W3 通过→`git restore --staged` 原样恢复，pre/post sha256 均为 e3b0c442...（空文件），vdt diff 不含该路径 |

## 源码修改

无（vdt 上游源码零修改，无 patches；仅编写 conanfile.py/conandata.yml/test_package 适配配方）。

## 依赖版本

无强制第三方依赖（C++11 标准库 + CMake 3.2+ + Python 3 仅用于 configure 阶段签名代码生成）。

## 上游测试申报台账（R51，全量枚举）

测试入口均来自官方 v0.4.6 源码，progs/units 与 progs/（DIAG=ON 构建）：

| 入口 | 类型 | 是否独立用例 | 运行结果 |
|------|------|-------------|----------|
| exp_test / log_test / sqrt_test / sin_test / cos_test / inv_test / tan_test / tanh_test / asin_test / acos_test / atan_test / atan2_test | 用户测试源（函数单元测试） | 是（12 个） | 全部 exit=0 通过 |
| fpDifferentBit / printInstSet / test_randomPool | 工具/诊断程序 | 否（工具，非断言测试） | exit=0 运行成功 |
| test_fcnResponse / test_fcnComparison / test_fcnPerformance | 诊断程序（读样本文件比对） | 否（诊断，非独立断言用例） | exit=0 运行成功 |
| vdtPerfBenchmark / vdtArithmBenchmark / vdtArithmComparison | 基准程序 | 否（benchmark，不计用例） | 编译成功，未计入通过率分母 |
| progs/testExp.py / vdtNumpyTime.py / vdtNumpytest.py / vdtCtypesTest.py | Python 包装测试脚本 | 否（依赖 numpy 绑定的辅助脚本） | 未实例化（需自建 vdtnpfun.so 包装模块，属 python 绑定辅助，非库主体测试） |
| src/testFatlib.cc | fatlib 内部试验源 | 否（未注册 CMake 目标） | 未实例化 |

- 源码声明独立用例数：12（progs/units/*_test.cpp）
- 当前配置实际实例化：12（DIAG=ON 全部构建）
- 实际执行通过：12/12，通过率 100%
- 统计口径：全目录枚举（progs/units 18 个 .cpp + progs 3 个 benchmark + 4 个 py 脚本），独立用例按用户测试源 TEST_CASE 判定

## 验证结果

```bash
# 上游单元测试 12/12 通过（DIAG=ON，progs/units/*_test.cpp）
# 消费者验证 consumer_probe：调用 vdt::fast_exp/fast_sin/fast_cos/fast_log/fast_isqrt + expv/sinv，12/12 对拍 PASSED
# 鸿蒙专项测试 ohos_special_probe：kOnOhos=1 kNeonPath=1，expv/sinv 8 点对拍 + fast_exp PASSED
# W3 本地 CI：L0 pass（JC 隔离复验后 0 junk）/ L1 pass（test_package 执行）/ L4 pass / L5 pass，Pass rate 100%
```

### 上游测试运行日志 SHA-256（留存 /storage/Users/currentUser/tmp/vdt-tests/）

| 日志 | SHA-256 |
|------|---------|
| exp_test.log | 38337eee722672a2e442e68c2304c3f9be736664ade06e81d8a4f338fcaeb9e6 |
| log_test.log | 2829b6584ebbcb5b92ffd9a502a46a6440bdc247871efaab613d7310dcb5ff75 |
| sqrt_test.log | bd039d878487aa2107d5b9ab09e48ff779e78d6790c07768dcd44bf02c98052d |
| sin_test.log | 2aa3cde807243204206ab7059ae3b5b2bd4ceabcb0029e418e85598b3210b7db |
| cos_test.log | 163fbfc0d9396dff242c2b0e9c44fc07953b03fd2ada38c700db762ec6009da9 |
| inv_test.log | 0a9bb6af73734c29d44f96ce049009cee1baf8b38efdc1a55a321ba967ab99ce |
| tan_test.log | 461ede53d36cb3644f5bc6cccf1f88bfd1e5b8d1e99a797ebd9fbea8f10157c9 |
| tanh_test.log | f17f9171b72e65543683bca5a6a0ebba78e84c47996991fb3c486cd64e0350f5 |
| asin_test.log | 3ea4930a37b102934276490607e5c810da1c35a71b81c8e38d6d778907aefb36 |
| acos_test.log | 24da19152ef35ec0d24104ffc92261b54a67107da4ca2d0ab32b5dc54b4dbb82 |
| atan_test.log | 78e2dccff399045f7dfa05edf1e9b4afec8f002487279a1d43efd77ce8e2c884 |
| atan2_test.log | 6bae5624396ea34efe1a2c7a6a5d65370adc6ac91868f716929e8e28a353edde |
| fpDifferentBit.log | 54631492577f538ffec9e838c6fb66f0478bd514b3018c698ebfa7347a08ebbd |
| printInstSet.log | b0969c431d1eb8e5669af89aaeddac19475334f9c7faf43e6c1212fbe55b967a |
| test_randomPool.log | a06783310f2d3aa0e4b6abddbdb56ff031782e25073072c34c180095b4ee9ce5 |
| test_fcnResponse.log | bb47939cfabcf3fe705f33120febf4b19f36f204dd38887497dd734d99dfac8a |
| test_fcnComparison.log | 67f62fe10f68c15caf059b749dd78b94800d5924cf1580aebed3aecedbc19574 |
| test_fcnPerformance.log | a2b459291b9f20187c7dbbb50421bd33366c2354abf8b1cf0d77e840d9be2a5b |

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | CMake 配方（OHOS profile、NEON、CMAKE_POLICY_VERSION_MINIMUM=3.5） |
| conandata.yml | 官方源 + sha256 |
| test_package/consumer.cpp | 消费者验证用例 |
| test_package/test_vdt_ohos.cpp | 鸿蒙专项测试用例 |
| manifest.yaml | 版本 manifest |

## 注意事项

- 本库为纯库（无 bin/），按 R38 不需要 commands.json（L0k 门禁复核通过）。
- vdt 函数为快速近似实现，双精度对拍阈值 1e-7（上游自身也非逐位精确）。
- 上游测试枚举台账已按双口径记录：source_declared_total=12，executed_passed=12（100%）。
- 与 archives/c/cern/0.4.6 的关系：同一上游（dpiparo/vdt v0.4.6，同一 SHA-256）曾被按
  cern 包名适配；本任务按绑定库名 vdt 正式发布包名 vdt。两包同源同版本，本包为正式包名版本。
---

**编译结束**: 2026-09-18 03:04
**最终状态**: built
---

**编译结束**: 2026-09-18 03:21
**最终状态**: built
