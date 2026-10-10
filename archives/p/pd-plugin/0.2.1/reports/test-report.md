# pd-plugin 0.2.1 test report

- Platform: HarmonyOS PC 6.0, aarch64
- Compiler: OHOS clang 15.0.4
- Conan profile: `ci/conan/profiles/ohos-aarch64`
- Upstream tests: 0 discovered, 0 run, 0 passed, 0 failed
- Adaptation tests: 1 run, 1 passed, 0 failed
- Consumer assertions: 20 run, 20 passed, 0 failed

The CI-equivalent `ci/conan/build_and_test.sh` pipeline completed with a 100%
package pass rate. Its destructive negative test moved the packaged `lib/`
directory away and confirmed that the consumer test then fails, demonstrating
that the test depends on the real packaged artifact.

The consumer test loaded `plugin~.pd_linux` with `RTLD_NOW`, invoked its Pure
Data setup entry, searched and loaded the packaged LADSPA `amp.so`, instantiated
`amp_mono`, processed a four-sample audio block, checked the exact samples, and
unloaded both shared objects cleanly.
