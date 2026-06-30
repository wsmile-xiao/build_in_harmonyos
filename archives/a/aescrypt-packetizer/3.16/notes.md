# aescrypt-packetizer 3.16 适配笔记

## 编译环境

- 构建系统: plain Makefile (非 autotools/cmake，Makefile 内手动管理编译规则)
- 编译日期: 2026-06-29
- 编译器: clang/clang++
- 目标平台: HarmonyOS aarch64 (ohos-aarch64 profile)
- 状态: published

## 编译步骤

```bash
# 源码为 plain Makefile 项目，无 configure 步骤
cd src/
make CC=clang \
     CFLAGS="-fPIC -O2 -Wall -Wextra -pedantic -std=c11 -D_FILE_OFFSET_BITS=64" \
     LDLIBS= \
     LDFLAGS=-static
```

关键参数说明：
- `CC=clang`：覆盖 Makefile 默认的 `gcc`
- `LDLIBS=`：清空链接库。HarmonyOS `uname -s` 返回 "HarmonyOS" 而非 "Linux"，Makefile 会错误地添加 `-liconv`，实际上 HarmonyOS 不需要 iconv
- `LDFLAGS=-static`：R26 要求终端工具静态链接
- `CFLAGS` 中 `-fPIC` 用于位置无关代码，`-D_FILE_OFFSET_BITS=64` 支持大文件

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Makefile 检测 `uname -s` 非 Linux 时添加 `-liconv` | HarmonyOS 的 `uname -s` 返回 "HarmonyOS"，不匹配 Makefile 中的 `ifeq ($(shell uname -s), Linux)` 条件 | 在 make 命令行显式覆盖 `LDLIBS=` 为空 |
| 2 | Makefile 默认使用 `gcc` | 上游 Makefile 硬编码 `CC=gcc` | 命令行覆盖 `CC=clang` |
| 3 | install 目标使用硬编码路径 | Makefile 的 install/uninstall 目标写入 `/usr/bin` 和 `/usr/share/man/man1`，不支持 DESTDIR | conanfile.py 中使用 `copy()` 手动安装产物 |

## 源码修改

无补丁。源码未修改，所有适配通过命令行参数覆盖完成。

## 依赖版本

无外部依赖。AES Crypt 是自包含的命令行工具，所有加密算法（AES-256、SHA-256）均在源码内实现。

## 验证结果

```bash
# make test 全部通过
$ make test CC=clang CFLAGS="..." LDLIBS= LDFLAGS=-static
# SHA-256 Validation Tests: 3/3 passed
# Rijndael Monte Carlo Test: 6/6 passed (128/192/256-bit, enc+dec)
# 文件加密/解密测试: 3/3 passed (空文件/短文件/长文件)
# 密码长度边界测试: 4/4 passed (0/1023/1024/1025)
# All file encryption tests passed

# conan-verify 8 道门禁全部通过
$ python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify aescrypt-packetizer 3.16
# G0-G4 + L2/L4/L5: ALL PASS
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/aescrypt | 1,148,864 bytes | AES-256 文件加密/解密工具 (静态链接) |
| bin/aescrypt_keygen | 1,120,192 bytes | 密钥文件生成工具 (静态链接) |
| share/man/man1/aescrypt.1 | 2,731 bytes | aescrypt man page |
| share/man/man1/aescrypt_keygen.1 | 1,967 bytes | aescrypt_keygen man page |

## 注意事项

1. **LDLIBS 覆盖**：HarmonyOS 平台编译时必须设置 `LDLIBS=` 为空，否则 Makefile 会尝试链接不存在的 `-liconv`
2. **静态链接**：R26 要求终端工具静态链接，使用 `LDFLAGS=-static`
3. **手动安装**：Makefile 不支持 DESTDIR，conanfile.py 使用 `copy()` 函数手动安装产物
4. **PIE disabled**：上游 Makefile 未启用 PIE (`-fPIE -pie`)，二进制为 EXEC 类型而非 DYN。这是上游设计，不影响功能
---

**编译结束**: 2026-06-30 15:51
**最终状态**: published
