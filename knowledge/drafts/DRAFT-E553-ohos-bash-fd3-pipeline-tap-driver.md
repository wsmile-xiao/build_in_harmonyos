# ═══ Draft knowledge entry — OHOS 移植 bash 5.3 组命令 fd 重定向不传入管道元素，automake tap-driver.sh 全军覆没 ═══
# Timestamp: 2026-09-16
# Software: libigloo 0.9.5 (任何经 automake TAP 驱动跑 make check 的 autotools 包)
# Gate: conan create build() 的 make check / 原生 make check
# Status: UNMATCHED — needs human/AI review to promote to E-entry

## 错误特征

```
tap-driver.sh: line 234: 3: Bad file descriptor
ERROR: tests/ro - missing test plan
ERROR: tests/uuid - missing test plan
... (每个 TAP 测试同样报法)
:global-test-result: ERROR
:test-result: ERROR
```

- `make check` 后每个 `tests/*.log` **为空**、`tests/*.trs` 全是 `:test-result: ERROR`。
- **测试二进制直接运行完全正常**（`./tests/ro` 输出 TAP 1..50 全 PASS）。
- 原生探索构建（configure 自动检测 `/bin/sh` 为 SHELL）同一套测试全绿。

## 触发条件

- automake `parallel-tests` + TAP driver（`parallel-tests` + `tap-driver.sh`）驱动的 `make check`。
- `grep -m1 '^SHELL' Makefile` 显示 `$(SHELL)` 为 OHOS conan profile buildenv 注入的 hnp bash
  （`/storage/.../usr/local/bin/bash`, GNU bash 5.3.0 aarch64-unknown-linux-ohos 移植版）。
- 仅 OHOS PC 的 bash 5.3 移植版复现；`/bin/sh`（mksh 系）正常。

## 根因分析

OHOS PC 的 bash 5.3 移植版存在文件描述符继承缺陷：

```sh
# 失败 — 组命令 { ...; } 3>log 的 fd 3 传不进管道元素:
{ echo y | cat >&3; } 3>log          # -> "3: Bad file descriptor"
exec 3>log; echo y | cat >&3          # -> 同样失败
# 正常 — 子外壳 ( ...; ) 3>log :
( echo y | cat >&3; ) 3>log           # -> OK
# 正常 — /bin/sh 下同构脚本全部通过
```

- fd 3 在组内 `/proc/self/fd` 可见，但 dup2(`>&3`) 失败——是 bash 管道 fork 路径的
  fd 表同步 bug，非 HMDFS 问题（`3>/dev/null` 亦失败）。
- automake tap-driver.sh 主结构 `{ (测试程序) | awk '{ print | "cat >&3" }' } 3>"$log_file"`：
  bash 下 awk 子进程里 `cat >&3` 全部失败 → TAP 输出一个字节都进不了 .log →
  tap-driver 判 "missing test plan" ERROR。
- 探索构建 configure 检测 SHELL=/bin/sh 一切正常，造成“探索全绿、conan 全 ERROR”的
  表象背离（与 E551 的 CONFIG_SHELL=bash 问题方向相反：本条 bash 是坏方）。

## 解决方案

conanfile `build()` 的 `make check` 用**命令行变量覆盖** `SHELL=/bin/sh`（mksh 系，
fd 3 继承正常）。命令行赋值优先级高于 Makefile 内置与 env 聚合，不改 Makefile、
不改全局 profile：

```python
autotools.make(target="check", args=["-j1", "SHELL=/bin/sh"])
```

## 验证命令

```sh
# 平台缺陷探针(零依赖):
bash -c '{ echo y | cat >&3 2>&1; } 3>/tmp/fd3probe.log; test -s /tmp/fd3probe.log && echo OK || echo BASH-FD3-BROKEN'
# 命中后修复验证:
make check SHELL=/bin/sh -j1        # libigloo: 10 程序 763/763 PASS
```

## 关键词

tap-driver.sh, Bad file descriptor, missing test plan, fd 3, group command, pipeline,
SHELL=/bin/sh, mksh, bash 5.3, aarch64-ohos, automake TAP, parallel-tests, check-TESTS

---
*源事件: libigloo 0.9.5 适配 (feat/libigloo-0.9.5); metrics 1/1 成功, 置信度 0.95*
