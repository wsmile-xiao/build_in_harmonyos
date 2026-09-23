# termutils 2.0 适配笔记

## 编译环境
- 构建系统: autotools（1995 年 autoconf 生成，仅支持 `--prefix`）
- 编译日期: 2026-09-13
- 编译器: clang 15.0.4（OHOS aarch64 工具链）
- 状态: built
- 任务号: 13409（开源鸿蒙PC专项积分赛-依赖）
- 分支: feat/termutils-2.0

## W0 依赖发布检查
- configure.in 仅检查系统头文件（string.h/termios.h/sgtty.h/unistd.h）与 libc
  函数（tcgetattr/strerror/bsearch），**无任何外部库依赖**（termcap 能力读取
  由源码树内 bundled termcap.c/tparam.c 提供）。
- 依赖清单为空 → 无需依赖发布检查，R36 拓扑约束不适用。

## W0b 历史经验核验
- 归档树 archives/t/ 无 termutils（本任务为首适配），无历史 notes.md 可参照。
- 参照了同仓库已验证先例 termcap 1.3.1 的老 configure 处理模式
  （`sh configure --prefix=<package_folder>` 直调、package() 直拷产物、E490
  exec-bit 规避）。

## 编译步骤

```bash
# 探索编译（设备原生 OHOS aarch64）
CC=clang CFLAGS="-std=gnu89 -g -O2" sh configure --prefix=<prefix>
make -j1
# 冒烟验证
TERM=gtu TERMCAP='gtu:co#80:li#24:' ./tput co   # → 80
./tabs --version                                 # → GNU tabs version 2.0
```

配方构建（conan create 路径）：`AutotoolsToolchain` 注入 `-std=gnu89`；
`build()` 以 `sh configure --prefix=<package_folder>` 直调后 `autotools.make(-j1)`；
`package()` 直拷 tput/tabs 到 bin/（上游 Makefile 无 DESTDIR 支持）。

## 上游测试（R51 四维账本）

| 维度 | 数值 | 说明 |
|---|---|---|
| N_static（上游静态声明） | 0 | 无 tests/ 目录、Makefile.am 无 check 目标/TESTS 变量、configure.in 无测试宏（证据见 test_package/MANIFEST.yml） |
| N_registered | 0 | 无 make check 可注册 |
| N_executed | 0 | 无上游套件 |
| N_consumer（新增消费者测试） | 1（断言 3 项） | test_package/test_termutils.sh，执行包内 tput 断言 co=80/li=24/未知能力退出码 4 |

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | tparam.c 编译错误 `conflicting types for 'memcpy'` | 源码第 25 行先 `#define bcopy(s,d,n) memcpy((d),(s),(n))` 再 include `<string.h>`，宏泄漏进 OHOS sysroot strings.h 的 `void bcopy(...)` 声明 | 补丁 0001：把 `#include <string.h>` 挪到宏定义之前（平台无关，glibc/musl 通吃） |
| 2 | 默认 `cc` 不存在，make 报 `cc: No such file or directory` | 1995 autoconf 默认 CC=cc；设备只有 clang | configure 时由 conan 工具链环境提供 CC=clang（AutotoolsToolchain） |
| 3 | clang 15 报 K&R 函数定义错误（tparam1 等） | clang >= 15 默认 gnu17 拒收无原型 K&R 定义 | `tc.extra_cflags = ["-std=gnu89"]` |
| 4 | `make install DESTDIR=...` 装到了 prefix 而非 staging | 1995 Makefile 无 DESTDIR 支持 | 配方 `--prefix=<package_folder>` + package() 直拷产物（termcap 1.3.1 同款处理） |
| 5 | `tabs 8` 等设置制表位操作 SIGSEGV（rc=139） | 见下方"已知限制"；另 tcutil.c 两处非 tty 路径用未初始化 termios 调 tcsetattr | 补丁 0002 修复非 tty termios 隐患；其余为上游缺陷，见已知限制 |

## 源码修改（patches/）

| 补丁 | 文件 | 内容 | 原因 |
|---|---|---|---|
| 0001 | tparam.c | 在 bcopy→memcpy 宏定义前插入 `#include <string.h>` | 修复与 OHOS sysroot strings.h 的 bcopy 声明冲突（所有平台通用） |
| 0002 | tcutil.c | restore_translations/disable_xtabs 增加 isatty(1) 守卫 | 非 tty 调用时不使用未初始化 termios 结构调 tcsetattr（平台通用健壮性修复） |

## 验证结果

```bash
# 探索编译（设备 OHOS aarch64 原生）
CC=clang CFLAGS="-std=gnu89 -g -O2" sh configure --prefix=$HOME/usr/local  # rc=0
make -j1                                                                    # rc=0
TERM=gtu TERMCAP='gtu:co#80:li#24:' ./tput co   # → 80, rc=0
TERM=gtu TERMCAP='gtu:co#80:li#24:' ./tput li   # → 24, rc=0
TERM=gtu TERMCAP='gtu:co#80:li#24:' ./tput zzz  # → 未知能力报错, rc=4
./tabs --version                                 # → GNU tabs version 2.0, rc=0
```

## 交付物

| 文件 | 说明 |
|------|------|
| bin/tput | termcap 能力查询工具（完整可用，消费者测试覆盖） |
| bin/tabs | 制表位工具（--version/--help 可用；见已知限制） |

## 已知限制

- **tabs 的制表位设置操作在 OHOS arm64 上段错误**（`tabs 8` rc=139）。
  定位证据：fprintf 探针链确认崩溃点在 parse_tabspec 列表解析循环的第二次
  条件求值处（`ix < tabs_length && spec[0] != 0`，地址与入参一致、-O0/-O2 均
  复现，设备 ptrace 受 SELinux 限制无法 gdb 定位到指令级）；同文件
  `-N` 分支还存在 `a_to_i(&spec[1], spec, 0)` 把指针当二级指针写的类型混淆。
  这是上游 1995 年 K&R 代码与 OHOS arm64 运行时组合的缺陷，不影响 tput。
  属"已定位的运行错误"，如实申报不做静默删除。

## 注意事项

- 消费者测试通过 TERMCAP/TERM 环境变量注入内存 termcap 条目，不依赖系统
  terminfo/termcap 数据库（OHOS 设备无 /etc/termcap）。
- `tabs` 若在真实终端（isatty）下使用，termios 路径已由补丁 0002 守卫。
---

**编译结束**: 2026-09-14 01:11
**最终状态**: built
