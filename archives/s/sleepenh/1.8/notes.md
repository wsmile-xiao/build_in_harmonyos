# sleepenh 1.8 适配笔记

## 编译环境
- 构建系统: makefile（上游小型裸 Makefile：`CC = gcc`、`CFLAGS = -std=gnu11 -Wall -Wextra -O2 $(EXTRA_CFLAGS)`，
  靠 GNU make 内置 `%: %.c` 规则一步编译链接；版本串由 `git describe` 生成；无 configure）
- 编译日期: 2026-09-23
- 编译器: OHOS SDK clang 15.0.4（`aarch64-unknown-linux-ohos`，经 `/data/service/hnp/bin/clang`），sysroot 为 OHOS musl
- 构建机: x86_64 runner 交叉编译；目标 aarch64-linux-ohos（profile `ci/conan/profiles/ohos-aarch64`，build_type=Release）
- 状态: built（conan-verify G0-G4 通过，W3 本地 conan create 通过）

## 源码来源

- 任务指定的上游仓库为 salsa 上的 `debian/sleepenh`（Debian 原生维护，gbp 布局）。取其 `upstream/1.8` 标签的归档：
  该分支是纯上游源码（无 `debian/` 目录），git tree `944af8d2f58bfb6895b729985b5552e66b0b237f` 与作者仓库
  （codeberg `nsc/sleepenh`，`debian/watch` 与 `debian/upstream/metadata` 所指的上游）的 `1.8` 标签完全相同。
- 归档 sha256 `6bb42f569bfdb9a61e10d7c0fa0623aa644b107a54a15f61c99b48b9091955fa`，两次独立下载一致；
  内含 5 个文件：`.gitignore` / `Makefile` / `changelog` / `sleepenh.1` / `sleepenh.c`。

## 编译步骤

1. 手工打通（临时目录）：`make sleepenh CC=/data/service/hnp/bin/clang EXTRA_CFLAGS=-O3 CPPFLAGS=-DNDEBUG vcsversion='\"1.8\"'`
   首次失败于 `program_invocation_short_name` 未声明（问题 1），打补丁后编译零告警（`-Wall -Wextra`）。
2. 配方 `build()`：`apply_conandata_patches` 后由 `AutotoolsToolchain(self).vars()` 取 `CC`、`CFLAGS`、`CPPFLAGS`、`LDFLAGS`，
   以 make 命令行变量传入（R33，不读裸 shell 变量），W3 实际命令：
   `make -j1 CC=/data/service/hnp/bin/clang EXTRA_CFLAGS=-O3 CPPFLAGS=-DNDEBUG LDFLAGS='' vcsversion='\"1.8\"' sleepenh`
   → `clang -std=gnu11 -Wall -Wextra -O2 -O3 -DVCSVERSION=\"1.8\" -DNDEBUG sleepenh.c -o sleepenh`
   - 工具链 CFLAGS 走上游的 `EXTRA_CFLAGS` 钩子（1.7 起提供）：若在命令行直接给 `CFLAGS`，会连同目标专属的
     `sleepenh: CFLAGS += -DVCSVERSION=...` 一起被覆盖，`VCSVERSION` 未定义导致编译失败；
   - 只构建 `sleepenh` 目标：`all` 还会用 gzip 生成 `sleepenh.1.gz`，man 页直接按原文件打包，构建不依赖 gzip。
