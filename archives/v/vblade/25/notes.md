# vblade 25 适配笔记

## 软件与来源

- 软件：vblade 25（minimal userland AoE target，OpenAoE）
- 上游仓库：https://github.com/OpenAoE/vblade
- 上游版本：tag `vblade-25`（`https://github.com/OpenAoE/vblade/archive/vblade-25.tar.gz`，32524 B）
- SHA256：`ce498da9b26b6dc0859b94e869dea9f3f67e3d6d27a09d48cc97250c55224685`
- 许可证：GPL-2.0-only（`COPYING`）
- 构建系统：plain Makefile（`makefile`，小写；targets 仅 `vblade/clean/install`）

## 编译环境

- 平台：HarmonyOS PC aarch64（真机预检，HongMeng Kernel + /data/service/hnp 工具链 + conan 2.30）
- 编译器：clang（取自 `tools.build:compiler_executables:c`，R33 合规，不裸用 shell `$CC`）
- Conan：OHOS 适配版，profile `ci/conan/profiles/ohos-aarch64`
- 状态：`built`（工作树首轮，真机 rule4 门禁待 HMBS 后台验证）

## W0 依赖核验

vblade 无第三方库依赖（仅系统头：`sys/socket.h`、`netpacket/packet.h`、`net/ethernet.h`、`linux/fs.h` 等）：

| 依赖 | 用途 | 核验 | 结果 |
|------|------|------|------|
| 无 | 仅系统头/系统调用 | 源码审计：`aoe.c/ata.c/bpf.c/linux.c/dat.c` 无第三方 `#include` | 无需发布依赖 |

## 编译步骤

```bash
make CC=<clang-from-conan-conf> -j1
# 产物：vblade（ELF64 aarch64）+ config.h（u64 探测生成）
# 打包：copy bin/vblade、bin/vbladed、share/man/man8/vblade.8、licenses/COPYING
```

说明：

- 上游 `makefile` 硬编码 `CC = gcc`；以 `make CC=...` 命令行覆盖，同时覆盖 `config.h` 探测规则中的 `${CC}`。
- 不调用 `make install`：其默认 `prefix=/usr` 且依赖 `install` 程序；改用 Conan `copy()` 直拷产物，在 HMDFS/受限 PATH 下更可靠。
- 不调用 `make check`：上游无该目标（审计结论 `no_tests`），`build()` 改为发射 `HMBS_UPSTREAM_TEST_RESULT` no_tests 机器证据。

## 上游测试审计（no_tests）

- 解包 `vblade-vblade-25.tar.gz` 全树 36 条目：无 `tests/`、`test/`、`spec/`、`t/` 目录；无 `*test*` 文件名。
- `makefile` 仅 `vblade/clean/install` 三目标；`aoe.c` 的 `main()` 为业务入口，`config/u64.c` 为 `config.h` 探测程序，均非测试套件。
- `make -n check` 为 make 空操作（`No rule to make target 'check'`），执行 0 用例。
- 结论：`upstream_tests_exist: false`，`upstream_test_total: 0`，口径 `autotools_tests`（makefile 无测试注册等价口径）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 `CC = gcc` 写死 | 原生 Linux 假设 | `make CC=<conan-conf-clang> -j1` 命令行覆盖（R33 合规） |
| 2 | `make check` 无目标 | 上游无测试套件 | 不调用；发射 no_tests 证据，test_package 做消费者冒烟测试 |
| 3 | `install` 路径在 OHOS 受限 | `make install` 依赖 `prefix`/`install` | 改用 `copy()` 直拷 `bin/`、`share/man/`、`licenses/` |

## 依赖版本

- 无 Conan 依赖（`requirements()` 为空）。

## 验证结果（待真机 evidence 轮回填实测数字）

```bash
# 配方构建（含上游 no_tests 证据）
conan create archives/v/vblade/25 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# 消费者冒烟测试（4 断言）
bash test_package/test_vblade.sh <package>/bin/vblade
# CASE SUMMARY: total=4 passed=4 failed=0 skipped=0
# HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"bash test_vblade.sh","discovered":4,"passedCount":4}
# HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests","framework":"makefile","command":"make check","discovered":0,"executed":0,"passed":0,"failed":0,"skipped":0}
```

## 平台限制（HarmonyOS PC）

1. **特权运行时**：`dial()` 使用 `PF_PACKET/SOCK_RAW` + `SO_ATTACH_FILTER`，`getsize()` 用 `BLKGETSIZE64`；在普通用户沙箱中打开发送/绑定会失败。冒烟测试仅覆盖“二进制可执行 + usage 路径”，不做真实 AoE 导出。
2. **无 `--version/--help`**：错误用法统一打印 `usage: ... shelf slot netif filename` 到 stderr 并 `exit(1)`；测试据此断言（退出码 + 非空 + 关键字），并设负向对照（非法选项同样被拒绝）。

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/vblade` | AoE 存储目标主程序（ELF64 aarch64） |
| `bin/vbladed` | 守护化包装脚本（调用 `logger`） |
| `share/man/man8/vblade.8` | 手册页 |
| `licenses/COPYING` | GPL-2 许可证正文 |

## 注意事项

- 零补丁构建；若真机出现 `features.h`/`netpacket`/`linux/fs.h` 缺失，再按 POSIX 兼容方式补齐（当前配方不预设平台宏）。
- 本轮为工作树首轮：未 commit、未 push；待 HMBS 真机 rule4 全部门禁通过后再提交。
