# dwarves 1.30 - HarmonyOS 编译记录

## 概述

dwarves（pahole 工具集）是 DWARF/CTF/BTF 调试信息分析库与命令行工具，
提供 pahole/codiff/pfunct/pdwtags 等 13 个 CLI，广泛用于内核 BTF
生成与调试信息分析。

**编译状态**: ✅ 构建与测试通过（built）

## 编译环境

| 项目 | 值 |
|------|-----|
| 系统 | HarmonyOS PC (aarch64) |
| 编译器 | clang 15.0.4 |
| C 库 | musl libc |
| 三元组 | aarch64-linux-ohos |
| 构建系统 | CMake + Conan 2.29.1 |

## 编译步骤

```bash
# 配方目录
conan create archives/d/dwarves/1.30 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable
```

## 产物

- `libdwarves.so.1` / `libdwarves_emit.so.1` / `libdwarves_reorganize.so.1`（带 DT_SONAME）
- 13 个 CLI：pahole codiff ctracer dtagnames pdwtags pfunct pglobal prefcnt scncopy syscse btfdiff fullcircle ostra-cg
- 公开头：`include/dwarves/*.h`（dwarves.h 等）

## 关键适配点

1. GitHub release tarball 不含 `lib/bpf` 子模块：source() 按 v1.30 锁定 commit 单独拉取 libbpf @42a6ef6
2. E091：OHOS linux/socket.h 与 musl sys/socket.h 冲突，libbpf netlink.c/nlattr.c 加 define-guard
3. musl 垫片：requires argp-standalone + musl-obstack，Findargp/Findobstack 经 CMAKE_LIBRARY_PATH 注入
4. 公开头 dwarves.h include obstack.h/argp.h/dwarf.h：消费者需显式链接垫片与 elfutils target
5. OHOS 无 CMake 平台模块：SONAME flag 需显式补 `-Wl,-soname,`

## 测试

上游 6 项测试全量枚举（default_vmlinux_btf 通过、4 项因缺 vmlinux/perf 按 upstream 设计 skip、
1 项因 /tmp erofs 只读平台阻塞），外加鸿蒙专项 BTF 解析测试与消费者用例（均通过）。
详见 `archives/d/dwarves/1.30/test-ledger.md`。

## 仓库

https://github.com/acmel/dwarves