# libOpenDRIVE

## 简介
libOpenDRIVE 是 OpenDRIVE 格式解析库，用于自动驾驶应用中解析道路网络描述文件。

## OHOS 适配
- CMake 构建
- 0.5.0 版本编译成功（部分质量门禁未通过）
- 无外部依赖（使用内嵌的 pugixml 和 earcut）

## 关键问题
- **C++ 标准库链接**: OpenHarmony 需要显式链接 libc++
  - 解决方案: CMAKE_CXX_FLAGS="-stdlib=libc++"
- **RPATH 设置**: CMake 默认不设置 RPATH
  - 解决方案: CMAKE_INSTALL_RPATH 设置（仍需改进）

## 依赖
- 无外部依赖（dependency-free）

## 功能验证
```bash
# 检查库
ls -la $HOME/usr/local/lib/libOpenDrive.so
# 运行示例
LD_LIBRARY_PATH=$HOME/usr/local/lib $HOME/usr/local/bin/test-xodr
```

## 参考
- 主页: https://github.com/pageldev/libOpenDRIVE