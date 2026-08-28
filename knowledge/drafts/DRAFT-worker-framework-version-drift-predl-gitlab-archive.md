# DRAFT-worker-framework-version-drift-predl-gitlab-archive

> Contributor: pc3-24 | Status: DRAFT | Updated: 2026-08-28
> Severity: high | Category: ohos / ci / infrastructure
> Audience: 所有用 GitLab /-/archive/ 官方归档 URL 作为 sources.url 并经 ohpc_compile_worker 跑 W3/finish 的新库执行端

## Scope
共享 ci/conan/build_and_test.sh 的 predl 预下载会把 conandata.yml 的 sources.url 改写为 file:// 本地缓存路径。当该 URL 是 GitLab 官方 /-/archive/ 归档时，环境内 curl 收到的是约 54KB HTML 页面而非 tarball，脚本误判"成功"并改写为断链 file:// 路径，导致 conan create 的 source() FileNotFoundError。更隐蔽的是 worker-framework-version-drift：仅修改 worktree 内 build_and_test.sh 未必生效，worker 实际加载的是其自身/旧框架副本。

## 背景
- W3/finish 由主机 ohpc_compile_worker 执行 worktree/scripts/ohc-run.py finish（cwd=worktree）。
- W3 本地 CI（scripts/ohc/workflow_checks.py run_local_ci）调用 project/ci/conan/build_and_test.sh（project 为 find_project_dir() 解析出的 worktree）。
- build_and_test.sh 内嵌 predl python 块：提取 URL → curl 下载到 .build-cache/predl_cache/ → 把 conandata.yml 的 URL 替换为 file:// 本地路径。
- 对 GitLab 官方 /-/archive/ 归档，predl 的 curl 在目标环境拿到的是 54KB HTML（UTF-8 text，<!DOCTYPE html>），因 size>100 被判定"成功"，并把 conandata.yml 改写为 file:// 断链路径。
- 随后 conan create 的 source() get() 对该 file:// 路径 FileNotFoundError。
- 关键陷阱：find_project_dir() 实测从 worktree 解析返回 worktree 自身；但 worker 实际运行的是独立/旧框架副本，因此仅改 worktree 内 build_and_test.sh 的 predl 逻辑不一定被 worker 加载（worker-framework-version-drift）。修复必须先在 worker 实际加载的框架副本上落地，或对该 GitLab /-/archive/ URL 做目标级 predl 跳过，使 Conan 保持从官方 URL 下载。

## 模式（步骤）
1. 确认 worker 实际框架副本：ps -ef | grep ohpc_compile_worker 记录 cmdline；worker 源码 _finish_command → runner_path=worktree/scripts/ohc-run.py, cwd=worktree；python3 调 find_project_dir() 确认解析；sha256sum ci/conan/build_and_test.sh 记录当前 SHA。
2. 目标级 predl 兼容/跳过：在 predl python 块中，对 https://gitlab.com/libeigen/eigen/-/archive/ 前缀 URL 从 urls 过滤（urls=[u for u in urls if not u.startswith(EIGEN_ARCHIVE_URL)]），使该 URL 不进入 predl 下载/改写，Conan source() 直接走官方 URL；不写 file://。
3. 隔离三处基线文件（JC full 模式按 git ls-files 索引扫描）：cp -p 备份到 worktree 外 && rm -f && git rm --cached。
4. 重跑 W3/finish（worker）至自然终态，收集日志与 SHA-256。
5. 恢复：cp -p 备份回原路径 && git reset HEAD -- <3 处>（git reset 不受 .gitignore 限制）；还原/隔离共享框架改动，使 eigen3 原子范围不变。
6. 若 worktree 改动仍不生效 → 判定 worker-framework-version-drift，记录证据，修复须在 worker 实际副本落地，不得在 worktree 内猜路径或改共享框架掩盖。

## 禁止
- 不把 worktree 内 build_and_test.sh 的改动当成已生效而跳过验证。
- 不把 source() file:// 断链报错归咎为 eigen3 配方问题（根因是 predl 改写）。
- 不把共享框架改动混入 eigen3 diff/staged/commit/PR。

