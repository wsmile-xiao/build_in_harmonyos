# antiword 0.37 编译笔记

## 软件信息
- 名称: antiword
- 版本: 0.37
- 描述: MS Word 文档转文本转换器
- 构建系统: 手写 Makefile (Makefile.Linux)

## 编译过程

### 第一步: 源码下载
- 原始 URL: http://www.winfield.demon.nl/files/antiword-0.37.tar.gz (已失效，返回 404)
- 实际使用 URL: http://deb.debian.org/debian/pool/main/a/antiword/antiword_0.37.orig.tar.gz
- 文件大小: 311KB

### 第二步: 构建系统适配
- 原构建系统: 手写 Makefile.Linux（非 autotools）
- 修改内容:
  - CC = gcc → clang
  - LD = gcc → clang
  - GLOBAL_INSTALL_DIR = /usr/local/bin → ~/usr/local/bin
  - GLOBAL_RESOURCES_DIR = /usr/share/antiword → ~/usr/local/share/antiword

### 第三步: 编译
- 编译命令: `make -f Makefile.Linux -j2`
- 编译器: clang 15.0.4
- 编译结果: 成功
- 编译警告: 15 个（均为非关键警告，未使用变量）

### 第四步: 安装测试
- 安装命令: `make -f Makefile.Linux global_install DESTDIR=$TEST_PREFIX`
- 安装路径: ~/usr/local
- 安装内容:
  - bin/antiword (248KB)
  - bin/kantiword (脚本，1.4KB)
  - share/antiword/*.txt (29 个字符映射文件)
  - share/antiword/fontnames

### 第五步: 功能验证
- 版本信息: 0.37 (21 Oct 2005)
- 帮助输出: 正常
- 用途: 显示 MS-Word 文件内容

### 第六步: 预编译包制作
- 产物: antiword-0.37-ohos-aarch64.tar.gz (589KB)
- 内容: bin/ + share/antiword/

## 补丁说明
- **0001-Makefile.Linux.patch**: 编译器适配补丁
  - 将 gcc 替换为 clang
  - 适配 OpenHarmony 安装路径
  - 清理注释中的 root 检查代码

## 依赖说明
- 无外部依赖，纯静态编译

## 注意事项
- 该软件使用手写 Makefile，不是标准的 autotools/cmake 构建
- 需要手动修改 Makefile.Linux 文件
- antiword 不支持 --version 参数，使用不带参数运行显示版本

---
**编译结束**: 2026-05-20
**最终状态**: published
