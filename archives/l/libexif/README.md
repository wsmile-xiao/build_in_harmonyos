# libexif

## 简介

libexif 是一个用于处理 EXIF（Exchangeable Image File Format）元数据的库。它支持读取、写入和编辑图像文件（如 JPEG）中嵌入的 EXIF 信息，包括相机型号、拍摄时间、曝光参数、GPS 坐标等。

## OHOS 适配

- 使用 autotools 构建系统（configure + make）
- 需要更新 config.guess 和 config.sub 以识别 HarmonyOS 平台
- configure 临时文件创建受 SELinux 限制，需修改临时目录路径为 ${HOME}/tmp
- 编译为纯静态库（libexif.a），无可执行二进制文件
- make check 通过：14 PASS, 1 SKIP

## 依赖

无外部编译依赖（自包含构建）。

## 功能验证

```bash
# 验证安装
pkg-config --modversion libexif
# 输出: 0.6.26.1

# 验证静态库
ls -lh $HOME/usr/local/lib/libexif.a

# 验证头文件
ls $HOME/usr/local/include/libexif/
```

## 参考

- 官网: https://libexif.github.io
- 源码: https://github.com/libexif/libexif
- 文档: https://libexif.sourceforge.net/manual.html