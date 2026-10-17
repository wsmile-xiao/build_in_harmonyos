# draft-scrub-2.6.1-git20240819-musl-double-pthread-join-segv

## 症状

scrub 2.6.1-git20240819.9b4267e 在 OHOS 真机 `make check` 17 FAIL / 0 PASS，
所有涉及随机 pattern 的用例 `exit status: 139`（Segmentation fault, core dumped）；
`-p fillff`（无随机 pass）正常。`-p random` 手动复现 12/12 SEGV，
`-O0 -g`/`-O2`/`-fsanitize=address` 全部同崩（ASan 无报告即崩）。

## 根因

`src/fillfile.c` 的 pthread 预取流水线：`refill_init` 为当前块 `pthread_create`，
`refill_memcpy` 先 `pthread_join` 再为下一块预取；`refill_fini` **无条件再 join
一次** `mp->thd`。单块文件（或最后一轮未预取）时该句柄已 join 过：

- glibc：对已 join 句柄静默容忍 → 上游 CI/RPM buildfarm 全绿（假绿镜像）；
- musl（OHOS）：解引用已回收的线程控制块 → 确定性 SIGSEGV。

## 修复（patches/0002-src-fillfile.c.patch，三行语义）

1. `refill_memcpy` join 成功后 `mp->thd = 0;`
2. `refill_fini` 改为 `if (!no_threads && mp->thd)` 才 join，join 后清零。

无平台宏、POSIX 通用；glibc 行为不变。

## 复现/验证命令（设备可直接执行）

```sh
# 复现（修复前）：任一可写目录下
dd if=/dev/zero of=rep.bin bs=1024 count=8
<已构建的 scrub> -p random rep.bin; echo "rc=$?"   # 修复前 139；修复后 0
```

修复后：12/12 通过；make check 17 FAIL/0 PASS → 15 PASS/6 SKIP/2 FAIL
（余 2 项为 /tmp 只读限制，与本条无关）。
