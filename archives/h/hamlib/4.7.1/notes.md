# hamlib 4.7.1 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-26
- 状态: published

## 编译步骤
./configure --prefix=$DEFAULT_PREFIX --without-libusb --without-readline
make -j1
make install DESTDIR=$TEST_PREFIX

## 遇到的问题与解决方案
- pthread_cancel 在 OpenHarmony 不可用

## 交付物
| 文件 | 说明 |
|------|------|
| hamlib-4.7.1-ohos-aarch64.tar.gz | 预编译包 |
