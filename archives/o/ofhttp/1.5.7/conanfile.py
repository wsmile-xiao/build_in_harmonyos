#!/usr/bin/env python3
"""Conan recipe for ofhttp 1.5.7 — ObjFW's HTTP/HTTPS command line client.

ofhttp is not a separate upstream project: it lives in the ObjFW source tree
under ``utils/ofhttp`` and is built by the very same autotools + in-source
build as ``libobjfw1``.  This recipe therefore reuses the libobjfw1 /
libobjfwrt1 1.5.7 adaptation and packages *only* the ``ofhttp`` executable
together with its localization data.

Adaptation points (all inherited from the libobjfw1/libobjfwrt1 1.5.7 precedents):
  * the release tarball ships no pre-generated ``configure`` -> run ``autogen.sh``
  * ``automake --add-missing`` overwrites ``config.sub`` with the stock copy, so
    the ``ohos`` triplet has to be re-injected into every ``config.sub`` afterwards
  * ``config.guess`` does not know ``aarch64-linux-ohos`` -> pass --build/--host
  * ``config.status`` runs under ``umask 077``, which is unwritable in the OHOS
    sandbox -> rewrite ``umask 077`` to ``umask 022``
  * the in-source layout is mandatory: the top level Makefile ships in the
    tarball and configure generates ``buildsys.mk`` / ``extra.mk`` beside it

``build()`` also compiles and executes ObjFW's own test suite (the top level
``make check`` target), because ofhttp links the very same libobjfw/libobjfwrt
that the suite exercises.  A non-zero suite result, or a run that produced no
parsable summary, fails the build -- an unexecuted suite must never read green.

Deviation from the precedents: those two packages are libraries and were built
with ``--without-tls``.  ofhttp is an HTTP client whose HTTPS support lives in
``libobjfwtls`` (wired up through ``OFHTTP_LIBS`` by configure), so TLS is kept
enabled here via the OHOS adapted ``openssl/1.1.1w`` package — the OHOS sysroot
ships no OpenSSL headers of its own.
"""
import os
import re
from io import StringIO

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import copy, get
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps

# config.guess/config.sub in the 1.5.7 tarball predate OpenHarmony, so the
# canonical OHOS triplet has to be passed explicitly.
OHOS_TRIPLET = "aarch64-unknown-linux-ohos"

# configure's default prefix; the staging dir is appended with DESTDIR.
DEFAULT_PREFIX = "/usr/local"

# What ObjFW's test runner (src/test/OTAppDelegate.m) prints as its last line,
# e.g. "1242 tests succeeded, 0 tests failed, 0 tests skipped".
UPSTREAM_SUMMARY_RE = re.compile(
    r"(\d+)\s+tests?\s+succeeded,\s*(\d+)\s+tests?\s+failed,\s*(\d+)\s+tests?\s+skipped"
)


