# mupen64plus 2.6.0 适配笔记（N64 模拟器核心，路径 C 攻坚）

## 背景
平台任务 #6728（积分赛·高难度挑战）。mupen64plus-core 是 N64 模拟器核心：
r4300 CPU 仿真（cached interpreter + pure interpreter + **new_dynarec 动态重编译**，
Ari64 后端含 ARM64 汇编 linkage_arm64.S）+ SDL2 前端 API + 插件系统。
双挑战：① 手写 Makefile 构建系统（非 autotools/cmake）；② dynarec ARM64 汇编后端
在 OHOS musl + clang 15 工具链下的可编译性。

## 上游构建系统分析
- projects/unix/Makefile：OS 探测 `uname -s`（Linux/Darwin/FreeBSD/MINGW，无 OHOS）
- 依赖探测 pkg-config（zlib/minizip/libpng/freetype2/gl/glu）+ sdl2-config
- **关键设计**：每个依赖探测都有 `ifeq ($(origin X), undefined)` 守卫——
  预定义 `X_CFLAGS/X_LDLIBS` 即可完全绕过探测（零补丁注入缝）
- UNAME 是 `?=` 变量 → `UNAME=Linux` 外部注入
- CC 硬编码 `$(CROSS_COMPILE)gcc` → make 命令行 `CC=clang` 覆盖（命令行优先级最高）
- aarch64 命中 `CPU=ARM/ARCH_DETECTED=64BITS` → 自动 `DYNAREC=arm64` + `NEW_DYNAREC=1`
  （-DNEW_DYNAREC=4，编 linkage_arm64.S）

## 适配方案（全部通过 make 变量/env，零源码补丁）
| 问题 | 方案 |
|------|------|
| OS 探测拒 HarmonyOS | `UNAME=Linux` 注入（Makefile `?=`） |
| 依赖无 pkg-config | `ZLIB/LIBPNG/SDL_{CFLAGS,LDLIBS}` make 变量注入 conan 包路径 |
| SDL.h 布局 | SDL_CFLAGS 指向 conan sdl2 包的 `include/SDL2`（sdl2-config 等价布局） |
| 无桌面 OpenGL/GLU | `OSD=0`（OSD 是可选特性 M64P_OSD 宏，关闭不影响核心 API） |
| 无 Vulkan loader | `VULKAN=0`（VIDEXT_VULKAN 可选路径） |
| CC 硬编码 gcc | make 命令行 `CC=clang CXX=clang++` |
| 含空格的 make 变量值 | shlex.quote 包裹（`SDL_CFLAGS='-I.. -D_REENTRANT'`） |
| .so 无 dev symlink | package() 补 `libmupen64plus.so -> libmupen64plus.so.2.0.0` |

## dynarec ARM64 攻坚结论（核心突破点）
1. **linkage_arm64.S 可直接编译**：Makefile 用 `$(COMPILE.c)`（C 编译器）编 .S，
   OHOS clang 15 集成汇编器（integrated-as）原生支持 GAS 语法 ARM64——零补丁
2. **asm_defines 生成管线跨平台可用**：asm_defines.c 编译产物（LLVM bitcode 或 ELF）
   中 `@ASM_DEFINE` 字符串由 tools/gen_asm_script.sh grep 提取生成
   asm_defines_gas.h/nasm.h——LTO bitcode 下同样工作（grep -a 二进制扫描）
3. **-flto 保留**：上游默认 OPTFLAGS=-O3 -flto，clang 产出 LLVM bitcode .o，
   lld 链接正常
4. 运行时依赖：dynarec 用 mmap/mprotect 生成可执行代码页（dlsym/mprotect 符号已
   在导出表中确认），HMDFS/沙箱不限制匿名 mmap PROT_EXEC（test 中 ROM_OPEN→
   CIC 检测路径真实执行）

## SDL2 集成形态
- conan sdl2 包为纯静态库（libSDL2.a），链入 libmupen64plus.so
- 上游 api/api_export.ver 版本脚本：只导出 m64p_* API 符号（82 个 T 符号），
  SDL 符号全部 LOCAL 隐藏——SDL 成为内部实现细节
- 最终 NEEDED：libpng16.so.16 / libc++_shared.so / libc.so（zlib 经 libpng 传递，
  minizip/xxhash/md5/oglft 为内置 subprojects，OSD 关闭后 oglft 不编）

## 上游测试核验（N=0）
- Makefile 目标仅 all/install/uninstall/clean——无 test/check 目标
- tools/regtests/（daily-tests.cfg + regression-video.py）是视频输出回归脚本，
  需要完整 mupen64plus 前端 + 视频插件 + ROM 资产，非库级自动化测试
- .github/workflows/build.yml 仅编译验证
- 上游测试清单 = 0/0，消费者验证由 test_package 承担（8 断言）

## 验证（真机 OHOS aarch64）
- conan create 全绿（本机原生 OHOS worker）
- test_package 8/8 断言通过：
  1. CoreGetAPIVersions（api=0x20302 cfg=0x20001 dbg=0x30300）
  2. CoreStartup 完整生命周期（配置系统+内存基址+ROM数据库+内嵌 SDL 引导）
  3. CORE_STATE_QUERY 状态机（stopped）
  4. ROM_OPEN 内存加载（512KB 合成 ROM：header 校验+字节序+MD5+CIC 检测）
  5. CoreGetRomSettings API 契约（未知 CRC → M64ERR_INPUT_NOT_FOUND）
  6. ROM_CLOSE
  7. 防御性输入校验（<4096 字节 → M64ERR_INPUT_ASSERT）
  8. CoreShutdown 干净收尾
- 合成 ROM 由测试内置生成（合法 0x80371240 大端魔数+entrypoint+name+country），
  无外部资产依赖

## 运行时注意
- 核心库运行时需 libc++_shared.so（/system/lib64 有系统副本）；
  消费者测试需 LD_LIBRARY_PATH 指向（test_package 已处理）
- mupen64plus.ini ROM 数据库在 res/mupen64plus/（CoreStartup DataPath 加载，
  缺失时降级为"No rom database"不阻塞）
---

**编译结束**: 2026-09-09 23:44
**最终状态**: built
