# syrep 0.9 测试报告

## 测试环境
- 平台: HarmonyOS PC (aarch64, OHOS 6.0), OHOS NDK clang 15
- 运行方式: `conan create`（W3 本地 CI 模拟，profile 与 CI 流水线同款 `ci/conan/profiles/ohos-aarch64`）
- 依赖: berkeley-db/4.8.30（静态链入）, zlib/1.3.1
- 本次结论: conan create 全流程 **PASS**（677 行完整日志，`ERROR`/`Error in` 计数为 0，无 `Permission denied`）

## 上游测试清点与执行（R51 三步法）

**第一步 清点（证据）**
- `src/Makefile.am:23`：`noinst_PROGRAMS = rm-rf-test copy-fd-test`
  → `make` 会编译这两个程序，但它们**未注册进 TESTS**，`make check` 不会执行
- `Makefile.am` 无 `TESTS` 变量，`make check` 为空操作
- 上游仓库无 `tests/` 目录，Debian 打包亦未附带独立测试套件

**第二步 执行（本适配把两者接入自动化）**

| 程序 | 调用方式 | 结果 |
|------|---------|------|
| `copy-fd-test` | `copy-fd-test <src> <dst>`，断言拷贝结果字节与 sha256 一致 | ✅ PASS（65792 bytes, sha256 match） |
| `rm-rf-test` | `rm-rf-test <dir>`，断言嵌套目录树被完整删除 | ✅ PASS（nested tree removed） |

调用点位于 `conanfile.py` 的 `build()`（make 之后、install 之前），日志形如
`syrep/0.9: [upstream test 1/2] copy-fd-test PASS ...`，CI 日志可直接核验。
**上游测试源码未做任何修改**。

**第三步 申报**：见 `test_package/MANIFEST.yml`（`upstream_tests` / `observed` 字段）。

## test_package 消费者测试

**文件**: `test_package/test_syrep.cpp`（7 处断言）

| # | 断言 | 结果 |
|---|------|------|
| 1 | syrep --version 可执行并自报版本/链接库 | ✅ |
| 2 | --update 在仓库 A 创建 .syrep/current.syrep 快照 | ✅ |
| 3 | 快照文件存在 | ✅ |
| 4 | 仓库 B update 后 makepatch A→B 生成补丁 | ✅ |
| 5 | patch merge 入 B 成功 | ✅ |
| 6 | B/f1.txt 内容 == A/f1.txt（"hello"） | ✅ |
| 7 | B/f2.txt 内容 == A/f2.txt（"world"） | ✅ |

## 测试结果

| 项 | 结果 |
|----|------|
| 上游测试（接入执行） | **2/2 PASS** |
| test_package 消费者测试 | **7/7 PASS** |
| conan create 全流程（configure → make → package → test_package） | **PASS** |

## 关键验证日志

```
syrep/0.9: [upstream test 1/2] copy-fd-test PASS (65792 bytes, sha256 match)
syrep/0.9: [upstream test 2/2] rm-rf-test PASS (nested tree removed)
---
syrep 0.9
Compiled with 64 Bit off_t.
Compiled with zlib 1.3.1, linked to zlib 1.3.1.
Compiled with libdb 4.8.30, linked to libdb 4.8.30
SVN Revision 115
Compiled with extended attribute support: no
Using sendfile(): yes
syrep 0.9 test passed: update/makepatch/merge round-trip OK
```

二进制自报"Compiled with … linked to …"版本一致，证明打包出的可执行文件确实静态链入了
本配方构建的 berkeley-db/zlib（R26 系统同名库静态隔离生效）。

## 已修复的历史失败（本轮 W3 定位）

| 现象 | 根因 | 修法 |
|------|------|------|
| CI：`./config.status: line 620: ./confLKEcNb/subs1.awk: Permission denied` → `could not setup config files machinery` → `Error in build() method, line 70` | HMDFS + `umask 077` 的 `mktemp -d` 目录恒为 0700，umask 对 HMDFS 目录无效（E110/E112/E129/E011 族）；本地曾因 PATH 中存在旧任务安装的全局 mktemp 垫片而掩盖，CI PATH 无垫片 | 配方内化 mktemp 垫片（`umask 002` + `chmod 2770`）并在 `build()` 中以 `PATH` 前缀注入 configure/make/install 全链 |
| W3（本机）：`Perl_my_cxt_init: symbol not found` | 系统 autoconf 与 conan perl 混搭（E041/E071 口径：CI 不应依赖 autotools 重生成） | 放弃重生成方案，改为直接修补上游 2005 版 configure（补丁 0002，4 行），并用 `os.utime` + `/bin/true` 防止 make 重跑 autotools（E248） |
| W3（本机）：`configure: error: newly created file is older than distributed files!` | E248 防触发所用的 `os.utime` 时间戳取了 `time.time() + 10`（未来时间），触发 autoconf 时钟自检 | 时间戳改为 `time.time()`：≥ 依赖文件（configure.ac）且不超前于当前时刻 |

## 已知限制
- merge 遇同名文件时为交互式询问（上游行为）；test_package 用空目录规避
- 交叉编译下 `make check` 为空操作（上游未接线 TESTS），测试覆盖由"build() 内联执行上游 2 程序 + test_package"承担
