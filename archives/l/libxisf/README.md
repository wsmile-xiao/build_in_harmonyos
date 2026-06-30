# libxisf

> XISF (Extensible Image Serialization Format) 图像格式库

## 简介

libXISF 是用于读写 XISF 图像格式的 C++ 库。XISF 是一种专为天文摄影设计的开放图像格式，支持高精度浮点数据、多层图像、扩展元数据等功能。

## OHOS 适配要点

- CMake 项目需要显式链接 libc++（测试程序链接缺失）
- 测试运行需要设置 LD_LIBRARY_PATH 到 build 目录
- 需修改 CMakeLists.txt 在 target_link_libraries 中添加 c++

## 排除与替代

无

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| cmake | 3.16+ | 构建系统 |
| libc++ | 系统 | C++ 标准库 |

## 功能验证

```bash
# 验证库安装
pkg-config --modversion libxisf
# 输出: 0.2.13
```

## 参考

- [libXISF 官方仓库](https://gitea.nouspiro.space/nou/libXISF)
- [XISF 规范](https://xisf.org/)