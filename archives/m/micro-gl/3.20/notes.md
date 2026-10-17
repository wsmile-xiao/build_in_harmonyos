# micro-gl 3.20 适配笔记

## 编译环境
- 构建系统: cmake（header-only INTERFACE 目标 microgl::microgl，无编译产物）
- 编译日期: 2026-09-28
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos, OHOS PC 工具链)
- 状态: built

## 版本标识核验（任务要求核验正式标签或 release commit）
- 上游仓库 https://github.com/micro-gl/micro-gl：**无 git tag、无 GitHub release**（ls-remote --tags 为空、API releases=[]）。
- 上游 CMakeLists project VERSION=1.0.0，cmake_minimum_required(VERSION 3.20)。
- 任务指定版本 3.20（delivery 路径 archives/m/micro-gl/3.20），执行端固定源码引用为上游 master HEAD
  `d7ddab9890ae6b391bc646b7086e695c06260abb`（push 2026-06-03），tarball SHA-256
  `a0a43d4ee828a7f500a98edd29f3b7dbeb877dc9016a62f3bb054aef46ccf5d4`。
- conandata.yml 固定该官方归档 URL + SHA-256（R39 官方源）。

## 编译步骤
1. `ohc-run.py init-build micro-gl 3.20 --url=<官方归档>`：下载、解压、建档（archives/m/micro-gl/3.20/）、环境检查通过。
2. `ohc-run.py lang-preflight`：detected=cpp（manifest: CMakeLists project("microgl")，源码统计 99/99 cpp）✅。
3. 上游为纯头文件 C++11 库（include/microgl/ 165 个文件，内含 micro-tess/micro-alloc 子模块树），
   INTERFACE CMake 目标，无编译步骤；conanfile.py 采用 header-library 打包（R26 不适用、无系统同名库）。
4. test_package/test_microgl.cpp：真实调用 canvas API（clear → flat_color drawRect → 像素读回断言 2 项），
   在 OHOS aarch64 上验证软件光栅化与 RGB888_PACKED_32 编解码实际可用（R34 非空壳）。

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 新建 worktree 检出后 archives/l/libXext 两文件显示脏改 | HEAD 树同时含 libXext/libxext 两种大小写路径，本机文件系统大小写不敏感无法两全（环境性基线怪象，非当前库文件） | 不做任何改动/不 add/不 commit；恢复至 HEAD 内容后仍有一侧路径被 git 标记，最终 diff 仅含允许路径（archives/m/micro-gl/3.20/**），报告如实说明 |

## 上游测试申报表（全量枚举台账，R51）

### 枚举清单（按用户测试源/框架/样例/基准/fixture/脚本/构建目标分类）

| 条目 | 类别 | 是否独立上游用例 | 是否实际运行 | 结果/原因 |
|------|------|------------------|--------------|-----------|
| CMakeLists.txt | 构建定义 | ❌ 非测试 | ❌ | 无 enable_testing()，无注册测试目标 |
| examples/*.cpp（30+ 演示程序） | 演示程序（example_clear/example_blend_modes 等） | ❌ 演示，不计独立测试 | ❌ | 依赖 examples/src 资源加载 harness，非注册测试 |
| include/microgl/micro-tess | 内嵌子模块源码 | ❌ 非测试 | ❌ | 库源码 |
| 无 tests/ 目录 / ctest / gtest | — | — | — | 上游不提供可运行的注册测试 |

上游测试结论：**无注册测试可运行**（0/0，清点证据如上）。

## 验证结果
- conan create（ohos-aarch64 profile）+ test_package ctest 运行 test_microgl（2 项像素断言）→ 详见 W3/门禁阶段日志与 SHA-256。

## 注意事项
- header-only 库，无 .so/.a 产物；LICENSE.MD 为自定义 semi-permissive 许可，已随包安装至 licenses/。
- 版本 3.20 为任务指定交付版本；上游无正式 tag/release，源码固定至 master HEAD d7ddab9（已在 conandata.yml/manifest 双处记录）。
---

**编译结束**: 2026-09-28 17:45
**最终状态**: built
