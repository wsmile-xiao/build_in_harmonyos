# Zint

Zint 是一个开源的条形码编码库，支持超过 50 种条形码符号，包括 QR Code、Data Matrix、PDF417 等常见格式。

## 简介

Zint 提供了一套完整的条形码生成解决方案，包含：
- **核心库** (`libzint`): C 语言实现的编码引擎
- **命令行工具** (`zint`): CLI 工具，用于快速生成条形码图像
- **API 接口**: 支持多种编程语言调用

## 支持的条形码符号

主要支持的符号包括：
- **二维码**: QR Code, Data Matrix, Aztec Code, PDF417
- **一维码**: Code 128, EAN/UPC, Code 39, Code 93
- **特殊码**: GS1 DataBar, MaxiCode, DotCode
- **工业码**: ITF-14, Telepen, Codabar

完整列表超过 50 种符号，覆盖绝大多数应用场景。

## OHOS 适配

### 关键要点

1. **RPATH 问题**: CLI 工具 `zint` 在运行时需要能找到 `libzint.so`，需要设置正确的 RPATH
   - 打包时使用 `patchelf --set-rpath` 修复
   - 或用户手动设置 `LD_LIBRARY_PATH`

2. **可选依赖**:
   - PNG 支持需要 `libpng`（默认禁用）
   - Qt GUI 支持需要 Qt 环境（默认禁用）

3. **CMake 配置**:
   ```bash
   cmake -DCMAKE_INSTALL_PREFIX=~/usr/local \
         -DCMAKE_BUILD_TYPE=Release \
         -DZINT_USE_PNG=OFF \
         -DZINT_USE_QT=OFF \
         ..
   ```

### 已知问题

- CMake 在 HarmonyOS 上链接时，NEEDED 字段使用构建树相对路径
- `BUILD_WITH_INSTALL_RPATH TRUE` 不能改变 NEEDED 字段中的路径
- RPATH 设置仅针对 Apple 平台，需要扩展到所有非 Windows 平台

## 依赖

### 编译依赖
- CMake 3.16+
- Clang/C++ 编译器

### 可选依赖
- libpng: PNG 图像输出支持（默认禁用）
- Qt: GUI 界面支持（默认禁用）

## 功能验证

```bash
# 基本验证
zint --version

# 生成 QR Code
zint -b 58 -d "Hello Zint" -o qrcode.png

# 查看 libzint 状态
ldd $(which zint) | grep libzint
```

## 参考

- 官网: https://zint.org.uk
- 源码: https://github.com/zint/zint
- 文档: https://zint.org.uk/manual