# avahi-glib 0.9_rc5 HarmonyOS adaptation notes

## Status

Adaptation is complete. A frozen single-package shadow CI run passed on the
OHOS device on 2026-08-24.

## Upstream and scope

- Source: Avahi tag v0.9-rc5.
- Archive SHA256: 5b0a9d88110b0fc8aaafc5cc0a26e83e7d2a4aca3a36bc27c9b626db7ead27b0.
- Build system: Autotools. The GitHub tag archive contains configure.ac and
  autogen.sh but no generated configure script.
- Package output: libavahi-glib, libavahi-gobject, and their required in-tree
  libavahi-client and libavahi-common libraries.
- Excluded: daemon, core, utilities, UI bindings, language bindings, libevent,
  Qt, GTK, introspection, documentation, NLS, and systemd integration.

avahi-glib is an upstream sublibrary rather than a standalone source project.
Building its four dependent subdirectories follows the repository's existing
same-source split-package pattern and avoids adding a separate dependency
adaptation to this change.

## W0 dependency check

The following commands succeeded against the ohpcd remote on 2026-08-24:

    conan download glib/2.84.0.1 -r=ohpcd --only-recipe
    conan download dbus/1.14.10 -r=ohpcd --only-recipe
    conan download expat/2.8.2.1 -r=ohpcd --only-recipe
    conan download automake/1.18 -r=ohpcd --only-recipe
    conan download libtool/2.5.4 -r=ohpcd --only-recipe
    conan download gettext/0.22.5.1 -r=ohpcd --only-recipe

A full Conan graph resolution also found libffi/3.4.4, pcre2/10.45, and
zlib/1.3.1.1 through GLib; all three recipes resolved from ohpcd.

No dependency library needs a separate adaptation before this package.

## Build strategy

The recipe reuses the OHOS/HMFS workarounds already exercised by the same
Avahi v0.9-rc5 source in avahi-compat-libdns_sd:

- run autogen.sh explicitly through the platform-provided shell;
- stage relocatable Gettext and Libtool scripts with their Conan package data
  paths;
- generate dbus-1.pc and GLib component pkg-config metadata from Conan;
- stage native launchers for GLib's Python code generators so the hard-coded
  glib-genmarshal and glib-mkenums commands run on HMFS;
- stage task-owned Automake launchers so gettextize can invoke aclocal and
  automake when cross-UID Conan cache scripts cannot execute directly;
- select CC and CXX from the Conan profile rather than the HMFS-installed cc
  wrapper;
- remove the generated configure temporary-directory umask pattern that fails
  on HMFS;
- build serially in dependency order;
- replace the restricted platform install helper for automake multi-file header
  installs.

The package is static by default. Its public Conan target links
avahi-gobject, avahi-glib, avahi-client, and avahi-common in that order and
propagates GLib/GObject headers and libraries plus the D-Bus link requirement
to consumers.

## Reusable knowledge draft

This adaptation adds a paired draft for the failure pattern that required the
most recipe-specific work:

- `knowledge/drafts/E337-draft-wxjshr-avahi-glib-bootstrap.kv`
- `knowledge/drafts/E337-draft-wxjshr-avahi-glib-bootstrap.md`

The draft documents how an OHOS Conan recipe can build a task-local Autotools
bootstrap closure when cross-UID HMFS policy rejects direct execution of
packaged shell, Perl, and Python tools and the same tool packages contain
non-relocatable Gettext or Libtool data paths. It also records the important
Avahi exception where `autogen.sh` reads `gettextize` as shell text, so that
specific command cannot be replaced by an ELF launcher.

This is submitted as a Path B contribution candidate. It does not modify the
formal knowledge graph or its indexes, and final classification remains subject
to maintainer review.

## Tests

Upstream declares one test in avahi-glib/Makefile.am:

    make -C avahi-glib check

glib-watch-test exercises watch and timeout dispatch through a GLib main loop
and does not require a running avahi-daemon. avahi-gobject has no upstream TESTS
target.

The test_package adds eight consumer assertions covering:

- creation of a dedicated GMainContext;
- creation and access of AvahiGLibPoll;
- timeout creation and callback dispatch;
- GaClient GType registration and GObject inheritance.

## Validation

Completed locally:

- official source download and SHA256 verification;
- source and build-system inspection;
- exact W0 recipe downloads from the ohpcd registry;
- recipe and test Python syntax checks;
- YAML parsing and static contract checks.

A native build was not attempted on Windows because the target recipe only
supports Linux/OHOS and this host has no WSL or OHOS toolchain.

Completed by frozen single-package shadow CI:

- commit: 8d7447081cfa5a26aad7d00f2b9489143d151a70;
- snapshot SHA256:
  402a53e0a6bef01f43c2d193d97fa2d90ff3ac28d7660d2955d3abd94271df2e;
- run root:
  /storage/Users/currentUser/ohpc-ci-shadow/runs/8d7447081cfa-20260824T100458Z-run-56003;
- setup_rc=0 and build_rc=0;
- L0 passed, L1 passed, L2 skipped for a library with no bin directory,
  L4 passed with no patches, and L5 passed with library artifacts;
- upstream make check: 1 discovered, 1 executed, 1 passed;
- test_package: 8 discovered, 8 passed;
- package reference:
  avahi-glib/0.9_rc5#fa9bdccd72c89daddfcf3e28e87d6e4b:cf21a5c386cea84476e1cc5c9f9f86949e86123e#b187023e46acab8e5d1be177d66c9726;
- build summary: Total 1, Success 1, Failed 0;
- setup log SHA256:
  20d602bca8da9ae7fb07ccf942708eec48c71ea6d7f0a79;
- build log SHA256:
  127e48d2b3ff55441c5ef3f744f6a38e1ef70f899e38985c0d09643131dd1f66.

The runner's optional curl pre-download step was unavailable, but Conan fetched
the verified source and all dependencies successfully. This did not affect any
gate.

## Re-run commands

From the repository root on the OHOS worker:

    CI_PACKAGES="archives/a/avahi-glib/0.9_rc5" zsh ci/conan/build_and_test.sh

Equivalent direct project form if the runner expects package/version:

    bash ci/conan/build_and_test.sh avahi-glib/0.9_rc5

Shadow CI:

    /path/to/run-ohos-shadow-ci.sh archives/a/avahi-glib/0.9_rc5

Confirmed evidence:

- W0 reports all six dependencies available;
- make -C avahi-glib check reports 1 passed and 0 failed;
- test_package reports 8 of 8 assertions passed;
- Build Summary reports Total: 1;
- package contains libavahi-glib, libavahi-gobject, libavahi-client,
  libavahi-common, and their public headers.