## 验证
- sha256sum ci/conan/build_and_test.sh（修复前后均记录）。
- W3 日志与 worker 日志 SHA-256。
- 三处基线文件隔离前/后/恢复后 SHA-256 一致；git ls-files 恢复为 3。
- 若跳过生效：W3 日志 predl 段不再出现 Pre-downloaded 1 files...file://，source() 用官方 URL 成功。

## Source（真实证据, eigen3 3.4.0 r07+r08）
- r07 证据：
  - worker cmdline: python3 /storage/Users/currentUser/.oh-runner/compile-worker/ohpc_compile_worker.py --state-dir .../compile-worker-state --worktree-root /storage/Users/currentUser/junshi_liu/worktrees --host 127.0.0.1 --port 18082
  - 官方 URL: https://gitlab.com/libeigen/eigen/-/archive/3.4.0/eigen-3.4.0.tar.gz；期望 SHA-256 8586084f71f9bde545ee7fa6d00288b264a2b7ac3607b974e54d13e7162c1c72（HTTP 200, gzip, 2.7MB）
  - predl 实测下载: source_bb23f95d (54KB) HTML；conandata.yml updated to file:// URLs；FileNotFoundError: ...predl_cache/bb23f95d_source_bb23f95d-/archive/3.4.0/eigen-3.4.0.tar.gz
  - build_and_test.sh 修复前 SHA 7c562ee8c781272c5b6c90981d66b05371da33173dbb84e407ccd6225e78df2f
  - r07 W3 日志 sha256 e528f99346d6e916d73adb4b0536d543a63a293674d77cdfb7f4aafcc699adab；r07 worker 日志 sha256 91805562d0069891a402558cd7eb2645228563f08dba52a95de0986c1feef8ff
- r08 运行时取证证据：
  - worker W3 实际执行: ps 捕获 zsh /storage/Users/currentUser/junshi_liu/worktrees/pc3-24-eigen3-3.4.0/ci/conan/build_and_test.sh archives/e/eigen3/3.4.0（PID 17661，cmdline 为绝对路径，即 worktree 内文件）
  - worktree/ci/conan/build_and_test.sh inode 2305843009214797716, size 80031, SHA-256 7c562ee8c781272c5b6c90981d66b05371da33173dbb84e407ccd6225e78df2f（HEAD 版）
  - 部署 Eigen-only predl 跳过后 SHA 499f53f034e1f23091c3fe02f044b8bcefd0afceca46f0cfc817a8319f520618；W3 重跑结果不变（仍 Pre-downloaded 1 files + file:// 断链）→ 被执行的 predl python 块与所编辑 heredoc 不同源
  - r09 调用链逐层取证证据：
  - build_and_test.sh 内部调用链：`SCRIPT_DIR=ci/conan`；line32 `source "$SCRIPT_DIR/sqlite_runtime.sh"`；func `validate_build_timeout_config`/`build_timeout_for`（awk，line46/67）；镜像改写 heredoc `python3 - CONANDATA <<PYEOF`（line939-1056，get_mirrors 对 github/gnu/gnome/kernel 等返回镜像列表，gitlab.com 无规则 → mirrors=[url] 原样）；predl heredoc `python3 - CONANDATA PREDL_DIR <<PYEOF`（line1074-1187，curl 下载到 PREDL_DIR + `content.replace(url, f'file://{local_path}')` 改写 conandata.yml）
  - 首个 file:// 改写点：predl heredoc line1166-1175（downloaded 非空时替换写入 conandata.yml）
  - line32 source 的 sqlite_runtime.sh：inode 2305843009252087536, size 3457, sha256 897ce6a2495010d46b2efee6f6ddc9224040db4328b2a263c6fd8650d2ef80ed
  - build_and_test.sh：inode 2305843009213722468, size 80031, sha256 7c562ee8c781272c5b6c90981d66b05371da33173dbb84e407ccd6225e78df2f（HEAD 版）
  - 部署 Eigen-only predl 跳过后 build_and_test.sh sha256 1a977ba138c81053aef67ebfb3b7a26814bc96e8757bee19da6fe034b8ff33a8；W3 重跑 predl 仍旧行为（Pre-downloaded 1 files + file:// 断链 + 54KB HTML）→ 被执行的 predl python 块与所编辑 heredoc 不同源
  - r09 W3 日志（archive reports/w3-local-ci.log）mtime 09:57:14；JC_RESULT=pass / Junk Files: 0（full 40221 文件）；predl 段仍 "found 1 source URL(s)" + "Pre-downloaded 1 files, conandata.yml updated to file:// URLs"；conan source() FileNotFoundError predl_cache/bb23f95d_source_bb23f95d-/archive/3.4.0/eigen-3.4.0.tar.gz
  - r09 finish worker: worker-7accae9a-745e-4b75-955e-90577c069fcb (failed exit=1, natural terminal)
  - 结论：worker W3 运行时实际执行的 predl 层与 worktree 文件内 heredoc 不一致（更底层 worker 框架副本/加载链仍未知），是 worker-framework-version-drift 的强化证据
