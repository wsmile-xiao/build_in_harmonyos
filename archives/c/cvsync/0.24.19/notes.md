# cvsync 0.24.19 适配笔记

## 编译环境
- 构建系统: BSD Makefile (无 configure)
- 编译日期: 2026-06-12
- 编译器: clang 15.0.4
- 状态: built

## 编译步骤

```bash
# 加载上下文
source .build-context-cvsync-0.24.19
cd $BUILD_SRC_DIR

# 编译（使用 OpenSSL hash）
make HASH_TYPE=openssl HASH_PREFIX=$DEFAULT_PREFIX PREFIX=$DEFAULT_PREFIX PTHREAD_PREFIX=$DEFAULT_PREFIX

# 手动安装（因为 install 命令不存在）
mkdir -p $TEST_PREFIX/$DEFAULT_PREFIX/bin
for dir in cvscan cvsup2cvsync cvsync cvsync2cvsup cvsyncd rcscan rcscmp; do
  llvm-strip "$dir/$dir"
  cp "$dir/$dir" $TEST_PREFIX/$DEFAULT_PREFIX/bin/
done

# 创建预编译包
cd $TEST_PREFIX
tar -czf $BUILD_ARCHIVE_DIR/packaging/cvsync-0.24.19-ohos-aarch64.tar.gz .
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | hash_native.c 编译错误：找不到 MD5_CTX 等类型 | 鸿蒙系统没有原生 MD5/SHA 实现 | 使用 HASH_TYPE=openssl，依赖已安装的 OpenSSL |
| 2 | rcscan/main.c: struct stat 未定义 | 缺少 `<sys/stat.h>` 头文件 | 创建补丁 0001-rcscan-main.c.patch，添加 #ifdef __OHOS__ 守卫 |
| 3 | rcscmp/main.c: struct stat 未定义 | 缺少 `<sys/stat.h>` 头文件 | 创建补丁 0002-rcscmp-main.c.patch，添加 #ifdef __OHOS__ 守卫 |
| 4 | install 命令不存在 | 鸿蒙系统缺少 GNU install | 手动复制文件到 staging 目录 |

## 源码修改

- 0001-rcscan-main.c.patch: 在 rcscan/main.c 中添加 `#include <sys/stat.h>`（带 __OHOS__ 守卫）
- 0002-rcscmp-main.c.patch: 在 rcscmp/main.c 中添加 `#include <sys/stat.h>`（带 __OHOS__ 守卫）

## 依赖版本

- OpenSSL: libcrypto (已安装在 ~/usr/local)
- zlib: 动态链接 (系统提供)

## 验证结果

```bash
# 编译成功，生成以下二进制文件
$ ls -lh $TEST_PREFIX/$DEFAULT_PREFIX/bin/
cvscan        66K  ELF shared object, 64-bit LSB arm64, stripped
cvsup2cvsync  53K  ELF shared object, 64-bit LSB arm64, stripped
cvsync       278K  ELF shared object, 64-bit LSB arm64, stripped
cvsync2cvsup  47K  ELF shared object, 64-bit LSB arm64, stripped
cvsyncd      285K  ELF shared object, 64-bit LSB arm64, stripped
rcscan        37K  ELF shared object, 64-bit LSB arm64, stripped
rcscmp        38K  ELF shared object, 64-bit LSB arm64, stripped

# 注意：由于缺少 ELF 签名，二进制文件无法直接执行
# 需要使用 /data/service/hnp/bin/hnp_sign 进行签名
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| cvsync-0.24.19-ohos-aarch64.tar.gz | 833K | 预编译包（包含 7 个二进制文件） |

## 注意事项

1. cvsync 使用 BSD Makefile 构建系统，没有 configure 步骤
2. 必须指定 HASH_TYPE=openssl 或 libgcrypt，不能使用 native
3. 需要手动安装文件，因为鸿蒙系统缺少 GNU install 命令
4. 二进制文件需要 ELF 签名才能在鸿蒙系统上执行

---

**编译结束**: 2026-06-12 14:46
**最终状态**: built