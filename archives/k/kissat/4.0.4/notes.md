# kissat 4.0.4 适配笔记

## 编译环境
- 构建系统: custom（自定义configure脚本，不支持--prefix）
- 编译日期: 2026-06-15
- 编译器: clang 15.0.4
- 平台: HarmonyOS, HongMeng Kernel 1.12.0 aarch64
- 状态: published

## 编译步骤

kissat使用自定义构建系统（非标准autotools），configure脚本不支持`--prefix`选项，也没有`make install`目标。

1. `./configure CC=clang -fPIC` — 配置编译器为clang，-fPIC确保位置无关代码
2. `make -j1` — 编译kissat二进制和libkissat.a静态库
3. 手动安装到DESTDIR staging目录:
   - `mkdir -p $TEST_PREFIX/$DEFAULT_PREFIX/bin $TEST_PREFIX/$DEFAULT_PREFIX/lib $TEST_PREFIX/$DEFAULT_PREFIX/include`
   - `cp build/kissat $TEST_PREFIX/$DEFAULT_PREFIX/bin/`
   - `cp build/libkissat.a $TEST_PREFIX/$DEFAULT_PREFIX/lib/`
   - `cp src/kissat.h $TEST_PREFIX/$DEFAULT_PREFIX/include/`
4. `make test` — 编译并运行tissat测试程序（864个测试任务）
5. 手动安装到$DEFAULT_PREFIX（模拟用户部署）
6. `ohc-run.py package kissat 4.0.4` — 制作预编译包

## 测试执行结果

### make test 真实执行输出（2026-06-16 14:43:26 CST）

```
TISSAT Tester for KISSAT
Version 4.0.4 unknown
clang version 15.0.4 -W -Wall -O3 -DNDEBUG -fPIC
Tue Jun 16 14:43:26 CST 2026 HarmonyOS localhost HongMeng Kernel 1.12.0 aarch64

Parallel execution using at most 4 processes (by default).
Found '../test' directory (running test cases that need '../test' too).
Did not find 'drabt' executable.
Did not find 'drat-trim' executable.
Did not find 'dpr-trim' executable.

Install either 'drat-trim' or 'drabt' to check proofs too!
No compression tests for non POSIX configuration.

Scheduled 864 jobs total.
Running 864 jobs in parallel using up to 4 processes.

All 864 test jobs succeeded in 2.65 seconds.
```

- **总任务数**: 864
- **成功数**: 864
- **失败数**: 0
- **耗时**: 2.65 秒
- **并行度**: 4 进程
- **跳过项**: 证明检查（缺少drat-trim/drabt）和压缩测试（非POSIX），均不阻塞

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure不支持--prefix | kissat使用自定义构建系统 | 跳过--prefix，手动安装文件 |
| 2 | 无make install目标 | kissat Makefile不提供install目标 | 手动cp文件到bin/lib/include目录 |
| 3 | DESTDIR覆盖文件权限问题 | HMDFS软链接特性，cp覆盖报Operation not permitted | 先rm -f旧文件再cp新文件 |
| 4 | G0 clean-verify需要自定义命令 | 验证脚本默认加--prefix参数 | 创建hints/clean-verify-hints.yaml指定自定义configure/build/install命令 |

## 源码修改

无补丁，源码无需修改即可在鸿蒙平台编译通过。

## 依赖版本

无依赖（bare metal solver，仅链接libm）

## 验证结果

```bash
$ /storage/Users/currentUser/usr/local/bin/kissat --version
4.0.4

$ file /storage/Users/currentUser/usr/local/bin/kissat
ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1)

$ make test (tissat)
All 864 test jobs succeeded in 2.65 seconds.
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| kissat-4.0.4-ohos-aarch64.tar.gz | 1129KB | 预编译包（含bin/kissat, lib/libkissat.a, include/kissat.h） |
| kissat-4.0.4-ohos-aarch64-debug.tar.gz | 55KB | debug符号包 |

## 注意事项

- kissat使用自定义configure脚本，不支持标准autotools选项
- 需要通过hints/clean-verify-hints.yaml提供自定义configure/build/install命令
- 没有共享库依赖（bare metal solver，仅链接libm）
- configure选项: CC=clang -fPIC（使用clang而非默认gcc，添加-fPIC支持位置无关代码）

---
**编译结束**: 2026-06-16 14:43
**最终状态**: published
---
