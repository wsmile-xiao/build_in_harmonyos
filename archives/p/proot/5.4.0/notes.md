# proot 5.4.0 适配笔记

## 编译环境
- 构建系统: 手写 GNUmakefile（`make -C src proot`；ELF loader 由 objcopy/objdump 包装进二进制）
- 编译日期: 2026-10-12
- 编译器: OHOS SDK clang 15.0.4（`~/.harmonybrew/opt/ohos-sdk@26.0.0.18/native/llvm/bin`）
- 目标平台: HarmonyOS PC / aarch64-linux-ohos（HongMeng Kernel 1.12.0，HAD-W32/W24）
- 上游源码（GitHub 官方 tarball 端点 codeload）:
  <https://codeload.github.com/proot-me/proot/tar.gz/refs/tags/v5.4.0>
  - sha256 = `29248aac2a7ce10c3bd5ee5602742ec33b2532310ff9cf73b79f3c133e5a5f68`
- 依赖: `talloc/2.4.4`（Conan 制品仓；proot 经 pkg-config 定位）
- Conan profile: `ohos-aarch64-device`（本机图像；CI 使用仓库 profile）
- 版本号: 构建时显式传 `VERSION=5.4.0`（上游从 `git describe` 推导，发行 tarball 无 .git）

## 编译步骤
1. `get()` 下载官方 tag 归档；`apply_conandata_patches()` 应用 4 个可移植性补丁
2. `make -C src proot -j1 CC=<conan conf clang> VERSION=5.4.0`（R9/R33）
   - `PKG_CONFIG_PATH`/`PKG_CONFIG_LIBDIR` 只指向 Conan `PkgConfigDeps` 生成的 talloc.pc（无宿主污染）
   - `OBJCOPY`/`OBJDUMP`/`STRIP` 优先解析编译器同目录的 LLVM 工具（设备与 CI 布局均可）
3. `package()` 显式拷贝 `bin/proot` 与 `licenses/COPYING`
   （上游 `make install` 依赖 `install(1)`，OHOS 无此命令）
4. `conan create` 内 test_package：`sh test_proot.sh` 16/16 PASS

## 上游测试清点（R51 申报表）

| 检查项 | 命令 | 结果 |
|---|---|---|
| 测试目录 | 解压树 `test/` | 存在：GNUmakefile + 94 个 `test-*.sh` + 36 个 `test-*.c` + 辅助程序（argv.c 等）+ docker/、sockets/ |
| 测试入口 | `make -C test check` | `check → clean_failure → check_failure → check-<name>`（.sh 用 `sh -ex`；.c 编译为 rootfs 静态程序后经 `proot -b /proc -r $ROOTFS /bin/<name>` 运行） |
| 测试依赖 | 各脚本头部 `which` 守卫 | mcookie/cpio/mknod/realpath 等具备；**gdb、strace、ldd、setcap、domainname、docker/podman 缺失**；CARE 未构建（本包只构建 proot） |
| 真机执行 | 监督器包裹 `make -C test check`（逐项语义不变，仅对挂死用例设 120s 看门狗） | **134 项检查 = 2 ok / 110 FAILED / 22 skipped**（1 项无输出挂死被看门狗击杀；失败主因见下节） |
| 挂死用例 | `test-gdb-ptrace.sh` | 前置二进制 `gdb-ptrace-test`（自身用 ptrace 模拟 gdb）在无 ptrace 环境挂死；120s 看门狗击杀后按 FAILED 记录（如实申报） |

**结论**：上游 134 项检查中绝大多数失败——根因是**平台能力边界**：OHOS 内核对非特权进程
禁用 ptrace（自建探针：`PTRACE_TRACEME/ATTACH/SEIZE` 与 `process_vm_readv` 全部被拒，
CapEff 无 CAP_SYS_PTRACE，进程带 Seccomp filter），proot 的每次 tracee 执行都在
`ptrace(TRACEME)` 被拒。22 项因缺外部工具/前置程序按上游惯例跳过（exit 125）。2 项"通过"
的断言是「非 root 使用 -i/-0 必须失败」——因平台边界确实失败而按断言口径通过（与上游
预期原因不同，如实记录）。逐项清单与样本见 `reports/test-report.md`。

## 平台能力边界：OHOS 禁止非特权进程使用 ptrace（本任务核心事实）

自建最小探针（源码 `probe/ptrace-probe.c`，输出 `ptrace-capability-probe.txt`，位于本任务
工作区）在同一 SSH 会话、同一 UID 实测：

| 场景 | 结果 |
|---|---|
| 子进程 `PTRACE_TRACEME` | 被拒（exit=1） |
| 父 → 子 `PTRACE_ATTACH` | `-1 / EACCES (Permission denied)` |
| 父 → 子 `PTRACE_SEIZE` | `-1 / EACCES` |
| `process_vm_readv` 读子进程内存 | `-1 / EACCES` |
| `prctl(PR_SET_PTRACER, PR_SET_PTRACER_ANY)` | `-1 / EINVAL` |
| `/proc/self/status` | `Seccomp: 2`、`Seccomp_filters: 1`、`CapEff=0x2a`（无 CAP_SYS_PTRACE） |
| `/proc/sys/kernel/yama/ptrace_scope` | 不存在（ENOENT） |

