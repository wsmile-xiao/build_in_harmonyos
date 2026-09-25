# libbs2b-tools

`bs2bstream` + `bs2bconvert` —— libbs2b 自带的两条命令行工具。

## Description

- `bs2bstream`：把原始 PCM 流（stdin/stdout）做 Bauer stereophonic-to-binaural
  交叉馈送，用于耳机收听时削弱"头中效应"。
- `bs2bconvert`：同样的 DSP，但走 libsndfile 读写音频文件，支持改采样率与位深。

## Project URL
https://sourceforge.net/projects/bs2b/

## License
LGPL-2.1-or-later

## HarmonyOS 适配说明

### 构建信息
- **版本**: 3.1.0（与库包 `libbs2b/3.1.0` 同源同版本）
- **构建系统**: autotools（`autoreconf -fi` → `configure` → `make`）
- **编译器**: clang 15.0.4
- **依赖**: `libsndfile/1.2.2`（静态）
- **链接方式**: `--disable-shared --enable-static`，两个工具都是自包含静态链接

### 与库包的分工
`archives/l/libbs2b/3.1.0` 负责 `libbs2b.a/.so`、`bs2b.h` 等头文件与 `libbs2b.pc`；
本包只负责 `bin/bs2bstream`、`bin/bs2bconvert`，`package()` 里删掉
`include/ lib/ share/`，保证同一个文件只有一个属主。

库包因为把 libsndfile 处理成"可选"而只能产出 `bs2bstream`；本包把
`libsndfile/1.2.2` 拉成真实依赖，补齐库包产不出的 `bs2bconvert`。

### 平台限制与补丁
| 问题 | 根因 | 处理 |
|------|------|------|
| configure 直接报 `Please install libsndfile` 并终止 | `configure.ac` 用 `PKG_CHECK_EXISTS([sndfile], [], [AC_MSG_ERROR(...)])` 把 sndfile 当硬依赖 | 补丁 `0003` 改为 `HAS_SNDFILE` + `AC_SUBST` + `AM_CONDITIONAL`，缺失只 WARN |
| `bs2bconvert` 链接期找不到 `-lsndfile` | `src/Makefile.am` 硬编码 `-lsndfile` 在 `bs2bconvert_LDFLAGS`，绕过 pkg-config，交叉编译拿不到 `-L` | 补丁 `0004` 改到 `LDADD` 的 `@SNDFILE_LIBS@`，并补 `bs2bconvert_CFLAGS = @SNDFILE_CFLAGS@` |
| 静态 libsndfile 链接期 `pow/sin` undefined | `-lm` 只在 `.pc` 的 `Libs.private` 里 | `0003` 用 `pkg-config --libs --static`；`make` 再显式传 `LIBS=-lm`（`$(LIBS)` 在 automake 链接行末尾，静态库顺序正确） |
| `PKG_CHECK_EXISTS` 找不到 sndfile | conan 不会把 `PkgConfigDeps` 的输出目录写进 `PKG_CONFIG_PATH` | `generate()` 里 `PkgConfigDeps(self).generate()` + `configure` 参数追加 `PKG_CONFIG_PATH=<generators>` |
| `autoreconf` 失败 | 2009 年的 `configure.ac` 用了废弃的 `AC_PROG_LIBTOOL` 与 `dist-lzma` | 补丁 `0003` 换 `LT_INIT`、去掉 `dist-lzma` |
| `config.guess` / `config.sub` 不认 HarmonyOS | 2009 版脚本无 ohos 分支 | 补丁 `0001` / `0002`（与库包同一份） |
| `config.status` 临时目录不可写 | autoconf 用 `umask 077 && mktemp -d ./confXXXXXX`，HMDFS 忽略 chmod | `build()` 里把新生成的 `configure` 两处改成 `umask 000 && mkdir -p $TMPDIR/conf$$` |
| L2 冒烟失败 | 两个工具只按 `argv[i][1]` 认选项，`--version`/`--help` 都掉进 default 分支 `return 1`，`-h` 也是 `return 1` | 补丁 `0005` 补 `-V/--version` 与 `--help`（退出 0） |
| 新二进制无法执行 | 鸿蒙安全机制要求 ELF 带 `.codesign` | `package()` 内调用 `llvm-objcopy` + `binary-sign-tool` 自签名 |

### 使用方式
```bash
bs2bstream -l c < in.pcm > out.pcm          # 原始 16bit native-endian 立体声
bs2bconvert -l jmeier in.wav out.wav        # 走 libsndfile 的文件转换
bs2bconvert --version
```

### 验证结果
- `ohc-run.py conan-verify libbs2b-tools 3.1.0`: G0-G4 / L2 / L4 / L5 全绿
- `test_package/test.sh`: 10 项断言（两个工具的 `--version`/`--help` 退出码、
  WAV 转换后帧数与采样率不变且样本被 crossfeed 改写、原始 PCM 流长度不变且内容被改写、
  缺失输入的反例）