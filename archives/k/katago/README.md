# KataGo

## 简介

KataGo 是一个强大的开源围棋引擎，基于 AlphaZero 技术，支持多种后端（CUDA、EIGEN 等）。在 HarmonyOS 上使用 EIGEN 纯 CPU 后端。

## OHOS 适配

- **架构检测**：使用 `uname -m` 检测架构，避免在 ARM 上使用 SSE 指令
- **字节序宏**：需定义 `BYTE_ORDER`、`LITTLE_ENDIAN`、`BIG_ENDIAN` 宏以兼容 HarmonyOS
- **libatomic**：aarch64 平台不需要链接 libatomic，需注释相关代码
- **后端选择**：使用 EIGEN backend（纯 CPU），无需 CUDA/TensorRT

## 依赖

- **编译依赖**：
  - eigen/3.4.0（线性代数库）
  - zlib/1.3.1（压缩库）
  
- **运行依赖**：
  - 无（静态链接 zlib）

## 功能验证

```bash
katago version
katago runtests
```

## 参考

- GitHub: https://github.com/lightvector/KataGo
- 文档: https://github.com/lightvector/KataGo/blob/master/README.md