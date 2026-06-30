# rsyslog 8.2404.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-28
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 初始化：下载源码并解压到 ~/builds/rsyslog-8.2404.0.work
2. 修改configure脚本：修复HMDFS临时目录权限问题（E011）
3. 运行configure：`./configure --prefix=$DEFAULT_PREFIX`
4. 修改源码：修复pthread_cancel函数缺失问题
5. 编译：`make -j1` 成功完成

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.status无法创建临时目录./confXXXXXX | HMDFS权限问题，umask 077创建的目录不可写 | E011方案：修改configure和config.status，使用$TMPDIR/build-tmp绝对路径 |
| 2 | dnscache.c缺少pthread_setcancelstate函数 | 鸟蒙系统缺少pthread_cancel系列函数 | 添加pthread.h头文件，使用HAVE_PTHREAD_CANCEL条件编译 |
| 3 | queue.c/wti.c/threads.c缺少pthread_cancel函数 | 同上 | 批量添加HAVE_PTHREAD_CANCEL条件编译 |
| 4 | net.c及其他plugins缺少pthread_cancel函数 | 同上 | 批量添加HAVE_PTHREAD_CANCEL条件编译 |

## 源码修改

修改了以下文件：
- configure: 临时目录路径修复
- runtime/dnscache.c: 添加pthread.h，条件编译
- runtime/queue.c: 条件编译
- runtime/wti.c: 条件编译
- threads.c: 条件编译
- runtime/net.c: 条件编译
- plugins/imdiag/imdiag.c: 条件编译
- plugins/imfile/imfile.c: 条件编译
- plugins/omprog/omprog.c: 条件编译

## 依赖版本

- libestr: 已安装（系统预编译包）
- libfastjson: 已安装（系统预编译包）
- libgcrypt: 1.11.0
- libuuid: 已安装

## 验证结果

```bash
make编译成功完成
生成rsyslogd可执行文件
所有模块编译通过
```

## 交付物

- 6个源码补丁文件
- manifest.yaml状态为built
- 编译产物：rsyslogd及相关模块

## 注意事项

- 鸿蒙系统缺少pthread_cancel函数，这是平台限制
- HMDFS文件系统对临时目录权限有特殊要求，必须使用$TMPDIR
- 所有补丁都使用HAVE_PTHREAD_CANCEL条件编译，不影响其他平台