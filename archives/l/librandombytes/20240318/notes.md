# librandombytes 20240318 适配笔记

## 编译环境
- 构建系统: 上游 python3 `./configure` + Makefile
- 编译日期: 2026-09-14
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos)
- 状态: built

## 编译步骤
- 前置 clang 到 `compilers/default`
- `./configure --prefix=...`
- 从生成的 arm64 Makefile 去掉 openssl 后端行
- `make`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | openssl 后端编不过 | OHOS 不走该后端 | Makefile 去掉 openssl 目标，仅 kernel |

## 验证结果
```
conan create archives/l/librandombytes/20240318 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
CREATE_EXIT:0
```
test_package 调用 `randombytes()` 并检查 `randombytes_source()`。

## 注意事项
- libmceliece 依赖本库
- 默认静态 `librandombytes.a`
