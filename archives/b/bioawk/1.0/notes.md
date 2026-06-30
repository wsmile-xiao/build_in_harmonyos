# bioawk 1.0 适配笔记

## 编译环境
- 构建系统: makefile（纯Makefile，BWK awk fork）
- 编译日期: 2026-06-18
- 编译器: clang 15.0.4
- 状态: published

## 编译步骤

1. 下载源码：使用 codeload.github.com 直链（github.com HTTPS 超时）
2. 解压到 work 目录
3. 直接 make（无 configure 脚本）：
   ```bash
   make CC=clang CFLAGS="-fPIC -O2 -Wall" YACC="bison -y" YFLAGS="-d"
   ```
4. 手动安装（无 install target）：
   ```bash
   cp bioawk $DEFAULT_PREFIX/bin/bioawk
   cp awk.1 $DEFAULT_PREFIX/share/man/man1/bioawk.1
   ```
5. Staging 安装同样手动复制到 $TEST_PREFIX/$DEFAULT_PREFIX/

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub HTTPS 下载超时 | github.com 到 codeload.github.com 重定向超时 | 使用 codeload.github.com 直链 + SSL_CERT_FILE 环境变量 |
| 2 | SSL CERTIFICATE_VERIFY_FAILED | 鸿蒙 OpenSSL 未配置 CA 证书 | 设置 SSL_CERT_FILE=$HOME/usr/local/ssl/cert.pem |
| 3 | G0 clean-verify 失败 (configure exit 127) | bioawk 无 configure 脚本，G0 假设有 configure | 纯Makefile项目 G0 不适用，手动验证已通过 |
| 4 | verify-build G4 缺少 build_system 字段 | manifest 模板使用 system 而非 build_system | 添加顶层 build_system: makefile 字段 |

## 源码修改

无源码修改（make CC=clang 直接编译通过）

## 依赖版本

- bison/yacc: /data/service/hnp/bin/bison（已预装）
- zlib: $HOME/usr/local/lib/libz.a（已预装）
- clang: 15.0.4
- make: GNU Make 4.4.1

## 验证结果

```bash
$ bioawk --version
awk version 20110810

$ echo -e "1 2 3\n4 5 6" | bioawk '{print $1+$2+$3}'
6
15

$ printf '>seq1\nACGTACGT\n>seq2\nTTTTGGGG\n' | bioawk -c fastx '{print $name, length($seq)}'
seq1	8
seq2	8
```

**编译结束**: 2026-06-22 16:30
**最终状态**: published
