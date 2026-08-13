# W0 dependency report: p11-kit 0.26.2

- Issue: https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/2074
- Branch: `feat/p11-kit-0.26.2-2074`
- Result: COMPLETE; dependency-free configuration confirmed by Shadow CI.

## Required dependencies

None. The selected core configuration uses the bundled hash implementation and
64 precompiled closures.

## Optional dependencies intentionally disabled

- `libffi`: disabled; `closures=64` keeps the closure implementation available.
- `libtasn1`: disabled with `trust_module=disabled`; the trust extraction module
  is outside the dependency-free core required by p11-kit-server.
- `systemd`: disabled because HarmonyOS does not use systemd socket activation.
- `libintl`: avoided with `nls=false`.
- Documentation and shell completion generators: disabled.

The target recipe itself is expected to be absent from the Conan remote before
its first publication. That is not a dependency blocker because the recipe has
no `requires()` entries.

## Validation note

The Windows preparation host does not provide a Conan executable, so the build
was executed by the isolated HarmonyOS aarch64 Shadow CI runner. `conan create`,
four upstream tests, and the consumer test package all passed there.
