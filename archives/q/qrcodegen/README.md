# qrcodegen

## 简介
QR Code generator library (C++ implementation) — 二维码生成库。Project Nayuki 出品的单文件 C++11 库（qrcodegen.cpp + qrcodegen.hpp），支持全部 40 个版本与 4 个纠错级别（QR Code Model 2 标准），输出原始模块矩阵。

## OHOS 适配
- 构建系统: cmake（上游 cpp/ 仅提供 Makefile，conanfile source() 内联生成 CMakeLists.txt）
- 语言: C++11（零依赖纯 C++）
- 源码 tarball 为多语言实现合集，C++ 实现位于 cpp/ 子目录，source() 提升到根
- 与 archives/l/libqrcodegen（C 实现）同上游不同语言绑定
- 详见各版本 notes.md 获取适配详情

## 依赖
无外部依赖

## 功能验证
- 上游测试: C++ 实现无自带测试套件（N=0；C 实现才有 qrcodegen-test）
- 消费者测试: test_package/test.cpp 12 项断言（encodeText/encodeBinary/QrSegment 全 API 真实调用 + QR 码结构断言）全部通过

## 参考
- https://github.com/nayuki/QR-Code-generator
- https://www.nayuki.io/page/qr-code-generator-library
