# sdl12-compat 1.2.68 适配笔记

## 编译环境

- 目标平台：HarmonyOS PC aarch64
- 构建系统：CMake
- 编译器：HarmonyOS clang/clang++
- 源码：上游 `release-1.2.68` 标签归档
- 必需依赖：`sdl2/2.30.10`（OHPCD 已发布）

## 适配方案

sdl12-compat 将 SDL 1.2 ABI/API 转换到 SDL2。上游构建只需要 SDL2 头文件，运行时通过动态加载查找 SDL2。配方使用 Conan 2 的 `CMakeDeps` 和最小补丁，从已声明的 Conan SDL2 包注入头文件路径，避免误用系统 SDL2。源码 URL 中的连字符使用等价 `%2D` 编码，并在 `source()` 中兼容 W3 预下载缓存的字面 `%2D` 文件名，以规避框架 URL 正则截断问题。

已发布的 `sdl2/2.30.10` 仅提供 PIC 静态制品，而 sdl12-compat 按上游设计必须在运行时 `dlopen()` SDL2。配方因此锁定已审计的 SDL2 recipe revision、package ID、package revision 和 `shared=False` 选项，以 `--whole-archive -z defs` 重链接为包内私有 `libSDL2-2.0.so.0`；构建后自动检查 AArch64、相对 SONAME、仅允许的 NEEDED 和无 RPATH/RUNPATH。该 SDL2 派生运行时属于明确的 bundled/relinked runtime，并随包交付独立的 `SDL2-LICENSE.txt`。

构建开启 `SDL12TESTS` 和开发文件，关闭上游仅支持 Linux 的可选静态兼容库。交付共享库、包内 SDL2 运行时、SDL 1.2 头文件、`libSDLmain.a`、pkg-config 文件、`sdl-config` 和两个上游项目的许可证。

## 测试策略

上游 CMake 构建 32 个测试程序，但没有 `add_test()`/CTest 注册。多数程序需要窗口、键鼠、摇杆、CD-ROM、OpenGL、真实音频设备或人工退出，不适合无人值守 CI。因此：

1. 构建全部 32 个上游测试程序；
2. 在 dummy video/audio 后端自动执行 14 个能确定性退出的程序：`testver`、`testplatform`、`testerror`、`testiconv`、`testfile`、`testkeys`、`testloadso`、`torturethread`、`testvidinfo`、`testblitspeed`、`testsem`、`testthread`、`testtimer`、`testjoystick`；其中带参数程序使用固定参数以覆盖动态加载、blit、信号量和 timer 路径；
3. 其余 18 个程序逐项归类为需人工输入/退出、真实音频或 CD-ROM、OpenGL/GPU，或 dummy 后端明确不支持的 gamma 路径；不把“编译成功”虚报为“测试通过”；
4. 通过独立 Conan 消费者测试真实链接 `SDL::SDL`，将 Conan 解析出的包内 SDL2 路径传入测试，并以 Conan 包目录 `/p/b/.../p/lib/libSDL2-2.0.so.0` 后缀对照 `/proc/self/maps`，兼容不同 Conan home 及 HarmonyOS HMDFS 对绝对路径的别名映射；随后在 dummy video/audio 后端验证版本、surface 绘制、事件队列与 timer API；
5. L5 检查共享库 ELF 架构、相对 SONAME、无绝对 RUNPATH/NEEDED 和 `.codesign` section。

## 已知边界

无人值守构建不验证真实显示、GPU/OpenGL、真实音频输出、物理输入事件和 CD-ROM。18 个未执行程序的具体限制和命令边界记录在 `evidence/upstream-test-matrix.md`；该限制只影响设备/交互后端覆盖，不影响 SDL 1.2 兼容库的构建、动态加载和已执行的 headless API 验证。当前流程仅支持 HarmonyOS PC aarch64 原生构建，因为上游测试和签名工具必须在目标系统执行。上游 `testplatform` 将 HarmonyOS 报告为 Linux，这是 SDL 1.2 兼容语义，已披露但不宣称原生 HarmonyOS 平台字符串。`testiconv` 仅作为执行型 smoke test，不计作逐输出一致性断言。
---

**编译结束**: 2026-08-15 16:20
**最终状态**: built
