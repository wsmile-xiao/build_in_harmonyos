# xerces

## 简介
Apache Xerces-C++ 是一个高性能、可校验的 XML 解析器库，提供 DOM、SAX、SAX2 解析接口，支持 XML 1.0/1.1、命名空间、Schema (XSD) 校验等。本目录对应上游 Apache Xerces-C++ 项目（源码包名为 `xerces-c-*`，Conan 包名为 `xerces`）。

## OHOS 适配
- CMake 构建系统，平台检测走 UNIX/WIN32/APPLE 通用标志（无 `STREQUAL "Linux"` 专属分支），CMAKE_SYSTEM_NAME=HarmonyOS 下行为一致，无需补丁
- 三个特性后端显式钉到 libc-only 实现，规避外部依赖：
  - `network-accessor=socket`（原生 BSD socket，规避 libcurl）
  - `transcoder=gnuiconv`（libc iconv，规避 ICU）
  - `message-loader=inmemory`（内置消息目录，规避 ICU/NLS）
- musl 的 pthread/iconv/socket 均在 libc 中，静态库无额外系统依赖
- 默认构建静态库 `libxerces-c.a`（上游工程名保持为 `xerces-c`，见版本 notes）
- 上游 `ctest` 在构建后运行（ThreadTest 多线程压力项除外，详见版本 notes 与 test_package/MANIFEST.yml）

## 依赖
- 无外部 Conan 依赖（后端均为 libc-only）

## 功能验证
```bash
# test_package：XercesDOMParser 解析内存 XML + DOM 遍历断言
./test_xerces
```

## 参考
- 官网: https://xerces.apache.org/xerces-c/
- 上游仓库: https://github.com/apache/xerces-c
