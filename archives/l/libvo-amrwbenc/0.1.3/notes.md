# libvo-amrwbenc 0.1.3 适配记录

## 上游与交付

- **上游**：VisualOn AMR-WB（Adaptive Multi-Rate Wideband / G.722.2）编码器 0.1.3。
  官方发行包（SourceForge `opencore-amr` 项目，自带 `configure`）：
  `vo-amrwbenc-0.1.3.tar.gz`，sha256 `5652b391…1a71d9d4e`；GitHub 镜像
  `mstorsjo/vo-amrwbenc`（tag `v0.1.3` 的归档包**不含** `configure`，需 autoreconf，
  因此本包用官方 release tarball）。平台任务：`libvo-amrwbenc` / `0.1.3`。
- **交付**：
  - `lib/libvo-amrwbenc.so.0.0.4`（+ `.so.0`/`.so` 软链；静态构建时为 `libvo-amrwbenc.a`）
  - `include/vo-amrwbenc/enc_if.h`（公开 C API：`E_IF_init`/`E_IF_encode`/`E_IF_exit`）
  - `bin/amrwb-enc`（命令行编码器）
  - `lib/pkgconfig/vo-amrwbenc.pc`（消费者契约）
  - `licenses/{COPYING,NOTICE}`（Apache-2.0）
- **解码侧**：AMR-WB 解码由同源的 `opencore-amr`（仓库已适配 0.1.6）提供，两者合起来
  才是完整的 AMR-WB 编解码链路 —— 消费者用例正是按这个真实分工做的闭环验证。

## OHOS 适配要点（沿用 lame/sqlite3 的 autotools 方案）

1. **名义三元组**：`config.sub` 不认 `aarch64-linux-ohos` → `--host/--build=aarch64-linux-gnu`，
   真实目标由 profile 的 `tools.build:compiler_executables`（OHOS clang）决定。
2. **uname shim**：设备 `uname -s` 为 `HarmonyOS`，config.guess 会走未知分支 →
   PATH 前置 shim（`-s`→`Linux`，`-m`→`aarch64`，其余转交系统 uname）。
3. **E011**：上游 `configure` 内的 `umask 077` 在 HMDFS/SELinux 下会让临时目录不可写 →
   构建前替换为 `umask 022`。
4. **bin_PROGRAMS 缺失**：发行包 `Makefile.in` 里 `bin_PROGRAMS = amrwb-enc` 没有被
   `all`/`install` 引用（较新 automake/make 下展开为空对象列表，`make amrwb-enc`
   直接报 `no input files`）。本包在库构建完成后**按 `Makefile.am` 的声明手工编译
   同一个目标**（`amrwb_enc_SOURCES = amrwb-enc.c wavreader.c`、
   `amrwb_enc_LDADD = libvo-amrwbenc.la`，链接 `-L.libs -lvo-amrwbenc -lm`），
   从而 `bin/amrwb-enc` 真正随包交付。
5. **串行 make**：HMDFS 上并行 make 偶发失败，按仓库惯例 `make -j1`。

## 测试证据

| 层级 | 内容 | 结果 |
|------|------|------|
| 上游官方测试 | 发行包内**没有**测试目录/测试目标（N=0），官方用法是它自己的 `amrwb-enc` | N=0（清点证据：无 `test/`、`Makefile.am` 无 `check`/`test` 目标、无 autopkgtest） |
| 完整消费者用例（rule12） | `test_package/test_vo_amrwbenc.c` 六步：① 生成真实 16 kHz WAV ② 用**交付的** `bin/amrwb-enc -r 23850` 编码 ③ 校验码流（魔数 `#!AMR-WB\n`、50 帧、每帧 61 字节、帧头 `FT=8`） ④ 用 `E_IF_*` API 编码并与 CLI 产物**逐字节一致**（3059 字节） ⑤ 9 种模式全部校验帧长 18/24/33/37/41/47/51/59/61 与文件总长 ⑥ 用参考解码器 `opencore-amr/0.1.6` 解码回 16000 样本，做**延迟搜索**后的相关系数与 SNR 闭环校验 | **6/6 通过**（本地原生编译 + 运行实测：相关系数 **0.9931**、SNR **18.52 dB**） |
| 适配自检（M） | `test_package/test_layout.py`：库/公开头/共享库 ELF、pkg-config 契约、`bin/amrwb-enc` 可执行、许可、未夹带源码与中间产物 | **9/9 通过** |

未修改上游任何源码或测试（`patches_applied: []`，唯一的构建期改动是 `umask` 替换）。

## 消费者用例的两个关键事实（对后续适配有复用价值）

1. **`E_IF_encode()` 的返回值已包含 1 字节帧头**（上游 CLI 就是 `n = E_IF_encode(...);
   fwrite(outbuf, 1, n, out)`），因此消费者可以直接与 CLI 产物逐字节比对。
2. **闭环验证必须做延迟搜索**：AMR-WB 编解码有算法延迟，纯音信号逐样本比对会得到
   **负相关系数**（相位差接近半个周期）；在 0~2000 样本范围内搜索最佳延迟后，
   相关系数 0.99+、SNR 18~21 dB（6.6k~23.85k 模式）。

## 本地验证的边界（如实说明）

本工作站（x86_64）没有 OHOS 工具链，本地无法执行 `conan create` 的 OHOS 构建；本地用
**同一份源码 + gcc 原生复现 recipe 的构建流程**（configure 选项、umask 替换、uname shim、
手工编译 CLI）并跑通消费者用例与自检。OHOS 侧的构建与真机执行由平台 CI 完成
（CI 的 host/build profile 同为 `ohos-aarch64` → 原生构建 → test_package 真跑）。
