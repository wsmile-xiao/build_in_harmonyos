# klibc-kinit 2.0.14 - 测试报告

> **测试日期**: 2026-09-22
> **测试环境**: HarmonyOS PC，HongMeng Kernel 1.12.0 aarch64（真机，非模拟器）
> **CONAN_HOME**: `~/work/psj/ch-klibc-kinit`（本会话独立缓存，profile 从 `~/.conan2/profiles/ohos-aarch64` 复制）
> **测试类型**: 上游官方自测实跑 + 消费者静态校验 + 破坏性反向验证

## 命令与总结果

```bash
conan create archives/k/klibc-kinit/2.0.14 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
```

| 项 | 结果 |
|---|---|
| `conan create` 退出码 | **0** |
| 构建窗口 | 2026-09-22 03:31:03 → 03:34:23（CST，3 min 20 s） |
| 完整包引用 | `klibc-kinit/2.0.14:6b129b068851896169fae42d399fa922d239ce8a`（二进制包 ID 由 settings/options 决定） |
| 上游自测断言 | **17 / 17 通过**（2 个自测程序，0 失败 0 跳过） |
| 消费者断言（鸿蒙特有测试） | **18 / 18 通过**（`HMBS_TEST_PACKAGE_RESULT: PASS`） |
| L1e/R34 破坏性反向 | `POS_EXIT:0` → 隐藏 `p/bin` → `NEG_EXIT:1`（test_package `build()` 即报 bindir 缺失）→ 还原 → `POS2_EXIT:0` |

包内产物：`bin/kinit`（63144 B）、`licenses/LICENSE`、`res/README`、`res/upstream-tests-summary.txt`。

## 上游构建

顶层 `make`（patch 0004 把 all 目标收敛为 scripts/basic + usr/klibc + usr/kinit）成功产出：

| 产物 | 大小 |
|---|---|
| `usr/kinit/static/kinit`（本包交付物） | 63144 B |
| `usr/kinit/shared/kinit` | 47600 B（PT_INTERP → `/lib/klibc-<hash>.so`，不随本包发布） |
| `usr/klibc/libc.a` | 1747928 B |
| `usr/klibc/libc.so` | 595264 B |

## 上游官方测试（`usr/kinit` 组件自带的 standalone 自测）

klibc 顶层 `make test` 只构建 `usr/klibc/tests`（39 个程序，属 libc 本体，已由 PR #11156
以 `klibc/2.0.14` 声明），不覆盖 `usr/kinit`。kinit 组件的测试是两段编译期宏包起来的
standalone main，配方用刚建好的 libc.a + crt0.o 静态编译并**实跑**：

- `usr/kinit/devname.c` `#ifdef TEST_DEVNAME` → `bdevname()` 的 dev_t → (major,minor) 分解
- `usr/kinit/name_to_dev.c` `#ifdef TEST_NAMETODEV`（按上游设计带 `-DDEBUG`，否则 `dprintf` 是空宏）
  → `name_to_dev_t()` 的内核命令行 `root=` 8 类变体解析

期望值取自 klibc 自身定义（`usr/include/sys/sysmacros.h` 的编码 + `usr/kinit/do_mounts.h`
的 `Root_RAM0/NFS/MTD/MULTI`），断言只比对行尾 `(major,minor)`，与宿主 `/sys/block`
是否可读无关。

| # | 命令 | 实际输出 | 结果 |
|---|------|----------|------|
| 1 | `test_devname 0x00000000` | `0x00000000 = dev(0,0)` | ✅ PASS |
| 2 | `test_devname 0x000000fd` | `0x000000fd = dev(0,253)` (Root_MULTI) | ✅ PASS |
| 3 | `test_devname 0x000000fe` | `0x000000fe = dev(0,254)` (Root_MTD) | ✅ PASS |
| 4 | `test_devname 0x000000ff` | `0x000000ff = dev(0,255)` (Root_NFS) | ✅ PASS |
| 5 | `test_devname 0x00000100` | `0x00000100 = dev(1,0)` (Root_RAM0) | ✅ PASS |
| 6 | `test_devname 0x00000807` | `0x00000807 = dev(8,7)` | ✅ PASS |
| 7 | `test_devname 0x000fffff` | `0x000fffff = dev(4095,255)`（major/minor 字段上限） | ✅ PASS |
| 8 | `test_name_to_dev 0x000000fe` | `kinit: name_to_dev_t(0x000000fe) = dev(0,254)` | ✅ PASS |
| 9 | `test_name_to_dev 0x000000ff` | `kinit: name_to_dev_t(0x000000ff) = dev(0,255)` | ✅ PASS |
| 10 | `test_name_to_dev 0x00000100` | `kinit: name_to_dev_t(0x00000100) = dev(1,0)` | ✅ PASS |
| 11 | `test_name_to_dev 0x00000807` | `kinit: name_to_dev_t(0x00000807) = dev(8,7)` | ✅ PASS |
| 12 | `test_name_to_dev 8:7` | `kinit: name_to_dev_t(8:7) = dev(8,7)`（十进制 major:minor 变体） | ✅ PASS |
| 13 | `test_name_to_dev /dev/nfs` | `kinit: name_to_dev_t(/dev/nfs) = dev(0,255)` | ✅ PASS |
| 14 | `test_name_to_dev /dev/ram` | `kinit: name_to_dev_t(/dev/ram) = dev(1,0)` | ✅ PASS |
| 15 | `test_name_to_dev /dev/mtd/root` | `kinit: name_to_dev_t(/dev/mtd/root) = dev(0,254)` | ✅ PASS |
| 16 | `test_name_to_dev sda,1` | `kinit: name_to_dev_t(sda,1) = dev(0,253)`（多根逗号形式） | ✅ PASS |
| 17 | `test_name_to_dev nonexistentdisk99` | `kinit: name_to_dev_t(nonexistentdisk99) = dev(0,0)`（未知返回 0） | ✅ PASS |

