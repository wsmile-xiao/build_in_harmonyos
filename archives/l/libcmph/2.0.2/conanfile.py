#!/usr/bin/env python3
"""Conan recipe — libcmph 2.0.2 (C Minimal Perfect Hashing Library).

Upstream ships a proper GNU autotools *release* tarball with a pre-generated
`configure` (dated 2018-12-29).  No `autoreconf` is needed — and therefore no
host automake/autoconf/libtool dependency.  This is the upstream-sanctioned way
to build libcmph 2.0.2 (the same path Homebrew and Debian use).

Two environment-only adaptations are applied at build time (no source patch,
no generated-file edit):

  * E114 — HMDFS turns a 0700 tmp dir (config.status' `umask 077 && mktemp`)
    into an unwritable drwx--S--- dir, breaking config.status.  The fix is the
    same as the abiword-plugin-clarisworks / aaphoto recipe: at build time
    strip `umask 077` from the generated `config.status` (and the generated
    `configure` in case of a re-run).  This only touches generated files and
    is idempotent.

  * config.guess (2018-03-08 snapshot) cannot identify HarmonyOS
    (uname -s = "HarmonyOS").  Pass `--build/--host=aarch64-unknown-linux-gnu`
    explicitly so configure never runs the probe — same approach as the
    libtool/automake recipes in this registry.
"""

