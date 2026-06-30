# libxpresent 1.0.2 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-16
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 下载源码：libXpresent-1.0.2.tar.xz
2. 解压并初始化归档
3. 应用平台适配补丁
4. configure --prefix=$HOME/usr/local
5. make -j1
6. make install DESTDIR=$TEST_PREFIX
7. 打包预编译包

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess无法识别HarmonyOS | GNU config.guess缺少HarmonyOS检测分支 | 使用patch-autotools-ohos.pl补丁脚本 |
| 2 | configure创建临时文件失败 | HMDFS SELinux限制，umask 077阻止临时文件创建 | sed -i 's/umask 077/umask 022/g' configure |
| 3 | 缺少依赖xproto/presentproto等 | X协议头文件未安装 | 安装xorgproto 2024.1预编译包 |
| 4 | 缺少依赖libXfixes | X Fixes库未安装 | 编译libXfixes 6.0.2 |
| 5 | 缺少依赖libXrender/libXrandr | 预编译包损坏 | 重新编译libXrender和libXrandr |

## 源码修改

应用补丁：
- 0001-config.guess.patch - 添加HarmonyOS/__OHOS__平台检测
- 0002-config.sub.patch - 添加linux-ohos三元组支持
- 0003-configure.patch - 修复HMDFS umask问题（077 → 022）

## 依赖版本

- xorgproto 2024.1
- libXfixes 6.0.2
- libXrender 0.9.12
- libXrandr 1.5.5

## 验证结果

```bash
$ pkg-config --modversion xpresent
1.0.2

$ ls -la ~/usr/local/lib/libXpresent*
libXpresent.a (69KB)
libXpresent.so -> libXpresent.so.1.0.0
libXpresent.so.1 -> libXpresent.so.1.0.0
libXpresent.so.1.0.0 (64KB)
```

## 预编译包

- libxpresent-1.0.2-ohos-aarch64.tar.gz (2.0MB)
- libxpresent-1.0.2-ohos-aarch64-debug.tar.gz (1.3MB)

---

**编译结束**: 2026-06-16T11:43:00
**最终状态**: built