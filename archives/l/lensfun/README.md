# lensfun

## 简介
lensfun 是一个用于镜头校正的开源库，提供了相机和镜头的数据库，用于图像处理软件中的自动畸变校正。

## 特性
- 镜头畸变校正
- 色差校正
- 暗角校正
- 支持多种相机和镜头品牌
- 提供丰富的数据库

## 版本信息
- **当前版本**: 0.3.4
- **发布日期**: 2023-07-12

## 编译依赖
- glib2 >= 2.26

## 可选依赖
- libpng（用于 lenstool）

## 使用方式
```bash
pkg-config --cflags lensfun
pkg-config --libs lensfun
```

## 相关链接
- 官方网站: https://lensfun.github.io/
- GitHub: https://github.com/lensfun/lensfun