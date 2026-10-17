# DRAFT-jc-full-scan-baseline-noise-exemption — JC full 模式整仓扫描命中无关库预存基线垃圾

> **Contributor**: pc3-22 | **Status**: DRAFT | **Updated**: 2026-08-28
> **Severity**: high | **Category**: ohos / ci / infrastructure
> **Audience**: 所有在共享仓库执行 W3/finish 的新库

## 问题（Symptom）

`finish` 的 W3 本地 CI 模拟在 `build_and_test.sh` 的 JC（junk_check）门禁失败：

```text
Junk Files: 2
JC_RESULT=fail
L0_RESULT=fail: junk_check failed
L1_RESULT=skip: blocked_by_JC
Pass rate: 0.0% (0/1)
Failed packages: <当前库> (JC gate)
```

失败命中的文件**不属于当前库**：

- JC3：`archives/g/goaccess/1.10.2/ncurses-headers.tar.gz`（跟踪的 tarball）
- JC5：`archives/s/scudo-malloc/19.1.6/.manifest-complete`、`.progress-closed`（未登记隐藏文件）

当前库自身 `conan create` / `conan-verify` / `test_package` 全部通过，仍被整仓门禁阻塞。

## 根因（Root Cause）

`ci/scripts/junk_check.sh` 判定检查范围（第 35-44 行）：

1. 有 `pr.diff` → `prdiff` 模式（仅 PR 文件）。
2. 否则三点 diff `origin/main...HEAD` 非空 → `incremental` 模式。
3. 两者皆空（本地新库分支尚未提交）→ **`full` 模式**：`CHECK_FILES=$(git ls-files)`，即**整仓所有已跟踪文件**。

full 模式下：
- JC3 拦截 `sources/`、任意 `*.tar.(gz|xz|bz2|tgz)`（非 `prebuilt`）、`/packaging/.*\.tar`（第 132-137 行）。
- JC5 拦截 `^archives/.*/\.[^/]+$` 且不在 `JC5_ALLOWED` 白名单（第 180-182 行）。

仓库 main 的历史基线里若预存了其他库的 tarball / 未登记隐藏标记，任何新库在本分支尚未有提交时都会在 full 模式整仓扫描中命中它们，从而被 `blocked_by_JC` 误伤。属**共享基线噪声**，非当前库缺陷。

## 查重差异（为何新增）

| 既有条目 | 主题 | 差异 |
|---|---|---|
| E291 | 既有正式条目的 graph validate 问题阻塞 finish/W4（Step6 顶层退出码） | 不同根因：知识图谱校验基线 vs JC 文件垃圾基线 |
| DRAFT-jc6-origin-main-stale-ref | JC6 incremental 模式因 origin/main 过时误报 W2 原子性 | 不同门禁（JC6 增量 vs JC3/JC5 整仓）与不同根因（ref 过时 vs 基线垃圾） |
| DRAFT-E212-ci-predl-regex-pypi-url | predl_cache 正则截断 PyPI 连字符 URL | 不同主题（URL 截断）与不同门禁 |
| E088/E223/E253/E292/E297/E277、DRAFT-2045 | 构建/runtime 隔离（namespace、staging、tmpfs、symlink 等） | 「隔离」一词同义但主题完全不同：那些是构建环境隔离，本条是索引级临时隔离以规避门禁误伤 |

结论：JC full 模式整仓扫描命中无关库预存基线垃圾 + 临时索引隔离恢复的完整模式，知识库无既有条目。

## 方案（Recovery）

**baseline_noise_exemption（索引级临时隔离 + 恢复）**：

```bash
# 1. 备份（可选）并记录命中文件原始 SHA-256
sha256sum archives/g/goaccess/1.10.2/ncurses-headers.tar.gz \
         archives/s/scudo-malloc/19.1.6/.manifest-complete \
         archives/s/scudo-malloc/19.1.6/.progress-closed

# 2. 从本地索引临时移出（不改工作区文件，不碰其他库内容）
git rm --cached archives/g/goaccess/1.10.2/ncurses-headers.tar.gz \
               archives/s/scudo-malloc/19.1.6/.manifest-complete \
               archives/s/scudo-malloc/19.1.6/.progress-closed

# 3. 重跑 W3/finish——JC full 模式按 git ls-files 扫描，文件已移出索引故不再命中
#    （worker/channel 提交同一 task_id 的 finish 作业）

# 4. 验证通过后恢复索引：git add；被 .gitignore 忽略的 tarball 需 -f
git add archives/s/scudo-malloc/19.1.6/.manifest-complete \
        archives/s/scudo-malloc/19.1.6/.progress-closed
git add -f archives/g/goaccess/1.10.2/ncurses-headers.tar.gz

# 5. 校验恢复完整
git diff HEAD -- <上述文件>   # 应为空
sha256sum <上述文件>          # 应与第 1 步一致
```

关键点：
- 只动当前 git 索引（`.git/index`），**不动任何其他库的工作区文件**，不 commit。
- JC full 模式的扫描源是 `git ls-files`（索引），移出索引即从扫描范围消失。
- 验证后必须恢复使 `git diff HEAD` 为空，保证零污染与 PR 原子性（W2/JC6：PR 白名单仅当前库目录）。

## 禁止

- ❌ 删除、清理或提交无关库基线文件（goaccess/scudo-malloc 等）来让门禁通过——那些修复归库主/框架单独 PR。
- ❌ 修改 `junk_check.sh` 的 `JC5_ALLOWED` 白名单或扫描逻辑混入当前库 PR——框架改动须单独 PR。
- ❌ 通过 `git checkout` 恢复他人库文件制造"干净"假象。
- ❌ 把 JC 命中当作当前库配方/源码缺陷反复调参（R43 螺旋）。

