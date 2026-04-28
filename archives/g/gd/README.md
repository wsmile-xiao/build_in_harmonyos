# gd

## 简介
GD Graphics Library — 开源图像处理库，支持 PNG、JPEG、GIF、WebP、BMP 等格式的创建和操作。

## OHOS 适配
- 需 config.guess/config.sub 补丁支持 HarmonyOS
- 依赖 libpng、freetype、libjpeg-turbo 等多个图像库
- configure 会检测可选依赖，缺失不影响核心功能编译

## 依赖
- 编译依赖：libpng, freetype, libjpeg-turbo（可选）
- 运行依赖：无

## 功能验证
```bash
# 验证库安装
ls -la $HOME/usr/local/lib/libgd*
pkg-config --modversion gdlib
```

## 参考
- 官方网站：https://libgd.github.io/
- GitHub：https://github.com/libgd/libgd
