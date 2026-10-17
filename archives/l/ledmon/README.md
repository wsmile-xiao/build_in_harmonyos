# ledmon 0.97 for HarmonyOS

## 概述

ledmon 是 Intel 维护的 SES/SMP  enclosure LED 管理守护进程，附带命令行工具 `ledctl`。
本目录记录其在 HarmonyOS / OpenHarmony (aarch64, musl) 上的构建与验证情况。

## 软件信息

| 项目 | 值 |
|------|-----|
| 名称 | ledmon |
| 版本 | 0.97 |
| 下载地址 | https://github.com/intel/ledmon/archive/refs/tags/v0.97.tar.gz |
| 上游仓库 | https://github.com/intel/ledmon |
| 构建系统 | autotools（tag 归档无生成物，配方内 `autoreconf -fi` 自举） |

## 鸿蒙环境

| 项目 | 值 |
|------|-----|
| 系统版本 | HarmonyOS（HongMeng Kernel，aarch64） |
| 架构 | aarch64 |
| 编译器 | clang / clang++ (LLVM) |
| C 库 | musl（OHOS 工具链 sysroot） |
| 交叉三元组 | `--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-ohos` |

## 产物

| 产物 | 说明 |
|------|------|
| `bin/ledmon` | LED 监控守护进程（设计为 root 运行） |
| `bin/ledctl` |  enclosure LED 控制 CLI |

动态链接 `libpci` / `libudev` / `sgutils2` / `librt`。OHOS 上执行前需按设备 XPM 要求自签，
运行期由 musl 加载器需要 `LD_LIBRARY_PATH`（`VirtualRunEnv` 注入，配方不硬编码路径）。

## 编译步骤

```bash
# 1. 下载源码
wget https://github.com/intel/ledmon/archive/refs/tags/v0.97.tar.gz
tar -xzf v0.97.tar.gz && cd ledmon-0.97

# 2. 应用补丁（见 patches/，strip:1）
for p in patches/*.patch; do patch -p1 < "$p"; done

# 3. 自举 autotools（GitHub tag 归档不含 configure）
autoreconf -fi

# 4. 配置（交叉；cache 变量见 conanfile.py generate()）
./configure --build=aarch64-unknown-linux-gnu \
            --host=aarch64-unknown-linux-ohos \
            --prefix=/usr

# 5. 编译安装
make -j2 && make install
```

## 补丁说明

| 补丁 | 修改文件 | 现象与根因 |
|------|----------|------------|
| `0001-ses-h-use-linux-types.patch` | `src/ses.h` | OHOS sysroot 无 `asm/types.h`；`__u8/__u32` 由 `linux/types.h` 承载 |
| `0002-drop-doc-subdir.patch` | `Makefile.am` | `doc/` 用 `pod2man` 生成 man 页，CI worker 无 perl 保证；纯文档产物，从 `SUBDIRS` 去掉 |
| `0003-am-cflags-use-top-srcdir.patch` | `configure.ac` | `AM_CFLAGS` 的 `-I../config` 在 VPATH 构建下相对构建目录解析 → `'config.h' file not found`；改 `-I$(top_srcdir)/config` |
| `0004-utils-h-include-sys-types.patch` | `src/utils.h` | OHOS musl 的 `ssize_t` 仅由 `sys/types.h` 声明（glibc 靠传递包含掩盖）→ `unknown type name 'ssize_t'` |
| `0005-ibpi2value-sentinel-explicit-value.patch` | `dellssd.c`/`vmdssd.c`/`amd_ipmi.c`/`npem.c` | `{IBPI_PATTERN_UNKNOWN}` 省略尾字段在 clang 下触发 `-Werror=missing-field-initializers`；补显式 `, 0`，语义不变 |
| `0006-onexit-compat-for-musl.patch` | `src/utils.{c,h}`、`src/ledctl.c` | `on_exit(3)` 为 glibc/BSD 专有，OHOS sysroot 无该符号 → `undefined symbol: on_exit`；以 `atexit` + 记录表补兼容实现（`#if !defined(__GLIBC__)` 守卫，保留 handler 参数与 LIFO 顺序） |

## 遇到的问题

1. **`undefined symbol: rpl_malloc`** —— `AC_FUNC_MALLOC` 交叉编译下无法运行探测，改写成 gnulib
   `rpl_malloc`；预置 `ac_cv_func_malloc_0_nonnull=yes` 跳过替换（`malloc(0)` 返回非 NULL 本就是 musl 语义）。
2. **`AX_CHECK_PROG([gcc])` 失败** —— 该项只查 PATH 上是否存在名为 `gcc` 的可执行文件，OHOS 交叉工具链
   不提供该名字（实际编译一律用 `$(CC)`）；预置 `ac_cv_prog_PROG_gcc=yes`。
3. **`libpci.pc` 缺失** —— conan 的 `pciutils` 包未设 `pkg_config_name`，`PkgConfigDeps` 落盘 `pciutils.pc`，
   而 configure 探测模块名是 `libpci`；`generate()` 内同内容别名一份 `libpci.pc`。
4. **`/dev/shm` 上的锁失效（平台行为，非适配引入）** —— `amd_sgpio.c` 在 `shm_open` 文件上 `flock`
   实测返回 `EACCES(13)`，且上游不检查返回值。详见 `0.97/notes.md` 与版本目录的知识草稿。

## 测试结果

五维测试账本（静态 1 / 注册 0 / 执行 0 / 跳过 1 / 消费者 5）见
[0.97/notes.md](./0.97/notes.md)；逐用例状态另存本地 `0.97/reports/test-report.md`。

| 测试项 | 结果 |
|--------|------|
| `ledctl --version` / `--help` | ✅ |
| `ledmon --version` / `--help` | ✅ |
| 非 root 执行特权命令被拒（`Only root can run this application.`） | ✅ |
| 上游 `test/exercise_ledctl.py` | ⚠️ 未执行：需 root + SAS SES 背板 + 硬编码 `/usr/sbin/ledctl` |
| 守护进程整机运行 | ⚠️ 未验证：设备无 root、无 SES enclosure |

## 验证安装

```bash
conan create archives/l/ledmon/0.97 -pr:h=ci/conan/profiles/ohos-aarch64 --build=missing
conan install --requires=ledmon/0.97@ohpcd/stable -pr:h=... --deployer=full_deploy
# 运行期（musl 需显式 LD_LIBRARY_PATH）
ledctl --version    # 期望输出 LED Control Application 0.97
```

## 经验总结

1. GitHub tag 归档不含 autotools 生成物时，`autoreconf -fi` + `tool_requires(automake, pkgconf)` 是必需路径；
   对 `configure` 的 umask 修补必须排在自举之后。
2. glibc 专有接口（`on_exit`）在 musl 上缺失时，兼容层要保留原有语义（参数、LIFO 顺序），
   并如实记录无法保留的部分（退出状态日志）。
3. "只用 `/dev/shm` 下的文件"不等于免疫 OHOS 对虚拟目录的只写限制——锁语义同样会被摘掉。

## 参考资料

- 上游 README/`ledctl` 手册：<https://github.com/intel/ledmon>
- 版本级适配记录：`0.97/notes.md`
