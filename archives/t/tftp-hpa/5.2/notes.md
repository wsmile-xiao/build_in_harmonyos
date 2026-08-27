# tftp-hpa 5.2 适配笔记

## 编译环境
- 构建系统: autotools (configure + make)
- 编译日期: 2026-08-22
- 编译器: clang/clang++
- 状态: built

## 编译步骤

```bash
./configure --prefix=$DEFAULT_PREFIX
make -j1
make install INSTALLROOT=$TEST_PREFIX
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.status: could not setup config files machinery (Permission denied) | OHOS mktemp -d with umask 077 inherits setgid bit from parent dir | Patch configure: remove umask 077, add chmod g-s after mktemp |
| 2 | ld.lld: error: duplicate symbol: toplevel | tftp.c and main.c both define sigjmp_buf toplevel; lld stricter than GNU ld | Patch tftp/tftp.c: declare extern sigjmp_buf toplevel |

## 验证结果

```bash
$ ./tftp/tftp -V
tftp-hpa 5.2, without readline

$ ./tftpd/tftpd -V
tftp-hpa 5.2, with remap, without tcpwrappers
```

## 最终状态
最终状态: built (conan-verify + W3 local CI passed)
