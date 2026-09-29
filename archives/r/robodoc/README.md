# robodoc 4.99.44 for HarmonyOS

## 概述

ROBODoc 从源码中特殊格式的注释头（`/****f* ... *****/`）抽取文档，支持 HTML、
LaTeX、RTF、DocBook XML、troff、ASCII 等多种输出；同时附带 `robohdrs` 头插入器。
本文档记录 robodoc 4.99.44 在 HarmonyOS/OpenHarmony (aarch64) 上的适配与验证。

## 软件信息

| 项目 | 值 |
|------|-----|
| 名称 | robodoc |
| 版本 | 4.99.44 |
| 上游仓库 | https://github.com/gumpu/ROBODoc |
| 下载地址 | https://github.com/gumpu/ROBODoc/releases/download/v4.99.44/robodoc-4.99.44.zip |
| SHA256 | `eeaff45f6fd7bfc2420d0b39e4b0ce44a9c1160564906d218bccd2824b0056e2` |
| 许可 | GPL-3.0-or-later |
| 构建系统 | autotools（autoconf 2.69 预生成 configure + automake makefile.in） |

## 鸿蒙环境

| 项目 | 值 |
|------|-----|
| 系统 | HarmonyOS（HongMeng Kernel 1.12.0） |
| 架构 | aarch64 |
| 编译器 | clang 15.0.4（target: aarch64-unknown-linux-ohos） |
| 构建系统 | autotools |

## 编译步骤

```bash
# 源码（官方 release 资产；git tag 归档缺 Source/makefile.in 不可构建）
curl -LO https://github.com/gumpu/ROBODoc/releases/download/v4.99.44/robodoc-4.99.44.zip
unzip robodoc-4.99.44.zip && cd robodoc-4.99.44

# 应用补丁
patch -p1 < patches/0001-Source-troff_generator.c.patch
patch -p1 < patches/0002-config.guess.patch
patch -p1 < patches/0003-config.sub.patch
patch -p1 < patches/0004-configure.patch

# 配置 / 编译 / 安装
./configure --prefix=$HOME/usr/local
make -j1
make install DESTDIR=$HOME/tmp/stage
```

## 补丁说明

| 补丁 | 目的 |
|------|------|
| `0001-Source-troff_generator.c.patch` | `troff_generator.c` 使用 SysV 遗留头 `<sys/unistd.h>`，OHOS（clang/musl）无此头，改为标准 `<unistd.h>` |
| `0002-config.guess.patch` | 2018-02-24 版 config.guess 无 HarmonyOS 分支，补入 `*:HarmonyOS:*:*` 识别，输出 `aarch64-unknown-linux-ohos` |
| `0003-config.sub.patch` | config.sub 补 `linux-ohos` 内核-OS 组合，使 `aarch64-unknown-linux-ohos` 三元组通过校验 |
| `0004-configure.patch` | HMDFS 新目录强制 setgid，`umask 077 && mktemp -d` 得到 `drwx--S---`(2700) 导致 config.status 写 `subs1.awk` 报 Permission denied；改为 `umask 022` |

> 说明：所有补丁均为可移植性修改，未引入平台宏；不使用 `--build/--host` 绕过平台探测（E007）。

## 遇到的问题

### 问题1: config.guess 无法识别 HarmonyOS

**现象**: `configure: error: cannot guess build type; you must specify one`
（`config.guess: unable to guess system type`）。

**原因**: 上游 config.guess 时间戳为 2018-02-24，`uname -s` 返回 `HarmonyOS`
不匹配任何已知系统分支。

**解决**: 补 `*:HarmonyOS:*:*` 分支输出 `aarch64-unknown-linux-ohos`，并补 config.sub。
注意老式 config.guess 的分支须以 `echo ...; exit` 结束，否则会 fall through 到
“unable to guess”。

### 问题2: config.status 报 Permission denied

**现象**: `./config.status[754]: can't create ./confXXXXXX/subs1.awk: Permission denied`
→ `could not setup config files machinery`。

**原因**: HMDFS 对新目录强制 setgid；`umask 077 && mktemp -d` 生成 2700 目录，
即使属主也无法在其中创建文件。

**解决**: 将 configure 中两处 `umask 077` 改为 `umask 022`（E129）。configure 内的
代码会写进生成的 config.status，故一处修改同时生效。

### 问题3: make 触发 automake maintainer 重建

**现象**: `WARNING: 'automake-1.16' is missing on your system.` → make 失败。

**原因**: 发布包内 `makefile.am` 与 `makefile.in` 时间戳相同，make 判定
`makefile.in` 过期而尝试调用 automake（OHOS 无 automake）。

**解决**: 构建时抬高 `makefile.in` / `config.h.in` 的 mtime，跳过重建（不改内容）。

### 问题4: 缺少 `<sys/unistd.h>`

**现象**: `troff_generator.c:33:10: fatal error: 'sys/unistd.h' file not found`。

**原因**: SysV 遗留头文件，主流 glibc 亦不提供，OHOS（clang/musl）无此头。

**解决**: 改为标准头 `<unistd.h>`。

## 测试结果

详见 [test-report.md](./reports/test-report.md)

| 测试项 | 结果 |
|--------|------|
| `robodoc --version` | ✅ 4.99.44 |
| `robodoc --config` 三元组 | ✅ aarch64-unknown-linux-ohos |
| HTML 文档抽取 | ✅ |
| ASCII 文档抽取 | ✅ |
| robohdrs 可运行 | ✅ |
| 上游 `make check` | ⚠️ 空目标（上游无自动化测试，见 MANIFEST.yml） |
| test_package（消费者 + 鸿蒙特有） | ✅ 10/10 |

## 验证安装

```bash
$ robodoc --version
4.99.44
$ robodoc --config
ROBODoc version 4.99.44
Configuration:
  Compiled using ./configure; make;
  Compiler flags -fPIC -O2
  Compiled for aarch64-unknown-linux-ohos
  Prefix for excutable and configuration <prefix>
```

## 经验总结

1. Autotools + HarmonyOS 的三件套：config.guess（平台识别）、config.sub（三元组）、
   configure/config.status（HMDFS umask）。
2. 优先使用上游官方 release 资产；仓库 tag 归档可能缺 `.gitignore` 忽略的生成文件。
3. 上游 `make check` 为空目标时，务必在 MANIFEST.yml 中附清点证据。

## 参考资料

- ROBODoc 手册：https://github.com/gumpu/ROBODoc/blob/master/Docs/manual.html
- 知识条目 E007（config.guess/config.sub）、E129（HMDFS umask）
