# libff 0.2.1 OHOS 适配笔记

## 上游身份链（先取证后写入）

| 项 | 值 | 证据 |
|---|---|---|
| 上游仓库 | https://github.com/scipr-lab/libff | 任务元数据：名称 libff / cmake / 版本 0.2.1 |
| 版本标签 | v0.2.1（GitHub tag） | tag 归档 URL 与 tags/v0.2.1.tar.gz |
| 源码归档 | https://github.com/scipr-lab/libff/archive/refs/tags/v0.2.1.tar.gz | 两次独立下载 SHA256 一致 |
| SHA256 | `630010841f6992ad6e4758bb079d248eab46cfe66a4c0391c11075f3e5387b60` | sha256sum ×2 交叉验证 |
| 许可证 | MIT（仓库根 LICENSE） | 归档内 LICENSE 文件 |
| 项目用途 | zk-SNARKs C++ 基础库：有限域 Fp/Fp2/Fp6/Fp12、椭圆曲线群 G1/G2、双线性配对 | 源码树 libff/algebra/、README |
| 构建系统 | CMake（上游 `cmake_minimum_required(2.8)`，实际 ≥2.8.11 特性；CURVE 选项选曲线） | 根 CMakeLists.txt:1 |
| 依赖 | gmp（REQUIRED）、openssl（find_package REQUIRED）；可选 libprocps | CMakeLists.txt find_path/find_library/find_package |
| 测试体系 | ctest：3 目标（algebra_bilinearity/algebra_groups/algebra_fields_test），EXCLUDE_FROM_ALL，挂 check target | libff/CMakeLists.txt |

同版本号 0.2.1 的其他候选（herumi/ff、demlabs/libff）与任务元数据不符：
herumi/ff 无 CMake、无 0.2.1 tag；demlabs/libff 是 scipr-lab fork，tag 归档非官方源。
任务元数据（包管理器 Conan + cmake + 0.2.1 + 语义库）唯一指向 scipr-lab/libff。

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-07
- 编译器: clang 15.0.4（OHOS SDK）
- Profile: ~/.conan2/profiles/ohos-aarch64（armv8, libc++, cppstd=17, cci 依赖）
- 状态: published

## 关键取证（configure 对照实验，~/tmp/libff-investigation.log）

| 实验 | 配置 | 结果 |
|---|---|---|
| D1 | 默认（CURVE=BN128） | **失败**：depends/CMakeLists.txt:4 `Cannot find source file "ate-pairing/src/zm.cpp"` —— 官方 tag 归档不含子模块内容 |
| D2 | CURVE=ALT_BN128 | configure 成功，alt_bn128 源码全部内置 libff/ 树 |
| D3 | BN128 + gitlink 精确 commit 子模块（ate-pairing=e69890125746cdaf25b5b51227d96678f76479fe / SHA256 `01aadb2b0d1a67916ab1d59ad3bd7018d5b19e1d4dfc3074c58d5aa7c4280577`；xbyak=f0a8f7faa27121f28186c2a7f4222a9fc66c283d / SHA256 `cb58a404760cc53384182e54ee66013c7dd5a56f8d4a253b82b837d6242ec5e0`，取自 GitHub API tag tree 的 mode=160000 条目） | configure 成功，但编译**失败**：`zm2.cpp:3644 use of undeclared identifier 'Xbyak'` —— 该行在 `#endif // MIE_USE_X64ASM`（3574 行）之后、守卫之外；aarch64 上 `zm.h:68` `#undef MIE_USE_X64ASM`（仅 `__x86_64__`/`_WIN64` 定义，见 zm.h:62-68），xbyak.h 不被 include。**结论：BN128 为上游 x86-64-only 设计，aarch64 不可编译，非归档缺陷单方面所致** |

## BN128（上游默认）vs ALT_BN128（本包采用）差异对照

| 维度 | BN128（libff/curves/bn128 + depends/ate-pairing） | ALT_BN128（libff/curves/alt_bn128） | 结论 |
|---|---|---|---|
| 密码学语义 | q=`21888…08583`、r=`21888…95617`（bn128_init.cpp:38,63，源值来自 herumi Param） | q、r 常数**逐位一致**（alt_bn128_init.cpp:41,61） | 同一条 BN254（alt-bn128/SNARK 曲线），配对值密码学等价 |
| API | `bn128_G1{bn::Fp X,Y,Z}`，域类型 `bn::Fp/Fp2/Fp6`（ate-pairing 类型） | `alt_bn128_G1{alt_bn128_Fq X,Y,Z}`，域类型 `Fp_model<n,modulus>` | 类型名与底层域类**不互换**：源码层面 `bn128_*` 与 `alt_bn128_*` 是两套不兼容 API，消费者须按本包实际导出的 `alt_bn128_*` 编程 |
| ABI | `bn::Fp` 内部为 mie::Vuint（Xbyak JIT 数据表布局，zm2.h）；bn.h 大量**静态函数指针**（`Fp6T::add/mul` 等运行时重定向） | `Fp_model` 固定 `mp_limb_t mont_repr[num_limbs]`（4×64bit），无函数指针 | 对象布局与链接符号（`libff::alt_bn128_*` vs `libff::bn128_*` + `mie::`）完全不同，**无 ABI 兼容性** |
| 序列化 | `operator<</>>` 转发到 `bn::Fp` 的流实现（ate-pairing 自有格式） | `operator<</>>` 走 `Fp_model` 的 bigint 流格式（is_zero 字节 + 坐标） | 两套**流格式不互通**；跨实现交换数据须走 affine 十进制文本 |
| 可移植性 | x86-64 only（Xbyak JIT，见 D3） | 纯 C++ + GMP，aarch64 可移植 | OHOS armv8 唯一可构建路径 |
| default_ec_pp | `CURVE_BN128` → `bn128_pp` | `CURVE_ALT_BN128` → `alt_bn128_pp`（ec_pp.hpp 宏选择） | 消费者经 `cpp_info.defines=["CURVE_ALT_BN128"]` 识别真实配置 |

