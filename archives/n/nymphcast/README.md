# nymphcast

## 简介
NymphCast 是一个音频和视频投屏系统，可将设备转变为媒体接收器，支持从移动设备投屏到电视或扬声器。

## OHOS 适配
- 上游无 CMakeLists.txt，使用 Makefile 构建
- patch 0001/0002 对上游既有 NymphCastServer.cpp / ffplay/sdl_renderer.cpp 做 __OHOS__ 增量适配
  （两文件在 v0.2-alpha0 上游源码树中真实存在，非缺失）
- SDL2 renderer 需适配 OHOS 平台差异
- nymphrpc、libnymphcast、SDL2_image 已发布为 Conan 包并被 requirements() 引用

## 运行时
- 产物 nymphcast_server 为 Conan 托管动态链接（无 RPATH），运行时需要 conanrun env
  （`conan install --requires=nymphcast/0.2-alpha0` 后 source conanrun 环境），裸跑需自行
  设置 LD_LIBRARY_PATH 指向各依赖 lib 目录

## 依赖
- Poco C++ Libraries
- FFmpeg
- SDL2
- nymphrpc（独立仓库）
- libnymphcast（独立仓库）
- SDL2_image

## 参考
- https://github.com/MayaPosch/NymphCast
