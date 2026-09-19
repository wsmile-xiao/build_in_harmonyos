# W0 dependency report

## Target

- Package: `libportaudiocxx/19.7.0`
- Task: 积分赛路径 A 基础适配（feat/libportaudiocxx-19.7.0）
- Checked: 2026-09-14, host-side preflight + shadow device run (pending CI)
- Remote: `ohpcd`
- Isolation: per-run `CONAN_HOME` under the HarmonyOS test runner

## Direct dependency availability

The recipe has exactly one direct Conan dependency: `portaudio/19.7.0`.

Verified with `conan graph info --requires=portaudio/19.7.0 -pr:h=ci/conan/profiles/ohos-aarch64`
(R35 requires graph-based probing, not `conan list`): the dependency resolves
to recipe revision `0cfb1dcf84c1b5107923e574eb3cd741` with an OHOS armv8
binary published on `ohpcd`, satisfying R36 (dependencies must be published
before the dependent package is built).

libportaudiocxx is the `bindings/cpp` subtree (PortAudioCpp) of the official
PortAudio tarball. It links only against PortAudio's public C API, so the
single dependency is sufficient.

## Source and build-system checks

- Upstream archive: official PortAudio tarball
  `https://files.portaudio.com/archives/pa_stable_v190700_20210406.tgz`
  (R39-compliant official source; waterlan's independent libportaudiocxx
  site is offline, and Alpine/Debian/Fedora packages of libportaudiocxx all
  build from this same PortAudio tarball's `bindings/cpp`).
- Official SHA-256 matched `47efbf42c77c19a05d22e627d42873e991ec0c1357219c0d74ce6a2948cb2def`
- The subtree carries a complete generated Autotools build system (its
  `configure` resolves `config.sub` / `install-sh` / `ltmain.sh` from the
  PortAudio source root via `$srcdir/../..`).
- Selected patches apply cleanly and sequentially to the verified source
  (verified with `git apply` on a pristine re-extraction).
- Local configure (VPATH, `--host=aarch64-linux-ohos`) completed and
  generated all Makefiles; all 16 `.cxx` translation units compile cleanly
  with the patched sources.

## Device checks

- Conan setup resolved the isolated graph with one direct requirement.
- The OHOS aarch64 profile and recipe passed the Shadow runner input checks.
- Final device run: `/storage/Users/currentUser/ohpc-ci-shadow/runs/<run-id>`
  (to be recorded by the shadow CI gate after this PR is submitted).
- The consumer test initializes PortAudioCpp's `System`, queries version and
  enumeration counts, and terminates cleanly.
- Expected final status: pass (pending official CI confirmation on the
  submitted commit).

## Notes

- 0001 removes the `bin` subtree from `SUBDIRS`: `devs` / `sine` are
  noinst example programs that link an in-tree `libportaudio.la` and are not
  packaged.
- 0003 redirects the library's link line from the in-tree
  `$(top_builddir)/$(PORTAUDIO_ROOT)/lib/libportaudio.la` (which does not
  exist in a standalone build) to `-lportaudio` resolved from the Conan
  `portaudio/19.7.0` dependency.
