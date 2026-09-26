#!/usr/bin/env python3
"""Conan recipe for rrdtool 1.9.0 — round-robin database tool (C, autotools).

OHOS PC adaptation notes
------------------------
* Upstream release tarball from the official oetiker/rrdtool-1.x GitHub
  release for tag v1.9.0.  The tarball ships generated Autotools files, so
  no autoreconf is run.
* Version string is exactly ``1.9.0`` (upstream derives it from its own
  ``VERSION`` file through ``m4_esyscmd``); it is not normalised.
* Graph rendering stays ENABLED (the upstream default).  The graph stack
  (glib / pango / cairo / libpng) is published to the artifact repository
  with OHOS binaries — verified with ``conan install --build=never`` in a
  fresh CONAN_HOME before this recipe was written, so the richer package
  is the correct trade-off over ``--disable-rrd_graph``.
* ``--disable-docs`` is mandatory, not cosmetic: configure.ac aborts with
  ``AC_MSG_ERROR([I need a copy of *nroff to format the documentation])``
  whenever documentation is enabled and gnroff/groff are absent.
* Language bindings (perl/python/ruby/lua/tcl) are off.  They build
  loadable extensions against a *host* interpreter; that is not a
  cross-compilable proposition and would ship artifacts no OHOS consumer
  can load.  Upstream degrades these automatically, but the build host
  does have a perl and a python3, so the auto-probe would pick them up.
* libdbi / librados / libwrap are explicitly disabled.  Their probes are
  bare ``AC_CHECK_LIB``/``AC_CHECK_HEADER`` with no hard failure, so a
  stray header on the build host would silently create an undeclared
  runtime dependency.
* cairo and libpng are pinned to exactly the versions pango resolves to
  (1.18.4 / 1.6.58).  Pinning the newer 1.18.4.2 / 1.6.58.3 makes Conan
  fail with a hard version conflict, so the lower pins are the only
  coherent choice while still clearing rrdtool's own minimums
  (cairo>=1.10.2, libpng>=1.4.8).
* Packaged ELFs are self-signed on OHOS: HarmonyOS PC refuses to execute
  unsigned binaries, so ``rrdtool --version`` (and the L2 smoke gate)
  would fail without this.
"""
import os
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
    rm,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class RrdtoolConan(ConanFile):
    name = "rrdtool"
    version = "1.9.0"
    description = (
        "RRDtool is a high performance data logging and graphing system for "
        "time series data such as network bandwidth, temperatures, or CPU load"
    )
    license = "GPL-2.0-or-later"
    homepage = "https://oss.oetiker.org/rrdtool/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("rrd", "time-series", "monitoring", "graphing", "cli")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"

    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    @property
    def _is_ohos(self):
        return str(self.settings.os) == "OHOS"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if not self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # Active (non-dnl) EX_CHECK_ALL probes in configure.ac:
        #   glib-2.0 / gobject-2.0        -> unconditional
        #   libpng, pangocairo-1.0        -> only with --enable-rrd_graph (default on)
        #   libxml-2.0                    -> only with --enable-rrd_restore (default on)
        # src/rrd_graph.c includes <cairo.h>, <cairo-svg.h>, <cairo-ps.h> and
        # <cairo-pdf.h> directly, so cairo is a declared dependency rather than
        # a pango implementation detail.
        self.requires("glib/2.84.0.1", transitive_headers=True, transitive_libs=True)
        self.requires("pango/1.50.14.1.1", transitive_headers=True, transitive_libs=True)
        self.requires("cairo/1.18.4", transitive_headers=True, transitive_libs=True)
        self.requires("libpng/1.6.58", transitive_headers=True, transitive_libs=True)
        self.requires("libxml2/2.15.3.1", transitive_headers=True, transitive_libs=True)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"rrdtool supports Linux/OHOS native builds, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        PkgConfigDeps(self).generate()

        toolchain = AutotoolsToolchain(self)
        toolchain.configure_args.extend(self._feature_args())
        toolchain.generate()

        # HarmonyOS PC mounts /tmp read-only and autoconf's config.status
        # creates its working directory under TMPDIR.
        tmpdir = os.path.join(self.build_folder, "conan-tmp")
        os.makedirs(tmpdir, exist_ok=True)
        env = Environment()
        env.define("TMPDIR", tmpdir)
        env.define("TMP", tmpdir)
        env.define("TEMP", tmpdir)
        env.vars(self, scope="build").save_script("rrdtool_tmpdir")

    def _feature_args(self):
        """Feature switches only; Conan's canonical --prefix/--libdir/... args
        come from the AutotoolsToolchain and are prepended separately."""
        args = [
            # --- hard-fail probes that must be switched off ---
            "--disable-docs",      # needs gnroff/groff, else AC_MSG_ERROR
            "--disable-examples",
            "--disable-nls",
            # --- host-interpreter loadable modules ---
            "--disable-perl",
            "--disable-python",
            "--disable-ruby",
            "--disable-lua",
            "--disable-tcl",
            # --- optional autodetected deps with no hard failure ---
            "--disable-libdbi",
            "--disable-librados",
            "--disable-libwrap",
            "--disable-dependency-tracking",
        ]
        if self.options.shared:
            args += ["--enable-shared", "--disable-static"]
        else:
            args += ["--disable-shared", "--enable-static"]
        return args

    # -- E386: capability-tested shell on HMDFS ---------------------------------
    # A shell on HMDFS can exit 0 while still emitting a getcwd diagnostic, so
    # neither the executable bit nor the return code proves it can preserve the
    # requested working directory.  Accept a candidate only when `pwd` exits 0
    # with *both* stdout and stderr empty (knowledge/graph/E386.kv).
    def _config_shell(self):
        candidates = []
        configured_shell = os.environ.get("CONFIG_SHELL")
        if configured_shell:
            candidates.append(configured_shell)

        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        c_compiler = compilers.get("c") if compilers else None
        if c_compiler:
            candidates.append(
                os.path.join(os.path.dirname(shlex.split(c_compiler)[0]), "bash")
            )

        candidates.extend(
            ["/system/bin/sh", shutil.which("bash"), shutil.which("sh"), "/bin/sh"]
        )

        seen = set()
        for candidate in candidates:
            if not candidate or candidate in seen:
                continue
            seen.add(candidate)
            if not os.path.isfile(candidate) or not os.access(candidate, os.X_OK):
                continue
            try:
                probe = subprocess.run(
                    [candidate, "-c", "pwd >/dev/null"],
                    cwd=self.build_folder,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=5,
                    check=False,
                )
            except (OSError, subprocess.TimeoutExpired):
                continue
            if probe.returncode == 0 and not probe.stdout and not probe.stderr:
                return candidate

        raise ConanInvalidConfiguration(
            "No executable POSIX shell can preserve the rrdtool build working "
            "directory (E386): tried " + ", ".join(sorted(seen))
        )

    def _save_shell_environment(self, config_shell):
        # Reasserted in its own script because the OHOS profile's [buildenv]
        # exports CONFIG_SHELL=<hnp bash>, which is exactly the shell that
        # cannot hold the working directory here.
        shell_env = Environment()
        shell_env.define("CONFIG_SHELL", config_shell)
        shell_env.define("SHELL", config_shell)
        if self._is_ohos:
            shell_env.define("MKDIR_P", "/system/bin/mkdir -p")
        shell_env.vars(self, scope="build").save_script("rrdtool_shell")

    def build(self):
        apply_conandata_patches(self)
        # E011/E114: the autoconf-generated configure wraps config.status
        # temp-dir creation in `umask 077 &&`, and HMDFS cannot write those
        # 0700-mode directories ("could not setup config files machinery";
        # precedent zile 0002 / radvd 0003 / probabel).  Drop the umask
        # wrapper, keep the temp-dir creation.
        replace_in_file(self, os.path.join(self.source_folder, "configure"),
                        "umask 077 && ", "")
        # The release tarball SHIPS src/rrd_config.h -- a stale configure
        # output from the maintainer's glibc machine (dated 2024-07-29,
        # #defines HAVE__NL_TIME_WEEK_1STDAY etc.).  rrd_tool.h includes
        # "rrd_config.h" with quotes, and a quoted include resolves relative
        # to the includer's directory first, so this stale file beats the
        # freshly generated one in the build dir: configure correctly
        # #undefs HAVE__NL_TIME_WEEK_1STDAY on musl, yet rrd_rpncalc.c
        # still compiled the glibc-only nl_langinfo branch (measured).
        # Remove the shipped file; config.status writes the real one into
        # the build dir.
        stale_config = os.path.join(self.source_folder, "src", "rrd_config.h")
        if os.path.isfile(stale_config):
            os.remove(stale_config)
        config_shell = self._config_shell()
        self.output.info(f"configure shell (capability-tested): {config_shell}")
        self._save_shell_environment(config_shell)

        toolchain = AutotoolsToolchain(self)
        toolchain.configure_args.extend(self._feature_args())
        configure = os.path.join(self.source_folder, "configure")

        # The OHOS profile exports CONFIG_SHELL/SHELL=<hnp bash> through
        # [buildenv], and that bash cannot resolve its own cwd on HMDFS
        # (measured: `/data/service/hnp/bin/bash -c pwd` -> rc=1
        # "shell-init: error retrieving current directory", reproduced in a
        # plain ~/tmp control directory, so it is a property of the binary on
        # this filesystem and not of the conan build folder).
        # Re-exporting CONFIG_SHELL/SHELL from a saved env script is *not*
        # enough: the aggregated conanbuild.sh was already emitted during
        # generate(), so the profile value wins and autoconf re-execs itself
        # into the broken shell ("configure: error: working directory cannot
        # be determined").  Pin the tested shell on the command itself so
        # nothing downstream can substitute it.
        command = " ".join(
            [
                f"CONFIG_SHELL={shlex.quote(config_shell)}",
                f"SHELL={shlex.quote(config_shell)}",
                shlex.quote(config_shell),
                shlex.quote(configure),
            ]
            + [shlex.quote(a) for a in toolchain.configure_args]
        )
        self.run(command, cwd=self.build_folder, env="conanbuild")
        Autotools(self).make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

        libdir = os.path.join(self.package_folder, "lib")
        # libtool archives carry build-machine absolute paths and are never
        # consumed by a Conan client.
        rm(self, "*.la", libdir)
        if self.options.shared:
            rm(self, "*.a", libdir)

        for license_file in ("COPYRIGHT", "LICENSE"):
            copy(
                self,
                license_file,
                src=self.source_folder,
                dst=os.path.join(self.package_folder, "licenses"),
                keep_path=False,
            )

        if self._is_ohos:
            self._sign_all_ohos_elf()

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "librrd")
        self.cpp_info.libs = ["rrd"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread"]

    # -- helpers ---------------------------------------------------------
    def _sign_all_ohos_elf(self):
        """HarmonyOS PC will not execute an unsigned ELF.

        Sign every packaged executable and the shared library so the L2
        smoke gate and the functional test can actually run the tool.
        """
        for folder in ("bin", "lib"):
            root = os.path.join(self.package_folder, folder)
            if not os.path.isdir(root):
                continue
            for dirpath, _dirnames, filenames in os.walk(root):
                for name in sorted(filenames):
                    path = os.path.join(dirpath, name)
                    if os.path.islink(path):
                        continue
                    if folder == "lib" and ".so" not in name:
                        continue
                    self._sign_ohos_elf(path)

    @staticmethod
    def _sign_ohos_elf(path):
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        readelf = shutil.which("llvm-readelf") or "/data/service/hnp/bin/llvm-readelf"
        if not os.path.isfile(signer) or not os.path.isfile(readelf):
            raise ConanInvalidConfiguration(
                "OHOS signing tools are required to package rrdtool: "
                f"missing {signer} or {readelf}"
            )
        output = path + ".signed"
        subprocess.run(
            [signer, "sign", "-inFile", path, "-outFile", output, "-selfSign", "1"],
            check=True,
            timeout=180,
        )
        sections = subprocess.run(
            [readelf, "-SW", output], check=True, capture_output=True, text=True, timeout=60
        ).stdout
        if sections.count(".codesign") != 1:
            raise ConanInvalidConfiguration(
                f"signed ELF has an invalid .codesign count: {path}"
            )
        os.chmod(output, (os.stat(path).st_mode & 0o777) | 0o055)
        os.replace(output, path)
