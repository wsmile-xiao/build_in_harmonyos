# s-nail 14.9.25 适配笔记

## 编译环境
- 构建系统: makefile（s-nail 自有 make 体系，非 autotools；`make config` 全非交互特性探测）
- 编译日期: 2026-09-22
- 编译器: clang 15（/data/service/hnp/bin/clang）
- 状态: built

## 编译步骤

```bash
# 配置（非交互；上游 os_setup 直接识别 HarmonyOS；可选特性 openssl/idna 缺库自动禁用）
PATH="$PATH:/system/bin" make CC=clang OPT_DOTLOCK=no config
# 构建（产物 .obj/s-nail）
PATH="$PATH:/system/bin" make CC=clang OPT_DOTLOCK=no -j1
# 上游测试套件（mx-test.sh --check，套件自身计数 TOTAL=PASS+FAIL+SKIP）
PATH="$PATH:/system/bin" make CC=clang OPT_DOTLOCK=no testnj
```

- `OPT_DOTLOCK=no`：dotlock 辅助程序需要 setuid root 安装，OHOS 单端不可用。
- PATH 追加 `/system/bin`：`make config` 硬性探测 chown(1)，测试需要 cksum(1)；
  二者都在 toybox 工具集（/system/bin），不在构建环境默认 PATH 内。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 启动即 `Panic: Cannot associate a name with uid 20020085`（SIGABRT） | OHOS 应用域 UID 无 /etc/passwd 条目，`getpwuid()` 返回 NULL 即 panic（src/mx/main.c） | 补丁 0001：LOGNAME/USER/HOME 综合身份回退 |
| 2 | Maildir 层级 mkdir 后创建子目录 EACCES，目录落盘 `drwx--S---`(2700) | s-nail 默认 umask=0077（gen-okeys.h）；HMDFS 对 umask 0077 下创建的目录剥掉组权限位，且目录属主映射为共享身份，进程自身反成"其他" | 补丁 0002：n_path_mkdir 创建目录时作用域化放宽 umask 至 0022（目录内文件仍受原 umask 约束） |
| 3 | Maildir 投递 `link()` 失败（Cannot link .tmdir/tmp/... to new/...） | HMDFS 完全不支持硬链接 | 补丁 0003：tmp→new 投递与 new→cur 状态迁移两处 link()+unlink() 在 link(2) 失败时回退 rename(2)（同文件系统原子等价） |

## 源码修改

| 补丁 | 文件 | 内容 |
|---|---|---|
| patches/0002-src-mx-main.c.patch | src/mx/main.c | getpwuid 失败时合成 passwd 身份（LOGNAME→USER→"unknown"，HOME→"/"），不再 panic |
| patches/0003-src-mx-path.c.patch | src/mx/path.c | n_path_mkdir 以临时 umask(0022) 作用域创建目录，规避 HMDFS 属主映射下的自访问拒绝 |
| patches/0001-src-mx-maildir.c.patch | src/mx/maildir.c | Maildir 投递与 new→cur 迁移两处 link(2) 失败回退 rename(2) |

## 依赖版本

- 无外部库依赖（缺省）：libc(musl) 提供 iconv/regex。
- 可选特性在设备上的探测结果：iconv=libc 启用；openssl(TLS)/S-MIME 禁用（无 OpenSSL）；idna 禁用（无 libidn）；termcap 禁用（无 curses/terminfo 库）。

## 验证结果

上游测试（mx-test.sh --check，套件自身计数，同一统计口径）：

```text
607 tests: 602 ok, 5 failure(s).  3 test(s) skipped
TOTAL = PASS + FAIL + SKIP + NOT_RUN = 602 + 5 + 3 + 0 = 607（套件汇总行，test-run4.log）
```

非 PASS 项（全部为 OHOS/HMDFS 文件系统类环境限制，逐项证据见 reports/）：

- netrc 断言 2 项：HMDFS 不保留属主独占权限位（chmod 0600 实落盘 0660），
  s-nail 拒绝加载非 owner-only 的 .netrc（`Not a regular file, or accessible by non-user`）。
  属上游安全设计，不应改弱检查。
- pipe_handlers 断言 3 项：测试用 `ln -f` 建硬链接并断言 `file-stat` 的 st_nlink；
  HMDFS 不支持硬链接（link() 恒失败），链接计数恒为 1。

跳过 3 项均为可选特性缺库跳过：`[!SMIME]`（无 OpenSSL）、`[!IDNA]`（无 libidn）、
`attachments#10`（无外部 iconv(1) 工具的指定转换）。

包验证（test_package，4 项断言全部通过）：版本横幅 / 批处理命令解释器 /
addrcodec 地址编码 / POSIX `-e` 空邮箱退出语义。

二进制加固（llvm-readelf）：Type=DYN(PIE)、GNU_STACK RW(NX)、GNU_RELRO、BIND_NOW。
---

**编译结束**: 2026-09-22 03:41
**最终状态**: built
