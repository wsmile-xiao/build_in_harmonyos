# DRAFT-ohos-autotools-dep-detection-macro-flag-injection — autotools 依赖检测宏只做存在性检查 → toolchain 注入（含静态库传递依赖）

> **Contributor**: GoliWie | **Status**: DRAFT | **Updated**: 2026-08-25
> **Severity**: medium (2) | **Category**: ohos / autotools / conan / configure / dependency / static-linking
> **Audience**: Conan+autotools 且依赖检测走宏探测（ACX_*/AC_CHECK_LIB，非 pkg-config）的项目

## 触发（trigger）

- configure 依赖段用 ACX_FFTW/ACX_OPENBLAS/ACX_CFITSIO + AC_CHECK_LIB/AC_CHECK_HEADER 探测。
- 报错：`fftw3.h: No such file or directory` / `CFITSIO library not found` / `xxx.h: No such file`。
- 依赖本身已发布到 Conan（ohpcd）——问题不在缺依赖，而在宏不传播 -I/-L。

## 机制（root cause，上游源码核验）

上游源码缓存 `/storage/Users/currentUser/.conan2/p/sourc9c08cbcd0a0e3/s`：
- `m4/acx_fftw.m4`：头文件 `AC_CHECK_HEADER($2/fftw3.h,...)`（存在性检查，定义 FFTW_H 为路径字面量）；库 `AC_CHECK_LIB(fftw3f, fftwf_execute, ..., [-L$1 -lm])`——不写 AM_CPPFLAGS。
- `m4/acx_cfitsio.m4`：头文件 `AC_CHECK_HEADER($2/fitsio.h,...)`；库 `AC_CHECK_LIB(cfitsio, ffopen, ..., [-L$1])`；cfitsio 静态库含未定义 zlib 符号（deflate/inflate），该链接探测缺 `-L<zlib>/lib -lz` 时失败（"CFITSIO library not found"）。
- `configure.ac` 290-338 行：`AC_SUBST(AM_CFLAGS/AM_CPPFLAGS/AM_LDFLAGS)` 但宏内从不写 AM_CPPFLAGS。

**措辞精确化（Curation Auditor §3.3）**：指定 libdir 时宏确实把 `-L$1` 写入链接探测；未注入的是构建期 `-I`（AM_CPPFLAGS）与静态库传递依赖的 `-L/-l`（如 zlib）。

## 修复（rec，AutotoolsToolchain 注入）

```python
# generate()
tc = AutotoolsToolchain(self)
tc.extra_cflags.append("-I%s" % os.path.join(fftw.package_folder, "include"))
tc.extra_cflags.append("-I%s" % os.path.join(blas.package_folder, "include"))
tc.extra_cflags.append("-I%s" % os.path.join(fits.package_folder, "include"))
tc.extra_ldflags.append("-L%s" % os.path.join(zlib.package_folder, "lib"))
tc.extra_ldflags.append("-lz")
tc.generate()
```

## 验证（verification，round-2 权威 CI）

- 日志 ci-round2-se-2.28.2.log（sha256 `9649d06a9c8091eaedc073cea52286595c5c1f90dcaf815b3b79fbd876a24cdf`）：
  - 433-445 行：configure 头文件检查通过（fftw3.h/fitsio.h 在 conan 包路径找到），`configure: creating ./config.status`。
  - 999-1002 行：实际编译/链接行含 `-I<fftw>/include -I<openblas>/include -I<cfitsio>/include` 与 `-L<zlib>/lib -lz`。
  - make check PASS（modelfit.test，1060-1065 行 TOTAL:1 PASS:1 FAIL:0 ERROR:0）。
- 先例观察（不否定 K2，反证跨库通用）：archives/s/swarp/2.41.5 配方已含 cfitsio→zlib 的 extra_ldflags -Lz/-lz（Archives 仓内先例，非 knowledge 条目）。

## 查重（dedup，Curator/Auditor 双重独立检索）

- `grep -rl -e "AM_CPPFLAGS" knowledge/` → **0 命中**
- `grep -rl -e "ACX_" knowledge/` → **0 命中**（ACX_FFTW/ACX_OPENBLAS/ACX_CFITSIO 均无）
- `grep -rl "cfitsio" knowledge/graph knowledge/drafts` → **0 命中**
- `grep -rl "extra_cflags" knowledge/graph knowledge/drafts` → E277（vendored 依赖 staging，场景为捆绑源码）、E2158-draft（-fsigned-char，无关）。
- 最相近条目逐项差异：E075（pkg-config 把 C_INCLUDE_PATH 当系统目录过滤 -I，机制不同）、E277（vendored/bundled 依赖 build() 内 staging，场景不同）、DRAFT-staticlib-transitive-libs / DRAFT-conan-staticlib-transitive-headers（消费者/中间包侧 Conan traits 层，K2 为 build 期 configure 宏探测）、E2158（-fsigned-char，无关）。

## Source

- Package: `archives/s/source-extractor/2.28.2`（conanfile.py generate()，sha256 `55163ba9a6e1d5a82231e1f1c8e082df192ee654efb0c1954454783ed9e7f29a`）
- Candidate: `64f1909f346d9847281d2fea1b70c5cbe0ec4a28`（feat/astromatic-1.3，round-2 权威 CI PASS + upstream FULL_PASS 1/1）
- Similar: E075、E277、E327-draft-configure-raw-lib-probe、DRAFT-conan-staticlib-transitive-headers
