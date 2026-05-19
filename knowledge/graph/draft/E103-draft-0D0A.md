# E103: OpenHarmony shebang 路径错误

## 问题描述

在 OpenHarmony/HongMeng 系统上运行 configure 或其他脚本时，出现以下错误：

```
bad interpreter: /bin/bash: no such file or directory
configure 失败 (exit 127)
```

## 根因分析

OpenHarmony 系统没有传统的 Linux `/bin` 目录结构：
- bash 位于 `/data/service/hnp/bin/bash`
- sh 位于 `/system/bin/sh`

当脚本使用 `#!/bin/bash` 或 `#!/bin/sh` 作为 shebang 时，系统找不到解释器，导致脚本无法执行。

## 受影响范围

所有使用传统 shebang 的脚本文件，包括：
- configure 脚本
- install.sh
- shorewall CLI
- uninstall.sh
- wait4ifup
- 其他 shell 脚本

## 解决方案

### 推荐方案（优先级 1）

修改脚本 shebang：

```bash
# bash 脚本
sed -i '1s|#!/bin/bash|#!/data/service/hnp/bin/bash|' configure

# sh 脚本
sed -i '1s|#!/bin/sh|#!/system/bin/sh|' install.sh shorewall uninstall.sh wait4ifup
```

### 回退方案（优先级 2）

如果无法修改源码，可以尝试创建符号链接（需要 root 权限）：

```bash
ln -sf /data/service/hnp/bin/bash /bin/bash
ln -sf /system/bin/sh /bin/sh
```

## 验证命令

```bash
head -1 configure install.sh shorewall | grep -E "hnp/bin/bash|system/bin/sh"
```

## 禁止事项

- ❌ 不要使用 `--build=...`、`--host=...`、`--target=...` 参数绕过此问题
- ❌ 不要假设 `/bin/bash` 存在

## 知识分类

- 类别: platform
- 严重级别: 🔴 blocking (severity=3)
- 触发工具: configure
- 触发阶段: configuration

## 相关原则

- R1: 参数最少化（只修改 shebang，不使用 --build/--host）
- R8: 源码"四不"准则（使用平台检测而非硬编码路径）
- R15: 历史仅供参考，不盲从（实际路径以当前系统为准）

## 示例补丁

```patch
--- a/configure
+++ b/configure
@@ -1,4 +1,4 @@
-#!/bin/bash
+#!/data/service/hnp/bin/bash

--- a/install.sh
+++ b/install.sh
@@ -1,4 +1,4 @@
-#!/bin/sh
+#!/system/bin/sh
```

---

*Created by 0D0A — 2026-05-15*