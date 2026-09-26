# libxdp 1.6.3 适配笔记

## 定位
- 目标库：**libxdp 1.6.3**（KIND：目标库；任务 #8447，分支 `feat/libxdp-1.6.3`）
- 上游：**xdp-tools** 的 libxdp 库（`github.com/xdp-project/xdp-tools`，tag `v1.6.3` → commit `8fbad9f0af621a22aa87ff2520b3735915b1f0fd`）
- 角色：XDP/eBPF 程序的用户态加载库（`libxdp.so.1`/`libxdp.a`），BPF 程序以 `lib/bpf/*.o` 形式随库分发

## 编译环境
- 构建系统：**自定义 shell `configure`（非 autoconf）+ GNU Make**；`init-build` 自动判为 autotools 属误判（本配方按 makefile 处理）
- 编译日期：2026-09-21
- 编译器：OHOS SDK clang 15.0.4（WSL 交叉）/ `/data/service/hnp/bin/clang`（真机原生）
- 状态：**built**

## 编译步骤
1. WSL 交叉：`conan create archives/l/libxdp/1.6.3 -pr:h=ohos-aarch64-wsl -pr:b=default -r=ohpcd` → **EXIT=0**
   （日志 `/mnt/e/dsh working/tasks/libxdp-1.6.3-2026-09-21/logs/025e-conan-create-cross.log`）
2. 鸿蒙笔记本原生：
   ```sh
   ~/.local/bin/conan create archives/l/libxdp/1.6.3 \
       -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
   ```
   → **conan create 退出码 0**，test_package **1/1 Passed（100%）**，0.03s（截图 `logs/070-laptop-native-build-test-pass.png`）
3. 关键命令：`bash configure`（见"问题 1"）→ `make libxdp` → `make libxdp_install PREFIX=<package>`

## 上游测试（R51 申报）

- 测试入口：**`make -C lib/libxdp test`** → `lib/libxdp/tests/test-libxdp.sh`（`test_runner.sh` 驱动）
- **注册口径**：`test-libxdp.sh` 的 `ALL_TESTS` = **10 个注册用例**（`test_link_so`、`test_link_a`、`test_old_dispatcher`、`test_xdp_devbound`、`test_xdp_frags`、`test_xsk_prog_refcnt_bpffs`、`test_xsk_prog_refcnt_legacy`、`test_xsk_non_privileged`、`test_link_detach`、`test_xsk_umem_flags`）。
- **测试源存量口径**：`lib/libxdp/tests/` 下 **12 个 `.c` 测试源** = 8 个用户态程序 + 3 个 BPF 程序 + 1 个共享辅助（`test_utils.c`）。
- **忠实模式实跑（关键证据）**：含 `unshare -n -m` 的上游原样 runner 在 OHOS 上打印 `Executing tests in separate net- and mount namespaces` 后立即 `zsh: invalid system call (core dumped)` —— **OHOS seccomp 以 SIGSYS 杀死 `unshare(CLONE_NEWNET|CLONE_NEWNS)`**；故只能置 `DID_UNSHARE=1` 在宿主 netns 下运行，此时 bpffs 挂载 / netlink veth / BPF 执行被 SELinux/内核拒绝。
- **执行结果（鸿蒙笔记本 HUAWEI MateBook Pro / OHOS 以 root 实跑官方 runner）：0 PASS / 8 环境阻塞（NOT_RUN）/ 2 link-only**：
  - 4 条（`test_old_dispatcher`、`test_xdp_devbound`、`test_xdp_frags`、`test_xsk_prog_refcnt_bpffs`）：`Unable to mount /sys/fs/bpf`（OHOS 内核无 bpffs）；
  - 3 条（`test_xsk_prog_refcnt_legacy`、`test_link_detach`、`test_xsk_umem_flags`）：`ip: can't talk to rtnetlink: Permission denied` + 测试二进制 `Operation not permitted`(126)（SELinux 拒 netlink/BPF 执行）；
  - 1 条 `test_xsk_non_privileged`：SKIPPED（未构建，缺 HAVE_CAP_NG）；
  - 2 条 `test_link_so`/`test_link_a`：编译+链接检查（link-only），等价能力由 `test_package` 的编译+链接+运行 `1/1` 覆盖。
  - **上述均为 OHOS 平台（内核/SELinux）限制，非本适配缺陷；按 R51 如实申报，未写 PASS。**
