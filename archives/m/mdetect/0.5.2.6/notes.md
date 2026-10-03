# mdetect 0.5.2.6 adaptation notes

## Build environment
- Build system: Autotools (configure.ac and Makefile.am are present).
- The source archive omits generated configure and Makefile files; the recipe must bootstrap with autoreconf -fi before configure.
- W0 dependency preflight passed with no declared dependencies.
- Compiler available on A: clang; C source is accepted by the task language preflight.
- Build has not started yet.

## Source/version facts
- The Debian changelog identifies the source package as mdetect 0.5.2.6.
- configure.ac still declares AC_INIT version 0.5.2.4; preserve exact Conan/archive/branch version 0.5.2.6 and do not modify upstream version metadata without a build need.
- debian/copyright describes the main source as dual-licensed under QPL-1.0 or GPL-2+; package the copyright notice with the executable.

## Runtime constraints
- mdetect scans /dev for mouse devices and may open serial ports, changing terminal settings while probing.
- Do not run the no-argument probe during build smoke checks on the build host; use the -h path for a safe CLI smoke check.
- Device-node availability on HarmonyOS must be recorded from a current device probe before stating runtime detection coverage.

## Build steps
Pending verified Conan build.

## Problems and fixes
None observed yet.

## Source modifications
None planned yet.

## Dependencies
None declared by the upstream project.

## Verification
Pending conan-verify and consumer test package.

## Delivery
Pending.

## 2026-09-27 setup command evidence
- Command: python3 scripts/ohc-run.py conan-init mdetect 0.5.2.6 --project-dir archives/m/mdetect/0.5.2.6 from the task worktree.
- Source SHA256: a0274a5820156b528e99bda55b62857ab0a74d2560086991819ac0a1d2d81fcb.
- Environment: DSH_AGENT=主理-76; task OHC_RESULT_OUT and CONAN_HOME set under ~/tmp; PATH was assigned the two required home bin directories but its inherited portion was escaped incorrectly by the Windows PowerShell caller.
- Exit code: 1. First error: sh: python3: inaccessible or not found.
- Fix before retry: pass the literal shell variable through PowerShell with a backtick, so the remote PATH retains its existing system entries.

## 2026-09-27 conan-init argument evidence
- Command: python3 scripts/ohc-run.py conan-init mdetect 0.5.2.6 --project-dir archives/m/mdetect/0.5.2.6 from the task worktree.
- Exit code: 1. First error: 归档目录不存在: archives/m/mdetect/0.5.2.6/archives/m/mdetect/0.5.2.6.
- Cause: --project-dir is a repository root, not an archive path; the option was unnecessary from the worktree root.
- Fix before retry: inspect the subcommand path handling and omit --project-dir from the worktree root.

## 2026-09-27 automake dependency availability evidence
- Exact query: conan download --only-recipe automake/1.18 --remote=conancenter using task CONAN_HOME /storage/Users/currentUser/tmp/ch/home-mdetect from the mdetect worktree.
- Exit code: 1. First error: 404: Not Found. [Remote: conancenter].
- Local evidence: this checkout contains rchives/a/automake/1.18/conanfile.py; device PATH has autoconf/autoreconf but no automake/aclocal.
- Next: inspect the repository's configured package preflight/remote flow and verify exact automake/1.18 availability there before deciding how the recipe can bootstrap.

## 2026-09-27 remote-template inspection evidence
- Command attempted to inspect the documented template home home-glm49-db53 with conan remote list and check its global.conf.
- Exit code: 1. First error: sh: conan: inaccessible or not found; the lookup command did not add the required user bin directories to PATH. The follow-on check also found no global.conf at that historical path.
- Fix before retry: enumerate current ~/tmp/ch homes, select a present home with an ohpcd remote and valid global.conf, and run Conan with the documented PATH.

