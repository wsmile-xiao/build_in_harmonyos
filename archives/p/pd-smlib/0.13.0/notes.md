# pd-smlib 0.13.0 适配笔记

## 上游构成

`pd-smlib_0.13.0.orig.tar.gz` 是 IOhannes m zmölnig 的 **SMLib** —— 一组把 DSP 数据
映射为控制数据的 Pure Data 外部对象（40 个类）。用 tarball 内置的
`pd-lib-builder`（`pd-lib-builder/Makefile.pdlibbuilder`）构建，产物是**每个类一个**
`<class>.pd_linux` 共享对象，Pd 在加载补丁时按类名从画布搜索路径里找到它们。

- `Makefile` 用 `<class>.class.sources` 逐类声明源文件，共 40 个类。
- 数据文件：`help/*-help.pd`（41 个）、`SMLib.pd`、`smlib-meta.pd`、`README.txt`；
  `extradirs = examples`。

## 构建

- **Pd API 头**：制品仓的 `puredata/0.54.1` 是 *application*，只装 `pd` 可执行与数据
  目录，**不含** `m_pd.h`。配方在 `source()` 里额外拉取 `puredata/0.54.1` 所依据的
  同一上游版本 `pure-data 0.54-1` 源码树（codeload.github.com，sha256 与
  `puredata/0.54.1` 一致），把 `PDINCLUDEDIR` 指向其 `src`。
- `pd-lib-builder` 用 `$(CC) -dumpmachine` 判断目标系统；OHOS clang 报
  `aarch64-...-linux-ohos` → 选中 Linux 分支与 `pd_linux` 扩展名。`CC` 由
  `tools.build:compiler_executables` 显式传入（不裸用 `${CC}`，R33）。
- 纯 C（`m_pd.h` + `math.h`），**零三方依赖、零补丁**：40 个类在 OHOS aarch64 上
  原样编译通过。

## 产物

| 路径 | 说明 |
|------|------|
| `lib/pd-externals/*.pd_linux` | 40 个 SMLib 外部对象 |
| `lib/pd-externals/*-help.pd` | 41 个帮助补丁 |
| `lib/pd-externals/SMLib.pd` / `smlib-meta.pd` / `README.txt` | 库抽象与元数据 |
| `lib/pd-externals/examples/*.pd` | 3 个示例补丁 |
| `licenses/LICENSE.txt` | GPL-2.0-or-later |

## 测试

上游 37 个 `unittests/*-unittest.pd`（每个旁边一份 512 点参考 `*.wav`）**全部真跑**。

它们实例化 `testtools/unit-test-frame`（**pd-testtools 0.1** 提供，BSD-3-Clause）。
该抽象是纯 Pd 的：`soundfiler` 读参考 `*.wav` → `tabwrite`/`tabread` 逐点相减 →
算差值标准差 → 打印

```
STDDEV-ZERO 0 <name>        完全一致      → pass
STDDEV-SMALL <x> <name>     rms < 1e-05   → pass
STDDEV-LARGE <x> <name>     rms >= 1e-05  → FAIL
```

**不需要音频图，也不需要 ggee**（`ggee/getdir` 缺席时框架回退到补丁同目录的
相对路径），所以无头环境可执行。判据是上游自己的比较 + 上游自己的参考渲染，
我们不掺任何判定逻辑。

- 配方本身不变；`test_package/conanfile.py` 按固定 sha256 额外拉取**两份**上游归档到
  临时目录（不进仓库、不进包）：pd-smlib 0.13.0 tarball（取 `unittests/` 与参考
  `*.wav`）和 pd-testtools 0.1（取 `unit-test-frame`）。这样判据是上游自己的字节，
  且受 sha256 校验，而不是把第三方代码 vendored 进仓库。
- 37 个补丁作为**同一画布的 37 个 subpatch**（各自独立 `$0` 空间）一次加载进一个
  无头 `pd`；补丁按 `smlib/` 命名空间取类，因此把安装产物拷到 `<work>/smlib/`
  （`pd-lib-builder` 本来就装到 `<externals-root>/<libname>/`）。
