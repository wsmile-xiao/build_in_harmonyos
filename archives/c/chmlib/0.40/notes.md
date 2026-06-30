# chmlib 0.40 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-03
- 编译器: clang 15.0.4 (OHOS SDK 26.0.0.18)，通过 cc-sign-wrapper 调用
- 链接器: GNU ld 2.45（通过 -B 标志替代 ld.lld）
- 状态: published
- 平台: aarch64-unknown-linux-ohos (HarmonyOS Kernel 1.12.0)

## 源码获取

原始下载 URL `https://www.jedrea.com/chmlib/chmlib-0.40.tar.gz` 不可用（503错误），
通过 openEuler 仓库获取源码包：
- `https://gitee.com/src-openeuler/chmlib/repository/archive/master.tar.gz`
- 内含 `chmlib-0.40.tar.bz2`，从中提取并重新打包为 tar.gz

## 编译步骤

1. 修改 config.guess，添加 HarmonyOS 检测分支（`*:HarmonyOS:*:*` case）
   - 使用 `echo ${MACHINE}-unknown-linux-ohos && exit 0` 格式
   - 注意：旧版 config.guess (2008) 使用 echo+exit 格式而非 GUESS= 格式
2. 修改 config.sub，三处添加 linux-ohos 支持
   - maybe_os 行：添加 `linux-ohos*`
   - OS 列表行：添加 `-linux-ohos*`
   - case 分支：添加 `-linux-ohos)` 条目（避免 -linux* 误转为 -linux-gnu）
3. 修改 configure 中 `umask 077` 为 `umask 002`（2处）
   - 解决 HMDFS setgid 目录权限限制问题
4. 修改 src/chm_lib.c，在 `#elif __x86_64__ || __ia64__` 后添加 `#elif __aarch64__` 类型定义块
5. 创建 cc-sign-wrapper：
   - 编译时自动调用 clang -B$HOME/tmp/gnu-ld-bin/ 替代 ld.lld
   - 编译后自动调用 sign-elf 签名 ELF 二进制（解决 OHOS 执行权限限制）
6. 运行 `./configure --prefix=$DEFAULT_PREFIX CC=$HOME/tmp/cc-sign-wrapper/cc`
7. 运行 `make -j1`
8. 运行 `make install DESTDIR=$TEST_PREFIX`（staging）
9. 运行 `make install`（本地安装到 $DEFAULT_PREFIX）
10. 验证安装结果

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 | 铁律符合性 |
|---|------|------|----------|-----------|
| 1 | config.guess 无法识别 HarmonyOS | 缺少 HarmonyOS 检测分支（2008版本太旧） | 添加 `*:HarmonyOS:*:*` case，使用 echo+exit 0 输出 | ✅ R23: 平台检测机制优先 |
| 2 | config.sub 不识别 linux-ohos | 缺少 linux-ohos 模式 | 三处添加 linux-ohos 支持 | ✅ R23 |
| 3 | config.status 无法创建临时目录 | HMDFS setgid + umask 077 导致临时目录权限不足 | 修改 configure/config.status 中 `umask 077` 为 `umask 002` | ⚠️ R6: 改 configure（生成文件），但无 configure.ac |
| 4 | chm_lib.c 编译 #error | 缺少 aarch64 平台类型定义 | 在类型定义块后添加 `#elif __aarch64__` 分支 | ✅ R8: 源码守卫 |
| 5 | ld.lld 无法执行（libxml2.so.16 依赖） | OHOS SDK ld.lld 需要 libxml2.so.16，但动态链接器无法加载 | 使用 -B 标志指向 GNU ld 目录，绕过 ld.lld | ⚠️ 平台限制 |
| 6 | 新编译 ELF 二进制无法执行（Permission denied） | OHOS 要求新编译的 ELF 必须签名后才能执行 | CC wrapper 自动调用 sign-elf 签名 | ⚠️ 平台限制 |

### 铁律偏差说明

