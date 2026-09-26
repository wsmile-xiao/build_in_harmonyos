# lcab 1.0b12 适配笔记

## 状态: built（conan create 通过，功能测试在 qemu-aarch64 下全绿）

## 编译环境

- 构建系统: autotools（发行包自带 configure，构建期不需要 autoconf/automake）
- 编译日期: 2026-09-20
- 编译器: OHOS clang 15.0.4（`aarch64-unknown-linux-ohos-clang`）
- Profile: `ci/conan/profiles/ohos-aarch64`（os=OHOS / arch=armv8 / libc++ / Release）
- 依赖: 无

## 编译步骤

```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# 内部等价于：
#   ./configure --host=aarch64-linux-ohos CC=<ndk>/aarch64-unknown-linux-ohos-clang
#   make && make install DESTDIR=<package_folder>
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `lcab -h` 打印 `v1.0b11`，与包版本 1.0b12 不符 | 上游 1.0b12 发行包忘记更新 `mytypes.h` 的 `VERSION` 宏 | 打 `0001-mytypes.h.patch`（与 Debian `20-version.patch` 同源） |
| 2 | 交叉编译产物无法在构建机上执行，test_package 的 `can_run()` 为假，测试被跳过 | host=OHOS/armv8，build=Linux/x86_64 | 额外用 `LDFLAGS=-static` 构建一份临时二进制，在 `qemu-aarch64` 下跑完整 test_package 脚本取得运行期证据（临时产物不入包） |
| 3 | 真机 CI 上 `config.status` 报 `./confstatXXXXXX/subs.sed: Permission denied`，随后 `make` 因无 Makefile 失败 | 旧版 configure 用 `umask 077` 在构建目录建临时目录；HMDFS 上该 0700 目录对同一进程不可写（知识 E011/E528） | `build()` 中 `replace_in_file` 把临时目录创建改为 `umask 000` 且优先落在 `$TMPDIR`（设备为应用私有 cache） |
| 4 | 真机 runner 本身是 aarch64，仍被传入 `--host=aarch64-linux-ohos`（R1/E205 禁止 native 传三元组） | `generate()` 仅按 `settings.os` 判断，未区分真实交叉 | 仅当构建机非 AArch64 时才追加 `--host`；真机走 native 路径 |
| 5 | CI #56257 编译、安装均通过，test_package 在真机报 `FAIL: file name not stored in cabinet`（同一脚本在 x86 GNU grep / busybox grep 下全绿） | 设备 grep（toybox）按行取 C 字符串匹配，cab 头部的 NUL 字节之后的文件名/数据对它不可见；GNU grep 按字节匹配二进制文件所以本地看不出 | 测试脚本改用 bash 内建 `read -d ''` 按 NUL 切段做字面量匹配（`cab_has`），不依赖设备 grep 实现；文本文件（`help.txt`/日志）仍用 grep |

无平台移植补丁：源码只用 POSIX 接口（`stdio.h`/`dirent.h`/`sys/stat.h`/`unistd.h`/`utime.h`），musl 全部提供，无需 `#ifdef __OHOS__` 守卫。

## 源码修改

- `mytypes.h`: `#define VERSION "1.0b11"` → `"1.0b12"`（补丁 0001）

## 依赖版本

无第三方依赖（W0 依赖发布检查：`requires` / `tool_requires` 均为空，无需预先发布任何包）。

## 上游测试清点（R51）

| 项 | 结果 | 证据 |
|---|---|---|
| `tests/` 目录 | 不存在 | 发行包仅 8 个 .c + 9 个 .h + autotools 骨架 |
| `TESTS` / `check_PROGRAMS` | 0 | `grep -n "TESTS\|check_PROGRAMS" Makefile.am Makefile.in` 无命中 |
| `make check` | 目标存在但无任何用例（automake 默认空目标） | `make check` 输出 `Nothing to be done` 级空跑 |

=> 上游无测试套件，因此测试完全由 test_package 补齐（见 `test_package/MANIFEST.yml`）：

- `test_lcab.sh`：5 组 CLI 场景 / 13 处断言。
- `test_roundtrip.py`（鸿蒙 PC 消费者用例，端到端）：在应用沙箱 `$TMPDIR`（真机为 HMDFS）下准备含中文文件名、多级目录、含 NUL 数据和跨 4 个 32 KiB CFDATA 块的项目目录 → `lcab -r` 打包 → 独立 MS-CAB 解析器读回、逐块重算校验和、逐文件按字节比对还原 → 篡改 1 字节必须被拒（4 处断言）。

## 验证结果

```bash
# 1) 交叉编译 + 打包
conan create .  ->  lcab/1.0b12  Package '6b129b0688...' created

# 2) 产物架构
file bin/lcab
#  ELF 64-bit LSB pie executable, ARM aarch64, dynamically linked,
#  interpreter /lib/ld-musl-aarch64.so.1, BIND_NOW, PIE

# 3) 功能测试（qemu-aarch64 运行同源静态构建）
bash test_package/test_lcab.sh
#  OK: usage banner reports v1.0b12
#  OK: single-file cabinet has MSCF header, file name and data
#  OK: multi-file cabinet built in quiet mode
#  OK: recursive mode packed nested file
#  OK: missing input handled gracefully
#  ALL LCAB TESTS PASSED

# 4) 鸿蒙 PC 消费者往返用例（NDK 静态重链副本经 qemu-aarch64；x86 原生副本同样通过）
python3 test_package/test_roundtrip.py <lcab>
#  OK: lcab -r packed 4 files into 103929 bytes
#  OK: MSCF header, 1 folder, 4 CFDATA blocks, all checksums valid
#  OK: every file extracted byte-for-byte (UTF-8 name, NUL data, multi-block file)
#  OK: single-byte corruption rejected by checksum
#  LCAB ROUNDTRIP CONSUMER TEST PASSED
# 反向：包装 lcab 使其写坏 cab 1 字节 -> FAIL: CFDATA checksum mismatch（rc=1）
```

qemu 跑的是同源静态重链副本，不等于交付的动态链接产物已实跑；交付产物的实跑以 AArch64 真机 CI 的 test_package 为准（x86 runner 上 test() 只断言 `bin/lcab` 存在）。

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/lcab` | aarch64-linux-ohos 可执行文件（musl，PIE，BIND_NOW） |
| `share/man/man1/lcab.1` | man 手册（上游 Makefile.am 不装，由 `package()` 复制） |
| `licenses/COPYING` | GPL-2.0-or-later |

## 注意事项

- 本包是纯命令行工具，不产出库：`package_type = "application"`，`cpp_info.libs/includedirs/libdirs` 均置空，仅保留 `bindirs`，并按 R38 在软件级目录提供 `commands.json`。
- 在设备上运行时，cabinet 文件名使用 CP/UTF 属性位，未做额外本地化适配（与上游行为一致）。
---

**编译结束**: 2026-09-20 05:30
**最终状态**: built