## B判定与自举工具链
- B判定：hit(E178)。当前 A 机有 autoconf/autoreconf，但没有 automake/aclocal；本配方从已发布的 automake/1.18 获取 aclocal/automake，并在 conanbuild 环境执行 autoreconf -fi。
- 原登记推荐 B配送=M15 不匹配实际源码：mdetect.c/mice.c 使用 alarm/SIGALRM 做设备探测超时，没有 fork/exec/shell 子进程或 WTERMSIG 状态误判。
- automake/1.18 精确依赖用 conan install --requires=automake/1.18 配 OHOS aarch64 profile、--build=never 从 ohpcd 安装成功，确认已有可用二进制。
- 当前 A 机 /dev 名称探针未发现 ttyS/ttyUSB/ttyACM 字符设备；消费测试只执行 mdetect -h，不覆盖硬件探测能力。

## 2026-09-27 static-check invocation evidence
- Command attempted an inline Python AST parse of the three recipe/test files, followed by commands.json and lang-preflight checks.
- Exit code: 1 before the checks ran. First error: Python reported an invalid syntax at the first pathlib.Path path; PowerShell quoting removed the intended Python string delimiters.
- Fix before retry: use py_compile with plain file arguments and run JSON/language checks as separate simple commands.

## 2026-09-27 language-check invocation evidence
- The file syntax and commands.json checks passed. The subsequent lang-preflight mdetect 0.5.2.6 call returned exit code 1 because --src is required.
- First error: lang-preflight: error: the following arguments are required: --src.
- Fix before retry: pass the extracted source directory under /storage/Users/currentUser/tmp/uc2/mdetect-0.5.2.6/builds/mdetect-0.5.2.6.work.

## 2026-09-27 first build attempt evidence
- Command: A short slot (build-slot.sh --kind short --wait 1800 --mem 2500) around memcap-run.py --probe -- python3 scripts/ohc-run.py build mdetect 0.5.2.6.
- Worktree: /storage/Users/currentUser/qzy/主理-76-A-mdetect-0.5.2.6; source SHA256: a0274a5820156b528e99bda55b62857ab0a74d2560086991819ac0a1d2d81fcb; task result output and task CONAN_HOME were set under ~/tmp.
- Pre-scan: zero findings, four knowledge rules; no source changes or patches were applied.
- Result: driver exit code 2 at Step3 configure (configure subprocess RC=127); first error: sh: /storage/Users/currentUser/tmp/uc2/mdetect-0.5.2.6/builds/mdetect-0.5.2.6.work/configure: No such file or directory.
- Cause: the direct ohc build driver invokes the generated configure script; the Conan recipe autoreconf step had not run in this driver path.
- Probe measured 191 MB before configure failed, so this is not a full-build peak measurement.
- Recovery: generate configure in the task's temporary source tree using the task-home automake/1.18 build environment, then resume the driver's reported Step4 command. No repository source was modified.

## 2026-09-27 evidence capture helper check
- The failed Step3 log was moved from the home root into this task's tmp directory successfully.
- A follow-up environment-file check returned 1 because it tested the generated conanbuild.sh for executable permission; the file is a readable shell environment script and should be sourced, not executed.

## 2026-09-27 stop-work checkpoint
- User requested stop and handoff. No active mdetect build process was found on A; no PR or CI exists.
- A is reachable. Current task branch is feat/mdetect-0.5.2.6 at base 48d9cee6844d0fca1f25e86c2df1293b904855d8. Task archive files are uncommitted. This checkpoint records an incomplete adaptation; it does not claim build or Conan verification.
- The Step3 failure was missing generated configure in the extracted task source. autoreconf -fi has since generated configure in the task temporary source tree; next action is the documented Step4 resume command.
- Build-driver .handoff.json still records its initial E510 suggestion and the old home-root log path. The observed Step3 failure was missing configure; do not apply the E510 GNU patch suggestion without new evidence. The active B classification is hit(E178), for the missing automake bootstrap tool.
- Worktree also has unrelated libXext README/manifest modifications and an untracked feedback file. They were left untouched and must not be included in the task commit.
- Git's configured identity is 主理-74; this window must use a one-command 主理-76 identity override for any task commit. Global Git configuration was not changed.
---

**编译结束**: 2026-09-30 14:20
**最终状态**: built
