# rdfind 1.8.0 HarmonyOS (OpenHarmony PC) adaptation notes

## Status

- Branch: `feat/rdfind-1.8.0`
- Task: 平台任务 rdfind 1.8.0（平台 id=10035，activity 开源鸿蒙PC专项积分赛）
- Current state: recipe authored; **1 patch** (HMDFS umask, see below); the only mandatory
  dependency is nettle (published as `nettle/3.10.2.1`). Platform CI builds **#50911, #50915,
  #50925 and #50928 passed** (`Conan test_package: 通过`, L0/L1 gates passed); the latest passing
  build for the currently pushed commit is **#50928**. Platform CI is **comment-triggered** (a push
  alone does not re-run it; `/rebuild` must be posted on the PR), so always cite the platform's
  newest `## CI 校验通过` comment instead of this list.

## Upstream source note

- URL: https://rdfind.pauldreik.se/rdfind-1.8.0.tar.gz（官方发布页，非镜像/非 fork）
- SHA256: `0a2d0d32002cc2dc0134ee7b649bcc811ecfb2f8d9f672aa476a851152e7af35`
- The release tarball already ships the generated `configure`, `Makefile.in`,
  `install-sh`, `missing` and `depcomp`, so no `autoreconf` bootstrap is needed
  (unlike `rnnoise/0.1.1`, whose tarball needed `automake`/`libtool` tool_requires).

## Portability patch (1)

`patches/0001-configure-hmdfs-umask.patch` — the only source change in this port; the
upstream `.c/.h` sources and `configure.ac` are untouched.

- autoconf's `configure` creates its private temporary directory with
  `(umask 077 && mktemp -d "./confXXXXXX")`. On the OHOS worker the workspace lives on
  HMDFS, where that 0700 + setgid directory is not writable, so `config.status` aborted
  in CI build #50908 with:

  ```
  ./config.status: line 611: ./confImGAig/subs1.awk: Permission denied
  config.status: error: could not setup config files machinery
  ```

- Fix: both `umask 077` occurrences become `umask 022` — the same remedy as the in-tree
  precedent `archives/y/yydecode/0.2.10/patches/0001-configure-hmdfs-umask.patch` and the
  knowledge entry whose `rec_approach` is `bypass-mktemp`.
- Verified locally: `patch -p1` applies both hunks cleanly to a pristine tarball tree and
  the patched tree still configures and builds (`CONFIGURE OK (patched)` /
  `MAKE OK (patched)` → ELF64 AArch64). Raw transcript: `reports/rdfind-crosscheck.txt`.

## W0 Dependency Check

- Mandatory dependency: **nettle** — `configure.ac` runs
  `AC_CHECK_HEADER(nettle/sha1.h, …)` and `AC_CHECK_LIB(nettle, nettle_pbkdf2_hmac_sha256, …)`,
  both with `AC_MSG_ERROR`, i.e. configure aborts without it. `nettle/3.10.2.1` is published
  in the registry and already archived in this repository, so the dependency gate is satisfied.
- Optional dependency: **xxhash** (`--with-xxhash`, default `check`). The recipe passes
  `--without-xxhash` explicitly so the build depends only on published packages.
- gmp arrives transitively through nettle; the symbols rdfind uses (sha1/sha256) do not pull
  gmp objects in, so no explicit `-lgmp` is required (the produced ELF's `NEEDED` entries are
  only `libc++_shared.so` / `libc.so`, confirming nettle was linked statically).

## Source and Build Analysis

- Build system: Autotools. `Makefile.am` declares `TESTS=` with **15** shell test cases
  (`checksum_buffersize.sh`, `checksum_options.sh`, `hardlink_fails.sh`, `largefilesupport.sh`,
  `md5collisions.sh`, `sha1collisions.sh`, `symlinking_action.sh`,
  `verify_deterministic_operation.sh`, `verify_dryrun_option.sh`, `verify_filesize_option.sh`,
  `verify_maxfilesize_option.sh`, `verify_nochecksum.sh`, `verify_ranking.sh`,
  `verify_size_savings.sh`, `verify_skipfirstbytes.sh`). `testcases/common_funcs.sh` is listed
  under `AUXFILES` (a shared fixture, not a test case), so it is **not** counted. `test-driver`
  ships in the tarball, so `make check` works out of the box on a native build.
- Command line contract: `rdfind [options] <dir>`, with `-outputname <file>`,
  `-makeresultsfile true|false`, `-checksum none|md5|sha1|sha256|sha512|xxh128`,
  `-dryrun|-n`, `-deleteduplicates`, `-deterministic`. The results file starts with
  `# Automatically generated` / `# duptype id depth size device inode priority name`
  (`Rdutil.cc:51-52`) and each row is classified as `DUPTYPE_FIRST_OCCURRENCE`,
  `DUPTYPE_WITHIN_SAME_TREE` or `DUPTYPE_OUTSIDE_TREE` (`Fileinfo.cc` `getduptypestring`).
  The packaged test asserts exactly on that contract.
