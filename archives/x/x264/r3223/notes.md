# x264 r3223 HarmonyOS PC 适配笔记

## 上游

- 仓库：https://code.videolan.org/videolan/x264
- 许可：GPL-2.0-or-later
- 语言：C + aarch64 汇编
- 第三方依赖：**无**（自包含）

### 版本号说明

x264 **没有发布 tag**（上游只有 master/stable 分支）。其“版本”由构建时
`version.sh` 用 `git rev-list HEAD | wc -l` 算出，即 `r<提交计数>`。

本包固定 master tip 提交 `0480cb05fa188d37ae87e8f4fd8f1aea3711f7ee`，
其 rev-list 计数为 **3223**（经 GitLab API 分页枚举确认），故版本号取
`r3223`。取 SHA 归档而非 master 分支归档的原因：分支会前进，那样
`conandata.yml` 里的 sha256 必然失配、CI 会随机失败。

> 已知副作用：SHA 归档不含 `.git`，上游 `version.sh` 会退化成 `ver="x"`，
> 使 `X264_VERSION` 为空、`X264_POINTVER` 变成 `0.165.x`。
> 本配方在 configure 之后按固定提交回填这两个宏（见 `_pin_version()`），
> 使 `x264 --version` 与 `x264.pc` 的 `Version` 报告 `0.165.3223`。

## 构建

x264 是**手写 configure**（非 autoconf 产物）+ make：

```bash
bash ./configure --prefix=... --host=aarch64-unknown-linux-gnu \
    --enable-shared --enable-static --enable-pic ...
make -j4
make install INSTALL=/bin/install
```

### 遇到的坑与处理

| # | 现象 | 根因 | 处理 |
|---|------|------|------|
| 1 | `./configure` → `No such file or directory` | configure 首行是 `#!/bin/bash`，OHOS 的 `/bin/bash` 不存在 | 用 hnp 的 bash 显式执行：`/data/service/hnp/bin/bash ./configure` |
| 2 | `--host=aarch64-unknown-linux-ohos` → `machine 'aarch64-unknown-linux' not recognized` | x264 自带 config.guess 不认识 OHOS | 改传 gnu 三元组 `aarch64-unknown-linux-gnu`（OHOS 内核接口与 linux 一致、libc 为 musl） |
| 3 | 设备无 `nasm`/`yasm`，担心汇编优化被关 | x264 configure 的 aarch64 分支用 `AS="${AS-${CC}}"`（即 clang）；`nasm` 仅出现在 x86/x86_64 分支 | 无需补汇编器：实测 `asm: yes`，汇编内核正常编译 |
| 4 | `make install` 依赖 coreutils `install` | OHOS 无该命令 | `/bin/install` 是 toybox 实现，实测支持 `-d`/`-m`，故上游 install 规则原样使用，只需 `INSTALL=/bin/install` |
| 5 | HMDFS 上默认 TMPDIR 不可写 | — | `TMPDIR=<build>/_tmp` |
| 6 | 版本串退化为 `0.165.x` | SHA 归档无 `.git` | configure 后回填 `x264_config.h` 的 `X264_VERSION`/`X264_POINTVER`；打包时同步改写 `x264.pc` 的 `Version` 与绝对路径 |
| 7 | `.so`/可执行文件在 OHOS 上无法加载/执行 | 鸿蒙 PC 要求代码签名 | 打包末尾 `llvm-objcopy --remove-section .codesign` + `binary-sign-tool sign -selfSign 1`（跳过符号链接，避免对同一目标重复签） |
| 8 | **CI 上 configure 报 `no NEON support, try adding -mfpu=neon to CFLAGS` 并退出 1**（本地与真机均通过） | x264 configure 对 `AS`/`AR`/`STRIP` 用 **`${VAR-default}`**——只认「未设置」，**不认「已设置但为空」**。CI worker 把 `AS` 导出成**空串**，于是 `AS="${AS-${CC}}"` 取到空值，汇编检查命令 `"$AS conftest.S ... -o conftest.o"` 退化成「执行 `conftest.S` 文件」→ 汇编自检失败 → 报该误导性错误 | 显式固定全部工具链变量为**绝对路径**：`CC/AS/AR/RANLIB/NM/STRIP`（`CC`/`AS` 取 `tools.build:compiler_executables` 的 `c`，缺省回退 `/data/service/hnp/bin/clang`；其余回退 `llvm-ar`/`llvm-ranlib`/`llvm-nm`/`llvm-strip`），不再依赖任何继承环境变量（R33） |

### 关于第 8 项（误报式失败）

