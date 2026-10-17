# etl 20.38.4 适配笔记

## 官方来源核验（Bootstrap）

- 官方仓库: https://github.com/ETLCPP/etl （默认分支 master）
- tag: **20.38.4** → commit `92e880f3b1635f2cf034db76de6c95cf8b1ccd82`
- 交叉核验: GitHub API refs/tags 与 GitLab 镜像 `git ls-remote` 返回同一 commit
- 源码 tarball: https://github.com/ETLCPP/etl/archive/refs/tags/20.38.4.tar.gz
- SHA-256: `4074583bacac17e7944030f099d18a4ea3591d5d58b8d8b85c1b7f080a3e9610`
- tarball 内容: 1221 个文件，顶层目录 `etl-20.38.4/`

## 库性质

- header-only C++ 模板库，`include/etl/` 下 266 个头文件
- 官方 CMake 以 `INTERFACE` 库提供（`add_library(etl INTERFACE)`），仅安装头文件
- 许可证: MIT（`LICENSE` 文件）

## 适配要点

- 无编译步骤，无运行依赖；配方 package() 直接拷贝 `include/etl/` 与 LICENSE
- test_package 以消费方视角 include 头文件并做编译期/运行期断言验证

## 首错记录（R01 保留，R02 继续遵守）

1. **默认 profile libcxx 误配**：`conan profile detect` 生成的默认 profile 为
   `compiler.libcxx=libstdc++11`，CMakeToolchain 注入 `-stdlib=libstdc++`，OHOS 工具链
   clang 15 只提供 libc++，报 `invalid library name in argument '-stdlib=libstdc++'`
   → CMake TryCompile broken。命中知识库 DRAFT-ecm629-stdlib-libstdcxx-invalid。
   **修复**：改用仓库预置 `ci/conan/profiles/ohos-aarch64`（libcxx=libc++）。
   ⛔ 禁止在 recipe 内写死 `-stdlib`（R33）。
2. **测试表达式修正**：test_package 初版含 `etl::nullopt != 0`（非法表达式，无对应
   operator），已改为 `!etl::optional<int>{}.has_value()`。

## 本地验证实测（R02）

- **conan create**（`-pr:h/-pr:b=ci/conan/profiles/ohos-aarch64`）exit 0；
  test_package 交叉编译通过，CTest `1/1 Test #1: test_etl ... Passed`（0.02s）。
- **鸿蒙特有测试**：同上 OHOS profile 实跑 test_package，实际调用 etl API
  （etl::vector/etl::optional/etl::string），1/1 通过。
- **上游测试套件**（宿主 clang 15 原生，`test/CMakeLists.txt` → etl_tests → ctest）：
  8440 个测试中 25 失败（60 failures），失败集中在 `char` 参与数值计算的统计测试
  （test_correlation / test_covariance / test_rms，如 `test_char_rms: Expected 5.21
  +/- 0.05 but was 167.721`）——宿主 `char` 为无符号导致，属上游测试的宿主平台差异、
  非 etl 库缺陷；etl 为 header-only，无二进制约束。
## 上游失败 reconcile 与责任归因（R03）

### 统计口径 reconciliation
- "25 out of 8440 tests failed" = UnitTest++ 测试用例数：8440 个注册测试中 25 个失败（因 test_read_int8_t 同时存在于 big/little endian 两个套件，25 个"套件-测试"对对应 24 个唯一测试名）。
- "60 failures" = 断言失败总数：逐测试断言失败次数求和恰为 60（如 test_read_int8_t 4 次、bresenham 各 3 次、correlation 各 2 次），等于进程退出码 60。
- 二者粒度不同（测试用例 vs 断言），一致不矛盾。

### 失败分组与责任归属
- bit_stream / bit_stream_reader_big|little_endian / bresenham_line / correlation / covariance / rms：全部因上游测试假定 char 为有符号。
- 最小复现：aarch64 宿主 char 为无符号（charprobe: char(-1)=255, CHAR_IS_UNSIGNED）。
- 源码核对：test_bit_stream_reader_big_endian.cpp 用 `std::array<char>` 存 int8_t 负值（0xA5/0xFF），无符号 char 窄化为 165/255，而 ETL read<int8_t> 正确返回 -91/-1；bresenham_line 测试 `using Value = char`；correlation/covariance/rms 的 char 统计测试假设有符号语义。
- 控制组：同套件 `-fsigned-char` 构建运行 → **8440/8440 全绿**（exit 0，日志 sha256 6865ae4cd...）。
- 结论：非 ETL 库缺陷（库按 int8_t 语义返回正确位模式），非 OHOS 特有（aarch64 默认无符号 char 的平台差异），属上游测试对 char 符号性的可移植性假设。恢复条件：上游测试在 signed-char 平台或加 `-fsigned-char` 运行即可全绿；ETL 实际消费者验证（OHOS profile test_package 1/1）不受影响。
---

**编译结束**: 2026-08-31 09:08
**最终状态**: built
