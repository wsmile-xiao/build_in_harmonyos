# autoconf configure 被 $CONFIG_SHELL 劫持到坏 bash：HMDFS getcwd 失败的强制 /bin/sh 方案

- **软件**: libfec 1.0-26-gc5d935f（泛化到 HMDFS 上的 autoconf 项目）
- **阶段**: configure（conan create）
- **severity**: 2
- **状态**: DRAFT

## 现象

```
shell-init: error retrieving current directory: getcwd: cannot access parent directories: Not a tty
job-working-directory: error retrieving current directory: ...
configure: WARNING: unrecognized options: ...
pwd: error retrieving current directory: ...
configure: error: working directory cannot be determined
```

即使用 `sh configure` 调用也一样失败。

## 根因（两层叠加）

1. 部分 OHOS 设备的工具链 bash（`/data/service/hnp/bin/bash`，ci profile 的
   `CONFIG_SHELL`/`SHELL` 指向它）在 HMDFS 目录下 **getcwd() 失败**（PWD 为空，
   errno 混乱：Not a tty / Invalid argument / Bad address）。`/bin/sh`(mksh)
   与用户级 bash 同目录正常——所以 frp 布局的设备不复现。
2. **autoconf 2.69 configure 前奏按 `$CONFIG_SHELL` 重 exec 自身**——配方里
   `sh configure` 没用，configure 仍切到环境里的坏 bash 上跑，pwd 检查即死。
3. conan `self.run(env="conanbuild")` 会 source profile `[buildenv]` 导出的
   CONFIG_SHELL/SHELL，配方进程 `os.environ` 的改动被覆盖。

## 修复

```python
# configure：变量前缀压过 buildenv 导出，并被记录进 config.status
self.run(f'CONFIG_SHELL=/bin/sh SHELL=/bin/sh sh "{configure}" {args}',
         env="conanbuild")
# make：变量覆盖（上游规则是 POSIX 简单命令，mksh 兼容）
autotools.make(target=..., args=["SHELL=/bin/sh"])
```

诊断探针（定位哪只 shell 坏）：

```sh
cd <HMDFS 构建目录>
for sh in /bin/sh /data/service/hnp/bin/bash $HOME/usr/local/bin/bash; do
  $sh -c 'echo PWD=$PWD'
done
```

## 证据

libfec 1.0-26-gc5d935f 影子验证（10.62.178.77，ci profile）：

- `bash configure`（diag4）与 `sh configure`（diag6，被 $CONFIG_SHELL 劫持）
  均死于 "working directory cannot be determined"；
- 探针证实 hnp bash 在 HMDFS 目录 PWD 为空、`/bin/sh` 正常；
- 加 `CONFIG_SHELL=/bin/sh SHELL=/bin/sh` 前缀 + `make SHELL=/bin/sh`
  （diag7）：**0 条 getcwd**，configure/make/上游 7 项正确性程序/
  test_package 24/24 全绿，package `21b17f8b…` created。
