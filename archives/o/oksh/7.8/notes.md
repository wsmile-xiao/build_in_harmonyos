# oksh 7.8 适配笔记

## 编译环境

- 构建系统: autotools（自定义 configure 脚本，非标准 autoconf 生成）
- 编译日期: 2026-06-16
- 编译器: clang 15.0.4 / clang++
- 状态: published
- 平台: HarmonyOS aarch64

## 编译步骤

1. `ohc-run.py init-build oksh 7.8 --url=https://github.com/ibara/oksh/releases/download/oksh-7.8/oksh-7.8.tar.gz`
   - 下载源码并解压到 ~/tmp/builds/oksh-7.8.work
   - 创建归档骨架 archives/o/oksh/7.8/
   - 依赖检查: 所有依赖已就绪（无外部依赖）
   - 环境检查: TMPDIR/CC/CXX/CFLAGS 均正确设置

2. `./configure --prefix=/storage/Users/currentUser/usr/local`
   - configure 自动检测 OS 为 HarmonyOS ✅
   - 检测 curses 库: not found → 编译为无屏幕清除支持模式（不影响核心功能）
   - 检测 __dead/__dead2: no → 使用 __attribute__((__noreturn__)) 替代 ✅
   - 检测 asprintf/confstr/issetugid/setresgid/setresuid 等: 均为 yes ✅
   - 检测 reallocarray/strtonum/pledge: no → oksh 内置替代实现 ✅
   - 生成 Makefile 成功

3. `make -j2`
   - 全部 39 个 .o 文件编译成功，无警告（-w 标志抑制）
   - 链接 oksh 二进制成功
   - 链接库: 仅 musl libc（-L/storage/Users/currentUser/usr/local/lib）

4. `make install DESTDIR=/storage/Users/currentUser/tmp/test-install-oksh-7.8`
   - 安装产物: bin/oksh (251,808 字节) + share/man/man1/oksh.1 (135,857 字节)
   - install -c -s: strip 符号表后安装

5. Staging 验证
   - 未签名二进制执行报 "Operation not permitted" → 需 ELF 签名
   - `ohc-run.py sign-elf` 签名后: oksh 可正常执行 ✅
   - `oksh -c 'echo $KSH_VERSION'` → `@(#)PD KSH v5.2.14 99/07/13.2` ✅

6. `ohc-run.py verify-build oksh 7.8`
   - G1 二进制完整性: PASS ✅
   - G2 功能可用性: PASS ✅
   - G3 可移植性: PASS ✅
   - G4 档案完整性: PASS ✅（修正 build_system 字段后）

7. `ohc-run.py package oksh 7.8`
   - 预编译包制作成功
   - oksh-7.8-ohos-aarch64.tar.gz: 408KB (417,875 字节)
   - oksh-7.8-ohos-aarch64-debug.tar.gz: 25KB (25,623 字节)
   - ELF 签名 + Strip + RPATH 设置均自动完成

8. `make install`（不带 DESTDIR，安装到 ~/usr/local）
   - 本地安装验证: oksh -c 'echo Hello from oksh' → Hello from oksh ✅

9. `ohc-run.py finish oksh 7.8 built`
   - 补丁生成: 无变更（无需补丁）
   - G0 干净构建验证: 通过（configure + make + make install 全部无人工介入）
   - G1-G4 质量门禁: PASS
   - 归档关闭: built → published
   - SUMMARY.md 更新完成

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 二进制首次执行报 Operation not permitted | HarmonyOS 安全机制，ELF 需签名 | `ohc-run.py sign-elf` 签名后可正常执行 |
| 2 | verify-build G4 报 manifest 缺少 build_system | verify 脚本检查扁平字段，而非嵌套 build.system | 在 manifest.yaml 顶层添加 build_system: autotools 字段 |

## 源码修改

无需源码修改。oksh configure 自动检测 HarmonyOS 平台，所有平台差异通过 configure 内置检测机制处理：
- __dead → __attribute__((__noreturn__))
- reallocarray/strtonum/pledge → oksh 内置替代实现（reallocarray.c, strtonum.c 等）
- sys_siglist/sys_signame → siglist.c/signame.c 内置替代

## 依赖版本

- ncurses: 未检测到（可选），oksh 编译为无屏幕清除支持模式（不影响核心 shell 功能）
- 无其他外部依赖
- 仅动态链接 musl libc (ld-musl-aarch64.so.1)

## 手动功能测试（37项）

详细测试报告见 reports/test-report.md。测试概要：
- 基础功能 10/10 通过（版本、echo、变量、算术、if/for/while、字符串、函数、命令替换）
- 中级功能 10/10 通过（管道、重定向、case、位置参数、pwd/type、trap、子shell、文件测试、here文档）
- 高级功能 7/7 通过（export、read、unset、特殊变量、逻辑运算、通配符、后台进程）
- ksh特有命令 5/5 通过（字符串截取#/%、whence、eval、print、return）
- 边界与异常 5/5 通过（空命令、大量参数、三级管道、文件读写、错误退出码）

已知限制（预期行为，非缺陷）：
- bash `${var/pattern/replacement}` 模式替换不可用 → ksh 规范行为
- 管道中 read 变量不传回主shell → ksh 规范行为
- 无屏幕清除功能 → 可选依赖未安装

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| oksh-7.8-ohos-aarch64.tar.gz | 408KB (417,875字节) | 预编译包（含 ELF 签名） |
| oksh-7.8-ohos-aarch64-debug.tar.gz | 25KB (25,623字节) | 调试符号包 |

打包产物内容：
- bin/oksh (276,224字节，含 ELF 签名后大小)
- share/man/man1/oksh.1 (135,857字节)

## 注意事项

- oksh 无 make check 测试套件（Makefile test 目标仅输出 "No tests"），通过 37 项手动功能测试确认可用
- oksh 因未检测到 curses 库，缺少屏幕清除功能，不影响核心 shell 功能
- 二进制首次执行需 ELF 签名（HarmonyOS 安全机制）
- oksh 不支持 bash 特有的 `${var/pattern/replacement}` 模式替换语法，应使用 ksh 的 `${var#pattern}` 和 `${var%pattern}` 字符串截取

---
**编译结束**: 2026-07-21
**最终状态**: published
