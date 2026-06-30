# perl-crypt-openssl-dsa 0.20 适配笔记

## 编译环境
- 构建系统: ExtUtils::MakeMaker (Perl)
- 编译日期: 2026-05-22
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 设置环境变量:
   ```bash
   export PKG_CONFIG_PATH=~/usr/local/lib/pkgconfig:~/usr/local/libressl/lib/pkgconfig:$PKG_CONFIG_PATH
   export OPENSSL_PREFIX=~/usr/local
   ```

2. 生成 Makefile（使用完整路径，避免 ~ 符号问题）:
   ```bash
   perl Makefile.PL PREFIX=$HOME/usr/local INC="-I$HOME/usr/local/include" LIBS="-L$HOME/usr/local/lib -lcrypto"
   ```

3. 编译:
   ```bash
   make -j2
   ```

4. 安装到测试前缀:
   ```bash
   make install DESTDIR=$HOME/tmp/test-install-perl-crypt-openssl-dsa-0.20
   ```

5. 安装到本地前缀:
   ```bash
   make install
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Makefile.PL 生成的 Makefile 中 INC 使用 ~ 符号 | MakeMaker 不自动展开 ~ | 使用 $HOME 变量替代 ~ |
| 2 | 编译找不到 openssl/bn.h 头文件 | INC 参数中的 ~ 未展开 | 重新生成 Makefile 使用完整路径 |
| 3 | 测试失败：DSA.so Permission denied | 需要签名 ELF 文件 | 使用 binary-sign-tool 签名 |
| 4 | 用户验证失败：即使签名后仍 Permission denied | SELinux/平台限制（E046） | 记录为平台限制，不阻塞 |

## 源码修改

无补丁。编译成功，仅有类型转换警告（char* vs unsigned char*），不影响功能。

## 依赖版本

- Perl: 5.42.0
- OpenSSL: 3.5.6 (路径 ~/usr/local)
- 编译工具: clang, make

## 验证结果

编译成功，但用户验证受阻于平台限制：

```bash
# 编译产物检查
find ~/tmp/test-install-perl-crypt-openssl-dsa-0.20 -type f \( -name "*.pm" -o -name "*.so" \)
# 输出:
# DSA.pm
# DSA.so

# 签名检查
llvm-readelf -S DSA.so | grep codesign
# [36] .codesign         PROGBITS        ...

# 用户验证（失败，平台限制）
perl -e "use Crypt::OpenSSL::DSA; print 'OK\n';"
# Error: Permission denied (SELinux限制，E046)
```

## 交付物

无预编译包（因用户验证失败，暂不发布）

## 注意事项

1. **Makefile.PL 环境变量**: 必须使用 `$HOME` 而不是 `~`，否则路径不会被展开
2. **OpenSSL 头文件路径**: 需要通过 INC 参数明确指定
3. **ELF 签名**: 使用 `binary-sign-tool sign -inFile <file> -outFile <tmp> -selfSign 1`
4. **平台限制（E046）**: 用户安装目录下的 .so 文件即使签名也可能因 SELinux 无法加载，这是已知平台限制

---
**编译结束**: 2026-05-22 15:01
**最终状态**: built (编译成功，用户验证受平台限制)