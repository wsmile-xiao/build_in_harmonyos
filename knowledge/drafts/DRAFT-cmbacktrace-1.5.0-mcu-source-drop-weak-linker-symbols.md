# DRAFT-cmbacktrace-1.5.0-mcu-source-drop-weak-linker-symbols：MCU source-drop 库在 OHOS 的弱符号链接脚本边界 + 优雅降级

> Contributor: pc2-40 | Status: Draft | Updated: 2026-09-19
> Source: cmbacktrace 1.5.0 适配（task cmbacktrace-1.5.0-r01-pc2-40-20260918T190817Z）

## 背景

cmbacktrace 1.5.0（armink/CmBackTrace）是 ARM Cortex-M 故障回溯库，以
"源码即插"（source-drop）形态分发：单编译单元 `cm_backtrace/cm_backtrace.c`
+ 头文件，上游**无任何构建系统**（无 configure/make/CMake）。直接按普通库
编译会遇到三层障碍：

1. 配置头 `cmb_cfg.h` 默认留空宏（`cmb_println`、`CMB_CPU_PLATFORM_TYPE`），
   预处理阶段直接 `#error`；
2. `cm_backtrace.c` 引用四个链接脚本符号 `CMB_CSTACK_BLOCK_START/END`、
   `CMB_CODE_SECTION_START/END`（对应 MCU 链接脚本的 `_sstack/_estack/_stext/_etext`），
   非 MCU 平台链接必失败；
3. 回溯/故障诊断依赖 Cortex-M 专属语义（BL/BLX Thumb 指令反汇编检查、
   `MRS msp/psp` 内联汇编、NVIC 寄存器映射），在 OHOS aarch64 上不适用。

## 修复（三层）

**① cmb_cfg.h 默认配置补丁（0001）**：`cmb_println` 填 printf 实现、
`CMB_USING_BARE_METAL_PLATFORM`、`CMB_CPU_PLATFORM_TYPE=CMB_CPU_ARM_CORTEX_M4`、
`CMB_PRINT_LANGUAGE_ENGLISH` —— 库"开箱即编译"；用户仍可用 `CMB_USER_CFG`
自带配置覆盖。

**② 链接脚本符号 weak 化补丁（0002）**：

```c
#elif defined(__GNUC__)
-    extern const int CMB_CSTACK_BLOCK_START;
+    extern const int CMB_CSTACK_BLOCK_START __attribute__((weak));
    /* ... END / CODE_SECTION_START / CODE_SECTION_END 同理 */
```

weak 声明使符号在未定义时解析为 0：链接通过；`cm_backtrace_init()` 检测
`main_stack_size==0` 打印文档化提示 "Unable to get the main stack information"
并返回（上游设计路径，不崩溃）。消费方在链接脚本/源码定义真实边界即自动覆盖。

**③ 架构专属语义如实优雅降级**：aarch64 上 `MRS %0, msp` 仅产生 operand-width
警告不阻断（这些函数只在 MCU 故障路径被调用）；`cm_backtrace_call_stack()`
因 BL/BLX Thumb 语义不适用返回 0 深度 —— 鸿蒙专项测试断言 `depth==0` 且
进程正常退出（exit 0），如实记录为优雅降级，不得伪造回溯结果。

## 验证

- `conan-verify` G0-G4 + L2/L4/L5 全 PASS；W3 本地 CI L0/L1/L1e/L4/L5 全 PASS
- test_package 消费者测试 1/1（init / firmware_info / call_stack 公开 API）
- 鸿蒙专项测试（reports/ohos-test/ohos_test.c，仅用已安装头文件+lib 链接运行）：
  init 打印栈配置提示、firmware_info 输出版本、call_stack depth=0、exit 0
- 库纯静态无 bin/（R38 不需 commands.json）；无 requires（R49 不需注入 prefix）

## 适用边界

- 适用：MCU/嵌入式目标、source-drop、无构建系统、引用链接脚本符号的 C 库
  （故障回溯、RTOS 组件、外设驱动等）在 OHOS PC/CI 的 Conan 适配
- 反例：有 CMake/Make 的上游走普通构建族模板；weak 符号为 0 时
  `cm_backtrace_init` 不置 init_ok，消费方测试不得在未提供边界时调用
  assert/fault 路径（会死循环）；弱符号依赖 ELF weak 语义，MSVC 不适用
- 上游测试：MCU 库通常无测试框架（本库 source_declared_total=0，demos 为
  MCU 工程不计独立用例），台账须如实附清点证据

## 查重差异（七轴）

| 轴 | 结论 | 说明 |
|----|------|------|
| exact_duplicate | false | 无任何条目覆盖"MCU source-drop 库 + 弱符号链接脚本边界 + 优雅降级"组合 |
| causal_duplicate | false | E085 弱符号是 musl 缺 pthread_cancel（libc API 探测），根因不同；E450 弱符号在 AVR 交叉 sysroot（host/target 分离），根因不同 |
| trigger_overlap | partial | 无构建系统与 E281/E305（资源包）及 enet 单头库草稿部分重叠；链接脚本符号缺失是全新触发 |
| solution_overlap | partial | weak 符号技术散见于 E085/E450，但"链接脚本 extern 符号 weak 化保链接"无人覆盖 |
| combination_novelty | true | source-drop 单 TU + weak 链接脚本符号 + cmb_cfg 默认配置 + 架构语义优雅降级，组合全新 |
| boundary_novelty | true | 首次明确"MCU 专属语义在非 MCU 平台如实降级（depth=0 属预期，非失败），不得伪造"边界 |
| test_migration_novelty | true | 鸿蒙专项测试用弱符号默认值断言优雅降级（depth==0 + exit 0），为 MCU 库新增验证模式 |

关系：`similar_to: [E085, E277, E281, E305, E450, DRAFT-enet-2.7.0-single-header-impl-lib]`、
`caused_by: []`、`prerequisite_of: []`、`conflicts_with: []`
