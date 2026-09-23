# lz4 1.10.0.3 — 编译进度

> 档案创建时间: 2026-09-10
> 分支: upgrade/lz4-1.10.0.3（worktree: D:\harmonyos\worktrees\lz4）
> 当前状态: 前置适配完成，本机静态验证通过，OHOS CI / 真机待执行

## 一、基本信息
| 项目 | 值 |
|------|-----|
| 软件 | lz4 |
| 版本 | 1.10.0.3（R37：上游 v1.10.0 + 适配修复后缀，源码不变） |
| 上游最新 | v1.10.0（2024-07-21，无更新 release；上游无 v1.10.0.3 tag） |
| 构建系统 | makefile（纯 Makefile，无 configure） |
| 依赖 | 无（零外部依赖，W0 通过） |
| CLI 工具 | 是（R38 → 软件级 commands.json 已登记） |

## 二、版本号说明（R37）

上游 lz4 官方只有 v1.9.4 / v1.10.0 两个近期版本（GitHub tags 与 releases 已核实，
ConanCenter 也只有 1.10.0/1.9.4/1.9.3）。本配方遵循仓库 R37 规则：
上游版本 `X.Y.Z` + 适配修复后缀 `.N`，源码 tarball 仍为 v1.10.0
（sha256 与 1.10.0 完全一致）。同类先例：highway 1.3.0 → 1.3.0.1 → 1.3.0.2。

**版本序号变更记录（2026-09-14）**：本 PR 最初以 1.10.0.1 提交并于 2026-09-10
CI 全绿（#43646）；同日晚间 main 并行合入了另一份 1.10.0.1（f976cad532，
goblinrs）与 1.10.0.2（b47859dd08，xioaxin，仅静态构建 `BUILD_SHARED=no`），
1.10.0.1 槽位被占。按 R37 取下一序号 **1.10.0.3**，不覆盖任何已合入内容；
分支名保留 upgrade/lz4-1.10.0.1（PR #9359 关联不变）。

本次适配修复（相对 main 现有 1.10.0 / 1.10.0.1 / 1.10.0.2 配方）：

1. **修复 shared 构建**：v1.10.0 顶层 Makefile 没有 `lib-shared` 目标（已核实
   源码：`default: lib-release lz4-release`），1.10.0 配方 `make lib-shared`
   在 `shared=True` 时必然失败，仅因 CI 默认静态构建未暴露。修复为
   `make -C lib lib`（lib/Makefile 的 `lib: liblz4.a liblz4`，同时产出静态与
   带版本号的共享库）。
2. **吸收 1.9.4 的 OHOS 环境加固**（1.9.4 于 2026-09-08 合入，为当前 CI 环境
   验证过的写法）：E132 lld 依赖 libxml2.so.16 的 LD_LIBRARY_PATH 兜底注入
   （isdir 保护，路径漂移时跳过）、`SHELL=/data/service/hnp/bin/bash`（OHOS
   /bin/sh 受限）、显式 `CC=clang CXX=clang++`、`LN_SF=cp`（hmdfs 拒绝
   symlink）。
3. **修正 test_package/MANIFEST.yml**：1.10.0/1.9.4 引用的 `tests/check_mex.c`
   在 v1.10.0 源码中不存在（上游后续版本才引入的文件），改为引用真实存在的
   `tests/frametest.c`、`tests/fuzzer.c`、`tests/test-lz4-basic.sh`。
4. 补丁 `0001-Makefile.inc.patch` 自 1.10.0 **字节级原样复用**（cmp 校验一致）。

## 三、编译阶段（checkbox 实时更新）

### Phase 1: 环境准备
- [x] W0 依赖检查：lz4 零依赖，无阻塞
- [x] 源码下载 + sha256 校验（本机，gh-proxy 镜像）
- [x] 构建系统识别：纯 Makefile
- [x] 补丁 dry-run 验证（patch -p1 --dry-run 通过，GNU patch 自动剥离 CRLF）

### Phase 2: 编译
- [x] conanfile.py / conandata.yml / test_package 编写完成
- [x] OHOS conan create（真机 2026-09-10：static + shared 双通过）

### Phase 3: 测试验证
- [x] test_package 真机执行（static/shared 各 1 次，round-trip PASS）
- [x] 上游测试复跑（test-lz4-basic / test-frametest / test-fuzzer 全 PASS）
- [x] shared=True 构建路径验证（本版修复点，真机实证）
- [ ] CI L0/L1（PR 后）

### Phase 4: 归档收尾
- [ ] PR 提交（issue 待补）
- [ ] CI 绿后更新本文件

## 四、本机已完成的验证（2026-09-10）

