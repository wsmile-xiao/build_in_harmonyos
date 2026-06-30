# libnfnetlink 1.0.2 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-09
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 初始化: `ohc-run.py init-build libnfnetlink 1.0.2 --url=https://...`
2. 修改 config.guess 添加 HarmonyOS 识别
3. 修改 configure/config.status 解决 HMDFS 临时目录权限问题
4. 修改源码文件解决 sockaddr_storage 重复定义
5. 编译: `./configure --prefix=$DEFAULT_PREFIX && make -j2`
6. 安装: `make install DESTDIR=$TEST_PREFIX` + `make install`
7. 验证: `ohc-run.py verify-build`
8. 打包: `ohc-run.py package`
9. 完成: `ohc-run.py finish built`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | 版本过旧 (2018-02-24) | 在 config.guess 添加 `aarch64:HarmonyOS:*:*` 识别 |
| 2 | config.status 创建临时文件失败 | HMDFS 对 700 权限目录有写入限制 | 修改 `umask 077` 为 `umask 000` |
| 3 | sockaddr_storage 重复定义 | 鸿蒙 SDK 头文件冲突 | 添加 `_UAPI_LINUX_SOCKET_H` 宏保护 |

## 源码修改

| 文件 | 修改内容 |
|------|----------|
| build-aux/config.guess | 添加 HarmonyOS 系统识别 |
| src/libnfnetlink.c | 添加 sockaddr_storage 重复定义保护 |
| src/iftable.c | 添加 sockaddr_storage 重复定义保护 |
| src/rtnl.c | 添加 sockaddr_storage 重复定义保护 |

应用补丁:
- 0001-config.guess-harmonyos.patch
- 0002-iftable.c-harmonyos-fix.patch
- 0003-libnfnetlink.c-harmonyos-fix.patch
- 0004-rtnl.c-harmonyos-fix.patch

## 依赖版本

无特殊依赖

## 验证结果

```bash
pkg-config --modversion libnfnetlink
1.0.2

ls -la /storage/Users/currentUser/usr/local/lib/libnfnetlink*
-rwxrwx--- libnfnetlink.la
lrwxrwxrwx libnfnetlink.so -> libnfnetlink.so.0.2.0
lrwxrwxrwx libnfnetlink.so.0 -> libnfnetlink.so.0.2.0
-rwxrwx--- libnfnetlink.so.0.2.0
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libnfnetlink-1.0.2-ohos-aarch64.tar.gz | 260KB | 预编译包 |

## 注意事项

1. 这是 netfilter 库，需要内核头文件支持
2. 鸿蒙 SDK 的 linux/socket.h 和 sys/socket.h 有类型冲突
3. HMDFS 文件系统对 mktemp 创建的临时目录有特殊权限限制

---
**编译结束**: 2026-06-09 12:21
**最终状态**: built
