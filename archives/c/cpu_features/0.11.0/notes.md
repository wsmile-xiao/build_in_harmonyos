# cpu_features 0.11.0 适配笔记

## 编译环境
- 构建系统: cmake（`project(CpuFeatures VERSION 0.11.0 LANGUAGES C)`）
- 编译日期: 2026-09-10
- 编译器: clang/clang++（OHOS aarch64，libc++）
- 状态: published
- 平台: HarmonyOS PC（OHOS 6.0, armv8/aarch64）
- 版本跟进口径：仓内已有 0.9.0 归档（2026-09-06），本任务为同库新版本适配，测试按新要求完整重做闭环

## 上游 0.9.0 → 0.11.0 差异审计（版本跟进必做）

| 维度 | 0.9.0 | 0.11.0 | 影响 |
|------|-------|--------|------|
| 公共 API（aarch64） | GetAarch64Info / GetAarch64FeaturesEnumValue / GetAarch64FeaturesEnumName | 同左，签名零变化 | 消费者源码无需修改 |
| Aarch64Features 位域 | ~46 位 | +22 位（mops/hbc/sveb16b16/lrcpc3/lse128/fpmr/lut/faminmax/f8cvt/f8fma/f8dp4/f8dp2/f8e4m3/f8e5m2/smelutv2/smef8f16/smef8f32/smesf8fma/smesf8dp4/smesf8dp2/poe） | 纯追加，ABI 兼容方向 |
| 枚举 Aarch64FeaturesEnum | 到 AARCH64_LAST_ | +22 枚举项，AARCH64_POE 成为 LAST_ 前最后一项 | test.c 新增 POE 一致性断言 |
| 测试声明数 | 132 | 133（新增 MrsMidrEl1_RPI4，FreeBSD 分支） | Linux/OHOS 实例化数不变：27 |
| ndk_compat | 有 | 有（无 init API 变化，任务提示中的"cpufeatures_init"未在上游 0.10/0.11 出现——实证核对 include/ 与 ndk_compat/ 无此符号） | 无影响 |
| CMake googletest | configure 期从 GitHub 下载 | 逐字相同（仅行号偏移） | patch 思路直接复用 |
| CMake C++ 标准 | 主 CMakeLists set(CMAKE_CXX_STANDARD 14) | 移至 test/CMakeLists.txt target_compile_features(cxx_std_14) | patch 不涉及 |
| 库源码组织 | 显式列出各架构 impl 文件 | file(GLOB src/impl_*.c) 全编入库 + 宏守卫；unix_based_hardware_detection 拆出 hwcaps_linux_or_android.c/hwcaps_freebsd_or_openbsd.c；新增 HAVE_STRONG_ELF_AUX_INFO | OHOS 下行为一致（__linux__ → CPU_FEATURES_OS_LINUX） |

任务提示中提到的"0.10 API 调整（cpufeatures_init 等）"经实证核对不存在于 0.11.0 头文件/源码（grep cpufeatures_init/CpuFeaturesInit/cf_init 零命中）；0.10 系列的实际变更为内部实现与新增特性位，公共 API 保持 0.9 形态。

## 编译步骤

