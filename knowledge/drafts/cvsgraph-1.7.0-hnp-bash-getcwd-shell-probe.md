# cvsgraph 1.7.0 — hnp bash 在 conan 构建目录 getcwd 损坏，按能力探针选 shell

## 现象

OHOS 真机（10.62.178.77）上 conan 构建 autotools 包，configure 一启动就刷屏：

```
shell-init: error retrieving current directory: getcwd: cannot access parent directories: Not a tty
job-working-directory: error retrieving current directory: getcwd: ...
pwd: error retrieving current directory: getcwd: ... Bad address
configure: error: Working directory cannot be determined
```

errno 五花八门（Not a tty / No error information / Permission denied /
Bad address / Bad file descriptor）——典型的 HMDFS FUSE 层异常表现。

## 根因

- `/data/service/hnp/bin/bash` 在 **conan 构建缓存目录**
  （`/storage/.../p/b/<hash>/b`，HMDFS 深路径）里自身 getcwd 损坏
- 同一目录下 `/system/bin/sh` 的 getcwd 完全干净
- 旧 autoconf（2.61）在 AC_INIT 阶段做 pwd 校验，getcwd 噪音直接致命
- 这是 E386（capability-tested-shell）描述的"shell 可返回 0 但带 getcwd
  诊断"情形的又一实证——**返回码不是判定标准，stdout/stderr 无诊断才是**

## 修复（真机实证）

1. configure 一律显式：
   `CONFIG_SHELL=/system/bin/sh /system/bin/sh <configure> --prefix=/`
   （显式 sh 调用顺带规避 hmdfs 拒绝 shebang 脚本 exec 的问题）
2. **CONFIG_SHELL 必须同步固定**：否则 autoconf 把 PATH 里的 hnp bash
   烤进 Makefile 的 `SHELL=`，config.status/make 阶段再次踩坑
3. 新设备首跑前的能力探针（E386 探针法）：

```sh
cd <conan 构建目录>          # 必须在实际构建目录，不是任意目录
bash -c pwd 2>/dev/null      # 输出干净才算可用
/system/bin/sh -c pwd        # 对比候选
```

## 设备差异警示

旧设备（10.62.134.118）上 celt/fcrackzip 用 `bash configure` 成功过——
**不能跨设备假设 bash 可用**，每台新设备先跑探针。本设备 `/bin/sh` 与
`/system/bin/sh` 同体（toybox），不是 mksh（celt 笔记里的 mksh 坑不适用）。

## 关联

- E386 — 能力探针选 shell 与选择性派发
- cvsgraph-1.7.0-autotools-no-canonical-host — 同日同设备的姊妹坑
