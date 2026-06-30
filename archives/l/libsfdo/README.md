# libsfdo

## 简介
libsfdo是XDG规范的实现库，提供basedir、desktop-file、desktop、icon等组件。

## OHOS 适配
- 使用meson构建系统
- 包含4个共享库：libsfdo-basedir, libsfdo-desktop-file, libsfdo-desktop, libsfdo-icon
- meson构建需正确设置CC/CXX/AR/RANLIB环境变量

## 依赖
- meson
- ninja

## 功能验证
ls ~/usr/local/lib/libsfdo-*.so

## 参考
- 源码: https://gitlab.com/nickolas/sfdo
