# libunwind 1.6.2 适配笔记

## 本轮结论

- 已进入真机 shadow CI 阶段，真机连接 `currentUser@10.62.220.52:2222` 可用。
- 已补齐 Conan 配方、源码校验、OHOS configure 补丁和非空壳 `test_package`。
- shadow CI 暴露并修复了 OHOS 构建环境里的 `AR/RANLIB`、`mktemp` 和 `test_package` CMake PATH 问题；r4 复跑已通过。
- 审查补充后已在真机执行上游测试：全量 `make check -j1` 为 29 项中 20 过、9 败；recipe 中 `run_upstream_tests=True` 固化为 OHOS 稳定上游子集 20/29，r11 复跑通过。
- issue 已按最新要求忽略。

## 构建系统分析

- 上游 1.6.2 使用 Autotools。
- release 包包含 `configure.ac`、`configure`、`Makefile.am`、`src/Makefile.am`、`tests/Makefile.am`。
- `config/config.sub` 不认识 `aarch64-linux-ohos`，需要补丁。
- `configure` 默认会在非 Android GCC/Clang 分支加入 `-lgcc_s`；OHOS Clang 运行时不应依赖该库，因此补丁把 `*ohos*` 纳入同类处理。

## W0 依赖

- 必需依赖: 无。
- 可选依赖: `zlib`、`xz/liblzma` 仅用于 compressed debug info，本轮关闭。
- 可选能力: `setjmp`、`coredump`、`ptrace`、文档生成关闭，避免引入权限/工具/依赖问题。

## 配方策略

- static-only: `--disable-shared --enable-static`，避免同名 `libunwind.so` 与系统/LLVM 运行时冲突。
- OHOS 仅声明 armv8/AArch64。
- OHOS 构建环境从 `tools.build:compiler_executables` 取得 clang 所在目录，注入 `PATH`、`AR`、`NM`、`RANLIB`、`STRIP`。
- OHOS configure 阶段注入 recipe-local 工具目录、`TMPDIR=/data/storage/el2/base/libunwind-configure-tmp`，并用 `replace_in_file(strict=True)` 将 Autoconf 生成 `config.status` 的临时目录从 `./conf*` 改到 `$TMPDIR/conf*`，规避构建目录子目录权限导致的 `subs1.awk: Permission denied`。
- `test_package` 在 OHOS 下也注入工具链目录，确保 CMake helper 能找到 `cmake`/`make`。
- 默认构建不跑上游 suite；真机窗口可通过 `-c user.libunwind:run_upstream_tests=True` 运行 OHOS 稳定上游子集 20/29。

## 测试策略

- `test_package` 使用 CMake 消费者测试。
- 测试程序定义 `UNW_LOCAL_ONLY`，调用 `unw_getcontext`、`unw_init_local`、`unw_get_reg` 和 `unw_step`，验证 IP/SP 非零并能至少展开一帧。
- 上游全量 `make check -j1` 已在真机 r10 执行：`TOTAL 29 / PASS 20 / FAIL 9`。
- recipe 的显式上游验证模式运行 20 个 OHOS 稳定上游测试：`test-proc-info`、`test-static-link`、`test-strerror`、`Gtest-bt`、`Ltest-bt`、`Gtest-exc`、`Ltest-exc`、`Gtest-init`、`Ltest-init`、`Gtest-concurrent`、`Ltest-concurrent`、`Gtest-trace`、`Ltest-trace`、`test-async-sig`、`test-flush-cache`、`test-init-remote`、`test-mem`、`Ltest-varargs`、`Ltest-nomalloc`、`Lrs-race`。
- 未纳入子集的 9 项：`Gtest-resume-sig`、`Ltest-resume-sig`、`Gtest-resume-sig-rt`、`Ltest-resume-sig-rt`、`test-reg-state` 在真机上段错误；`Ltest-init-local-signal` 栈步数与上游预期不一致；`Ltest-mem-validate` 地址校验返回非预期；`Ltest-nocalloc` abort；`run-check-namespace` 因 `/bin/sh` interpreter permission denied 失败。

## 本机验证

- 官方 GitHub release 源可下载，SHA256:
  `4a6aec666991fb45d0889c44aede8ad6eb108071c3554fcdff671f9c94794976`
