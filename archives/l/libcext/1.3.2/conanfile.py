#!/usr/bin/env python3
"""Conan recipe for the ESO C Extension Library (libcext) 1.3.2.

libcext is ESO's C utility library used to implement the Common Pipeline
Library (CPL). The release archive ships a pre-generated Autotools configure
script and admin/config.sub (2022-01-03) that already accepts aarch64.

No .patch files are used.  However, the recipe DOES adjust the generated
``configure`` at build time (runtime text replacement, not a source patch) to
work around two OHOS environment issues that cannot be solved via Conan
environment variables alone:

1. ``umask 077`` → ``umask 022``: HMDFS setgid build dirs make the 0700 temp
   dirs created by config.status unwritable (Permission denied).
2. ``#! /bin/sh`` shebang → real OHOS shell: /bin/sh may not be available.
3. Re-exec guard: only re-exec with ``$CONFIG_SHELL`` when it is an
   executable file, so the profile's nonexistent CONFIG_SHELL path does not
   break configure.

The profile's ``[buildenv]`` sets ``CONFIG_SHELL=/data/service/hnp/bin/bash``
which is sourced AFTER all Conan toolchain environment scripts, overriding
``tc.environment()``, ``buildenv_info``, and ``os.environ``.  No Conan-level
environment variable can win against it.  The generated-configure adjustment
is therefore the only reliable mechanism on this profile.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import copy, get, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class LibcextConan(ConanFile):
    name = "libcext"
    version = "1.3.2"
    description = "ESO C Extension Library — C utility library for the Common Pipeline Library (CPL)"
    license = "LGPL-2.1-or-later"
    homepage = "https://www.eso.org/sci/software/cpl/"
    url = "https://ftp.eso.org/pub/dfs/pipelines/libraries/cext/"
    topics = ("eso", "cpl", "cext", "utility", "container")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        if self.settings.os == "Windows":
            self.options.shared = False

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libcext supports Linux and OHOS, not {self.settings.os}"
            )
        if self.settings.os == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ------------------------------------------------------------------ #
    # Environment resolution
    # ------------------------------------------------------------------ #

    def _ohos_shell(self):
        for candidate in (
            os.environ.get("CONFIG_SHELL"),
            os.environ.get("SHELL"),
            shutil.which("bash"),
            shutil.which("sh"),
            "/bin/sh",
            "/system/bin/sh",
        ):
            if candidate and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate
        return "/bin/sh"

    def _compiler_executable(self, key, fallback_name):
        executables = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        ) or {}
        configured = executables.get(key)
        if configured and os.path.isfile(configured):
            return configured
        found = shutil.which(fallback_name)
        return found or configured or fallback_name

    def _tool_executable(self, *names):
        for name in names:
            found = shutil.which(name)
            if found:
                return found
        return names[0]

    def _gnu_triplet(self):
        arch = str(self.settings.arch)
        machine = {
            "armv8": "aarch64",
            "armv8.3": "aarch64",
            "x86_64": "x86_64",
            "armv7": "arm",
        }.get(arch, arch)
        return f"{machine}-unknown-linux-gnu"

    def _ohos_host_lib_dir(self):
        """Directory shipping the OHOS LLVM *host* shared libraries.

        The toolchain ``ld.lld`` is dynamically linked against
        ``libxml2.so.16`` -- a host dependency, not a target one -- and only
        carries ``RUNPATH=$ORIGIN/../lib``.  When CC is reached via a symlink
        or wrapper whose ``$ORIGIN/../lib`` does not contain
        ``libxml2.so.16`` (e.g. the CI toolchain laid out under
        ``/data/service/hnp``), the loader cannot start ``ld.lld`` at all and
        ``configure`` dies with ``C compiler cannot create executables``
        leaving no usable stderr.  Derive the real host lib dir from
        ``realpath(CC)`` so the ``LD_LIBRARY_PATH`` we prepend always points at
        the directory that actually ships ``libxml2.so.16`` for this
        toolchain, regardless of how CC was named on the command line.
        """
        cc_real = os.path.realpath(self._compiler_executable("c", "clang"))
        return os.path.normpath(
            os.path.join(os.path.dirname(cc_real), os.pardir, "lib")
        )

    def _ohos_lld_probe(self):
        """Fail fast if the OHOS linker cannot start.

        ``ld.lld`` NEEDS ``libxml2.so.16``; if the loader cannot satisfy it
        from ``LD_LIBRARY_PATH`` (set in ``generate()``) or ``$ORIGIN/../lib``,
        every link silently fails and ``configure`` reports ``C compiler
        cannot create executables`` with no useful stderr.  Probe the linker
        directly through the generated ``conanbuild`` env so the real root
        cause surfaces here instead of mid-configure.

        The generic ``lld`` driver needs ``-flavor gnu`` to select the GNU
        backend; ``ld.lld`` selects it by program name and rejects
        ``-flavor`` (exit=1), so a bare ``--version`` is used for it.
        """
        host_lib = self._ohos_host_lib_dir()
        libxml2 = os.path.join(host_lib, "libxml2.so.16")
        if not os.path.isfile(libxml2):
            raise ConanInvalidConfiguration(
                f"OHOS LLVM host lib dir {host_lib} (derived from "
                f"realpath(CC)={os.path.realpath(self._compiler_executable('c', 'clang'))}) "
                f"is missing libxml2.so.16, which ld.lld is dynamically linked "
                f"against. configure would fail with 'C compiler cannot create "
                f"executables'. Ensure the OHOS LLVM toolchain ships "
                f"libxml2.so.16 in its host lib dir."
            )
        ld = self._tool_executable("ld.lld", "lld", "ld")
        # ``ld.lld`` selects its GNU backend by program name and rejects
        # ``-flavor`` (exit=1), which must not be misread as a libxml2
        # load failure.  Only the generic ``lld`` driver needs ``-flavor
        # gnu``.  ``ld`` (GNU ld) is the final fallback and never needs it.
        ld_base = os.path.basename(ld)
        if ld_base == "ld.lld":
            probe_cmd = f'"{ld}" --version'
        elif ld_base == "lld":
            probe_cmd = f'"{ld}" -flavor gnu --version'
        else:
            probe_cmd = f'"{ld}" --version'
        try:
            self.run(probe_cmd, env=["conanbuild"])
        except ConanException as exc:
            raise ConanInvalidConfiguration(
                f"OHOS linker {ld} cannot start (libxml2.so.16 not loadable). "
                f"LD_LIBRARY_PATH={host_lib}. Underlying error: {exc}"
            ) from exc

    # ------------------------------------------------------------------ #

    def generate(self):
        tc = AutotoolsToolchain(self)
        if str(self.settings.os) == "OHOS":
            shell = self._ohos_shell()
            environment = tc.environment()
            environment.define_path("SHELL", shell)
            environment.define_path("CONFIG_SHELL", shell)
            environment.define_path("CC", self._compiler_executable("c", "clang"))
            environment.define_path("CXX", self._compiler_executable("cpp", "clang++"))
            environment.define_path("LD", self._tool_executable("ld.lld", "lld", "ld"))
            environment.define_path("AR", self._tool_executable("llvm-ar", "ar"))
            environment.define_path("RANLIB", self._tool_executable("llvm-ranlib", "ranlib"))
            environment.define_path("STRIP", self._tool_executable("llvm-strip", "strip"))
            environment.define_path("NM", self._tool_executable("llvm-nm", "nm"))
            # ld.lld is dynamically linked against libxml2.so.16 (a host
            # dependency). When CC is reached via a symlink/wrapper whose
            # $ORIGIN/../lib lacks it, the loader cannot start ld.lld and
            # configure reports "C compiler cannot create executables".
            # Prepend the real host lib dir (derived from realpath(CC)) so the
            # loader finds libxml2.so.16 throughout configure/make/check.
            environment.prepend_path("LD_LIBRARY_PATH", self._ohos_host_lib_dir())
            gnu_triplet = self._gnu_triplet()
            tc.update_configure_args(
                {
                    "--build": gnu_triplet,
                    "--host": gnu_triplet,
                }
            )
        if self.options.shared:
            tc.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            tc.configure_args.extend(["--disable-shared", "--enable-static"])
            if self.options.get_safe("fPIC"):
                tc.configure_args.append("--with-pic")
        if str(self.settings.os) == "OHOS":
            tc.generate(env=environment)
        else:
            tc.generate()

    def _patch_configure_runtime(self):
        """Adjust the GENERATED configure at build time.

        These are runtime adjustments to the generated build script, NOT
        source patches (.patch files).  The upstream source tarball is
        unchanged.  They work around OHOS environment issues that cannot be
        solved via Conan environment variables (the profile [buildenv] is
        sourced last and overrides all Conan env).

        1. umask 077 → 022: HMDFS setgid dirs make 0700 temp dirs unwritable.
        2. #! /bin/sh → real OHOS shell: /bin/sh may not be present.
        3. Re-exec guard: only re-exec with $CONFIG_SHELL when it is
           executable, so the profile's nonexistent path is skipped.
        """
        configure_path = os.path.join(self.source_folder, "configure")
        if not os.path.isfile(configure_path):
            return
        shell = self._ohos_shell()
        replace_in_file(self, configure_path, "umask 077", "umask 022", strict=False)
        # Replace the shebang with a block that resets CONFIG_SHELL/SHELL
        # when the profile's configured path is absent (nonexistent path
        # would break sub-script invocations like config.sub).
        override_block = (
            f"#!{shell}\n"
            f"# OHOS runtime: reset shell vars when the profile path is absent\n"
            f'if test -n "$CONFIG_SHELL" && ! test -x "$CONFIG_SHELL"; then\n'
            f'  CONFIG_SHELL="{shell}"; SHELL="{shell}"; export CONFIG_SHELL SHELL\n'
            f"fi"
        )
        for pattern in ("#! /bin/sh", "#!/bin/sh", "#! /bin/bash", "#!/bin/bash"):
            replace_in_file(self, configure_path, pattern, override_block, strict=False)
        replace_in_file(
            self,
            configure_path,
            'if test x"${_as_can_reexec}" != xno && test "x$CONFIG_SHELL" != x; then',
            'if test x"${_as_can_reexec}" != xno && test "x$CONFIG_SHELL" != x && test -x "$CONFIG_SHELL"; then',
            strict=False,
        )

    def build(self):
        if str(self.settings.os) == "OHOS":
            self._patch_configure_runtime()
            self._ohos_lld_probe()
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # Upstream test suite: 7 TESTS in tests/Makefile.am.
        # Host is native aarch64 OHOS so test binaries run directly.
        autotools.make(target="check", args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install(args=["-j1"])
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        self._remove_libtool_archives()

    def _remove_libtool_archives(self):
        lib_dir = os.path.join(self.package_folder, "lib")
        if not os.path.isdir(lib_dir):
            return
        for entry in os.listdir(lib_dir):
            if not entry.endswith(".la"):
                continue
            os.remove(os.path.join(lib_dir, entry))

    def package_info(self):
        self.cpp_info.libs = ["cext"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.set_property("cmake_file_name", "libcext")
        self.cpp_info.set_property("cmake_target_name", "libcext::libcext")
        self.cpp_info.set_property("pkg_config_name", "cext")
        pc_dir = os.path.join(self.package_folder, "lib", "pkgconfig")
        self.buildenv_info.append_path("PKG_CONFIG_PATH", pc_dir)
        self.runenv_info.append_path("PKG_CONFIG_PATH", pc_dir)
