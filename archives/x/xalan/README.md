# xalan

## 简介
Apache Xalan-C++ 是 XSLT 1.0 标准的 C++ 实现，基于 Xerces-C++ 构建，提供库（`libxalan-c` + `libxalanMsg`）与 `Xalan` 命令行转换工具，可将 XML 文档按 XSLT 样式表转换为目标输出。

## OHOS 适配
- CMake 构建系统（1.12 起唯一构建，Autoconf 已移除），平台检测走通用 UNIX 标志，无 Linux 专属分支
- `transcoder=default`（不引入未发布的 ICU），C++ 标准交由 Conan 工具链
- Xerces 查找双兼容：`cmake/XalanXerces.cmake` 先找 `XercesC`，找不到回退 `xerces-c` 并别名，兼容本仓小写目标与 CCI 大写目标
- 默认构建静态库；上游 21 个 ctest（1 Threads + 20 samples）全量保留并在 `build()` 运行

## 依赖
- `xerces-c/3.2.5`（本仓，transitive headers+libs）

## 功能验证
```bash
# test_package：真实 XSLT 文件转换 + 输出断言
./test_xalan
```

## 参考
- 官网: https://apache.github.io/xalan-c
- 上游仓库: https://github.com/apache/xalan-c
