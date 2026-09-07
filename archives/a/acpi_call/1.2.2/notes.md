# acpi_call 1.2.2 HarmonyOS adaptation notes

## Scope

- Package path: `archives/a/acpi_call/1.2.2`
- Branch: `feat/acpi_call-1.2.2`
- Issue: 待补

## W0 dependency check

acpi_call has **no Conan dependencies** — it depends only on Linux kernel headers.

However, this is the fundamental blocker: **Linux kernel headers are not available as a Conan package in the OHPCD registry**, and the HarmonyOS sysroot does not include Linux kernel headers (`linux/module.h`, `linux/acpi.h`, etc.).

## Source and build-system analysis

- Source URL: `https://codeload.github.com/nix-community/acpi_call/tar.gz/6ad1e676dbfb5dcb1ec1f973c10ef5c57ffb4069`
- SHA256: `dc9a762941f68de82f62aee438894d2fecf10b3947b24fd649d38aac1edb9b80`
- Upstream repo: https://github.com/nix-community/acpi_call (maintained fork, VERSION=1.2.2), https://github.com/mkottman/acpi_call (original, inactive since 2013)
- License: GPL-3.0-or-later
- Build system: **Kbuild** (Linux kernel build system)
  - `Makefile`: `obj-m := acpi_call.o`
  - `make KDIR=/lib/modules/$(uname -r)/build`
- Source files:
  - `acpi_call.c` (449 lines in the pinned upstream commit) — the kernel module implementation
  - `VERSION` — contains `1.2.2`
  - `dkms.conf.in` — DKMS template
  - `examples/` — shell scripts for GPU switching (ASUS, Dell, Alienware)
  - `support/` — helper files

## What acpi_call does

acpi_call is a Linux kernel module that:

1. Creates `/proc/acpi/call` (procfs entry)
2. Accepts ACPI method names + arguments written to that file
3. Calls `acpi_evaluate_object()` in the kernel
4. Returns the result (integer, string, buffer, or package) via read

Common use cases:
- Switching between integrated and discrete GPUs (NVIDIA Optimus)
- Battery charging threshold control
- Fan speed management on laptops

## Why it cannot build on HarmonyOS

### Compile-time blocker

The C source `acpi_call.c` includes:

```c
#include <linux/module.h>       // MODULE_LICENSE, module_init, module_exit
#include <linux/kernel.h>       // printk, KERN_ERR
#include <linux/version.h>      // LINUX_VERSION_CODE, KERNEL_VERSION
#include <linux/proc_fs.h>      // proc_create, proc_dir_entry
#include <linux/slab.h>         // kmalloc, kfree
#include <linux/uaccess.h>      // copy_from_user
#include <linux/acpi.h>         // acpi_get_handle, acpi_evaluate_object
```

These headers are part of the Linux kernel source tree, not glibc or any
standard libc. They are only available when:

1. The full Linux kernel source tree is present at `/lib/modules/$(uname -r)/build`
2. The kernel was configured with `CONFIG_MODULES=y` and `CONFIG_ACPI=y`

HarmonyOS (OHOS) does not ship:
- Linux kernel headers for external module compilation
- The `Kbuild` infrastructure needed to compile `.ko` modules
- Any equivalent to `/lib/modules/*/build`

### Runtime blocker (if it could compile)

Even if compilation were somehow made possible:

1. `acpi_root_dir` — the module declares `extern struct proc_dir_entry *acpi_root_dir` which is a Linux kernel global. This symbol does not exist in the HarmonyOS kernel.
2. `acpi_evaluate_object()` — the core ACPI call function is not exported by HarmonyOS kernels.
3. `/proc/acpi/call` — the procfs interface requires an ACPI-aware kernel.
4. `module_init` / `module_exit` — kernel module loading requires `insmod`/`modprobe` which may not be available or permitted on OHOS.

## Existing ACPI recipes in build_in_harmonyos

| Recipe | Type | Status | Notes |
|--------|------|--------|-------|
| `acpitool/0.5.1` | Userspace CLI (Autotools) | Built OK | Runtime limitation: no `/proc/acpi`, `/sys/bus/acpi` |
| `acpica/20251212` | iASL compiler tools | Built OK | Userspace tools, no kernel dependency |
| `acpica-unix/20260408` | ACPICA Unix build | Built OK | Userspace tools |
| `acpid/2.0.34` | ACPI daemon | Present | Userspace daemon |
| `acpi-override/0.1+nmu2` | ACPI override | Merged PR !5787 | Userspace helper |
| **acpi_call/1.2.2** | **Kernel module** | **BLOCKED** | **Requires kernel headers** |