3. `package()`：上游 `install` 目标写死 `$(DESTDIR)/usr/bin`、`$(DESTDIR)/usr/share/man/man1`，与 Conan 布局不符，
   改为把 `sleepenh` 复制到 `bin/`、`sleepenh.1` 复制到 `share/man/man1/`；源码包没有 COPYING，
   把 sleepenh.c 头部注释（GPL-2.0-or-later 许可声明）写入 `licenses/LICENSE`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `sleepenh.c:97:3: error: use of undeclared identifier 'program_invocation_short_name'` | glibc 扩展变量。SDK 自带 llvm-nm 实测：sysroot 头文件无任何声明；`libc.so` 动态符号表只导出 `__progname`；`libc.a` 却有弱别名 `V program_invocation_short_name` / `V program_invocation_name`。只补 `extern` 声明时，动态链接报 `ld.lld: error: undefined symbol: program_invocation_short_name`，`-static` 链接则成功 | 补丁在 `main()` 开头从 `argv[0]` 取 basename 存入 `progname`（glibc 该变量的值即 argv[0] 的 basename），`usage()` 改用它；纯 C、无平台宏。知识库 E493 签名只有 `program_invocation_name`、推荐 `__OHOS__`+`__progname`（违反 R8）；已沉淀草稿 E6402（静态/动态导出不对称与静态验证假阳性） |
| 2 | 版本串为空：上游默认构建 `-DVCSVERSION=''`，`--version` 输出 `sleepenh `，同时打印 `fatal: not a git repository` | `vcsversion` 由 `git describe --dirty` 生成，源码归档没有 `.git` | 与 Debian `debian/rules` 相同，在 make 命令行传 `vcsversion='\"1.8\"'`（取 `self.version`）；test_package F1 校验 `sleepenh 1.8`。同类问题已有草稿 DRAFT-libfirm-1.22.0-makefile-version-header-tarball 覆盖，不另立条目 |
| 3 | 上游 Makefile 写死 `CC = gcc` | 交叉构建须用 OHOS clang | make 命令行变量覆盖（命令行赋值优先于 Makefile 赋值），值取自 AutotoolsToolchain（R33），不改 Makefile |
| 4 | `install` 目标路径写死 `/usr` | 上游按 Debian 打包习惯编写 | `package()` 直接 copy 二进制与 man 页 |
| 5 | x86 runner 无法运行交付的动态产物 | 构建机没有 OHOS 的 `/lib/ld-musl-aarch64.so.1`，binfmt qemu 启动即报 `Could not open '/lib/ld-musl-aarch64.so.1'` | 功能验证改用同源、同标志的 `.o` 静态重链副本经 qemu 实跑；test_package 在异架构主机上把功能层如实记为 SKIPPED |
| 6 | `init-build` 把构建系统判成 `autotools`，`conan-init` 生成 autotools 配方与 CMake 空壳 test_package | 工具侧判定问题（已写入 SKILL_FEEDBACK） | 按实际的裸 Makefile 手写配方，test_package 改为 Python 功能测试 |

## 源码修改

`patches/0001-sleepenh.c.patch`（`refresh-patch --auto` 生成，+7/-1，`patch --dry-run -p1` 干净；无任何平台宏）：

1. 新增 `static const char *progname = "sleepenh";`（argv[0] 为空时的默认名）；
2. `main()` 开头：`argv[0]` 非空时取最后一个 `/` 之后的部分赋给 `progname`；
3. `usage()` 的 `program_invocation_short_name` 改为 `progname`。

行为与 glibc 版一致：以任意路径调用时 usage 行都显示 basename（test_package F2 以绝对路径调用验证）。

## 依赖版本

- 无 Conan 依赖（仅 libc）；W0 核验：配方 `requirements()` 为空，无需探测制品仓；`sleepenh/1.8` 制品仓尚无同版本（L0j）。
- 工具链：OHOS SDK clang 15.0.4、ld.lld、musl sysroot。

## 上游测试清点（R51）

- 清点：源码归档共 5 个文件、无子目录；无 `tests/` 目录（0 个）、无测试脚本、无 ctest/pytest 注册（0 个）；
  Makefile 目标只有 `all` / `sleepenh` / `%.1.gz` / `clean` / `distclean` / `install`，`make -n check`、`make -n test`、
  `make -n tests` 均报 `No rule to make target`；Debian 打包（tag `debian/1.8-1`）也没有 `debian/tests`。
  **上游测试用例数 N = 0**，可运行数 N′ = 0，通过率不适用。
