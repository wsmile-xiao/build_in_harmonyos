# libkeccak — Keccak 家族哈希库

libkeccak 是一个面向位的、逐线（lanewise）实现的 Keccak 家族哈希库，支持：
- 可扩展输出大小（SHAKE/XOF）
- 状态序列化与反序列化（marshal/unmarshal）
- 隐式参数的算法调优
- 敏感数据的安全擦除
- HMAC 支持

## 已编译版本

| 版本 | 状态 | 编译日期 | 构建系统 |
|------|------|----------|----------|
| 1.4.3 | published | 2026-06-01 | makefile |

## 源码地址

https://github.com/maandree/libkeccak

## 依赖

- **运行时**: libc（仅依赖 libc，无其他运行时依赖）
- **构建时**: libc + clang + make + llvm-ar

## 编译要点

- 无 configure 脚本，纯 Makefile 项目
- 需覆盖 CC=clang（默认 c99 在 HarmonyOS 不可用）
- 需覆盖 CFLAGS="-fPIC -O2"（环境要求）
- 需覆盖 AR=llvm-ar（使用 LLVM 工具链）
- DESTDIR 模式下 PREFIX=$DEFAULT_PREFIX 路径正确

## 安装产物

- `lib/libkeccak.so.1.4`（共享库）
- `lib/libkeccak.so.1 → libkeccak.so.1.4`（符号链接）
- `lib/libkeccak.so → libkeccak.so.1.4`（符号链接）
- `lib/libkeccak.a`（静态库）
- `include/libkeccak.h`（主头文件）
- `include/libkeccak/*.h`（9 个子头文件）
- `share/man/man3/*.3`（57 个 man 页面）
- `share/man/man7/libkeccak.7`
- `share/licenses/libkeccak/LICENSE`