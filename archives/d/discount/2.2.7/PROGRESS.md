# discount 2.2.7 编译记录

## 编译开始
**时间**: 2026-04-29 23:55  
**软件**: discount  
**版本**: 2.2.7  
**构建系统**: autotools (configure.sh)

## 步骤记录

### Step 1: init-build
- ✅ 下载源码（通过 git clone，因 tarball 解压问题）
- ✅ 替换源码目录为完整源码
- ✅ 环境检查通过

### Step 2: configure
- ✅ 运行 `./configure.sh --prefix=/storage/Users/currentUser/usr/local`
- ✅ 成功检测所有依赖函数和头文件

### Step 3: make
- ✅ 编译成功（有警告：旧式函数定义）
- ⚠️ 遭遇硬链接问题（E079: HMDFS不支持硬链接）
- ✅ 修复 librarian.sh：用 `cp` 替代 `ln`

### Step 4: make install (DESTDIR)
- ⚠️ 遭遇 install 命令缺失（E098）
-  创建 install-sh 替代脚本
-  修复 librarian.sh install 部分
- ✅ 成功安装到 staging 目录

### Step 5: 验证
-  二进制存在: markdown (92KB)
- ✅ 库文件存在: libmarkdown.a (104KB)
-  头文件存在: mkdio.h

## 问题与修复

### 问题1: tarball 解压不完整
- **现象**: tarball 仅包含 cmake 子目录
- **原因**: GitHub tarball 格式问题
- **修复**: 使用 git clone 获取完整源码

### 问题2: 硬链接不支持（E079）
- **文件**: librarian.sh
- **修复**: 将 `/usr/bin/ln $LIBRARY.a $LIBRARY` 改为 `cp $LIBRARY.a $LIBRARY`

### 问题3: install 命令缺失（E098）
- **文件**: Makefile, librarian.sh
- **修复**: 创建 install.sh 替代脚本，修改 Makefile 和 librarian.sh

## 编译结束
**时间**: 2026-04-30 00:05  
**最终状态**: success  
**备注**: 成功编译并通过基本验证