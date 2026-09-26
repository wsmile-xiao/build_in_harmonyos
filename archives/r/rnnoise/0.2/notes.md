# rnnoise 0.2 adaptation notes (HarmonyOS PC, aarch64)

- Upstream is the official Xiph rnnoise release, tag `v0.2`. The recipe uses
  the **GitHub release dist tarball** (`make dist` 产物), which contains the
  generated `configure`, `Makefile.in`, `package_version`
  (`PACKAGE_VERSION="0.2"`), and `src/rnnoise_data.{c,h}`. The SHA-256 is
  byte-verified in `conandata.yml`.
- ⚠️ 不要切回 gitlab 的 `/-/archive` 快照 tarball：它不含构建期生成文件
  `rnnoise_data.{c,h}`（需 download_model.sh 从 media.xiph.org 拉取约 22MB
  模型包再生成），`make` 编译 `rnn.c`/`denoise.c` 时缺 `rnnoise_data.h`
  直接失败（CI build #51220 实测，错误 `fatal error: 'rnnoise_data.h' file
  not found`）。
- ⚠️ 上游打包缺陷：`src/os_support.h` 被 `src/vec.h`（通用路径）与
  `src/vec_neon.h`（ARM/NEON 路径，第 35 行）引用，但该文件既不在上游 git
  也不在 release tarball 中（未列入 `Makefile.am` 的 `noinst_HEADERS`，
  `make dist` 漏打包）。aarch64 必然走 NEON 分支 → 编译报
  `vec_neon.h:35: fatal error: 'os_support.h' file not found`（CI build
  #52162 实测）。补丁 `patches/0001-add-missing-os_support-header.patch` 从
  Opus（同为 Xiph/BSD-3-Clause）补回 `OPUS_COPY`/`OPUS_MOVE`/`OPUS_CLEAR`
  宏，并改为包含 rnnoise 的 `common.h`（提供 `OPUS_INLINE`），不引入新依赖。
- ✅ 因为 dist tarball 自带 `configure`，`build()` **默认不跑 `autoreconf`**
  （仅在源码树缺 `configure` 时回退执行）。原因：`autoreconf -fi` 属高
  fork/内存开销步骤，CI worker 在负载高时对其报 `can't fork - try again`
  （build #51345 / #51238 实测；同段日志里 `grep`/`cut` 也出现
  `Out of memory`）。`tool_requires`（automake/1.18 + libtool/2.5.4）保留给
  回退路径。
- `package_version` 在构建前被重写为 `AUTO_UPDATE=no` +
  `PACKAGE_VERSION="0.2"`：dist tarball 自带的文件缺 `AUTO_UPDATE` 行，
  重写后保证 AC_INIT 的 `m4_esyscmd` 探针恒为 0.2、make 期 `update_version`
  规则退出且不触碰 `configure.ac`（无构建中途 autoconf 重生成）。
- v0.2 adds SSE4.1/AVX2 fast paths and run-time CPU detection (RTCD), both
  x86-only and gated by `--enable-x86-rtcd` (default off). On OHOS aarch64
  the recipe passes `--disable-x86-rtcd` explicitly and the NEON path
  (`src/vec_neon.h`) is selected via the arch macros.
- `--disable-doc` is passed: doxygen is absent from the sandbox while the
  default enables the doc targets.
- E114 (OHOS security framework): configure's `config.status` subprocess
  cannot create its `./confXXXXXX` temp dir and write `subs1.awk`
  (Permission denied). The recipe pre-creates a writable dir, points
  `TMPDIR` at it, and repoints configure's internal `ac_tmp` (same fix as
  rnnoise/0.1.1).
- The library links only against libm; no third-party runtime dependencies.
- Upstream v0.2 ships no test suite (no tests dir / make check / framework);
  `Makefile.am` builds the library, the noinst `dump_features`/
  `dump_weights_blob` training tools, and the `rnnoise_demo` example.
- Consumer validation (test_package/test.c) exercises rnnoise_get_size /
  rnnoise_get_frame_size / rnnoise_create / rnnoise_process_frame /
  rnnoise_destroy on OHOS aarch64 and runs inside `conan create`.
---

## 验证与知识沉淀（2026-09-23）

- CI 校验通过：Build #56475（worker CI-023），Conan test_package / L0 结构门禁 / L1 测试执行门禁全部通过。
- 路径 B 知识草稿（随本 PR 提交）：
  1. `knowledge/drafts/DRAFT-11327-upstream-dist-drops-referenced-header-non-x86-path.{md,kv}`
     —— 上游发行包漏打包被引用头文件（仅非 x86/NEON 分支命中）
  2. `knowledge/drafts/DRAFT-11327-ohos-cannot-fork-heavy-bootstrap-intermittent.{md,kv}`
     —— 受限 CI worker 上间歇性 `can't fork` 的判定与规避