**影响**：proot 的隔离执行功能（`-r`、`-b`、`-0`、`-R/-S` 等）在该平台上被系统策略阻断，
任何用户态补丁都无法绕过；CLI 表面（`--version`/`-V`/`--help`、参数校验、错误报告、
rootfs 绑定校验）完整可用，由 `test_package/test_proot.sh` 的 16 条消费侧断言覆盖。
与同平台 reptyr 任务记录的能力边界一致。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `error: type name requires a specifier or qualifier`（CIRCLEQ_ENTRY 等 12 处） | OHOS `<sys/queue.h>` 为 FreeBSD 衍生版且已移除 CIRCLEQ 家族（FreeBSD 2018 删除；musl 系不提供） | 补丁 0002：`src/path/binding.h` 中 `#ifndef CIRCLEQ_HEAD` 守卫下补标准 CIRCLEQ 宏（特性检测，无平台宏） |
| 2 | `error: incompatible integer to pointer conversion ... get_current_dir_name` | `get_current_dir_name()` 为 GNU 扩展，OHOS C 库不声明/不提供 | 补丁 0003：改用上游 `__ANDROID__` 分支同款的可移植 `getcwd()` 写法（libc 特性检测） |
| 3 | `error: redefinition of 'struct sockaddr_storage'`（portmap.c） | `<linux/net.h>` 经 `<linux/socket.h>` 定义内核侧同名结构，与 musl 系 `<sys/socket.h>` 冲突 | 补丁 0001：包含 UAPI 头期间重命名内核侧结构（E091 同类；glibc 不受影响） |
| 4 | 上游测试 `test/ptrace-2.c` 无法编译（`enum __ptrace_request`） | glibc 专属类型，OHOS C 库无 | 补丁 0004：无该类型时以 `int` 声明（Alpine Linux 对同一测试的相同修法） |
| 5 | 版本横幅退化为 `-` | GNUmakefile 用 `git describe` 推导版本，tarball 无 .git | 构建时显式传 `VERSION=5.4.0`（Alpine 同法） |
| 6 | 上游测试大面积失败 | OHOS 禁止非特权 ptrace（见上节） | 如实记录平台边界；test_package 覆盖可用行为面 |

## 源码修改

`patches/` 四个补丁，均为可移植性修复，均不注入平台宏（R8/PF5）：

1. `0001-src-extension-portmap-portmap.c.patch` — sockaddr_storage 重定义（+12）
2. `0002-src-path-binding.h.patch` — CIRCLEQ 兼容宏（+101）
3. `0003-src-path-temp.c.patch` — get_current_dir_name 兼容（+4/-1）
4. `0004-test-ptrace-2.c.patch` — 上游测试 glibc 类型兼容（+7/-1）

## 依赖版本

- `talloc/2.4.4`（W0：`conan download talloc/2.4.4 -r=ohpcd` 验证已发布；见验证结果）
- uthash 随源码内置（`lib/uthash/include`）；CARE 未构建（其 libarchive 依赖无需引入）

## 验证结果

```text
# 本机手工构建（OHOS SDK clang 15.0.4，aarch64 设备原生）
make -C src proot -j1 CC=<SDK clang> VERSION=5.4.0  → rc=0；产物 src/proot (ELF aarch64)
./src/proot --version → rc=0，打印 "5.4.0" 与 "accelerators: process_vm = yes, seccomp_filter = yes"
./src/proot --help    → rc=0，完整用法
./src/proot（缺命令）  → rc=1，"fatal error: see `proot --help`."
./src/proot --bogus   → rc=1，"unknown option '--bogus'."
./src/proot -r / /bin/true → rc=1，"ptrace(TRACEME): Permission denied"（平台边界，见上节）

# 上游套件（真机，监督器逐项执行 make -C test check）
134 项检查 = 2 ok / 110 FAILED / 22 skipped（详见 reports/test-report.md）

# W0 依赖验证
conan download talloc/2.4.4 -r=ohpcd --only-recipe → rc=0（revision 142e47a8…）
conan download talloc/2.4.4 -r=ohpcd               → rc=0（OHOS/armv8/clang 15/Release 已发布）

# conan-verify（profile ohos-aarch64-device）
G0–G4 + L2/L4/L5 全 PASS；G2 conan create 成功（reports/conan-verify-report.md）
test_package：sh test_proot.sh → 16/16 PASS（reports/conan-create.log："# passed: 16, failed: 0"）
产物：package 内 2 个文件（bin/proot、licenses/COPYING）

# 本地 CI 门禁与 finish
本地 CI 门禁（平台同款脚本）: L0/L1/L1a/L1b/L1e/L2/L4/L5 PASS，KC/JC 通过
finish: W3 本地 CI 模拟通过；.ci-result.json exit_code=0（integrity_hash 8b04f4b6ea183d35）
```

## 交付物

| 文件 | 说明 |
|------|------|
| bin/proot | 主程序（aarch64 ELF，动态链接 OHOS libc） |
| licenses/COPYING | GPL-2.0-or-later 许可证 |

## 注意事项

- 产物为可执行命令，已在软件级 `archives/p/proot/commands.json` 声明（R38）。
- **核心功能受平台边界限制**：OHOS 对非特权进程禁用 ptrace；`proot <命令>` 在
  `ptrace(TRACEME)` 处被拒（"Permission denied"，rc=1），隔离执行不可用。复现探针与输出
  见本任务工作区 `ptrace-capability-probe.txt`。
- 上游测试需外部工具（gdb/strace/ldd/setcap/domainname/docker）与 CARE；缺失者按上游惯例
  跳过（exit 125），已在 `reports/test-report.md` 逐一列明。

---
**编译结束**: 2026-10-12
**最终状态**: built
