# roll 2.7.0 适配笔记

## 编译环境
- 构建系统: autotools（`configure` + make；`roll.c` + `parser.y` + `scanner.l` 三翻译单元，dist 归档自带生成的 `configure`/`parser.c`/`scanner.c`，无需 flex/bison）
- 编译日期: 2026-09-20
- 编译器: clang 15.0.4（OHOS SDK / Harmonybrew；目标 `aarch64-unknown-linux-ohos`；配方经 Conan toolchain 注入，无裸 `${CC}`）
- 状态: built（conan-verify G0–G4 PASS；本地 CI L0/L1/L1e/L2/L4/L5 PASS；上游 `make check` 15/15；test_package 21/21）

## 编译步骤
```bash
# 探索编译（模式 B）
cd $BUILD_SRC_DIR
./configure --prefix=$DEFAULT_PREFIX
make -j1
make install DESTDIR=$TEST_PREFIX
make check                       # 3 个 TAP 脚本 / 15 条断言

# Conan 配方验证（设备 profile）
python3 scripts/ohc-run.py conan-verify roll 2.7.0 --profile ohos-aarch64-device
#   → G1/G0/G2/G3/G4 全 PASS；G2 内真实执行：
#     build(): 打补丁 → configure → make -j1 → make check（15/15，"All 3 tests passed" 强校验）
#     test_package: sh test_roll.sh → 21/21（真实执行已安装二进制）

# 本地 CI 门禁（与平台同脚本）
export CONAN_PROFILE=ohos-aarch64-device
export CI_PACKAGES="archives/r/roll/2.7.0" CI_REPO_ROOT="$PWD"
zsh ci/conan/build_and_test.sh "$CI_PACKAGES"
#   → L0/L1/L1e/L2/L4/L5 全 PASS；L1e 破坏性负例确认消费者测试真实依赖 bin/roll
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure` 收尾自动执行的 `config.status` 失败：`./confXXXXXX/subs1.awk: Permission denied`，config.status 随即打印 “could not setup config files machinery” 并失败（configure 自身 rc=1） | dist 归档的 configure/config.status 用 `umask 077 && mktemp -d "./confXXXXXX"`（回退 `umask 077 && mkdir`）创建临时目录；HMDFS 强制 setgid 并重映射属主 UID，产生的 `drwx--S---` 目录连属主也不可写 | 补丁 `0001-configure.patch`：去掉该处两行的 `umask 077`（单处、无平台宏；E011/E114 标准解法，本仓库 948 个 autotools 归档同型）。补丁后 configure/make/make check 全绿；同类先例见 `archives/a/a52dec/0.7.4`（umask 022 变体） |
| 2 | 设备直连 GitHub release 资产超时（`github.com/.../releases/download/...` 重定向到 objects.githubusercontent.com 不可达；api.github.com 与 codeload 正常） | 国内网络对 release 资产 CDN 的可达性不稳定 | 本地下载经镜像完成，但**字节以官方 digest 为准**：GitHub release API 公布 `roll-2.7.0.tar.gz` 的 sha256 = `9e116501…3533`，镜像下载产物实测同值（170222 字节），conandata.yml 只写官方 URL；CI/门禁侧由工具自动注入镜像通道（E017），交付形态不含镜像 URL |
| 3 | `make -j2` 报 `jobserver mkfifo: …/GMfifo…: Operation not permitted`（随后回退串行继续执行） | HMDFS 不允许创建 FIFO（toybox 亦无 mkfifo 命令），GNU make 4.4 的 jobserver 管道不可用（E074/E525） | 配方固定 `autotools.make(args=["-j1"])`：与本仓库主流程约定一致，同时匹配上游 `AUTOMAKE_OPTIONS = serial-tests`，保证测试日志确定可复现 |
| 4 | `refresh-patch --auto` 把 `roll.1` 误判为源码修改，生成伪补丁 `0002-roll.1.patch`（diff 仅一行：`@PACKAGE_DATE@` 被替换为构建当日日期） | 探索阶段在 .work 里跑了 configure/make，`config.status` 会按 `AC_SUBST(PACKAGE_DATE, date)` 重新生成 man 页 `roll.1`——该文件在基线中存在，于是被补丁工具当成人工编辑；这是"构建产物回写源码树"被误收进补丁的陷阱（E429 草稿家族/E254/E484 的相邻情形） | 从 `.orig` 恢复 `roll.1` 后重跑 refresh-patch，只保留 `0001-configure.patch`；旧伪补丁删除。判别法：补丁 hunk 与构建期生成行为（日期/路径/版本替换）相关时先对照 `.orig` 确认是"源码修改"还是"构建回写" |
| 5 | 本地 CI 门禁执行后 `conandata.yml` 残留 `gh-proxy.com` 镜像多 URL 形态（脚本曾打印"已还原为官方 URL"，但 git status 仍显示 modified） | 门禁预下载阶段对 conandata.yml 做原地镜像改写，其还原路径在本机环境下未完全生效（E415：CI 后必须逐字节核验还原） | `git checkout -- archives/r/roll/2.7.0/conandata.yml` 恢复到 HEAD 形态（单官方 URL），`git status` 归零；提交前再次核验 `grep ghfast/gh-proxy` 为空 |

