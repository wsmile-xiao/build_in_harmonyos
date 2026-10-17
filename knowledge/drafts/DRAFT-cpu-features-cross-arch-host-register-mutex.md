# DRAFT：CPU 探测类库 GTest 套件的跨架构宿主寄存器互斥论证范式——实例化边界拆解 + 逐用例证据链

## 错误特征 / 触发场景

```
场景：CPU/硬件探测类库的 GTest 套件在 arm64/OHOS 交叉环境适配
表象：上游声明 N 个 TEST，实际只能实例化执行 M 个（M << N），
      申报口径混乱会被 rule4 审查打回（实测"2/133"误报被打回两轮）
伴随证据：
  Including cpuinfo_x86.h from a non-x86 target.   ← 上游头文件 #error 硬守卫
  test/CMakeLists.txt: if(PROCESSOR_IS_X86) ...    ← 架构宏互斥注册
```

## 根因（机制层）

CPU 探测类库的测试套件天然按**宿主架构 × 宿主 OS** 双维度互斥切分：

1. **架构维度**（103/106 未实例化的来源）：
   - `test/CMakeLists.txt` 用 `PROCESSOR_IS_X86/ARM/MIPS/POWER/S390X/RISCV/LOONGARCH` 宏守卫 `add_executable`——非目标架构的测试目标在 CMake 配置期即不注册（不是编译失败被排除）
   - 上游头文件自身带 `#error` 平台硬守卫（`cpuinfo_x86.h:295: #error "Including cpuinfo_x86.h from a non-x86 target."` 等 7 个头文件逐行实测）——即使绕过 CMake 强行 `-fsyntax-only` 编译也被拦
   - 机制本质：这些用例断言**宿主 CPU 特有寄存器/指令**（x86 `cpuid`/`xgetbv`、arm32 半字 `HWCAP`、MIPS/PPC/s390x STFLE/RISC-V/LoongArch CPUCFG），arm64 目标上不存在对应硬件，**连编译都不可能**——上游设计的跨架构天然互斥，非适配排除
2. **OS 维度**（3/106）：
   - 同架构套件内部按 OS 宏 `#elif` 编译期剔除：aarch64 的 `FromDarwinSysctlFromName`（`CPU_FEATURES_OS_MACOS`，sysctlbyname）、`WINDOWS_AARCH64_RPI4`（`CPU_FEATURES_OS_WINDOWS`，IsProcessorFeaturePresent）、`MrsMidrEl1_RPI4`（`CPU_FEATURES_OS_FREEBSD||OPENBSD`，sysctl+MRS 直读）
   - OHOS 映射 `CPU_FEATURES_OS_LINUX` 走 `getauxval(AT_HWCAP/AT_HWCAP2)` hwcap 路径——该路径的解析用例（FromHardwareCap/FromHardwareCap2）**恰是实例化集合的一部分且真跑通过**

## 解法（四步论证范式）

1. **声明计数**：`grep -c "TEST\(_F\)\?(" test/*.cc` 得声明总数，逐源文件分列
2. **实例化拆解**：读上游 CMakeLists 架构宏守卫行 + 套件内 `#elif` OS 宏，得出双维实例化集合
3. **报错证据采集**（三条互补，机器可验证）：
   - CMake 配置期：非目标架构测试目标不注册
   - 编译器实测：`clang --target=aarch64-linux-ohos -fsyntax-only` 强编非目标架构测试源 → 逐行记录 `#error` 硬拦证据
   - 运行期：实例化可执行**逐一真实运行**，记录每个的 GTest 原始汇总行（`[ PASSED ] N tests` + exit=0），非 ctest 聚合抽样
4. **真机闭环**（hwcap 专项）：test_package 交叉核对——库报出特性与 `/proc/cpuinfo` 实测**双向词级断言**（库报出⇄cpuinfo 必含），证明 getauxval/hwcap 宿主探测在 OHOS 真实工作（implementer=72 part=3331 实测）

**口径公式**：`声明总数 = 实例化通过 + 未实例化豁免（三类分组：跨架构寄存器互斥 + 非 Linux OS 接口互斥 + 框架可执行性）`，每组带报错证据。

```bash
# 证据采集命令（可复制）
grep -c "TEST\(_F\)\?(" test/*.cc                                    # 声明计数
clang --target=aarch64-linux-ohos -fsyntax-only test/cpuinfo_x86_test.cc 2>&1 | head -2   # #error 证据
ctest -R "bit_utils_test" --output-on-failure                        # 逐可执行运行
```

## 验证

PR #9229 feat(cpu_features): 0.11.0（任务 #6885）：
- CI **#43816 绿**（2026-09-10 20:04），27 个实例化用例真跑全过（bit_utils 2 + string_view 17 + stack_line_reader 4 + cpuinfo_aarch64 4，逐用例 GTest 输出在 PR 正文）
- Septest 12:15/19:09 两轮 rule4 打回（口径误报"2/133"）→ 补齐三类分组证据链 + 逐用例输出后获认可（21:27 全链闭环）
- test_package/test_ohos.c hwcap 真机交叉核对全过

## 适用范围（跨库复用）

任何**硬件探测/系统信息类库**的 GTest 套件在交叉/异构平台的测试边界论证：
- cpu_features / infoware / hwloc / cpuid 类（宿主寄存器互斥）
- 其他按 PROCESSOR_IS_* / OS 宏互斥注册测试的上游（CMake 宏互斥范式通用）
- rule4 测试通过率申报的豁免分组方法论（逐项技术原因 + 报错证据 + 口径对齐公式）

## 关联与区别

- **DRAFT-infoware-cpuid-arch-guard**（PR #8568）：同类库的**编译失败**场景（x86 内联汇编在 aarch64 报 invalid output constraint，走源码守卫+零值回退修法）——本条是**测试实例化边界论证**（测试能编译但架构互斥不注册），互补不重叠
- **E292**（分层 ctest 迁移）：CTest/GTest 跨平台迁移的通用机制——未覆盖"宿主寄存器互斥"这一硬件维度豁免论证
- **E332**（highway standalone runner）：BUILD_TESTING 构建形态切换——非架构互斥场景

## 红线

- 申报口径必须**唯一**（实例化子集通过率 vs 声明总数拆解二选一作主口径，两者用公式对齐呈现，消除歧义表述）
- 未实例化豁免必须逐项分组 + 机器可验证报错证据，禁止笼统"平台不支持"
- 实例化子集必须逐可执行真跑（GTest 原始汇总行），禁止 ctest 聚合冒充逐用例
