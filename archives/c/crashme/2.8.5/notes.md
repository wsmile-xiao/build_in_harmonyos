# crashme 2.8.5 适配笔记

## 上游信息
- 上游作者: George J. Carrette（crashme，1990s 起）
- 功能: 通过随机数据 / 随机机器指令测试系统与软件的健壮性（crash 注入）
- 形态: 纯 C 命令行工具 + 一个 unix makefile（另有 VMS 的 descrip.mms）

## 源码获取
上游站点在 CI worker 上不可达。改用 **Debian pool 的 orig.tar.gz**：
```
https://deb.debian.org/debian/pool/main/c/crashme/crashme_2.8.5.orig.tar.gz
sha256 = 0581b050d95e90697b9eef8735041c7aa33122a33b85db305484b4497a4f3ce1
```

## 编译（等价于上游 makefile 的 `all: crashme pddet`）
```
clang -O2 -Wall -DPRNG_MT -c crashme.c    -o crashme.o
clang -O2 -Wall -DPRNG_MT -c vnsq.c       -o vnsq.o
clang -O2 -Wall -DPRNG_MT -c mt19937ar.c  -o mt19937ar.o
clang -O2 -Wall -DPRNG_MT -c pddet.c      -o pddet.o
clang -O2 -Wall -DPRNG_MT -o crashme crashme.o vnsq.o mt19937ar.o
clang -O2 -Wall -DPRNG_MT -o pddet   pddet.o
```
- `-DPRNG_MT` 必填：上游 `CCFLAGS=-DPRNG_MT ...`，启用 Mersenne Twister 随机源
  （`mt19937ar.c`）；不定义会出现符号缺失。
- 无外部依赖，`DT_NEEDED` 仅 `libc.so`。

## 运行验证
- `crashme <nbytes> <seed> <ntries>` —— 上游 makefile 的 ptest2 用法。
  该工具**会主动制造 SIGSEGV/SIGILL**，属设计行为。
- `pddet` —— 能捕获并检测子进程崩溃的辅助工具，上游 ptest1 目标就是直接 `./pddet`。
- **CI 回归不执行崩溃路径**：消费者测试只做静态校验 + `pddet` 安全调用。

## 测试（test_package，8 条断言）
1–2. `bin/crashme`、`bin/pddet` 存在
3–4. 两者可执行
5–6. 两者均为 ELF64 / AArch64（e_machine == 0xB7）
7.   `crashme` 产物非平凡可读（> 4KB）
8.   `pddet` 安全调用：未被信号杀死、退出码不在 {126,127,255}

**注意**：`crashme` 无 `--version/--help`，且其运行目的就是崩溃，因此不做 `crashme` 的运行断言；
断言全部用 `popen` 直读子进程输出，**不落盘到 /tmp**（OHOS 上 /tmp 只读）。