该失败**具有极强误导性**：错误文本指向 NEON/`-mfpu=neon`，但真实原因与 NEON 无关。
判别特征：configure 的 **stdout 只剩那两行**（前面的检查都写 stderr），可用它快速确认
是「死在 as_check」而非别的阶段。

本机精确复现与验证（`export AS=; bash ./configure ...`）：

| 条件 | rc | stdout 行数 | 结果 |
|------|----|-----------|------|
| `AS` 未设置（基线） | 0 | 27 | `asm: yes` |
| `AS=/data/service/hnp/bin/as` | 0 | 27 | 正常（`as` 也能过） |
| **`AS=` 空串** | **1** | **2** | **`no NEON support...`（与 CI 日志逐字一致）** |
| `AS=` 空串 + 显式 `AS=clang` | **0** | 27 | **`asm: yes`（修法生效）** |

修法落地后，以 `AS= conan create ...` 模拟该 worker 环境回归验证：rc=0、
无 NEON 错误、checkasm 仍 2 次 `All tests passed`、test_package 6/6 全过。

另：`build()` 里加了失败兜底——configure 失败时把 `config.log` 末 60 行打到 CI 日志。
起因是本次 CI 只留下那句 NEON 报错，而 configure 已把**失败命令原文与编译器 stderr**
写进 `config.log`；不打出来就得靠猜（本次即吃了这个亏）。


> 关于 main 上既有的 `archives/x/x264/master/patches/0001-Makefile.patch`：
> 该补丁以“HMDFS 上 `$(shell cat config.h)` 失效”为由，把 threadpool 与
> bit-depth 模块改为无条件编译。**本机实测 `$(shell cat config.h)` 在
> HMDFS 与 /data 下均正常**（`make` 的条件判定命中），故本包未采用该补丁，
> 保持上游 Makefile 原样、改动最小。

## 上游测试

`tools/checkasm.c` 是上游自带的汇编内核自检程序，`make checkasm`
产出 `checkasm8` / `checkasm10` 两个可执行文件（对应 8bit / 10bit 路径）。

**实测结果（本地 OHOS aarch64）**：

| 可执行 | 结果 |
|--------|------|
| `checkasm8` | **66 项 [OK]，0 项 [FAIL]**，末行 `x264: All tests passed Yeah :)` |
| `checkasm10` | **36 项 [OK]，0 项 [FAIL]**，同上 |

合计 **102 项全通过**，覆盖 intra pred / coeff_last / coeff_level_run /
pixel hadamard_ac / sub_dct4 / zigzag_interleave / mc / deblock 等汇编内核。

注意：checkasm 二进制需先签名才能在本机运行（未签名直接执行会被拒），
这也是 package() 统一重签的原因之一。

## 消费者测试

`test_package/test.c`（6 项断言，独立于上游 checkasm）：

1. `X264_BUILD >= 165` —— 头文件把 `x264_encoder_open` 粘到
   `x264_encoder_open_<X264_BUILD>`，故该项同时证明头/库 ABI 一致
2. `x264_encoder_open` 成功
3. `x264_encoder_headers` 产出 SPS/PPS
4. `x264_encoder_encode` 产出一帧的 NAL 单元
   （x264 有帧延迟：首调用可能返回 0，需按 `x264_encoder_delayed_frames()`
   以 NULL 输入冲刷）
5. NAL 载荷以 H.264 起始码 `00 00 00 01` 开头
6. **阴性对照**：以不支持的 `i_bitdepth=99` 打开编码器必须失败
   —— 以证明前述断言非恒真

实测：EXIT=0，6/6 全过（输出 4 个 NAL 单元）。

## 交付物

| 文件 | 说明 |
|------|------|
| `lib/libx264.so` → `libx264.so.165` | 共享库（已签名） |
| `lib/libx264.a` | 静态库 |
| `include/x264.h`、`include/x264_config.h` | 公共头 |
| `lib/pkgconfig/x264.pc` | pkg-config（路径已改为 `${prefix}` 相对形式） |
| `bin/x264` | 命令行编码器（已签名） |

## 已知限制 / TODO

- 仅适配 aarch64（OHOS 目标平台）；`--host` 为固定三元组，未参数化到其它架构
- `--disable-lavf/--disable-ffms/--disable-swscale`：x264 CLI 不支持通过
  libav* 读取输入（会引入 ffmpeg 依赖），只支持内置的 raw YUV/Y4M 输入
- `--disable-opencl`：无 GPU 驱动
- x264 为 GPL-2.0-or-later：下游若为 LGPL 项目（如 ffmpeg 默认构建）
  需自行评估许可兼容性
