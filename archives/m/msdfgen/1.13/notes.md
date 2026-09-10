# msdfgen 1.13 适配笔记

## 编译环境
- 构建系统: cmake (upstream `cmake_minimum_required(VERSION 3.15)`)
- 编译日期: 2026-09-09
- 编译器: OHOS SDK clang (target aarch64-linux-ohos), OpenHarmony PC (HarmonyOS aarch64)
- 分支: feat/msdfgen-1.13
- 状态: in_progress

## 上游核实（v1.13 tag, commit 1874bcf7）

### 源码与许可
- 官方 repo: https://github.com/Chlumsky/msdfgen （README 内所有自引用链接均为 Chlumsky/msdfgen）
- 官方 tarball: https://github.com/Chlumsky/msdfgen/archive/refs/tags/v1.13.tar.gz
- SHA256: `93cd1ad8918c1a78c5c96e82d4f4c77f0eb86c2e7e8579a0967e54196c4b7167`
  （本地 `sha256sum` 复核一致；解包后顶层目录 `msdfgen-1.13/`）
- License: MIT（LICENSE.txt, "Copyright (c) 2014 - 2025 Viktor Chlumsky"）
- 无 gitlink 子模块：`git ls-tree` 对 tag v1.13 无 `160000` mode 条目；tarball 内无 `.gitmodules`，
  E150 manual-download 流程不适用（已核实留证）

### 构建选项（CMakeLists.txt v1.13 全量 11 个）
| 选项 | 上游默认 | 本配方 | 理由 |
|---|---|---|---|
| MSDFGEN_CORE_ONLY | OFF | OFF | ext 库承载 FreeType 字体导入，是核心能力 |
| MSDFGEN_BUILD_STANDALONE | ON | ON | 交付 CLI |
| MSDFGEN_USE_VCPKG | ON | OFF | 用 Conan CMakeDeps 而非 vcpkg 工具链 |
| MSDFGEN_USE_OPENMP | OFF | OFF | 桌面 OpenMP 运行时，库交付不需要 |
| MSDFGEN_USE_CPP11 | ON | ON | 公共头 msdfgen-config.h 的 MSDFGEN_USE_CPP11 |
| MSDFGEN_USE_SKIA | ON | OFF | Skia 几何预处理（import-svg 增强），桌面重依赖；核心 MSDF 不受影响 |
| MSDFGEN_DISABLE_SVG | OFF | OFF | tinyxml2 文本轮廓输入是 CLI 核心输入路径 |
| MSDFGEN_DISABLE_PNG | OFF | OFF | PNG 输出是 CLI 核心功能 |
| MSDFGEN_INSTALL | OFF | ON | 安装库+头+CLI+CMake config |
| MSDFGEN_DYNAMIC_RUNTIME | OFF | OFF | MSVC-only 选项 |
| BUILD_SHARED_LIBS | OFF | ON(shared=True) | 交付动态库 |

### 依赖与 target 名
上游 CMake（v1.13 CMakeLists.txt L139-169）：
- `find_package(Freetype REQUIRED)` → 链接 `Freetype::Freetype`
- `find_package(PNG REQUIRED)` → 链接 `PNG::PNG`
- `find_package(tinyxml2 REQUIRED)` → 链接 `tinyxml2::tinyxml2`

本仓库 Conan 包导出的 CMakeDeps target：
- freetype/2.14.3 → `freetype::freetype`（cmake_file_name "freetype"）
- libpng/1.6.58 → `libpng::libpng`（cmake_file_name "libpng"）
- tinyxml2/11.0.0 → `tinyxml2::tinyxml2`（原生匹配）

桥接方案（generate() 内 `CMakeDeps.set_property`，不改上游源码）：
```python
deps.set_property("freetype", "cmake_target_name", "Freetype::Freetype")
deps.set_property("freetype", "cmake_file_name", "Freetype")
deps.set_property("libpng", "cmake_target_name", "PNG::PNG")
deps.set_property("libpng", "cmake_file_name", "PNG")
```

### 安装目标（MSDFGEN_INSTALL=ON 时）
- 库: `lib/libmsdfgen-core.so`, `lib/libmsdfgen-ext.so`
- CLI: `bin/msdfgen`
- 头文件: `include/msdfgen.h`, `include/msdfgen-ext.h`, `include/msdfgen/{core,ext}/*.h`,
  `include/msdfgen/msdfgen-config.h`（core 依赖此配置头）
- CMake config: `lib/cmake/msdfgen/{msdfgenConfig.cmake, msdfgenTargets.cmake, ...}`，
  导出命名空间 `msdfgen::`（msdfgen::msdfgen-core / msdfgen::msdfgen-ext / msdfgen::msdfgen / msdfgen-standalone::msdfgen）

## 上游测试：0 项（三方面证据）
1. **目录**: tarball 内无 `tests/`、`test/` 目录；`tar tzf` 全量列表核实
2. **构建目标**: CMakeLists.txt 无 `enable_testing()`，无 `add_test()`，无 BUILD_TESTING/TESTS 选项
   （`grep -c "add_test\|enable_testing"` = 0）
3. **测试框架**: 无 CTest/GTest/Catch 等任何测试框架引用；vcpkg.json 无 test vcpkg feature；
   README 无测试章节；`msdfgen` CLI 的 `-test` 类参数不存在

