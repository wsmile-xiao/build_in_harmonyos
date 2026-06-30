# smenu 1.5.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-26
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. init-build 下载并解压源码包
2. 替换 build-aux/config.guess 和 config.sub（automake-1.17版本，支持 aarch64-unknown-linux-ohos）
3. ./configure --prefix=$DEFAULT_PREFIX
4. make -j1
5. make install DESTDIR=$TEST_PREFIX
6. make check（通过，无错误输出）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别系统类型 | 自带的 config.guess 版本旧，不支持 HarmonyOS | 用 automake-1.17 的 config.guess/config.sub 替换 build-aux/ 中的版本 |
| 2 | config.status 创建临时文件 Permission denied | HMDFS 文件系统下 umask 077 创建的目录权限为 700，UID映射导致写入失败 | 将 config.status 和 configure 中的 umask 077 改为 umask 022 |

## 源码修改

### 1. 替换 config.guess / config.sub
- 文件: build-aux/config.guess, build-aux/config.sub
- 操作: 用 /storage/Users/currentUser/usr/local/share/automake-1.17/ 中的版本替换
- 原因: 自带版本不支持 HarmonyOS 系统检测

### 2. umask 077 → 022
- 文件: config.status (行 579, 584), configure
- 操作: sed -i 's/umask 077/umask 022/g'
- 原因: HMDFS 文件系统下 umask 077 创建的 700 权限目录无法写入

## 产物

- bin/smenu (ELF 64-bit aarch64, 动态链接 libc.so, ncurses 已静态链接)
- share/man/man1/smenu.1

## 静态链接 (R26)

smenu 链接了 libncursesw.a（静态），readelf -d 显示仅依赖 libc.so（系统 musl libc）。
无非系统动态依赖，满足 R26 终端工具静态链接要求。

{如有补丁，列出文件名和修改内容；无则删除此节}

## 依赖版本

{列出本次编译依赖的具体软件版本}

## 验证结果

```bash
{验证命令和结果}
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
{有打包产物时添加；无则删除此节}

## 注意事项

{需要特别注意的点；无则删除此节}
---

**编译结束**: 2026-06-29 15:52
**最终状态**: published
