# rvvm

RVVM is a self-contained RISC-V virtual machine written in C (C11), featuring a
tracing JIT, multicore support, PCI/NVMe devices, userspace networking and an
embeddable public API (`rvvmlib.h`).

## Package contents

- Static library: `librvvm_static.a`
- Public headers: `include/rvvm/rvvmlib.h`, `include/rvvm/fdtlib.h`,
  `include/rvvm/devices/*.h`
- CLI runner: `bin/rvvm`
- License: GPL-3.0 OR MPL-2.0 (dual)

## OpenHarmony adaptation

- Self-contained build; no external Conan dependencies (only libc/libm/pthread).
- Disables the X11/SDL framebuffer and the JNI binding (absent on HarmonyOS PC).
- Keeps RV64/RV32, the arm64 RVJIT backend, PCI, FDT and userspace networking.
- Ships the static library only — the upstream shared library has no DT_SONAME
  and static linking is safer for embedding on OHOS.
- The upstream `make test` needs an external `riscv-tests.tar.gz`; the packaged
  consumer test instead exercises the public API (create machine, RAM I/O, opts).

## Usage

```c
#include <rvvm/rvvmlib.h>

rvvm_machine_t *m = rvvm_create_machine(RVVM_DEFAULT_MEMBASE, 0x10000000, 1, true);
rvvm_start_machine(m);
/* ... */
rvvm_free_machine(m);
```

Upstream: https://github.com/LekKit/RVVM
