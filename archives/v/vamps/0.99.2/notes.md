# vamps 0.99.2 适配笔记

## 编译环境
- 构建系统: makefile（上游为手写递归 Makefile，无 configure / 无 CMake）
- 编译日期: 2026-09-20
- 编译器: clang 15.0.4（conan profile `tools.build:compiler_executables.c` = /data/service/hnp/bin/clang，OHOS SDK 工具链）
- 依赖: libdvdread/7.1.0（ohpcd 已发布，默认静态变体 libdvdread.a）
- 状态: built（本地 conan create EXIT=0 + test_package 5/5；conan-verify 全绿后待 CI）

## 编译步骤
```bash
# 独立 worktree（主仓被其他任务占用，防混入）
git worktree add /storage/Users/currentUser/tmp/wt-vamps -b feat/vamps-0.99.2 upstream/main

# 真实构建（双 profile 绝对路径，R36 依赖已提前 conan download 验证）
bin/conan create archives/v/vamps/0.99.2 \
  -pr:h=/storage/Users/currentUser/tmp/wt-vamps/ci/conan/profiles/ohos-aarch64 \
  -pr:b=/storage/Users/currentUser/tmp/wt-vamps/ci/conan/profiles/ohos-aarch64 \
  --build="vamps/*"
# → EXIT_CODE=0（本地日志 .workbuddy/tmp/vamps-0.99.2/create-r2.log，183 行，不入库；
#   入库证据为 reports/w3-local-ci.log —— W3 强制重建日志）
#   build(): make -j1 CC=<conf clang> CFLAGS="…-I<libdvdread include>" LDFLAGS="-L<libdvdread lib>"
#   包产物: bin/vamps + bin/play_cell + licenses/COPYING

# test_package（conan create 自动执行，5/5 PASS）
sh test_package/test.sh <package_folder>/bin
```

## 上游测试

**上游无任何自动化测试**（审计证据：`.workbuddy/tmp/vamps-0.99.2/upstream-test-audit.log`）：
- `find -iname "*test*"` → 源树零测试文件（EXIT=0 无文件行）
- 三份 Makefile 检索 `check:|TESTS|add_test|enable_testing|BUILD_TESTING` → 零命中（grep EXIT=1）
- gtest/pytest/criterion/unittest 绑定 → 零命中（grep EXIT=1）
- 顶层 Makefile 递归目标仅 `all install uninstall clean`

test_package 新增 **5 个鸿蒙消费者冒烟用例**（全部实际执行，5/5 PASS）：

| # | 用例名称 | 命令 | 预期 | 结果 |
|---|---|---|---|---|
| 1 | vamps_usage_bogus_option | `vamps --bogus </dev/null` | rc=1 + stderr "Usage: vamps"（musl getopt_long_only '?' 路径） | ok |
| 2 | vamps_usage_stdin_not_regular | `vamps </dev/null` | rc=1 + "Standard input is not a regular file"（musl fstat/S_ISREG 守卫） | ok |
| 3 | vamps_usage_bad_factor | `vamps -e notanumber </dev/null` | rc=1 + "Bad factor"（strtof 校验） | ok |
| 4 | play_cell_usage_no_args | `play_cell` | rc=1 + "Usage: play_cell"（二进制可加载；坏链将 rc=127） | ok |
| 5 | vamps_requant_empty_ps_eof | `vamps -e 1.0 -S 1 < 空常规文件` | rc=0 无 Fatal（malloc + pthread 管线 + 干净 EOF 关闭） | ok |

