# GraalVM Community JDK 25.0.3 Adaptation Notes

## Version Identity

- Conan reference: `graalvm/25.0.3`
- Java version: `25.0.3`
- GraalVM release: `25.1.3`
- Upstream artifact root: `graalvm-community-25.1.3+9.1`
- Architecture: Linux aarch64 input, OpenHarmony armv8 output

The upstream GraalVM release number and the bundled Java version are distinct.
The task version follows the Java version exposed by `java -version` and
`native-image --version`.

## Dependency Closure

The only external Conan dependency is `freetype/2.14.3`. W0 resolved its exact
OHOS armv8 binary from `ohpcd` with `--build=never`; all graph nodes had an
empty `info_invalid`. A known published `libgcrypt/1.12.2` control resolved in
the same isolated environment. gcompat 1.1.0 and zlib 1.3.2 are official source
inputs built privately inside this recipe, not hidden Conan dependencies.

Issue #1085 also names `xorgproto/2025.1` and `giflib/6.1.3` as prerequisites.
Both recipes are published, but neither supplies the X11 shared libraries or
display bridge required by XAWT, and giflib is not a direct dependency of the
five excluded desktop/audio ELFs. The submission declares a headless boundary
and does not represent the excluded X11/audio paths as supported.

## Adaptation Design

The official distribution contains 76 AArch64 ELF files and five symbolic
links. The recipe validates the exact link inventory and materializes each
link before packaging. It then removes five unsupported desktop/audio ELFs:

- `bin/jconsole`
- `lib/libawt_xawt.so`
- `lib/libjawt.so`
- `lib/libjsound.so`
- `lib/libsplashscreen.so`

The remaining 71 official ELFs are rewritten in place. The replacement names
are never longer than their GNU originals, so dynamic-string offsets and ELF
layout remain stable. The recipe rewrites `PT_INTERP`, `DT_NEEDED`, and GNU
version-file identities, then adds two private libraries:

- `libg.so`: gcompat 1.1.0 plus the OpenHarmony ABI patch. The patch is
  applied only inside this OHOS-targeted recipe and folds the target behavior
  directly into the patched source, without injecting platform-named
  preprocessor branches into gcompat.
- `libjz.so`: zlib 1.3.2 rebuilt as a private, versioned shared library

The 71 retained official ELFs, two private libraries, and two native launchers
produce 75 packaged ELFs. Every one is checked, self-signed, checked again, and
recorded in `share/graalvm/ohos-adaptation.json`. `lib/libjimage.so` receives
the private `$ORIGIN:$ORIGIN/server` RPATH needed for its loader closure, and
`lib/jspawnhelper` receives the private `$ORIGIN` RPATH needed when Java starts
native toolchain probes with `LD_LIBRARY_PATH` unset. The two retained `.real`
Native Image drivers receive package-relative private RPATHs for `libg.so` and
`libjz.so`; the two signed public launchers have empty RPATHs. Other upstream
RPATH values are preserved.

## Native Image

Both Native Image entry points are wrapped. The wrapper:

- uses a signed OpenHarmony AArch64 PIE launcher that resolves itself through
  `/proc/self/exe` and runs a same-directory Python companion in isolated mode
  through fixed CI app, HNP, and canonical OpenHarmony user-local interpreter
  paths;
- starts each signed real driver through an exact package-relative private
  RPATH for `libg.so` and `libjz.so`;
- removes Python, JVM-option, and loader-path injection variables before the
  real driver starts;
- fixes the active processor count at one and the Java heap at 1 GiB;
- copies the signed OpenHarmony AArch64 PIE launcher to `.t/ohos-clang`; in
  that mode the launcher pins clang temporary files to its own directory and
  execs `/data/service/hnp/bin/clang`;
- injects the OpenHarmony compatibility header and private `libg.so`;
- serializes the fixed `./.t` scratch path, validates its ownership and mode,
  refuses every pre-existing path instead of deleting unowned contents, and
  removes only the directory created by the current invocation;
- opens coordination locks read-only, creates them group-shareable for HMDFS
  UID drift, and accepts only current-UID or supplemental-group regular files
  with one link and no permissions for other users;
- builds into a private same-filesystem staging directory, serializes the
  destination directory, and commits with `renameat2`; existing targets are
  exchanged atomically so failures restore the original inode and metadata;
- forwards HUP, INT, and TERM to the real driver process group and returns the
  conventional signal exit status without leaving a child or staging file;
- rewrites, signs, fsyncs, and atomically installs the generated executable;
- publishes the exact signed `libg.so` as a complete file with atomic
  `renameat2(RENAME_NOREPLACE)`, verifies its commit identity, and rejects a
  different or concurrently replaced existing file.

