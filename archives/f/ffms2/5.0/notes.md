# ffms2 5.0 编译笔记

## 编译日期
2026-06-09

## 编译环境
- 平台: aarch64-unknown-linux-ohos
- 编译器: clang 15.0.4
- 构建系统: autotools

## 依赖处理

### FFmpeg依赖
ffms2依赖FFmpeg库：
- libavformat >= 60.16.0
- libavcodec >= 60.31.0
- libswscale >= 7.5.0
- libavutil >= 58.29.0
- libswresample >= 4.12.0

FFmpeg已预先编译并安装在~/usr/local。

### pkgconfig文件修正
需要修正两个问题：
1. 版本号不完整：pkgconfig文件中的Version字段只写了主版本号（60），需要改为完整版本号（60.16.100等）
2. Libs字段错误：使用了`-llibavformat`等错误格式，需要改为`-lavformat`

### FFmpeg头文件
FFmpeg头文件未随库文件一起安装，需要手动从源码目录复制：
- libavformat/*.h → ~/usr/local/include/libavformat/
- libavcodec/*.h → ~/usr/local/include/libavcodec/
- libswscale/*.h → ~/usr/local/include/libswscale/
- libavutil/*.h → ~/usr/local/include/libavutil/
- libswresample/*.h → ~/usr/local/include/libswresample/

## 编译步骤

1. 解压源码：tar -xzf ffms2-5.0.tar.gz
2. 运行autoreconf：autoreconf -ivf（需要pkg.m4宏文件）
3. 配置：./configure --prefix=~/usr/local
4. 编译：make -j2
5. 安装：make install DESTDIR=~/tmp/test-install-ffms2-5.0

## 遇到的问题

### 1. PKG_PROG_PKG_CONFIG宏未展开
**问题**：configure脚本中出现语法错误"syntax error: unexpected '0.22'"
**原因**：pkg.m4宏文件未包含在aclocal.m4中
**解决**：从/data/service/hnp/pkg-config.org/pkg-config_0.29.2/share/aclocal/pkg.m4复制到m4目录，然后重新运行autoreconf

### 2. FFmpeg版本号检查失败
**问题**：configure要求libavformat >= 60.16.0，但pkg-config返回版本为60
**原因**：pkgconfig文件中的Version字段不完整
**解决**：手动修改pkgconfig文件，将完整版本号写入

### 3. FFmpeg链接失败
**问题**：链接器无法找到库文件"ld.lld: error: unable to find library -llibavformat"
**原因**：pkgconfig文件中的Libs字段使用了错误的格式（-llibavformat而不是-lavformat）
**解决**：修改pkgconfig文件，将-llibxxx改为-lxxx

### 4. FFmpeg头文件缺失
**问题**：configure测试程序无法找到libavformat/avformat.h
**原因**：FFmpeg编译时头文件未安装
**解决**：从FFmpeg源码目录手动复制头文件到~/usr/local/include/

## 编译结果

成功编译并安装：
- 二进制文件：ffmsindex
- 库文件：libffms2.so.5.0.0
- 头文件：ffms.h, ffmscompat.h
- pkgconfig文件：ffms2.pc

