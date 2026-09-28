# linuxptp 4.4 适配笔记

## 编译环境
- 构建系统: makefile（上游单 Makefile，无 configure/CMake/meson）
- 编译日期: 2026-09-26
- 编译器: clang（OHOS SDK 15，`tools.build:compiler_executables` 经 Conan conf 注入）
- 目标平台: OHOS / aarch64（设备原生编译，非交叉）
- 状态: published

## 编译步骤

```bash
# 1) 拉取上游源码包（sha256 已校验）
#    https://downloads.nwtime.org/linuxptp/linuxptp-4.4.tgz
#    277069 bytes, sha256=61757bc0a58d789b8fcbdddf56c88a0230597184a70dcb2ac05b4c6b619f7d5c

# 2) 设备原生编译（关键：两处环境适配，见下节）
export PATH=/data/service/hnp/bin:$PATH
KBUILD_OUTPUT=/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot \
  make -j1 CC=clang EXTRA_CFLAGS="-D__MUSL__"

# 3) 补全单元测试（上游无测试，路径 B）
clang -Wall -D_GNU_SOURCE -DVER=4.4 -D__MUSL__ -I. tests/test_linuxptp_units.c \
      filter.o mave.o mmedian.o hash.o lstab.o tsproc.o print.o util.o phc.o sk.o \
      -lm -lrt -pthread -o linuxptp_units
./linuxptp_units
```

产物（9 个可执行文件，与 Makefile 的 `PRG` 一致）:
`ptp4l hwstamp_ctl nsm phc2sys phc_ctl pmc timemaster ts2phc tz2alt`，
另有 9 个 man8 手册随包分发。**无需任何源码补丁。**

## 上游测试清点（R51 第 1 步）

上游 4.4 **完全没有测试**，三条原始证据：

```
$ find . -iname "*test*"          # 全树
(count=0)

$ make -n check
.//incdefs.sh[195]: [: Kernel: unexpected operator/operand      # 未设 KBUILD_OUTPUT 时的告警
grep: /usr/include/linux/net_tstamp.h: No such file or directory
make: *** No rule to make target 'check'.  Stop.

$ make -n test
（同上：No rule to make target 'test'）

$ ls -d CMakeLists.txt meson.build configure Makefile
ls: CMakeLists.txt: No such file or directory
ls: meson.build: No such file or directory
ls: configure: No such file or directory
Makefile
```

结论：无 tests/ 目录、无 check/test 目标、无 ctest/pytest 注册 → 走 **路径 B 补全测试**（见下）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `missing.h` 重定义 `HWTSTAMP_TX_ONESTEP_SYNC` / `HWTSTAMP_TX_ONESTEP_P2P` | `incdefs.sh` 把内核头文件探测路径写死为宿主 `/usr/include`；OHOS 宿主无 `/usr/include`，`grep` 全部失败 → `HAVE_ONESTEP_SYNC`/`HAVE_ONESTEP_P2P` 未定义 → `missing.h` 再定义已被 sysroot `<linux/net_tstamp.h>` 定义的枚举 | 按上游自身跨编译钩子设置 `KBUILD_OUTPUT=<ohos sysroot>`（incdefs.sh 显式读取该变量，同时附带给 `-I<sysroot>/usr/include`）；修复后 `make -n 2>&1 \| grep -ci "no such file"` = **0** |
| 2 | `struct sockaddr_storage` 重定义（`sys/socket.h` vs `linux/socket.h`） | OHOS sysroot 的 `<sys/socket.h>` 用 `#ifndef __MUSL__` 守卫该结构，而 `<linux/socket.h>` 无条件定义；SDK 自带编译器驱动 `aarch64-unknown-linux-ohos-clang` 总是预定义 `__MUSL__=1` 保持一致，而 profile 中的裸 `clang` 定义为 `0` → 二者同时可见即冲突 | 配方在 `os == "OHOS"` 时显式加 `-D__MUSL__`（知识库 E091 的 define-guard 修复思路；E119 macro-guard-skip-header 同源） |
| 3 | `make` 默认用 `gcc` | Makefile 硬编码 `CC = $(CROSS_COMPILE)gcc`，OHOS 无 gcc（`gcc: inaccessible or not found`） | `make CC="<conan conf 中的 c 编译器>"`，禁用裸 `${CC}` 环境变量（R33） |
| 4 | `make install` 不可用 | OHOS 无 `install(1)`（`command -v install` 无输出） | `package()` 直接 `copy()` 产物到 `<prefix>/bin` 并 `chmod 0755`；man8 一并入包 |

## 源码修改

**无。** 本次适配未修改任何上游源码，`patches_applied: []`，`conandata.yml` 无 `patches:` 段。
两处适配均通过构建期环境变量/编译选项完成（`KBUILD_OUTPUT`、`-D__MUSL__`），不改上游文件，
因此无需 `patches/` 目录。

## 依赖版本

上游 4.4 只依赖系统 C 库与内核 UAPI 头文件（`-lm -lrt -pthread`），**无任何 conan 依赖**：
`dependencies: []`。

## 补全测试用例（路径 B，R51 第 2/3 步）

上游无测试，故本移植贡献单元测试 `tests/test_linuxptp_units.c`，在 `build()` 内编译并实跑，
直接链接上游 `make` 产出的对象文件，覆盖核心算法 API（意图：确定性断言，非空壳）：

