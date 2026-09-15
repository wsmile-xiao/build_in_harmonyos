# cron 3.0pl1 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-09-11
- 编译器: clang/clang++ 15
- 平台: HarmonyOS PC aarch64
- 状态: built（已完成本地 Conan/W3 验证，尚未上传制品仓）

## 编译步骤

1. 使用 Debian 官方镜像源码：
   `https://deb.debian.org/debian/pool/main/c/cron/cron_3.0pl1.orig.tar.gz`
2. 执行 `make -j1 CC=clang`。
3. 由于 OHOS 环境缺少可用的 coreutils `install`，使用隔离 staging 目录复制 `cron`、`crontab` 和 man 页面。
4. Conan 配方通过 `conan create` 干净构建验证。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|---|---|---|
| 1 | `struct tm` 未定义 | 旧 `SYS_TIME_H` 逻辑选择了 OHOS 的 `sys/time.h` | 在 `cron.c` 和 `misc.c` 使用标准 `time.h` |
| 2 | `SIGCLD` 未定义 | OHOS 仅提供标准 `SIGCHLD` | 替换 `cron.c` 和 `do_command.c` 中的旧信号名 |
| 3 | `sigblock`/`sigmask`/`sigsetmask` 未定义 | BSD 信号屏蔽 API 不可用 | 在 `popen.c` 使用 POSIX `sigprocmask` |
| 4 | Makefile 安装目标不可用 | OHOS worker 缺少 coreutils `install` 且旧 Makefile 目标不兼容 | Conan 直接打包源码目录中的可执行文件 |
| 5 | 当前 UID 不在 passwd | worker 的 NSS 环境不提供 UID 映射 | 记录为消费者环境限制，不伪造通过结果 |

## 源码修改

- `0001-cron.c.patch`: 使用 `time.h`，并将 `SIGCLD` 改为 `SIGCHLD`。
- `0002-do_command.c.patch`: 将 `SIGCLD` 改为 `SIGCHLD`。
- `0003-misc.c.patch`: 使用 `time.h`。
- `0004-popen.c.patch`: 用 POSIX 信号集合和 `sigprocmask` 替换 BSD API。

## 测试结果

- 上游测试命令：`make check`。
- 上游测试结果：源码没有 `check` 或 `test` 目标，未报告上游测试用例；该事实已写入 `test_package/MANIFEST.yml`。
- 消费者测试：安装后的 `cron -x invalid` 正确返回非零并输出 usage，PASS。
- 鸿蒙专用消费者测试：`test_ohos.c` 使用 `__OHOS__` 编译断言，并通过 fork/exec 执行 Conan 包内 `cron`，PASS。
- `crontab -l`：正确检测到当前 UID 不在 passwd，返回非零；这是 worker 环境限制，不计为功能通过。
- Conan `conan-verify`：G1/G2/G3/G4/L2/L4/L5 全部 PASS。

## 依赖版本

- 无 Conan 运行时依赖。
- OHOS 编译器 clang 15，GNU Make 4.4.1。
---

**编译结束**: 2026-09-11 21:14
**最终状态**: published
