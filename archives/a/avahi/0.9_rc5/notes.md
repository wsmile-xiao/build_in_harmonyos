# avahi 0.9_rc5 HarmonyOS PC adaptation notes

## Status

Core-library adaptation is complete and **locally verified**. `conan create`
succeeded on the OHOS aarch64 profile: dependencies resolved and downloaded
from the ohpcd registry, autogen.sh → configure → make → install all passed,
and the test_package compiled, linked, and ran (`Avahi test passed`).

- Package reference:
  `avahi/0.9_rc5#64fe4a50e49e9f1198d19807793c8ee1:21b17f8b2bc0e9511e276e3d57a23893067cefe5`
- Profile: `ci/conan/profiles/ohos-aarch64` (os=OHOS 6.0, arch=armv8,
  clang 15, libc++, cppstd 17, Release)
- Conan 2.29.1

A native/real-hardware shadow-CI run was **not** performed here; final
verification should come from CI on an OHOS worker after a PR is opened.

## Upstream and scope

- Source: Avahi tag v0.9-rc5.
- Archive SHA256: 5b0a9d88110b0fc8aaafc5cc0a26e83e7d2a4aca3a36bc27c9b626db7ead27b0.
- Build system: Autotools. The GitHub tag archive contains configure.ac and
  autogen.sh but no generated configure script.
- Package output: libavahi-common and libavahi-core (the base mDNS/DNS-SD
  libraries) plus their public headers.
- Excluded: daemon, client, GLib/GObject wrappers (avahi-glib), compat
  libdns_sd/howl, utilities, UI/language bindings, libevent, Qt, GTK,
  introspection, documentation, NLS, D-Bus, and systemd integration.

avahi-common and avahi-core are in-tree sublibraries of the Avahi source.
Building only these two subdirectories follows the repository's existing
same-source split-package pattern (see the sibling avahi-glib package).

## W0 dependency check

Verified against the ohpcd remote with `conan download --only-recipe`
(R35 — `conan search` is unreliable for this registry):

    conan download automake/1.18       -r=ohpcd --only-recipe   # OK
    conan download libtool/2.5.4        -r=ohpcd --only-recipe   # OK
    conan download gettext/0.22.5.1     -r=ohpcd --only-recipe   # OK

These are the only dependencies the core libraries need — all three are
build tools for the autogen.sh bootstrap. The core libraries have no
external runtime `requires`: expat, libdaemon, dbus, and glib are only
pulled in by the daemon/client/glib components, which are excluded here.
(Those four were also confirmed available in ohpcd — expat/2.8.2.1,
libdaemon/0.14, dbus/1.14.10, glib/2.84.0.1 — for the sibling packages.)

## Build strategy

The recipe reuses the OHOS/HMFS workarounds proven by the same Avahi
v0.9-rc5 source in avahi-glib:

- run autogen.sh explicitly through `/bin/sh` with `NOCONFIGURE=1`
  (HarmonyOS refuses shebang script execution);
- stage relocatable Gettext and Libtool scripts with their Conan package
  data paths patched in (gettextize/libtoolize hardcode the build machine's
  absolute datadir);
- stage native C launchers for aclocal/automake (cross-UID HMFS policy
  rejects direct execution of the packaged Perl scripts);
- override `gettext_datadir` / `ACLOCAL_PATH` so gettextize finds its data
  in the relocatable Conan package;
- text-patch the generated configure to strip `umask 077` from the
  AS_TMPDIR mktemp step (HMFS refuses to write into the 2700+setgid temp
  dir, otherwise config.status fails with "Permission denied");
- select CC/CXX from the Conan profile (`tools.build:compiler_executables`,
  keys `c`/`cpp`) rather than an HMFS cc wrapper;
- build serially in dependency order (avahi-common, then avahi-core);
- replace the restricted platform install helper with a cp/mkdir shim for
  automake batch header installs (the HMBS install shim only accepts
  single-file two-arg calls).

The package is static by default. Its public Conan target links
avahi-core then avahi-common (left-to-right symbol resolution) and exposes
the `avahi-core` pkg-config name.

## Tests

test_package (`test.c`) links against the packaged core libraries and
exercises the public avahi-common API:

- `avahi_address_parse("127.0.0.1", AVAHI_PROTO_INET, &addr)`
- `avahi_address_snprint(buf, sizeof(buf), &addr)` and asserts the
  round-tripped string equals `127.0.0.1`.

Observed output during `conan create`:

    Avahi address test: 127.0.0.1
    Avahi test passed

## Validation performed here

- ohpcd remote configured and reachable;
- W0 recipe downloads for the three build tools from ohpcd;
- full `conan create` on the OHOS aarch64 profile (build + package +
  test_package) — PASSED;
- package contains libavahi-core, libavahi-common, and their public headers.

Not performed: real-hardware/shadow CI, PR submission, `conan upload`.

## Re-run command

From the repository root:

    conan create archives/a/avahi/0.9_rc5 \
        -pr:h=ci/conan/profiles/ohos-aarch64 \
        -pr:b=ci/conan/profiles/ohos-aarch64 \
        --build=missing

CI form:

    CI_PACKAGES="archives/a/avahi/0.9_rc5" zsh ci/conan/build_and_test.sh

## Iron-rule compliance

- R26: system-name libraries built static (`--enable-static --disable-shared`).
- R32: `settings.os in ("Linux", "OHOS")` in validate().
- R33: CC/CXX taken from the Conan profile, not bare shell variables.
- R28: basic Autotools layout via explicit configure/make.
- Dependency versions verified present in ohpcd (no `@ohpcd/stable`
  pseudo-channel — the registry uses plain `name/version`).
