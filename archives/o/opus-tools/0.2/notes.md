# opus-tools 0.2 编译笔记

## 编译环境
- OS: HarmonyOS (aarch64-unknown-linux-ohos)
- Compiler: clang 15.0.4
- Prefix: /storage/Users/currentUser/usr/local

## 关键问题及解决方式

### 1. 源码下载失败 (GitHub不可达)
- **问题**: GitHub URL无法下载，DNS解析超时
- **解决**: 使用xiph.org官方下载URL: https://downloads.xiph.org/releases/opus/opus-tools-0.2.tar.gz

### 2. E007: config.guess无法识别HarmonyOS
- **问题**: autotools的config.guess(2017)不支持HarmonyOS系统
- **解决**: 替换为automake-1.16的config.guess/config.sub，并用patch-autotools-ohos.pl验证(Score: 5/5)

### 3. 依赖缺失
- **opus**: 通过cmd-pkgs安装opus 1.4
- **libogg**: 通过cmd-pkgs安装libogg 1.3.6
- **opusfile**: 通过cmd-pkgs安装opusfile 0.12
  - 注意: 头文件和库文件安装路径不在标准位置，需手动移动
  - opusfile.h需移到~/usr/local/include/opus/
  - libopusfile.a/so需移到~/usr/local/lib/
  - .pc文件prefix需修正为完整路径
- **flac**: 通过cmd-pkgs安装flac 1.4.3
- **libopusenc**: 从源码编译libopusenc 0.2.1
  - config.status有HMDFS临时目录权限问题，需使用--no-create+手动修复

### 4. opusurl缺失 (HTTP URL streaming)
- **问题**: opusurl>=0.5为configure硬性要求，但cmd-pkgs的opusfile包不含opusurl
- **解决**: 修改configure.ac使opusurl可选(PKG_CHECK_MODULES ACTION-IF-NOT-FOUND)
  - 修改opusdec.c添加#if HAVE_OPUSURL条件分支，opusurl不可用时直接用op_open_file()
  - 重新autoconf生成configure脚本

### 5. config.status HMDFS权限问题
- **问题**: autoconf 2.69的config.status使用umask 077创建临时目录，在HMDFS上导致Permission denied
- **解决**: 使用autoconf 2.72重新生成configure(使用umask 000)，或使用--no-create然后手动修改config.status

### 6. cmd-pkgs安装包路径问题
- **问题**: 多个预编译包的头文件/库文件/pc文件安装位置不在标准路径
- **解决**: 手动将文件移动到正确位置(bin/lib/include/pkgconfig)

## 编译命令
```bash
./configure --prefix=$DEFAULT_PREFIX
make
make install DESTDIR=$TEST_PREFIX
make install
```

## 制品
- opus-tools-0.2-ohos-aarch64.tar.gz (1330KB)
- opus-tools-0.2-ohos-aarch64-debug.tar.gz
- 包含: opusenc, opusdec, opusinfo, opusrtp (仅opusenc/opusdec/opusinfo已安装)
---

**编译结束**: 2026-05-26 12:09
**最终状态**: published