- **实跑环境要点**：OHOS 的 `sudo` 只支持 `sudo <cmd>`（不支持 `-S/-v`）；busybox 自带 `ip`/`unshare` 可做 shim；上游 runner 的 `#!/bin/bash` 在 OHOS 不存在（`/bin`→`/system/bin` 只读），需以 hnp bash 直跑 runner；`/data/local/tmp` 连 root 也被 SELinux 拒写。
- **R40 人工确认**：libxdp 是 XDP/eBPF 底层加载库，OHOS 无 BPF syscall 时 `attach/load` 路径不可用；本包可验证面为非 syscall API，**适配完整性需人工确认**。

## 遇到的问题与解决方案（四段式）

### 1. `configure` 在真机报 `/tmp/...: Read-only file system`，随后 libbpf 探针 `undefined symbol: main`
- **首错原文**：`configure[460]: can't create temporary file /tmp/shvdtgay.tmp: Read-only file system`；
  `ld.lld: error: undefined symbol: main`
- **根因**：鸿蒙电脑 `/tmp` 只读；`sh`（dash）把 here-document 临时文件写在 `/tmp`，导致 `quiet_config` 失败、
  libbpf 探针源文件未生成 → 链接只剩 crt，报 `undefined symbol: main`。
- **修复**：配方用 **bash**（尊重 `TMPDIR`）执行 configure，并把 `TMPDIR` 指到构建目录下的可写子目录
  （`conanfile.py` 的 `_bash()` / `_env()`）。WSL（`/tmp` 可写）与真机均通过。
- **验证**：真机 `configure` 输出 15 个 libbpf 函数探针全 `yes`。

### 2. `clang -target bpf` 编 `xdp-dispatcher.o` 报 `linux/types.h: No such file or directory`
- **首错原文**：`../../headers/linux/bpf.h:11:10: fatal error: 'linux/types.h' file not found`
- **根因**：BPF 目标编译不会应用编译器的默认 sysroot 搜索列表；`configure` 只把**arch 子目录**
  （`.../sysroot/usr/include/aarch64-linux-ohos`）放进 `ARCH_INCLUDES`，而 `linux/types.h` 在
  `.../sysroot/usr/include`（WSL 上恰好被宿主 `/usr/include` 兜住，掩盖了问题）。
- **修复**：配方在 `generate/build` 期用 `$CC -E -Wp,-v -xc -` 取编译器自身的 include 搜索列表，
  经 `ARCH_INCLUDES` 环境变量注入 Makefile（`BPF_CFLAGS` 也会带上）。
- **验证**：真机 BPF 对象 `xdp-dispatcher.o`、`xsk_def_xdp_prog.o`、`xsk_def_xdp_prog_5.3.o` 全部编译通过。

### 3. `sockaddr_storage` 重定义（E119 模式；两次触发）
- **首错原文**：`.../sysroot/usr/include/linux/socket.h:23:8: error: redefinition of 'sockaddr_storage'`；
  `.../usr/include/sys/socket.h:377:8: note: previous definition is here`
- **根因**：OHOS/bionic sysroot 的 `linux/socket.h` 与 `sys/socket.h` 都定义 `sockaddr_storage`；
  libxdp 经 **vendored** `headers/linux/if_link.h` → `linux/netlink.h` 把 uapi 版拉进来。
- **修复**：按 **E119** 平台无关自守卫，在 vendored `headers/linux/if_link.h` 里先
  `#include <sys/socket.h>`，再 `#if !defined(_UAPI_LINUX_SOCKET_H) ... #define ... typedef __kernel_sa_family_t ...`
  屏蔽 uapi 头。该文件只被用户态对象使用；BPF 目标只用 `linux/bpf.h`，不受影响（已核验）。
- **验证**：`libxdp.c`/`xsk.c` 与 7 个上游测试程序全部编译通过。

### 4. `vendored linux/compiler_types.h` 条件包含 `compiler-gcc.h`，在坏人 sysroot 上触发 guard 报错
- **首错原文**：`headers/linux/compiler-gcc.h:3:2: error: "Please don't include <linux/compiler-gcc.h> directly, include <linux/compiler.h> instead."`
- **根因**：OHOS/bionic 的 `linux/stddef.h` 会 `#include <linux/compiler_types.h>`；由于 `-I headers` 在
  隐式 sysroot 之前，解析到 **vendored** `compiler_types.h`，其无条件 `#include <linux/compiler-gcc.h>`
  在 `_TOOLS_LINUX_COMPILER_H_` 未定义时（只有 `linux/compiler.h` 会定义）报错。WSL 宿主
  `/usr/include/linux/stddef.h` 不 include compiler_types.h，故只在 OHOS 暴露。
- **修复**：把 `#include <linux/compiler-gcc.h>` 从 `compiler_types.h` 移到 `compiler.h`
  （守卫定义之后），保持上游语义（`compiler.h` 是唯一正规入口）。
