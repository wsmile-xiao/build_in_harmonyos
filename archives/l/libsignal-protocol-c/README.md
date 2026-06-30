# libsignal-protocol-c

## 简介
libsignal-protocol-c是Signal Protocol的C语言实现，用于安全消息传输。

## OHOS 适配
- CMake版本兼容性问题：需要修改cmake_minimum_required>=3.5(适配CMake 4.x)
- 生成的库为静态库libsignal-protocol-c.a
- **注意：该项目已于2022-02-12归档，不再维护**

## 补丁说明
- 0001-CMakeLists.txt.patch: 修复CMake版本兼容性(2.8.4→3.5)

## 依赖
无编译依赖

## 功能验证
ls ~/usr/local/lib/libsignal-protocol-c.a

## 参考
- 源码: https://github.com/signalapp/libsignal-protocol-c
- 项目状态: Archived (2022-02-12)
