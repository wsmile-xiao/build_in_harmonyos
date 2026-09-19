# libfreeaptx-tools

`freeaptxenc` + `freeaptxdec` —— libfreeaptx 自带的两条命令行工具。

## Description

- `freeaptxenc`：把原始 24 bit signed 立体声 PCM 从 stdin 编成 aptX（6:1）
  或 aptX HD（4:1）写到 stdout，`--hd` 切换高清模式。
- `freeaptxdec`：反向解码，遇到损坏的流会自动重新同步并尽量恢复，输入不是
  aptX 数据时以非 0 退出。

## Project URL
https://github.com/regularhunter/libfreeaptx

## License
LGPL-2.1-or-later

## HarmonyOS 适配说明

### 构建信息
- **版本**: 0.2.2（与库包 `libfreeaptx/0.2.2` 同源同版本）
- **构建系统**: 纯 POSIX Makefile（无 configure）
- **编译器**: clang 15.0.4
- **依赖**: 无（两个工具都自包含，除 libc 外没有任何动态依赖）

### 与库包的分工
`archives/l/libfreeaptx/0.2.2` 负责 `libfreeaptx.so`、`freeaptx.h` 与
`libfreeaptx.pc`；本包只负责 `bin/freeaptxenc`、`bin/freeaptxdec`，
`package()` 里删掉 `include/ lib/ share/`，保证同一个文件只有一个属主。

### 平台限制与补丁
| 问题 | 根因 | 处理 |
|------|------|------|
| 工具删掉 `lib/` 后在加载期直接失败（退出码 127） | Makefile 的 `$(UTILITIES): $(LIBNAME)` + `.o:` 规则把工具链到共享库上，生成的二进制带 `DT_NEEDED libfreeaptx.so.0` 且没有 RUNPATH | 补丁 `0001` 改成直接由 `$@.o` + `freeaptx.c` 链接，二进制自包含 |
| `make freeaptxenc.static` 报 "No rule to make target" | 上游声明了 `STATIC_UTILITIES` 和 `.SUFFIXES: .o .c .static`，却没有 `.c.static:` 规则 | 上游的静态工具目标是空壳，改链接规则而不是补它 |
| 交叉编译注入不了 CFLAGS | Makefile 里 `CFLAGS = -W -Wall -O3` 会盖掉环境变量 | 以 make 命令行变量传 `CFLAGS="-W -Wall -O3 -fPIC"` |
| 默认 `make` 顺带编出用不到的 `.so` | `default:` 里带上了 `$(SOFILENAME) $(SONAME) $(LIBNAME)`，`install` 也一并安装 | 补丁 `0001` 把 `default` 收窄到工具，`install` 只装 `bin/` |
| L2 冒烟失败 | 两个工具只认 `-h/--help` 与 `--hd`，`--help`/`-h` 与未知选项一律 `return 1` | 补丁 `0002` 补 `-V/--version`（退出 0），`--help`/`-h` 也改成退出 0 |
| 新二进制无法执行 | 鸿蒙安全机制要求 ELF 带 `.codesign` | `package()` 内调用 `llvm-objcopy` + `binary-sign-tool` 自签名 |
| 上游源码地址失效 | 库包 manifest 登记的 savannah 地址已 404 | conandata 改用维护者本人仓库的 tag tar.gz（sha256 已固定） |

### 使用方式
```bash
sox sample.wav -t raw -r 44.1k -L -e s -b 24 -c 2 - | freeaptxenc > sample.aptx
freeaptxdec < sample.aptx | sox -t raw -r 44.1k -L -e s -b 24 -c 2 - sample.wav
freeaptxenc --hd < sample.s24le > sample.aptxhd
freeaptxenc --version
```

### 验证结果
- `ohc-run.py conan-verify libfreeaptx-tools 0.2.2`: G0-G4 / L2 / L4 / L5
- `test_package/test.sh`: 16 项断言（`--version`/`--help`/`-V` 退出码契约、
  `readelf -d` 确认没有 `libfreeaptx` 的 DT_NEEDED、
  4800 字节 PCM 的 aptX 与 aptX HD 往返及精确字节数、
  解码结果有损但平均绝对误差仅 2898、未知选项与非 aptX 流被拒绝）