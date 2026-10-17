# Release CMake 强制可选 Python 绑定子模块时分离核心 header 组件

> 状态：本地路径 B 草稿，需人工审核后才可提升为正式知识条目。

## 现象

`libasd` README 将 C++ 组件描述为仅依赖标准库的 header-only 库，同时提供依赖 pybind11 的 Python binding。v1.5.6 release tarball 保留 `.gitmodules`，但没有 `extlib/pybind11` 内容；顶层 CMake 仍无条件添加 `extlib` 和 `python`。

## 诊断证据

- `extlib/CMakeLists.txt` 在 pybind11 目录缺失时尝试 `git submodule init/update`，随后无条件 `add_subdirectory(pybind11)`。
- 干净 release 源码没有可用的子模块 checkout，CMake configure 在 Python binding 路径失败，测试目录尚未执行。
- 直接以 OHOS clang++ C++11 编译包含 `<libasd/libasd.hpp>` 的最小 consumer 通过，证明核心 header 组件有独立适配边界。

## 推荐方案

1. 先按 release tarball 的实际内容验证子模块是否存在，不因 `.gitmodules` 存在就假设源码已打包。
2. 当核心 header 与可选绑定有清晰边界时，Conan 包只交付可验证的核心组件；用真实 consumer 覆盖 public API。
3. 在 manifest/notes/report 中单独列出绑定组件和上游测试未执行的原因，不能把核心 consumer 通过写成完整项目通过。

## 禁止策略

- 禁止从未锁定的 SSH/HEAD 子模块下载代码来伪造 release 完整性。
- 禁止把 Python/pybind11 依赖源码混入核心 C++ 归档 PR。
- 禁止把“configure 失败前未进入测试”记为上游测试通过，也禁止用空壳 consumer 替代真实 API 调用。

## 适用边界

适用于同时提供 header-only/C++ 核心和 Python/其他绑定的项目，且 release 包缺少绑定子模块、顶层构建系统又强制进入绑定目录的情况；若绑定是任务要求的主体，则不能用本条将任务降级为核心组件成功。

## 实测对象

- 软件：libasd 1.5.6
- 缺失子模块：`extlib/pybind11`
- 平台：OpenHarmony PC arm64 / clang++ 15 / Conan 2.29.1
