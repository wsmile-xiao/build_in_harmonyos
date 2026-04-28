# RapidJSON

## 简介
RapidJSON 是一个高性能的 C++ JSON 解析器和生成器，提供 SAX 和 DOM 风格的 API。

## OHOS 适配
- Header-only 库，无需编译二进制文件
- CMake 不识别 HarmonyOS，采用手动安装头文件方案
- 安装头文件到 include/rapidjson/，创建 pkg-config 和 CMake 配置文件

## 依赖
- 无外部依赖（header-only）
- 可选：CMake（用于安装配置文件生成）

## 功能验证
```bash
# 验证头文件安装
ls ~/usr/local/include/rapidjson/*.h
pkg-config --cflags RapidJSON
```

## 参考
- 官网：https://rapidjson.org/
- GitHub：https://github.com/Tencent/rapidjson