| 覆盖模块 | 断言内容 |
|----------|----------|
| tmv | 加减/比较/符号/零判定；`tmv_to_Timestamp`（sec/nsec）；`timestamp_to_tmv`（线格式）；`tmv_to_TimeInterval`（±2^16） |
| filter/mave | 长度 4 滑动均值逐步为 100/150/200/250/325；`filter_reset` 后窗口重启 |
| filter/mmedian | 长度 3 中位数（1→1、1,5→3、1,3,5→3、窗口滑出→5）；长度 2 取两中值整数均值；`length=0` 拒绝 |
| hash | `hash_create`、插入、**重复 key 拒绝**、三 key 查找、缺失 key 为 NULL、销毁回调计数=3 |
| lstab | 闰秒表 `LSTAB_OK`(2020-01-01→TAI-UTC 37)、`LSTAB_AMBIGUOUS`(闰秒前 1 秒→36)、`LSTAB_EXPIRED`(超出 24 Dec 2024)、`LSTAB_UNKNOWN`(表前时间，off 不被写入)、缺文件创建被拒 |
| tsproc | `TSPROC_RAW` 原始路径：delay=25 ns、offset=175 ns、单位权重；`tsproc_reset` 后返回 -1；`TSPROC_RAW` 零时延→偏差 0；未知 mode / 零长度滤波器被拒 |

实测输出：`=== linuxptp supplementary unit tests: 67/67 checks passed ===` / `RESULT: PASS`。

## 验证结果

```bash
# 设备原生编译（9 个可执行文件）
$ ls -l ptp4l pmc phc2sys ts2phc
-rwxrwx--- 1 ... 354752 ptp4l
-rwxrwx--- 1 ... 182720 pmc
-rwxrwx--- 1 ... 219584 phc2sys
-rwxrwx--- 1 ... 231872 ts2phc
$ file ptp4l
ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped

# 补全单元测试
$ ./linuxptp_units
=== linuxptp supplementary unit tests: 67/67 checks passed ===
RESULT: PASS

# 九个二进制本机可运行（统一用 -v，均 rc=0 且报告 4.4）
$ for b in ptp4l hwstamp_ctl nsm phc2sys phc_ctl pmc timemaster ts2phc tz2alt; do ./$b -v; done
4.4                               # 九个同，rc=0
$ ./ts2phc -h; echo rc=$?
usage: ts2phc [options]
rc=255                            # ts2phc.c:683 对未知选项 return -1（上游既定行为）

# ptp4l 真实功能路径（异常网卡必须报错退出）
$ ptp4l -f cfg -i no_such_interface_0 -m ; echo rc=$?
failed to create a clock
rc=255
```

## 注意事项

1. `KBUILD_OUTPUT` 是本配方的**关键**环境变量：它同时承担 incdefs.sh 的内核头文件探测根
   与 `-I<sysroot>/usr/include` 的注入。缺少它会在 arm64 上编译失败（`HWTSTAMP_TX_ONESTEP_*`
   重定义）。CI clean 环境中该路径由 `_sysroot()` 从 Conan conf 的编译器位置推导，
   回退到已安装 SDK 布局，并要求 `<sysroot>/usr/include/linux/net_tstamp.h` 真实存在。
2. `-D__MUSL__` 只在 `os == "OHOS"` 时加；glibc 下加它会与 `<sys/socket.h>` 语义冲突。
3. 上游二进制**不支持 `--version`**（返回 `unrecognized option: version`），平台 smoke 统一用 `-v`
   （九个工具 `-v` 均 rc=0 并报告 4.4）；其中八个工具 `-h` 返回 0，`ts2phc -h` 上游返回 **255**
   （`ts2phc.c:683` 对未知选项 `return -1`），属既定行为，测试中对该返回码做显式断言。
4. `-lrt` 在 OHOS sysroot 中存在且链接正常；`-pthread` 亦正常。
5. 上游默认闰秒表有效期至 2024-12-24（`lstab.c` 的 `expiration_date_ntp`），运行期超出会得到
   `LSTAB_EXPIRED`——这是**上游行为**，非移植缺陷；单元测试对此作了显式断言。

## 对话记录

### 对话 #1（2026-09-26，OHOS PC / aarch64 设备原生）

- 环境：HarmonyOS PC 本机（OHOS 6.0 / aarch64），OHOS SDK 封装编译器
  `aarch64-unknown-linux-ohos-clang`，Conan 2.29.1 + `ci/conan/profiles/ohos-aarch64`。
- 设备原生编译验证：先行探索式编译确认 `KBUILD_OUTPUT` 是必需项，随后 `make -j2` 成功，
  产出 9 个 aarch64 ELF 可执行文件与 9 个 man8 手册。
- 上游无测试（`make check` → `No rule to make target 'check'`；无 `tests/`；无 `Makefile.am`），
  按 R51 走路径 B：补全 `tests/test_linuxptp_units.c`，在设备原生执行 67/67 通过。
- W3 本地 CI 模拟（prdiff 模式，仅本包文件）通过；conan-verify G1–G4 与 L2/L4/L5 通过；
  `conan create` 干净构建通过；归档状态 published。
---


**编译结束**: 2026-09-26 22:38
**最终状态**: published
---

**编译结束**: 2026-09-26 22:53
**最终状态**: published
