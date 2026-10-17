# libfreeaptx-tools 0.2.2 适配笔记

## 编译环境
- 构建系统: 纯 POSIX Makefile（无 configure、无 CMake/Meson）
- 编译日期: 2026-09-16
- 编译器: clang 15.0.4
- 依赖: 无（两个工具都是自包含静态链接，除去 libc 之外没有任何 NEEDED 项）

## 本包与库包的分工

| 归档 | 交付物 |
|------|--------|
| archives/l/libfreeaptx/0.2.2 | libfreeaptx.so.0.2.2 及其符号链接、freeaptx.h、libfreeaptx.pc |
| archives/l/libfreeaptx-tools/0.2.2 | bin/freeaptxenc、bin/freeaptxdec |

`package()` 里删掉 `include/ lib/ share/`，保证同一个文件只有一个属主。

## 关键问题

| # | 问题 | 根因 | 处理 |
|---|------|------|------|
| 1 | 工具删掉 lib/ 后加载期直接失败，退出码 127 | Makefile 用 `$(UTILITIES): $(LIBNAME)` + `.o:` 规则 `$(CC) ... -o $@ $< $(LIBNAME)` 把工具链到共享库上，生成的二进制带 `DT_NEEDED libfreeaptx.so.0` 且没有 RUNPATH | 补丁 0001 改成 `$(CC) $(CFLAGS) $(CPPFLAGS) $(LDFLAGS) -I. -o $@ $@.o $(SOURCES)`，工具直接吃 freeaptx.c，二进制自包含 |
| 2 | `make freeaptxenc.static` 报 "No rule to make target" | 上游声明了 `STATIC_UTILITIES = $(NAME)enc.static $(NAME)dec.static` 和 `.SUFFIXES: .o .c .static`，但没有 `.c.static:` 规则 | 不指望上游的静态目标，改链接规则（见 #1） |
| 3 | 交叉编译时无法从外部注入 CFLAGS | Makefile 里 `CFLAGS = -W -Wall -O3` 是普通赋值，会盖掉环境变量 | conanfile 里以 make 命令行变量传 `CFLAGS="-W -Wall -O3 -fPIC"`（命令行赋值优先级最高） |
| 4 | 默认 `make` 会顺带编出用不到的 libfreeaptx.so | `default: $(SOFILENAME) $(SONAME) $(LIBNAME) $(UTILITIES) $(HEADERS)`；`install` 也会把它、头文件和 .pc 一起装进包里 | 补丁 0001 把 `default` 收窄成 `$(UTILITIES) $(HEADERS)`，`install` 只装 bin/ |
| 5 | L2 冒烟失败 | 两个工具只认 -h/--help 与 --hd：--help/-h 都 `return 1`，未识别选项（含 --version）也 `return 1` | 补丁 0002 补 -V/--version（退出 0），并把 -h/--help 改成退出 0 |
| 6 | 新二进制无法执行 | 鸿蒙安全机制要求 ELF 带 `.codesign` | `package()` 内调用 `llvm-objcopy` + `binary-sign-tool` 自签名 |
| 7 | 上游源码地址失效 | 库包 manifest 登记的 savannah 地址已 404 | conandata 用维护者本人仓库的 tag tar.gz（sha256 已固定） |

## 构建步骤

1. `get()` 下载 0.2.2.tar.gz（sha256 `5ab5ebdd...`）并应用补丁 0001/0002
2. `make -j1 CC=<conan conf 里的编译器> CFLAGS="-W -Wall -O3 -fPIC"`
3. `make install DESTDIR=<package_folder> PREFIX=/` → 只产生 `<package_folder>/bin/`
4. ELF 自签名
5. 断言 `bin/freeaptxenc` 与 `bin/freeaptxdec` 都存在

## 验证方式

- `ohc-run.py conan-verify libfreeaptx-tools 0.2.2`：G0-G4 / L2 / L4 / L5
- `test_package/test.sh`：16 项断言 —— 两个工具的 `--version`/`--help`/`-V` 退出码契约、
  `readelf -d` 确认没有 `libfreeaptx` 的 DT_NEEDED 项、
  4800 字节 24bit 立体声 PCM 走 aptX 得到 892 字节（800 + 92 帧发送缓冲）后解回原长度
  且平均绝对误差 2898（约 0.03% 满量程）、同样的输入走 aptX HD 得到 1338 字节
  （1200 + 138 帧发送缓冲）、未知选项与非 aptX 数据流都必须非 0 退出

## 端到端实测（x86_64 Linux，gcc，仅用于确认补丁语义）

```
$ patch -p1 < 0001-Makefile-static-tools.patch   # patching file Makefile
$ patch -p1 < 0002-cli-version-help.patch        # patching file freeaptxdec.c, freeaptxenc.c
$ make -j1 CC=gcc CFLAGS="-W -Wall -O3 -fPIC"
gcc -W -Wall -O3 -fPIC  -I. -c -o freeaptxenc.o freeaptxenc.c
gcc -W -Wall -O3 -fPIC  -s -I. -o freeaptxenc freeaptxenc.o freeaptx.c
$ readelf -d freeaptxenc | grep NEEDED
 0x0000000000000001 (NEEDED)   Shared library: [libc.so.6]      # 没有 libfreeaptx.so.0
$ make install DESTDIR=/tmp/pkg PREFIX=/
$ find /tmp/pkg -type f
/tmp/pkg/bin/freeaptxdec
/tmp/pkg/bin/freeaptxenc
```

## 未决 / 注意

- 上游没有测试套件（Makefile 里没有 check/test 目标，README 只给了手工 sox 管道示例），
  test_package 是本包唯一的自动化验证
- 本包不安装 man 页（上游 tar.gz 里就没有 man 目录，Debian 的 man 页来自 debian/ 打包目录）