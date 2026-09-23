# gnuspool for HarmonyOS

## 概述

GNUspool 1.8 在 HarmonyOS/OpenHarmony (aarch64) 上的编译指南与测试记录。
GNUspool 是一套打印队列系统（补充/替代传统 lpd），提供透明的网络共享打印与作业管理。

本适配按 `--without-network` 构建：作业提交/队列管理/记账等本地能力可用，多机远程
复制与远程打印需要后续完成网络相关代码的 musl 适配，不在本次范围内。

## 软件信息

| 项目 | 值 |
|------|-----|
| 名称 | gnuspool |
| 版本 | 1.8 |
| 下载地址 | https://ftp.gnu.org/gnu/gnuspool/gnuspool-1.8.tar.gz |
| 官方文档 | https://www.gnu.org/software/gnuspool/ |

## 鸿蒙环境

| 项目 | 值 |
|------|-----|
| 目标平台 | OpenHarmony / HarmonyOS PC（aarch64，armv8） |
| 编译器 | clang / clang++ 15（OHOS SDK） |
| 构建系统 | autotools（上游自带 configure） |
| Conan | 2.29.1（OHOS 适配版） |
| profile | `ci/conan/profiles/ohos-aarch64` |

## 构建

```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

配方内的关键处理（详见 `1.8/notes.md`）：

- `configure` 前移除 configure 内 `umask 077` 包裹（HMDFS，E011/E114），并把 SysV
  shm/msgq 的致命探测分支替换为保守回退（`--enable-using-mmap --enable-using-flock`）；
- 编译宏：`-D_GNU_SOURCE -DHAVE_TERMIO_H -DSIGCLD=SIGCHLD -fcommon`，并把
  `-I/-L`（ncurses）同时放进 `CCFLAGS`（gnuspool 的 Makefile 不认 CPPFLAGS/LDFLAGS）；
- configure 后把 Makefile 中裸调用的 `libtool` 补 `--tag=CC`；
- 打包：可执行文件 → `bin/`，共享库 → `lib/`，帮助数据 → `share/gnuspool/help/`。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| ncurses | 6.6 | 全屏工具（spq/pmenu 等）所需；制品仓已发布 |

## 功能验证

```bash
# 消费者测试（conan create 的 test() 阶段自动执行）：
# 以使用者身份运行随包发布的 gspl-cjlist，断言用法输出并确认 help 数据可被工具找到
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64

# 手工验证（设备/目标机）
export LD_LIBRARY_PATH=<pkg>/lib
<pkg>/bin/gspl-cjlist        # 打印用法并退出（用法错误码 100）
```

上游无自动化测试套件（源码树无 `test/` 目录、`Makefile` 无 `check`/`test` 目标），
故消费者测试承载本次适配的功能验证；清点证据见 `1.8/test_package/MANIFEST.yml`。

## 参考

- [官方文档](https://www.gnu.org/software/gnuspool/)
- [源码](https://ftp.gnu.org/gnu/gnuspool/)
