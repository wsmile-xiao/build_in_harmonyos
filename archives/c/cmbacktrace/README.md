# CmBackTrace

## 简介

CmBackTrace 是一款面向 ARM Cortex-M 微控制器的故障回溯库，提供：
- 断言（assert）定位：打印断言发生时的函数调用栈
- 故障（fault）诊断：解析 Cortex-M 的 MemManage/Bus/Usage/Hard 故障状态寄存器
  并给出原因与调用栈
- 调用栈回溯：基于栈上的 LR 值 + BL/BLX 指令反汇编校验还原调用链

## OHOS 适配

- 上游是 source-drop 形态（单编译单元 + 头文件），无 configure/make/CMake，
  配方直接编译 `cm_backtrace/cm_backtrace.c` 为静态库
- 补丁 0001：cmb_cfg.h 提供可用默认配置（printf 版 cmb_println、bare-metal、
  Cortex-M4、英文输出）
- 补丁 0002：链接脚本符号（CMB_CSTACK_BLOCK_START/END、
  CMB_CODE_SECTION_START/END）声明为 weak，非 MCU 平台可正常链接；
  消费方定义真实栈/代码边界即可启用完整回溯
- 在 OHOS aarch64 上，Cortex-M 语义的调用栈回溯返回 0 深度属预期；
  公开 API（init/firmware_info/call_stack）可编译、链接、运行

## 依赖

无外部编译依赖。

## 功能验证

```bash
# 消费者用例：调用公开 API（test_package/test.c）
./test_cmbacktrace
# 预期输出：Firmware name: ... / cm_backtrace_call_stack depth=0 / OK
```

## 参考

- 官网: https://github.com/armink/CmBackTrace
- 源码: https://github.com/armink/CmBackTrace/archive/refs/tags/1.5.0.tar.gz