## 源码修改

- `patches/0001-configure.patch`（唯一补丁，2 行）：`configure` 的临时目录创建块
  `tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`` → `tmp=`mktemp -d "./confXXXXXX" 2>/dev/null``；
  `(umask 077 && mkdir "$tmp")` → `mkdir "$tmp" 2>/dev/null`（回退分支同时以 `2>/dev/null` 与 mktemp 分支保持一致的静默；两处改动均不含平台宏）。patch_type: portability（仅因 HMDFS 平台特性而存在），无平台宏/无 `__OHOS__` 守卫。
- 上游 C 源（roll.c/parser.y/scanner.l）与测试用例零修改。

## 依赖版本

无（W0 实测：零第三方依赖，仅系统 libc/libm；`conan download`/`conan install` 无需任何 requires）。

## 验证结果

```bash
# 1) 上游测试（make check，设备实测，日志 logs/check2.log 与 conan-create.log）
Testing '1d6' = 3 / '1d10' = 3 / '1d%' = 33 / '1DF' = 1 / 'd10X' = 9 / '42d0' = 0
Testing '1d6 + 1' = 4 / '1d10-1' = 2 / '1d%*2' = 66 / '2D6/2' = 3 / '1d6x10' = 30
Testing '4d6h3' = 9 / '4d6l3' = 9 / '4d6LX' = 9 / '4d6HX' = 9
→ PASS: tests/dices.test / tests/operations.test / tests/special.test
→ "All 3 tests passed"（3/3 脚本，15/15 断言，0 修改）
# 2) conan-verify（设备 profile），G1/G0/G2/G3/G4 全 PASS
#    G2 内配方自检：roll upstream suite: PASS (make check, 3 scripts / 15 assertions)
#    test_package：roll test_package: 21 passed, 0 failed
# 3) 本地 CI 门禁：L0_RESULT=pass / L1=pass / L1e=pass（破坏性负例）/ L2=pass / L4=pass / L5=pass
# 4) 已安装二进制抽查：
$P/bin/roll --version            # → roll 2.7.0
$P/bin/roll --test '4d6h3'       # → 9
```

## 交付物

| 路径 | 说明 |
|------|------|
| `bin/roll` | 骰子表达式求值器（arm64 ELF） |
| `share/man/man1/roll.1` | 上游 man 手册（configure 生成） |
| `share/bash-completion/completions/roll` | 上游 bash 补全脚本 |
| `licenses/COPYING` | GPL-2.0 全文 |

## 注意事项

- 产物为可执行命令，已在软件级 `archives/r/roll/commands.json` 声明（R38）。
- `--test` 语义：每颗骰子恒为 3（上游为测试提供的确定性开关），消费者测试的全部数值断言依赖该语义；随机路径仅用 1..6 区间断言验证。
- 退出码语义：正常 0；错误（溢出/除零/不可能的筛选/缺表达式/未知符号）统一 `exit(EXIT_FAILURE)`=1；`-p` 只改变系列求和的截断（表达式值仍原样打印）。
- `manifest.yaml` 的 `patch_generation.source_orig_dir/source_work_dir` 是 refresh-patch 写入的设备侧构建目录（工具遥测，非配方配置）；构建真正读取的是 conandata.yml 的官方 HTTPS URL 与 `patches/` 相对路径。
- 首次执行新二进制时设备可能弹安全确认框（R7）；本任务验证均在解锁状态下完成。

## 对话记录

### 对话 #1 — 2026-09-20 任务下达与范围确认
- 用户指示：适配 roll 2.7.0（任务 #10227 / 分支 `feat/roll-2.7.0`）；完成适配后、提交 PR 前停下，先给出路径 B 可行性分析，由用户决定按 A 提交还是补齐后按 B 提交。
- 执行结论：本轮完成 W0–W4 全部门禁材料（探索编译、配方、conan-verify、本地 CI、finish、独立审计），**不创建 PR**；B 可行性分析单独成文上报。

### 对话 #2 — 2026-09-20 环境与协同记录
- 共享设备上其他参与者正在 `conan create`，按共享设备纪律串行等待，未与其他任务并发使用 Conan 缓存；未触碰他人 worktree/分支/设备进程。
- 源与补丁决策：上游源码固定为官方 release 资产（sha256 与 GitHub release API digest 逐字一致）；补丁只保留 configure 临时目录的 HMDFS 修正；构建产物回写（roll.1 的日期替换）不进入补丁。
- 验证决策：上游 `make check` 15/15 与消费者 21/21 均真实执行，未跳过、未修改用例。

---

**编译结束**: 2026-09-20 22:59
**最终状态**: built
