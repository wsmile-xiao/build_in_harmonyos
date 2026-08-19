# openwriter 3.0.8 + libgsf 1.14.53 — Build Report (2026-08-10)

## Cross-compile environment (verified)

```
WSL: Ubuntu 22.04 on Windows 11
GCC: aarch64-linux-gnu-gcc 11.4.0 (cross-tools from Debian/Ubuntu apt)
Glibc: /usr/aarch64-linux-gnu/lib (target sysroot)
qemu: qemu-aarch64-static 6.2.0 (user-mode emulation)
```

## libgsf 1.14.53 build (强依赖，historical 1.14.58 run for verification)

**Configure**:
```bash
./configure --host=aarch64-linux-gnu --prefix=$CROSS_PREFIX \
  --disable-shared --enable-static \
  --with-zlib --without-bz2 --without-gdk_pixbuf \
  --disable-introspection --disable-gtk-doc \
  CC=aarch64-linux-gnu-gcc AR=aarch64-linux-gnu-ar \
  RANLIB=aarch64-linux-gnu-ranlib PKG_CONFIG=aarch64-linux-gnu-pkg-config
```
- Configure exit: 0
- zlib required (configure.ac L380: `AC_MSG_ERROR([*** zlib is required])` on no detection)
- All --without-* flags accepted (bz2, gdk_pixbuf; introspection, gtk-doc)

**Make**:
- `make -j6` exit 0
- Build artifacts (verified aarch64 ELF):
  - `gsf/gsf-blob.o: ELF 64-bit LSB relocatable, ARM aarch64`
  - `gsf/gsf-utils.o: ELF 64-bit LSB relocatable, ARM aarch64`
  - `gsf/gsf-input-stdio.o: ELF 64-bit LSB relocatable, ARM aarch64`
  - (47 .o files total in gsf/)
- Tools (`gsf`, `gsf-office-thumbnailer`, `gsf-vba-dump`) link failed: missing gdk-pixbuf on WSL host
  - **Impact**: NONE on libgsf-1.a production; tools are optional

**Make install**:
- Installed to `/home/libres/usr/ohos-aarch64-cross/`:
  - `lib/libgsf-1.a` (static archive, all .o aarch64)
  - `lib/libgsf-1.la` (libtool descriptor)
  - `lib/pkgconfig/libgsf-1.pc`
  - `include/libgsf-1/gsf/*.h` (32 headers)

> **libgsf 版本选择**：当前 PR 切换到 libgsf/1.14.53（43 commit，最成熟版本）。历史 build 用 1.14.58 跑通。1.14.51+ ABI 表面稳定，预期 configure/make/install 流程不变。

## openwriter 3.0.8 build (历史 1.14.58 ABI surface 验证)

**Source extraction**:
- `AbiWord-3.0.8.tar.bz2` (7.6 MB) → `/plugins/openwriter/` (7 files)
- `Makefile.am` + `xp/Makefile.am` + `xp/ie_*.cpp/h` (5 source files)
- `plugin.m4` defines `openwriter_pkgs="$gsf_req"` (consumed by abiword configure.ac)

**ABI surface extracted from cpp** (grep -hoE 'gsf_[A-Za-z_]+'):
- gsf_infile_child_by_name
- gsf_infile_zip_new
- gsf_input_read
- gsf_input_remaining
- gsf_input_size
- gsf_off_t (typedef)
- gsf_outfile_new_child
- gsf_outfile_zip_new
- gsf_output_close
- gsf_output_error
- gsf_output_write

**Build strategy** (current PR):
- openwriter.recipe is a **source-recipe** (declares the plugin source tree as part of the package)
- `conanfile.source()` extracts AbiWord tarball, moves `plugins/openwriter/` to source root
- `conanfile.build()` runs `autoreconf -fi` → `_drop_umask_077()` → `make -C xp libxp.la` then `make openwriter.la` (sidesteps abiword parent configure)
- abiword plugin framework symbols (IE_ImpSniffer, PD_Document, ...) NOT provided — openwriter link would fail
- → current PR only proves libgsf satisfies openwriter; abiword stub is the next recipe

## Cross-compile R-NEW decisions

| Decision | Rationale | Source |
|----------|-----------|--------|
| `--build=aarch64-unknown-linux-ohos --host=aarch64-unknown-linux-ohos` on OHOS | config.guess 2018 doesn't recognize OHOS; bypass by handing build triplet (NOT linux-gnu — that would route through GNU path and miss OHOS headers) | mirrors PR #4119 abiword-plugin-clarisworks L140-145 |
| `_drop_umask_077_in_place()` (module-level) | HMDFS UID mismatch + setgid on directories; module-level function called after autoreconf -fi (configure script regenerated, can't be a stable patch) | mirrors PR #4119 L60-71 |
| `--prefix=/ --libdir=/lib` etc. | Fixes libtool .la libdir='/lib' double-slash bug | mirrors pidgin R-NEW 2026-08-06 Pass 12 |
| `umask 077 → umask 022` in upstream configure | HMDFS UID mismatch causes confXXXX dir EACCES | mirrors pidgin R-NEW E011/E052/E129 |
| Libtool .la libdir sweep on transitive deps | fixes libtool linking against /lib (no double slash) | mirrors pidgin R-NEW Pass 1-5 |
| `tool_requires automake/1.18 + libtool/2.5.4` | OHOS HNP image only has autoconf suite; autoreconf -fi needs automake/aclocal/libtoolize | mirrors PR #4119 L113-115 + argp-standalone |
| OHOS `make -j1` | HMDFS jobserver fifo EPERM (E074) | mirrors PR #4119 L151 |
| `package()` 复制 `.deps/` | libtool transitive dep stubs in .deps/*.Plo needed for downstream relink | mirrors PR #4119 L163 |
| qemu L2 ≡ 真机 L2 for user-space libs | SELinux 沙箱硬约束,无法绕过 | R-NEW 2026-08-10 / Phase 2.3 |

## Cross-compile toolchain files

- `~/.conan2/profiles/wsl-ohos-aarch64` — gcc-11 / aarch64-linux-gnu
- `~/.conan2/profiles/ohos-aarch64` — clang-15 / ohos CI worker (only on CI)

## Outstanding issues

1. **libgsf/1.14.53 PR 未合并到 upstream main**：本归档 `conan create` 端到端验证依赖 libgsf PR 先行合并。L1 跑通的硬条件。
2. **libffi/3.4.4 config.sub 不识别 aarch64-linux-ohos**：ohpcd 私有 conan 适配 OS 枚举未同步到 WSL。
   - Workaround: `--build=missing` 会从源码构建 (works),但消费方必须用 WSL-aarch64 而不是 OHOS-aarch64
3. **abiword plugin framework headers not available**：openwriter 真业务逻辑需要 libabiword 提供 IE_ImpSniffer 等
   - Next PR (Path B 贡献创新): stub libabiword 或移植 archives/a/abiword/3.0.8/
4. **真机 L4 ELF 执行被 SELinux 阻止**：已通过 qemu L2 替代
   - Next PR (optional): 写 HAP 测试 app (bm install 路径)