- 补全：test_package 的 `test_sleepenh.py` 共 12 项检查——A1-A4 产物检查（ELF64 AArch64 / PIE /
  `PT_INTERP=/lib/ld-musl-aarch64.so.1` / man 页，所有主机）+ F1-F8 功能检查（版本串、usage 程序名、无参数退出码 10、
  inf/nan 退出码 12、过期起点、--warp 折返、真实 0.3 s 休眠由 SIGALRM 唤醒、链式调用无累计漂移；
  退出码 + stdout 精确比对 + 计时窗口，每次运行 30 s 超时）。aarch64 CI worker 上功能层必跑。

## 验证结果

```bash
# conan-verify（G0-G4 PASS）/ W3 conan create，test_package 输出（x86_64 runner）：
[ok] A1 ELF64 little-endian EM_AARCH64 image
[ok] A2 position-independent executable (ET_DYN)
[ok] A3 PT_INTERP is /lib/ld-musl-aarch64.so.1 (found /lib/ld-musl-aarch64.so.1)
[ok] A4 share/man/man1/sleepenh.1 is the upstream man page
[skip] F1-F8 not run: this x86_64 host cannot execute the aarch64 OHOS image (aarch64-binfmt-P: Could not open '/lib/ld-musl-aarch64.so.1': No such file or directory)
RESULT: artifact checks 4/4 passed, functional checks 0/8 run (SKIPPED)

# 交付产物安全属性（llvm-readelf）：GNU_STACK RW（NX）、GNU_RELRO + BIND_NOW（full RELRO）、FLAGS_1 NOW PIE、NEEDED libc.so

# 功能验证：Conan 构建目录中已打补丁的 sleepenh.c，按 conan create 相同标志
# clang -std=gnu11 -Wall -Wextra -O2 -O3 -DVCSVERSION="1.8" -DNDEBUG -c 后 -static 重链，qemu-aarch64 实跑 test_sleepenh.py：
F1-F8 8/8 passed（F7 实测 0.320 s；A2/A3 对静态副本不适用，记 FAIL 属预期，不代表交付产物）

# 消融对照（同法静态重链，qemu-aarch64 实跑）：
#   上游默认 vcsversion（git describe，无 .git）   -> -DVCSVERSION=''，F1、F3 失败（版本串为空，6/8）
#   未打补丁 + 仅补 extern 声明                   -> 动态链接 ld.lld undefined symbol；-static 链接成功且 F2 通过（静态验证假阳性）
#   完整配方（补丁 + vcsversion）                 -> F1-F8 全部通过
```

**说明**：x86 runner 上交付的动态产物本身未实跑（缺 OHOS loader），上面的功能结果来自同源同标志的
静态重链副本，不等于交付产物已实跑；交付产物的功能层由 aarch64 CI worker 上的 test_package 强制执行。
补丁对动态链接的必要性由 conan create 链接通过（仅补 extern 时链接失败）来验证。

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/sleepenh` | ELF64 aarch64 PIE，动态链接 OHOS musl（`libc.so`） |
| `share/man/man1/sleepenh.1` | 上游 man 页（未压缩） |
| `licenses/LICENSE` | sleepenh.c 头部的 GPL-2.0-or-later 许可声明 |

## 注意事项

- `--warp` 计算 `int tmp = (now - it) / st;`：INITIALTIME 距今超过约 `INT_MAX * TIMETOSLEEP` 秒时溢出（C 未定义行为，
  aarch64 与 x86 结果不同）——上游既有行为，与平台无关，未改动；test_package F6 使用 10.2 s 前的起点（k = 20）。
- 定时精度：`setitimer()` 的微秒部分按 `(long)(sleep_time * 1e6) % 1000000` 截断，可能比目标早约 1 µs 唤醒，
  程序仍输出理论结束时间；F7 的计时下限因此取 0.29 s。
---

**编译结束**: 2026-09-23 21:27
**最终状态**: built
