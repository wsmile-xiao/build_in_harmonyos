# memtester 4.7.1 适配笔记

## 编译环境
- 构建系统: makefile（djbdns 风格，无 configure 脚本）
- 编译日期: 2026-06-03
- 平台: HarmonyOS (HongMeng Kernel 1.12.0) aarch64
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 状态: published

## 编译步骤

1. `source .build-context-memtester-4.7.1`
2. `cd $BUILD_SRC_DIR`
3. 编辑 `conf-cc`：`cc → clang -fPIC`（添加 -fPIC 用于 ELF 签名兼容）
4. 编辑 `conf-ld`：`cc -s → clang`（移除 -s strip 标志，由 package 9 步管线负责 strip）
5. 编辑 `Makefile`：添加 `PREFIX ?=` / `DESTDIR ?=` / `INSTALLPATH = $(DESTDIR)$(PREFIX)` 支持（R20 DESTDIR 模式合规）
6. `make -j1` — 编译成功，1 个已知 warning（-Wparentheses）
7. `make install DESTDIR=$TEST_PREFIX PREFIX=$DEFAULT_PREFIX` — staging 安装 ✅
8. 安全弹窗验证（R7）：`$DEFAULT_PREFIX/bin/memtester` → 显示 `memtester version 4.7.1 (64-bit)` ✅
9. memtester 无上游测试套件，跳过 `make check`
10. 真实执行测试：`memtester 1M 1` → 全部 18 项内存测试通过 ✅
11. `ohc-run.py verify-build` — G1-G4 PASS
12. `ohc-run.py package` — 打包完成，产出 92KB 预编译包
13. `make install PREFIX=$DEFAULT_PREFIX` — 本地安装验证 ✅
14. `ohc-run.py finish memtester 4.7.1 published` — 收尾完成

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 源码包 SSL 下载失败 | Python urllib SSL 证书验证失败（CERTIFICATE_VERIFY_FAILED） | 使用 `curl -fsSL` 手动下载 tarball 到 `~/tmp/builds/`，init-build 检测已存在文件跳过下载 |
| 2 | Makefile 不支持 DESTDIR/PREFIX | 原始 Makefile 硬编码 `INSTALLPATH=/usr/local`，无 PREFIX/DESTDIR 变量 | 添加 `PREFIX ?= /usr/local`、`DESTDIR ?=`、`INSTALLPATH = $(DESTDIR)$(PREFIX)`，实现 R20 DESTDIR 模式合规 |
| 3 | conf-cc 使用 cc 而非 clang | djbdns 风格构建系统默认用 `cc` 编译 | 改为 `clang -fPIC -O2 -DPOSIX -D_POSIX_C_SOURCE=200809L -D_FILE_OFFSET_BITS=64 -DTEST_NARROW_WRITES -c`，添加 -fPIC 确保 ELF 签名兼容 |
| 4 | conf-ld 使用 cc -s | 链接时 strip（-s）会影响调试符号包 | 改为 `clang`，移除 -s 标志，由 ohc-run.py package 9 步管线负责 strip 和调试符号分离 |
| 5 | G0 clean-verify 失败（exit 127） | memtester 是 makefile 项目，无 configure 脚本；G0 尝试运行 `./configure` 导致 `No such file or directory` | 已知脚本限制，clean-verify 仅支持 autotools/cmake 项目。手动验证 3 个补丁自包含性通过 |
| 6 | G4 manifest 缺少 build_system 顶层字段 | verify-build 检查顶层 `build_system:` 字段，但 init 生成的 manifest 使用嵌套 `build.system:` | 添加顶层 `build_system: makefile` 字段 |
| 7 | G4 补丁数不一致（manifest=0 vs disk=3） | init 生成的 manifest `patches_applied: []` 为空 | 更新 `patches_applied` 为实际 3 个补丁列表 |

## 源码修改

3 个补丁（per-file-difflib 生成）：

- `0001-Makefile.patch`：添加 PREFIX/DESTDIR 支持（R20 DESTDIR 模式合规）
  - 原：`INSTALLPATH = /usr/local`
  - 改：`PREFIX ?= /usr/local`、`DESTDIR ?=`、`INSTALLPATH = $(DESTDIR)$(PREFIX)`