- **R1（参数最少化）偏差**: configure_options 不为空，包含 CC wrapper 和 -B 标志。
  原因：ld.lld 平台限制和 ELF 签名要求是环境问题，无法通过源码补丁解决。
  标记为技术债务（build_cleanliness: technical_debt: true）。
- **R6 偏差**: 修改了 configure（生成文件）中的 umask，而非 configure.in（源文件）。
  原因：chmlib-0.40 的 configure.in 中不包含 umask 设置（由 autoconf 自动生成），
  无法通过修改 configure.in 解决。标记在补丁分类中。

## 源码修改清单

| 文件 | 修改内容 | 补丁状态 | 分类 |
|------|----------|----------|------|
| config.guess | 添加 HarmonyOS 检测 case，echo+exit 0 格式 | ✅ 0001-config.guess.patch | platform |
| config.sub | 三处添加 linux-ohos 支持 | ✅ 0002-config.sub.patch | platform |
| configure | umask 077 → umask 002（2处） | ✅ 0003-configure.patch | platform (⚠️ 生成文件) |
| src/chm_lib.c | 添加 __aarch64__ 类型定义块 | ✅ 0004-src-chm_lib.c.patch | platform |

## 依赖版本

- clang 15.0.4 (OHOS SDK 26.0.0.18)
- GNU Make 4.4.1
- GNU ld 2.45（通过 -B 标志替代 ld.lld）
- sign-elf 工具（$SKILL_ROOT/scripts/ohc-run.py sign-elf）

## 验证结果

### 头文件验证
```bash
$ ls /storage/Users/currentUser/usr/local/include/chm_lib.h  # ✅ 5906 bytes
$ ls /storage/Users/currentUser/usr/local/include/lzx.h       # ✅ 2527 bytes
```

### 库文件验证
```bash
$ ls /storage/Users/currentUser/usr/local/lib/libchm.a        # ✅ 38720 bytes
$ ls /storage/Users/currentUser/usr/local/lib/libchm.la       # ✅ 959 bytes
```

### 预编译包验证
```bash
$ ls archives/c/chmlib/0.40/packaging/chmlib-0.40-ohos-aarch64.tar.gz  # ✅ 53,788 bytes
```

## make check 结果

chmlib 没有自动化测试套件（`make check` 无目标）。源码中的 test_chmLib.c 是示例驱动程序，
需传入 .chm 文件路径才能运行，非自动化测试框架。

```bash
$ make check
make: *** No rule to make target 'check'.  Stop.
```

**跳过原因**: 软件本身不提供测试套件，这是软件限制而非平台问题。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| chmlib-0.40-ohos-aarch64.tar.gz | 53KB | 预编译包（头文件+静态库） |
| libchm.a | 38720 bytes | CHM 解析静态库 |
| chm_lib.h | 5906 bytes | CHM API 头文件 |
| lzx.h | 2527 bytes | LZX 解压缩头文件 |
| 0001-config.guess.patch | 1287 bytes | 平台检测补丁 |
| 0002-config.sub.patch | 2902 bytes | OS 识别补丁 |
| 0003-configure.patch | 883 bytes | umask 修复补丁 |
| 0004-src-chm_lib.c.patch | 1097 bytes | aarch64 类型定义补丁 |

## 注意事项

- chmlib 仅生成静态库（libchm.a），不支持共享库构建
- HMDFS 文件系统限制：`umask 077` 创建的临时目录权限不足，必须改为 `umask 002`
- chm_lib.c 中 `_XOPEN_SOURCE 500` 与 OHOS SDK `_XOPEN_SOURCE 700` 冲突（编译警告，不影响功能）
- OHOS SDK ld.lld 存在 libxml2.so.16 依赖问题，需通过 -B 标志使用 GNU ld
- 新编译的 ELF 二进制需要签名才能在 OHOS 上执行

---
**编译结束**: 2026-06-03 17:06
**最终状态**: published