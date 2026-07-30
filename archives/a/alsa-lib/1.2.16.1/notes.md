# alsa-lib 1.2.16.1 adaptation notes

## Current state

The recipe completed a fresh shared and static Conan W3 directly on the
OpenHarmony PC target. Run r35 returned zero for the driver and both modes.
The two official upstream entries and all 11 independent consumers passed,
for a target-only logical result of 13/13 (100%). CI and publication status
are not claimed here.

## Source and extraction boundary

The recipe consumes the official 1.2.16.1 release archive with SHA256
`f740db7f488255944ffd4428416ee3390a96742856916433df468c281436480e`.
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

Fresh W3 r35 used frozen recipe input
`17dde268ec49738b2328000619068923d8c4f5659e531b26b056a9f4a78278ec`
and runner
`3409e512c1b3d8c8e5e3188373399264d986c14d601db4dafcab64594811d2d2`.
The shared and static logs have SHA256
`7bcf227d5c6d936a065c6e390c4d8bfc8fe759eec1966307e370b539dbedcc77`
and
`e7f1a23611ee476156a48cfff10377c93393f29799ce433ae0c0eac916b5578b`.

The downloaded 4,104,328-byte evidence bundle has SHA256
`cfe65995eec2d3912c967cbf0036976f44bd8b4ddecca26d8481870c788e2e75`.
Its validator accepted exact input hashes, zero exits, both two-file upstream
PASS sets, both 11-ID consumer PASS sets, unique signing rows, package evidence,
and every remote/local evidence hash. Failure, timeout, unexecuted, and unknown
terminal counts are zero.
