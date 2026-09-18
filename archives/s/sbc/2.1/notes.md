# sbc 2.1 适配笔记

## 编译环境

- 构建系统: autotools（configure 预生成；AC_INIT([sbc],[2.1])）
- 平台任务: contrib-10404（sbc 2.1），claimer Ember5843，认领 2026-09-16T10:02Z
- 目标平台: HarmonyOS PC arm64（clang 15 / musl），本机原生构建
- 依赖: **无外部依赖**（纯 C 编解码器）
- 上游: kernel.org 蓝牙栈（https://www.kernel.org/pub/linux/bluetooth/）
- 源码 sha256: `426633cabd7c798236443516dfa8335b47e004b0ef37ff107e0c7ead3299fcc2`
- 语言实测（R47 lang-preflight）: 11 文件全部 C，主体 100%

## 源码面貌（摸底结论）

- 交付形态: `libsbc.a/.so` + `sbcenc`/`sbcdec`/`sbcinfo` 三个命令行工具 + `sbc/sbc.h`
- configure 预生成；本仓 autotools 全套先例直接适用（显式三元组、bash、
  umask 077→022、stdin /dev/null、CC 导出、LD_LIBRARY_PATH 清空盾）
- 上游无测试套件（src/ 仅三个工具源码）

## 移植要点

1. 本仓 autotools 先例全套适用，无特殊补丁
2. sbctester（上游自测工具）硬依赖 libsndfile——平台不可得，用上游自带
   --disable-tester 开关排除（库与编解码工具不受影响）
3. 消费者测试走真实编解码往返：sbc_encode 一帧 → sbc_decode 解回，
   断言帧结构契约（解码字节数与输入严格一致）
3. 工具二进制随包交付（bin/），L2 门禁可验证

## 状态

- [x] 配方四件套
- [x] 设备实机 conan create + conan-verify + 消费者测试
- [x] push / PR / 平台绑定 / 提审
