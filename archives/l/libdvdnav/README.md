# libdvdnav

**libdvdnav** 是 VideoLAN 的 DVD 导航库，封装 DVD 虚拟机与播放状态，
对外提供单一逻辑块流 + dvdnav 事件，支持 DVD 菜单、多角度回放与交互式 DVD。

- 上游：<https://code.videolan.org/videolan/libdvdnav>
- 官方源：<https://download.videolan.org/pub/videolan/libdvdnav/>
- 许可证：GPL-2.0-or-later
- 构建系统：meson

## 依赖

- libdvdread >=6.0.0（vendored meson 子项目，与官方 .gitlab-ci.yml 一致）
- pthread（系统库）

## OHOS 适配要点

- meson 构建，`wrap_mode=nodownload`，所有外部源由 conandata 提供。
- libdvdread 按 `git clone ... subprojects/libdvdread` 官方做法 vendoring 源码。
- libdvdread 默认通过 dlfcn 动态探测 libdvdcss，OHOS 上 dlopen 可用。
- 默认静态（`default_library=static`）。
