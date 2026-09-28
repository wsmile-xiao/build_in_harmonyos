# jam-build-host-toolchain-env-shadowing — 宿主工具链环境变量覆盖构建工具自身的变量默认值

- **软件**：argyll-cms 3.5.0（Perforce Jam 构建）
- **时间**：2026-09-27
- **状态**：DRAFT（待主编审核；建议归入 build-system/toolchain 类）

## 现象

`jam -fJambase` 首次执行时，**全部静态库归档失败**，并级联 skip 掉后续 34 个可执行目标：

```
Archive numlib/libui.a
llvm-ar: error: unknown option n
OVERVIEW: LLVM Archiver
USAGE: llvm-ar [options] [-]<operation>[modifiers] ...
```

日志中还能看到真实的执行命令（缺操作符 `rusc`）：

```
	llvm-ar numlib/libui.a numlib/ui.o
	llvm-ar plot/libplot.a plot/plot.o
```

同一个构建里，内置 jpeg/tiff 的 `configure` 也报出一串
`llvm-ar: error: unknown option /`（`AC_PROG_AR`/libtool 直接用环境里的 `AR`）。

## 根因

1. **Jam 会把与 jam 变量同名的环境变量导入变量表。** Jambase 的归档器默认值是
   `AR ?= ar rusc ;` —— `?=` 只在“变量未设置”时生效，而宿主导出的 `AR=llvm-ar`
   已经把它“设置”了，于是归档动作变成 `llvm-ar <archive> <objs>`（没有操作符），
   `llvm-ar` 把归档文件名首字母当成了选项（`n`/`p`/`c`…）。
   OHOS 设备的环境里同时导出了
   `AR=llvm-ar RANLIB=llvm-ranlib NM=llvm-nm STRIP=llvm-strip AS=llvm-as LD=ld.lld`。
2. **autoconf / libtool 同样直接读环境 `AR`/`RANLIB`**，所以子包的 configure 也中招。
3. **同一批环境变量还会被 Jambase 收编成编译/链接 flag**：
   `CCFLAGS ?= $(CPPFLAGS) -g -DUNIX ...`、`LINKFLAGS ?= $(LDFLAGS)`，
   于是宿主 `CPPFLAGS=-I$HOME/usr/local/include`、`LDFLAGS=-L$HOME/usr/local/lib`
   被塞进每一条编译/链接命令，把**共享用户前缀**混进构建（R49/E524 同类风险）。

## 复现/判定命令

```bash
env | grep -E '^(AR|RANLIB|NM|STRIP|AS|LD|CFLAGS|LDFLAGS|CPPFLAGS)='
grep -n '^\s*AR\s*?=' Jambase            # 默认值会被同名环境变量顶掉
grep -n "llvm-ar: error: unknown option" <build.log>
```

## 修复（argyll-cms 采用的最小改动）

```python
# conanfile.py build() 首部：剔除构建工具会隐式读取的宿主工具链变量
for var in ("AR", "RANLIB", "NM", "STRIP", "AS", "LD",
            "CFLAGS", "CXXFLAGS", "CPPFLAGS", "LDFLAGS"):
    os.environ.pop(var, None)
```

```jam
# JamExtra（上游 Jamtop 自带的覆盖钩子）——用确定性通道把工具补回来
CC = <tools.build:compiler_executables 的 c> ;
C++ = <... cpp> ;
AR = ar rusc ;
RANLIB = "" ;
```

依赖的 `-I/-L/-Wl,-rpath` 一律由 `self.dependencies` 的 cpp_info 注入，不再经过环境。

## 通用性

这类“**构建工具隐式从环境读配置**”的问题不限于 Jam：

| 构建工具 | 会读的环境变量 |
|---|---|
| Jam | `AR` `CC` `C++` `LINK` `CCFLAGS` `LINKFLAGS` `RANLIB` `JAM_NEW_GNU_AR_OPTIONS` |
| autoconf/libtool | `AR` `AR_FLAGS` `RANLIB` `NM` `STRIP` `LD` `CC` `CFLAGS` `LDFLAGS` `CPPFLAGS` |
| make | `MAKE` `AR` `RANLIB` `CFLAGS` `LDFLAGS` |

在 OHOS 设备上，宿主导出的是**没有操作符的 llvm-* 工具**（`llvm-ar` 需要 `llvm-ar cru ...`），
而传统构建系统期望的是“程序 + 操作符”形式的 `ar rusc`，两者一旦同名相遇即静默错配。

## 与现有条目的关系

- **E007**（config.guess 不识别 HarmonyOS）：同一次适配中另一类问题，见 patch 0002/0005 的补充结论
  （老版本 config.guess 的 case 分支只有 `GUESS=` 赋值，没有 `echo "$GUESS" ; exit`，补分支后仍不生效）。
- **E011**（HMDFS umask 077）：内置 configure 的私有临时目录问题，见 patch 0004/0007。
- **R33 / R49(E524)**：本条目是它们在“构建工具隐式读环境”方向上的具体化——
  R33 管 recipe 自己别裸用 shell 变量，本条管**宿主环境变量反过来污染构建工具**。

> 条目主题一句话：**宿主工具链环境变量与构建工具自身变量同名时的静默错配**——
> 判据是“构建工具是否会 import 同名环境变量”，修复是“构建前剔除 + 用 recipe 的确定性通道重新注入”。
