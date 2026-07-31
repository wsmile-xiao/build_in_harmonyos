# crafty 23.4 适配笔记

## 编译环境
- 构建系统: makefile (纯 Makefile，无 configure)
- 编译日期: 2026-07-29
- 编译器: clang/clang++
- 状态: built

## 编译步骤

Crafty 是纯 Makefile 项目（无 configure），上游 `make linux-64` 默认用 Intel icc 编译器并带 x86 assembly spinlock。鸿蒙 aarch64 无 icc、无 x86 asm 约束（`=&q`），改为：

```bash
make target=LINUX CC=clang CXX=clang++ \
  CFLAGS='-Wall -pipe -O2' CXFLAGS='-Wall -pipe -O2' \
  LDFLAGS='' LIBS='-lpthread -lstdc++' \
  opt='-DCPUS=2 -DNOEGTB' crafty-make
```

- `target=LINUX`：走 Linux 路径（鸿蒙 PC 兼容）
- `__aarch64__`：编译器预定义宏，触发 lock.h 的 aarch64 分支（用 `__sync` 内建替代 x86 asm）
- `-DCPUS=2`：启用 SMP lock 代码（验证多线程守卫）
- `-DNOEGTB`：禁用 egtb.cpp 的 endgame-tablebase 大文件机制（上游 FTP 已失效，且 egtb.cpp 有 C++11 字面后缀语法问题）
- 禁 `INLINE64`/`POPCNT`：x86/Intel 专用 assembly，aarch64 不适用

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `lock.h: '=&q' invalid output constraint` | 上游在非-POWERPC 的 unix 路径硬编码 x86 asm spinlock（`xchgl` + `pause`），aarch64 无此约束 | 加 `__aarch64__` 守卫分支，用 GCC/clang `__sync_lock_test_and_set` + `__sync_lock_release` 内建实现等价原子 spinlock（见 patches/0002） |
| 2 | `egtb.cpp: invalid suffix on literal; C++11 requires a space` | `DEC_INDEX_FORMAT" "DEC_INDEX_FORMAT" "DEC_INDEX_FORMAT"\n"` 字面后缀紧贴标识符，C++11 不允许 | 字面与标识符间加空格（见 patches/0001） |

## 源码修改

| 文件 | 补丁 | 内容 |
|------|------|------|
| lock.h | patches/0002-lock.h.patch | 新增 `__aarch64__` 分支，用 `__sync` 内建替代 x86 asm spinlock（LockAtomic/UnlockAtomic），保留 x86 路径不动 |
| egtb.cpp | patches/0001-egtb.cpp-cpp11-literal-suffix.patch | `DEC_INDEX_FORMAT" "` → `DEC_INDEX_FORMAT " "`（字面与宏间加空格，C++11 合规） |

## 依赖版本

- 无外部库依赖（Debian control: `debhelper-compat (=13), libnuma-dev [amd64]`，libnuma 仅 amd64 可选，aarch64 不适用）
- 编译器: clang 15.0.4（OHOS SDK）
- make 4.4.1

## 验证结果

```bash
# 编译成功 → AArch64 ELF64
$ readelf -h crafty | grep -E 'Machine|Class|ELF'
Class: ELF64
Machine: AArch64

# 版本输出
$ printf 'quit\n' | ./crafty
Crafty v23.4 (1 cpus)

# 上游测试命令 (test.c → Test() 函数，实质调用搜索 Iterate())
$ printf 'test /storage/Users/currentUser/crafty-test.stdin\nquit\n' | ./crafty
solution 1. e4
              18     5.40   0.13   1. Nc3 Nc6 2. Nf3 Nf6 3. e4 e5 ...
test results summary:
total positions searched.......... 1
number right...................... 1
percentage right.................. 100
```

## 注意事项

- crafty 是**命令行工具**（application），非库 —— `package_type="application"`，`cpp_info.bindirs=["bin"]`，需 commands.json (R38)
- 上游 FTP (ftp.cis.uab.edu) 已失效（Debian uscan 报 500），源码用 Debian pool 官方镜像 `deb.debian.org`（R39 权威镜像源）
- crafty 启动会找 `./book.bin`/`./books.bin`（不存在则 disable book，非致命，测试可忽略）
- license 是 Robert Hyatt 个人非自由许可（Debian non-free），`license="non-free"`
---

**编译结束**: 2026-07-29 14:17
**最终状态**: built