按 TEST_QUALITY_SPEC 无上游测试规范处理：以 test_package 消费者测试（1/1）与鸿蒙专项测试（1/1）
替代，全部从最终 Conan 包构建/运行。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | tinyxml2/10.0.0 无法安装 | 该配方 OHOS+shared 时硬编码校验 `/data/service/hnp/bin/` 签名工具（本机不可写、工具实际在 `/storage/Users/currentUser/usr/local/bin/`） | 改用 tinyxml2/11.0.0（无该校验，且 ohpcd 有 OHOS shared 预构建包，target 名一致） |
| 2 | 上游期望 Freetype::Freetype / PNG::PNG | 上游为 vcpkg 风格 target 名，本仓库 Conan 包导出小写包名 target | CMakeDeps.set_property 桥接（cmake_target_name + cmake_file_name），无需 patch |
| 3 | MSDFGEN_USE_VCPKG 默认 ON 会强求 vcpkg toolchain | 上游默认面向 vcpkg 用户 | 显式 -DMSDFGEN_USE_VCPKG=OFF |
| 4 | Skia 不可用 | MSDFGEN_USE_SKIA=ON 时需 find_package(skia)（本仓库无 Skina 包） | 关闭（仅影响 import-svg 几何预处理增强；core MSDF 生成与 FreeType/PNG/tinyxml2 路径不受影响，resolve-shape-geometry.cpp 无 Skia 时优雅降级） |

## 验证方案（不引入来源不明字体/图片）
- CLI 输入用 `-defineshape` 内联文本轮廓定义（shape-description 语法，msdfgen 自己的格式），
  不依赖任何外部字体/图片文件
- 消费者测试直接调库 API：`msdfgen::Shape` + `generateMSDF`/`generateSDF`（core 路径）+
  `savePng`（ext 路径），对程序化构造的矩形/三角形轮廓断言：
  尺寸、通道数、像素值域、内/外符号关系、角落三通道不对称性、异常输入行为

## 语义核实（实测，OpenHarmony PC / clang-15 / libc++）
- 浮点 MSDF/SDF 输出是【带符号距离，像素单位】：内部为负（实测矩形中心 -17.5）、
  外部为正（四角 +7.3）；不是 [0,1] 归一化域。CLI `-format text` 的 hex 输出则经过
  pixelFloatToByte（clamp 到 [0,1] × 255），FF=内部、00=外部。
- 绕向：CCW 轮廓内部为负距离；CW 被 normalize() 反转后内外符号对调。
- Projection 映射：px → shape 为 unproject(px) = px/scale − translate（注意顺序，
  与直觉的 (px−translate)/scale 不同）。
- 空形状（无轮廓）：距离查找器最小值保持无穷 → 输出全 NaN/Inf（上游固有语义，
  确定性可检测，非随机垃圾）。

## 浮点跨配置稳定性实验（2026-09-10，msdfgen 1.13 core 静态编译 + 同机运行）
同一份 core 源码分别以 `-O2`、`-O2 -ffp-contract=off`、`-O3`、`-Ofast -ffast-math`、
`-O2 -mcpu=native` 构建（其中 Ofast 产物 fmadd 指令数 367→439、体积 248320→260608，
代码确实不同），对矩形与 4 段三次贝塞尔圆各生成 64×64×3 MSDF：
**五种配置输出逐位（bit-exact）一致**（md5 相同，12288 个 float 的十六进制位模式全等）。
本机无 x86_64 运行环境（无 qemu-x86_64、无 x86 sysroot），跨架构逐字节对比不可执行；
基于以上实测，未取得"跨配置/跨架构浮点输出必然分歧"的真实证据，故不创建该方向的知识草稿。
消费者/鸿蒙测试全部采用结构性 + 容差型断言（符号关系、统计值域、尺寸、token 域），
而非逐字节 oracle —— 与 TEST_QUALITY_SPEC 的跨架构断言要求一致。

补充实验（同日，-O0 + 64 边形 + 128×128）：同一静态编译方案下以 -O0/-O2/-O3
构建（O0 比 O2 大 512000 字节，代码确实不同），对 64 段直边正多边形轮廓生成
128×128×3 MSDF（49152 个 float）：三种优化级别输出仍逐位一致
（md5 3789b51c0fea40b0b33e3852cb7719ec）→ 路径 A（浮点/图像算法跨架构验证）
在无 x86 对照环境的前提下依旧没有真实分歧证据，维持不创建知识草稿的结论。

## C++98 失败归因实验（2026-09-10，安装头 + clang++ 15 -std=c++98 -pedantic-errors）
- 步骤1 原始安装头：`#include <msdfgen/msdfgen.h>` 编译失败，15 处 error
  （9 rvalue references、3 explicit conversion functions、3 long long，均 C++11 extension）。
- 步骤2 临时副本删除 `#define MSDFGEN_USE_CPP11` 后重编译：仍失败，剩 3 处
  error——core/edge-coloring.h L15/L21/L27 的 `long long` 不受该宏守卫。
- 结论：宏只解释 15 处中的 12 处，移除后 C++98 依旧无法编译 →
  "生成宏是消费者 C++11 锁定的根因"命题不成立（宏非单独根因），
  按规则删除知识草稿、放弃该知识扩展方向。
  消费者事实不变：安装头仍要求最低 C++11（宏内代码与未守卫 long long 共同决定），
  test_package 显式 `target_compile_features(cxx_std_11)`。

## 交付物
- libmsdfgen-core.so.1(.13)、libmsdfgen-ext.so.1(.13)（版本化 SONAME，OHOS 签名, ELF64 AArch64）
- bin/msdfgen CLI（OHOS 签名，支持 -version/--help，exit 0）
- 头文件 + CMake config（msdfgen:: 命名空间，INTERFACE_COMPILE_DEFINITIONS 含构建配置宏）
