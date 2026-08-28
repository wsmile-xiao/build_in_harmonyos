# julius 1.8.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-26
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 下载源码: https://github.com/bvschaik/julius/archive/refs/tags/v1.8.0.tar.gz
2. CMake 配置（配方 generate() 自动注入）:
   - CMAKE_SYSTEM_NAME=Linux（E092 平台绕过）
   - CMAKE_SYSTEM_PROCESSOR=aarch64
   - CMAKE_POLICY_VERSION_MINIMUM=3.5（CMake 4.x 兼容）
   - SDL2_INCLUDE_DIR/SDL2_LIBRARY/SDL2_MIXER_INCLUDE_DIR/SDL2_MIXER_LIBRARY（模块模式 Find 注入）
3. 编译: cmake --build . --parallel 1（R9 规避 HMDFS mkfifo 坑）
4. 测试: cmake.test()（make test → ctest 36 个集成测试）
5. 安装: cmake.install() → bin/julius，随后 llvm-objcopy 剥 .codesign + binary-sign-tool 自签

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 不识别 HarmonyOS 平台 | OHOS 无对应 CMake 平台（E092） | CMAKE_SYSTEM_NAME=Linux |
| 2 | 上游 FindSDL2/FindSDL2_mixer 找不到依赖 | 模块模式 Find 不走 CMakeDeps config | generate() 注入 SDL2_INCLUDE_DIR 等 4 个 cache 变量 |
| 3 | CMake 4.x 报版本过旧 | 上游 cmake_minimum_required(3.1) | CMAKE_POLICY_VERSION_MINIMUM=3.5 |
| 4 | 产物运行报 Operation not permitted | OHOS ELF 未签名 | llvm-objcopy --remove-section .codesign + binary-sign-tool sign -selfSign 1 |
| 5 | 平台 CI worker 沙箱 lld 加载 libxml2.so.16 失败（Error relocating symbol not found） | CI worker（AppSpawn, USER=100）动态加载器无法按 lld RUNPATH($ORIGIN/../lib) 命中 SDK llvm/lib，编译链在 CMake 编译器自检即断 | build() 内 clang -print-resource-dir 动态推导 SDK llvm/lib 前缀并注入 LD_LIBRARY_PATH（优雅降级：推导失败/缺 libxml2.so.16 时返回 None 不注入；无硬编码路径，R33）；属 worker 沙箱环境兼容 workaround，根因（worker 加载器配置）仍需 @CI 维护者修复，设备端无法复现该缺陷，worker 侧效果需平台 CI 实证 |

## 依赖版本

- sdl2 2.30.10（ohpcd 已发布）
- sdl2_mixer 2.8.1（ohpcd 已发布，julius 是其首个消费者）
- libpng 可选（回退捆绑 ext/png + ext/zlib）

## 验证结果

- conan create 通过，build() 内 36 个 CTest 集成测试真实执行
- test_package 用 julius --help（输出含 Usage）+ 非法参数负向断言（E003）验证二进制真实性

- 官方 CI（build_and_test.sh round-2）：PASS，exit 0，Build Summary 1/1（100.0%）。G0/G0e/KC/JC/L0/L1/L1e/L4/L5 全过。
- 上游测试：36/36（100%，CTest 集成测试，`100% tests passed, 0 tests failed out of 36`，Total time 15.72s）。
- test_package：assertion_count=4，CI 实测全部通过（`[pass] julius --help prints usage`；`[pass] julius rejects invalid option`）。
- 本地模拟 Web Review：结论 PASS_WITH_WARNINGS（6 条 finding 全为 B 类，无 A 类）。
- **验证边界（WR-julius-002）**：SDL2 图形渲染/游戏主循环在 OHOS 上的实际运行未验证。CI 仅验证 CLI 参数解析（发生于 SDL 初始化之前）与上游 stub 集成测试（test/stub 桩件，不触碰 SDL 渲染）；无显示环境，游戏主循环未运行。建议在带显示/图形栈的环境人工确认适配完整性（R40）。

## 注意事项

- julius --help 退出码为 1，L2 smoke 会报非阻塞 warn，属预期
- 运行时需 Caesar III 原版数据目录（非构建依赖）
