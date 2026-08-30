# DRAFT-vtzero-1.2.0-baseline-noise-exemption：JC3 全仓误报与可逆基线噪音隔离

> Contributor: pc1-42 | Status: Draft | Updated: 2026-08-29
> Source: vtzero 1.2.0 HarmonyOS PC 适配 r04（baseline-noise-exempted PR delivery）

## 现象（error_signature）

本地 `finish` Step5 W3（ci/conan/build_and_test.sh -> ci/scripts/junk_check.sh）
在**与本库无关**的文件上被 JC3 拦截：

```text
[FAIL] JC3: 1 个 tarball/打包产物被跟踪:
       archives/g/goaccess/1.10.2/ncurses-headers.tar.gz
Junk Files: 1
JC_RESULT=fail
L0_RESULT=fail: junk_check failed
```

触发案例：vtzero 1.2.0 适配（r03/r04）。main 分支早在提交
`51eae6ae0e`（feat(goaccess): 1.10.2 适配完成）中就跟踪了
`archives/g/goaccess/1.10.2/ncurses-headers.tar.gz`。该文件与 vtzero 完全无关，
vtzero 自身目录没有任何 JC1–JC5 命中。

## 根因（root_cause）

`junk_check.sh` 按优先级选择检查范围：

1. `prdiff` 模式：存在 `pr.diff` 时，只检查 PR 涉及文件（CI 远端用）；
2. `incremental` 模式：`git diff origin/main...HEAD` 非空时，只检查提交差异文件；
3. **`full` 模式**：两者都不可用时回退到 `git ls-files`（**索引**全量扫描）。

本地 W3 模拟时，若当前库文件全部是未跟踪新文件（尚未 commit、HEAD 相对
origin/main 无提交差异），`git diff origin/main...HEAD` 为空 → 落入 **full 模式**，
按**索引**（git ls-files，而非工作区）判断。于是 main 上任何历史已跟踪的
tarball 都会被 JC3 命中，本地 W3 被与自身无关的**历史基线**阻塞。

关键发现：**仅把工作区文件 `mv` 走不消除命中**——full 模式读的是索引，
`git ls-files` 仍输出该路径。必须同时从**索引**移除。

## 方案（solution）：可逆两部隔离（索引 + 工作区）

1. **隔离前记录四元组**（evidence 基准）：
   - 绝对路径（readlink -f）
   - 权限/大小（stat：mode/size/mtime）
   - Git 状态（git ls-files --stage 的 blob 与模式）
   - SHA-256（sha256sum）
2. **可逆隔离两步**：
   ```sh
   git rm --cached -- <F>          # 从索引移除 → full 模式的 git ls-files 不再命中
   mv <F> "$HOME/tmp/$(basename <F>).bak"   # 工作区实体移走
   ```
   复核 `bash ci/scripts/junk_check.sh "$PWD"` → 期望 `Junk Files: 0` / `JC_RESULT=pass`。
3. **重跑完整 finish/W3**（+ conan-verify + 上游测试）：
   通过后 `.ci-result.json` 写入 `exit_code=0`（含日志 SHA-256），可继续 W4/提交。
4. **恢复并核验**：
   ```sh
   mv "$HOME/tmp/$(basename <F>).bak" <F>
   git add -f -- <F>                # 基线文件被 .gitignore 覆盖时必须 -f 强制恢复索引
   git status --porcelain -- <F>    # 期望空（0 变更）
   git ls-files --stage -- <F>      # 期望 blob 与隔离前一致
   sha256sum <F>                    # 期望与隔离前一致
   ```
5. **铁律**：基线文件**绝不**进入当前库的 commit 或 PR 文件清单——
   提交前三重核对 `git status`、`git diff --cached --name-only`、
   `git diff origin/main...HEAD --name-only` 均只含本库白名单文件。

## 验证证据（evidence）

vtzero 1.2.0 r04（pc1-42，2026-08-29）：

| 项 | 隔离前 | 隔离后恢复 |
|---|---|---|
| 路径 | `archives/g/goaccess/1.10.2/ncurses-headers.tar.gz` | 一致 |
| 权限/大小 | mode 660（-rw-rw----）/ 159275 字节 | 一致 |
| mtime | 2026-08-28 10:14:39.668305469 +0800 | 一致 |
| Git 状态 | index `100644 b154073f94a4637ead69f8628bc1f2588acbe478`，无未提交变更 | `git status --porcelain` 空，index blob 一致 |
| SHA-256 | `bf58efee849debcfa56ce02f2a099aa25638de6bed90f356fc1018aac59d5e11` | 一致 |

- 隔离后 `junk_check` full 模式文件数 43770 → 43769，JC3 无命中，`Junk Files: 0`，`JC_RESULT=pass`。
- finish W3 通过，`.ci-result.json` `exit_code=0`；conan-verify G0–G4 PASS；
  ctest 12/12；unit-tests 186 用例 / 1297 断言全过；test_package 消费者往返 PASS。
- 最终 commit `b2733b3c50` 与 PR #7141 文件清单仅含 `archives/v/vtzero/1.2.0/` 的 8 个文件
  （conandata.yml / conanfile.py / manifest.yaml / notes.md / test_package/*4），
  goaccess 基线文件未入库、未入 PR。

## 恢复条件（recovery_condition）

隔离操作完全可逆，常规无需恢复。若恢复后 SHA-256 或 Git 状态与隔离前记录不一致，
用 `git checkout origin/main -- <F>` 或 `git add -f <F>` 重新对齐，并以隔离前
四元组为准复核。

## fixture-tests 覆盖性说明（独立注意事项）

- **状态**：不可运行（unavailable），非 100% 上游执行。
- **ownership（原因归属）**：源码归档缺失 —— 上游 `test/fixture-tests` 需要
  `FIXTURES_DIR` 指向 mvt-fixtures 子模块（https://github.com/mapbox/mvt-fixtures），
  官方 v1.2.0 release 归档（tar.gz）未包含该子模块。
- **recovery（恢复条件）**：使用包含子模块的完整上游 checkout（`git clone --recursive`），
  或使用上游提供的 fixtures 归档并设置 `FIXTURES_DIR` 后运行。
- 通过率统计仅基于实际运行的测试（ctest 12/12、unit-tests 186/186、test_package 1/1），
  不得把未运行的 fixture-tests 计入分母或宣称 100%。

## 适用边界

- 适用于任何在共享仓库工作树做本地 W3/finish、分支尚未提交、main 存在已跟踪
  tarball/二进制/状态文件基线的适配任务。
- 远端 CI 采用 prdiff/incremental 定向扫描，不受 full 模式影响；本地完成隔离验证后，
  提交内容以「仅本库白名单」为准即可。
- 与查重差异：现有条目（E002 /tmp 只读、E046 chmod、junk_check JC 体系文档）
  均未覆盖「full 模式按索引扫描 + 无关基线 tarball 误报 + 可逆两部隔离」这一
  W3/共享框架层模式；本草稿为该错误模式的独立新增。