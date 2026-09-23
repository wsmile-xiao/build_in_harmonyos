# msdfgen

## 简介
msdfgen 是 Viktor Chlumsky 开发的多通道带符号距离场（Multi-channel Signed Distance Field）生成器，
用于从矢量轮廓和字体字形生成 MSDF/MTSDF/SDF 纹理，供实时图形中以纹理形式高效重建原形状。
项目分为 core（无外部依赖，纯 C++ 核心算法）与 ext（FreeType 字体导入、libpng 图像读写、
tinyxml2 文本轮廓描述解析）两个库，外加 `msdfgen` CLI 工具。

## 上游
- 官网/源码: https://github.com/Chlumsky/msdfgen
- License: MIT
- v1.13 tag: commit 1874bcf7, tarball SHA256 `93cd1ad8918c1a78c5c96e82d4f4c77f0eb86c2e7e8579a0967e54196c4b7167`
- v1.13 release tarball 完整、无 gitlink 子模块（已逐一核实）

## OHOS 适配要点
- CMake 构建（`cmake_minimum_required 3.15`），产物：libmsdfgen-core、libmsdfgen-ext、CLI `msdfgen`
- 上游 CMake 期望 vcpkg 风格 target 名 `Freetype::Freetype` / `PNG::PNG`；本仓库 Conan 包导出
  `freetype::freetype` / `libpng::libpng`。通过 `CMakeDeps.set_property` 桥接（cmake_target_name +
  cmake_file_name），不改上游源码
- `tinyxml2::tinyxml2` 与上游原生匹配，无需桥接；选 tinyxml2/11.0.0（10.0.0 配方有硬编码
  /data/service/hnp/bin 签名工具路径校验，会阻断本地安装；11.0.0 无此检查且 ohpcd 有 OHOS 预构建包）
- 关闭的选项（仅裁剪与库交付无关的桌面依赖，不触碰核心 MSDF 功能）：
  - `MSDFGEN_USE_OPENMP=OFF`（桌面 OpenMP 运行时）
  - `MSDFGEN_USE_SKIA=OFF`（Skia 桌面几何预处理，仅影响 import-svg 增强）
  - `MSDFGEN_USE_VCPKG=OFF`（不用 vcpkg 工具链，用 Conan CMakeDeps）
- 保持开启：`MSDFGEN_CORE_ONLY=OFF`（ext 是 FreeType 字体导入所在）、`MSDFGEN_DISABLE_PNG=OFF`
  （PNG 输出是 CLI 核心功能）、`MSDFGEN_DISABLE_SVG=OFF`（文本轮廓描述输入是 CLI 核心输入路径）、
  `MSDFGEN_BUILD_STANDALONE=ON`（交付 CLI）、`MSDFGEN_INSTALL=ON`
- 共享库签名：按 libpng 1.6.58.2 的 `_resolve_tool` 模式从 Conan clang 编译器目录解析
  llvm-objcopy / binary-sign-tool，无硬编码路径
- 上游 v1.13 无任何测试目标（无 enable_testing/ctest、无 tests/ 目录、无测试框架），按
  TEST_QUALITY_SPEC 以 test_package 消费者测试 + 鸿蒙专项测试替代

## 依赖
- freetype/2.14.3（字形导入）
- libpng/1.6.58.2（PNG 读写）
- tinyxml2/11.0.0（shape-description 文本输入解析）

## SONAME（OHOS 交付要求）
上游 `add_library` 未设 SOVERSION，产物无 SONAME。两步补齐：
1. `patches/0001-ohos-soname.patch`：给 msdfgen-core / msdfgen-ext 设
   `VERSION 1.13 SOVERSION 1` → `libmsdfgen-core.so.1(.13)` + 开发 symlink
2. conanfile `generate()`：`CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG="-Wl,-soname,"`
   （CMake 无 HarmonyOS 平台模块，不定义该变量时 VERSION/SOVERSION 属性被静默忽略；
   尾逗号是 CMake 直接拼接值的要求，如 `-Wl,-soname,libmsdfgen-core.so.1`）
安装布局与 libpng16.so.16 / libfreetype.so 惯例一致；ext 以 SONAME 依赖 core，
CLI 以 SONAME 依赖两者（test_ohos.sh H2 断言）。

## 消费者兼容性（已实测）
已安装的 `msdfgen/msdfgen-config.h` 由上游 configure_file 生成，内嵌
`#define MSDFGEN_USE_CPP11` 等构建配置宏（无条件、无守卫）→
**消费者最低语言标准被锁定为 C++11**（-std=c++98 -pedantic-errors 下安装头报
15 处 error：9 rvalue reference、3 explicit conversion、3 long long）。
test_package 显式声明 `target_compile_features(cxx_std_11)`。
归因实验（notes.md）：临时副本移除 MSDFGEN_USE_CPP11 后仍剩 3 处
edge-coloring.h 未受宏守卫的 long long 错误 → 宏非唯一根因，未创建知识草稿。

## CLI 输入形式（测试使用）
- `-defineshape "<文本轮廓定义>"`：从命令行直接定义矢量轮廓（无需字体/图片文件）
- `-shapeout <file>` / `-format text`：文本格式输出，可直接断言像素值
- 字体输入（`msdfgen -font <font> <char>`）需要真实字体文件，测试避免使用来源不明字体，
  改用 `-defineshape` 内联轮廓

## 参考
- 论文: Chlumsky, "Shape Decomposition for Multi-channel Distance Fields"
- 相关项目: msdf-atlas-gen（字形图集生成）