class OfhttpConan(ConanFile):
    name = "ofhttp"
    version = "1.5.7"
    description = "ofhttp — HTTP/HTTPS command line client shipped with ObjFW"
    license = "LGPL-3.0"
    homepage = "https://objfw.nil.im/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        # R32: this recipe is only meaningful for POSIX-like targets.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanException(
                f"ofhttp only supports Linux/OHOS, got os={self.settings.os}"
            )

    def requirements(self):
        # HTTPS support: ObjFW's libobjfwtls wraps a system TLS library and the
        # OHOS sysroot provides none, so use the OHOS adapted openssl package.
        self.requires("openssl/1.1.1w", transitive_headers=True, transitive_libs=True)
        # NOTE: Objective-C exceptions need _Unwind_RaiseException, which the
        # OHOS toolchain resolves from its own SDK libunwind (see the
        # exception note in manifest.yaml / notes.md).  The published
        # libunwind/1.6.2 package is deliberately NOT required here: LLVM
        # libunwind built that way exposes only the unw_* generic API, so it
        # cannot satisfy the EH personality and would shadow the SDK one.

    def build_requirements(self):
        # autogen.sh needs aclocal/automake/libtool; the tarball is bare.
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        # ObjFW must be built in-source (libobjfw1 precedent): the top level
        # Makefile is source provided and configure drops buildsys.mk/extra.mk
        # next to it, so an out-of-source build cannot resolve them.
        self.folders.source = "."
        self.folders.build = "."
        self.folders.generators = os.path.join(self.folders.build, "conan")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compiler_executable(self, language="c"):
        # Same access pattern AutotoolsToolchain uses internally, so OBJC
        # resolves to the very same driver that CC/CXX got.
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        return compilers.get(language) or "clang"

    def generate(self):
        # prefix= keeps the staged layout predictable:
        # <DESTDIR>/usr/local/bin/ofhttp.
        tc = AutotoolsToolchain(self, prefix=DEFAULT_PREFIX)
        # The toolchain PATH contains a stale `aarch64-unknown-linux-ohos-clang`
        # shim whose exec target is missing (exit 127).  autoconf's
        # AC_CHECK_TOOL prefers that triplet-prefixed name over plain `clang`,
        # and AutotoolsToolchain only pins CC/CXX, so OBJC/OBJCPP have to be
        # pinned by hand or configure aborts with
        # "Objective C compiler cannot create executables".
        env = tc.environment()
        objc = self._compiler_executable("c")
        env.define("OBJC", objc)
        # autoconf's own default for OBJCPP is "$OBJC -E"; pinning OBJCPP to the
        # bare driver makes the preprocessor sanity check compile instead of
        # preprocess, and configure then aborts with
        # 'Objective C preprocessor ... fails sanity check'.
        env.define("OBJCPP", objc + " -E")
        if str(self.settings.os) == "OHOS":
            tc.configure_args.extend([
                f"--build={OHOS_TRIPLET}",
                f"--host={OHOS_TRIPLET}",
            ])
        tc.configure_args.extend([
            "--enable-runtime",
            "--disable-shared",
            "--with-tls=openssl",
        ])
        tc.generate(env)
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()

    def build(self):
        self.run("./autogen.sh", cwd=self.source_folder)
        # autogen.sh runs `automake --add-missing`, which restores the stock
        # config.sub and drops the ohos entry, so re-inject it afterwards.
        self._patch_config_sub()
        # Must happen before configure runs. configure writes config.status from
        # a here-doc embedded in its own body, and the umask lives in that
        # here-doc:
        #     cat >>$CONFIG_STATUS <<\_ACEOF
        #     ...
        #     tmp=`(umask 077 && mktemp -d "./confXXXXXX")`
        # configure then executes config.status itself, so on HMDFS the 077
        # umask leaves ./confXXXXXX/subs1.awk non-executable and the build dies
        # with "Permission denied ... subs1.awk" / "could not setup config
        # files machinery" (the objfw/1.5.7 patches/0002-configure-hmdfs-umask
        # precedent; it patches `configure` because its tarball ships one).
        # Relaxing it here, in the generated configure, is the same fix.
        self._relax_umask()

        autotools = Autotools(self)
        autotools.configure()
        # configure re-emitted config.status, so relax the umask once more.
        self._relax_umask()

        # libobjfwrt1 precedent uses -j1: ObjFW's generated Makefiles declare
        # their own recursive ordering and are not reliably parallel safe.
        self.run("make -C src -j1", cwd=self.build_folder, env="conanbuild")
        self.run("make -C utils/ofhttp ofhttp -j1", cwd=self.build_folder,
                 env="conanbuild")

        # ofhttp is a thin front end over libobjfw/libobjfwrt, so the upstream
        # suite is what actually proves the port. Run it before staging.
        self._build_and_run_upstream_tests()

        # Stage the install tree, then copy only ofhttp out of it.
        stage = os.path.join(self.build_folder, "stage")
        self.run(f"make -C utils/ofhttp install DESTDIR={stage}",
                 cwd=self.build_folder, env="conanbuild")

    def package(self):
        stage = os.path.join(self.build_folder, "stage")
        bin_src = os.path.join(stage, DEFAULT_PREFIX.lstrip("/"), "bin")
        copy(self, "ofhttp", src=bin_src,
             dst=os.path.join(self.package_folder, "bin"),
             keep_path=False)

        # ofhttp reads its translations from <datadir>/ofhttp/localization.
        data_src = os.path.join(stage, DEFAULT_PREFIX.lstrip("/"), "share", "ofhttp")
        if os.path.isdir(data_src):
            copy(self, "*", src=data_src,
                 dst=os.path.join(self.package_folder, "share", "ofhttp"))

        # `make install` also drops ofhttp.1 next to the binary; shipping it
        # keeps the packaged CLI self-documenting instead of silently dropping
        # an upstream deliverable.
        man_src = os.path.join(stage, DEFAULT_PREFIX.lstrip("/"), "share", "man")
        if os.path.isdir(man_src):
            copy(self, "*", src=man_src,
                 dst=os.path.join(self.package_folder, "share", "man"))

        copy(self, "COPYING*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

        # Shipped executables must keep the executable bit.
        bin_dst = os.path.join(self.package_folder, "bin", "ofhttp")
        if os.path.isfile(bin_dst):
            os.chmod(bin_dst, 0o755)

    def package_info(self):
        # Executable package: expose the installed binary through PATH only.
        self.cpp_info.bindirs = ["bin"]
        if self.settings.os in ("Linux", "OHOS"):
            # ofhttp statically links libobjfw/libobjfwrt/libobjfwtls, libssl,
            # libcrypto and libunwind, so consumers only need the C runtime.
            # Keep the unwinder reachable for anything that links ofhttp's
            # own Objective-C exception personality.
            self.cpp_info.libs = []

    # ------------------------------------------------------------------ utils

    def _target_is_runnable(self):
        # Deterministic host/target comparison. The CI worker builds OHOS
        # natively, so the suite runs there; a Linux box cross-building for
        # OHOS can only compile it.
        return (str(self.settings_build.os) == str(self.settings.os)
                and self.settings_build.arch == self.settings.arch)

    def _build_and_run_upstream_tests(self):
        """Compile and execute ObjFW's own test suite.

        ObjFW ships its suite in ``tests/`` and wires it to the official entry
        point in the top level Makefile::

            check: tests
                ${MAKE} -C tests -s run

        ``tests/tests`` walks every ``- (void)testXxx`` method reachable from
        the compiled test classes (so a method inherited by a concrete
        subclass is executed once per class), prints
        ``<N> tests succeeded, <M> tests failed, <K> tests skipped`` and exits
        with ``M``.

        The suite is always compiled -- a compile failure is a genuine OHOS
        porting bug.  The run is only enforced when the build host can execute
        the target binaries, and an unparsable summary is treated as a failure
        so that a suite which never ran can never be mistaken for a green one.
        """
        self.run("make -C tests -j1", cwd=self.build_folder, env="conanbuild")

        if not self._target_is_runnable():
            self.output.warning(
                "ObjFW upstream suite compiled for os=%s arch=%s, but the build "
                "host (os=%s arch=%s) cannot execute it: skipping the run and "
                "claiming no pass rate."
                % (self.settings.os, self.settings.arch,
                   self.settings_build.os, self.settings_build.arch)
            )
            return

        log = StringIO()
        self.run("make check", cwd=self.build_folder, env="conanbuild",
                 stdout=log, stderr=log, ignore_errors=True)
        text = log.getvalue()

        match = UPSTREAM_SUMMARY_RE.search(text)
        if not match:
            raise ConanException(
                "ObjFW `make check` produced no parsable test summary, so the "
                "upstream suite cannot be considered executed. Tail of output:\n"
                + text[-4000:]
            )

        passed, failed, skipped = (int(group) for group in match.groups())
        executed = passed + failed + skipped
        # Machine-greppable line: this is the number the PR report quotes.
        self.output.info(
            "UPSTREAM_OBJFW_TESTS: executed=%d passed=%d failed=%d skipped=%d"
            % (executed, passed, failed, skipped)
        )
        if executed == 0:
            raise ConanException("ObjFW `make check` executed 0 test cases")
        if failed:
            raise ConanException(
                "%d of %d upstream ObjFW test case(s) failed on os=%s arch=%s"
                % (failed, executed, self.settings.os, self.settings.arch)
            )

    def _config_sub_roots(self):
        roots = {self.source_folder, self.build_folder,
                 os.path.dirname(self.build_folder)}
        return roots

    def _patch_config_sub(self):
        for root in self._config_sub_roots():
            for dirpath, _dirnames, filenames in os.walk(root):
                if "config.sub" not in filenames:
                    continue
                path = os.path.join(dirpath, "config.sub")
                with open(path, encoding="utf-8", errors="surrogateescape") as fh:
                    content = fh.read()
                if "ohos" in content:
                    continue
                # Two lists to extend: the plain OS list and the
                # <kernel>-<os> combinations used by the *-*- style block.
                content = content.replace(
                    "| palmos* | uclinux* |",
                    "| palmos* | ohos* | uclinux* |", 1)
                content = content.replace(
                    "linux-musl*- | ",
                    "linux-musl*- | linux-ohos*- | ", 1)
                with open(path, "w", encoding="utf-8",
                          errors="surrogateescape") as fh:
                    fh.write(content)

    def _relax_umask(self):
        for root in self._config_sub_roots():
            for dirpath, _dirnames, filenames in os.walk(root):
                for name in ("configure", "config.status"):
                    if name not in filenames:
                        continue
                    path = os.path.join(dirpath, name)
                    with open(path, encoding="utf-8",
                              errors="surrogateescape") as fh:
                        content = fh.read()
                    if "umask 077" not in content:
                        continue
                    with open(path, "w", encoding="utf-8",
                              errors="surrogateescape") as fh:
                        fh.write(content.replace("umask 077", "umask 022"))
                    os.utime(path, None)