统计：发现 5、执行 5、通过 5、失败 0、跳过 0（上游测试：发现 0、执行 0——上游无测试入口，test_package 不替代上游测试统计）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 首轮 build 失败：`requant.c: error: unknown type name 'uint'` ×20 → vamps 二进制缺失，package() 守卫中止 | `uint` 是 glibc `<sys/types.h>` 在 `__USE_MISC` 下的遗留 typedef；musl 完全不提供。requant.c 是唯一消费者（29 处），vamps.c/play_cell.c 零使用 | 补丁 `patches/0001-musl-uint-typedef.patch`：在 requant.c 系统头之后补 `#ifndef __GLIBC__ typedef unsigned int uint; #endif`；净源码树 `patch -p1` 干跑校验通过后复跑 create（第 2 轮 EXIT=0） |
| 2 | 上游 Makefile 硬编码 `CC = gcc`、`LDFLAGS += -s`（链接期 strip） | 手写 Makefile 未留工具链接口 | 无需补丁：CFLAGS 为 `?=`、LDFLAGS 为 `+=`，GNU make 规则下**命令行赋值胜过 makefile 内赋值**（无 override 指令），build() 直接注入 `CC/CFLAGS/LDFLAGS`，顺带压掉 `-s` |
| 3 | conandata 源 URL 以 `/download` 结尾（SourceForge 重定向端点） | conan `get()` 会把 URL 末段误当文件名（abcmidi 同型坑），解档走错解码器 | conanfile `source()` 显式传 `filename="vamps-0.99.2.tar.gz"` |
| 4 | 上游 `install` 目标依赖 `install(1)` 且 PREFIX 写死 | 交叉/隔离环境不保证 install(1)；PREFIX 烘焙安装路径 | `package()` 直接 copy `bin/vamps`、`bin/play_cell`、`COPYING`，并断言产物存在 + chmod 0755 |

## 源码修改

一个可移植性补丁（`patches/0001-musl-uint-typedef.patch`，7 行）：requant.c 补 musl 缺失的 `uint` typedef（`#ifndef __GLIBC__` 守卫，glibc 宿主行为不变）。其余零修改：`vamps.c` 自带 `_GNU_SOURCE`（musl 下 `getopt_long_only` 可用），无 linux/asm 专有头、无 lseek64/mmap。

## 依赖版本

- `libdvdread/7.1.0`（ohpcd 已发布，R36 验证：`conan download --only-recipe` EXIT=0；`conan install --build=never` EXIT=0 Package installed；满足上游 Debian 钉定下限 `>= 4.1.3`）
- libdvdread 取默认**静态**变体链入 play_cell（NEEDED 实测仅 `libc.so`），规避 E316/E492/E505 SONAME 软链运行期问题
- `-lm`/`-lpthread`：OHOS SDK sysroot 自带 `libm.a`/`libpthread.a` 桩（musl 已并入 libc），无需改动

## 验证结果

```text
# conan create（第 2 轮）: EXIT_CODE=0
#   vamps/0.99.2: cd3241c31408e4d3426b5b9323fbd7d10346fd20 (package_id)
#   二进制: ELF 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1)
#   NEEDED: bin/vamps → libc.so；bin/play_cell → libc.so（libdvdread 静态链入）
#   conanmanifest.txt 全量 md5 复算: 4/4 OK，不一致数 = 0
# test_package: 5/5 PASS（HMBS_TEST_PACKAGE_RESULT passedCount=5）
# 上游测试: 无测试入口（审计日志 upstream-test-audit.log）
```

适配验证在本地 OHOS 设备（HarmonyOS PC，aarch64）真实完成，产物即备份。

### 对话 #1（2026-09-20 适配会话）

- W0 依赖分析：唯一强制第三方依赖 libdvdread（play_cell 链接 + 头文件），ohpcd 已发布 7.1.0 且 OHOS 预编译二进制可消费（download/install 双 EXIT=0）；vamps 主工具仅系统库 libm/libpthread。
- W1 配方：手写递归 Makefile 经 make 命令行注入 CC/CFLAGS/LDFLAGS 接管；conandata 源 URL 用 SourceForge 官方归档（与 Debian orig sha256 一致）。
- W2 构建：第 1 轮失败于 musl 缺失遗留 typedef `uint`（requant.c 29 处），补丁 0001 后第 2 轮 EXIT=0。
- W3 测试：上游无测试入口（审计留档）；test_package 新增 5 个鸿蒙消费者用例 5/5 PASS；conan-verify 8 闸 Verdict PASS；W3 本地 CI 通过（junk_check 以仓根 pr.diff 走 prdiff 模式，规避 full 全仓扫描对 upstream 既有 cloog/kics 状态标记的误伤）。
- 收尾：verify-build PASS → PackageBuilder 10 步产出 packaging/*.tar.gz；.ci-result.json 由 finish 写入。
---

**编译结束**: 2026-09-20 20:34
**最终状态**: built
