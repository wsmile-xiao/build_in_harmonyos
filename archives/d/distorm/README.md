# distorm

## 简介

diStorm3 是轻量、高速、易用的 x86/AMD64 二进制流反汇编库（约 45KB，单一 API），BSD 许可。

## OHOS 适配

- 纯 C99 实现，零依赖，无需补丁即可用 clang 编译
- 编译旗标与上游 `make/linux/Makefile` 一致
  （`-fPIC -O2 -DSUPPORT_64BIT_OFFSET -DDISTORM_STATIC -std=c99`）
- 编译器路径从 Conan conf 获取 (R33)
- 库文件名保持上游命名 `libdistorm3`

## 依赖

- 无

## 功能验证

```c
#include "distorm.h"

unsigned char code[] = { 0x90 }; /* NOP */
_DecodedInst result[32];
unsigned int used = 0;
distorm_decode(0, code, sizeof(code), Decode32Bits, result, 32, &used);
```

## 参考

- 上游仓库：https://github.com/gdabah/distorm
