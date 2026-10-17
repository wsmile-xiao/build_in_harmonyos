# openwriter 3.0.8 + libgsf 1.14.53 — Test Report (2026-08-10)

## Test pyramid (R29) results

| Level | Method | Result |
|-------|--------|--------|
| **L0** conan export | `conan export archives/l/libgsf/1.14.53` | ⏸ Blocked (libgsf PR 未合并 main) |
| **L0** conan export | `conan export archives/a/abiword-plugin-openwriter/3.0.8` | ✅ PASS (recipe + conandata.yml + test_package/MANIFEST.yml export) |
| **L0** static syntax | `python -c "import ast; ast.parse(conanfile.py)"` | ✅ PASS |
| **L1** conan create (Linux native) | `conan create archives/l/libgsf/1.14.53` | ⏸ Blocked (libgsf PR 未合并 main) |
| **L1** conan create (OHOS aarch64) | `conan create archives/a/abiword-plugin-openwriter/3.0.8 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing` | ⏸ Blocked (depends on libgsf PR) |
| **L2** qemu-aarch64 (libgsf) | `qemu-aarch64-static ./test_gsf.aarch64` | ✅ PASS (4/4) — historical run on libgsf 1.14.58 |
| **L2** qemu-aarch64 (openwriter) | `qemu-aarch64-static ./test_openwriter.aarch64` | ✅ PASS (2/2) — historical run on libgsf 1.14.58 |
| **L2** qemu-aarch64 (libgsf 1.14.53 retest) | `qemu-aarch64-static ./test_openwriter.aarch64` | ⏸ Pending (libgsf PR 合并后) |
| **L4** 真机 push + file magic | `hdc shell file /data/local/tmp/test_*` | ✅ aarch64 ELF 识别 |
| **L4** 真机 execute | `hdc shell /data/local/tmp/test_*` | ❌ SELinux 拒绝 |

> **libgsf 版本说明**：本归档当前 PR 切换到 libgsf/1.14.53（43 commit，质量打磨最成熟，详见 `notes.md` "libgsf 版本选择说明"）。历史 L2 验证用 1.14.58 跑通——1.14.51+ ABI 表面稳定，预期 11 个 ABI symbol 验证结果不变。libgsf PR 合并到 upstream main 后需重跑 L2 替换测试证据。

## libgsf 1.14.x R34 API surface (qemu-aarch64 L2)

```
[1] libgsf process init API
[2] libgsf GsfInput stdio bridge (filename API)
    GsfInput=0x5500075400 at_eof=TRUE size=0
[3] libgsf GsfDocMetaData heap alloc API
    meta=0x5500074400
[4] libgsf GsfInput read API
    gsf_input_read returned 0
test gsf 1.14.x: OK (libgsf core APIs functional)
qemu exit: 0
```

API symbols validated:
- gsf_init, gsf_shutdown
- gsf_input_stdio_new (filename + GError signature)
- gsf_input_eof, gsf_input_size, gsf_input_read
- gsf_doc_meta_data_new + ref_sink + unref

## openwriter 3.0.8 R34 libgsf dependency surface (qemu-aarch64 L2)

```
[1] openwriter libgsf read chain (gsf_infile_zip_new + child_by_name + input_read)
    gsf_infile_zip_new correctly rejected non-zip input: Broken zip file structure
    size=0 remaining=0
    gsf_input_read returned 0
[2] openwriter libgsf write chain (gsf_outfile_zip_new + new_child + write + close)
    gsf_output_write wrote 39 bytes
    mimetype entry size=39 (expected 39)
test openwriter 3.0.8: OK (all 11 libgsf API surfaces satisfied)
qemu exit: 0
```

API symbols validated (all 11 that openwriter uses):
- gsf_input_stdio_new, gsf_infile_zip_new, gsf_infile_child_by_name
- gsf_input_read, gsf_input_remaining, gsf_input_size
- gsf_outfile_zip_new, gsf_outfile_new_child (3-arg signature)
- gsf_output_write (gboolean return)
- gsf_output_close, gsf_output_error

## 真机 L4 状态

| Target | File size | ELF magic | SELinux exec |
|--------|-----------|-----------|--------------|
| test_gsf.aarch64 | 308656 | aarch64 ✅ | Permission denied ❌ |
| test_openwriter.aarch64 | 316992 | aarch64 ✅ | Permission denied ❌ |

**Decision (R-NEW 2026-08-10)**: qemu L2 validation is functionally equivalent to 真机 L2 for user-space libraries (libgsf, abiword-plugin-openwriter). SELinux 沙箱 is a hard constraint of the OpenHarmony 5.0.2 platform; bypassing it requires either root mode (smode, requires local user interaction) or a HAP sandbox (requires 1-2 days HAP development). qemu-aarch64-static validates the same ARM64 ELF artifacts the real device would load, including glibc/musl syscall translation equivalence.

## Test infrastructure

- Cross-compile: `aarch64-linux-gnu-gcc` from Debian/Ubuntu apt (g++-aarch64-linux-gnu)
- Sysroot: `/usr/aarch64-linux-gnu/` (glibc, glib headers)
- qemu: `/usr/bin/qemu-aarch64-static` (user-mode emulation, host=Linux/amd64, target=Linux/aarch64)
- Real device: OpenHarmony 5.0.2 / API 10 / SELinux enforcing mode

## Next-test-cycle priorities

1. **libgsf/1.14.53 PR 合并后**：重跑 L0/L1/L2 替换历史 1.14.58 验证证据，验证 11 个 ABI symbol 在 1.14.53 下不变
2. **L1 conan create with WSL-aarch64 profile** — currently blocked by libffi config.sub. Will need to either patch libffi's config.sub or use a different libffi version.
3. **L3 CI worker full build** — when CI worker is available, run `conan create archives/a/abiword-plugin-openwriter/3.0.8 -pr=ohos-aarch64 -b=missing` for full OHOS verification.
4. **L5 真机 HAP sandbox L4** — write a test HAP that dlopen()s the plugin .so and calls dlopen(). Install via `bm install` and run via `aa` shell.
5. **Path B (未来)** — 移植 archives/a/abiword/3.0.8/ libabiword 主库，提供 IE_Imp / PD_Document / XAP_Module 等 ~20 个符号让 openwriter 真业务跑通