# cups 2.4.7 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-04
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 状态: built

## 编译步骤

1. init-build: `python3 ohc-run.py init-build cups 2.4.7`
2. 修复config.guess: 在 `Linux|GNU|GNU/*)` 分支中添加 `HarmonyOS`，添加 `aarch64:HarmonyOS:*:*)` case输出 `aarch64-unknown-linux-ohos`
3. 修复config.sub (E072): 3处修改 - ohos-linux映射、ohos* OS白名单、linux-ohos* kernel-os白名单
4. configure: `CC=$TMPDIR/cc-wrapper.sh ./configure --prefix=$DEFAULT_PREFIX` (CC wrapper adds `-fuse-ld=bfd` for linking and auto-signs binaries)
5. 修复config.h: `#ifdef __OHOS__` guard to `#undef HAVE_SHADOW_H` (musl has shadow.h but getspnam/endspent not implemented)
6. 修复Makedefs: 移除 `INSTALL_BIN` 和 `INSTALL_LIB` 的 `-s` strip标志 (防止strip破坏ELF签名)
7. 修复cups/thread.c: `#ifdef __OHOS__` guard to use `pthread_detach` instead of `pthread_cancel` (musl不支持pthread_cancel)
8. `make -j1` 编译成功
9. `make install DESTDIR=$TEST_PREFIX` staging安装成功
10. 批量签名staging目录61个ELF文件

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess无法识别HarmonyOS | uname -s返回"HarmonyOS"，不在Linux|GNU|GNU/*分支 | 在分支中添加HarmonyOS，添加aarch64:HarmonyOS:*:*) case (E007) |
| 2 | config.sub验证ohos三元组失败 | config.sub未识别ohos作为合法OS | 3处修改：ohos-linux映射、ohos* OS白名单、linux-ohos* kernel-os白名单 (E072) |
| 3 | configure测试二进制无法执行 | HMDFS禁止未签名二进制执行 | 创建CC wrapper，编译后自动调用binary-sign-tool -selfSign 1签名 |
| 4 | HAVE_SHADOW_H=1导致编译错误 | musl有shadow.h但getspnam/endspent未实现 | config.h中加#ifdef __OHOS__ guard undef HAVE_SHADOW_H |
| 5 | INSTALL_BIN -s标志strip二进制 | -s标志strip会破坏ELF签名 | 移除Makedefs中INSTALL_BIN和INSTALL_LIB的-s标志 |
| 6 | pthread_cancel不可用 | musl不支持pthread_cancel | cups/thread.c中用#ifdef __OHOS__ guard替换为pthread_detach |
| 7 | lld链接器问题 | clang默认使用ld.lld，某些链接场景失败 | CC wrapper添加-fuse-ld=bfd使用GNU ld |

## 源码修改

| 文件 | 修改内容 |
|------|----------|
| config.guess | 添加HarmonyOS到LIBC检测分支，添加aarch64:HarmonyOS:*:*) case |
| config.sub | E072 3处修改：ohos-linux映射、ohos* OS白名单、linux-ohos* kernel-os白名单 |
| config.h | #ifdef __OHOS__ guard to #undef HAVE_SHADOW_H |
| Makedefs | 移除INSTALL_BIN和INSTALL_LIB的-s标志 |
| cups/thread.c | #ifdef __OHOS__ guard: pthread_cancel→pthread_detach |

## 依赖版本

- openssl 1.1.1w
- zlib 1.3.1
- libiconv 1.17
- libusb 1.0.26
- dbus 1.14.10

## 验证结果

```bash
# 61 ELF binaries signed and staged successfully
# Key binaries: cups-config, ipptool, ippeveprinter, lpq, lpr, lprm, ppdc, ppdhtml, ppdi, ppdmerge
# Key sbin: cupsd, cupsfilter, cupsaccept, cupsctl, lpc
# Key libraries: libcups.so.2, libcupsimage.so.2
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libcups.so.2 | ~760KB | CUPS核心库 |
| libcupsimage.so.2 | ~180KB | CUPS图像处理库 |
| cupsd | ~2MB | CUPS打印调度器 |

## 注意事项

- HMDFS禁止未签名二进制执行，所有编译产物需binary-sign-tool签名
- CC wrapper脚本需在configure和make时使用，自动添加-fuse-ld=bfd和签名
- musl不支持pthread_cancel和getspnam/endspent，需__OHOS__守卫
---

**编译结束**: 2026-06-04 01:00
**最终状态**: built
