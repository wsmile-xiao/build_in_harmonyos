# abduco 0.6 adaptation notes

- Upstream: `https://github.com/martanne/abduco`, tag `v0.6`.
- Source archive SHA256:
  `647d0381418f43a38f861d151b0efb2e3458ec651914e7d477956768b0af9bb7`.
- Source transport uses the SHA256-verified ghproxy mirror.
- Build system: upstream Makefile.
- Conan dependencies: none.
- `export_sources()` is provided for Conan patch handling.
- `STRIP=true` is used during build and install because OpenHarmony MAC rejects
  the stripped binary.
- The consumer test executes `abduco -v` and asserts exit code 0 plus the
  `abduco-0.6` version string.
- The test does not use `can_run()` early return, so R34 correctly fails when
  the package binary is removed.
- Real-device verification:
  `conan-verify` passed and `build_and_test.sh` passed with L0/L1/L1e/L2/L4/L5.