## 验证（Evidence，libutf8proc/2.10.0 r02 + dr_flac/0.12.39 r03）

### 案例 1：libutf8proc/2.10.0 r02（pc3-22）

- 隔离前（r01）：`JC3: 1 个 tarball 被跟踪` + `JC5: 2 个 archives 下未登记的隐藏文件` → `Junk Files: 2` → `JC_RESULT=fail` → `Pass rate 0.0%`。
- 隔离后（r02）：`git rm --cached` 移出 3 文件 → 重跑 finish：
  - `JC3: PASS`、`JC5: PASS`、`Junk Files: 0`、`JC_RESULT=pass`
  - `L0/L1/L4/L5 = pass`，`Pass rate 100.0% (1/1)`
  - `test_package: PASS: utf8proc version=2.10.0 NFKC(A)=A OK`
- 恢复：3/3 SHA-256 MATCH（goaccess `bf58efee…`，两空文件 `e3b0c442…`），`git diff HEAD` 为空。
- 结论：`baseline_noise_exempted`。

### 案例 2：dr_flac/0.12.39 r03（pc1-74，同一 task_id 主任务内，2026-08-31）

命中路径（与案例 1 相同的外部追踪基线）：

| 路径 | pre/post SHA-256 | HEAD blob | restore |
|---|---|---|---|
| `archives/g/goaccess/1.10.2/ncurses-headers.tar.gz` | `bf58efee849d…`（前后一致） | `b154073f94a4…` | `git add -f`（`.gitignore:40 archives/**/*.tar.gz`） |
| `archives/s/scudo-malloc/19.1.6/.manifest-complete` | `e3b0c44298fc…`（前后一致，空文件） | `e69de29bb2d1…` | `git add` |
| `archives/s/scudo-malloc/19.1.6/.progress-closed` | `e3b0c44298fc…`（前后一致，空文件） | `e69de29bb2d1…` | `git add` |

- 隔离（`git rm --cached`，exit 0）：工作区文件原样（`ls -la` 未变），`git ls-files` 不再列出 3 路径；隔离证据日志 hash `8849bc78c183…`。
- 隔离下自然重跑完整 `finish`（Step5 W3）：`build_and_test.sh RC=0`、`JC_ERRORS=0`、`L0_RESULT=pass`、`L1_RESULT=pass: test_package executed`、`L4_RESULT=pass`、`Total 1 / Success 1 / Pass rate 100%`；日志 `finish-r03-isolated.log` hash `76ba22d461…`，W3 本地 CI 日志 `w3-local-ci.log` hash `647b779cd687…`。
- 本库门禁全绿：G1-G4 PASS（`conan-verify-report.md` hash `f969386d63…`）；强制 `conan remove 'dr_flac/*' -c` 后全量重建消费者测试 8/8 断言 exit 0（日志 `r03-conan-create-consumer.log` hash `4522397e06…`）。
- PR-diff JC 模拟（仅本库 10 交付文件）：`JC_RESULT=pass, JC_ERRORS=0`（`r03-jc-prdiff-sim2.log` hash `bef92489e7…`）。
- 恢复（`git add` + `git add -f`）：post SHA-256/HEAD blob/索引 blob 与隔离前逐项一致，`git diff HEAD -- <3 路径>` 为空，全量 `git status --porcelain` 无 goaccess/scudo 条目；恢复证据日志 hash `0232c2e18a68…`。
- 本库范围首错处置：r03 隔离 finish 的 conan-verify G2 镜像注入在归档目录残留 `conandata.yml.ghfast-bak`（与 `conandata.yml` 逐字节一致，临时副产物）→ 触发 PR-diff JC1 → 删除后复测 `JC_RESULT=pass`。
- 结论：`baseline_noise_exempted`；基线 3 路径绝未进入交付范围（dr_flac 交付白名单仅 10 文件）。

## 适用边界与维护归属

- **前置条件**：本库自身的适用门禁（G1-G4、强制清理缓存后的消费者测试、PR-diff JC）必须先独立通过，且证明外部追踪基线是 full-scan 唯一阻塞；否则豁免不成立。隔离后的运行若暴露本库失败，豁免无效并须先修复本库。
- **非永久许可**：本程序不是删除/改动/提交其他库基线文件的许可；那类修复归共享仓库维护方（清理或登记 `JC5_ALLOWED` 白名单，单独 PR）。
- **不承诺远端**：本地豁免通过不表示远端 CI 或远端交付成功。

## Source

- 证据日志（案例 2）：`.oh-executor/dr_flac-r03-logs/{pre-isolation-evidence.log(387458d54a6f…), isolation-evidence.log(8849bc78c183…), finish-r03-isolated.log(76ba22d461…), restoration-final-evidence.log(0232c2e18a68…), r03-conan-create-consumer.log(4522397e06…), r03-jc-prdiff-sim2.log(bef92489e7…)}`；`archives/d/dr_flac/0.12.39/reports/w3-local-ci.log(647b779cd687…)`
- 证据日志（案例 1）：`archives/l/libutf8proc/2.10.0/reports/w3-local-ci.log`（r01 JC 命中 2 项 / r02 JC 0 项）；worker 日志 `~/.oh-runner/compile-worker-state/logs/worker-ac03d732-…`（r01）、`worker-9025b0f6-…`（r02）
- 门禁脚本：`ci/scripts/junk_check.sh`（35-44 模式判定、126-144 JC3、173-190 JC5、`JC5_ALLOWED` 第 180 行）
- 事件：libutf8proc/2.10.0 r01→r02（pc3-22）；dr_flac/0.12.39 r02→r03（pc1-74）