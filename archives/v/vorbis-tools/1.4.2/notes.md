# vorbis-tools 1.4.2 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-03
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 初始化编译环境：
   ```bash
   source .build-context-vorbis-tools-1.4.2
   cd $BUILD_SRC_DIR
   ```

2. 应用平台识别补丁：
   - 修改 config.guess 添加 HarmonyOS 平台识别
   - 修改 config.sub 接受 linux-ohos 作为合法 OS

3. 执行编译：
   ```bash
   ./configure --prefix=/storage/Users/currentUser/usr/local
   make -j2
   make install DESTDIR=/storage/Users/currentUser/test-install-vorbis-tools-1.4.2
   ```

4. 验证安装：
   ```bash
   ~/usr/local/bin/oggenc --version
   ~/usr/local/bin/oggdec --version
   ```

5. 制作预编译包：
   ```bash
   python3 $SKILL_ROOT/scripts/ohc-run.py package vorbis-tools 1.4.2
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 平台识别失败 | config.guess/config.sub 不识别 HarmonyOS | 添加 HarmonyOS 平台识别分支（0001/0002 补丁） |
| 2 | configure tmp 权限错误 | mktemp 使用 umask 077 导致权限问题 | 修改 umask 为 022（0003 补丁） |

## 源码修改

共 3 个补丁：

### 0001-config.guess.patch
- 文件: config.guess
- 修改: 添加 HarmonyOS 平台识别分支
- 内容: aarch64/arm64/x86_64/i?86 映射到 *-unknown-linux-ohos

### 0002-config.sub.patch
- 文件: config.sub
- 修改: 接受 linux-ohos* 作为合法 OS
- 内容: 在 maybe_os case 中添加 linux-ohos*

### 0003-configure.patch
- 文件: configure
- 修改: 修改 tmp 目录创建权限
- 内容: 将 umask 077 改为 022

## 依赖版本

- libogg: 1.3.5（预编译包）
- libvorbis: 1.3.7（预编译包）

## 验证结果

```bash
$ ~/usr/local/bin/oggenc --version
oggenc from vorbis-tools 1.4.2

$ ~/usr/local/bin/oggdec --version
oggdec from vorbis-tools 1.4.2

$ ls ~/test-install-vorbis-tools-1.4.2/storage/Users/currentUser/usr/local/bin/
oggdec (283K), oggenc (1.0M), ogginfo (351K), vcut (247K), vorbiscomment (303K)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| vorbis-tools-1.4.2-ohos-aarch64.tar.gz | 2.1M | 预编译包（主包） |
| vorbis-tools-1.4.2-ohos-aarch64-debug.tar.gz | 586K | 调试符号包 |

## 注意事项

1. vorbis-tools 依赖 libogg 和 libvorbis，需要先安装这两个库的预编译包
2. 补丁仅涉及平台识别和权限修复，不涉及功能修改
3. 编译简单，无兼容性问题

---
**编译结束**: 2026-06-03 17:56
**最终状态**: built