- **验证**：真机与 WSL 均通过。

### 5. musl 无 `secure_getenv`，上游回退实现引用 musl 内部 `libc.secure`
- **首错原文**：`./compat.h:9:9: error: use of undeclared identifier 'libc'`（`test_utils.c` 同样）
- **根因**：OHOS musl 未导出 `secure_getenv`（链接探针 `undefined symbol`），`HAVE_SECURE_GETENV` 未定义，
  上游回退体用的是 **musl 内部** `libc.secure`，外部库不可见。
- **修复**：回退改用 `getauxval(AT_SECURE) ? NULL : getenv(name)`（与 glibc 语义一致）；
  并让测试共用 `compat.h`（`test_utils.h` 引入）。
- **验证**：真机链接、L1 运行均通过。

## 依赖版本
| 依赖 | 版本 | 来源 | 状态 |
|------|------|------|------|
| libbpf | 1.5.1 | ohpcd（静态库；xdp-tools 1.6.3 的 gitlink 为 libbpf 1.5.0） | ✅ 已发布 |
| elfutils（libelf） | 0.195 | ohpcd（libbpf 静态传递） | ✅ |
| zlib | 1.3.1.1 | ohpcd（libbpf 静态传递） | ✅ |
| m4 / pkg-config / llvm-objcopy / llvm-readelf / clang | — | 真机 `/data/service/hnp/bin`；WSL DevEco SDK | ✅ |

## 验证结果
```
# WSL 交叉（交付架构 aarch64-linux-ohos）
conan create archives/l/libxdp/1.6.3 -pr:h=ohos-aarch64-wsl -pr:b=default -r=ohpcd
→ libxdp/1.6.3 ... Package 'a633df2f...' created   EXIT=0

# 鸿蒙电脑原生（=CI 路径）
conan create archives/l/libxdp/1.6.3 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
→ 1/1 Test #1: test_libxdp ...... Passed  0.03 sec
→ 100% tests passed, 0 tests failed out of 1
```

## 交付物（包内）
| 路径 | 说明 |
|------|------|
| `include/xdp/*.h` | 公开头文件（`libxdp.h`/`xsk.h`/…） |
| `lib/libxdp.a`、`lib/libxdp.so.1.6.0`（soname `libxdp.so.1`） | 静态 + 共享库（546 个导出符号） |
| `lib/bpf/{xdp-dispatcher,xsk_def_xdp_prog,xsk_def_xdp_prog_5.3}.o` | 内嵌 XDP 程序对象 |
| `lib/pkgconfig/libxdp.pc` | pkg-config |
| `share/xdp-tools/tests/libxdp/*` | 上游测试程序（`make libxdp_install` 安装） |
| `share/man/man3/libxdp.3` | 手册页 |

## 注意事项
1. **OHOS 无 BPF syscall**（seccomp/SIGSYS）：libxdp 的 `xdp_program__attach` 等加载/挂载路径在设备上不可用；
   本包可用的是 ELF/BTF 解析、程序对象管理、错误处理等非 syscall API。上游测试因此不执行（见上）。
2. `xdp_program__open_file()`/`find_file()` 失败时返回 **ERR_PTR 而非 NULL**，必须用 `libxdp_get_error()` 判定，
   不可直接 `xdp_program__close()`（L1 初版曾因此段错误，已修正）。
3. 鸿蒙电脑 `/tmp` 只读 → 构建必须用 bash + 可写 `TMPDIR`（本配方已处理）。
4. `make` 会输出 `jobserver mkfifo /tmp/GMfifo...: Operation not permitted` 警告，属设备 `/tmp` 只读的
   警示信息，不影响构建结果；CMake 亦会提示 `System is unknown to cmake, create Platform/HarmonyOS`（已知无害）。
5. 官方 release 资产（`releases/download/v1.6.3/xdp-tools-1.6.3.tar.gz`）由 `mkarchive.sh` 合并了 libbpf 子模块；
   本配方显式走系统 `libbpf/1.5.1`（`FORCE_SYSTEM_LIBBPF=1`），不构建树内子模块。
6. 路径 B 归属：`xdp` 词边界 0 命中；最近条目 **E334**（fastnetmon 后端门控）只讲"关掉 Linux-only 抓包后端"，
   本库贡献的是**构建机制**（自定义 configure 探针 + `clang -target bpf` + `ld --format=binary` 嵌入）与
   E119/E320 同族的 sysroot/头文件冲突，差异见知识草稿（02 定稿时产出）。
---

**编译结束**: 2026-09-21 21:00
**最终状态**: built
