# libqrcodegen

## 简介
QR code generator library - C implementation by Project Nayuki. A compact, correct QR Code generator library supporting all 40 versions and 4 error correction levels.

## OHOS 适配
- 构建系统: cmake (自定义 CMakeLists.txt，上游仅提供 Makefile)
- 语言: C99
- 无外部依赖
- 源码 tarball 包含多语言实现，conanfile source() 方法处理 c/ 子目录提升
- 详见各版本 notes.md 获取适配详情

## 依赖
无外部依赖

## 功能验证
- 上游测试: 521 个测试用例全部通过 (qrcodegen-test)
- 消费者测试: 编码文本和二进制数据为 QR 码，验证尺寸和模块多样性

## 参考
- https://github.com/nayuki/QR-Code-generator
- https://www.nayuki.io/page/qr-code-generator-library
