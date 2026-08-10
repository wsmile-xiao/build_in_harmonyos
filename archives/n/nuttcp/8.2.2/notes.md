# nuttcp 8.2.2 适配笔记

## 编译环境
- 构建系统: makefile (plain Makefile, no configure)
- 编译日期: 2026-08-07
- 编译器: clang/clang++
- 状态: published

## 编译步骤

nuttcp 使用简单的 Makefile 构建，无 configure 脚本。

```bash
source .build-context-nuttcp-8.2.2 && cd $BUILD_SRC_DIR
make CC="clang" OPT="-fPIC -O2" -j1
```

构建产物为单个可执行文件 `nuttcp-8.2.2`。

安装到 staging：
```bash
mkdir -p $TEST_PREFIX/bin $TEST_PREFIX/share/man/man8
cp nuttcp-8.2.2 $TEST_PREFIX/bin/nuttcp
cp nuttcp.8 $TEST_PREFIX/share/man/man8/
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | sys/poll.h 重定向警告 | 鸿蒙 sysroot 将 sys/poll.h 重定向到 poll.h | 非致命警告，不影响编译 |
| 2 | SSL 证书过期导致下载失败 | nuttcp.net 官方 SSL 证书过期 | 手动 curl -k 下载后放置到 builds 目录 |

## 源码修改

无源码修改，nuttcp 在 HarmonyOS 上直接编译通过。

## 依赖版本

无外部依赖，仅依赖 musl libc。

## 验证结果

```bash
$ ./nuttcp-8.2.2 -V
nuttcp-8.2.2
```

二进制正确报告版本号，ELF 格式为 aarch64 动态链接可执行文件。

## 注意事项

- nuttcp 是命令行工具 (application)，不是库 (library)
- 需要创建 commands.json 声明 (R38)
- conanfile.py 使用 makefile 构建系统，非 autotools
---

**编译结束**: 2026-08-07 06:09
**最终状态**: built
