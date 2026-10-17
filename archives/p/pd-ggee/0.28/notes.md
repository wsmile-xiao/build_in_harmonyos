# pd-ggee 0.28 适配笔记

## 上游构成

`pd-ggee` 是 Guenter Geiger 的 Pure Data 外部对象库 **ggee**（"Pretty Damn
Good" 系列），上游仓库 <https://github.com/pd-externals/ggee>，唯一 tag
`v0.28`。用上游自带的 **pd-lib-builder**（`pd-lib-builder/Makefile.pdlibbuilder`
v0.6.0）构建：按 `Makefile` 里 `class.sources` 逐类编译，产出**每个类一个**
`<class>.pd_linux` 共享对象，Pd 在打补丁时按类名 dlopen 它们。

- `class.sources` 共 **42** 个源文件：`control/` 16、`experimental/` 3、
  `filters/` 9、`gui/` 9、`signal/` 5。
- `gui/fatom.c` 在上游 Makefile 里是**注释掉的**（`#class.sources += gui/fatom.c`），
  因此 `[fatom]` 类本次不构建。`fatom.h` 仍被 `gui/slider.c`、`gui/sliderh.c`、
  `gui/ticker.c` 以 `#include "fatom.h"` 引用；这三个类只用头文件里的声明与内联辅助
  定义，不引用 `fatom.c` 的外部符号，因此照常编译链接通过（已用
  `nm -D --undefined-only` 确认三个 `.pd_linux` 无未定义 `fatom*` 符号）。
- `other/` 目录（`messages.c`、`vbap.c`）不在 `class.sources` 里，上游也未构建。
- `experimental/stk.cpp`（STK 合成器）同样不在 `class.sources` 里，不构建。
- 数据文件：`datafiles` 声明 `*/*-help.pd`（45 个）、`LICENSE.txt`、
  `README.txt`、`gui/state.list`、`gui/logo100.gif`、`ggee-meta.pd`。

## 构建

- **Pd API 头**：制品仓 `puredata/0.54.1` 是 *application* 类型，`package_info()`
  不导出 `includedirs`，但包内 `include/pd/` 确实装了 `m_pd.h` 与
  `g_canvas.h`。配方 `_pd_include_dir()` 直接从依赖包目录解析出该目录并作为
  `PDINCLUDEDIR` 传下去（与 `pd-libdir/1.11` 同一手法）。ggee 的源文件只 include
  公开 Pd API（`<m_pd.h>` + 同目录的 `g_canvas.h`），不碰 `m_imp.h` 等内部头。
- **平台判定**：pd-lib-builder v0.6.0 用 `$(CC) -dumpmachine`（**不是** `uname`）
  取三元组首词判系统。CI worker 的 OHOS NDK clang 与本地 WSL 交叉 shim 都报
  `aarch64-...-linux-ohos`，其中 `linux` 一词命中 → 走 Linux 分支，得到
  `.pd_linux` 扩展名、`-DUNIX`、`-fPIC -shared -rdynamic`、`-lc -lm`。
  配方仍在命令行显式传 `system=Linux` 兜底，使平台选择不依赖 worker clang 的
  三元组拼写。
- **`arch.c.flags`**：`target.arch` = `aarch64` → `-mcpu=cortex-a53`，OHOS clang
  原样接受，无需覆盖。
- 命令：`make -j1 system=Linux CC=<clang> PDINCLUDEDIR=<puredata>/include/pd`。
- **零补丁、零源码改动**即可在 OHOS aarch64 编译通过。唯一告警是
  `error()` 隐式声明（`control/unwonk.c`、`control/qread.c`、
  `experimental/fofsynth~.c`）与若干 unused parameter——`-Wimplicit-function-declaration`
  在 clang 15 只是 warning，符号在 Pd 主程序里存在，链接与运行均正常。

## 产物

| 路径 | 说明 |
|------|------|
| `lib/pd-externals/*.pd_linux` | 42 个 ggee 外部对象（构建产物在源码根，扁平安装） |
| `lib/pd-externals/*-help.pd` | 45 个帮助补丁，**扁平**安装 |
| `lib/pd-externals/ggee-meta.pd` | 库元数据 |
| `lib/pd-externals/{state.list,logo100.gif}` | `[state]` / `[image]` 的随包数据（源码里位于 `gui/`，两者都不按名查找，属随包资产） |
| `licenses/{LICENSE.txt,README.txt}` | 上游许可与说明（`datafiles` 声明的两份文本） |

> 布局说明：帮助补丁在**源码树**里按类分目录存放（`control/` 17、`experimental/` 4、
> `filters/` 9、`gui/` 9、`other/` 1、`signal/` 5，共 45），但 pd-lib-builder v0.6.0 的
> `install-datafiles` 规则是逐文件 `install -p -m 644` 落到同一个 installpath、
> **不做 `cp -R`**，所以上游 `make install` 的结果本身就是扁平布局。Pd 查帮助补丁的
> 方式是「已声明 path 目录 + `<类名>-help.pd`」、**不递归子目录**，因此配方同样扁平
> 安装：使用方只需 `-path <pkg>/lib/pd-externals` 一个目录，即可同时加载 42 个外部
> 对象与全部 45 个帮助补丁。

打包形态取 `library`（Pd 插件 dlopen 加载，不是命令行程序），故**不需要**
软件级 `commands.json`（R38 不适用）。

## 依赖

| 依赖 | 状态 | 用途 |
|------|------|------|
| `puredata/0.54.1` | 已发布（`conan download "puredata/*" -r=ohpcd --only-recipe` 实测命中） | Pd API 头 `m_pd.h` / `g_canvas.h`；消费者测试的 `pd` 可执行文件 |

`pd-libdir` / `pd-maxlib` 是同系列先例，均已在 main 且 CI 绿。

## 测试

上游无自动化测试套件（清点见 `test_package/MANIFEST.yml` 的
`upstream_test_audit`）→ 上游 N=0。

消费者测试 `test_package/test_pd_ggee.sh`（3 项断言）用 **OHOS 的 `pd`**
无头加载安装后的外部对象，驱动三个确定性控制类：

- `[constant pi]` + bang → `3.14159`
- `[sinh 2]` → `3.62686`
- `[inv 10]` → `0.1`

脚本在启动 pd 前先断言 42 个 `.pd_linux` 全部安装到位，避免对残缺安装跑绿。

本地 `conan create`：`CREATE_RC=0`，消费者 3/3。

> 备注：`pd` 的 `; pd quit;` 退出消息会与 `loadbang` 输出竞争、可能让个别 print
> 丢失，因此脚本用 `timeout 40` 结束 pd 进程（输出在退出前已落地），不在补丁内
> 主动退出——与 `pd-maxlib` 的做法一致。
>
> 本地 WSL 是 x86_64，跑 aarch64/OHOS 产物需要 binfmt+qemu 与 guest musl 的
> `__fd_chk` 等 shim；这是**环境侧**设施（见 pitfall-memo T017），配方里不含任何
> `LD_PRELOAD`/shim/运行期补丁。
