# tiny-AES-c

tiny-AES-c 是一个用 C 编写的小型、可移植、无外部依赖的 AES 实现，支持 128/192/256 位密钥与 ECB、CTR、CBC 三种工作模式，常用于嵌入式、资源受限环境或作为轻量加密依赖。

## 功能概述

- AES-128 / AES-192 / AES-256 分组加密（16 字节分组）
- 三种工作模式，可在编译期独立开关：
  - ECB：`AES_ECB_encrypt` / `AES_ECB_decrypt`（单分组，16 字节）
  - CBC：`AES_CBC_encrypt_buffer` / `AES_CBC_decrypt_buffer`（多分组，长度须为 16 的倍数）
  - CTR：`AES_CTR_xcrypt_buffer`（加解密同一函数，多分组）
- 上下文接口：`AES_init_ctx`、`AES_init_ctx_iv`、`AES_ctx_set_iv`
- C++ 使用 `aes.hpp`（在 `extern "C"` 中引入 `aes.h`）
- 不提供填充（padding）与错误检查，调用方需自行保证缓冲区长度

## OHOS 适配

- **零补丁**：`aes.c` 只包含 `<stdint.h>` 与 `<string.h>`，源码中没有任何 OS、平台或字节序条件编译，OHOS 与 Linux 共用同一份源码。
- **构建系统**：使用仓库根目录的 raw `Makefile`。上游同时提供的 `CMakeLists.txt` 在本仓库不可用，原因有三：`cmake_minimum_required(VERSION 2.8.12)` 会被 CMake 4.x 直接拒绝（Compatibility with CMake < 3.5 has been removed）；`target_include_directories(tiny-aes PRIVATE tiny-AES-c/)` 指向的 `tiny-AES-c/` 子目录在 release tarball 中不存在；且没有任何 `install` 规则。
- **产物配置**：打包产物为上游默认配置（AES128，CBC/ECB/CTR 全部启用），静态库 `libtiny-aes.a`；`shared=True` 时链接同一份 `-fPIC` 目标文件得到 `libtiny-aes.so`。
- **已知约束**：密钥长度（`AES128/AES192/AES256`）与模式（`CBC/ECB/CTR`）是写进 `aes.h` 的编译期宏，同时决定 `struct AES_ctx` 的布局（`RoundKey[AES_keyExpSize]`、`Iv[16]`）。上游自带的 conanfile 把它们暴露为选项，会让消费方在按头文件默认值（`#define AES128 1`）编译的同时链接到按其他配置编译的库，产生静默的结构体布局错配；本包因此不提供这些选项，需要其他密钥长度时按下节重建。
- 与 Linux 的差异：无。该库不涉及系统调用、文件系统或线程。

## 依赖关系

- 编译依赖：无（仅需 C99 标准头）
- 运行依赖：无（静态库；动态库仅依赖 libc）

## 需要非默认密钥长度时

在消费方自己的工程内定义宏并自行编译 `aes.c`，或在本仓库内以 `AES192=1` / `AES256=1` 为目标配置另建一个版本目录。不要仅通过 `-D` 覆盖消费方代码而不重建库。

## 参考资料

- 上游仓库：https://github.com/kokke/tiny-AES-c
- 许可证：The Unlicense（见包内 `licenses/unlicense.txt`）
- 分组算法参考：FIPS-197；工作模式参考：NIST SP 800-38A
