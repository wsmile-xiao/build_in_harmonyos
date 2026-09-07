# ═══ Draft knowledge entry — 上游 x86 内联汇编在 aarch64 的架构宏守卫 + 零值回退 ═══
# Timestamp: 2026-09-06
# Software: infoware 0.6.0（模式适用于任何含 x86 CPUID/XGETBV 汇编的库）
# Gate: PR #8568（任务 #5452）；设备 conan-verify G2 首跑失败日志
# Status: UNMATCHED — needs human/AI review to promote to E-entry

id: DRAFT-infoware-cpuid-arch-guard
severity: 2
category: compat|architecture|inline-asm|portability|source-patch
trigger_tool: clang / cmake / make / conan
phase: compilation
approach: 用架构宏 #if defined(__x86_64__) || defined(__i386__) 守卫原 x86 实现，
  #else 提供 cpuid 零叶 + xgetbv=0 回退；改前逐个核验 cpuid( 调用方对零值安全
  （只做位测试、无除法/索引）；补丁只用架构宏，禁止平台宏（R8/PF5）；
  refresh-patch --auto 生成并登记 patch_type: portability

keywords: cpuid, __cpuid_count, cpuid.h, xgetbv, invalid output constraint, =a,
  aarch64, __x86_64__, __i386__, 架构守卫, 内联汇编, 零值回退, GLOB_RECURSE

error_signature: invalid output constraint '=a' in asm|error: invalid output constraint
match_keywords: cpuid, invalid output constraint, xgetbv, aarch64, __x86_64__

root_cause: 上游把 CPU 探测实现放在 cpuid_non_windows.cpp（#ifndef _WIN32 即编译），
  内嵌 <cpuid.h> 的 __cpuid_count 与 xgetbv 汇编（"=a"/"=d" 约束）为 x86 专有；
  CMake GLOB_RECURSE 把它编入所有平台，aarch64 clang 在 asm 约束校验期报 6 处
  "invalid output constraint '=a' in asm"，无编译选项可绕过。上游无 disable-asm
  configure 开关（区别于 E016 的 reconfigure-no-asm 场景），删文件又致 cpuid()
  符号缺失链接失败。
affected_scope: 任何在"非 Windows"通用源文件内嵌 x86 CPUID/XGETBV/RDTSC 汇编的
  C/C++ 库（系统信息、性能计数、加密优化类）在 aarch64/arm/riscv 的 OHOS 适配

rec_priority: 1
rec_impl: source-patch-arch-guard
verification: conan create G2 通过；设备 ctest 4/4；clang -Wall -Wextra -pedantic 零警告；
  CI build #40887 通过

similar_to: E016（reconfigure-no-asm：仅当存在 configure 关闭开关时适用，本模式适用
  于无开关且需保 API 场景）
forbidden: 补丁用平台宏 __OHOS__（PF5 拦截）；删文件不补符号（链接失败）；
  未核验消费方零值安全就上零回退（运行期除零/越界）
