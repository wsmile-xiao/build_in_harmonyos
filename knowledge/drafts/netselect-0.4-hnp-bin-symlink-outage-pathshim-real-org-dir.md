# DRAFT: 设备 /data/service/hnp/bin 符号链接集体失效——PATH 前置 .org 真实目录绕过

> 草稿（DRAFT）。与同目录 `netselect-0.4-hnp-bin-symlink-outage-pathshim-real-org-dir.kv` 成对。
> 实证来源：netselect 0.4 真机 shadow CI（2026-09-29，r1），同日所有库的 job 全部死在 KC。

## 现象

真机 shadow CI 跑到 KC（或任何调用 bash 的步骤）即失败：

```
ci/conan/build_and_test.sh:980: permission denied: bash
[fail] KC: knowledge check failed — blocking build
L1_RESULT=skip: blocked_by_KC
```

直接探测可确认整条工具链断裂：

```sh
bash -c "echo ok"        # → 127 / permission denied / inaccessible
ls -la /data/service/hnp/bin/
# 所有条目显示 l?????????  ? ? ?  —— 符号链接目标全部不可解析
```

**关键判别**：这不是 PATH 缺失（opencsg/zlib/E529/E540 那类"把 hnp/bin 加进
PATH"解决的是工具不在 PATH；本次是 PATH 里有、但 `/data/service/hnp/bin/`
下的符号链接本身失效）。同日设备上其它所有库的 job（libltc/ntldd/esekeyd/
edlin/xfpt/wordplay…）exit code 全部为 1/127，即设备级故障而非单包问题。

## 根因

`/data/service/hnp/bin/` 下每个工具（bash/make/clang/readelf/…）都是指向
`/data/service/hnp/<项目>.org/<版本>/...` 的符号链接；某次挂载/文件系统事件
后这些链接目标全部不可解析（HMDFS 符号链接跟踪故障，E050/E073 的设备侧
变体）。`command -v bash` 仍能找到路径，但执行/ls 均被拒。

## 解决方案（job 环境层，不改基础设施）

**原位真实二进制目录仍然可用且有 ELF 签名**。把对应 `.org` 版本目录直接
前置到隔离 job 的 `env.sh` PATH（job 目录文件，不属于 git 基础设施）：

```sh
# bash 的真实位置
ls /data/service/hnp/bash.org/bash_5.3/bin/   # bash bashbug —— 真实文件
# env.sh 修改（PATH 行前置）
export PATH=/data/service/hnp/bash.org/bash_5.3/bin:$HOME/ohpc-ci-shadow/python-user/bin:$HOME/.local/bin:$PATH
```

验证：

```sh
PATH=/data/service/hnp/bash.org/bash_5.3/bin:$PATH bash -c "echo ok"
```

## 两个被实测否决的替代方案

1. **把真实 bash 复制到 HMDFS job 目录再进 PATH** → exit 126 Permission
   denied：副本丢失 ELF 签名（E077）。签名只在原位有效。
2. **复制到非 HMDFS 可执行分区** `/data/storage/el2/base/haps/entry/files/`
   → 同样 126：该分区也不保留签名，必须 `binary-sign-tool` 重签——而签
   名工具本身也在坏掉的 hnp/bin 里，死锁。

## 复用要点

- 看到 `permission denied: bash` 且同日其它 job 也全灭 → 先 `ls -la
  /data/service/hnp/bin/` 看 symlink 是否 `l?????????`，别急着改自己的包。
- 绕过口诀：`.org` 目录原位真实二进制 + job env.sh PATH 前置；不要复制。
- readelf 等诊断工具同样会失效，自写测试脚本要准备 `file` 兜底。
