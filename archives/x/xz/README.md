# XZ Utils

## 简介
通用数据压缩软件，提供高压缩比的 LZMA2/XZ 格式支持，包含 xz、lzma、xzcat 等工具。

## OHOS 适配
- 需修补 config.guess/config.sub 和 po 文件
- autotools 构建
- 12 个补丁文件（含自动生成的构建文件）

## 依赖
- 标准 C 库

## 功能验证
```bash
xz --version
echo "test" | xz | xz -d
```

## 参考
- 官网: https://tukaani.org/xz/
