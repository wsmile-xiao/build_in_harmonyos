# DRAFT-pangomm-2.50.1-cxx17-libcxx-conan-profile — 统一 C++17/libc++ Profile 后 ohpcd 发布依赖图选项不一致的解决与 pangomm 本地闭环修复链（r12 补正）

> **Contributor**: junshi_liu | **Team**: 兰州大学DSLab | **Status**: VERIFIED DRAFT | **Updated**: 2026-08-25
> **Severity**: medium | **Category**: conan-profile / dependency-graph / ohpcd-publish / ohos-toolchain

## Usage

Use this pattern when adapting a Meson-based library that consumes glibmm,
cairomm, pango/harfbuzz on OHOS armv8 clang15 C++17/libc++ profile via Conan,
and encounters PkgConfigDeps missing alias-.pc、variable injection、find_library
link path、binary-sign-tool syntax、and runtime musl loader compatibility issues.

## Symptom

### r11 original (fixed by new harfbuzz publish)

```
ERROR: Missing binary: harfbuzz/14.2.0.1:1b5bfb055da66cb3e7048ff4353ae90d33ea8614
Options conflicts: glib/2.84.0.1:shared=True (current value) / harfbuzz/14.2.0.1->shared=False
```

Published harfbuzz binary 3009fa3b required glib/2.84.0.1:7bf99b8d (static),
but pangomm graph resolved glib shared=True (b55f7a48). Fixed by ohpcd
publishing harfbuzz/14.2.0.1#58fa487c (2026-08-23) with binary 1b5bfb requiring
glib/2.84.Z (dynamic, unpinned revision).

### r12 — pangomm recipe fixes (conan create passed)

Error sequence and fixes:

| Error | Fix |
|-------|-----|
| `dependency('pangocairo')` not found | Create forwarding `pangocairo.pc` + `pangoft2.pc` with Name/Description/Version |
| `gmmprocdir` pkg-config variable missing | Inject `gmmprocdir=${libdir}/glibmm-2.68/proc` into generated `glibmm-2.68.pc` |
| `find_library('glibmm_generate_extra_defs-2.68')` not found | Add `-L<glibmm-libdir>` via `tools.build:sharedlinkflags/exelinkflags` conf |
| `binary-sign-tool sign -a` fails (`-a` not a valid command) | Fix to `sign -selfSign 1 -inFile X -outFile Y` |
| `pangomm.h` not found in test_package | Add `package_info()` with `include/pangomm-2.48` + `lib/pangomm-2.48/include` |
| `Pango::AttributeList` / `AttrSize` API mismatch | Fix test_package to use `AttrList` / `AttrInt` with `set_value()` |
| `AttrInt()` constructor protected | Simplify test to use `AttrList` default ctor only |

### r12 — runtime musl loader block

```
Error loading shared library libcairomm-1.16.so.1: (needed by ./test_probe)
Error relocating libpangomm-2.48.so.1: _ZN5Cairo11FontOptionsC1EP19_cairo_font_optionsb: symbol not found
```

The symbol exists in cairomm .so dynamic symbol table (verified via llvm-nm -D).
OHOS musl-based dynamic linker fails to resolve it. Removing .codesign section
and adding SDK libc++_shared.so path did not help. This is an external runtime
environment issue with the published cairomm binary, not a pangomm recipe issue.

## Evidence

1. **HarfBuzz new package**: `conan list 'harfbuzz/14.2.0.1:*' -r ohpcd` shows
   recipe revision 58fa487c (2026-08-23) with binary 1b5bfb requiring
   glib/2.84.Z (unpinned, dynamic). Full graph resolves with errors=none.

2. **Profile match**: `conan graphite --format=json` shows all dependency
   binaries (libsigc, glibmm, cairomm, pango, harfbuzz, glib, fontconfig) in
   Cache/Cache for the pangomm-cxx17 profile.

3. **conan create**: Successfully built pangomm package (f610782...), meson
   configure/build/install gated through. Test package compiled and linked.

