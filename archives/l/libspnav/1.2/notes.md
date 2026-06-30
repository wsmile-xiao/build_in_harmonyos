# libspnav 1.2 编译笔记

## 编译步骤
1. ./configure --prefix=$HOME/usr/local --disable-x11
2. make && make install

## 问题与方案
### 问题: 缺少 X11 开发库
- 解决: --disable-x11

## 交付物
- 库文件: libspnav.a, libspnav.so
