# RELEASENOTE - zutils 1.15

## 版本: 1.15
## 发布日期: 2025-05-27

### 预编译包信息
- 平台: OpenHarmony ARM64
- 编译器: clang++
- 状态: partial (编译成功，测试部分失败)

### 编译说明
1. 源码下载: `https://download-mirror.savannah.gnu.org/releases/zutils/zutils-1.15.tar.lz`
2. 配置: `./configure --prefix=/storage/Users/currentUser/usr/local CXX=clang++`
3. 编译: `make -j$(nproc)`
4. 安装: `make install DESTDIR=...`

### 已知问题
- 测试因平台限制失败:
  - gzip 权限拒绝
  - FIFO 创建限制
  - 软链接权限问题

### 运行要求
- gzip, bzip2, lzip, xz 压缩工具已安装

### 包含工具
- zcat, zcmp, zdiff, zegrep, zfgrep, zgrep, ztest, zupdate

---
编译日期: 2026-04-24
编译者: OpenHarmony Compile Agent