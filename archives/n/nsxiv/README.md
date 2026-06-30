# nsxiv

## 简介
nsxiv (Neo Simple X Image Viewer) 是 sxiv 的轻量级分支，提供快速图像查看功能。

## OHOS 适配
- 禁用 HAVE_INOTIFY=0：OHOS 内核不提供 inotify API
- 修改 PREFIX 路径适配 OHOS 安装位置

## 依赖
- imlib2
- libx11

## 参考
- https://github.com/nsxiv/nsxiv