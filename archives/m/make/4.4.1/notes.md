# GNU make 4.4.1 编译笔记

## 编译状态

**成功** ✅

## 编译日期

2026-05-18

## 编译环境

- 平台: aarch64-unknown-linux-ohos
- 编译器: clang 15.0.4
- 构建系统: autotools

## 遇到的问题及解决方案

### 问题 1: lld 链接器缺少依赖

**症状**:
```
Error relocating /data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/lld: 
xmlFreeDoc: symbol not found
```

**原因**: lld 链接器依赖 libxml2.so.16，但系统缺少该库。

**解决方案**: 使用 ld.bfd 替代 lld，通过 `-fuse-ld=bfd` 选项指定。

### 问题 2: config.guess 无法识别 HarmonyOS

**症状**:
```
config.guess: unable to guess system type
```

**原因**: GNU config.guess 不包含 HarmonyOS 检测分支。

**解决方案**: 使用 patch-autotools-ohos.pl 脚本打补丁，修改 config.guess 和 config.sub。

### 问题 3: config.sub 不接受 linux-ohos 组合

**症状**:
```
Invalid configuration `aarch64-unknown-linux-ohos': Kernel `linux' not known to work with OS `ohos'.
```

**原因**: config.sub 的 kernel-os 组合验证列表缺少 linux-ohos*。

**解决方案**: 在 config.sub 的 `case $kernel-$os in` 分支中添加 `linux-ohos*`。

### 问题 4: 编译后的程序无法执行

**症状**:
```
./conftest: Permission denied
```

**原因**: 鸿蒙系统要求 ELF 文件必须签名才能执行。

**解决方案**: 创建 clang-sign-wrapper 脚本，在编译后自动签名 ELF 文件。

### 问题 5: mktemp 创建的临时目录无法写入

**症状**:
```
./config.status[864]: can't create ./confXXXXXX/subs1.awk: Permission denied
```

**原因**: HMDFS 文件系统中，mktemp 创建的目录权限为 2700（只有用户有权限，且设置了 SUID），导致子进程无法写入。

**解决方案**: 修改 config.status 使用固定的临时目录（~/tmp/make-config-tmp），而不是 mktemp 创建的动态目录。

## 配置选项

```bash
./configure --prefix=$HOME/usr/local LDFLAGS="-fuse-ld=bfd" CC="$HOME/bin/clang-sign-wrapper"
```

## 验证结果

```bash
$ ~/usr/local/bin/make --version
GNU Make 4.4.1
Built for aarch64-unknown-linux-ohos
Copyright (C) 1988-2023 Free Software Foundation, Inc.
License GPLv3+: GNU GPL version 3 or later <https://gnu.org/licenses/gpl.html>
This is free software: you are free to change and redistribute it.
There is NO WARRANTY, to the extent permitted by law.
```

## 功能测试

```bash
$ cd ~/tmp
$ echo 'all:; echo "make works"' > Makefile
$ ~/usr/local/bin/make
echo "make works"
make works
```

## 补丁文件

- build-aux/config.guess: HarmonyOS 系统识别支持
- build-aux/config.sub: linux-ohos kernel-os 组合支持

## 预编译包

- 路径: archives/m/make/4.4.1/packaging/make-4.4.1-ohos-aarch64.tar.gz
- 大小: 278591 bytes
- 内容: make 二进制文件

## 编译结束

**最终状态**: built
**质量门禁**: ✅ 编译成功、✅ 版本验证、✅ 功能测试、✅ ELF 签名