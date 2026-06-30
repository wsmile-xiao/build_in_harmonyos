# gallery-dl

gallery-dl 是一个命令行程序，用于从各种图片托管网站下载图片和视频。

## 描述

gallery-dl 支持数百个网站（如 Pixiv、DeviantArt、Reddit、Instagram 等），可以批量下载整个画廊或用户的全部作品。支持自定义文件命名规则、下载过滤和代理设置。

## 已编译版本
- 1.32.1 (2026-05-26)

## 依赖
- Python 3.x

## 特性
- 支持数百个图片托管网站
- 批量下载画廊和用户作品
- 自定义文件命名规则
- 下载过滤和速率限制
- 支持 Ugoira 动画下载

## 使用方法
```bash
# 下载画廊
gallery-dl <url>

# 查看版本
gallery-dl --version
```

## 注意事项
- 需要配置某些网站的认证信息（如 cookies、API keys）