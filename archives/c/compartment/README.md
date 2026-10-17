# compartment

Compartment is a Linux process isolation toolkit. The zero-dependency core
provides `compartment-user` (Landlock plus seccomp plus environment sanitize,
rootless) and `compartment-root` (full namespace container, requires root)
with a shared profile format.

## OHOS adaptation

- Builds only the zero-dependency core tools from the upstream Makefile.
  The optional `compartment-bpf` module is not built: it needs libbpf,
  bpftool, libsodium, BTF and a 6.6+ kernel with BPF LSM, none of which the
  HarmonyOS PC worker provides.
- Uses the Conan-provided compiler and `make -j1`; installs with
  `make install PREFIX= DESTDIR=<package>` so the two binaries land in
  `bin/` with their man pages.
- Upstream tests are the shell suites behind `make test-quick`: the
  compartment-user filesystem/seccomp/env matrix and the child inheritance
  suite. The sandbox proxy and Claude CLI smoke suites need network access
  and external CLIs and are not run in the offline build.
- OHOS binaries are self-signed after build and after install, otherwise
  the HongMeng kernel rejects exec.

## Dependencies

None. The core tools are zero-dependency C11 with no Conan requirements.

## References

- https://github.com/nmicic/compartment
- Upstream tag `v1.3.0` is used for recipe version `1.3` (task naming).
