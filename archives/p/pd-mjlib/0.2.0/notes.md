# pd-mjlib 0.2.0 适配笔记

## 上游构成

`pd-mjlib_0.2.0.orig.tar.gz` 是 Pure Data 外部对象集合 **mjlib**，用上游自带的
`pd-lib-builder`（`Makefile.pdlibbuilder`）构建，每个类产出一个
`<class>.pd_linux` 共享对象：

| 类 | 说明 |
|---|---|
| `about` | 基于锚点值 + 百分比偏差的随机发生器 |
| `metroplus` | 多区间 metro |
| `monorhythm` | 多区间多输出节奏发生器 |
| `morse` | 文本转摩尔斯电码 |
| `n2m` | 音名（如 `C5`）转 MIDI 音编号 |
| `pin~` | 基于随机的信号路由 |
| `prob` | 随机事件发生器 |
| `synapseA~` | 块平均/比较器 |

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
| `lib/pd-externals/*.pd_linux` | 8 个 mjlib 外部对象 |
| `lib/pd-externals/*-help.pd` | 帮助补丁 |
| `lib/pd-externals/mjlib-meta.pd` | 库元数据 |

## 测试

上游无自动化测试套件（只有 Pd 帮助补丁与 `test/prob-test.pd`）→ 上游 N=0。

消费者测试 `test_package/test_pd_mjlib.sh`（2 项断言）用**真机 OHOS 的 `pd`**
无头加载安装后的外部对象，驱动确定性的 `[n2m]` 类：

- `note C5` → `72`
- `note D#3` → `51`

真机 `conan create`：`CREATE_RC=0`，消费者 2/2。
