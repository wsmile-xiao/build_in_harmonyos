# E257 — HarmonyOS 拒绝 shebang 脚本 exec

## 错误特征

在 OpenHarmony PC 上直接执行任何带 shebang（`#!` 开头）的脚本文件时：

```text
/data/service/hnp/bin/bash: ./script.sh: /bin/sh: bad interpreter: Permission denied
/bin/sh: ./configure: Permission denied
shunit2:FATAL please declare TMPDIR with path on partition with exec permission
```

典型场景：
- `./configure`（autoconf 生成，`#! /bin/sh`）→ Permission denied (exit 126)
- shunit2 测试框架的 noexec phantom 检查 → FATAL
- 集成测试脚本（`#!/usr/bin/env bash` 或 `#!/data/service/hnp/bin/bash`）→ bad interpreter
- 修改 shebang 指向任意合法解释器路径仍失败（与解释器路径无关）

## 触发条件

- 构建系统: autotools（configure 脚本）/ 任意测试框架（shunit2/CTest 脚本）/ 纯脚本工具
- 阶段: configuration（configure）、testing（make check）、runtime（脚本工具）
- 文件位置: tmpfs（/storage/Users）、hmdfs、hmfs 均受影响；仅 `/data/service/hnp` 下的脚本可 exec

## 根因分析

OpenHarmony PC 内核/MAC 安全机制对"脚本文件（文本 + shebang）"的 exec 系统调用有访问控制：
任何用户在可写位置创建的脚本文件，通过 `execve` 由 shebang 解释器加载时均被拒绝
（内核返回 EACCES，shell 显示 "bad interpreter: Permission denied"）。

该限制对**脚本文件本身**生效，与 shebang 指向的解释器路径无关：
- 直接运行 ELF 二进制（C 程序、编译产物）→ 正常
- 直接运行文本脚本（无 shebang，如 `exit 0`）→ bash 可自行解释（fallback）
- 直接运行带 shebang 的脚本 → 被拒
- 用解释器显式执行（`bash script.sh`、`sh configure`）→ 正常

## 解决方案

### 推荐方案
1. **脚本一律显式解释执行**：`bash script.sh` / `sh script`，不用 `./script`
2. **测试框架 phantom 去 shebang**：shunit2 生成的 phantom 文件内容去掉 `#! /bin/sh` 行，
   bash 会 fallback 自行解释无 shebang 文本
3. **make check 加 LOG_COMPILER**：`make check LOG_COMPILER=bash SHELL=bash`，
   让集成测试用 bash 显式运行
4. **conan build() 显式 bash**：`self.run("NOCONFIGURE=1 bash autogen.sh")` +
   `self.run("bash configure ...")`
5. **进程替换改 here-string**：bash 的 `< <(cmd)` 依赖 /dev/fd（HarmonyOS 亦不可访问），
   改为 `<<< "$(cmd)"`

### 禁止做法
- ❌ 仅修改 shebang 解释器路径（如 `#!/bin/sh` → `#!/data/service/hnp/bin/bash`）——
  HarmonyOS 拒绝 exec 任何脚本文件，改路径无效
- ❌ 依赖脚本通过 shebang 直接执行的方式交付工具（需提供 `bash xxx` 调用或 C wrapper）

## 验证
```bash
# 失败现象
./test.sh   # → bad interpreter: Permission denied

# 修复后
bash test.sh          # → 正常执行
make check LOG_COMPILER=bash   # → 测试通过
```

bashdb 实例：`bashdb --version`（bash 显式执行）正常，`bashdb`（shebang 直接执行）被拒。

## 关联条目
- 相关: E002（/tmp 只读）、/dev/fd 不可访问（进程替换失败，与 E257 同源）