| 项 | 结果 |
|---|---|
| 上游版本核实 | GitHub tags/releases + ConanCenter config.yml：无 v1.10.0.3，确认 R37 后缀语义 |
| tarball sha256 | `537512904744b35e232912055ccf8ec66d768639ff3abe5788d90d792ec5f48b` 与 conandata.yml 一致 |
| 补丁可应用性 | `patch -p1 --dry-run` 在干净 v1.10.0 源码上通过（CRLF 补丁由 GNU patch 剥离 CR） |
| shared 目标核实 | lib/Makefile `lib: liblz4.a liblz4`，顶层无 lib-shared（1.10.0 配方 bug 确认） |
| 头文件清单 | lib/{lz4,lz4hc,lz4frame,lz4frame_static,lz4file}.h 均存在 |
| 配方语法 | conan 2.31.2 本机 `conan inspect` / py_compile 通过 |
| 本机构建 | 不可行（本机无 make/clang/MSVC），OHOS 构建交由 CI/真机 |

## 四B、真机验证（2026-09-10，frp 隧道，与 swift 任务错峰）

环境：HarmonyOS aarch64（kernel 1.12.0，24GB），clang@`/storage/Users/currentUser/usr/local/bin`，
conan 隔离 `CONAN_HOME=$HOME/tmp/lz4-ohos/conan-home`（profile 编译器路径已按设备实际修正），
TMPDIR 指向 `$HOME/tmp`，jobs=1，MemAvailable 全程 ≥8.8GB。

| 项 | 命令 | 结果 |
|---|---|---|
| conan create（static） | `-pr:h/-pr:b=ohos-aarch64 --build=missing` | ✅ PASS，test_package `LZ4 compress=52 decompress=50 round-trip OK` |
| conan create（shared） | 同上 + `-o lz4/*:shared=True` | ✅ PASS（本版修复点 `make -C lib lib` 实证） |
| 产物 | liblz4.a 183KB；liblz4.so/.so.1/.so.1.10.0 各 182KB（LN_SF=cp 副本，hmdfs 预期）；bin/lz4 | ✅ |
| CLI 冒烟 | `lz4 --version` | ✅ `v1.10.0 64-bit multithread` |
| 上游测试 | `make -C tests {test-lz4-basic,test-frametest,test-fuzzer} POSIX_ENV=Yes CC=clang` | ✅ 3/3 PASS（fuzzer 5122/5122 all completed） |
| 路径 B 消费者用例 | test_lz4_consumer.c（LZ4F frame API 往返 + LZ4_loadDictSlow 字典压缩往返）+ conanfile test() 内 CLI 文件往返（bin/lz4） | ✅ static/shared 各 3/3 PASS（2026-09-10 复验，含 18 断言） |

真机排障记录（配方/环境各一坑，均已修复）：
1. **配方坑**：SHELL 硬编码 `/data/service/hnp/bin/bash` 仅 CI worker 存在，真机报
   `make: ...: No such file or directory`（Error 127）→ 改为 os.path.exists 自适应，
   真机回退默认 /bin/sh（1.10.0 同源实证可用）。
2. **环境坑（非配方）**：设备 profile 的 `compiler_executables` 仍指 CI 路径
   `/data/service/hnp/bin/clang`（设备 clang 已在 usr/local/bin，2026-09 布局变更），
   导致 test_package cmake.configure 找不到编译器 → 隔离 profile 副本 sed 修正，
   **共享 ~/.conan2 未动**。
3. 上游 tests/Makefile 用裸 `cc`（设备无 cc）→ 测试命令显式 `CC=clang`。

## 五、下一步命令（真机 / shadow CI）

```sh
# shadow CI 单包定向验证（在 worktree 提交后）
CI_PACKAGES="archives/l/lz4/1.10.0.3" zsh ci/conan/build_and_test.sh

# 真机（通过 frp-tip.com SSH，conan 在 $HOME/.local/bin/conan）
conan create archives/l/lz4/1.10.0.3 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
# shared 修复点回归：
conan create archives/l/lz4/1.10.0.3 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 -o shared=True --build=missing

# 上游测试（POSIX_ENV=Yes 必带，否则幻影通过；先清 usan 残留 .o）
cd <源码目录> && rm -f lib/*.o tests/*.o && make -C tests test-frametest test-fuzzer test-lz4-basic POSIX_ENV=Yes
```

## 六、对话记录

### 对话 #1 — 2026-09-10
**操作**: 前置适配（W0 + 源码分析 + 配方 + test_package + 本机静态验证）
**结果**: 完成；发现并修复 1.10.0 配方 shared 构建 bug 与 MANIFEST 幽灵测试引用
**当前状态**: 待 CI / 真机验证
**遗留问题**: issue 未创建；真机空闲窗口未分配

### 对话 #2 — 2026-09-10
**操作**: 真机构建（frp 隧道，隔离 CONAN_HOME，与设备上 swift 任务错峰）
**结果**: ✅ static + shared conan create 双 PASS，test_package ×2 PASS，CLI 冒烟 OK，
上游测试 basic/frametest/fuzzer 3/3 PASS；修复 SHELL 硬编码适配坑（改自适应）
**当前状态**: 真机验证完成，待建 issue + PR + CI
**遗留问题**: issue/PR 未创建；设备 profile 的 CI 编译器路径失效问题属环境项
（已在隔离副本修正，共享 ~/.conan2 未动，建议反馈维护者）