The difference: all other ACPI recipes are **userspace** programs that link against libc and (optionally) libacpi or read from sysfs/procfs. acpi_call is the only **kernel module** in the set — it requires Linux kernel headers and Kbuild, which are a fundamentally different build-time dependency.

## Potential paths to unblock

1. **Package Linux kernel headers for OHOS** — if HarmonyOS's kernel is based on Linux, its headers could theoretically be extracted and packaged as a Conan dependency. This would be a large effort.

2. **Cross-compile from a Linux host** — build the `.ko` on a Linux machine with matching kernel headers, then load on OHOS. Only works if OHOS kernel ABI matches.

3. **Port the functionality to userspace** — rewrite acpi_call's logic using the `acpica` userspace library (`acpica/20251212` is already adapted). This would not be a 1:1 port of acpi_call but would provide similar ACPI method call functionality without a kernel module.

4. **Accept the blocker** — export the pinned upstream source for inspection,
   verify its module contract in CI, and keep kernel-state verification blocked.
   This is the current approach.

## Upstream tests

acpi_call has **no test suite**. The only way to test it is:

1. `insmod acpi_call.ko` (load the module)
2. `echo '\_SB.PCI0.PEG1.GFX0.DOFF' > /proc/acpi/call` (call an ACPI method)
3. `cat /proc/acpi/call` (read the result)
4. `rmmod acpi_call` (unload)

This requires root, kernel module loading permission, and ACPI firmware support.

## Packaging notes

- The `VERSION` file in the repo root contains `1.2.2`, confirming the version.
- There are no tagged releases; the recipe uses a pinned commit (`6ad1e676`) from the nix-community fork.
- The fork at `nix-community/acpi_call` is the actively maintained version with version bumps and compatibility patches. The original `mkottman/acpi_call` has been inactive since 2013.
- The exported `acpi_call.c` is based on that pinned commit but is not byte-identical:
  - `parse_acpi_args()` now rejects inputs exceeding `MAX_ACPI_ARGS` before the fixed argument array can be exceeded.
  - `parse_acpi_args()` counts non-blank argument tokens, so separator and trailing whitespace no longer cause a false "too many arguments" result.
  - Error cleanup now sets `*args = NULL` after `kfree(*args)`, preventing a second free in `acpi_proc_write()`.
  - The argument array is zero-allocated so malformed whitespace cannot make error cleanup inspect uninitialized buffer fields.
  - `do_acpi_call()` handles a successful void method without dereferencing a missing result object and reports result-conversion truncation explicitly.
  - `acpi_result_to_string()` appends all formatted values through `vsnprintf()` with the remaining destination size, eliminating unbounded `sprintf()` writes to `result_buffer`.
  - ACPI integer results are formatted as `unsigned long long` with `%llx`, preserving all 64 bits instead of casting through `int`.
  - Procfs reads and writes share a mutex so concurrent access cannot race on the static input, temporary, and result buffers.
  - The recipe explicitly exports this locally hardened source with `exports_sources`, copies it to `package/src/acpi_call.c`, and test_package checks that packaged file; `conandata.yml` records upstream provenance rather than the local-file digest.
  - The parser and result-formatting defects plus these hardening changes should be reported to nix-community/acpi_call.

## Path B knowledge draft

The reusable Path B learning has been recorded as a paired draft:

- `knowledge/drafts/DRAFT-acpi_call-kbuild-source-contract-6499.kv`
- `knowledge/drafts/DRAFT-acpi_call-kbuild-source-contract-6499.md`

The draft captures how to package a pinned, locally hardened Kbuild module source
when OHOS has no matching kernel build tree, run fail-closed source-contract
checks against the packaged file, and report upstream tests, static contracts,
and blocked kernel load/invoke evidence separately. It does not modify the
official knowledge graph or index and does not reserve an official E number.

## Next device or shadow CI command

The `.ko` cannot be built in OHOS CI. The package exports the safety-hardened
`src/acpi_call.c`, and `test_package` runs eleven static source/safety
assertions. Kernel load/invoke remains a real-device-only test and is not
claimed as passed.

```sh
# Would-be command (will fail with ConanInvalidConfiguration):
CI_PACKAGES="archives/a/acpi-call/1.2.2" zsh ci/conan/build_and_test.sh
```
