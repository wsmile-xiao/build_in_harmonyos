# E7300 — qemu-user 下「消费者程序 fork/exec 被测 aarch64 CLI」子进程 exec 失败（rc=127）

## 错误特征

x86_64 runner 上用 `qemu-aarch64 ./consumer-static <被测 CLI 路径>` 跑消费者用例，
消费者自己能启动、能跑完本进程内的检查，但凡是「拉起被测 CLI」的断言全部失败，
子进程退出码为 127（消费者里 `execv` 失败后 `_exit(127)`）。典型现场
（members 20080128.1-nmu3）：

```text
checks=35 failed=22        # 22 项 FAIL 全部是 --help / 无参数 / -s -p -t -a 等需要 exec members 的断言
FAIL: --help 退出码 0
FAIL: 不存在的组：退出码 1，stderr 给出 does not exist
```

## 触发条件

- 验证环境：x86_64 + `qemu-aarch64`，`/proc/sys/fs/binfmt_misc/qemu-aarch64` 不存在，
  所装 qemu-user 不支持 `-execve`（`qemu: unknown option 'execve'`）。
- 被测对象是 CLI 二进制，消费者通过 `fork+execv` / `posix_spawn` / `popen` 调用它。

## 根因分析

`qemu-aarch64 ./consumer` 由 qemu 自己加载 ELF；但消费者内部的 `execve` 系统调用被
透传给宿主内核，宿主 x86 内核不认识 aarch64 ELF，在没有 binfmt_misc handler 时返回
`ENOEXEC`。与 E544 草稿（动态产物缺 `/lib/ld-musl-aarch64.so.1`）是不同层次的问题：
把被测程序静态重链只解决了「加载器缺失」，解决不了「exec 链」。这不是被测程序的缺陷。

## 解决方案

### 推荐方案

消费者和被测 CLI 都用同源 `.o` 静态重链，再用一个 shell wrapper 充当被测程序的路径——
wrapper 是宿主可直接 exec 的脚本，由它显式起 qemu：

```bash
clang++ -static -o members-static members.o
clang++ -std=c++17 -static -o test_members-static test_members.cpp
printf '#!/bin/sh\nexec qemu-aarch64 %s "$@"\n' "$PWD/members-static" > members-qemu
chmod +x members-qemu
qemu-aarch64 ./test_members-static "$PWD/members-qemu"   # checks=35 failed=0
```

消费者源码无需为此改动，在 aarch64 原生环境里仍然直接 exec 真实的 `bin/<tool>`。

### 回退方案

装有支持 `-execve` 的 qemu-user 或已注册 binfmt_misc 时可直接 exec。都不具备时，让
`test_package` 在非 aarch64 宿主上只编译链接消费者并输出明确 warning「未运行」，
执行交给 aarch64 CI，PR / notes 如实写「本地未实跑、由 CI 执行」。

### 禁止做法

- ❌ 把子进程 rc=127 改成 skip / 放行：127 是验证环境的 exec 链问题，放宽断言会吞掉真回归，
  消费者用例退化为空壳，会被 rule12 判「只是断言」。
- ❌ 把「静态重链副本 + wrapper 跑过」写成「交付产物已实跑」。

## 验证

```bash
ls /proc/sys/fs/binfmt_misc/qemu-aarch64 2>&1
qemu-aarch64 ./test_members-static ./members-static   # 子进程 rc=127 → 22/35 FAIL
qemu-aarch64 ./test_members-static ./members-qemu     # wrapper → checks=35 failed=0
```

## 关联条目

- 相关: 草稿 E544-draft-7C1A（x86 runner 上 qemu-user 无法运行 OHOS aarch64 动态链接产物）
