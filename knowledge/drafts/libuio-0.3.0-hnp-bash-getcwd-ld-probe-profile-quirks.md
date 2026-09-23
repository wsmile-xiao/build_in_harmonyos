# libuio 0.3.0 — 真机三小坑：bash getcwd / 裸 ld 探测 / profile 缺 os.version（draft）

**Category**: ohos | build-system | shell | conan · **Severity**: 2 · **Tool**: configure/bash/conan

## 症状（三个独立故障）

```text
# 1. bash 在 HMDFS cwd 下起不来
shell-init: error retrieving current directory: getcwd: cannot access parent directories
configure: error: working directory cannot be determined

# 2. 老 autotools 找不到裸 ld（SDK 只有 ld.lld，还是个加 --code-sign 的 sh 包装）

# 3. profile 不齐
ERROR: libuio/0.3.0: Invalid: 'settings.os.version' value not defined
```

## 根因与对策

1. **hnp bash 的 getcwd 在 HMDFS 上全挂**。mksh（/bin/sh）getcwd 正常，但 config.status
   走 mksh 又撞别的坑（见姊妹条目）。正解：**预设 `PWD=$build_folder`**——bash 的
   逻辑 pwd 用 `$PWD`（stat 校验，不依赖 getcwd），且 PWD 随环境传播给全部子进程
   （configure/config.status/make）。注意与另一台真机（libfec，autoconf 2.69）的
   `CONFIG_SHELL=/bin/sh` 解法区分：本机 autoconf 2.72 + HMDFS 组合用 PWD。
2. **裸 ld 探测**：celt 的"build 目录 bin/ 造 ld→ld.lld 符号链接"在此类设备不可行
   （HMDFS 拒 symlink，复制包装脚本又拒 exec）。正解：**预设
   `LD=<clang 目录>/ld.lld`**——configure/libtool 尊重 $LD，lld 按 argv[0] 走
   GNU ld 仿真，包装脚本保留 --code-sign。
3. **profile**：设备预置 `ohos-aarch64` 缺 `os.version`，而制品仓二进制按
   os.version=6.0 发布 → 用 **`ohos-aarch64-fixed`**（含 os.version + SDK clang
   绝对路径 + cmake 路径），host/build 同用。

会话级配套：`export PATH=/data/service/hnp/bin:$HOME/.local/bin:$PATH`
（clang/autoconf/m4/perl/gawk/pkg-config 在 SDK，conan 2.29.1 在 .local/bin）。

## 适用面

HMDFS conan 缓存真机（10.62.178.77 实证）上的一切 autotools/脚本类构建；
$LD 方案对"SDK 只有 ld.lld"的所有设备通用。
