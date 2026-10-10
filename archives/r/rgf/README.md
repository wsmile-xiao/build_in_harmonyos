# rgf

`rgf` 是正则贪心森林（Regularized Greedy Forest，Rie Johnson / Tong Zhang，
IEEE TPAMI 2014）的 C++ 命令行实现，用于回归与二分类模型的训练、预测与
联合训练预测（`rgf train|predict|train_predict`）。

上游：<https://github.com/RGF-team/rgf>（MIT）。

## 功能概述

- `rgf train_predict algorithm=RGF,train_x_fn=...,train_y_fn=...,test_x_fn=...,model_fn_prefix=...`：端到端训练并预测
- `rgf train ...` / `rgf predict ...`：分步训练与预测
- 输入为 `%RGF/examples/sample%` 格式的 `.x/.y` 数据与 `.inp` 参数文件
- 产物：模型文件（`m-01`…）、预测文件（`.pred`）、模型信息（`.info`）

## 依赖关系

- 编译依赖：无（RGF 核心仅链接 C++ 标准库；CMake 构建）
- 运行依赖：无

## OHOS 适配要点

- 本次为路径 A（基础适配），范围与 Homebrew 公式一致：只构建 `RGF/`
  子目录的原始实现，交付单二进制 `bin/rgf`；FastRGF（OpenMP 多核变体）
  与 python-package / R 包装器不在本次范围内
- 上游 tag 根目录无 CMakeLists，配方用
  `cmake.configure(build_script_folder=<source>/RGF)` 定点
- RGF C++ 核心无测试套件（无 ctest 注册、无 tests/ 目录、无 check 目标；
  `python-package/tests` 只测 Python 包装器，不计入本包口径），按
  `no_tests` 处理；`test_package/test_rgf.sh` 补 12 条消费侧功能断言
  （真实执行已安装二进制，含错误路径非零退出证据），审计见
  [3.12.0/test_package/MANIFEST.yml](3.12.0/test_package/MANIFEST.yml)

## 参考资料

- 上游仓库：<https://github.com/RGF-team/rgf>
- 用户手册：`RGF/rgf-guide.rst`（随包示例见 `share/rgf/examples/sample`）
- 发行包：<https://github.com/RGF-team/rgf/archive/refs/tags/3.12.0.tar.gz>

## 版本

- `3.12.0` — 适配 HarmonyOS PC（aarch64 / armv8）；见 [3.12.0/notes.md](3.12.0/notes.md)

## 产物

| 路径 | 说明 |
|------|------|
| `bin/rgf` | 主程序（arm64 ELF） |
| `share/rgf/examples/sample` | 上游示例数据与参数文件（14 个） |
