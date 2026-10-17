# libsvm 3.37.1.1 适配笔记

## 概述

- 上游版本：3.37
- 适配修复版本：3.37.1.1
- 构建系统：Makefile
- 外部依赖：无
- 源码补丁：无

## 构建适配

上游 Makefile 默认使用 `g++`，配方显式传入 `CXX=clang++`（R33：编译器从 `tools.build:compiler_executables` 获取，不裸用 shell 变量），构建三个命令行工具及共享库。上游没有 install 目标，配方在 `package()` 中安装二进制、头文件与 `libsvm.so.4`。

## 测试

上游没有正式自动化测试入口，但 README 给出了基于 `heart_scale` 的缩放、训练、预测示例。适配测试保留该命令行流程作为一个端到端集成用例，并新增一个共享库消费者 API 用例，覆盖参数校验、训练、预测、模型保存与加载。

- 上游文档示例流程：1/1 通过（svm-train #iter=162 / nSV=132，svm-predict Accuracy=86.6667% (234/270)，svm-scale 270 行输出）
- 新增消费者 API 测试：1/1 通过
- Conan G0-G4、L2、L4、L5：通过
- W3 本地 CI：通过
- 版本依据：`svm.h` 中 `LIBSVM_VERSION=337`

## 版本说明

- `libsvm/3.37` 已存在于上游 main（PR !2036）与制品仓；`libsvm/3.37.1` 已存在于上游 main（PR !6531）。
- 本版本 3.37.1.1 为适配修复版本（R37 版本号策略）：基于已合入 main 的 3.37.1 配方，重新执行完整编译验证（init-build → make all lib → 上游测试 → conan-init → conan-verify → finish published），全部门禁通过。

## 已知限制

命令行工具没有 `--version` 参数；版本由上游 `svm.h` 中的 `LIBSVM_VERSION=337` 确认。
---

**编译结束**: 2026-08-29
**最终状态**: published
