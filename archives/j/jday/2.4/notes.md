# jday 2.4 适配笔记

## 编译环境
- 构建系统: autotools（configure + automake 1.x + libtool 1.5.6，均为 2004/2005 年版本）
- 编译日期: 2026-09-21
- 编译器: OHOS NDK clang（aarch64-unknown-linux-ohos-clang）
- 目标: aarch64-linux-ohos（armv8）
- 状态: published（conan-verify 全门禁通过，W3 本地 CI exit_code=0）
- 依赖: 无（仅 libc）

## 上游测试清点（R51 第一步）

| 项 | 内容 |
|---|---|
| 测试入口 | `Makefile.am` 的 `check:` 目标 → `$(srcdir)/RunTest` |
| 自动判定用例数 | **26**（`RunTest` 内 `TestJD` ×13 + `TestJ2D` ×13，脚本自带 PASS/FAIL 统计与退出码） |
| 非判定脚本 | `Testdbd`：循环调用 `dbd` 打印 121 组日期差，无期望值、无断言，不计入通过率 |
| 不适用脚本 | `JdayTest.pl`：测试随包分发的 Perl 模块 `CalDate.pm`，测试对象是 Perl 实现而非本次适配的 C 产物 |
| 无 ctest/pytest | 项目无 CMake/Python 测试注册 |

清点命令：

```bash
grep -c '^TestJD \|^TestJ2D ' RunTest     # 26
sed -n '/^check:/,+2p' Makefile.am        # check: $(srcdir)/RunTest
```

## 编译步骤

```bash
NDK=/opt/command-line-tools/sdk/default/openharmony/native
export CC=$NDK/llvm/bin/aarch64-unknown-linux-ohos-clang
export AR=$NDK/llvm/bin/llvm-ar RANLIB=$NDK/llvm/bin/llvm-ranlib

# config.guess / config.sub 打补丁后：
./configure --prefix=/root/usr/local --host=aarch64-linux-ohos \
            --disable-shared --enable-static
make
make install DESTDIR=<staging>
```

源码本身零修改：`make` 一次通过，只有 3 条 `-Wdeprecated-non-prototype` 警告
（K&R 风格 `main( argc, argv )`，C17 下仍可编译）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `./config.sub aarch64-linux-ohos` → `machine 'aarch64-linux' not recognized`，configure 直接失败 | 随包 config.sub 时间戳 2004-08-29，早于 aarch64 架构（2012）与 OHOS，既无 `aarch64` CPU 项也无 `linux-ohos` 内核-OS 组合 | `patches/0002-config.sub.patch`：三处列表各加一项（KERNEL-OS 组合加 `linux-ohos*`、basic_machine 加 `aarch64`、OS 列表加 `-linux-ohos*`） |
| 2 | 鸿蒙 PC 真机上 `config.guess` 报 `unable to guess system type` → `configure: error: cannot guess build type`（CI #57604 实测） | 真机 `uname -s` 返回 **HarmonyOS**（`uname -r` = `HongMeng Kernel 1.12.0`），2004 年的 config.guess 无此分支；落到兜底逻辑后又要往 `$TMPDIR` 写 `dummy.c` 做编译探测，在 HMDFS 上 `Permission denied`，于是彻底失败。知识图谱 **E007** 正是此模式 | `patches/0001-config.guess.patch`：新增 `aarch64:HarmonyOS:*:* \| aarch64:OHOS:*:*` 分支，直接输出 `aarch64-unknown-linux-ohos`，在 case 命中即 `exit`，不再走需要写临时文件的兜底路径 |
| 3 | conan 不为本配方注入交叉三元组 | profile 的 host/build 同为 `os=OHOS`，`cross_building()` 为 False，AutotoolsToolchain 因此不生成 `--host/--build` | 配方在 `settings.os == "OHOS"` 时显式追加 `--host=aarch64-linux-ohos`；**不**写死 `--build`，交给已打补丁的 config.guess 探测——鸿蒙真机探到 `aarch64-unknown-linux-ohos`（与 host 规范化值相同 → 原生编译）、x86_64 交叉构建机探到 `x86_64-unknown-linux-gnu`（→ 交叉编译），两种构建机各走正确路径 |
| 4 | 真机上 `config.status` 报 `./confstatXXXXXX/subs.sed: Permission denied`，Makefile 生成失败（CI 第 2 轮实测） | autoconf 2.59 的 config.status 用 `mktemp -d -q "./confstatXXXXXX"` 建临时目录，该调用把权限**硬编码为 0700**（不受 umask 影响）；HMDFS 存在 UID 映射（目录属主 UID ≠ 进程 UID）且会附加 setgid 位，于是 0700 目录对本进程不可写。知识图谱 **E011** 记录了同一现象 | `patches/0003-configure.patch`：去掉 `mktemp` 分支，只保留原有的 `mkdir` 回退分支并将其 `umask 077` 改为 `umask 000`，让临时目录以 0777 创建，不依赖 UID 匹配。目录仍在构建目录内、仍由原有 `trap ... rm -rf` 清理，作用域不变 |
| 5 | 真机上 `make -j20` 报 `jobserver mkfifo: Operation not permitted` → `No targets specified and no makefile found`（CI 第 2 轮实测） | GNU Make 4.4+ 默认用 FIFO jobserver，HMDFS 不支持 `mkfifo`；conan 默认按 CPU 数并发。知识图谱 **E074 / E525** 记录此模式 | 配方 `generate()` 注入 `MAKEFLAGS=-j1`（覆盖嵌套 make），`build()` / `package()` 显式 `make(args=["-j1"])` / `install(args=["-j1"])`。参照先例 `archives/a/at/3.2.5`、`archives/a/ace/8.0.5` |
| 6 | x86_64 构建机上无法执行交付产物做功能验证 | 产物为动态链接 aarch64-OHOS ELF，`interpreter /lib/ld-musl-aarch64.so.1` 在构建机不存在（E544）；qemu binfmt-P 模式下 `QEMU_LD_PREFIX` 不生效 | 用同源 `.o` 加 `-static` 重链一份副本，在 `qemu-aarch64` 下跑完整 `RunTest`；test_package 的测试程序在 `CMAKE_SYSTEM_NAME=HarmonyOS` 时同样静态链接，使 `conan create` 的 test 阶段可在构建机上真实执行 |

