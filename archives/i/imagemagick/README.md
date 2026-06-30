# ImageMagick (v6 legacy)

ImageMagick v6 是 ImageMagick 的 legacy 版本，用于编辑和操作数字图像。支持多种文件格式（JPEG、PNG、GIF、TIFF、PDF 等）。

## 描述
ImageMagick 是一个免费的开源软件套件，可以创建、编辑、组合或转换位图图像。v6 是 legacy 维护版本，与 v7 是不同的源码仓库。

## 已编译版本
- 6.9.13-48 (2026-05-25)

## 依赖
- libjpeg-turbo 3.1.4.1
- xz 5.6.2
- lcms2 (system)
- libpng 1.6.43

## 使用方法
```bash
# 转换图片格式
convert input.png output.jpg

# 查看图片信息
identify image.png

# 批量处理
mogrify -resize 50% *.jpg
```

## 官方网站
- Legacy (v6): https://legacy.imagemagick.org/
- Modern (v7): https://imagemagick.org/

## 源码仓库
- GitHub v6: https://github.com/ImageMagick/ImageMagick6