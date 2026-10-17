# jitterentropy-library 3.6.3 编译记录

## 编译信息
- **日期**: 2026-05-29
- **版本**: 3.6.3
- **编译器**: clang
- **构建系统**: makefile
- **耗时**: 约 2 分钟

## 编译环境
- 平台: OpenHarmony (OHOS)
- 编译器: clang (系统默认)
- 工作目录: ~/tmp/jitterentropy-library-3.6.3.work
- 安装前缀: /storage/Users/currentUser/usr/local
- DESTDIR: ~/tmp/test-install-jitterentropy-library-3.6.3

## 编译步骤

### 1. 下载源码
```bash
cd ~/tmp
curl -k -L https://github.com/smuellerDD/jitterentropy-library/archive/refs/tags/v3.6.3.tar.gz -o jitterentropy-library-3.6.3.tar.gz
```

**问题**: SSL 证书验证失败
**解决**: 使用 `curl -k` 跳过证书验证

### 2. 解压源码
```bash
mkdir -p jitterentropy-library-3.6.3.work
tar -xzf jitterentropy-library-3.6.3.tar.gz --exclude='tests/raw-entropy/recording_userspace' -C jitterentropy-library-3.6.3.work --strip-components=1
```

**注意**: 源码包包含符号链接循环目录 `tests/raw-entropy/recording_userspace`，必须排除

### 3. 编译
```bash
cd ~/tmp/jitterentropy-library-3.6.3.work
make CC=clang PREFIX=/storage/Users/currentUser/usr/local
```

**输出**:
- 编译警告: `egrep: warning: egrep is obsolescent; using grep -E` (非致命)
- 成功生成:
  - libjitterentropy.so.3.6.3 (46K)
  - libjitterentropy.a (43K)

### 4. 手动安装
由于系统没有 `install` 命令，手动创建目录并复制文件：

```bash
DESTDIR=~/tmp/test-install-jitterentropy-library-3.6.3
PREFIX=/storage/Users/currentUser/usr/local

# 创建目录结构
mkdir -p "$DESTDIR/$PREFIX/lib" "$DESTDIR/$PREFIX/include"

# 复制文件
cp libjitterentropy.so.3.6.3 "$DESTDIR/$PREFIX/lib/"
cp libjitterentropy.a "$DESTDIR/$PREFIX/lib/"
cp jitterentropy.h "$DESTDIR/$PREFIX/include/"
cp jitterentropy-base-user.h "$DESTDIR/$PREFIX/include/"

# 创建符号链接
cd "$DESTDIR/$PREFIX/lib"
ln -sf libjitterentropy.so.3.6.3 libjitterentropy.so.3
ln -sf libjitterentropy.so.3 libjitterentropy.so
```

### 5. 功能测试
创建测试程序验证库功能：

```c
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "jitterentropy.h"

int main() {
    int ret;
    struct rand_data *ec = NULL;
    unsigned char buffer[32];

    ret = jent_entropy_init();
    if (ret != 0) {
        fprintf(stderr, "ERROR: jent_entropy_init() failed with code %d\n", ret);
        return 1;
    }

    ec = jent_entropy_collector_alloc(0, 0);
    if (!ec) {
        fprintf(stderr, "ERROR: jent_entropy_collector_alloc() failed\n");
        return 1;
    }

    ret = jent_read_entropy(ec, (char *)buffer, sizeof(buffer));
    if (ret != sizeof(buffer)) {
        fprintf(stderr, "ERROR: jent_read_entropy() returned %d\n", ret);
        jent_entropy_collector_free(ec);
        return 1;
    }

    jent_entropy_collector_free(ec);
    printf("All tests passed!\n");
    return 0;
}
```

编译并运行：
```bash
clang -o test_jitterentropy test_jitterentropy.c \
  -I test-install-jitterentropy-library-3.6.3/storage/Users/currentUser/usr/local/include \
  -L test-install-jitterentropy-library-3.6.3/storage/Users/currentUser/usr/local/lib \
  -ljitterentropy -lpthread

LD_LIBRARY_PATH=test-install-jitterentropy-library-3.6.3/storage/Users/currentUser/usr/local/lib \
  ./test_jitterentropy
```

**测试结果**: 全部通过 ✅

### 6. Strip 和签名
```bash
# Strip 共享库
llvm-strip libjitterentropy.so.3.6.3
# 大小从 46K 减小到 26K

# ELF 签名
python3 $SKILL_ROOT/scripts/ohc-run.py sign-elf libjitterentropy.so.3.6.3
```

### 7. 打包
```bash
cd ~/tmp/test-install-jitterentropy-library-3.6.3/storage/Users/currentUser/usr/local
tar czf jitterentropy-library-3.6.3-ohos-aarch64.tar.gz lib include
```

**打包内容**:
```
lib/
lib/libjitterentropy.so.3.6.3
lib/libjitterentropy.a
lib/libjitterentropy.so.3 -> libjitterentropy.so.3.6.3
lib/libjitterentropy.so -> libjitterentropy.so.3
include/
include/jitterentropy.h
include/jitterentropy-base-user.h
```

## 问题解决记录

### 问题 1: SSL 证书验证失败
- **现象**: wget/curl 从 GitHub 下载时报错 `SSL: CERTIFICATE_VERIFY_FAILED`
- **原因**: 系统证书库可能不完整
- **解决**: 使用 `curl -k` 跳过证书验证

### 问题 2: 符号链接循环
- **现象**: 解压时遇到符号链接循环错误
- **原因**: tests/raw-entropy/recording_userspace 是符号链接循环
- **解决**: 使用 `--exclude='tests/raw-entropy/recording_userspace'` 排除该目录

### 问题 3: install 命令不可用
- **现象**: Makefile 的 install 目标需要 install 命令
- **原因**: OHOS 系统未提供 GNU coreutils 的 install 命令
- **解决**: 手动创建目录并使用 cp 和 ln -sf 复制文件

## 与 3.4.0 版本的差异
- 版本号从 3.4.0 升级到 3.6.3
- 编译过程完全一致，无 API 变化
- 安装方法相同（手动安装）
- 质量门禁全部通过

## 质量门禁结果
- **G0 干净构建**: ✅ 通过
- **G1 二进制完整性**: ✅ 通过（共享库+静态库+头文件+符号链接）
- **G2 功能可用性**: ✅ 通过（API 测试全部通过）
- **G3 可移植性**: ✅ 通过（ELF 已签名，可执行）
- **G4 档案完整性**: ✅ 通过（所有必需文件存在）

## 编译总结
编译过程顺利，所有质量门禁通过。关键点：
1. 必须设置 `CC=clang`
2. 必须排除符号链接循环目录
3. 必须手动安装（无 install 命令）
4. 必须手动 strip 和 ELF 签名
5. API 简单易用，测试通过
---

**编译结束**: 2026-07-15 17:56
**最终状态**: built
