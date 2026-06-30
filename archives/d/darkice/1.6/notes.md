# darkice 1.6 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-29
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. 源码来自 GitHub rafael2k/darkice v1.6 tarball（SVN-imported仓库，嵌套源码需手动提取 darkice/trunk/）
2. 源码缺少 configure 脚步，只有 configure.in，需要运行 autoreconf -fi 重新生成构建系统
3. autoreconf 时需要设置 ACLOCAL_PATH 包含 pkg.m4（来自 pkg-config），否则 PKG_CHECK_MODULES 宏不会展开
4. configure 命令：
   ```bash
   export PKG_CONFIG_PATH=/storage/Users/currentUser/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH
   ./configure --prefix=$DEFAULT_PREFIX \
     --with-vorbis --with-opus --with-flac --with-alsa \
     --without-lame --without-faac --without-fdkaac --without-twolame \
     --without-pulseaudio --without-jack
   ```
5. make -j1 && make install DESTDIR=$TEST_PREFIX

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 嵌套源码检测错误，将 darkice-gui/trunk/po 作为源码 | SVN仓库结构导致嵌套检测选择错误子目录 | 手动从tarball提取 darkice/trunk/ 目录作为源码 |
| 2 | configure 语法错误: unexpected 'VORBIS,' | PKG_CHECK_MODULES宏未展开（aclocal.m4缺少pkg.m4） | 设置ACLOCAL_PATH=/storage/Users/currentUser/usr/local/share/aclocal后重新运行autoreconf -fi |
| 3 | darkice二进制运行时pulseaudio库缺失 | libpulsecommon-17.0.so未安装，pulseaudio共享库不完整 | 重新configure --without-pulseaudio |

## 源码修改

无源码修改。仅运行autoreconf生成构建系统文件（configure/config.guess/config.sub等），这些是生成文件非源文件。

## 依赖版本

- ogg: 已安装（usr/local）
- vorbis/vorbisenc: 已安装（usr/local）
- opus: 已安装（usr/local）
- FLAC: 已安装（usr/local）
- ALSA: 已安装（usr/local）
- lame: 未安装（编译时禁用）
- faac/fdk-aac/twolame: 未安装（编译时禁用）
- pulseaudio: 部分安装但共享库不完整（编译时禁用）
- jack: 未安装（编译时禁用）

## 验证结果

```bash
$ darkice -h
DarkIce 1.6 live audio streamer, http://code.google.com/p/darkice/
Copyright (c) 2000-2007, Tyrell Hungary, http://tyrell.hu/
Copyright (c) 2008-2013, Akos Maroy and Rafael Diniz
Copyright (c) 2014-2024, Rafael Diniz and others
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
{打包后添加}

## 注意事项

- darkice是音频流工具，运行需要至少一个音频输入源（ALSA/OSS/PulseAudio/JACK）
- 此仓库为SVN导入结构，源码在 darkice/trunk/ 子目录中，init-build的嵌套检测可能出错
- autoreconf需要pkg.m4宏才能正确展开PKG_CHECK_MODULES
- pulseaudio在当前环境下共享库不完整，建议不启用
---

**编译结束**: 2026-05-29 11:02
**最终状态**: published
