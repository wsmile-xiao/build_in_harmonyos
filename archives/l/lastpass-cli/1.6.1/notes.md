# lastpass-cli 1.6.1 适配笔记

## 编译环境
- 构建系统: custom (CMake项目，但CMake在OpenHarmony平台无法正常configure)
- 编译日期: 2026-06-03
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. **源码下载**: 从 GitHub 获取 v1.6.1 tarball
   - URL: https://github.com/lastpass/lastpass-cli/archive/refs/tags/v1.6.1.tar.gz

2. **版本生成**: 运行 `sh ./LASTPASS-VERSION-GEN` 生成 version.h
   - 输出: `#define LASTPASS_CLI_VERSION "1.6.1.GIT"`

3. **CMake尝试失败**: 
   - CMake 4.1.2 在 OpenHarmony 平台检测失败（"System is unknown to cmake"）
   - LLD链接器依赖 libxml2.so.16，添加 harmonybrew/lib 到 LD_LIBRARY_PATH 后LLD无法运行
   - CMake test compiler check 失败

4. **手动编译方案**:
   - 编译: `clang -std=gnu99 -pedantic -Wall -Wextra -Wno-language-extension-token -D_GNU_SOURCE -fPIC -O2 -I. -I/storage/Users/currentUser/usr/local/include/libxml2 -c *.c`
   - 链接: `clang -fPIC -O2 -L/storage/Users/currentUser/usr/local/lib *.o -o lpass -lxml2 -lssl -lcrypto -lcurl`
   - 注意: 不能将 ~/.harmonybrew/lib 加入 LD_LIBRARY_PATH，会导致 LLD 链接器找不到 libxml2.so.16

5. **DESTDIR 安装**:
   - `mkdir -p $TEST_PREFIX/$DEFAULT_PREFIX/bin`
   - `cp lpass $TEST_PREFIX/$DEFAULT_PREFIX/bin/lpass`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 无法检测 C compiler | CMake 不识别 OpenHarmony 平台，LLD链接器依赖libxml2.so.16在特定LD_LIBRARY_PATH下无法运行 | 改用手动编译方式，绕过CMake |
| 2 | LLD链接器运行失败 | 将 ~/.harmonybrew/lib 加入 LD_LIBRARY_PATH 会干扰LLD链接器 | 使用默认LD_LIBRARY_PATH编译/链接，仅在使用Python时添加harmonybrew/lib |
| 3 | CMakeLists.txt版本兼容性警告 | cmake_minimum_required(VERSION 2.8) 与 CMake 4.1.2 不兼容 | 改用手动编译，无需处理CMake兼容性 |

## 源码修改

无源码修改。lastpass-cli 在 OpenHarmony 上可以直接编译，仅需手动编译而非使用CMake。

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| libxml2 | 2.11.9 | cmd-pkgs预编译包 |
| openssl | 1.1.1w | cmd-pkgs预编译包 |
| libcurl | 8.8.0 | cmd-pkgs预编译包 |

## 验证结果

```bash
$ ./lpass --version
LastPass CLI v1.6.1.GIT
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| lpass | 191040 | LastPass CLI 可执行文件 |

## 注意事项

1. lastpass-cli 是 CMake 项目但在 OpenHarmony 上 CMake configure 失败，需手动编译
2. 编译/链接时不能将 ~/.harmonybrew/lib 加入 LD_LIBRARY_PATH（会破坏 LLD 链接器）
3. 版本号显示为 "1.6.1.GIT" 而非 "1.6.1"，因为 LASTPASS-VERSION-GEN 在非git仓库中回退到 DEF_VER=v1.6.1.GIT
---

**编译结束**: 2026-08-10 02:59
**最终状态**: built
