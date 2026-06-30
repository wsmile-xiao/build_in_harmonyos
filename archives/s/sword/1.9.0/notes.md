# sword 1.9.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-25
- 编译器: clang/clang++ 15.0.4
- 状态: published

## 编译步骤

1. `./configure --prefix=/storage/Users/currentUser/usr/local`
2. `make -j1`
3. `make install DESTDIR=$TEST_PREFIX` (staging)
4. `make check` (0 tests, cppunit not installed)
5. `make install` (to $DEFAULT_PREFIX, local verification)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | GNU config.guess (2018-08-29) 缺少 HarmonyOS 检测分支 (E007) | 手动修改 config.guess 添加 HarmonyOS 检测，修改 config.sub 添加 linux-ohos* 支持 |
| 2 | config.status 创建临时文件 Permission denied | HMDFS 文件系统 umask 077 + SGID 位导致目录不可写 | 修改 configure 和 config.status 中的 umask 077 → umask 022 |
| 3 | 链接器找不到 -lssl -lcrypto | OpenSSL 库仅有 .so.3 版本，缺少 .so 符号链接 | 创建 libssl.so → libssl.so.3 和 libcrypto.so → libcrypto.so.3 符号链接 |

## 源码修改

- **config.guess**: 添加 HarmonyOS 系统识别（输出 aarch64-unknown-linux-ohos）
- **config.sub**: 添加 linux-ohos* 到 OS 识别列表（2处）
- **configure**: umask 077 → umask 022（2处，修复 HMDFS 临时目录权限问题）

## 依赖版本

- curl/8.19.0 (已预装)
- zlib/1.3.1 (已预装)
- openssl/3.0 (系统自带 .so.3)

## 验证结果

```bash
$ diatheke --version
Diatheke command-line SWORD frontend Version 4.8 (SWORD: 1.9.0)

$ installmgr --version
(SWORD: 1.9.0)

$ osis2mod --version
You are running osis2mod: $Rev: 3769 $ (SWORD: 1.9.0)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| sword-1.9.0-ohos-aarch64.tar.gz | 16848KB | 预编译包（含 ELF 签名、RPATH、strip） |

## 注意事项

- config.guess 补丁脚本 patch-autotools-ohos.pl 对旧版 (2018-08-29) 不完全兼容：使用 GUESS 变量但旧版需要 echo/exit
- HMDFS 的 umask 077 会导致 config.status 临时目录不可写，需修改为 umask 022
- sword 的测试套件需要 cppunit，当前环境未安装，make check 结果为 0 tests
---

**编译结束**: 2026-06-25 12:40
**最终状态**: published
