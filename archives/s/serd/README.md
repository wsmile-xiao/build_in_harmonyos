# Serd

## 简介
Serd 是一个轻量级的 RDF 序列化库，用于读写 RDF 数据格式。

## 功能概述
- 支持 Turtle, N-Triples, JSON-LD 格式
- 提供 serdi 命令行工具进行格式转换
- 高性能流式处理

## OHOS 适配
- 构建系统: meson 1.11.1
- ELF 签名必需，否则 serdi 无法执行
- 0.32.9-git 测试全部通过（41/41）
- 0.32.10 新增 Conan recipe，上游 Meson 测试 65/65 通过，test_package 验证 C API 与 serdi CLI 2/2 通过

## 依赖
- zix >= 0.6.0 (0.32.9-git 适配记录)
- 0.32.10 源码构建未声明外部三方库依赖

## 功能验证
```bash
export LD_LIBRARY_PATH=$HOME/usr/local/lib
serdi --version
```

## 参考
- 官网: https://drobilla.net/software/serd
- 源码: https://gitlab.com/drobilla/serd
