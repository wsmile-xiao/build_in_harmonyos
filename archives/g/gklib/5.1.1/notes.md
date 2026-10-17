# gklib 5.1.1 adaptation notes

- The default library has no external Conan dependencies; `libm` is supplied by
  the target system C library/toolchain.
- Optional PCRE and OpenMP support is disabled to keep the dependency closure
  deterministic.
- The upstream `test/` directory defines ten command-line executables but no
  CTest registrations. `strings` and `gksort` are deterministic no-argument
  self-checks; both were rebuilt against the installed archive and passed on
  the OHOS target. The other eight programs require external input files, so
  they are recorded in the inventory but are not reported as executed tests.
- The package remains library-only: the packaging patch omits the upstream
  utility subdirectory from the install build, while W3 reconstructs the two
  eligible upstream self-checks directly from their unchanged sources.
- The consumer links the installed `GKlib` archive and verifies seven observable
  API results across memory, string, sorting, and integer-log helpers.
- A host Conan run first built the consumer under `build/bin` but attempted to
  execute it from the test-package working directory. The test recipe now
  verifies and resolves that build-folder path before `self.run`; the isolated
  offline rebuild passed with all seven consumer assertions.
- W3 r002 remains a signer-environment failure. W3 r003 separated the native
  signer's loader environment from the target probe environment and completed
  the 12-receipt transaction with upstream 2/2, state 3/3, consumer 1/1 and
  7/7 assertions, followed by release and postrelease absence readback.
