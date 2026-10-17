# libocas

OCAS solver library for training linear SVM classifiers from large-scale data.

- 上游：https://cmp.felk.cvut.cz/~xfrancv/ocas/html/
- 许可证：GPL-3.0-only
- 构建系统：Makefile

## OHOS 适配要点

- 删除 x86 专用的 `-msse` 编译选项，适配 HarmonyOS aarch64。
- `CC` 改为可覆盖形式，从 Conan 配置传入 clang，不依赖裸环境变量。
- 无 MATLAB 环境，仅构建 C 库与 `svmocas`、`msvmocas`、`linclassif` 三个工具。
- 上游无 C 自动化测试；test_package 覆盖 C API 与命令行端到端流程。

## 版本

- 0.97：初次适配（上游 0.97，2013-05-14）。
