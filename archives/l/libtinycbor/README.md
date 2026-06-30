# TinyCBOR

## 简介

TinyCBOR是一个轻量级的CBOR（Concise Binary Object Representation）编码/解码库，用于处理二进制数据序列化格式。CBOR是JSON的二进制等价物，设计用于资源受限环境。

## OHOS 适配

**适配要点**：
- 纯CMake项目，无需特殊平台配置
- 无外部依赖，编译过程简单
- CMake能正确识别OHOS平台
- 生成的产物为静态库和cbordump工具

**已知问题**：
- make check需要Qt6测试框架（OHOS未安装），可设置BUILD_TESTING=OFF跳过
- 无已知平台兼容性问题

## 依赖

**编译依赖**：无外部依赖（纯CMake）

**可选依赖**：
- Qt6：用于测试套件（可跳过）

## 功能验证

```bash
# 库验证
pkg-config --modversion tinycbor
# 应返回: 7.0

# 工具验证
cbordump --help
# 应显示帮助信息
```

## 产物

- **静态库**: libtinycbor.a (56KB)
- **头文件**: tinycbor/cbor.h
- **工具**: cbordump（CBOR数据解析工具）
- **pkg-config**: tinycbor.pc

## 参考

- 官方仓库: https://github.com/intel/tinycbor
- CBOR规范: RFC 8949