- r10 运行时替换层取证证据：
  - 完整父进程链：14853 (ohpc_compile_worker.py, --worktree-root .../worktrees) → 40557 (python3 worktree/scripts/ohc-run.py finish eigen3 3.4.0 built) → 40998 (zsh worktree/ci/conan/build_and_test.sh archives/e/eigen3/3.4.0)
  - W3 进程 cwd = worktree；启动环境 PATH=/system/bin:/usr/bin:/bin:~/.local/bin:~/.npm/bin:~/usr/local/bin:...:/data/service/hnp/bin; LD_LIBRARY_PATH=~/usr/local/lib:...; CMAKE_PREFIX_PATH=~/usr/local
  - heredoc 用 Python 解释器：/storage/Users/currentUser/usr/local/bin/python3 (3.12.9, sys.executable)
  - heredoc 临时/缓存文件：.build-cache/predl_cache/bb23f95d_source_bb23f95d (UTF-8 text 54KB, sha256 ef455167f29ef8170cb80ab082efa227a7cb8b951ac111228dbb9d61aabfd851)
  - conandata.yml 写入证据：官方 URL (sha ebcb4e19...) 被 predl 改写为 file:// (sha d258d32c..., mtime 2026-08-28 10:12:42, inode 2305843009252089814)，写入者为 W3 build_and_test.sh 进程
  - 副本比对：main repo (/storage/Users/currentUser/junshi_liu/build_in_harmonyos/ci/conan/build_and_test.sh, inode 2305843009236128464) 与 worktree (inode 2305843009238115170) 均 sha 7c562ee8...；无 .oh-runner 部署副本、无覆盖挂载、非软链接；ohc 包存在 __pycache__ 字节码缓存(finish/cli/utils 等)
  - 部署 Eigen-only predl 跳过 (build_and_test.sh sha 6836bddc...) 后 W3 重跑 predl 仍旧行为（found 1 source URL(s) + [cached] source_bb23f95d 54KB + file:// 断链）→ 被执行的 predl python 块与所编辑 heredoc 不同源
  - r10 finish worker: worker-e69b92ef-ba5e-4a39-93ec-76535c2242e2 (failed exit=1, natural terminal)；r10 W3 日志 mtime 10:21:35，JC_RESULT=pass / Junk Files: 0（full 40221）
  - 结论：worker W3 实际执行的 predl 层与 worktree 文件内 heredoc 不一致，真实执行源仍在更底层（worker 框架自身副本/运行时替换层），是本轮首个缺口
- r11 最终复验证据：
  - 加载链重申（ps 取证）：14853 (ohpc_compile_worker.py) → 62162 (python3 worktree/scripts/ohc-run.py finish eigen3 3.4.0 built) → 62456 (zsh worktree/ci/conan/build_and_test.sh archives/e/eigen3/3.4.0)；predl 消息源=worktree build_and_test.sh line1094/1175
  - 再次部署 Eigen-only predl 跳过（worktree build_and_test.sh sha 7c562ee8→b65f0165，ast 校验 OK）后，W3 仍报：found 1 source URL(s) + [cached] source_bb23f95d (54KB) + Pre-downloaded 1 files...file:// + conan source() FileNotFoundError（第 5 次修复尝试无效）
  - 三处基线文件隔离/恢复 SHA 一致；eigen3 原子范围不变；build_and_test.sh 已还原 HEAD（sha 7c562ee8）
  - 结论：对 worktree/main repo 已确认执行路径的 predl 修复不生效 → 执行源在更底层，属 worker-framework-version-drift，报告 external_blocked，停止继续重试，等待框架维护方
