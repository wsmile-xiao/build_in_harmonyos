# sdl12-compat 1.2.68 HarmonyOS PC 预分析

## 结论

适配风险低。项目是单一 C 共享库，使用标准 CMake，唯一必需依赖为已发布的 `sdl2/2.30.10`。核心兼容层不直接依赖 Linux 图形、音频或输入设备 API，而是在运行时通过 SDL2 后端工作。

## 平台扫描

| 项目 | 结果 | 处理 |
|---|---|---|
| 构建系统 | CMake | 使用 Conan `CMakeToolchain`/`CMakeDeps` |
| 必需依赖 | SDL2 headers | 锁定 `sdl2/2.30.10` 已审计制品，并从 Conan 包注入头文件路径 |
| Linux 专属接口 | `dlopen`/`dlsym` 兼容路径 | HarmonyOS libc 支持，保留上游实现 |
| 图形/音频服务 | 由 SDL2 运行时后端提供 | CI 使用 dummy video/audio 驱动 |
| 汇编/SIMD | 可选 x86 intrinsics 探测 | aarch64 探测失败后由上游禁用，不需补丁 |
| 上游测试 | 32 个独立程序，无 CTest 注册 | 构建全部程序，执行 14 个可无人值守程序；其余 18 个逐项记录设备/交互限制 |
| 产物 | `libSDL-1.2.so`、`libSDL-1.2.so.0` 相对链接、包内 SDL2 runtime 和头文件 | 检查 ELF、SONAME、NEEDED、RUNPATH、签名 |

## 测试边界

交互式窗口、物理输入事件、CD-ROM、OpenGL/GPU、真实音频播放以及只能由外部信号终止的程序不适合无人值守 CI。它们仍会被编译，确保 API 与链接兼容；自动执行的 14 个上游程序覆盖版本、平台、错误处理、字符转换、RWops、键名、动态加载、线程、dummy 视频信息、软件 blit、信号量、定时器和摇杆枚举。消费者测试另行验证 dummy 视频 surface、事件队列、定时器及包内 SDL2 运行时加载。
