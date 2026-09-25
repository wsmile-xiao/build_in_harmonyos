# E544（草稿）x86_64 runner 上 qemu 跑不了 OHOS 动态产物，静态副本可以

## 现象

在 x86_64 构建机上想实跑一下交叉编译出来的 aarch64 产物：

```
$ ./since -V                      # binfmt_misc 已注册 qemu-aarch64
aarch64-binfmt-P: Could not open '/lib/ld-musl-aarch64.so.1': No such file or directory

$ qemu-aarch64 -L $NDK/sysroot ./since -V
qemu: uncaught target signal 11 (Segmentation fault) - core dumped
```

把 NDK 的 `libc.so` 软链成 `<sysroot>/lib/ld-musl-aarch64.so.1` 补齐路径后，仍然 signal 11。

## 根因

两道坎，第二道才是关键：

1. **路径**：动态产物的解释器写死 `/lib/ld-musl-aarch64.so.1`，宿主没有这个文件。
2. **加载器**：把路径补齐后，OHOS 的 musl 动态加载器在 qemu-user 下依然段错误。
   用最小 hello world 复现同样结果，**与被测程序无关**：

```
$ clang -o hello hello.c   && qemu-aarch64 -L /root/tmp/ohos-sysroot ./hello
qemu: uncaught target signal 11 (Segmentation fault)
$ clang -static -o hello_s hello.c && qemu-aarch64 ./hello_s
hello-ohos          ← 静态链接可以跑
```

即：问题只发生在动态加载阶段，程序本身的代码在 qemu 下执行没问题。

另外注意一个陷阱：仓库 profile 的 build 与 host 都是 `os=OHOS`，所以 conan 的
`can_run()` 返回 **True**——它比较的是 profile，不是物理 CPU。**不能用 `can_run()`
判断"能不能执行"**。

## 对策

把"功能验证"和"发布产物"分开：

```bash
# 1) 功能验证：额外编一份只用于测试的静态副本
$CC -static -o $TMPDIR/since_static since.c

# 2) 用 wrapper 复用上游/发行版的测试脚本，无需改脚本
mkdir -p $TMPDIR/qbin
printf '#!/bin/sh\nexec qemu-aarch64 %s "$@"\n' "$TMPDIR/since_static" > $TMPDIR/qbin/since
chmod +x $TMPDIR/qbin/since
PATH=$TMPDIR/qbin:$PATH AUTOPKGTEST_TMP=$TMPDIR/adt sh -x debian/tests/simple   # 6/6 通过
```

**发布产物保持动态链接不变**——不要为了能跑测试就把包改成静态。

`test_package` 写成两层，一份脚本同时适配两种环境：

```python
if not artifact_checks(binary):        # ELF magic + e_machine==0xB7 + 可执行位
    return 1
runnable, detail = probe_runnable(binary)
if not runnable:
    print(f"[skip] runtime checks: this machine cannot execute {binary}")
    print(f"       probe output: {detail}")     # 原样打印探测输出，不掩盖
    return 0
return 0 if runtime_checks(binary) else 1       # CI 的 aarch64 真机走这里
```

本机 W3 输出 `[skip]` 并附探测原文，CI 真机上自动升级为完整运行时断言。

## 不要这样做

- **不要把 skip 当 pass**，也不要在 `test()` 里 try/except 吞掉执行失败后 `return 0`：
  L1e 破坏性反向验证与真人评审都会核对，伪造运行证据是一票否决项。
- **不要为了跑测试把发布包改成静态链接**：链接方式是产物形态，不该被验证手段倒推。

## 与既有条目的区别（查重）

- **E356（chibicc，固定目标编译器）**：根因是**编译器生成的是 x86-64 代码**而 worker 是
  armv8，属于目标架构不匹配；本条是**同架构下动态加载器在 qemu-user 里跑不起来**，
  换成静态链接即可执行，修复方向完全不同。
- **E374**：同属「`can_run()` 为真不等于能执行」这一族，但 E374 的阻塞点是
  **OHOS 真机缺 ELF 签名工具链**，对策是 artifact-first + 能力门控、缺工具时记
  NOT_RUN；本条的阻塞点是 **x86 宿主上 qemu-user 加载 OHOS musl 动态解释器崩溃**，
  且给出了一条 E374 没有的可行路径——**用静态副本在 qemu 下跑完整功能断言**，
  从"只能 NOT_RUN"变成"本机也能拿到真实通过率"。两条互补，建议并存并互相引用。

## 实测来源

since 1.1 适配（`archives/s/since/1.1`），qemu-aarch64 10.0.13 + OpenHarmony NDK
musl sysroot；静态副本在 qemu 下跑通 Debian autopkgtest 的 6 条功能断言。