```bash
conan create . --user=ohpcd --channel=stable \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

- `source()`: 下载官方 GitHub tag v0.11.0 tarball，SHA-256 `ab2463f2d38fcaff1ce806be8e4c91333449931f5e02009d543b2569a3fa471a`
- `build()`: cmake configure（`BUILD_TESTING=ON`，外部 gtest）→ 构建库 + list_cpu_features + 4 个测试可执行 → 直接运行并解析 gtest 输出，生成 `HMBS_UPSTREAM_TEST_RESULT`
- `package()`: `cmake.install()`（头文件安装到 include/cpu_features/）+ LICENSE
- `test_package/`: 消费者测试 test.c（GetAarch64Info/GetAarch64FeaturesEnumName/GetAarch64FeaturesEnumValue 真实 API + 0.11.0 新增 AARCH64_POE 枚举一致性）+ OHOS 专项 test_ohos.c（库结果与 /proc/cpuinfo 交叉核对）

## 上游测试用例审计（双口径台账）

| 测试程序 | 源码声明 | 说明 |
|----------|---------|------|
| bit_utils_test | 2 | 平台无关 |
| string_view_test | 17 | 平台无关 |
| stack_line_reader_test | 4 | 平台无关 |
| cpuinfo_aarch64_test | 7 | Linux 分支 4；macOS/Windows/FreeBSD 分支 3 互斥 |
| cpuinfo_arm_test | 11 | PROCESSOR_IS_ARM 互斥（不实例化） |
| cpuinfo_x86_test | 69 | PROCESSOR_IS_X86 互斥（不实例化） |
| cpuinfo_mips_test | 7 | 互斥 |
| cpuinfo_ppc_test | 5 | 互斥 |
| cpuinfo_s390x_test | 4 | 互斥 |
| cpuinfo_riscv_test | 5 | 互斥 |
| cpuinfo_loongarch_test | 2 | 互斥 |
| **合计** | **133** | 本配置实例化 27，执行通过 27 |

- `source_declared_total=133`（11 个测试源文件所有 TEST/TEST_F）
- `configured_executable_total=27`（OHOS/armv8 实例化：2+17+4+4）
- `executed_passed_total=27`（4 个可执行全部 PASSED）
- 未实例化 106 = 架构互斥 103 + aarch64 OS 分支互斥 3（逐项守卫证据见下节）

## 上游 106 个未执行用例逐项技术原因（rule4 口径，按审核要求三类分组）

上游测试套件为 CMake GTest（`test/*.cc` 11 个测试源文件，共 133 个 TEST/TEST_F 声明，grep 实测：bit_utils 2 + string_view 17 + stack_line_reader 4 + cpuinfo_aarch64 7 + cpuinfo_x86 69 + cpuinfo_arm 11 + cpuinfo_mips 7 + cpuinfo_ppc 5 + cpuinfo_s390x 4 + cpuinfo_riscv 5 + cpuinfo_loongarch 2 = 133）。106 个未执行用例按成因分三类，每类计数与报错证据如下：

### 类①：GTest 框架在 OHOS 的可执行性——框架本身完全可跑，0 个用例因框架未执行

**这是排除性结论，非成因分类**：GTest 1.17.0（Conan 制品仓预编译包）在 OHOS/arm64 上完全可执行——本适配 4 个实例化测试可执行（bit_utils_test/string_view_test/stack_line_reader_test/cpuinfo_aarch64_test）共 27 个用例全部真实执行、`0 failed / 0 skipped`（conan create 日志 `[ PASSED ]` 实测输出 + HMBS_UPSTREAM_TEST_RESULT marker: executed=27, passed=27, failed=0, skipped=0）。106 个未执行用例中**没有任何一个是因为 GTest 框架在 OHOS 上不可执行**——patch 0001 将上游 configure 期 GitHub 下载 googletest 改为 `find_package(GTest CONFIG REQUIRED)` 后，框架链路已打通并实证。

### 类②：需要宿主 CPU 特有寄存器/指令检测的用例——OHOS PC（arm64）真机无对应硬件，103 个

| 套件（源文件） | 用例数 | 检测的宿主硬件接口 |
|----------------|--------|--------------------|
| cpuinfo_x86_test.cc | 69 | x86 `cpuid` 指令 / `xgetbv`（SandyBridge/SkyLake/CascadeLake 等 CPUID 叶子解析） |
| cpuinfo_arm_test.cc | 11 | arm32 `HWCAP`/`HWCAP2` 半字 + `/proc/cpuinfo` 32 位格式（ODroid/RaspberryPi Zero/Nexus4 等 armv7 板卡） |
| cpuinfo_mips_test.cc | 7 | MIPS `getauxval` HWCAP 位（Loongson 等） |
| cpuinfo_ppc_test.cc | 5 | POWERPC auxv（POWER8/9/10） |
| cpuinfo_s390x_test.cc | 4 | s390x STFLE 位（z14/z15 HWCAP） |
| cpuinfo_riscv_test.cc | 5 | RISC-V hwcap 位（V 扩展等） |
| cpuinfo_loongarch_test.cc | 2 | LoongArch CPUCFG 寄存器 |
| **小计** | **103** | |

**构建层互斥证据**：上游 `test/CMakeLists.txt` 以宿主架构宏互斥生成测试目标——L62 `if(PROCESSOR_IS_X86)` / L80 `if(PROCESSOR_IS_ARM)` / L109 MIPS / L117 POWER / L125 S390X / L133 RISCV / L141 LOONGARCH。aarch64 目标下这些宏全为假，`add_executable` 不执行，**测试目标根本不生成**（非编译失败后排除，是 CMake 配置期即不注册）。

**编译器实测报错证据**（OHOS aarch64 clang 15.0.4 `--target=aarch64-linux-ohos -fsyntax-only` 强行编译 7 个非 aarch64 测试源，全部被上游头文件自身的平台守卫 `#error` 拦截，2026-09-10 本机实测复现）：

```
cpuinfo_x86_test.cc       → include/cpuinfo_x86.h:295:      error: "Including cpuinfo_x86.h from a non-x86 target."
cpuinfo_arm_test.cc       → include/cpuinfo_arm.h:118:      error: "Including cpuinfo_arm.h from a non-arm target."
cpuinfo_mips_test.cc      → include/cpuinfo_mips.h:71:      error: "Including cpuinfo_mips.h from a non-mips target."
cpuinfo_ppc_test.cc       → include/cpuinfo_ppc.h:146:      error: "Including cpuinfo_ppc.h from a non-ppc target."
cpuinfo_s390x_test.cc     → include/cpuinfo_s390x.h:106:    error: "Including cpuinfo_s390x.h from a non-s390x target."
cpuinfo_riscv_test.cc     → include/cpuinfo_riscv.h:22:     error: "Including cpuinfo_riscv.h from a non-riscv target."
cpuinfo_loongarch_test.cc → include/cpuinfo_loongarch.h:22: error: "Including cpuinfo_loongarch.h from a non-loongarch target."
```

即：即使绕过 CMake 互斥强行编译，上游头文件在 arm64 目标下也会 `#error` 硬拦截——这些用例在 arm64 真机上**连编译都不可能**（无 cpuid 指令、无 arm32 半字 HWCAP、无 MIPS/PPC/s390x/RISC-V/LoongArch 寄存器可读），属上游设计的跨架构天然互斥，非本适配排除。

### 类③：依赖非 Linux 内核系硬件能力查询接口的 aarch64 用例——OHOS/Linux hwcap 路径之外的 OS 专属分支，3 个

aarch64 套件（cpuinfo_aarch64_test.cc，7 个声明）内部再按 OS 互斥。Linux/OHOS 走 `getauxval(AT_HWCAP/AT_HWCAP2)` hwcap 路径（`CPU_FEATURES_OS_LINUX` 宏），已实例化 4 个用例（Aarch64FeaturesEnum + FromHardwareCap + FromHardwareCap2 + ARMCortexA53）**全部真实执行通过**——其中 FromHardwareCap/FromHardwareCap2 正是 hwcap 解析用例（上游测试基建 hwcaps_for_testing.cc 的 SetHardwareCapabilities 注入 AARCH64_HWCAP_FP/AARCH64_HWCAP_AES 等位组合，断言 GetAarch64Info 对 hwcap 位到 feature 位的映射，27/27 中含此 2 个）。

未执行的 3 个是**非 Linux OS 的硬件能力查询接口专属分支**（上游 `#elif` 宏剔除，OHOS 映射 `CPU_FEATURES_OS_LINUX` 时编译期不存在）：

| 用例 | 守卫宏（源码行号） | 断言的 OS 专属接口 | 与 OHOS 的关系 |
|------|--------------------|--------------------|----------------|
| FromDarwinSysctlFromName | `#elif CPU_FEATURES_OS_MACOS`（L335） | macOS `sysctlbyname("hw.optional.*")` | OHOS 为 Linux 内核系，无 sysctlbyname 硬件能力接口 |
| WINDOWS_AARCH64_RPI4 | `#elif CPU_FEATURES_OS_WINDOWS`（L397） | Windows `IsProcessorFeaturePresent()` | 同上，无 Win32 API |
| MrsMidrEl1_RPI4 | `#elif CPU_FEATURES_OS_FREEBSD\|\|OPENBSD`（L420） | FreeBSD `sysctl` ELF auxv 路径 + `MRS` 寄存器直读 | OHOS 无 BSD sysctl 硬件检测路径（该用例为 0.10→0.11 新增，仅 FreeBSD/OpenBSD 实例化） |

这 3 个用例断言的硬件能力查询接口（macOS sysctlbyname / Windows IsProcessorFeaturePresent / FreeBSD sysctl+MRS 直读）在 OHOS（Linux 内核系，走 getauxval/hwcap）上不存在，上游以 `#elif` OS 宏在编译期剔除，非运行失败。

### 小结

106 = 类② 103（跨架构宿主寄存器/指令互斥，CMake 不生成目标 + 头文件 #error 硬守卫）+ 类③ 3（非 Linux OS 硬件能力接口互斥，#elif 宏剔除）+ 类① 0（GTest 框架可执行性无任何影响——27 个实例化用例含全部平台无关/hwcap 解析用例已全过）。若要在 arm64 上"执行"其余 106 个，需要 x86/arm32/mips/ppc/s390x/riscv/loongarch 宿主硬件或 macOS/Windows/FreeBSD 目标环境，与 HarmonyOS PC（arm64/Linux 内核系）适配平台天然互斥。

执行侧 27/27 全过（100%）：bit_utils_test 2/2 + string_view_test 17/17 + stack_line_reader_test 4/4 + cpuinfo_aarch64_test Linux 分支 4/4（Aarch64FeaturesEnum + FromHardwareCap + FromHardwareCap2 + ARMCortexA53，前两者守卫 `#if CPU_FEATURES_OS_LINUX||FREEBSD||OPENBSD` 在 Linux 下成立）。

### 逐用例通过证据（2026-09-10 二次打回复核补强）

4 个实例化可执行逐一真实运行（非 ctest 聚合、非抽样）：bit_utils_test `[PASSED] 2 tests`（UtilsTest.IsBitSet/ExtractBitRange）、string_view_test `[PASSED] 17 tests`、stack_line_reader_test `[PASSED] 4 tests`（TruncatedLine/TruncatedLines 等）、cpuinfo_aarch64_test `[PASSED] 4 tests`（Aarch64FeaturesEnum/FromHardwareCap/FromHardwareCap2/ARMCortexA53），合计 27 通过/0 失败/0 跳过（HMBS_UPSTREAM_TEST_RESULT: executed=27, passed=27, failed=0, skipped=0）。

其中 8 个用例（stack_line_reader 4 + cpuinfo_aarch64 4）使用上游测试框架自带注入基建 hwcaps_for_testing.cc（SetHardwareCapabilities 注入 hwcap 位）与 filesystem_for_testing.cc（注入 /proc/cpuinfo 内容）——这是上游自己的确定性测试设计（上游任何架构 CI 均同方式运行），非本适配引入的 stub/跳过；真机硬件路径由 test_package/test_ohos.c 在 OHOS 运行时与 /proc/cpuinfo 实测双向交叉核对覆盖（词级精确匹配双向断言：库报出则 cpuinfo 必含、cpuinfo 含则库必报出；implementer=72 part=3331 实测全过；修复 AI 检视 P2 断言空转 + P3 strstr 子串误匹配/strtol 无 endptr 校验/注释不符三问题）。口径对齐：133 = 27（实例化且全部通过）+ 106（未实例化豁免）；审核计数请以四个 GTest 汇总行（2+17+4+4=27）为准，test_package 的 ctest 汇总（消费者测试，两个可执行）属适配新增测试，不计入上游 133 口径。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 时 googletest 下载失败 | 上游在 configure 期 `git clone https://github.com/google/googletest.git`，OHOS CI 无法访问 GitHub | patches/0001：改为 `find_package(GTest CONFIG REQUIRED)` + 将裸 `gtest`/`gmock_main` target 映射到 Conan gtest 包的 `GTest::gtest`/`GTest::gmock_main`；conanfile `test_requires("gtest/1.17.0")`（0.9.0 同款方案，0.11.0 行号偏移后重新生成 patch） |
| 2 | 0.9.0 patch 直接复用失败 | 0.11.0 主 CMakeLists 删除了 CMAKE_CXX_STANDARD 块，hunk 上下文不匹配 | 按 0.11.0 orig/work 重新 diff 生成 0001 patch，`patch -p1 --dry-run` 验证干净应用 |

## 源码修改

- `patches/0001-CMakeLists.txt.patch`：测试部分改用外部 GoogleTest（find_package + 裸 target 映射）

## 依赖版本

- gtest/1.17.0（test_requires，OHOS armv8 预编译已发布——W0 conan download 实测）
- gmock/1.17.0（gtest 传递依赖）

## 验证结果

```bash
conan create . --user=ohpcd --channel=stable -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64   # EXIT=0
# 上游测试: 27/27 PASSED (bit_utils 2 + string_view 17 + stack_line_reader 4 + cpuinfo_aarch64 4)
# test_package: 2/2 PASSED (test_cpu_features + test_cpu_features_ohos)
```

## 注意事项

- conandata.yml 主 URL 为官方 GitHub tag（R39 官方源），CI 侧自动添加镜像 fallback
- 全量通过率口径：27/133（20.3%）；当前配置可执行集合：27/27（100%）
- 版本号策略（R37）：0.11.0 为上游正式版本，首次适配直接用上游版本号
---

**编译结束**: 2026-09-09 23:31
**最终状态**: published

## Staging 验证

- packaging/cpu_features-0.11.0-ohos-aarch64.tar.gz：libcpu_features.a + include/cpu_features/ + cmake config + list_cpu_features，产物清单与 conan package 一致
- .staging-verified：staging 验证完成标记（2026-09-10）