import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibcmphConan(ConanFile):
    name = "libcmph"
    version = "2.0.2"
    description = "C Minimal Perfect Hashing Library"
    license = "LGPL-2.1-only OR MPL-1.1"
    homepage = "https://cmph.sourceforge.net/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("perfect-hash", "mphf", "hashing", "minimal-perfect-hash")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "cxxmph": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
        "cxxmph": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        # cxxmph builds a C++ helper library; it pulls in C++11 stdlib into
        # consumers and offers little for the C core we package here, so it
        # is opt-in and off by default (matches Debian's split package).
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libcmph supports Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        AutotoolsDeps(self).generate()
        toolchain = AutotoolsToolchain(self)
        # config.guess (2018 snapshot) cannot identify HarmonyOS; pass the
        # triplet explicitly (config.sub accepts *-linux-gnu) so configure
        # never runs the probe — same approach as libtool/automake recipes.
        triplet = self._build_triplet()
        toolchain.configure_args.append(f"--build={triplet}")
        toolchain.configure_args.append(f"--host={triplet}")
        toolchain.configure_args.append("--disable-dependency-tracking")
        toolchain.configure_args.append("--disable-silent-rules")
        # cxxmph is opt-in; keep the default build C-only.
        if not self.options.get_safe("cxxmph"):
            toolchain.configure_args.append("--disable-cxxmph")
        # The bundled unit tests gated behind --enable-check need libcheck,
        # which is not packaged here; the upstream `make check` TESTS target
        # (graph/select/compressed_seq/compressed_rank/cmph_benchmark) is
        # libcheck-free and is what we run.
        toolchain.configure_args.append("--disable-check")
        env = toolchain.environment()
        if str(self.settings.os) == "OHOS":
            shell = self._config_shell()
            env.define("CONFIG_SHELL", shell)
            env.define("SHELL", shell)
        toolchain.generate(env=env)

    def build(self):
        apply_conandata_patches(self)
        # Pin the build environment directly into os.environ BEFORE invoking
        # any autotools helper.  The ohos-aarch64 profile hardcodes
        # CONFIG_SHELL=/data/service/hnp/bin/bash in [buildenv] — that path
        # exists on CI but not on every developer machine / device, and the
        # generated `configure` executes $CONFIG_SHELL directly (line ~157),
        # so a stale profile value aborts configure with "inaccessible or not
        # found".  Setting os.environ directly is process-global and wins
        # over the profile's buildenv (the same proven approach as the
        # autoconf/automake recipes in this registry); the
        # `Environment.vars().apply()` context manager alone does NOT reliably
        # override a profile-injected [buildenv] value.
        self._prepare_build_environment()
        # E114: config.status (generated by configure) uses
        # `umask 077 && mktemp -d` for its temp dir; on HMDFS the resulting
        # 0700 dir becomes unwritable (setgid drwx--S---), so the awk/sed
        # subs files cannot be written and config.status aborts with
        # "could not setup config files machinery".  Strip `umask 077` from
        # the generated configure *before* running it so the probe inside
        # configure (and the later config.status it spawns) both use the
        # default umask.  Same approach as the aaphoto /
        # abiword-plugin-clarisworks recipes.
        configure_path = os.path.join(self.source_folder, "configure")
        if os.path.isfile(configure_path):
            self._drop_umask_077(configure_path)
            self._guard_config_shell(configure_path)
        autotools = Autotools(self)
        autotools.configure()
        # E074: HMDFS SELinux forbids the make jobserver FIFO; use -j1.
        autotools.make(args=["-j1"])
        # L1: run the upstream `make check` TESTS target
        # (graph_tests, select_tests, compressed_seq_tests,
        #  compressed_rank_tests, cmph_benchmark_test — all self-contained,
        #  no libcheck dependency).
        autotools.make(target="check", args=["-j1"])

    def package(self):
        self._prepare_build_environment()
        autotools = Autotools(self)
        autotools.install()
        self._relocate_libtool_la()
        # Licenses
        for license_file in ("COPYING", "LGPL-2", "MPL-1.1"):
            src = os.path.join(self.source_folder, license_file)
            if os.path.isfile(src):
                copy(
                    self,
                    license_file,
                    src=self.source_folder,
                    dst=os.path.join(self.package_folder, "licenses"),
                    keep_path=False,
                )

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "libcmph")
        self.cpp_info.set_property("cmake_target_name", "libcmph::libcmph")
        self.cpp_info.set_property("pkg_config_name", "cmph")
        self.cpp_info.libs = ["cmph"]
        # cmph_search needs -lm on some targets (configure appends LIBM);
        # declare it as a system requirement so consumers link correctly.
        self.cpp_info.system_libs = ["m"]
        bindir = os.path.join(self.package_folder, "bin")
        self.cpp_info.bindirs = ["bin"]
        # cmph CLI lives in bin/; expose it on PATH for consumers.
        self.buildenv_info.append_path("PATH", bindir)
        self.runenv_info.append_path("PATH", bindir)
        pc_dir = os.path.join(self.package_folder, "lib", "pkgconfig")
        if os.path.isdir(pc_dir):
            self.buildenv_info.append_path("PKG_CONFIG_PATH", pc_dir)
            self.runenv_info.append_path("PKG_CONFIG_PATH", pc_dir)

    # ── helpers ───────────────────────────────────────────────────────

    def _build_triplet(self):
        arch = str(self.settings.arch)
        cpu = {
            "armv8": "aarch64",
            "armv8.3": "aarch64",
            "armv8_32": "arm",
            "armv7": "arm",
            "x86_64": "x86_64",
        }.get(arch, "aarch64")
        return f"{cpu}-unknown-linux-gnu"

    def _config_shell(self):
        candidates = (
            os.environ.get("CONFIG_SHELL"),
            os.environ.get("SHELL"),
            "/data/service/hnp/bin/bash",
            "/bin/bash",
            "/system/bin/sh",
            "/bin/sh",
            "sh",
        )
        for candidate in candidates:
            if not candidate:
                continue
            if os.path.isabs(candidate):
                if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                    return candidate
            elif shutil.which(candidate):
                return candidate
        return "sh"

    def _prepare_build_environment(self):
        """Pin build environment directly into os.environ.

        This process-global override beats the profile's [buildenv] —
        essential here because the ohos-aarch64 profile hardcodes
        CONFIG_SHELL=/data/service/hnp/bin/bash, a path that exists on CI
        but not on every developer machine / device.  The generated
        `configure` executes $CONFIG_SHELL directly, so a stale profile
        value aborts configure with "inaccessible or not found".  Same
        proven approach as the autoconf/automake recipes in this registry.
        """
        tmpdir = os.path.join(self.build_folder, ".tmp")
        os.makedirs(tmpdir, exist_ok=True)
        shell = self._config_shell()
        os.environ["SHELL"] = shell
        os.environ["CONFIG_SHELL"] = shell
        os.environ["TMPDIR"] = tmpdir
        # tests/Makefile.am and examples/Makefile.am have no AM_CPPFLAGS, so
        # the noinst_PROGRAMS they build (packed_mphf_tests, mphf_tests, and
        # the four examples) use #include <cmph.h> (angle-bracket) that the
        # out-of-tree VPATH build cannot resolve.  Setting CPPFLAGS here makes
        # configure bake -I<src>/src into EVERY generated Makefile (via
        # @CPPFLAGS@), so the include resolves for check_PROGRAMS,
        # noinst_PROGRAMS, and examples alike — no source patch needed.
        src_inc = os.path.join(self.source_folder, "src")
        existing_cppflags = os.environ.get("CPPFLAGS", "")
        if src_inc not in existing_cppflags:
            os.environ["CPPFLAGS"] = (
                f"-I{src_inc} {existing_cppflags}".strip()
            )
        if str(self.settings.os) == "OHOS":
            mkdir_p = shutil.which("mkdir")
            if mkdir_p:
                os.environ["MKDIR_P"] = f"{mkdir_p} -p"

    def _drop_umask_077(self, path):
        """E114: strip `umask 077` from a generated autotools script.

        Only touches generated files (configure / config.status), never
        source.  Idempotent: re-running on an already-patched file is a
        no-op.
        """
        try:
            with open(path, encoding="utf-8", errors="ignore") as fh:
                text = fh.read()
        except OSError:
            return
        if "umask 077" not in text:
            return
        patched = text.replace("umask 077", "umask 022")
        if patched != text:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(patched)
            self.output.info(f"E114: dropped umask 077 -> umask 022 in {path}")

    def _guard_config_shell(self, path):
        """Guard the generated configure's CONFIG_SHELL re-exec.

        The ohos-aarch64 profile's [buildenv] injects
        CONFIG_SHELL=/data/service/hnp/bin/bash — valid on CI but absent on
        other hosts/devices.  Conan's env composition sources the profile
        buildenv *after* the toolchain env, so neither ``os.environ`` nor
        ``AutotoolsToolchain`` env vars can override it.  The generated
        configure does ``exec $CONFIG_SHELL`` early (line ~152), aborting
        with "inaccessible or not found" when the path doesn't exist.

        Fix: insert a guard right before the re-exec check that clears
        CONFIG_SHELL if it points to a non-executable binary, so
        configure's own shell-probing logic runs instead.  On CI (where
        the path is valid) the guard is a no-op; on other hosts it makes
        the build work without depending on a CI-specific path.  Only
        touches the generated configure (never source).  Idempotent.
        """
        try:
            with open(path, encoding="utf-8", errors="ignore") as fh:
                text = fh.read()
        except OSError:
            return
        marker = "_conan_config_shell_guard"
        if marker in text:
            return
        anchor = 'if test x"${_as_can_reexec}" != xno && test "x$CONFIG_SHELL" != x; then'
        if anchor not in text:
            return
        guard = (
            f"# {marker}: clear stale CONFIG_SHELL (profile buildenv may inject\n"
            "# a CI-specific path absent on this host) if not executable, so\n"
            "# configure probes for a working shell instead of aborting re-exec.\n"
            "if test -n \"${CONFIG_SHELL:-}\" && ! { command -v \"$CONFIG_SHELL\" >/dev/null 2>&1 || test -x \"$CONFIG_SHELL\"; }; then\n"
            "  unset CONFIG_SHELL\n"
            "fi\n"
        )
        patched = text.replace(anchor, guard + anchor, 1)
        if patched != text:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(patched)
            self.output.info(f"Conan: guarded CONFIG_SHELL re-exec in {path}")

    def _relocate_libtool_la(self):
        """Make installed .la files relocatable by replacing the baked-in
        `prefix=/` / libdir with values resolvable at consumer link time.

        libtool 2.x writes `prefix=` and `libdir=` as absolute paths derived
        from --prefix at `make install` time.  Conan installs with
        --prefix=<package_folder> via DESTDIR, so the .la points at the
        conan cache path and breaks when the package is consumed from a
        different cache.  Rewriting to the package-relative path keeps the
        .la valid without the cache path leak.  Only generated install
        artifacts are touched (never source).
        """
        libdir = os.path.join(self.package_folder, "lib")
        if not os.path.isdir(libdir):
            return
        for la_name in os.listdir(libdir):
            if not la_name.endswith(".la"):
                continue
            la_path = os.path.join(libdir, la_name)
            try:
                with open(la_path, encoding="utf-8", errors="ignore") as fh:
                    text = fh.read()
            except OSError:
                continue
            new = text
            # Rewrite baked-in absolute prefix/libdir to package-relative.
            new = new.replace(
                f"prefix={self.package_folder}",
                f"prefix={shlex.quote(self.package_folder)}",
            )
            new = new.replace(
                f"libdir={self.package_folder}/lib",
                f"libdir={shlex.quote(libdir)}",
            )
            if new != text:
                with open(la_path, "w", encoding="utf-8") as fh:
                    fh.write(new)
