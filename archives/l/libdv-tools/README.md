# libdv-tools

`encodedv` + `dubdv` + `dvconnect` —— libdv 自带的三条命令行工具。

## Description

- `encodedv`：把 PPM 图像序列（+ 可选原始音频）编码成 DV 流。
- `dubdv`：把一条新的音轨混入已有的 DV 文件。
- `dvconnect`：通过 IEEE1394/FireWire 采集 DV 到文件或 stdout。

## Project URL
https://sourceforge.net/projects/libdv/

## License
LGPL-2.1-or-later

## HarmonyOS 适配说明

### 构建信息
- **版本**: 1.0.0
- **构建系统**: autotools（**不**重新生成 configure，见下）
- **编译器**: clang 15.0.4
- **依赖**: `popt/1.16`（静态）
- **链接方式**: `--disable-shared --enable-static`，三个工具都静态链 libdv

### 与库包的分工
`archives/l/libdv/1.0.0-r8` 负责 `libdv.a/.so`、`libdv/*.h` 与 `libdv.pc`；
本包只负责 `bin/encodedv`、`bin/dubdv`、`bin/dvconnect`，`package()` 里删掉
`include/ lib/ share/`，保证同一个文件只有一个属主。

### 平台限制与补丁
| 问题 | 根因 | 处理 |
|------|------|------|
| configure 报 ``machine `aarch64' not recognized`` | 随包 `config.sub` 是 2005-12-11 版，CPU 表里没有 aarch64 | 补丁 `0002` 只补 `aarch64`/`arm64` 两条 CPU 规则与 `linux-ohos*` 的 KERNEL-OS 规则（+29 行） |
| `config.guess` 报 `cannot guess build type` | 同一份 2005 脚本；OHOS 的 `uname -s` 是 `HarmonyOS`，case 表里没有分支能命中 | 补丁 `0001` 插入 `*:HarmonyOS:*:*` 分支，输出 `aarch64-unknown-linux-ohos`（+10 行） |
| `encodedv` 无参数段错误（退出码 139） | popt 由 `AC_CHECK_LIB` 探测，缺失时 configure 只 WARN，工具被编译成没有 `HAVE_LIBPOPT`，启动时遍历空选项表 | `requires popt/1.16`，并在 configure 之后断言 `config.h` 里是 `#define HAVE_LIBPOPT`（不能只 grep 宏名：autoheader 的 `/* #undef HAVE_LIBPOPT */` 也含这个字符串） |
| `config.status` 临时目录不可写 | configure 用 `umask 077 && mktemp -d ./confXXXXXX`，HMDFS 忽略 chmod | `build()` 里把 `configure` 两处改成 `umask 000 && mkdir -p $TMPDIR/conf$$` |
| X / GTK / XVideo 不可用 | 默认开启 `playdv` 显示后端 | `--without-x --disable-gtk --disable-xv` |
| IDCT 汇编不兼容 | 内联汇编只针对 x86 | `--disable-asm` |
| 工具运行期找不到 `libdv.so` | 默认构建 `.so`，而 tools 包会删掉 `lib/` | `--disable-shared --enable-static` |
| 新二进制无法执行 | 鸿蒙安全机制要求 ELF 带 `.codesign` | `package()` 内调用 `llvm-objcopy` + `binary-sign-tool` 自签名 |

### 关于 configure 不被重新生成
libdv 用 `AM_MAINTAINER_MODE` 且默认关闭，`make` 不会触发 `autoconf`/`automake`，
所以这两个 `config.guess` / `config.sub` 补丁能稳定生效。这一点与 `libbs2b-tools`
正好相反：后者必须 `autoreconf -fi` 重新生成 `configure` 才能应用 `configure.ac` 补丁。

### 使用方式
```bash
encodedv --version
encodedv pond%%05d.ppm out.dv                 # PPM 序列 → DV
encodedv - audio.wav < frame.ppm > out.dv     # stdin/stdout
dubdv new.wav in.dv out.dv                    # 替换音轨
dvconnect -- - < capture.dv                   # FireWire 采集
```

### 验证结果
- `ohc-run.py conan-verify libdv-tools 1.0.0`: G0-G4 / L2 / L4 / L5 全绿
- `test_package/test.sh`: 12 项断言（`encodedv` 的 `--version`/`--help` 与真实
  popt 选项表、`dubdv --help`、三个工具无参数调用的退出码必须 < 128
  —— popt 缺失时会变成 139、未知选项必须被拒）