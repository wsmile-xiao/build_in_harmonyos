# WCSLIB 8.4 编译笔记

## 编译状态
**成功** - 静态库安装完成

## 编译日期
2026-06-11

## 源码信息
- 版本: wcslib-8.4（实际下载的文件名为wcslib-8.2.tar.xz，但内容是8.4版本）
- 来源: 本地文件（从Debian镜像获取）
- 构建系统: autotools/GNUmakefile

## 遇到的问题及解决方案

### 问题1: 官方下载源超时
- **描述**: FTP和HTTPS官方下载源连接极其缓慢，多次尝试均超时
- **解决方案**: 使用本地已有的tarball（从Debian镜像获取的wcslib_8.4+ds.orig.tar.xz）

### 问题2: configure脚本无法创建临时文件
- **描述**: config.status无法创建临时目录中的subs1.awk文件，提示"Permission denied"
- **原因**: autoconf生成的configure脚本在某些情况下无法正确创建临时文件
- **解决方案**: 手动创建makedefs和wcsconfig.h文件，绕过configure

### 问题3: GNUmakefile依赖config.status
- **描述**: GNUmakefile会检查config.status是否存在，不存在则尝试重新运行configure
- **解决方案**: 直接在C目录手动编译源文件，创建静态库

### 问题4: getwcstab.c编译失败
- **描述**: getwcstab.c需要cfitsio头文件（fitsio.h），但cfitsio未安装
- **解决方案**: 排除getwcstab.o，只编译其他22个源文件创建libwcs-8.4.a

### 问题5: 共享库创建失败
- **描述**: 创建libwcs.so时提示"recompile with -fPIC"
- **原因**: .o文件未使用-fPIC编译
- **解决方案**: 暂不创建共享库，仅提供静态库libwcs-8.4.a（gnuastro可以使用静态库）

## 编译命令记录

```bash
# 手动编译源文件
cd /storage/Users/currentUser/builds/wcslib-8.4.work/C
for f in *.c; do
  if [ ! -f "${f%.c}.o" ]; then
    cc -I. -I.. -O2 -Wall -c "$f"
  fi
done

# 创建静态库（排除getwcstab.o）
ar rc libwcs-8.4.a $(ls *.o | grep -v getwcstab.o)
ranlib libwcs-8.4.a

# 安装
cp libwcs-8.4.a $DEFAULT_PREFIX/lib/
cp *.h $DEFAULT_PREFIX/include/wcslib-8.4/
ln -s wcslib-8.4 $DEFAULT_PREFIX/include/wcslib

# 创建pkg-config文件
cat > $DEFAULT_PREFIX/lib/pkgconfig/wcslib.pc << EOF
prefix=/storage/Users/currentUser/usr/local
exec_prefix=/storage/Users/currentUser/usr/local
libdir=/storage/Users/currentUser/usr/local/lib
includedir=/storage/Users/currentUser/usr/local/include/wcslib

Name: WCSLIB
Description: An implementation of the FITS World Coordinate System standard
Version: 8.4
Requires:
Libs: -L${libdir} -lwcs-8.4 -lm
Cflags: -I${includedir}
EOF
```

## 安装验证

```bash
$ pkg-config --modversion wcslib
8.4

$ pkg-config --cflags wcslib
-I/storage/Users/currentUser/usr/local/include/wcslib

$ pkg-config --libs wcslib
-L/storage/Users/currentUser/usr/local/lib -lwcs-8.4 -lm
```

## 产物信息

- 静态库: `/storage/Users/currentUser/usr/local/lib/libwcs-8.4.a` (1.7M)
- 头文件目录: `/storage/Users/currentUser/usr/local/include/wcslib-8.4/`
- pkg-config文件: `/storage/Users/currentUser/usr/local/lib/pkgconfig/wcslib.pc`

## 知识沉淀

1. **autoconf临时文件问题**: 当config.status无法创建临时文件时，可以手动创建makedefs和wcsconfig.h绕过configure
2. **WCSLIB依赖**: wcslib可选依赖cfitsio（用于某些测试和工具），核心库不需要cfitsio
3. **静态库命名**: wcslib静态库命名为libwcs-{version}.a（如libwcs-8.4.a），需要在pkg-config中正确指定

---
**编译结束**
**最终状态**: 成功（静态库安装完成）
---

**编译结束**: 2026-06-12 14:39
**最终状态**: built
