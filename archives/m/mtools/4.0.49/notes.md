# mtools 4.0.49 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-26
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 下载源码: https://ftp.gnu.org/gnu/mtools/mtools-4.0.49.tar.gz
2. 修改 config.guess 识别 HarmonyOS 平台
3. 临时移除 GNU libiconv.h 头文件（避免 iconv 符号重映射）
4. configure --prefix=/storage/Users/currentUser/usr/local
5. make -j1
6. make install DESTDIR=$TEST_PREFIX
7. make install (本地安装)
8. package 打包

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | E007: config.guess 不识别 HarmonyOS uname 输出 | 添加 HarmonyOS 到 case $UNAME_SYSTEM 分支 + 添加 aarch64:HarmonyOS:*:* 模式映射到 linux-ohos |
| 2 | 链接失败: undefined libiconv_open/libiconv_close/libiconv | GNU iconv.h 头文件将 iconv_open 等宏重映射为 libiconv_open，但 libiconv.so 未签名无法加载 | 临时移除 GNU iconv.h，使用 musl 内置 iconv（标准 POSIX 函数） |

## 源码修改

- config.guess: 添加 HarmonyOS 平台识别支持（补丁 0001-config.guess.patch）
  - case $UNAME_SYSTEM 中加入 HarmonyOS
  - 添加 aarch64:HarmonyOS:*:* 和 *:HarmonyOS:*:* 模式

## 依赖版本

- musl libc (内置 iconv 支持)
- clang 15.0.4

## 验证结果

```bash
/storage/Users/currentUser/usr/local/bin/mtools --version
# 输出: mtools (GNU mtools) 4.0.49
# configured with the following options: disable-xdf disable-vold disable-new-vold disable-debug enable-raw-term
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| mtools-4.0.49-ohos-aarch64.tar.gz | 6114KB | 预编译包 |
| mtools-4.0.49-ohos-aarch64-debug.tar.gz | 1665KB | 调试符号包 |

## 注意事项

- GNU libiconv.h 头文件会重映射 iconv 函数为 libiconv_* 前缀，在 HarmonyOS 上由于 libiconv.so 未签名无法动态加载，应使用 musl 内置 iconv
- G0 干净构建验证需注意 configure 环境中的 iconv.h 版本问题
- mtools 无 make check 测试套件

---
**编译结束**: 2026-05-26 15:25
**最终状态**: built
---

**编译结束**: 2026-05-26 15:28
**最终状态**: published
