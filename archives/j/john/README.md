# John the Ripper

John the Ripper 是一个密码安全审计和恢复工具，支持多种加密算法的密码破解。

## 功能概述

- 支持 400+ 种密码哈希类型
- 自动检测哈希类型
- 多种破解模式（字典、暴力、规则）
- 支持多线程和分布式破解
- 可扩展插件系统
- 支持加密文件破解

## OHOS 适配要点

### Makefile.legacy 编译

由于 configure 脚本无法识别 HarmonyOS 平台，建议使用 Makefile.legacy：

```bash
make -f Makefile.legacy linux-arm64le \
    CFLAGS="-I~/usr/local/include -DHAVE_LIBSSL -DJOHN_NO_SIMD" \
    LDFLAGS="-L~/usr/local/lib -Wl,-rpath,~/usr/local/lib -Wl,--allow-shlib-undefined -lssl -lcrypto -lm -lz -lcrypt"
```

### SIMD 禁用

HarmonyOS 上 NEON 指令的 shift 参数有问题，需要禁用 SIMD：

```bash
CFLAGS="-DJOHN_NO_SIMD"
```

### OpenSSL 链接问题

预编译的 OpenSSL 使用 FORTIFY_SOURCE，需要添加链接器选项：

```bash
LDFLAGS="-Wl,--allow-shlib-undefined"
```

### john_build_rule.h 缺失

Makefile.legacy 的 linux-arm64le 目标未自动创建 john_build_rule.h，需要手动添加创建规则。

### 测试验证

```bash
john --test
# 显示各种加密算法的破解速度
```

## 依赖关系

### 编译依赖
- OpenSSL 1.1.1w
- clang/gcc
- make

### 运行依赖
- musl libc

## 验证命令

```bash
john --version
# John the Ripper 1.9.0-jumbo-1 [linux-arm64le]

john --test=0
# 快速测试所有加密算法
```

## 注意事项

1. SIMD 禁用会影响部分算法的性能
2. 需要设置 LD_LIBRARY_PATH 或使用 RPATH
3. 配置文件位于 ~/usr/local/share/john/

## 参考资料

- 官方仓库：https://github.com/openwall/john
- 发布页面：https://github.com/openwall/john/releases
- 文档：https://github.com/openwall/john/blob/bleeding-jumbo/doc/