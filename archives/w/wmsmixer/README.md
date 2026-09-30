# wmsmixer

Window Maker 混音器 dockapp（dockapp 声音混音器，支持滚轮调节音量）。

- 上游: https://www.hibernaculum.net/wmsmixer.html（当前 DNS 不可达，源码经 dockapps.net 获取）
- 版本: 0.5.1
- 许可证: GPL-2.0

## 简介

wmsmixer 是 Window Maker dockapp 风格的音频混音器小程序，在 wmmixer 基础上改进：
支持滚轮调节音量、显示当前通道音量文本、单声道单宽条显示、多种自定义图标等。

## OHOS 适配

- **构建系统**: 上游为 Imakefile/xmkmf（imake），OHOS 环境无 imake 工具链，配方中改为
  直接 clang++ 编译单一源文件 `wmsmixer.cc`（+ `mixctl.h` 头文件），链接 `-lX11 -lXpm -lXext`
- **依赖链**: libx11 → libxcb → libXau/libXdmcp/xtrans/xorgproto；libxpm；libxext（XShape 扩展）
- **编译注意**: OHOS SDK 的 lld 链接器运行时依赖 llvm/lib 下 libxml2.so.16，编译前须注入
  `LD_LIBRARY_PATH` 指向该目录（同 asmix CI #30003 根因）

## 使用说明

`wmsmixer --version` 与 `--help` 在 X 连接前即可运行（无显示环境可验证）；完整 GUI 运行
需要 X server 与 OSS 混音器设备（/dev/mixer）。

## 依赖

- libx11/6.4.0
- libxpm/3.5.17
- libxext/6.4.0.1
