# 上游测试真实执行证据 — liblzxcomp 20050705

本文件记录**上游官方测试程序 `lzx_test.c` 的真实执行证据**（R34/R51 要求：测试必须真实执行，
不能只声称）。所有命令与输出均为实测原样粘贴。

---

## 1. 源码与测试程序溯源

| 项目 | 值 |
|------|-----|
| 源码包 URL | https://mirrors.ustc.edu.cn/freebsd-ports/distfiles/lzx_compress.tar.gz |
| 源码包 sha256 | `d63f046130677db666d6cec6f4a62349060928ec85b1feaf2fce9222293a95f7` |
| 上游测试程序 | `lzx_compress/lzx_test.c` |
| `lzx_test.c` sha256 | `217d2002d7f71586ddf1d45c6fbdb1d05055fd29d7df5b4deb763c98a061dad2` |
| 归档副本 | `test_package/lzx_test.c`（**字节级一致，未改动一行**，sha256 相同） |

上游发行包只有 1 个测试程序（Makefile 提供 `lzx_test`（slide 变体）与 `lzx_test2`（nonslide 变体，
即 `liblzxcomp.a` 的对象集）两个目标），**没有**单元测试框架 / `check` 目标 / `ctest`：

```
$ tar tzf lzx_compress.tar.gz
./lzx_compress/ChangeLog          ./lzx_compress/lzx_compress.h
./lzx_compress/COPYING            ./lzx_compress/lzx_compress.man3
./lzx_compress/hash_slide.c       ./lzx_compress/lzx_compress.mdoc3
./lzx_compress/hash_slide.h       ./lzx_compress/lzx_config.h
./lzx_compress/lz_nonslide.c      ./lzx_compress/lzx_constants.h
./lzx_compress/lz_nonslide.h      ./lzx_compress/lzx_layer.c
./lzx_compress/lz_slide.c         ./lzx_compress/lzx_test.c
./lzx_compress/lz_slide.h         ./lzx_compress/Makefile

$ grep -nE '^(all|check|test|lzx_test)' Makefile
19:all: liblzxcomp.a
41:lzx_test: lzx_test.o $(OBJS)
44:lzx_test2: lzx_test.o $(OBJS2)
```

---

## 2. 原生（x86_64）真实执行

环境：WSL2 Ubuntu / gcc 11.4.0 / GNU make。

### 2.1 打全 3 个补丁并构建

```
$ patch -p1 < patches/0003-lzx_config.h.patch   # 字节序探测改用编译器内建宏
$ patch -p1 < patches/0002-lz_nonslide.h.patch  # 补 u_char typedef (musl/OHOS)
$ patch -p1 < patches/0001-lz_nonslide.c.patch  # 修 64 位堆溢出 (sizeof(*lentab))

$ sha256sum lzx_config.h lz_nonslide.h lz_nonslide.c
5f18b60f52c927a468e94148ce42c233738e16bdbac2c94ef0b16961e4ccec44  lzx_config.h
f1e94ed6ed834315f1c70d3c451e4de96c940447e26a084bdc3a89dc6a1e8a3c  lz_nonslide.h
c63426a84fd869b2704f1fee86b4bcac0ec289a60cbd309316616c75ab8979ad  lz_nonslide.c

$ make CC=gcc AR=ar RANLIB=ranlib -j1
ar -q liblzxcomp.a lzx_layer_nonslide.o lz_nonslide.o
ranlib liblzxcomp.a
-rw-r--r-- 1 root root 75310 liblzxcomp.a
```

### 2.2 按上游 Makefile `lzx_test2` 目标的方式运行上游测试程序

```
$ cc -I. lzx_test.c liblzxcomp.a -lm -o lzx_test2
$ ./lzx_test2 15 < upstream_in.bin > upstream_out.bin
compressed: 896, uncompressed 163840, ratio 99.453125
$ echo $?
0
$ stat -c%s upstream_in.bin upstream_out.bin
145600
900          # = 896 字节压缩流 + 4 字节未压缩长度前缀
```

未打 `patches/0001-lz_nonslide.c.patch` 时同一测试程序在 64 位平台堆崩溃（`memset` 元素尺寸
错误导致 2 倍溢出），即该用例确实覆盖了本适配修复的缺陷。

---

## 3. CI 内执行（OHOS aarch64）— 本 PR 新增

自本 PR 起，上游测试程序不再是"仅本地跑过一次"，而是**随 `conan create` 在 CI worker
（OpenHarmony / aarch64）上每次真实执行**：

- `test_package/lzx_test.c` — 上游 `lzx_test.c` 字节级副本（sha256 `217d2002…dad2`）
- `test_package/CMakeLists.txt` — 以 `lzx_test2` 为名构建，链接 `liblzxcomp::liblzxcomp`
  （与上游 Makefile `lzx_test2` 目标的链接对象集一致）；配置阶段用 `string(REPEAT)` +
  `file(WRITE)` 生成确定性语料 `upstream_in.bin`（145600 字节，无外部命令依赖）
- `test_package/conanfile.py` — `test()` 中重定向 stdin/stdout 执行
  `"lzx_test2" 15 < upstream_in.bin > upstream_out.bin`，并断言退出码 0、
  输出 > 4 字节（长度前缀）且小于输入

本机（x86_64，同一份归档）以 `conan create` 端到端复现，退出码 0：

```
======== Testing the package: Executing test ========
liblzxcomp/20050705 (test package): RUN: ./test_liblzxcomp
compressed: 1372, uncompressed 524288
test liblzxcomp 20050705: OK (in=524288 out=1372)

liblzxcomp/20050705 (test package): RUN: "./lzx_test2" 15 < "./upstream_in.bin" > "./upstream_out.bin"
compressed: 896, uncompressed 163840, ratio 99.453125

liblzxcomp/20050705 (test package): upstream lzx_test.c: PASS (in=145600 out=900, ratio 99.38%)
```

### 3.1 CI L1e 破坏性反向验证（本地同构复现）

CI 的 L1e 会移走包产物（`lib/`、`include/`）后重跑 `conan test`，要求测试**失败**，
以证明测试真实依赖被测包。本地同构复现：

```
$ mv <pkg>/lib <bak>/lib && mv <pkg>/include <bak>/include
$ conan test test_package liblzxcomp/20050705 -pr default --build=missing
CMake Error at .../cmakedeps_macros.cmake:81 (message):
  Library 'lzxcomp' not found in package. ...
ERROR: liblzxcomp/20050705 (test package): Error in build() method, line 45
	cmake.configure()
ConanException: Error 1 while executing
$ echo $?
1        # 非 0 → L1e PASS（测试真依赖被测包，非空壳）
```

---

## 4. 通过率

| 项目 | 用例数 | 执行数 | 通过 | 通过率 |
|------|--------|--------|------|--------|
| 上游 `lzx_test.c`（集成/自测程序） | 1 | 1 | 1 | **100% (1/1)** |
| 鸿蒙特有消费者测试 `test.c` | 1 | 1 | 1 | **100% (1/1)** |

> 说明：`lzx_test.c` 的 stderr 统计中 `uncompressed` 为块对齐值（上游按 `1 << window_size`
> 整块读取），故 145600 字节输入报告为 163840；这是上游程序自身的行为，非适配改动。
