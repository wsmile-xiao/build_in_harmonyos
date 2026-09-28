# outils-ts 0.14 适配笔记

## 身份与版本口径

| 项 | 值 |
|---|---|
| 请求名 / 版本 | `outils-ts` / `0.14` |
| 实际实体 | 上游工程 **outils**（"port of some non-standard OpenBSD tools to Linux"，作者 Leah Neukirchen）中的 **`ts` 工具** |
| 上游仓库 | <https://github.com/leahneukirchen/outils> |
| 上游 tag / commit | `v0.14` / `32b1295c6918db01c23f6921c46b6e3b70bd516b`（2025-05-25） |
| 源码 tarball | `https://github.com/leahneukirchen/outils/archive/refs/tags/v0.14.tar.gz`，sha256 `e4dcbd92b25bbb371216b0fad5aa80cdff19f466f7ec8b5e145111fb348c91eb`（281863 B，194 条目） |
| 许可证 | 0BSD（AUR `outils` 0.14-3 声明）；代码源自 OpenBSD CVS（ts.c 为 ISC 风格） |
| 构建系统 | makefile（手写 GNU Makefile，无 configure/cmake/meson） |
| 语言 | C（R47 预检：task=cpp，detected=c，兼容族） |

`outils-ts` = outils 内 ts 组件的独立包（AUR 亦按 `outils-<tool>` 拆包，如 `outils-apply`/`outils-rdate`）。
同源父工程包 `outils/0.14`（含全部 13 个工具）已在本制品仓发布（`conan download outils/0.14 -r=ohpcd --only-recipe` → rc=0）。

## 编译环境
- 构建系统: makefile（上游手写 Makefile，无 configure）
- 编译日期: 2026-09-26
- 编译器: clang 15.0.4（OHOS SDK，target `aarch64-unknown-linux-ohos`）
- 状态: built

## 编译步骤
1. 下载官方 tag 归档（GitHub archive v0.14，sha256 `e4dcbd92…91eb`，与 conandata.yml 声明值逐字节一致）
2. 应用 1 个补丁（见下）
3. `make CC="<clang>" -j1 src/usr.bin/ts/ts`（只构建 ts 目标；Makefile 自带 CPPFLAGS/LDFLAGS/LIBS，无需额外参数）
4. 上游无测试套件（R51 清点：13 个 Makefile 的 test/check/regress 目标计数 = 0，无 tests/ 目录，无 CI 配置）
5. test_package：10 组、23 个断言（含鸿蒙特有 11 项：T9 reallocarray 增长路径 2 项 + T10 ELF/ABI/依赖 9 项）

## 遇到的问题与解决方案

| # | 问题 | 首个真实错误 | 根因 | 解决方案 | 重新验证 |
|---|------|--------------|------|----------|----------|
| 1 | ts 链接失败 | `ld.lld: error: undefined symbol: reallocarray ▶ referenced by ts.c ▶ src/usr.bin/ts/ts.o:(main)` | OHOS 的 musl libc 不提供 `reallocarray(3)`（glibc 提供）；上游 Makefile 的 ts 闭包只链 `ts.o + strlcpy.o + pledge.o`，而同源兼容实现 `src/liboutils/reallocarray.c` 未参与链接 | 补丁 0001：把 `src/liboutils/reallocarray.o` 加入 ts 目标（与同源 `rs`/`rdate` 目标写法一致） | `make CC=clang src/usr.bin/ts/ts` → rc=0；产物 `ELF 64-bit LSB arm64, PIE`，NEEDED 仅 libc.so |

### 补丁生成过程的一处修正
`refresh-patch --auto` 首轮生成的补丁除目标行外还夹带了 `ALL=` 行的尾随空格差异（`.work` 侧该行尾随空格丢失）。为保持补丁最小化，已把该行恢复为与上游逐字节一致后再生成，最终补丁为 `+1/-1`，仅动 ts 目标行。

### 本地 CI 模拟对 conandata.yml 的临时改写（已还原）
W3/CI 的 `ci/conan/build_and_test.sh` 会在"Mirror fallback"步骤把 conandata 中的 `github.com` 源改写为 URL 列表（`https://gh-proxy.com/<orig>` + 原 URL），并把备份写成 `<version>/conandata.yml.orig`；该步骤**没有还原逻辑**（后续 pre-download 步骤的 `trap EXIT` 只还原它自己那份 file:// 改写）。因此本地跑完 `finish` 后必须手动把 `conandata.yml` 还原为单一官方 URL 并删除 `conandata.yml.orig` / `conandata.yml.ghfast-bak`，否则会被 PF7（源 URL 闸）判 FAIL。本包最终提交版本为单一官方源，见 conandata.yml。

## 源码修改

| 文件 | 修改内容 | 补丁 |
|------|----------|------|
| Makefile | ts 目标补链 `src/liboutils/reallocarray.o` | 0001 |

> 未改动任何 `.c/.h`；无平台宏注入（R8/PF5 无命中）。

## 依赖
- 无第三方依赖（`requires` = 0）。ts 仅链接 libc（+ 同源 `liboutils` 对象：strlcpy / pledge(stub) / reallocarray）。
- `pledge(3)` 在 Linux/OHOS 下即同源空实现（`src/liboutils/pledge.c`: `int pledge(...) { /* stub */ return 0; }`）。
- W0 核验：`conan download outils/0.14 -r=ohpcd --only-recipe` → rc=0；无第三方依赖需要探测。

## 验证结果

```bash
make CC=clang src/usr.bin/ts/ts     # rc=0
printf 'foo\nbar\n' | ts            # Sep 26 13:37:10 foo / ... bar
./run_ts_tests.sh <ts>              # 9 用例 9 通过（上游样例 + 选项矩阵）
conan create .                      # 见 reports/conan-create.log
conan-verify outils-ts 0.14         # 见 reports/conan-verify-report.md
```

- 上游无自动化测试套件（清点证据见 `reports/upstream-test-inventory.log`），故按 ts(1) 手册的 SYNOPSIS/EXAMPLES 构造等价用例并全部实跑。
- test_package 的 T9 覆盖 OHOS 适配唯一改动点（reallocarray 扩容路径）；T10 覆盖打包 ELF 的 AArch64/PIE/musl/依赖形状。
- `conan create` 实测：test_package 输出 `--- results: 23 passed, 0 failed ---` / `OUTILS_TS_OK: all 23 checks passed`。
- `conan-verify outils-ts 0.14` 判定 **PASS**（G0/G1/G2/G3/G4 全过；`archives/o/outils-ts/0.14/reports/conan-verify-report.md`）。
  - 说明：本机环境下 L2/L4/L5 三门为 `⏭️ 跳过（无 cache 路径）`（G4 的程序包 ID 查询在当前 conan 2.29.1 的 `conan list --format=json` 层级结构上未命中，与同源父包 `outils/0.14` 的报告表现一致）。该三门的等价证据由 test_package 提供：它在真实打包产物上执行 23 项断言，已覆盖 L2 的"二进制可运行"与 L4/L5 关心的 ELF 属性（PIE、musl 解释器、唯一 NEEDED、无 RPATH/RUNPATH）。
---

**编译结束**: 2026-09-26 14:14
**最终状态**: built
