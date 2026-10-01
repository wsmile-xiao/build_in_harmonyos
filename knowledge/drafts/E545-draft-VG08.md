# E545 — conan 子进程继承 stdin 为 socket 时 OHOS SDK clang 静默 exit 1

## 错误特征

`conan create` 构建阶段，make 只输出一行被调用的编译命令，紧接着就是归一化的
失败，**没有任何编译器诊断**：

```
vgabios/0.8a: RUN: make -j1 CC=/data/service/hnp/bin/clang GCC=… BCC=… AS86=…
/data/service/hnp/bin/clang -o vbetables-gen vbetables-gen.c
make: *** [Makefile:85: vbetables-gen] Error 1

vgabios/0.8a: ERROR:
Package '6b129b068851896169fae42d399fa922d239ce8a' build failed
ERROR: vgabios/0.8a: Error in build() method, line 121
	self.run(
	ConanException: Error 2 while executing
```

在 `self.run` 里直接探针同一二进制，可见 `clang --version` 与
`clang-15 --version` 都是 `rc=1` 且 stdout/stderr 全空：

```
##clang15
rc=1                                   # 无任何输出
##py3
Python 3.12.9
rc=0                                   # 非 SDK 路径的二进制正常
```

## 触发条件

- 平台：HarmonyOS / OpenHarmony 桌面沙箱（OpenDesk agent 会话），工具链位于
  `/data/service/hnp/**`（HNP 挂载）
- 触发者：`conan create`（其 `ConanFile.run` → `subprocess.Popen(shell=True, …)`
  未指定 stdin，子进程继承 agent 会话的 **socket 型 stdin**）
- 阶段：compilation（第一次调用 SDK clang 即失败）

## 根因分析

1. `ConanFile.run()` 经 `conan_run()` 使用
   `subprocess.Popen(command, shell=shell, stdout=…, stderr=…, cwd=cwd)`，
   **没有传 `stdin=`**，因此子进程（以及 make 再派生的 clang）继承会话 stdin。
2. 本沙箱下该 stdin 是 socket；SDK 的 `clang` 是 180 字节 `#!/bin/sh` 包装脚本
   （`exec -a <自身路径> <clang-15> "$@"`），真正干活的是 109 MB 的 `clang-15`。
   在此继承关系下，`clang`/`clang-15` 启动后**静默 `exit 1`**（零输出）。
3. make 把非零退出归一为 `Error 1`，于是现象被误读为「源码/配方编译错误」。

**已排除项**（vgabios 0.8a 实测，均可复现反证）：

| 假设 | 反证 |
|------|------|
| 环境变量 | 把 conan 子进程 ENVDUMP 的 84 项变量全量复制到交互 shell，clang 正常 |
| rlimit | conan 子进程 `/proc/self/limits` 全部 unlimited |
| LD_LIBRARY_PATH | 指向 dev86 `p/lib`（无 `.so`）；`env=-u LD_LIBRARY_PATH` 仍失败 |
| shell 种类 | `/bin/sh`、`/data/service/hnp/bin/bash` 显式 `-c` 均失败 |
| conanbuild 包装 | `self.run(cmd, env=None)`（不 source conanbuild.sh）仍失败 |
| cwd | 在 conan 缓存目录手工 `make` 可成功 |
| HNP 挂载本身 | `/data/service/hnp/bin/bash` 在 conan 子进程中可正常执行 |

## 解决方案

### 推荐方案

在**调用侧**把 conan 进程自身的 stdin 重定向为 `/dev/null`：

```bash
conan create archives/v/vgabios/0.8a \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --build="vgabios/*" < /dev/null

# ohc 工具同理（其内部会再调 conan create）
python3 scripts/ohc-run.py conan-verify vgabios 0.8a < /dev/null
python3 scripts/ohc-run.py finish      vgabios 0.8a built < /dev/null
```

实测：同一条命令加 `< /dev/null` 后 `conan create` rc=0，5 个 ROM 全部产出、
test_package 9/9 PASS。

> 注意：只把 **make 命令**重定向（`self.run("make … < /dev/null")`）**无效** ——
> 需要重定向的是 conan 进程自己的 stdin，让整条 self.run→make→clang 链路
> 都不继承会话 socket。

### 回退方案

用包装脚本在 exec 前显式重定向：

```bash
zsh -c 'exec 0</dev/null; <conan create …>'
```

## 关联

- 同族问题：`DRAFT-CONAN-RUN-ENV-NOT-DELIVERED-TO-COMPILER`（conan `run(env=)`
  的语义与传递陷阱）
- 同平台另一静默失败点见 E546（zsh heredoc 依赖只读 `/tmp`）
