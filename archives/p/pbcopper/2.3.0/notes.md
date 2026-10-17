# pbcopper 2.3.0 适配笔记

## 编译环境

- 构建系统: meson (>= 0.57, C++20 / C17)
- 编译日期: 2026-09-26
- 编译器: clang/clang++ (HarmonyOS PC, libc++)
- 状态: built (待真机 rule4 门禁验证后更新为 published)
- 申请人: Bingggooo / 队伍: 来都来了

## 上游信息

- 上游仓库: https://github.com/PacificBiosciences/pbcopper (已归档, 只读)
- 上游版本: v2.3.0 (2023-12, meson.build project version 2.3.0)
- 源码包: pbcopper-2.3.0.tar.gz (2953968 字节, 818 个文件)
- 许可证: BSD-3-Clause-Clear
- 依赖: threads (系统), boost (system include_type), gtest (仅测试)
- 测试框架: gtest (79 个 tests/src/*.cpp; 静态宏扫描约 700, 真机 gtest XML
  tests="697"), meson test 注册 2 条
  (formatting check + gtest unittests, 其中 gtest 二进制写
  pbcopper-gtest-unittests.xml)

## 编译步骤

1. `get()` 解压官方 GitHub tag 归档 (strip_root=True)。
2. `generate()` 用 MesonToolchain: cpp_std=c++20, wrap_mode=nodownload,
   default_library 按 shared 选项, tests 按选项透传, build-docs=false;
   boost_root 属性指向 Conan boost 包目录并追加 -I<header> (bali-phy/4.1 同款)。
3. `meson configure` + `meson compile -j1`。
4. tests=true 时运行 `meson test --no-rebuild --print-errorlogs`,
   解析 gtest XML 得 697 用例计数并输出 HMBS_UPSTREAM_TEST_RESULT 标记。
5. `meson install` + 拷贝 LICENSE.txt; 将构建期 overlay 的 boost/icl 与
   boost/numeric/ublas 等 header-only 头一并打包到 include/boost (公头
   Interval.h 需要, 否则 test_package 消费者缺头); 共享别名實體化 (OHOS loader
   对版本化 symlink 支持不可靠, canfigger/libavtp 先例)。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | meson 可能试图下载 gtest subproject | tests/meson.build 用 fallback gtest, 无系统 gtest 时走 wrap 下载 | wrap_mode=nodownload + test_requires gtest/1.17.0.1 提供系统 gtest, 与 cppdap 同策略 |
| 2 | meson 找不到 Conan 提供的 boost | meson boost 模块按 root 目录扫描头文件+库, 不读 Conan flags | boost_root 属性 + cpp_args -I, bali-phy/4.1 已验证模式 |
| 3 | Windows 检出上游 main 失败 | archives/g/gama/2.29 含带 CR 的非法文件名, Windows 无法落地 | 本机用 git archive 按需提取 + sparse 规避; 真机 (Linux) 全量检出不受影响, 见任务记录 |
| 4 | meson configure 报 GTest found NO | meson main:true 查 gtest_main 且工厂无 cmake 方法, PkgConfigDeps 文件名映射不可靠 | host 依赖 + 手写 gtest.pc/gtest_main.pc 到 generators 目录并透传 PKG_CONFIG_PATH |
| 5 | AffineAlignment.cpp 缺 boost/numeric/ublas/matrix.hpp, 接着 Clipping.cpp 缺 boost/icl/discrete_interval.hpp | boost/1.91.0.1.1 仅安装过滤子集, 缺整片 header-only 模块; 逐个 vendor 是打地鼠 | source() 拉取官方 boost 1.91.0-1 cmake 包 (与 boost 配方同 URL/sha256) 并合并全部 libs/*/include/boost 为 overlay, -I 置顶; 删除 patches/boost-extra 77 文件, 不改 boost 配方 |

## 源码修改

无上游代码补丁 (conandata patches 为空, 不改算法源码)。
Boost 头文件缺口在构建时解决: source() 从官方 boost 1.91.0-1 cmake 包
(与 boost/1.91.0.1.1 同源, BSL-1.0) 合并全部 header-only 头为 overlay,
供 Interval.h 的 icl 与 AffineAlignment.cpp 的 ublas 使用;
不改任何 boost 配方与上游算法代码, 仓库内不再保留 patches/boost-extra。

## 依赖版本

- boost/1.91.0.1.1 (transitive_headers + transitive_libs)
- gtest/1.17.0.1 (tests=true 时的 host 依赖, 仅构建上游测试; 手写 gtest.pc/gtest_main.pc 供 meson 解析)
- meson/1.11.0 (tool_requires, canfigger 同款版本)

## 验证结果

- 本地 (Windows): 仅完成配方静态编写与源码包校验, 未运行 conan (按规范
  不在本机运行 conan, 真机验证由 HMBS 后台执行)。
- 待真机预检: `conan create` (meson compile + meson test 700 gtest +
  test_package 8 checks), 日志将用于填充 PR 正文通过率。

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Meson 主配方 (含上游测试 + HMBS 标记) |
| conandata.yml | 官方 URL + sha256 |
| manifest.yaml | 版本清单 |
| test_package/ | 消费者测试 (Interval/Cigar/StringUtils/LibraryInfo, 8 checks) |

## 注意事项

- pbcopper 为纯库, 无命令行产物, 不需要 commands.json (R38)。
- 非系统同名库, 保留共享库 (默认 shared=True)。
- 平台判断用 `in ("Linux", "OHOS")` (R32)。
- 上游测试计数口径为 gtest_macros (700), 详见 test_package/MANIFEST.yml 审计块。
