# hexer 1.0.7 适配笔记

## 编译环境
- 构建系统: makefile（plain Makefile，非 autotools）
- 编译日期: 2026-06-17
- 编译器: clang 15.0.4
- CFLAGS: -fPIC -O2 -std=c99 -Wno-deprecated-non-prototype
- 链接库: -lncursesw -lm
- 状态: built

## 编译步骤

hexer 1.0.7 使用纯 Makefile 构建，无 `./configure` 脚本。Makefile 通过变量 `PREFIX ?=` 控制安装路径，通过 `config-test.c` 自动检测平台特性生成 `config.h`。

```bash
# 编译（Makefile 自行处理 config.h 生成）
make PREFIX=$DEFAULT_PREFIX -j1

# Staging 安装
make install PREFIX=$DEFAULT_PREFIX DESTDIR=$TEST_PREFIX

# 本地安装
make install PREFIX=$DEFAULT_PREFIX

# ELF 签名（OpenHarmony 要求）
sign-elf ~/usr/local/bin/hexer
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | set.c 编译失败 `-Wdeprecated-non-prototype` 硬错误 | clang 15 将调用无原型函数指针视为硬错误，`-Wno-` 标志和 pragma 均无法抑制 | 修改 `set.h` 中 `typedef void (*set_fn)()` → `typedef void (*set_fn)(long)`；同步修改 `hexer.c` 中所有 action 函数签名为 `long` 参数，`set.c` 调用点添加类型转换 |
| 2 | tio.c 编译失败 `-Wint-conversion` 硬错误 | OpenHarmony `term.h` 仅声明 `tputs`，缺少 `tgoto`/`tgetent`/`tgetstr`/`tgetnum`/`tgetflag` 声明，导致隐式声明返回 int 触发类型转换错误 | 在 `tio.c` 中添加 `extern` 声明（前一个编译会话已修改但未追踪，本次补录为补丁） |
| 3 | Makefile `CFLAGS_STD ?=` 在 G0 验证环境中未生效 | `?=` 赋值方式在 clean-verify 的 make 环境中行为异常，`-Wno-deprecated-non-prototype` 未被应用 | 将 `CFLAGS_STD ?=` 改为 `CFLAGS_STD =`（强制赋值） |
| 4 | G0 clean-verify 尝试运行不存在的 `./configure` | 验证脚本默认执行 `bash ./configure`，但 hexer 无 configure 脚本 | 新增 `configure` wrapper 脚本，解析 `--prefix` 并写入 `config.mk` |
| 5 | G4 门禁报 "manifest 缺少 build_system" | 验证脚本检查顶层 `build_system` 字段，而非 `build.system` | 在 manifest.yaml 添加顶层 `build_system: makefile` 字段 |

## 源码修改

共 6 个补丁：

| 补丁 | 文件 | 修改内容 |
|------|------|----------|
| 0001-Makefile.patch | Makefile | `CFLAGS_STD ?=` → `CFLAGS_STD =`，确保编译标志始终生效 |
| 0002-configure.patch | configure (新增) | 添加 configure wrapper 脚本，适配 G0 验证流程 |
| 0003-hexer.c.patch | hexer.c | action 函数签名从 `int`/`void` 改为 `long`，移除不必要的 `(set_fn)` 强制转换 |
| 0004-set.c.patch | set.c | 更新 `i->action()` 调用点的参数类型转换 |
| 0005-set.h.patch | set.h | `typedef void (*set_fn)()` → `typedef void (*set_fn)(long)`，移除 GCC pragma hack |
| 0006-tio.c.patch | tio.c | 添加 termcap 函数声明（tgoto/tgetent/tgetstr/tgetnum/tgetflag） |

## 依赖版本

- ncurses: 6.4 (静态库 libncursesw.a，OpenHarmony 预编译)
- musl libc: 系统内置
- 无其他外部依赖

## 验证结果

```bash
$ hexer -V
hexer 1.0.7

$ hexer -F
Features: hexer=1.0.7

$ file ~/usr/local/bin/hexer
ELF shared object, 64-bit LSB arm64, dynamic, stripped

$ readelf -d ~/usr/local/bin/hexer | grep NEEDED
Shared library: [libc.so]
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| hexer-1.0.7-ohos-aarch64.tar.gz | 388KB | 预编译主包（bin + man + doc） |
| hexer-1.0.7-ohos-aarch64-debug.tar.gz | 21KB | 调试符号包 |

## 注意事项

- hexer 是终端编辑器，在非交互式环境（如 CI/CD、非终端 shell）中会报 "no termcap file found"，属预期行为。
- OpenHarmony 的 `term.h` 仅声明了 `tputs`，termcap 其他函数（tgoto 等）存在于 libncursesw.a 中但缺少头文件声明，编译时需要手动 extern。
- clang 15 的 `-Wdeprecated-non-prototype` 是硬错误，无法通过命令行标志或 pragma 抑制，必须修改源码使用正确原型的函数指针。
---

**编译结束**: 2026-06-18 15:31
**最终状态**: built
