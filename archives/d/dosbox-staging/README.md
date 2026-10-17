# DOSBox Staging

DOSBox Staging is a modern continuation of DOSBox focused on accuracy,
usability, audio quality, and maintainable platform support.

## OHOS adaptation

- Builds the official 0.82.2 release with Meson and C++20.
- Keeps SDL2_net, libslirp, FluidSynth, and mt32emu enabled.
- Uses the validated SDL2 texture renderer path and explicitly disables the
  desktop OpenGL backend until an OHOS `gl` provider satisfies the upstream
  desktop-GL contract.
- Disables Linux-only ALSA auto-detection and optional XInput2 integration.
- Uses the published release tag commit as the Git-hash provenance fallback
  because the official source archive does not contain `.git` metadata.
- Requires 23 independently registered upstream Meson tests to finish with
  `OK` and the intentional `gtest example` failure to finish with
  `EXPECTEDFAIL` before a validation run can pass.

## Dependencies

The selected feature set depends on IIR1, opusfile, SDL2, zlib, libpng,
SpeexDSP, SDL2_net, libslirp, FluidSynth, and mt32emu. Their Conan references
are pinned in the version recipe.

## References

- Upstream: https://github.com/dosbox-staging/dosbox-staging
- Release tag: `v0.82.2`
- Contest version: `0.82.2-r1`
- Detailed path-C evidence: `0.82.2-r1/reports/high-difficulty-evidence.md`
- Test framework/toolchain Wiki source: `0.82.2-r1/reports/test-framework-toolchain-wiki.md`
