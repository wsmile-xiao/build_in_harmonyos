# wyhash

> The fastest-quality 64-bit non-cryptographic hash function and PRNG.

## 简介

wyhash is a fast, portable, non-cryptographic 64-bit hash function created by
Wang Yi. It passes SMHasher and is designed to be efficient on 64-bit machines,
especially for short keys. The same repository also provides `wyrand`, a
companion 64-bit PRNG, plus `wyhash32.h` (32-bit variant) and `o1hash.h` (an
O(1) "quick and dirty" hash).

The library is **header only**: `wyhash.h` pulls in nothing beyond `<stdint.h>`
and `<string.h>`, so it can be included directly in C or C++ translation units.

## OHOS 适配要点

- Header-only package: `conan create` installs `include/wyhash.h`,
  `include/wyhash32.h` and `include/o1hash.h`, and no binary or library.
- The task version `0-2.gbp234f0c6` pins upstream commit `234f0c6`
  ("Add copyright header"). This snapshot still uses the pre-"final 4"
  algorithm; **do not substitute upstream master**, whose output differs and
  would invalidate the vectors.
- Consumers only need the include directory. With Conan, link against the
  generated CMake target `wyhash::wyhash`.

## 依赖

| 依赖 | 版本 | 说明 |
| --- | --- | --- |
| （无） | - | 仅依赖 C 标准库 `<stdint.h>` / `<string.h>` |

## 功能验证

```cpp
#include <wyhash.h>
#include <cstdio>
#include <cstring>

int main() {
    const char *s = "abc";
    std::printf("%016llx\n",
                (unsigned long long)wyhash(s, std::strlen(s), 2, _wyp));
    return 0;
}
```

Expected for `"abc"` with seed `2`: `0bc54887cfc9ecb1` (see the committed
`test_package/` vectors).

## 参考

- [源码仓库](https://github.com/wangyi-fudan/wyhash)
- [上游 README](https://github.com/wangyi-fudan/wyhash/blob/master/README.md)
