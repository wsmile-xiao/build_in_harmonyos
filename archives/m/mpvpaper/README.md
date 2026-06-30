# mpvpaper

## 简介
mpvpaper 是一个 Wayland 视频壁纸程序，使用 mpv 作为后端播放视频壁纸。

## OHOS 适配
- musl 缺少 pthread_cancel/pthread_setcancelstate，需使用 `#ifdef __OHOS__` 守卫 stub 替代
- 改用 flag-based exit 机制替代 pthread_cancel

## 依赖
- mpv
- wayland-client

## 参考
- https://github.com/GhostNaN/mpvpaper