- `0002-conf-cc.patch`：编译器适配（cc → clang -fPIC）
  - 原：`cc -O2 -DPOSIX -D_POSIX_C_SOURCE=200809L -D_FILE_OFFSET_BITS=64 -DTEST_NARROW_WRITES -c`
  - 改：`clang -fPIC -O2 -DPOSIX -D_POSIX_C_SOURCE=200809L -D_FILE_OFFSET_BITS=64 -DTEST_NARROW_WRITES -c`
- `0003-conf-ld.patch`：链接器适配（cc -s → clang）
  - 原：`cc -s`
  - 改：`clang`

## 依赖版本

- 无外部依赖（纯 C 程序，仅依赖 libc 和 POSIX 接口）
- 编译器: clang 15.0.4

## 验证结果

### 版本验证

```bash
$ ~/usr/local/bin/memtester
memtester version 4.7.1 (64-bit)
need memory argument, in MB

Usage: ~/usr/local/bin/memtester [-p physaddrbase [-d device] [-u]] <mem>[B|K|M|G] [loops]
Copyright (C) 2001-2024 Charles Cazabon.
pagesize is 4096
```

### 真实执行测试（1MB × 1 循环）

```bash
$ ~/usr/local/bin/memtester 1M 1
memtester version 4.7.1 (64-bit)
...
want 1MB (1048576 bytes)
got  1MB (1048576 bytes), trying mlock ...locked.
Loop 1/1:
  Stuck Address       : ok
  Random Value        : ok
  Compare XOR         : ok
  Compare SUB         : ok
  Compare MUL         : ok
  Compare DIV         : ok
  Compare OR          : ok
  Compare AND         : ok
  Sequential Increment: ok
  Solid Bits          : ok
  Block Sequential    : ok
  Checkerboard        : ok
  Bit Spread          : ok
  Bit Flip            : ok
  Walking Ones        : ok
  Walking Zeroes      : ok
  8-bit Writes        : ok
  16-bit Writes       : ok
Done.
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| `memtester-4.7.1-ohos-aarch64.tar.gz` | 92KB | 预编译包（含 bin/memtester + man/man8/memtester.8.gz） |
| `memtester-4.7.1-ohos-aarch64-debug.tar.gz` | 31KB | 调试符号包（含 memtester.debug） |

## 质量门禁结果

| 门禁 | 结果 | 详情 |
|------|------|------|
| G1 二进制完整性 | ✅ PASS | ✅1 ⚠️0 ❌0 |
| G2 功能可用性 | ✅ PASS | ✅0 ⚠️1 ❌0（memtester 无 --version 选项） |
| G3 可移植性 | ✅ PASS | ✅0 ⚠️2 ❌0（无 RPATH，无共享库依赖） |
| G4 档案完整性 | ✅ PASS | ✅0 ⚠️0 ❌0 |
| G0 干净构建 | ❌ FAIL | 脚本限制：无 configure 脚本 |

## 注意事项

- memtester 没有 `--version` 选项，在错误调用时（无参数）会显示版本号
- memtester 没有 configure 脚本，G0 clean-verify 会被脚本限制阻塞
- memtester 没有上游测试套件，无法运行 `make check`
- djbdns 风格构建系统：通过 `conf-cc` 和 `conf-ld` 文件配置编译器和链接器，而非传统 Makefile 变量
- `find-systype.sh` 在 HarmonyOS 上会落入 `*)` 兜底分支，但不影响编译

## 知识沉淀

- L2 模式经验：djbdns 风格构建系统（conf-cc/conf-ld）在鸿蒙平台的适配方法：修改 conf-cc 添加 clang + -fPIC，修改 conf-ld 移除 -s
- L2 模式经验：makefile 类型项目无 configure 脚本，需要手动添加 DESTDIR/PREFIX 支持
- L1 平台真理：G0 clean-verify 对 makefile 类型项目无效（脚本假设所有项目都有 configure）

---

**编译结束**: 2026-06-03 00:22
**最终状态**: published