# mhash 0.9.9.9 — OpenHarmony 预编译包

## 简介

mhash 是一个开源的哈希库，支持多种哈希算法（MD5、SHA1、SHA256、SHA512、CRC32、HMAC 等），提供统一的 C API 接口。

- **官网**: https://mhash.sourceforge.net/
- **源码**: https://download.savannah.nongnu.org/releases/mhash/
- **版本**: 0.9.9.9
- **构建系统**: autotools

## 预编译包内容

| 路径 | 说明 |
|------|------|
| `lib/libmhash.so.2.0.1` | 共享库（动态链接用） |
| `lib/libmhash.so.2` | 共享库 soname 链接 |
| `lib/libmhash.so` | 共享库开发链接 |
| `lib/libmhash.a` | 静态库 |
| `lib/libmhash.la` | libtool 元数据 |
| `include/mhash.h` | 主头文件 |
| `include/mutils/mhash.h` | 哈希 API 头文件 |
| `include/mutils/mglobal.h` | 全局定义 |
| `include/mutils/mtypes.h` | 类型定义 |
| `include/mutils/mutils.h` | 工具函数 |
| `include/mutils/mhash_config.h` | 配置定义 |
| `include/mutils/mincludes.h` | 包含文件 |
| `share/man/man3/mhash.3` | man 页面 |

## 支持的哈希算法（28种）

CRC32, MD5, SHA1, SHA256, SHA512, SHA224, SHA384, HAVAL256/224/192/160/128, RIPEMD160/128/256/320, TIGER/128/160, GOST, CRC32B, MD4, ADLER32, WHIRLPOOL, SNEFRU128/256, MD2

## 使用方法

### 编译链接（共享库）
```bash
clang -I$PREFIX/include -L$PREFIX/lib -lmhash your_program.c -o your_program
```

### 编译链接（静态库，推荐在 HarmonyOS 上使用）
```bash
clang -I$PREFIX/include your_program.c $PREFIX/lib/libmhash.a -o your_program
```

### 示例代码
```c
#include <mhash.h>
#include <stdio.h>

int main() {
    MHASH td = mhash_init(MHASH_MD5);
    mhash(td, "hello", 5);
    unsigned char hash[16];
    mhash_deinit(td, hash);
    for (int i = 0; i < 16; i++) printf("%02x", hash[i]);
    printf("\n");
    return 0;
}
```

## HarmonyOS 适配说明

- HMDFS 上共享库符号链接不被动态链接器解析，建议使用静态链接或将库文件复制为真实文件
- mhash 无命令行二进制，仅提供库和头文件