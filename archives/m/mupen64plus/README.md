# mupen64plus

Mupen64Plus 核心库——任天堂 64 模拟器核心（r4300 CPU 解释器 + Ari64 新动态重编译器 new_dynarec ARM64 后端 + SDL2 前端 API）。

- 上游: https://github.com/mupen64plus/mupen64plus-core
- 许可证: GPL-2.0-or-later
- 语言: C（含 ARM64 GAS 汇编 linkage_arm64.S）
- 构建系统: 手写 GNU Makefile（projects/unix/Makefile，无 configure）
- 分类: library-tool（仿真核心库，仅产出 libmupen64plus.so）

## 平台适配要点（OHOS PC / aarch64）

- dynarec ARM64 后端原生可用：NEW_DYNAREC=4 路径（linkage_arm64.S + asm_defines 生成管线）在 OHOS clang 15 下零补丁编译
- SDL2 静态链接进核心库（版本脚本限制只导出 m64p_* API）
- OSD=0（无桌面 OpenGL/GLU）、VULKAN=0（无 Vulkan loader）
