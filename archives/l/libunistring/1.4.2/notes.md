# libunistring 1.4.2 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-26
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. 下载源码: https://mirrors.tuna.tsinghua.edu.cn/gnu/libunistring/libunistring-1.4.2.tar.xz
2. 解压到 ~/builds/libunistring-1.4.2.work/
3. 应用 HarmonyOS 补丁到 config.guess/config.sub
4. 修改 configure 中的 umask 077 → umask 022（解决 HMDFS 权限问题）
5. configure --prefix=$HOME/usr/local
6. make -j1（约 11 分钟）
7. make install DESTDIR=$TEST_PREFIX
8. make install

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 不识别 HarmonyOS | autotools 缺少 ohos triplet | 应用 E007 补丁 |
| 2 | configure 临时脚本权限 000 | HMDFS umask 077 问题 | 修改 configure 为 umask 022 |

## 依赖版本

无外部依赖。

## 验证结果

```bash
ls ~/usr/local/lib/libunistring.so.5.2.1
# 存在 ✅
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libunistring.so.5.2.1 | 3.3MB | 共享库 |
| libunistring.a | 5.6MB | 静态库 |

## 注意事项

HMDFS 文件系统的 UID 映射机制导致 umask 077 创建的目录权限位缺失。
