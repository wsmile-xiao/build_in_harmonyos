# pxr-kind 26.08 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-23
- 编译器: clang/clang++ (15)
- 状态: built

## 软件说明

pxr-kind 是 Pixar OpenUSD (Universal Scene Description) 的 kind 注册表库
（源码位于 monorepo 的 `pxr/usd/kind/`）。kind 是 USD 中对 prim 的分类体系
（model/component/group/assembly/subcomponent），KindRegistry 提供内置
分类层级查询（HasKind/GetBaseKind/IsA/GetAllKinds/IsModel 等），并支持
通过 plug 插件元数据（plugInfo.json 的 "Kinds" 字段）扩展自定义分类。

依赖链（源自 pxr_library(kind LIBRARIES tf plug) 与 plug 的
LIBRARIES arch tf js trace work TBB::tbb）：
kind → plug → arch/tf/js/trace/work + TBB；work 为 header-only。

与已发布的 pxr-vt/26.08 同源（同一 OpenUSD v26.08 tarball，sha256 一致），
配方结构复用其已验证模式：全量源码 + cmake.build(target="kind") +
libusd_*.a 打包。本包 conan 级依赖仅 tbb/2023.0.0（ohpcd 已发布）。

## 上游测试清点（R51）

- 上游测试：`pxr/usd/kind/testenv/testKindRegistry.py`（1 个，Python，经
  ctest 注册为 testKindRegistry，实际以 pytest/unittest 方式运行）。
- 上游用例内容：注册 python 插件后校验内置 kind（group/model）与
  插件贡献 kind（test_root_kind/test_model_kind，来自
  TestKindModule_plugInfo.json）。
- 无法原样运行的技术原因：上游测试为 Python 脚本，依赖
  PXR_ENABLE_PYTHON_SUPPORT=ON 编译的 Python 绑定模块（Kind/Plug/Tf
  python module）与 python 型插件加载；本适配为无 Python 的静态 C++
  交付（对齐 pxr-vt 已合入模式），目标环境无 USD Python 运行时。
- 等价覆盖：test_package/test_pxr_kind.cpp 以 C++ 逐条复刻上游断言
  （内置 5 kind 校验、baseKind 层级、IsA 传递性、GetAllKinds、以及经
  plugInfo.json 注册的 test_model_kind/test_root_kind——上游用 python
  型插件，此处改用 resource 型插件，Type=python 在无 Python 构建下会被
  info.cpp 拒绝）。

## 编译步骤

1. 下载 OpenUSD v26.08 tarball（与 pxr-vt 同源，sha256 一致）
2. 应用 OHOS arch 修复补丁（与 pxr-vt 相同，kind 构建链同样编译 arch/tf）
3. Conan 2 构建目标 kind（自动拉取依赖: plug, js, tf, trace, arch, work）
4. 禁用 Python 支持、成像、工具等非必要模块

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | arch/tf 在 OHOS 下的编译错误（复用 pxr-vt 结论） | _SC_LEVEL1_DCACHE_LINESIZE/strerror_r/__environ/DEFFILEMODE 缺失或语义不同 | 复用 0001-arch-fixes-for-ohos.patch |
| 2 | TBB 解析（无 CMakeDeps） | OpenUSD Packages.cmake 先试 TBB CONFIG 失败后回退自带 FindTBB.cmake 模块 | conan CMakeToolchain 为直接依赖注入 CMAKE_LIBRARY_PATH/CMAKE_INCLUDE_PATH，模块内 find_path/find_library 命中 conan tbb 包 |
| 3 | kind 库位置与 pxr-vt 不同 | kind 属于 usd 层而非 base 层 | libusd_kind.a 在 build/pxr/usd/kind/，其余依赖仍在 build/pxr/base/<name>/ |

## 依赖版本

- tbb/2023.0.0 (来自 ohpcd 制品仓，已验证发布)

## 验证结果

见 reports/test-report.md 与 reports/audit-result.json

## 最终状态

status: closed
COMPLETED
---

**编译结束**: 2026-09-23 14:53
**最终状态**: built
