# giflib

## 简介
giflib — GIF 图像格式的读写库和工具集。提供 GIF 编码、解码、裁剪等操作。

## OHOS 适配
- 使用简单 Makefile，无 configure 脚本
- 需手动修改 Makefile 添加 `-fPIC` 和交叉编译支持
- 系统缺少 `install` 命令，需手动复制文件
- 文档编译需要 ImageMagick convert，不影响库和工具功能

## 依赖
- 编译依赖：无

## 功能验证
```bash
ls -la $HOME/usr/local/lib/libgif*
giftool --help 2>&1 | head
```

## 参考
- 官方网站：https://sourceforge.net/projects/giflib/
