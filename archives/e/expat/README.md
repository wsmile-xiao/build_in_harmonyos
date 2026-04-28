# expat

expat 是一个高性能的 C 语言 XML 解析库，使用流式 SAX（Simple API for XML）解析器设计。

## 功能概述
- 流式 SAX 解析器，内存占用低
- 支持 XML 1.0/1.1 规范
- 命名空间支持
- DTD 验证
- 随附 xmlwf 命令行工具（XML 文件校验）
- 同时支持 autotools 和 CMake 构建

## OHOS 适配
- **推荐使用 CMake 构建**：autotools configure 在 HarmonyOS 上因 HMDFS 文件系统限制可能卡住或权限不足
- 使用 autotools 构建时需要更新 config.guess/config.sub
- CMake 构建无需补丁
- xmlwf 命令行工具可正常使用

## 依赖关系
- **编译依赖**: 无（CMake 可选依赖：docbook2x）
- **运行依赖**: 无

## 参考资料
- 官网: https://libexpat.github.io/
- 源码: https://github.com/libexpat/libexpat
