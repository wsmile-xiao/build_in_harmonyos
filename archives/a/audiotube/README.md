# audiotube

> KDE Kirigami music player with YouTube Music integration

## 简介

audiotube 是 KDE 开发的音乐播放器，基于 Kirigami/QML UI 框架，集成 YouTube Music 服务。由于 OHOS 平台缺少 Qt6Qml/Qt6Quick/KF6Kirigami 等 QML GUI 依赖，当前仅以 OHOS_MINIMAL_BUILD 模式编译了底层 ytm 静态库（pybind11 封装的 ytmusicapi Python 绑定接口）。

## OHOS 适配要点

- OHOS 缺少 Qt6Qml/Qt6Quick/Qt6QuickControls2/Qt6Multimedia/KF6Kirigami 等 GUI 依赖
- OHOS_MINIMAL_BUILD 模式仅构建 ytm 静态库，不构建 QML/Kirigami GUI
- 当 Qt/KF6 QML 组件可用后，可关闭 OHOS_MINIMAL_BUILD 构建完整应用

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| pybind11 | 3.0.4 | Python/C++ 绑定 |
| ECM | 6.0 | KDE CMake 预置模块 |

## 功能验证

```bash
# 检查 ytm 静态库
ls ~/usr/local/lib/libytm.a
ls ~/usr/local/include/audiotube/ytmusic.h
```

## 参考

- [源码仓库](https://github.com/KDE/audiotube)