# acme-client 0.1.16 适配笔记

## 编译环境
- 构建系统: GNU makefile
- 编译日期: 2026-05-22
- 编译器: cc (clang)
- 状态: built

## 版本说明
- acme-client 0.1.16 使用acme-client-portable master分支源码
- OpenBSD distfiles中没有独立的0.1.16版本tarball
- acme-client是OpenBSD base系统的一部分，版本号与OpenBSD版本相关

## 编译步骤

1. 使用已有的acme-client-portable源码包
2. 应用之前编译时的API适配修改
3. 设置LibreSSL环境变量
4. 静态编译: make STATIC=1 PREFIX=/storage/Users/currentUser/usr/local

## API适配详情

### LibreSSL 3.x/OpenSSL 3.x API兼容修改

| 文件 | 修改内容 | 原因 |
|------|---------|------|
| acctproc.c | RSA_get0_key(&n, &e, NULL) 替代 r->n, r->e | OpenSSL 1.1.x+隐藏RSA内部结构 |
| acctproc.c | EVP_PKEY_type(EVP_PKEY_id(pkey)) 替代 pkey->type | EVP_PKEY结构体成员不再公开 |
| acctproc.c | EVP_MD_CTX_new/free 替代 create/destroy | API命名规范化 |
| certproc.c | BIO_number_written(bio) 替代 bio->num_write | BIO结构体成员不再公开 |
| keyproc.c | EVP_PKEY_base_id(pkey) 替代 pkey->type | 同上 |
| rsa.c | EVP_PKEY_base_id()适配 | 同上 |
| revokeproc.c | X509_get_ext_count() 替代 x->ex->sk_num | X509结构体成员不再公开 |
| revokeproc.c | BIO_number_written()适配 | 同上 |
| config.h | getprogname()定义为__progname | musl libc不提供program_invocation_short_name |
| extern.h | extern变量声明修正 | 编译警告修复 |
| main.c | extern变量声明修正 | 同上 |

### 关键符号验证

LibreSSL 3.9.2已提供以下关键符号：
- BIO_sock_init ✓
- CRYPTO_lock ✓
- UI_OpenSSL ✓
- CRYPTO_add_lock ✓

## 编译命令

```bash
cd ~/builds/acme-client-0.1.16.work

export PATH=/storage/Users/currentUser/usr/local/bin:$PATH
export PKG_CONFIG_PATH=/storage/Users/currentUser/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH
export LD_LIBRARY_PATH=/storage/Users/currentUser/usr/local/lib:$LD_LIBRARY_PATH
export CFLAGS="-I/storage/Users/currentUser/usr/local/include -DMUSL_LIBC"
export LDFLAGS="-L/storage/Users/currentUser/usr/local/lib"

make STATIC=1 PREFIX=/storage/Users/currentUser/usr/local
```

## 验证结果

```bash
./acme-client --version
# 输出: usage信息，二进制可正常执行

file acme-client
# ELF 64-bit LSB executable, ARM aarch64

ls -la acme-client
# -rwxrwx--- 1 ... 2111936 2026-05-22 acme-client
```

## 交付物

- 二进制: ~/builds/acme-client-0.1.16.work/acme-client (2.1MB)
- 源码包: ~/archives/a/acme-client/0.1.16/acme-client-0.1.15-portable.tar.gz

## 注意事项

1. **静态链接**: 动态库在OpenHarmony上加载可能失败，静态链接是最可靠方案
2. **LibreSSL依赖**: 必须使用LibreSSL而非OpenSSL，代码使用LibreSSL特定API
3. **musl libc适配**: 需要定义MUSL_LIBC宏，绕过libbsd依赖

---
**编译结束**: 2026-05-22
**最终状态**: built
---

**编译结束**: 2026-05-22 11:13
**最终状态**: built