The directory locks serialize all packaged wrapper invocations. POSIX path
rename APIs do not provide an inode-compare-and-swap primitive for unrelated
writers that ignore those locks. The defensive identity checks therefore
restore an observed third-party inode when the exchange window permits it,
retain the recovery stage on ambiguity, and fail instead of deleting an
unrecognized path.

The generated executable has interpreter `/lib/ld-musl-aarch64.so.1`, RPATH
`$ORIGIN`, a single non-empty `.codesign` section, and no fixed GNU loader or
GNU SONAME dependency.

Buildbot PR validation runs Python from `/data/app/bin/python3` while some
interactive devices expose it under `/data/service/hnp/bin/python3` or the
canonical user-local prefix. The native launcher trusts only these fixed paths
and accepts a candidate only after confirming that it is an executable ELF, so
shell-wrapper interpreter paths and `PATH` injection remain blocked while the CI
runtime path is accepted. The reusable launcher rule is recorded as
`knowledge/doc/E215.md`.

## Supported Boundary

Core Java, `javac`, JAR tooling, and Native Image are validated with
`LD_LIBRARY_PATH` unset. Headless AWT and font-manager loading are supported
through the declared `freetype/2.14.3` dependency and the packaged
`conf/fonts/fontconfig.HarmonyOS.properties`, which maps logical fonts to the
target's `/system/fonts` HarmonyOS and Noto files. The consumer test does not
set `sun.awt.fontconfig`, so it also verifies automatic discovery from
`os.name=HarmonyOS`. X11 AWT/JAWT, sound, splash-screen, and jconsole are
intentionally not shipped. The compatibility layer parses passwd and group
streams, provides the glibc C-locale ctype table contract, and maps flattened
`dlinfo` namespace queries to `LM_ID_BASE`; it does not claim to be a complete
glibc implementation.

## Test Contract

The official binary distribution contains no runnable upstream test harness.
The Conan consumer package therefore defines nine independent flows covering
version identity, Java compilation/execution, structured adaptation-report
validation, isolated font-manager loading, headless AWT, JAR creation and
execution, Native Image creation/ELF closure/execution, and direct gcompat ABI
coverage. A separate transaction flow deterministically injects HUP, INT, and
TERM at staging creation, sidecar publication, and target exchange. It also
injects a directory-fsync failure after commit for both new and existing
outputs and proves complete output, libg.so, and stage rollback. It injects
third-party destination replacement both before rollback and inside the
rollback check-to-rename window, preserving the replacement content and inode
while retaining a recoverable old-output stage when needed. The finalizer also
fails closed when rollback sees a third-party replacement at the installed
target path, leaving that replacement untouched and retaining the prior output
outside the unconditional temporary cleanup set. Output-stage and scratch
cleanup are bound to the directory identities created by the current invocation,
cleanup failure still releases all directory locks, and the lock parent/output
parent identities are retained across the publish transaction.
The finalizer copies from the same O_NOFOLLOW stage inode accepted by the
wrapper and installs the signed postimage with a same-directory exchange CAS
that also binds the signed temporary file identity before publication.
When the transaction flow runs against the installed `native-image.py`
companion, it resolves the finalizer from the installed
`libexec/graalvm-ohos` support directory, matching the packaged wrapper's
runtime layout instead of assuming a source-tree-only sibling file.
The flow also rejects a concurrent replacement of an existing matching libg.so
and a same-UID replacement of the finalizer's staged input after the wrapper's
validation step. The manifest declares 504 baseline logical assertions,
including target OS,
font-override absence, the exact automatically discovered fontconfig path, and
both private Native Image driver RPATHs. The 2026-08-04 target run executed a
previous 438-assertion baseline and remains historical after the current
rollback-target replacement and symlink-race extensions; the next target W3
must report the current baseline minus any platform-denied symlink-only
assertions. The checks
cover both signed public launchers, fixed-path isolated Python startup,
sanitized JVM and loader environments, transactional HUP/INT/TERM handling,
pre-existing scratch preservation, identity-bound cleanup, reserved output
rejection, signed-output exchange identity preservation, destination
compare-and-swap protection, exact argv forwarding, ordinary/signal exit codes,
and concurrent lock serialization.

The exact assertion decomposition covers the composite launcher failure
contracts, symlink-skip accounting, transactional rollback cases, native-image
signal handling, and gcompat ABI closure verified by the test package.
---

**编译结束**: 2026-08-04
**最终状态**: built