4. **ABI verification**: cairomm-1.16.pc → Version 1.16.2, glibmm-2.68.pc →
   2.68.2, giomm-2.68.pc → 2.68.2, libcairomm-1.16.so → exists.

5. **Runtime block**: cairomm binary musl loader symbol resolution failure.
   Symbol exists in .dynsym but musl loader cannot resolve.

## Resolution

**Short-term**: conan create succeeds. test_package compiles and links. The
runtime execution is blocked by cairomm published binary musl loader
compatibility, which is an external dependency environment issue.

**Medium-term**: Publish cairomm/1.16.2 binary with OHOS musl loader compatible
ELF structure, or verify the runtime environment can load the shared library.
Consider adding llvm-objcopy --remove-section .codesign in the test_package
test() prior to running (if the codesign section causes the issue).

**Long-term**: Ensure ohpcd published binary ELF structures are compatible with
OHOS musl dynamic linker. The .codesign section may interfere with symbol
resolution.

## Verification

```bash
# Check harfbuzz new binary glib dependency
conan list 'harfbuzz/14.2.0.1:*' -r ohpcd

# Full pangomm build
conan create archives/p/pangomm/2.50.1 --profile:host=pangomm-cxx17 --build=missing

# Test compilation (build+link, runtime may be environment-blocked)
cd test_package && clang++ test.cpp ... -o test_probe
```

## b_evidence_search Result

No existing pangomm knowledge drafts found. E258 (clang toolchain) not applicable.
This is a new finding documenting the full pangomm adaptation closure.

---

## r14 补正（2026-08-25）：cairomm/1.18.0 ABI 兼容实证

### 上游测试核验

pangomm 2.50.1 `tests/` 目录仅有 autotools `Makefile.am`，无 `meson.build`
入口；顶层 meson.build 无 `test()` 注册（subdir 仅
tools/extra_defs_gen、pango、MSVC_NMake/pangomm、pango/pangomm、
docs/reference）。**上游 meson 测试 = 0 个**，不虚构数量。

test_package 提供 4 项消费者检查（Pango::init、FontDescription、
AttrList 默认构造、PANGOMM_MAJOR_VERSION），r13/r14 运行均
`pangomm 2.50.1: all 4 checks passed`。

### cairomm 1.18.0 vs 1.16.2 对比结论

| 验证项 | cairomm/1.16.2 (r12) | cairomm/1.18.0 (r13/r14) |
|--------|----------------------|--------------------------|
| `cairomm-1.16.pc` | ✅ Version 1.16.2 | ✅ Version 1.18.0 (≥1.15.1) |
| `libcairomm-1.16` | ✅ | ✅ |
| Meson `dependency('cairomm-1.16')` | ✅ | ✅ |
| conan create / test_package 编译链接 | ✅ | ✅ |
| **test_package 运行时 (OHOS musl loader)** | ❌ `FontOptions symbol not found` | ✅ 全部通过 |

**根因**：1.16.2 发布 binary 的 ELF 结构与 OHOS musl 动态加载器不兼容
（符号存在于 .dynsym 但 loader 无法解析，移除 .codesign + 补 libc++ 路径均无效）；
1.18.0 发布 binary 无此问题。**结论：cairomm/1.18.0 是 pangomm 2.50.1
在 OHOS C++17/libc++ profile 下的可用依赖，recipe 固定 1.18.0，不恢复 1.16.2。**

### r14 门禁结果

- conan-verify：G1/G2/G3/G4/L2/L4/L5 全部 PASS（补 test_package/MANIFEST.yml 后 G1 通过）
- finish W2/W3：本地 CI 卡在 JC junky check——**其他包遗留文件**
  （isa-l_crypto/conandata.yml.orig、middleclass/conandata.yml.ghfast-bak、
  swift-corelibs-blocksruntime/.staging-verified）被全仓扫描拦截，非 pangomm
  可修复，属仓库级外部阻塞。
