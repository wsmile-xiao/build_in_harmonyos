# alsa-lib 1.2.16 adaptation notes

## Current state

The recipe is adapted from the existing alsa-lib 1.2.16.1 recipe: the seven
scoped portability patches apply to the 1.2.16 sources with the same semantics
(verified with `git apply --check`; only hunk line offsets differ).

## Source and extraction boundary

The recipe consumes the official 1.2.16 release archive with SHA256
`122b1e3166d55fe19bcde656535d7a36f2ab10e66c72c6ad2f43f20ffded0a96`.
It validates every tar member before extraction. The release's only symbolic
link, `include/alsa -> .`, is replaced by an independently hashed real-file
tree so source copies remain valid on HMDFS.

The generated Autotools release files are present in the official archive.
The recipe applies seven scoped portability patches: OHOS triplet recognition,
an unversioned Libtool output override, a feature-tested thread-cancel path,
materialized include handling, writable `config.status` temporary directories,
and a readable zero source for OHOS null capture.

## Build and package contract

The standard Conan `shared` option selects mutually exclusive Autotools shared
or static modes. Static `fPIC=True` preserves the single compiler `-fPIC` added
by Conan while removing the incompatible Libtool `--with-pic` configure option.
The test package then links the static archives into a DYN ELF under
`--whole-archive -shared -Wl,-z,defs` as an internal artifact check.

OHOS shared packages contain real unversioned `libasound.so` and
`libatopology.so` files plus `aserver`. Static packages contain
`libasound.a`, `libatopology.a`, and the static `aserver`, with no ALSA shared
objects. Package metadata is made relocatable and checked through CMakeDeps and
PkgConfigDeps consumers.

Every linked target ELF passes through the native compiler/signing wrapper.
Compile and sign TSV rows bind the pre-sign hash, output path, post-sign hash,
and the unique non-empty `.codesign` section. The final package signing JSON is
re-read by the test package.

## Mode-specific upstream build handling

Automake registers only `test/lsb/config` and `test/lsb/midi_event`. Their
sources, inputs, and PASS rules are unchanged. Both run under an external
180-second timeout and must produce the exact two-file `.trs` set.

The root test directory also declares 19 unregistered `check_PROGRAMS`.
Shared mode builds all 19. `oldapi.c` deliberately requests the versioned
symbol `snd_pcm_hw_params_get_access@ALSA_0.9`; a static archive exports the
ordinary symbol rather than the shared version node. Static mode therefore
omits only this build-only shared-version probe and still builds the remaining
18 programs. Neither registered upstream test is removed or modified.

Libtool places linked test ELFs in `test/lsb/.libs` for shared mode and directly
in `test/lsb` for static mode. Likewise, PCM plug-in objects live under
`src/pcm/.libs` in shared mode and `src/pcm` in static mode. The recipe chooses
these paths by package mode, then applies the same hash and codesign checks. It
does not disable the checks when the path changes.

## Test accounting

The logical test inventory is:

- 2 official upstream Automake entries;
- 6 consumer behavior flows;
- 2 component consumers;
- 3 package workflows.

This is 13 independent entries. Shared/static reruns validate artifact modes
and are not added together. The 19 root build programs, 60 public ABI address
probes, signing operations, metadata checks, and internal static PIC link are
not additional test cases.

## Target evidence

To be filled after the local conan W3 verification run on the 1.2.16 recipe
(shared and static modes, r35 driver, exact test/consumer pass sets).
