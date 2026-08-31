# mpck 0.21 — 适配笔记

## 1. 上游核实

| 项 | 值 |
| --- | --- |
| 上游项目 | Checkmate (Sjoerd Langkemper) |
| 命令行工具名 | mpck |
| 版本 | 0.21 |
| GitHub tag | `v0.21` (commit c876755) — https://github.com/Sjord/checkmate/releases/tag/v0.21 |
| 源 tarball | https://checkmate.gissen.nl/checkmate-0.21.tar.gz |
| sha256 | `a27b4843ec06b069a46363836efda3e56e1daaf193a73a4da875e77f0945dd7a` |
| 校验来源 | Homebrew Formula m/mpck.rb（独立复核：本地下载 sha256 一致） |
| 许可证 | COPYING = GNU GPL v2 → `GPL-2.0-or-later`（每个源文件头"version 2, or (at your option) any later version"） |
| 主页 | https://checkmate.gissen.nl/ |

## 2. 上游测试入口（穷举）

> 修正：先前版本称"上游 0.21 无任何测试入口（N=0）"，经重新核查上游原始脚本后**结论错误**，已纠正。

上游 0.21 存在 **1 个测试脚本**：`mpck/test/crctest.sh`（git tag v0.21，commit c876755）。已直接读取该脚本的 GitHub blob（base64，577 字节，sha `556e9ab5`）逐行核实其真实逻辑。

### 2.1 crctest.sh 真实逻辑（逐行核实，非据评审文字猜测）

```sh
mkdir -p crc; cd crc
dd if=/dev/urandom of=soundfile.raw count=1000
for BITRATE     in 32 48 56 64 80 96 112 128 160 192 224 256; do   # 12
for SAMPLERATE  in 8000 12000 11025 16000 22050 24000 32000 44100 48000; do  # 9
for CHANNELS    in 1 2; do                                          # 2
  FILE=b${BITRATE}s${SAMPLERATE}c${CHANNELS}
  KHZ=`echo ${SAMPLERATE} | sed 's/.../'`
  if [ $CHANNELS = 1 ]; then TOPT="-a"; LOPT="-m m"; else TOPT=""; LOPT=""; fi
  toolame $TOPT -s $KHZ -b $BITRATE -e soundfile.raw $FILE.mp2
  lame -S $LOPT -s $KHZ -b $BITRATE -p soundfile.raw $FILE.mp3
done; done; done
cd ..
```

- 三层嵌套循环 = 12 × 9 × 2 = **216 组参数组合**（bitrate × samplerate × channels）。
- 调用的外部命令：`dd`（生成 1000 块 /dev/urandom 原始音频）、`toolame`（生成 MP2）、`lame`（生成 MP3）、`sed`、`mkdir`。
- **关键**：脚本中 `mpck` 出现 **0 次**，且**无任何 pass/fail/expected 断言逻辑**——它仅生成 216 个 `.mp2/.mp3` fixture 文件，不验证 mpck 的 CRC 检查结果。脚本以 `cd ..` 结束。即它是一个 **fixture 生成器**，不是 test validator。

### 2.2 该脚本不在 release tarball 中

- release tarball `checkmate-0.21.tar.gz`（sha256 `a27b4843...`）共 100 个文件，**不含 `test/` 目录、不含任何 `.sh`**（仅 `autogen.sh` 在 git 树，tarball 内亦无）。`mpck/test/crctest.sh` 仅存在于 git 仓库 tag v0.21。
- tarball 与 git 的 `Makefile.am` 均未把 `mpck/test/` 注册进 `TESTS`/`check_PROGRAMS`/`EXTRA_DIST`，故 `make check` 仍为 no-op，`make distcheck` 也不打包它。

### 2.3 上游正式测试统计（按评审口径修正）

| 项 | 值 |
| --- | --- |
| 上游正式测试套件 | 1（`mpck/test/crctest.sh`） |
| 内部参数组合 | 216（12 BITRATE × 9 SAMPLERATE × 2 CHANNELS） |
| 在 OHOS 实际执行 | 0 |
| 平台/依赖阻塞 | 1 |
| 阻塞原因 | crctest.sh 依赖 `toolame` 与 `lame` CLI 编码器；toolame 在 archives/t/、ohpcd Conan registry（0 命中）、OHOS PATH（`command -v toolame` → not found）均不存在；lame 虽在 archives/l/lame 与 ohpcd registry，但 OHOS PATH 不可用（`command -v lame` → not found）。无法经当前依赖图获得 OHOS AArch64 可执行体，故未运行。 |

诚实记录：**上游正式测试套件 = 1，已执行 = 0，依赖阻塞 = 1**。不得声明"上游测试通过"。test_package 承担真实功能验证（见 §5）。

## 3. 构建系统

GNU Autotools。release tarball 内附 `configure`、`aclocal.m4`、`Makefile.in`，无需 autoconf/automake。依赖仅 C 编译器 + 可选 `getopt_long`（缺则编译 bundled `libgnugetopt-1.2`）。无外部库依赖。

OHOS 交叉：`configure` 用 `AC_PROG_CC` 探测编译器，会编译并运行一个 trivial program 测试；交叉编译器下须显式给 `--build`/`--host=aarch64-unknown-linux-gnu`，否则 `configure` 把"无法 run 交叉产物"误判为编译器不可用（实际本机无 host C 编译器，见 `_build/config.log`）。

## 4. 退出码语义（用于 test_package 断言）

来自 `main.c` main()：

- 无文件名参数 → `exit(EINVAL)`。
- 全部文件 GOOD 且无错误 → `exit(last_error)`（last_error 为 0 即返回 0）。
- 至少一个文件损坏 → `exit(1)`。

输出（`print.c`）：每个文件打印 `SUMMARY: <file>` 扫描行；`-q` 安静模式仅打印 GOOD/BAD。

## 5. test_package 真实测试

不跑 `--help`。生成一个**最小合法 MP3**（一段 MPEG-1 Layer III 采样率 44100Hz 的静音帧，无 ID3），喂给 mpck，断言：

1. 退出码 0（文件 GOOD）。
2. stdout 含 `mpck` 与文件名（扫描行）。

MP3 帧头由 base64 可审计 fixture 提供（`mp3/min_good.mp3.b64`），不提交来源不明的二进制；解码用 `base64 -d`，可独立审计。

## 6. OHOS AArch64 musl 确认

- profile：`ci/conan/profiles/ohos-aarch64`，`os=OHOS os.version=6.0 arch=armv8 compiler=clang compiler.libcxx=libc++`。
- 工具链：`tools.build:compiler_executables` 指向 `/data/service/hnp/bin/clang`（OHOS NDK）。
- triplet：OHOS 适配版 conan 将 OHOS 映射为 `linux-ohos`，libc 为 musl（OHOS 用户态）。
- 静态链接应用，无运行时 .so 依赖，musl 兼容性无风险。
