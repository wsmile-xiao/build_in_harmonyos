# libredwg 0.13.3 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-15
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos)
- 状态: built

## 编译步骤
- `./configure --build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu --disable-python --disable-bindings --disable-werror --enable-debug --enable-static --disable-shared`
- `make -C src`
- `make -C test/unit-testing check`（325 binaries + check-objects.pl）
- 打包 `include/dwg.h` `include/dwg_api.h` `lib/libredwg.a`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess Permission denied | HMDFS + 未指定 --build | `--build/--host=aarch64-unknown-linux-gnu` |
| 2 | config.status subs1.awk Permission denied | umask 077 + HMDFS setgid | configure 内 umask 077→022 |
| 3 | make install 要 makeinfo | 无 texinfo | 不跑 `make install`，直接 copy 头文件和 `.a` |
| 4 | 默认 --disable-static | `AC_DISABLE_STATIC` | `--enable-static --disable-shared` |

## 验证结果
```
conan create archives/l/libredwg/0.13.3 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
CREATE_EXIT:0
libredwg version=10 entity=LINE read_missing=4096
```
