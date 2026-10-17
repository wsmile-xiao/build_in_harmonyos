# E675（草稿）: automake TAP harness 在设备 bash 下 tap-driver 组 fd3 重定向失效，make check 报 ERROR 且测试日志 0 字节

> Draft: E675-draft-qsoptex
> Stem: `E675-draft-qsoptex` — pairs with the same-stem `.kv`

## 现象

qsopt-ex 2.5.10.3（任务 9919）设备原生探索阶段，`make check` 报：

```
ERROR: tests/test_qs - missing test plan
ERROR: tests/test_qs - exited with status 1
sh: >&3 : bad file descriptor
# TOTAL: 2   PASS: 0   FAIL: 0   ERROR: 2
```

`tests/test_qs.log` 是 **0 字节**。而同一个二进制直接运行输出完整 TAP：

```
$ ./tests/test_qs
1..8
ok 1 - Loaded test LP problem
...
ok 8 - LP written to /dev/null      # rc=0，8/8 全过
```

## 根因

上游 `tap-driver.sh`（automake 1.18 stock，autoreconf --force 更新到 2025-05-03
版本）把整条 `(子进程) | awk` 管道包在：

```sh
:;{
  ( … "$@" 2>&$stderr_fd 3>&- 4>&- … ) | LC_ALL=C awk '… print | "cat >&3" …'
} 3>"$log_file"
```

fd3 承载日志文件。实测在设备/CI 的 **bash 5.3**（`/data/service/hnp/bin/bash`）下，
管道子 shell 内 `2>&3`（stderr_fd=3）直接报 `3: Bad file descriptor`：

- `bash -c '{ ( ls /proc/self/fd | …; echo x 2>&3 ) | cat; } 3>file'` → ls 能看到
  fd3 存在，但 `2>&3` 判失败——bash 内部 fd 表与 /proc 不一致；
- 同结构换 toybox `/bin/sh`（SH_OK）、无管道的 bash 组（NP_OK）都正常。

于是日志 fd 失效 → 测试 stdout 进不了 awk → `missing test plan` + 判
`exited with status 1` + 日志 0 字节。属「产物为空」的假红面（与 G11「返回 0 却
0 字节输出」同族，只是方向相反）：**rc 与 summary 都不能单独作为测试判据**。

## 修复/验证方法

`make check` 显式覆盖 `LOG_DRIVER`，把 driver 解释器换成 POSIX `/bin/sh`：

```bash
# 设备复现（任务目录内，构建树 qsopt-ex-2.5.10.3.work）
cd /storage/Users/currentUser/ws/tmp/builds/qsopt-ex-2.5.10.3.work
env AM_TAP_AWK=gawk /data/service/hnp/bin/bash ./tap-driver.sh \
  --test-name tests/test_qs --log-file ./repro.log --trs-file ./repro.trs \
  -- ./tests/test_qs
wc -c repro.log        # 复现：sh: >&3 : bad file descriptor，0 字节

# 修复形态（配方 build() 同款；$(AWK)/$(top_srcdir) 交给 make 展开）
make check 'LOG_DRIVER=env AM_TAP_AWK=$(AWK) /bin/sh $(top_srcdir)/tap-driver.sh'
grep -A9 "Testsuite summary" test-suite.log   # → TOTAL: 8  PASS: 8  ERROR: 0
wc -c tests/test_qs.log                       # → 744 字节（非 0）
```

配方落点（conanfile.py `build()`）：

```python
self.run(
    'mkdir -p .ohos-test-home && HOME="$PWD/.ohos-test-home" '
    'make check \'LOG_DRIVER=env AM_TAP_AWK=$(AWK) /bin/sh $(top_srcdir)/tap-driver.sh\'',
    cwd=self.build_folder, env="conanbuild")
```

判据三件套：①make check 退出码；②Testsuite summary 的 TOTAL/PASS/ERROR；
③`<test>.log` 字节数 > 0 —— 三者缺一即可被空日志假象骗过。

## 实证

- qsopt-ex 2.5.10.3（任务卡 9919）：bash driver → ERROR/0B；`/bin/sh` driver →
  `# TOTAL: 8 # PASS: 8 # ERROR: 0`、`tests/test_qs.log` 744B、rc=0。
- 结构性排除：`tests/test_qs` 直跑 8/8 全过（证明不是测试本身失败）；
  toybox sh 同结构组重定向正常（证明不是 fd3 打不开，而是 bash 管道子 shell 的
  fd 表问题）。

- 关联：E114（HMDFS mktemp 0700→2700，config.status 空产物同族环境问题）、
  G11 教训（rc=0 却 0 字节输出 = 假绿，本条是其镜像假红）。
