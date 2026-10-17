# httpry 0.1.8 适配笔记

## 编译环境
- 构建系统: makefile (plain make)
- 编译日期: 2026-08-06
- 编译器: clang/clang++
- 状态: built

## 编译步骤

```bash
# 安装 libpcap 依赖 (conan 制品仓)
conan install --requires=libpcap/1.10.6 -r=ohpcd ...

# 编译 httpry
make CC=clang CCFLAGS="-Wall -O2 -fPIC -I<pcap_include>" LIBS="-L<pcap_lib> -lpcap -lm -pthread"

# 安装到 staging
mkdir -p $TEST_PREFIX/bin $TEST_PREFIX/man/man1
cp httpry $TEST_PREFIX/bin/
cp httpry.1 $TEST_PREFIX/man/man1/
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | pthread_cancel linker error | OHOS 不提供 pthread_cancel (E051 未实现 syscall) | 用 flag-based cancellation 替代：添加 thread_exit_flag 变量，线程循环中检查标志位，sleep 拆分为 1 秒间隔 |

## 源码修改

- patches/0001-rate.c.patch
  - rate.c: 添加 `static volatile int thread_exit_flag`
  - rate.c: `exit_rate_stats_thread()` 设置 flag 替代 `pthread_cancel()`
  - rate.c: `run_stats()` 循环检查 flag，sleep 拆分为 1 秒间隔

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| libpcap | 1.10.6 | conan 制品仓 (ohpcd) |
| libm | system | OHOS libc |
| pthread | system | OHOS libc |

## 验证结果

```bash
$ ./httpry -h
httpry version 0.1.8 -- HTTP logging and information retrieval tool
Copyright (c) 2005-2014 Jason Bittel <jason.bittel@gmail.com>
Usage: httpry [ -dFhpqs ] [-b file ] [ -f format ] [ -i device ] ...
```

## 注意事项

- httpry 是命令行工具 (application)，不是库
- 需要网络接口权限才能实际抓包，CI 环境中仅验证二进制可用性
- OHOS 上 /tmp 只读，PID_FILENAME 默认 /var/run/httpry.pid 需要实际使用时注意

## 编译结束
status: closed
---

**编译结束**: 2026-08-06 17:45
**最终状态**: built

