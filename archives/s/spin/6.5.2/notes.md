# spin 6.5.2 适配笔记

## 编译环境
- 构建系统: makefile（自定义 Makefile，无 configure 脚本）
- 编译日期: 2026-06-08
- 编译器: clang 15.0.4 (OHOS SDK)
- 状态: built

## 编译步骤

spin 使用自定义 Makefile，无 configure 脚本。编译命令如下：

```bash
cd $BUILD_SRC_DIR/Src

# 编译
make CC=clang CFLAGS="-fPIC -O2 -DNXT -Wall -pedantic" YACC="bison -y" LDFLAGS="-fuse-ld=bfd"

# Staging 安装（DESTDIR 在 spin 中实为 PREFIX）
make install DESTDIR=$STAGING_PREFIX INSTALL="install -D"

# 真实安装
make install DESTDIR=$DEFAULT_PREFIX INSTALL="install -D"
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `y?tab.c` 编译失败 | bison 默认生成 `spin.tab.c` 而非 `y.tab.c`，Makefile 的 `y?tab.c` 通配模式不匹配 | 使用 `YACC="bison -y"` 强制 bison 以 yacc 传统模式输出 `y.tab.c` |
| 2 | 链接阶段 lld 报 libxml2.so.16 加载错误 | OHOS SDK 的 lld 依赖 libxml2.so.16 但加载路径不正确 | 使用 `LDFLAGS="-fuse-ld=bfd"` 切换到 ld.bfd 链接器 |
| 3 | spin 二进制首次执行 Permission denied | OHOS ELF 签名安全机制 | 使用 `ohc-run.py sign-elf` 签名后可正常执行 |
| 4 | G0 clean-verify make install 失败 | spin Makefile install 目标不创建目标目录（bin/） | 在 required_env 中设置 `INSTALL="install -D"` 使 GNU install 自动创建父目录 |

## 源码修改

无源码修改。所有适配通过 make 参数传递完成。

## 依赖版本

- bison 3.8.2（提供 yacc 功能）
- clang 15.0.4 (OHOS SDK)
- GNU install (coreutils 9.10, 支持 -D 选项)

## 验证结果

```bash
$ spin -V
Spin Version 6.5.2 -- 6 December 2019

$ file /storage/Users/currentUser/usr/local/bin/spin
ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1)

$ readelf -d spin | grep NEEDED
  NEEDED  libc.so
```

spin 无 make check 目标。使用功能验证替代：
- 版本号确认正确 ✅
- spin -a 模型生成正常 ✅（需 -Pclang 包装脚本）
- spin 语法检查正常 ✅
- spin -run/-search ⚠️ 需 gcc 预处理器（已知平台限制）

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| spin-6.5.2-ohos-aarch64.tar.gz | 1.2M | 预编译包（含 bin/spin + share/man/man1/spin.1） |
| spin-6.5.2-ohos-aarch64-debug.tar.gz | 58K | 调试符号（spin.debug） |

## 注意事项

1. spin Makefile 中 DESTDIR 变量实际为安装 PREFIX（与 autotools DESTDIR 含义不同），需特别注意 R20 DESTDIR 模式适配
2. spin 默认使用 gcc 作为 C 预处理器，OHOS 平台需使用 `-P<clang-wrapper>` 或安装 gcc
3. bison 必须使用 `-y` 选项以生成兼容的 `y.tab.c` 文件名格式
4. 安装时需 `INSTALL="install -D"` 使 GNU install 自动创建目标目录
5. 二进制需 ELF 签名才能在 HarmonyOS 上执行（sign-elf）---

**编译结束**: 2026-06-08 18:02
**最终状态**: built
---

**编译结束**: 2026-06-08 18:06
**最终状态**: built
