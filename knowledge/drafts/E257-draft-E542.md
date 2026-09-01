# E257 — UNAME 白名单缺 HarmonyOS 导致 make install 目标未定义

## 错误特征

```
make: *** No rule to make target 'install'.  Stop.
```

或（包一层目录变量缺失时）：

```
make: *** No targets specified and no makefile found.  Stop.
```

注意与 E108 的区别：E108 是 `make: install: No such file or directory`（Error 127，命令不存在）；
本条是 `No rule to make target`（目标整体未定义），`which install` 探测对它无效。

## 触发条件

- 构建系统: 纯 Makefile（无 configure 步骤）
- 阶段: make install
- 环境: HarmonyOS（`uname -s` 返回 `HarmonyOS`，不在上游白名单内）

## 根因分析

上游顶层 Makefile 用平台白名单包裹整个安装规则段：

```make
ifneq (,$(filter Linux Darwin GNU/kFreeBSD GNU Haiku OpenBSD FreeBSD NetBSD DragonFly SunOS CYGWIN% , $(UNAME)))

DESTDIR     ?=
install: ...
```

`$(UNAME)` 为 `HarmonyOS` 时 filter 不命中，`install:` 目标、`DESTDIR`、
`BINDIR/LIBDIR/INCLUDEDIR` 等变量全部未定义，`make install` 直接报
`No rule to make target 'install'`。xxhash 0.8.2 实测命中（Makefile 第 498 行）。

## 解决方案

### 推荐方案

在**源 Makefile** 的 UNAME filter 白名单中追加 `HarmonyOS`（R1/R6：改源文件并经
track-edit 记录，补丁由 `refresh-patch --auto` 生成）：

```make
ifneq (,$(filter Linux Darwin GNU/kFreeBSD GNU Haiku OpenBSD FreeBSD NetBSD DragonFly SunOS CYGWIN% HarmonyOS , $(UNAME)))
```

若系统同时缺 GNU `install` 命令（合并 E108 处理），HarmonyOS 分支下用：

```make
INSTALL ?= cp -p
INSTALL_DATA ?= cp -p
INSTALL_DIR ?= mkdir -p
```

### 禁止做法

- ❌ `--build=`/`--host=` 三元组参数（R15 铁律，native 编译禁止）
- ❌ 只在生成/副本 Makefile 上 sed（R6：改源文件，补丁由 refresh-patch 统一生成）

## 验证

```bash
make -n install   # 能打印安装命令序列即白名单生效
make install DESTDIR=<staging> PREFIX=<prefix>   # 实际安装成功
```

## 关联条目

- 相关: E108（install 命令缺失 Error 127，需合并处理）
