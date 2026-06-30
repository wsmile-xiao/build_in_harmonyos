# libtirpc 1.3.3 编译笔记

## 编译日期
2026-05-22

## 编译环境
- OpenHarmony系统
- HMDFS文件系统限制

## 关键问题与解决方案

### 1. HMDFS临时文件权限问题
**问题**：config.status脚本在当前目录创建临时文件时遇到HMDFS权限限制。
**错误**：`./config.status[990]: can't create ./confXXXXXX/subs1.awk: Permission denied`
**解决方案**：
- 将源码复制到 `/data/storage/el2/base/tmp-build/libtirpc-1.3.3` 目录进行编译
- 该目录在hmfs文件系统上，没有HMDFS的限制

### 2. aclocal-1.16 perl依赖问题
**问题**：aclocal-1.16脚本的shebang指向错误的perl路径
**错误**：`/storage/Users/currentUser/usr/local/bin/aclocal-1.16: bad interpreter: /storage/Users/currentUser/usr/local/bin/perl: no such file or directory`
**解决方案**：
- 创建perl符号链接：`ln -sf /data/service/hnp/bin/perl /storage/Users/currentUser/usr/local/bin/perl`

### 3. GSS-API依赖缺失
**问题**：configure报错缺少gssapi.h头文件
**错误**：`configure: error: gssapi.h not found. Use --disable-gssapi, or install GSS-API.`
**解决方案**：
- 使用 `--disable-gssapi` 参数禁用GSS-API功能
- GSS-API是libtirpc的可选安全功能，对OpenHarmony平台可以禁用

## 编译参数
```bash
./configure --prefix=/storage/Users/currentUser/usr/local --disable-gssapi
make -j1
make install DESTDIR=/storage/Users/currentUser/tmp/test-install-libtirpc-1.3.3
```

## 编译产物
- libtirpc.so.3.0.0 (动态库，588KB)
- libtirpc.a (静态库，1.2MB)
- 头文件：/include/tirpc/*.h

## 编译警告
- 大量C语言原型警告（deprecated non-prototype）
- 这些是旧式C代码风格警告，不影响功能

## 后续建议
1. 如果其他软件需要GSS-API功能，可以考虑编译GSS-API库
2. HMDFS文件系统限制是OpenHarmony平台的固有问题，建议在非HMDFS目录编译
3. perl符号链接已创建，后续编译automake相关软件时可以正常使用
---

**编译结束**: 2026-05-22 15:50
**最终状态**: built
