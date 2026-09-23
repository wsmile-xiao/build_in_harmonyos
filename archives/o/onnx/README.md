# ONNX

Open Neural Network Exchange（开放神经网络交换格式），用于表示机器学习模型的开放标准格式。
本归档提供 ONNX 1.22.0 在 HarmonyOS PC（aarch64）上的 C++ 库适配，含 onnx.proto 工具链产物。

## 版本列表

| 版本 | 状态 | 编译日期 |
|------|------|----------|
| [1.22.0](./1.22.0/) | built | 2026-09-12 |

## 依赖

- protobuf/33.6.1（含 abseil-cpp/20260107.1、zlib/1.3.1 传递依赖）
- 交叉编译需 host protoc（由 protobuf 包提供）