- 画布里挂一个 `[delay 15000] → [; pd quit(`，让 Pd **自己退出**。若改用
  `timeout` 发 SIGTERM，Pd 的 stdout 是块缓冲的，尾部结果会被整块丢掉（实测
  37 条只剩 24 条），必须避免。
- 上游 `lstd-unittest.pd` 自己的参考名写成了 `lsdt`，对应的参考文件也是
  `lsdt.wav`；断言集合按 `*.wav` 基名取，与上游保持一致。

消费者测试 `test_package/test_pd_smlib.sh`（17 项断言）用**真机 OHOS 的 `pd`**
无头加载安装后的外部对象，驱动 13 个确定性 list 类并核对打印结果：

| 断言 | 内容 |
|------|------|
| vmax / vmin | `[vmax 3 9 4]`→9，`[vmin 3 9 4]`→3 |
| vsum | `[vsum 1 2 3 4]`→10 |
| vmtof / vftom | 69↔440，`[vmtof 60 72 84]`→261.626 523.251 1046.5 |
| vclip | `[vclip 0 10]` 作用于 -5 5 50 → 0 5 10 |
| vvplus | `[vvplus 10 20 30]` + `1 2 3` → 11 22 33 |
| vrms / vstd | 3.53553 / 2 |
| vabs | `[vabs -1 -2.5 3]`→1 2.5 3 |
| vcog / vdbtorms / vnmax | 2.33333 / 0 / 9（索引 2） |
| **鸿蒙特有** | 全部 externals 的 ELF `e_machine==0xb7`（AArch64）；40 个类完整安装 |

## 踩坑与处置

| # | 问题 | 根因 | 处置 |
|---|------|------|------|
| 1 | `fatal error: 'm_pd.h' file not found` | `puredata/0.54.1` 是 application，不装 Pd API 头 | `source()` 额外拉 pure-data 0.54-1 源码树，`PDINCLUDEDIR` 指向其 `src` |
| 2 | 用 `[obj 20 20 vmax 3 9 4]` 创建参数驱动，输出 `-3.40282e+38` / `bang` | SMLib 的 list 类只 `class_addlist`，创建参数走的是 float/bang 方法 | 改用 `[msg ...]` 发 `list ...` 消息 |
| 3 | `[vvplus]` + 两次 list 输出的是原样列表 | 无创建参数时创建的是**标量**版（`vvplus_scal_class`，右入口为 float inlet） | 用 `[vvplus 10 20 30]` 创建双缓冲向量版，再送 `list 1 2 3` 得 11 22 33 |
| 4 | 本地跑 `pd` 报 `Error relocating ...: __fd_chk: symbol not found` | WSL/qemu 的 guest musl 早于 glibc fortify shim | 测试脚本里在 `/opt/ohos-guest/lib/libfdchkshim.so` 存在时条件注入 `LD_PRELOAD`（CI 原生 OHOS 无此路径，不受影响） |
| 5 | 上游 37 个 unittest 报 `smlib/vmax: couldn't create` | 补丁按 `smlib/` 命名空间取类，包里是拍平的 `lib/pd-externals/*.pd_linux` | 测试工作目录里把安装产物拷到 `<work>/smlib/`，还原 `pd-lib-builder` 的 `<externals-root>/<libname>/` 布局 |
| 6 | `cat *.pd` 拼起来只有 1 个用例出结果 | Pd 文件里裸 `#N canvas` 会被当作未 restore 的 subpatch，`loadbang` 不触发 | 每段后补 `#X restore 0 0 pd <name>;`，才是真正放在父画布上的 subpatch |
| 7 | 37 条结果只落了 24 条 | `timeout` 发 SIGTERM，Pd 的 stdout 块缓冲尾部未刷出 | 画布里挂 `[delay 15000] → [; pd quit(`，让 Pd 正常退出 |
| 8 | `vclip` / `lstd` / `threshold` 三个用例总是缺 | 它们的 `[line]`/`pipe` 链要 1 s 以上逻辑时间 | quit 延迟取到 15 s（本地实测 37/37 需 2.5 s 逻辑时间） |

## 交付物

`lib/pd-externals/` 下 40 个 `.pd_linux` + 41 个 help 补丁 + 抽象/示例 + 许可证。
