# pd-maxlib 1.6.0 适配笔记

## 上游构成

`pd-maxlib_1.6.0.orig.tar.gz` 是 Pure Data 外部对象集合 **maxlib**，用上游自带的
`pd-lib-builder`（`Makefile.pdlibbuilder`）构建。构建产出**每个类一个**
`<class>.pd_linux` 共享对象（供 Pd 在打补丁时按类名加载）。

- `Makefile` 用 `<class>.class.sources` 逐类声明源文件；`netclient`/`netdist`/
  `netrec`/`netserver`/`maxlib.c` 在上游 Makefile 中**已被注释排除**（它们依赖 Pd
  内部头 `m_imp.h`/`s_stuff.h`），本次共构建 **58** 个外部对象。
- 数据文件：`help/*-help.pd`、`maxlib-meta.pd`。

## 构建

- **Pd API 头**：制品仓的 `puredata/0.54.1` 是 *application*，只装 `pd` 与数据目录，
  **不装** `m_pd.h`。配方在 `source()` 里额外拉取同一上游版本 `pure-data 0.54-1`
  的源码树（`codeload.github.com`，sha256 与 `puredata/0.54.1` 相同），把
  `PDINCLUDEDIR` 指向其 `src`。
- `pd-lib-builder` 用 `$(CC) -dumpmachine` 判断目标系统；OHOS clang 报
  `aarch64-...-linux-ohos` → 选中 Linux 分支与 `pd_linux` 扩展名。`CC` 由配方的
  `tools.build:compiler_executables` 显式传入。
- 纯 C，`make -j1 CC=<clang> PDINCLUDEDIR=<pd-api>/src`；无三方依赖。

## 产物

| 路径 | 说明 |
|------|------|
| `lib/pd-externals/*.pd_linux` | 58 个 maxlib 外部对象 |
| `lib/pd-externals/*-help.pd` | 帮助补丁 |
| `lib/pd-externals/maxlib-meta.pd` | 库元数据 |

## 测试

上游无自动化测试套件（只有 Pd 帮助补丁与 `test/all_maxlib.pd`）→ 上游 N=0。

消费者测试 `test_package/test_pd_maxlib.sh`（2 项断言）用**真机 OHOS 的 `pd`**
无头加载安装后的外部对象，驱动两个确定性类：

- `[divide 10 20]` → `0.5`
- `[plus 3 4]` → `7`

真机 `conan create`：`CREATE_RC=0`，消费者 2/2。

> 备注：`pd` 的 `; pd quit;` 退出消息会与 `loadbang` 输出竞争、导致个别 print 丢失，
> 因此测试用 `timeout 20` 结束 pd 进程（输出在退出前已落地），而非在补丁内主动退出。
