# mt-st 1.8 适配笔记

## 编译环境
- 构建系统: makefile（手写 Makefile，无 configure）
- 编译日期: 2026-09-23
- 编译器: clang 15（OHOS SDK 26.0.0.18）
- 状态: built

## 编译步骤

1. 从官方 codeload 取 tag `v1.8` 的源码包（`mt-st-1.8.tar.gz`）。
2. 直接 `make CC=<ohos clang> CFLAGS="-Wall -O2" -j1`，产出 `mt` 与 `stinit` 两个可执行文件。
3. 用内嵌的 shelltestrunner 兼容运行器执行上游 `tests/*.test`（31 例）。
4. `package()` 安装 `bin/mt`、`bin/stinit`、`share/man/man1/mt.1`、`share/man/man8/stinit.8`、示例配置与手册到 `share/mt-st/`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 `make check` 无法直接运行 | `make check` 调用 `shelltest`（shelltestrunner，Haskell 程序），OHOS 与 CI worker 都没有 | 内嵌一个零依赖的 format-1 兼容运行器，解析并执行同一批 `tests/*.test` 定义（含上游 Makefile 的 `-DVERSION=1.8` 宏替换语义） |
| 2 | 源码是否缺 OHOS 内核头？ | 该库使用 `mt.c`/`stinit.c` + 自带 `mtio.h`，并 `#include <linux/major.h>`、`<scsi/sg.h>` | OHOS SDK sysroot 已提供这两者，无需补丁 |
| 3 | `mt-errors.test` 中 `./mt -f /dev/null status` 失败 | 上游断言 glibc 对 `ENOTTY` 的文案 `Inappropriate ioctl for device`；OHOS libc 对同一 errno 返回 `Not a tty` | 仅放宽该条上游期望为 `/(Inappropriate ioctl for device|Not a tty)/`（补丁 0001），测试语义（ENOTTY + 退出码 2）不变 |

## 源码修改

| 文件 | 原因 | 方式 | 补丁状态 |
|------|------|------|----------|
| `tests/mt-errors.test` | OHOS libc 的 `ENOTTY` 文案与 glibc 不同 | 该条期望正则改为接受两种文案 | ✅ `patches/0001-tests-accept-ohos-enotty-text.patch` |

## 依赖版本

无三方依赖（仅 libc / OHOS sysroot 头文件）。

## 验证结果

```bash
# 上游测试（tests/*.test，shelltestrunner format 1，-DVERSION=1.8；含补丁 0001）
UPSTREAM TESTS: 31/31 passed, 0 failed

# 消费者（test_package/test_mt_st.sh）
MT_ST_CHECK_SUMMARY checks=8 fails=0
```

## 注意事项

- `mt`/`stinit` 的绝大多数命令需要真实的 SCSI 磁带设备与 `/sys/class/scsi_tape`；上游测试以「错误路径/用法」为主，因此无需磁带硬件即可全部通过。
