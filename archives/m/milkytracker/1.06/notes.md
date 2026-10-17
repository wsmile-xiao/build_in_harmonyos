# milkytracker 1.06 适配笔记

## 编译环境
- 构建系统: cmake（上游 CMakeLists.txt，`cmake_minimum_required(3.10)`，C++11）
- 编译日期: 2026-08-07
- 编译器: clang/clang++ 15.0.4（OHOS aarch64）
- 平台: OpenHarmony PC（aarch64），profile: ci/conan/profiles/ohos-aarch64
- 状态: published

## 编译步骤

1. 源码获取：`gh-proxy.com` 拉取 GitHub release tarball
   `https://github.com/milkytracker/MilkyTracker/archive/refs/tags/v1.06.tar.gz`
   SHA256 与 FreeBSD distinfo 一致：`6e70590dfed324e6d6ac813e33d9f9dcfaa13b2f57fdec9e178e9dda05538cb0`
2. `ohc-run.py init-build milkytracker 1.06`（环境检查通过）
3. 重写 conan 配方（conan-init 模板误判为 autotools，实际是 CMake 项目）：
   - `CMakeToolchain + CMakeDeps + cmake_layout`，依赖 `sdl2/2.30.10`（cnb 制品仓已就绪）
   - `CMAKE_SYSTEM_NAME=Linux`（E092：CMake 不识别 HarmonyOS 平台）
   - `CMAKE_POLICY_VERSION_MINIMUM=3.5`（CMake 4.x 兼容）
4. `conan create archives/m/milkytracker/1.06 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=... --build=missing`
   → configure + build 通过，产物 bin/milkytracker、bin/milkycli 及示例曲目
5. package() 内对 bin/ 下 ELF 执行 `llvm-objcopy --remove-section .codesign` + `binary-sign-tool sign -selfSign 1` 签名
6. test_package：milkycli 将包内示例 `share/milkytracker/songs/*.xm` 导出 WAV 验证

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `cmake_policy(SET CMP0004 OLD)` 报错 | CMake 4.x 不再允许 CMP0004=OLD | 补丁 0001：加 `if(${CMAKE_VERSION} VERSION_LESS "4.0.0")` 版本守卫 |
| 2 | `System is unknown to cmake`（HarmonyOS） | CMake 无 Platform/HarmonyOS.cmake | E092 方案：`CMAKE_SYSTEM_NAME=Linux` + `CMAKE_SYSTEM_PROCESSOR=aarch64` |
| 3 | `Synths.cpp` 三元表达式 narrowing 硬错误 | clang15 C++11 严格模式（`-Wc++11-narrowing` 视为 error） | 补丁 0002：env_master/fx_delay_amt/row_len 三处补显式强转 |
| 4 | `include/SDL2 is not absolute` | Conan 2 依赖 includedirs 需绝对路径 | generate() 中用 `sdl2.package_folder` 拼接绝对路径 |
| 5 | `find_package(SDL2)` 找不到 target | sdl2 配方未声明 cmake 属性 | 消费方重写 `cmake_file_name=SDL2`、`cmake_target_name=SDL2::SDL2`，并补 `include/SDL2` 目录（上游 `#include <SDL.h>`） |
| 6 | test_package 运行被拒 | OHOS ELF 未签名 | package() 内 binary-sign-tool 签名 |

## 源码修改

- `patches/0001-CMakeLists-cmp0004-cmake4-compat.patch`：CMakeLists.txt CMP0004 加版本守卫
- `patches/0002-Synths-cpp-cxx11-narrowing.patch`：Synths.cpp 三处显式强转（C++11 narrowing）

## 依赖版本

- sdl2/2.30.10（cnb 制品仓，OHOS aarch64 预编译包，静态链接）
- zlib/lhasa/zziplib/ALSA/JACK/RtMidi：均为上游可选依赖（find_package 不带 REQUIRED），
  缺失时对应功能自动禁用（本适配 MIDI/LHA/GZIP/ZIP 解压禁用，核心 tracker 功能不受影响）

## 验证结果

- `conan create` 干净构建通过（G2）
- test_package：milkycli 导出 WAV 成功（退出码 0，产物 > 44 字节）
- 后续以 `conan-verify` 门禁复核（G0-G4 + L2/L4/L5）

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py + conandata.yml | CMake 配方与补丁注册 |
| patches/0001、0002 | 平台适配补丁 |
| test_package/ | 应用型功能验证 + MANIFEST.yml |
| reports/test-report.md | 功能测试报告 |
| packaging/milkytracker-1.06-ohos-aarch64.tar.gz | 预编译包 |

## 注意事项

1. milkytracker 是 SDL2 GUI 应用，无显示环境下图形界面无法运行，功能验证以 milkycli（命令行 WAV 导出）为准
2. 上游未提供自动化测试套件（无 ctest），示例曲目（resources/music/*.xm）作为测试输入
3. conandata sources.url 本地调试用 file:// 镜像，提交前已切换为官方 GitHub URL（CI 自动注入 ghfast.top 镜像）

---

**编译结束**: 2026-08-07
**最终状态**: published