### 未运行的上游用例

| 用例 | 结果 | 技术原因 |
|------|------|----------|
| `usr/kinit/nfsmount/dummypmap_test.c` | ⚪ 未运行 | 上游 `usr/kinit/nfsmount/Kbuild:6` 原话 `#FIXME - build is broken static-y := dummypmap`，该目标未登记进 `static-y/shared-y`，构建系统从不构建它；且该文件全文只有 `#define TEST` + `#include "dummypmap.c"` 两行，2.0.14 的 `dummypmap.c` 内没有任何 `TEST` 条件块也没有 `main()`（`grep -c 'ifdef TEST' usr/kinit/nfsmount/dummypmap.c` = 0），按上游源码现状无法链接。属上游自身失效，非本环境缺依赖 |

## 消费者测试（鸿蒙特有测试，18 项）

`kinit` 是 initramfs 的 PID 1 程序：`usr/kinit/kinit.c` 的失败路径 `umount2("/proc")` /
`umount2("/sys")`（288–320 行），成功路径经 `usr/kinit/initrd.c:113-154` 与
`usr/kinit/run-init/` 用 `MS_MOVE` 重挂根 + `chroot` 后接管 init。**在在线 HarmonyOS 上
exec 它属破坏性操作**，因此消费者对交付物做装载前静态校验：

| # | 断言 | 结果 |
|---|------|------|
| 1 | bindir 存在（由包 cpp_info 推导） | ✅ PASS |
| 2 | `bin/kinit` 已安装 | ✅ PASS |
| 3 | `bin/kinit` 有可执行位 | ✅ PASS |
| 4 | `bin/kinit` 尺寸非平凡（63144 B） | ✅ PASS |
| 5 | ELF 魔数 `0x7f454c46` | ✅ PASS |
| 6 | `ELFCLASS64` | ✅ PASS |
| 7 | `ELFDATA2LSB`（小端） | ✅ PASS |
| 8 | `e_type = ET_EXEC`（静态可执行，非依赖解释器的 DYN） | ✅ PASS |
| 9 | `e_machine = EM_AARCH64`（0xb7） | ✅ PASS |
| 10 | 不含 `ld-musl` 解释器路径 | ✅ PASS |
| 11 | 不含 `ld-linux` 解释器路径 | ✅ PASS |
| 12 | 不含 `/lib/klibc-` 解释器路径（确为 static/kinit 而非 shared/kinit） | ✅ PASS |
| 13 | `IP-Config` 字面量存在 → ipconfig 目标文件确被链入 kinit | ✅ PASS |
| 14 | `rootfs not a ramfs or tmpfs` 存在 → run-init 目标文件确被链入 | ✅ PASS |
| 15 | `usr/kinit/run-init/runinitlib.c` 路径记录存在 → 确由上游 usr/kinit 源码构建 | ✅ PASS |
| 16 | `kinit_mount=` 存在 → 内核命令行参数解析器已链入 | ✅ PASS |
| 17 | 包内 `res/upstream-tests-summary.txt` 报 `failures=0` | ✅ PASS |
| 18 | `licenses/LICENSE` 随包 | ✅ PASS |

字面量匹配走 `od -An -v -tx1 | tr -d ' \n'` 的十六进制流：toybox 0.8.12 的 `grep -ac`
对二进制不做行匹配（恒 0），`tr -c '[:print:]' '\n'` 又是恒等变换，两者叠加会让断言假通过；
本方法与设备上的 `strings` 逐条交叉验证一致。

## 构建期告警（如实记录，未屏蔽）

- `-Wmacro-redefined`：`__bitwise` 在 `usr/include/klibc/compiler.h:144` 与
  `usr/include/linux/types.h:25` 各定义一次（klibc 头与内核 UAPI 头同域），上游固有。
- `usr/kinit/name_to_dev.c` 内 `dprintf(stderr, ...)` 把 `FILE *` 传给 `printf`：上游
  `partlabel_to_dev_t()` 的既有笔误（`kinit.h` 里 `dprintf` 就是 `printf`），仅在该分支
  被走到时有意义，本次 17 项断言未触及；未修改上游逻辑。
- `clang-15: warning: argument unused during compilation: '-no-pie'`：链接期由驱动忽略，无害。