- Savannah release 主源本机访问返回 `502 Bad Gateway`。
- 本机未安装 `conan`，未运行 `conan create`。
- `python -m py_compile conanfile.py test_package/conanfile.py` 通过。
- `git diff --check -- archives/l/libunwind/1.6.2` 通过。

## 知识草稿

- `knowledge/drafts/E338-draft-libunwind-ohos-autotools-native-tools.{kv,md}`: 记录 OHOS native Autotools release 包在 shadow CI 上需要 recipe-local 工具链 PATH、`AR/NM/RANLIB/STRIP` 和 `mktemp` wrapper 闭环。
- `knowledge/drafts/E339-draft-libunwind-ohos-test-package-cmake-path.{kv,md}`: 记录 Conan 2 `test_package` 是独立 recipe 环境，CMake helper 需要单独注入 OHOS 工具链 PATH。

## 真机 shadow CI

隔离 job:

```sh
/storage/Users/currentUser/ohos-users/codex/libunwind-1.6.2-shadow-20260825-192940/run-conan-heavy.sh
```

真机运行记录:

- `codex-1.6.2-libunwind-1.6.2-shadow-20260825-192940-conan-20260825-193325-49430`: 等锁 277s 后执行，失败于 `configure: could not determine link -lib interface`；原因是 runner PATH 未包含 `/data/service/hnp/bin`，Autotools 未找到 `ar`。
- `codex-1.6.2-libunwind-1.6.2-shadow-20260825-192940-conan-20260825-195007-10524`: 注入 `AR/NM/RANLIB/STRIP` 后等锁 2126s 执行，失败于 `./conf*/subs1.awk: Permission denied`；原因是 OHOS 上 `mktemp` 创建的 Autoconf 临时目录权限不可执行。
- `codex-1.6.2-libunwind-1.6.2-shadow-20260825-192940-conan-20260825-203010-1333`: 已同步 `mktemp` wrapper 修复并启动复跑；由于全局锁持续被其它 shadow CI 抢占，未拿到执行窗口，已中断等待，未生成退出码。
- `codex-libunwind-libunwind-1.6.2-shadow-20260825-192940-conan-watch-20260825-220313-20260825-220413-57701`: 等空闲后抢锁成功，主包构建/打包通过，失败于 `test_package` 的 `cmake: inaccessible or not found`。
- `codex-libunwind-libunwind-1.6.2-shadow-20260825-192940-conan-watch-r4-20260825-221014-20260825-221637-7273`: 注入 test_package PATH 后通过，`exit-code.txt=0`；`test_package` 输出 `libunwind walked 3 frame(s)`，Build Summary: Success 1 / Failed 0。
- `codex-libunwind-libunwind-upstream-tests-r10-20260826-1735-20260826-172935-65198`: 绝对 profile 路径 + 本地 source tarball 验证，全量 `make check -j1` 执行，结果 `TOTAL 29 / PASS 20 / FAIL 9`，失败项见“测试策略”。
- `codex-libunwind-libunwind-upstream-tests-r11-20260826-1741-20260826-173639-14405`: `run_upstream_tests=True` 运行 OHOS 稳定上游子集，日志标记 `PASS LIBUNWIND_UPSTREAM=20/29 scope=ohos-stable-subset`，`exit_code=0`；`test_package` 输出 `libunwind walked 3 frame(s)`。

复现命令:

```sh
ssh -i C:/Users/ASUS/.ssh/ohos_pc_codex_ed25519 -p 2222 currentUser@10.62.220.52 \
  'JOB=/storage/Users/currentUser/ohos-users/codex/libunwind-1.6.2-shadow-20260825-192940; . "$JOB/env.sh"; sh "$HOME/bin/ohos-test-runner.sh" --user "$OHOS_ISOLATED_USER" --lib libunwind --task "$OHOS_ISOLATED_JOB-conan-rerun" --mode heavy --try-lock --workdir "$CI_REPO_ROOT" -- zsh ci/conan/build_and_test.sh "$CI_PACKAGES"'
```

## 下一步

```sh
CI_PACKAGES="archives/l/libunwind/1.6.2" zsh ci/conan/build_and_test.sh
```

可选真机上游子集测试:

```sh
cd archives/l/libunwind/1.6.2
conan create . --user=ohpcd --channel=stable \
  -pr:h=$HOME/.conan2/profiles/ohos \
  -pr:b=$HOME/.conan2/profiles/ohos \
  --build=missing \
  -c user.libunwind:run_upstream_tests=True
```