- `config.guess` cannot recognise the OHOS triple, so the cross trio is supplied by the Conan
  toolchain (`AutotoolsToolchain`): the effective configure line on the build host is
  `--host=aarch64-linux-ohos --build=x86_64-unknown-windows` (see
  `reports/rdfind-conan-attempt.log`). The recipe deliberately adds **no** second
  `--host/--build` pair: a duplicate pair would override the toolchain's values and make
  configure believe it is a native build (it would then try to run aarch64 test programs on
  the build machine).
- AutotoolsToolchain does not inject dependency include/lib directories, and rdfind probes
  nettle with `AC_CHECK_HEADER`/`AC_CHECK_LIB` rather than pkg-config — so nettle's
  `includedirs`/`libdirs` are appended to `extra_cflags`/`extra_cxxflags`/`extra_ldflags`
  (R33: compiler and flags come from Conan, never from bare shell variables).
- rdfind 1.8 requires **C++17** (`rdfind.cc:9` has
  `static_assert(__cplusplus >= 201703L, …)` and `configure.ac` errors out without it);
  the profile's `compiler.cppstd=17` supplies `-std=gnu++17` (CI profile
  `ci/conan/profiles/ohos-aarch64` is 17, same as the local `ohos-aarch64-windows`).

## Recipe Notes

- `package_type = "application"`; the package installs `bin/rdfind`, therefore the
  software-level `commands.json` (R38/L0k) declares the tool:
  `{"name": "rdfind", "type": "tool", "versions": {"1.8.0": {"ref": "rdfind/1.8.0", "binary": true}}}`.
- `make check` (the upstream suite) runs on native builds and **its result gates the
  build**: a real failure fails the build, so a green CI run is evidence about the
  upstream suite rather than a hidden warning. Skipped only when cross-building (the
  test programs are aarch64 OHOS binaries).
- **Upstream suite result on the OHOS worker (real data)**: `make check` →
  `# TOTAL: 15 · PASS: 9 · XFAIL: 6` — the six expected failures are declared with
  automake's `XFAIL_TESTS` in `conanfile.py` because they need capabilities the worker
  does not provide. Reasons were taken from the worker's own `test-suite.log`
  (CI build #50919, embedded in the failing CI comment) and are listed in
  `manifest.yaml` under `test_results.upstream.expected_failure_details`:
  HMDFS rejects hard links (`hardlink_fails.sh`, `verify_size_savings.sh`), `dd` cannot
  create 4 GiB sparse files (`largefilesupport.sh`), the worker's `base64` lacks GNU
  `decode` (`sha1collisions.sh`), and the worker's `stat` lacks `--dereference`
  (`symlinking_action.sh`, `verify_dryrun_option.sh` — the latter's dryrun assertions
  themselves passed). None of these is a porting defect of rdfind.

## 编译结束

- 构建入口（CI/worker）：`conan create archives/r/rdfind/1.8.0 -pr:h=ohos-aarch64
  -pr:b=ohos-aarch64 --build=rdfind/*`（由 `ci/conan/build_and_test.sh` 调用，
  CI profile 的 host/build 同为 OHOS ⇒ `cross_building()` 为假 ⇒ test_package 真实执行）。
- 本地验证（Windows 宿主）：本地 `conan create` 无法驱动 autotools —— 实测
  `conan/internal/subsystems.py::deduce_subsystem` 在 build scope 读取的是 **build profile**
  的 `os`，且只有 `conanfile.win_bash` 为真时才返回 bash subsystem；本机 build profile 是
  `os=Windows`，配方未设 `win_bash=True`，且 `tools.microsoft.bash:*` 只写在 host profile，
  因此 conan 用 cmd.exe 调 `./configure` 而失败（`reports/rdfind-conan-attempt.log:101-103`）。
  本地改为 **git-bash 内 in-tree configure + make** 的真交叉编译验证：`configure` 通过
  （nettle 头文件与 `-lnettle` 链接探测均 OK），`make` 通过（9 个 C++ 源文件全部编译），
  产物 `rdfind` 461,088 bytes，`llvm-readelf -h` 显示 `Class: ELF64` / `Machine: AArch64`；
  应用补丁后的复验同样通过。完整记录见 `reports/rdfind-crosscheck.txt`。
- 权威验证：平台 CI 构建 #50911 / #50915 / #50925 / #50928（R51 强制门禁下：make check 判定
  `# FAIL: 0`、`# XFAIL: 6`，`Conan test_package: 通过`、L0 结构门禁通过、L1 测试执行验证通过）；
  最新通过构建 **#50928 对应当次推送的提交**。CI 为**评论触发**（push 不触发），后续修订后需在
  PR 上发 `/rebuild` 重跑，引用请以平台最新 `## CI 校验通过` 评论为准（不要沿用本行历史构建号）。
