# bcrypt 1.0 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-07-15
- 编译器: clang 15.0.4
- 平台: aarch64 / OpenHarmony 6.0
- 状态: published

## 源码
- 仓库: https://github.com/rg3/libbcrypt
- Commit: 8aa32ad94ebe06b76853b0767c910c9fbf7ccef4
- 描述: bcrypt password hash C library by rg3, wraps Solar Designer's crypt_blowfish

## 编译步骤
1. 应用补丁 (0001-Makefile.patch, 0002-crypt_blowfish-Makefile.patch): 将 CC=gcc 改为 CC=clang
2. 运行 `make CC=clang -j1` 构建 bcrypt.a 静态库
3. 测试通过: `make test` → bcrypt_test 全部通过

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Conan build:compiler_executables:c 不存在 | OHOS适配版Conan不支持子键访问 | 改用 dict.get() 获取编译器路径 |
| 2 | Conan build: "No makefile found" | basic_layout 将构建目录与源码目录分离 | 使用 make -C {source_folder} |
| 3 | CMakeDeps: "Library 'bcrypt' not found" | 库文件名为 bcrypt.a, Conan期望 libbcrypt.a | package() 中重命名为 libbcrypt.a |

## 平台适配说明
- x86.S 文件有 #ifdef __i386__ 守卫, 在 aarch64 上编译为空对象文件
- BF_ASM=0 在 aarch64 上, 使用纯 C 实现 (无需汇编)
- 无需额外平台补丁

**编译结束**: 2026-07-15 15:26
**最终状态**: published
