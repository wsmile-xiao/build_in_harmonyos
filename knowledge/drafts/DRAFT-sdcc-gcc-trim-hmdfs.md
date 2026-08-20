# DRAFT-sdcc-gcc-trim-hmdfs: gcc 风格嵌套构建树在 OHOS HMDFS 上的 getcwd/权限/裁剪版连环坑

> **Contributor**: AtomCode | **Status**: Draft | **Updated**: 2026-08-20
> **Severity**: 3 | **Category**: compiler / gcc / autotools / hmdfs / libtool / cross-build

## 错误特征

```text
make[2]: Entering directory '.../support/cpp'
Configuring in ./gcc
getcwd: cannot access parent directories: Not supported   ← HMDFS
./gcc/configure: No such file or directory

config.status: creating config.h
./conf12345/subs1.awk: Permission denied                 ← E011（umask 077）

libtool: link: cannot find the library `//lib/libgmp.la'   ← .la libdir 异常

checking readline/readline.h... no                        ← 递归 configure 丢 CPPFLAGS
configure: error: readline development packages are probably missing

sdcc: fatal error: cannot execute 'cc1': posix_spawnp: No such file or directory
```

## 触发条件

- 软件: sdcc 4.6.0（SDCC sdist 内嵌 gcc 12.1.0 裁剪版 = sdcpp/support/cpp）
- 构建: autotools 顶层 + `$(MAKE) -C X` 递归子项目 + gcc 风格嵌套构建树
- 平台: OpenHarmony PC（arm64），/storage 挂载 HMDFS（剥离目录权限）、
  /data 非 HMDFS（chmod 生效、getcwd 正常）

## 根因分析

### ① HMDFS getcwd（make 递归子项目）

顶层 Makefile 用 `$(MAKE) -C X` 递归——**make 的 chdir 不更新 PWD 环境变量**，
子 shell 的 `pwd`/`getcwd` 需 stat 父目录链，而 HMDFS 剥离目录读权限 →
`getcwd: cannot access parent directories`。

**修复**：顶层 Makefile 全部 `$(MAKE) -C X` → `(cd X && $(MAKE))`
（bash cd 更新 PWD），且整个构建迁移到非 HMDFS 分区（/data）。

### ② E011（config.status 临时目录）

autotools configure 的 `(umask 077 && mktemp -d ...)` 生成 0700 目录，
HMDFS 上 other 用户不可读/写（见 E011 全文）。

**修复（三层）**：TMPDIR 指向非 hmdfs 可写目录（/data 候选链）+
patch configure `mktemp -d "$TMPDIR/confXXXXXX"` + umask 077→022。

### ③ gcc 裁剪版不完整（sdist 自身缺陷）

SDCC sdist 内嵌 gcc 12.1.0 裁剪版，每层构建缺文件/缺生成目标：

| 缺失项 | 表现 | 补丁 |
|---|---|---|
| `config/aarch64/` 目录（只有 dummy/i386/riscv） | cc1 引用 `config/aarch64/*.def` No such file | 空 .def 桩 |
| `support/cpp/libiberty/` | LIBIBERTY 指向不存在目录 | 改指 `../../sdbinutils/libiberty/libiberty.a` |
| `bversion.h` 模板（configure 不生成） | `#if (GCC_VERSION >= 3000)` not found | 手动写 `#define GCC_VERSION 120100` |
| `all-tree.def` 生成目标 | gcc.o 编译 not found | 手动 `make all-tree.def` |
| install 默认 strip | OHOS 上 stripped ELF 执行 `Operation not permitted` | `make install STRIP=/bin/true` |
| cc1 安装路径 vs `STANDARD_LIBEXEC_PREFIX` 编译宏 | test 报 `cannot execute 'cc1'` | test 复制 cc1 到 bin/（PATH 可达） |

### ④ libtool .la libdir 异常（DESTDIR 安装 bug）

依赖包 .la 文件 `libdir='//lib'`（DESTDIR 安装时 prefix 拼接错误）→ libtool
读 dependency_libs 引用 `//lib/libgmp.la` 找不到。

**修复**：消费者配方 build() 预处理依赖 .la（libdir → 真实包路径），
不修改已合入的依赖配方。

### ⑤ 递归 configure 丢 CPPFLAGS

make 阶段触发的递归 configure-gdb 不继承主 configure 的 CPPFLAGS →
依赖头找不到（readline/readline.h no）。

**修复**：`make all-gdb CPPFLAGS='...' LDFLAGS='...'` 显式传 make 变量。

## 解决方案（配方层清单）

1. 构建整体迁移非 HMDFS 分区（/data，chmod 生效、getcwd 正常）
2. 顶层 Makefile `$(MAKE) -C X` → `(cd X && $(MAKE))`
3. TMPDIR 候选链（/data 优先）+ configure 递归 patch（mktemp $TMPDIR + umask 022）
4. gcc 裁剪版补丁（.def 桩 / LIBIBERTY / bversion.h / all-tree.def / STRIP=/bin/true）
5. 依赖 .la 预处理（libdir 修正）
6. make 显式传 CPPFLAGS/LDFLAGS
7. test 复制包到非 HMDFS + cc1 复制到 bin/ + PATH/cwd 注入 + 真实试载探测

## 验证

- 本地 conan create 全流程通过：`Package created` + `OK: sdcc 4.6.0 real API
  ok (8051 compile -> .ihx)`，75 个 device lib 全架构编译
- CI（conan-build-test）通过

## 相关

- E011（HMDFS umask 077）、E007（config.guess）
- DRAFT-swftools-autotools-hmdfs-2168（TMPDIR + umask + sh configure）
- DRAFT-hmdfs-script-exec-interpreter（脚本/子进程执行沙盒限制）
- DRAFT-patchelf-breaks-ohos-signing（签名二进制不可修改 → 禁用 strip 同根）
