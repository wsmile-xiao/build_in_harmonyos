# lhasa 0.6.0 适配笔记

## 编译环境
- 构建系统: autotools (autoconf + automake + libtool)
- 编译日期: 2026-08-23
- 编译器: clang/clang++
- 状态: built

## 编译步骤
```bash
autoreconf -fi  # 重新生成 configure（如果需要）
./configure --prefix=/usr/local --enable-static --disable-shared
make -j1
make check
make install DESTDIR=/tmp/staging
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 报 "working directory cannot be determined" | HMDFS 上 bash 的 getcwd() 失败，CONFIG_SHELL=/data/service/hnp/bin/bash 导致 re-exec 失败 | 用 CONFIG_SHELL=/bin/sh 代替 bash；patch configure 中 ac_pwd=\`pwd\` 为 echo $PWD |
| 2 | config.status 报 "can't create subs1.awk: Permission denied" | umask 077 创建目录后 HMDFS 的 chmod 不生效，文件实际不可写 | patch configure 中 umask 077 为 umask 0 |
| 3 | 14 个 shell 测试脚本全部失败 "PWD: unbound variable" | test_common.sh 使用 set -eu 且 bash getcwd() 失败导致 $PWD 未设置 | patch test_common.sh 中 \`test_base="$PWD"\` 为 \`test_base="${PWD:-.}"\` |

## 源码修改

上游测试脚本 test_common.sh 中修改了 \$PWD 引用方式，添加了 ${PWD:-.} 降级处理。

## 依赖版本

无外部依赖，仅需标准 C 库和 autotools 工具链。

## 验证结果

```bash
# 编译验证（在 HarmonyOS aarch64 环境）
CONFIG_SHELL=/bin/sh ./configure --disable-shared --enable-static --build=aarch64-unknown-linux-gnu
make -j1
make install DESTDIR=.../p

# 上游测试
make check  # 3/17 编译测试通过，14 个 shell 脚本因 HMDFS 环境限制未运行
```

## 交付物

| 文件 | 说明 |
|------|------|
| liblhasa.a | 静态库 |
| liblhasa.la | libtool 归档 |
| lha | 命令行工具 |

## 注意事项

- lhasa 是纯 C 库，无外部依赖，适配简单
- 构建产物包括 liblhasa 库（.a）和 lha 命令行工具
- 上游测试使用 automake check 框架：3 个编译测试（test-crc16, test-basic-reader, test-decoder）+ 14 个 shell 脚本测试
- 14 个 shell 测试因 HMDFS 文件系统上 bash getcwd() 失败而无法运行，属于环境限制，非代码问题
- 编译测试（test-crc16, test-basic-reader, test-decoder）全部通过