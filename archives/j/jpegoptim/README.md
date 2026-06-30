# jpegoptim

jpegoptim 是一个用于优化和压缩 JPEG 文件的命令行工具。

## 描述
jpegoptim 可以无损或有损地优化 JPEG 文件，减少文件大小而不显著降低图像质量。支持 stripping EXIF/IPTC/ICC profiles 等元数据。

## 已编译版本
- v1.5.6 (2026-05-25)

## 依赖
- libjpeg-turbo 3.1.4.1

## 使用方法
```bash
# 无损优化
jpegoptim image.jpg

# 有损优化（指定最大质量）
jpegoptim -m80 image.jpg

# Strip 所有元数据
jpegoptim --strip-all image.jpg
```