## 源码修改

仅构建系统辅助脚本，**不含任何平台宏**，不触碰 C 源码：

| 补丁 | 文件 | 规模 | 说明 |
|---|---|---|---|
| `0001-config.guess.patch` | `config.guess` | +6/-0 | 新增 `aarch64:Linux:*:*`（aarch64 Linux 构建机）与 `aarch64:HarmonyOS:*:* \| aarch64:OHOS:*:*`（鸿蒙 PC 真机，输出 `aarch64-unknown-linux-ohos`）两个分支 |
| `0002-config.sub.patch` | `config.sub` | +3/-3 | 识别 `aarch64` 与 `linux-ohos` |
| `0003-configure.patch` | `configure` | +1/-5 | config.status 的临时目录改用 `mkdir` + `umask 000`，替掉权限硬编码 0700 的 `mktemp -d`（HMDFS UID 映射下不可写，E011） |

> `0003` 改的是上游 tarball 里分发的 `configure`（autoconf 2.59 生成物）。问题出在 autoconf
> 自身的 config.status 模板代码，`configure.ac` 层面无从修复；仓库内有同类先例
> （如 `archives/a/aalib/1.4p5/patches/0002-configure-lt-target.patch`）。

补丁的真机行为在本地用 mock `uname`（复刻 CI #57604 日志里的真机输出）验证过：

```bash
$ PATH=/tmp/mock-bin:$PATH ./config.guess      # 模拟 uname -s=HarmonyOS, -m=aarch64
aarch64-unknown-linux-ohos
$ ./config.sub aarch64-unknown-linux-ohos      # build 规范化
aarch64-unknown-linux-ohos
$ ./config.sub aarch64-linux-ohos              # host 规范化（两者相同 → 真机走原生编译）
aarch64-unknown-linux-ohos
$ ./config.guess                               # x86_64 构建机不受影响
x86_64-unknown-linux-gnu
```

## 依赖版本

无第三方依赖；`requirements()` 为空，`conan download` 无需探测任何包。

## 验证结果

```bash
# 1) 上游用例（R51 第二步）——qemu-aarch64 执行同源 .o 静态重链副本
$ sh ./RunTest
./jday 1970 1 1 0 0 0 -> 2440587.500000 - OK
./j2d  2440587.500000 -> 1970-01-01 00:00:00 - OK
...
TEST COMPLETE: Test count: 26, Test success: 26, Test failed: 0
OK - ALL TESTS PASSED OK

# 2) 交付产物形态
$ file <pkg>/bin/jday
ELF 64-bit LSB pie executable, ARM aarch64, interpreter /lib/ld-musl-aarch64.so.1

# 3) test_package（conan create 内）
jday test_package: all 7 assertions passed
```

> **验证边界（如实说明）**：上述 26/26 是在 **x86_64 构建机 + qemu-aarch64 + 静态重链副本**
> 上取得的，代码路径与交付产物同源（同一批 `.o`），但**不等于交付的动态链接产物已在
> 鸿蒙真机上实跑**。真机侧执行由 CI 的 `conan create`（test_package 阶段）覆盖。

## 交付物

| 路径 | 说明 |
|------|------|
| `bin/jday` | 日历日期 → 儒略日 |
| `bin/j2d` | 儒略日 → 日历日期 |
| `bin/dbd` | 计算两个儒略日之间的天数 / 月数 |
| `lib/libjday.a` | `JulDate()` / `CalDate()` 转换库（静态） |
| `include/jday.h` | `UTinstant` 结构与两个 API 声明 |
| `lib/pkgconfig/jday.pc` | pkg-config 描述 |
| `man/man1/jday.1` | man 手册 |

## 注意事项

- **固定静态库**：上游 `configure.ac` 自注 "default will be to build static library
  since it is so tiny"；随包 libtool 1.5.6 也没有 `linux-ohos` 的共享库规则，因此配方不
  提供 `shared` 选项，直接 `--disable-shared --enable-static`。`libjday` 与系统库不同名，
  不存在 R26 的 `/lib`、`/lib64` 污染面。
- `make install` 会额外装出 libtool 存根 `lib/libjday.la`（内含构建机路径），配方在
  `package()` 中删除。
- man 页安装到 `man/man1`（老 autotools 默认）而非 `share/man/man1`，未做改动以保持与上游一致。
---

**编译结束**: 2026-09-24 03:56
**最终状态**: published
