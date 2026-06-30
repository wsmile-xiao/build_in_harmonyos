# libhtp 0.5.53 编译笔记

## 编译环境
- 编译日期: 2026-06-04
- 编译器: clang
- 构建系统: autotools

## 源码信息
- 源码地址: https://github.com/OISF/libhtp/archive/refs/tags/0.5.53.tar.gz
- 版本: 0.5.53

## 编译依赖
- zlib
- iconv

## 编译过程

### 1. 源码下载与解压
从 GitHub 下载 libhtp 0.5.53 源码包并解压。

### 2. 源码预处理
libhtp 源码包不包含 configure 脚本，需要运行 autogen.sh 生成：
```bash
./autogen.sh
```

### 3. 配置问题修复
在 HMDFS 文件系统环境下，configure 脚本中的 `umask 077` 会导致临时文件创建失败。
错误信息：
```
HMDFS hmmac MAC 拒绝访问
```

解决方案：
使用 hints/post-download.sh 自动化修复 configure 脚本：
```bash
sed -i 's/umask 077/umask 022/g' configure
```

### 4. 配置与编译
```bash
./configure --prefix=/usr
make
make install
```

## 验证
```bash
pkg-config --modversion htp
# 输出: 0.5.53
```

## 关键发现
1. libhtp 使用 autotools 构建系统，但源码包需要先运行 autogen.sh
2. HMDFS 文件系统与 umask 077 存在兼容性问题
3. 使用 hints/post-download.sh 替代传统的 patch 文件方案，更加灵活

## 参考链接
- https://github.com/OISF/libhtp