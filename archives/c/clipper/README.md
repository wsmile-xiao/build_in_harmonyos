# Clipper2

## 软件简介

Clipper2 是一个高性能的多边形裁剪库（Polygon Clipping Library），支持多种多边形操作：

- 并集（Union）
- 交集（Intersection）
- 差集（Difference）
- 异或（XOR）
- 偏移（Offset）
- 简化（Simplify）
- 三角化（Triangulation）

## 特性

- 支持整数和浮点数坐标
- 高性能算法
- 支持 C++、C# 和 Delphi Pascal
- 无外部依赖
- 跨平台支持

## 版本信息

当前版本：2.0.1

## 安装使用

```bash
# 安装预编译包
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- clipper 2.0.1
```

## 链接方式

```cmake
# CMakeLists.txt
find_package(Clipper2 REQUIRED)
target_link_libraries(your_target PRIVATE Clipper2::Clipper2)
```

## 项目主页

https://github.com/AngusJohnson/Clipper2
