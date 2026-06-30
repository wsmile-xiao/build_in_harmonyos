# libpostal

地址解析库，用于解析和规范化地址字符串。

## 版本

- **当前版本**: 1.1

## 描述

libpostal 是一个用于解析和规范化地址字符串的 C 库，支持多种语言的地址格式。它使用机器学习技术来识别地址组件（如街道、城市、国家等）。

## 编译注意事项

### 平台兼容性

- **ARM 架构**: 必须使用 `--disable-sse2` 禁用 SSE 优化，因为 ARM 不支持 x86 SSE 指令集
- **HMDFS 环境**: linenoise.c 硬编码 `/tmp/lndebug.txt`，需注意 /tmp 只读限制

## 依赖

无外部依赖（使用内置的 utf8proc 和其他组件）

## 安装文件

- **bin**: libpostal
- **lib**: libpostal.so, libscanner.so

## 使用示例

```bash
libpostal "123 Main Street, New York, NY"
```

## 参考资料

- [GitHub](https://github.com/openvenues/libpostal)