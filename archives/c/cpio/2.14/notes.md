# cpio 2.14 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-28
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 下载源码: wget https://ftp.gnu.org/gnu/cpio/cpio-2.14.tar.gz
2. 解压到 VPATH 构建目录
3. 修改 config.guess/config.sub（添加 HarmonyOS 支持）
4. 修改 configure umask（077->022，解决 HMDFS 权限问题）
5. VPATH 构建: ../cpio-2.14.work/configure --prefix=$HOME/usr/local
6. 编译: make -j4
7. 手动安装到 staging 目录

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别系统 | HarmonyOS 未被识别（E072） | 添加 aarch64:HarmonyOS:*:* 分支，返回 aarch64-unknown-linux-ohos |
| 2 | config.sub 无法验证三元组 | ohos 未在白名单（E072） | 下载最新 GNU config.sub（已支持 ohos） |
| 3 | config.status 权限错误 | HMDFS UID 映射 + umask 077（E011） | 修改 configure 中 umask 077 -> umask 022 |

## 源码修改

### 补丁列表
1. 0001-build-aux-config.guess.patch - 添加 HarmonyOS 支持
2. 0002-build-aux-config.sub.patch - 更新到 GNU config（支持 ohos）
3. 0003-doc-stamp-vti.patch - 文档时间戳
4. 0004-doc-version.texi.patch - 文档版本
5. 0005-configure-umask.patch - 修复 HMDFS 权限问题（umask 077->022）

## 依赖版本

- clang: 15.0.4
- make: GNU Make 4.4.1
- gawk: GNU Awk 5.4.0
- automake: 1.16.5

## 验证结果

```bash
$ cpio --version
cpio (GNU cpio) 2.14
Copyright (C) 2023 Free Software Foundation, Inc.
License GPLv3+: GNU GPL version 3 or later <https://gnu.org/licenses/gpl.html>
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| cpio | 547KB | 主程序二进制 |
| rmt | 190KB | 远程磁带守护程序 |

## 注意事项

1. HMDFS 文件系统需要 umask 022 而不是 077（E011）
2. make install 需要跳过文档构建（缺少 makeinfo）
3. VPATH 构建模式可避免源码目录污染

## 知识沉淀

- **E072**: config.sub 三元组验证失败（ohos 未识别）
- **E011**: HMDFS umask 077 权限问题（临时目录不可写）

---

**编译结束**: 2026-05-28 19:05
**最终状态**: published
**预编译包**: cpio-2.14-ohos-aarch64.tar.gz (251KB)
**打包规范**: 扁平结构（bin/、libexec/），已签名，已 strip
