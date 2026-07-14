# jp2a

jp2a converts JPEG and WebP images to ASCII art.

## 版本

- 1.3.3

## OpenHarmony PC 适配

当前适配使用 autotools 构建，依赖 libjpeg-turbo 和 libwebp，关闭可选的 curl 网络下载能力和 termlib 终端尺寸探测，并移除当前制品仓不可用的 PNG/EXIF 依赖。

## 安装

```bash
conan install --requires=jp2a/1.3.3 -r=ohpcd --build=missing
```

## 验证

```bash
jp2a --version
jp2a --help
```
