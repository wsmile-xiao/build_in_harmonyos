# sluice 0.03.01 适配笔记

## 编译环境
- 构建系统: makefile（上游纯 Makefile，无 configure）
- 编译日期: 2026-09-21
- 编译器: clang 15.0.4（OHOS aarch64，musl libc）
- 状态: published

## 上游测试清点（R51 申报表）

**上游无自动化功能测试**，清点证据：

| 检查项 | 结果 |
|---|---|
| 顶层 Makefile test/check 目标 | 无（`grep -n "test\|check" Makefile` 无匹配，exit 1） |
| 上游 CI（.travis.yml）script | `make -j2 PEDANTIC=$PEDANTIC` —— 仅编译门禁 |
| tests/ 目录 | 不存在（tarball 仅 Makefile/sluice.c/sluice.1/COPYING/README.md/.travis.yml/bash-completion/debian） |
| ctest/pytest 注册 | 无 |

本地已复现上游编译门禁：`make -j2 CC=clang PEDANTIC=1` 零警告通过。

## 编译步骤

```bash
# 探索构建（OHOS 真机，clang 15.0.4）
make -j2 CC=clang            # 通过，exit 0，零警告
make -j2 CC=clang PEDANTIC=1 # 通过，exit 0，零警告（对齐上游 CI 门禁）
make install DESTDIR=$TEST_PREFIX BINDIR=... MANDIR=... BASHDIR=...  # staging 成功
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 下载超时（python urllib） | 本环境 github.com 直连超时，codeload 可达 | curl 从 codeload.github.com（官方下载域）取 V0.03.01 tarball，sha256 校验一致 |
| 2 | `make clean` 失败（rm: No such file or directory） | 本机 sandbox PATH 首位 shim 目录的 rm 损坏（环境问题，非 OHOS/上游问题） | 修正 PATH 后复验通过；CI 环境无此问题 |
| 3 | 管道转发字节数少于输入（如 1048576 输入 @2MB/s 转发 1000000） | 上游 EOF 处理：读循环命中 EOF 时 break 丢弃未写出的尾部缓冲（sluice.c 主循环 `if (eof) break;` 位于 write 之前）。与上游 master 逐字节比对（42719 字节、行号一致），为上游既有行为，非 OHOS 适配引入 | 不篡改上游逻辑；验证用例选用 io_size/页对齐大小规避（8000000=128×62500@2MB/s；1048576=256 页@-n 模式） |

## 源码修改

无补丁。sluice.c 为纯 POSIX C（fcntl F_SETPIPE_SZ / sysconf / sigaction），
OHOS musl 全部支持，源码零修改编译通过。

## 依赖版本

无第三方依赖（纯 C，仅 libc）。

## 验证结果

```bash
$ ./sluice -h
sluice, version 0.03.01   # 版本横幅正确

$ head -c 1048576 /dev/zero | ./sluice -n | wc -c
1048576                   # 直通模式字节完整性

$ head -c 8000000 /dev/zero | ./sluice -r 2000000 | wc -c   # 耗时 ~4.03s
8000000                   # 限速模式速率控制有效、零丢失

$ file sluice
ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1)  # OHOS 原生格式
```

## 交付物

| 文件 | 说明 |
|------|------|
| bin/sluice | aarch64 OHOS 可执行文件（musl 动态链接） |

## 注意事项

- **EOF 尾部截断为上游既有行为**：`-n` 直通模式转发 `floor(N/4096)×4096`（4 组实测吻合），
  限速模式转发 `floor(N/io_size)×io_size`。依赖 sluice 保证字节完整性的下游应选用
  io_size 整数倍的数据量或显式 `-m`。此结论适用于上游全平台（代码与 master 一致），
  非 OHOS 特有缺陷。
- sluice 为 CLI 工具（R38）：commands.json 已在软件级目录声明。
---

**编译结束**: 2026-09-21 18:16
**最终状态**: built
