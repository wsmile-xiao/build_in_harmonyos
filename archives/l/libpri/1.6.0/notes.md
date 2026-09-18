# libpri 1.6.0 适配笔记

## 编译环境
- 构建系统: makefile（上游根 Makefile，无 configure / 无 autotools）
- 编译日期: 2026-09-16
- 编译器: clang 15.0.4（OHOS aarch64，profile `ci/conan/profiles/ohos-aarch64`）
- 归档器: llvm-ar / llvm-ranlib（从 Conan conf 注入）
- 状态: built

## 编译步骤

```bash
# 配方自包含构建：conan create 内部执行 source() 下载解压 → build() → package()
conan create archives/l/libpri/1.6.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable
```

`build()` 里实际驱动的命令（CC/AR/RANLIB 全部来自 Conan conf，R33）：

```bash
make -j1 CC=<conf c> AR=<conf ar|llvm-ar> RANLIB=<conf ranlib|llvm-ranlib> \
     LDCONFIG=true UTILITIES="rosetest testprilib"
./rosetest    # 上游 ROSE 编解码用例
./testprilib  # 上游 BRI 环回冒烟测试
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `make all` 在 OHOS 直接失败 | 上游 `UTILITIES= pridump pritest rosetest testprilib`，其中 `pritest.c`、`pridump.c` 都 `#include <dahdi/user.h>`，而 DAHDI 是 Linux 内核驱动，OHOS 没有、发行 tarball 里也不含该头 | 命令行 `UTILITIES="rosetest testprilib"` 只构建两个可移植程序，不改上游 Makefile；`pritest` 在测试统计里按 NOT_RUN 单列并写明原因 |
| 2 | `testprilib.o` 编译报 `error: redirecting incorrect #include <sys/signal.h> to <signal.h> [-Werror,-W#warnings]` | OHOS sysroot 对 `<sys/signal.h>` 只发 `#warning`，上游 Makefile 带 `-Werror`，警告被升级为错误 | 补丁 0002 把该 include 改成 POSIX 的 `<signal.h>`（比关掉 `-Werror` 更小的改动） |
| 3 | 链接共享库步骤调用 `/sbin/ldconfig`，OHOS 无此程序 | 上游假设 Linux 发行版布局 | `make LDCONFIG=true`（命令行变量覆盖 Makefile 赋值） |
| 4 | 归档器用的是字面 `ar rcs` / `ranlib`，交叉编译时用的是 PATH 上碰巧存在的宿主 binutils | Makefile 未参数化归档器 | 补丁 0001 参数化为 `$(AR)`/`$(RANLIB)`，配方从 `tools.build:compiler_executables` 注入 `llvm-ar`/`llvm-ranlib`（实测日志里已是 `/data/service/hnp/bin/llvm-ar`） |
| 5 | `rosetest` 无论成功失败都 `exit 0`（`main()` 末尾无条件 `return 0`，失败只经 `pri_error()` 打印） | 上游测试程序没有失败返回值 | 判据改为读输出：用例计数（267 条 `encoded length is`）+ 精确失败标记正则（`Error: Message:<n> ` / `test: Message failed to decode` / `did not match`）；计数不符或出现失败标记即让 `conan create` 失败 |
| 6 | prescan 报 critical：`Makefile` 里的 `ln -s` 在 HMDFS 上不受支持（PSCAN-HMDFS-001） | 通用规则；本包实测未复现 | 实测 `ln -sf libpri.so.1.4 libpri.so` 在构建目录 rc=0（日志 `w3-local-ci.log`），共享分支产物 symlink 正常创建；保留为已评估的非阻塞观察项 |

## 源码修改

| 补丁 | 文件 | 内容 |
|------|------|------|
| `0001-Makefile-parameterize-archiver.patch` | `Makefile` | 新增 `AR=ar` / `RANLIB=ranlib` 默认值；静态库规则由字面 `ar rcs` / `ranlib` 改为 `$(AR)` / `$(RANLIB)` |
| `0002-testprilib-use-posix-signal-header.patch` | `testprilib.c` | `#include <sys/signal.h>` → `#include <signal.h>` |

两个补丁都是可移植性改动，不改任何被测行为；`rosetest.c` / `test_package/` 未修改上游测试语义。

## 依赖版本

无第三方依赖（仅 libc；`nm --undefined-only libpri.a` 全部落到 libc 符号，无 libm/pthread 需求）。

## 验证结果

```bash
# 上游测试（build() 内执行，conan create 日志留痕）
upstream rosetest: 267/267 cases executed, 0 failure marker(s)
upstream testprilib: 4/4 required protocol event lines present

# 适配后消费者测试（test_package，链接安装后的 libpri.a + include/libpri.h）
./test_libpri
27 checks, 0 failed
```

## 交付物

| 文件 | 说明 |
|------|------|
| `include/libpri.h` | 公共头（上游原样） |
| `lib/libpri.a` | 静态库（`shared=False` 默认；`shared=True` 时交付 `libpri.so.1.4` + `libpri.so`） |
| `licenses/LICENSE` | 上游 GPL-2.0 许可证 |

## 注意事项

1. `libpri` 是 GPL-2.0-or-later；静态链接进下游会传染 GPL，属上游许可约束而非本适配引入。
2. `pritest` 需要 DAHDI 内核驱动与 `/dev/dahdi/*` 设备，OHOS 无法运行；它在上游是「接电话」演示程序，不是无硬件可跑的自动化用例。
3. 共享库 SONAME 固定为 `libpri.so.1.4`（上游 Makefile `SONAME:=1.4`，与包版本 1.6.0 不同名，属上游设计，未改）。