消费者识别：上游 `libff/common/default_types/ec_pp.hpp` 以 `CURVE_*` 宏决定 `default_ec_pp`；
构建侧由根 CMakeLists `add_definitions(-DCURVE_${CURVE})` 注入，消费侧由配方
`package_info() → cpp_info.defines` 传播**全宏集**（`CURVE_ALT_BN128` +
`BINARY_OUTPUT` + `MONTGOMERY_OUTPUT`，见 E2186：架构驱动的后端替换是兼容性
契约，宏集必须完整下发），test_package 以 `#error` 门禁 + `static_assert`
编译期验证该宏集与 `default_ec_pp = alt_bn128_pp` 一致。子模块缺失与
gitlink 固定提交恢复的方法论属 E150（manual-download），本笔记仅记录案例证据。

## 编译步骤

```bash
conan create . -pr:h ~/.conan2/profiles/ohos-aarch64 -pr:b ~/.conan2/profiles/ohos-aarch64 --build=missing
```

配方内固化：
1. `CMAKE_POLICY_VERSION_MINIMUM=3.5`（CMake 4.x 兼容，E103/E187）
2. `CURVE=ALT_BN128`（唯一可自包含构建路径；BN128/EDWARDS 依赖空子模块）
3. `WITH_PROCPS=OFF`（OHOS 无 libprocps；上游 NO_PROCPS 回退已验证）
4. `IS_LIBFF_PARENT=ON`（注册测试目标与 install() 规则）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 默认 CURVE=BN128 configure 失败 | 官方归档空子模块 | 固定 CURVE=ALT_BN128（自包含） |
| 2 | libprocps pkg-config 失败 | OHOS 无 procps | WITH_PROCPS=OFF → 上游 NO_PROCPS 回退（profiling.cpp:26） |
| 3 | CMake 4.x 拒绝兼容模式 | 上游要求 2.8 | CMAKE_POLICY_VERSION_MINIMUM=3.5（E103/E187） |
| 4 | 上游测试空转退出 | 测试以 assert() 为 oracle，`#ifndef NDEBUG` 门控；Conan Release 注入 -O3 -DNDEBUG | 双构建树：正式树 Release 打包；测试树 CMAKE_BUILD_TYPE=Debug（无 NDEBUG）构建+运行全部上游测试（E294 变体） |
| 5 | 测试二进制运行报 `__gmpn_sub_n: symbol not found` | ctest 用 conanbuild 环境，不含 gmp shared 的 lib 路径 | ctest 切到 conanrun 环境 |
| 6 | test_package 编译失败：gmp.h 找不到 | libff 公开头 bigint.hpp 直接 #include <gmp.h>，gmp 是传递依赖 | `self.requires("gmp/6.3.0.1", transitive_headers=True)` |

## 源码修改

无（ALT_BN128 与 NO_PROCPS 均为上游原生 CMake 选项，未打补丁）。

## 依赖版本

- gmp/6.3.0.1（cci，transitive_headers）
- openssl/3.5.6（cci）

## 验证结果

```bash
# 上游官方测试（Debug 测试树，真实运行，非空转）
$ ctest --test-dir .../build-tests --output-on-failure --timeout 600
1/3 Test #1: algebra_bilinearity_test .........   Passed    0.26 sec
2/3 Test #2: algebra_groups_test ..............   Passed   18.74 sec
3/3 Test #3: algebra_fields_test ..............   Passed    0.87 sec
100% tests passed, 0 tests failed out of 3

# test_package（消费者视角，真实核心 API）
$ ctest --test-dir test_package/build/clang-15-armv8-17-release
1/2 Test #1: test_package ......... Passed  # alt_bn128_pp::reduced_pairing 双线性/非退化/群逆/序列化往返，17 CHECK 全过
2/2 Test #2: test_package_ohos .... Passed  # 鸿蒙专项 8 checks（见测试统计）

# 包内容
include/libff/**: 49 .hpp + 18 .tcc
lib/libff.a: ELF64 AArch64
licenses/LICENSE: MIT
```

## 测试统计

- 上游 ctest：3 注册 / 3 构建 / 3 运行 / 3 通过 / 0 跳过（无 NDEBUG 空转）
- test_package：1 可执行 / 1 通过（17 项显式 CHECK：配对、群公理（含群逆
  P+(-P)=O）、域运算、序列化；CHECK 为普通 if，Release/NDEBUG 下不空转）
- test_package_ohos（鸿蒙专项）：1 可执行 / 8 检查通过 —— NO_PROCPS profiling
  回退运行、aarch64 可移植 Fp invert/sqrt、bigint↔mpz 互操作、q/r 常数位级
  一致、配对确定性、zero 序列化分支 ×2、包内 libff.a 对象级检查（ar/ELF
  头逐成员解析：24 对象全 ELF64/小端/ET_REL/EM_AArch64、alt_bn128 5 对象
  齐备、公共 3 TU 齐备、无 bn128_* 混入）
