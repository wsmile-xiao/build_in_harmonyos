#!/usr/bin/env python3
"""Conan recipe — dinotrace 9.4f (X11/Motif waveform viewer)

Dinotrace is a graphical waveform / value-change-dump (VCD) viewer for
Verilog/VHDL simulation traces (Wilson Snyder, veripool).  It is written
directly against the X Toolkit (Xt) and the Motif widget set (libXm).

OHOS PC (aarch64, os=OHOS) adaptation:
- Motif (libXm) does not exist upstream of this repository; it is supplied by
  the locally adapted ``motif/2.3.8`` package (libXm.so.4 + Xm/*.h).
- The 2019 hand-written Autotools build is built *in-source* (the top-level
  Makefile hard-codes ``bin/dinotrace-$(HOST)`` copies and a source-relative
  ``obj_dir``; it does not support VPATH/out-of-source builds).
- ``AC_PATH_XTRA``/``AC_PATH_X`` are satisfied with ``--x-includes`` and
  ``--x-libraries`` pointing at the packaged ``libx11`` headers/libs.
- Dependency include/lib roots are injected through the private Conan build
  folder (R49) — never a shared ``/usr/local`` prefix.
- E011: the HMDFS ``umask 077`` in ``configure`` is rewritten to ``022`` and
  the ``/bin/sh`` shebangs / ``SHELL`` make variables are repointed to the
  OHOS shell.
- Perl is a hard build dependency (``src/dist_date.pl``, ``src/dinodoc.pl``
  generate ``dist_date.h`` and ``dinodoc.h``).
- Headless reality: this machine and OHOS have no X server / no Wayland, so
  any code path reaching ``XtOpenDisplay`` cannot succeed.  ``dinotrace
  --version`` is headless-safe and is what the consumer test asserts; the
  GUI cannot be exercised (see notes.md / reports/).
"""
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    load,
    replace_in_file,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps


class DinotraceConan(ConanFile):
    name = "dinotrace"
    version = "9.4f"
    description = "Dinotrace waveform viewer (X11/Motif) for Verilog/VCD traces"
    license = "GPL-3.0-or-later"
    homepage = "https://www.veripool.org/dinotrace"
    url = "https://www.veripool.org/ftp/dinotrace-9.4f.tgz"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: accept both Linux and OHOS, never `== "Linux"` only.
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"dinotrace supports Linux and OHOS, not {self.settings.os}"
            )

    def requirements(self):
        # Motif (libXm.so.4 + <Xm/*.h>) — the GUI toolkit dinotrace is written
        # against.  Its public headers transitively pull <X11/Intrinsic.h>
        # (libXt), <X11/Xlib.h> (libx11) and the xorgproto protocol headers,
        # so mark it transitive_headers; libXm links libXt/libXext/libX11 so
        # mark it transitive_libs as well.
        self.requires("motif/2.3.8", transitive_headers=True, transitive_libs=True)
        # xorgproto owns <X11/X.h>, <X11/Xfuncproto.h>; declare it explicitly
        # so the header roots are guaranteed present on a clean graph.
        self.requires("xorgproto/2025.1", transitive_headers=True)

    def layout(self):
        # The 2019 hand-written top-level Makefile does not support an
        # out-of-source (VPATH) build: `dinotrace_exe` creates a relative
        # `obj_dir`, copies the result back to `./dinotrace` and
        # `bin/dinotrace-$(HOST)`, and the `info`/`install-info` targets glob
        # `*.info*` in the current directory.  Force an in-source build.
        self.folders.build = "."
        self.folders.generators = os.path.join(".", "conan")

    def source(self):
        source_data = dict(self.conan_data["sources"])
        # These keys document the archive but are not get() arguments.
        source_data.pop("upstream_version", None)
        source_data.pop("tar_format", None)
        get(self, **source_data, strip_root=True)

    def generate(self):
        pkg_config = PkgConfigDeps(self)
        pkg_config.generate()
        VirtualBuildEnv(self).generate()

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
            environment.define_path(
                "RANLIB", self._tool_executable("llvm-ranlib", "ranlib")
            )
            environment.define_path(
                "STRIP", self._tool_executable("llvm-strip", "strip")
            )
            environment.define_path("NM", self._tool_executable("llvm-nm", "nm"))
            # Perl is required: dist_date.pl -> dist_date.h, dinodoc.pl -> dinodoc.h.
            environment.define_path("PERL", self._tool_executable("perl"))
            # R49: private build-folder include/lib roots only.
            environment.append("CPPFLAGS", self._dep_cppflags())
            environment.append("LDFLAGS", self._dep_ldflags())
        # AC_PATH_XTRA/AC_PATH_X read --x-includes / --x-libraries; point them at
        # the packaged libx11 (which owns <X11/Xlib.h>) and its lib dir.
        libx11 = self.dependencies["libx11"]
        tc.configure_args.append(f"--x-includes={libx11.package_folder}/include")
        tc.configure_args.append(f"--x-libraries={libx11.package_folder}/lib")
        if str(self.settings.os) == "OHOS":
            tc.generate(env=environment)
        else:
            tc.generate()

    def build(self):
        apply_conandata_patches(self)
        if str(self.settings.os) == "OHOS":
            self._patch_configure_runtime_shell()
            self._patch_shell_scripts()
        autotools = Autotools(self)
        autotools.configure()
        # Single-threaded: the in-source obj_dir build + perl-generated headers
        # are not parallel-safe with this vintage Makefile.
        autotools.make(args=["-j1"])
        # === Upstream test step (R51 / docs/TEST_QUALITY_SPEC.md §3.3) ===
        # Dinotrace 9.4f ships NO test suite and NO `check:` target; the only
        # upstream target is `test:` (= `./dinotrace traces/ascii.tra`), which
        # requires an X display.  Invoke it verbatim with raw output captured;
        # declare the platform exemption in MANIFEST.yml — never fake it.
        self._run_upstream_tests()

    def package(self):
        # ---- Deterministic staging (QA rework) ---------------------------
        # Upstream `install: all info installdirs install-info`
        # (Makefile.in:184) installs exactly two things: the program to
        # $(bindir) and every `*.info*` to $(infodir).  There is no
        # share/dinotrace payload (`pkgdatadir` is only a runtime config
        # search path).  On this OHOS/HMDFS box `make install` is unusable as
        # a packaging driver, for two independent reasons:
        #   (1) the `dinotrace_exe` prerequisite re-runs
        #       `cp obj_dir/dinotrace ./dinotrace`, and HMDFS refuses to
        #       overwrite the already-present executable ->
        #       `cp: .../dinotrace: Operation not permitted`
        #       (`make: *** [Makefile:135: dinotrace_exe] Error 1`);
        #   (2) upstream's helper `install-sh` cannot be exec'd at all because
        #       HMDFS ignores chmod -> `/bin/sh: ./install-sh: can't execute:
        #       Permission denied`
        #       (`make: *** [Makefile:196: install-info] Error 126`).
        # So the real artifacts are staged explicitly with copy() and then
        # VERIFIED; the package must never depend on `make install`.
        #
        # Refresh the shipped Texinfo outputs' mtimes so the `info`
        # prerequisite of the (evidence-only) install below is a no-op
        # (makeinfo/texi2pdf are absent here).  The files always exist and are
        # writable, so this cannot fail -> no ignore_errors.
        self.run(
            "touch dinotrace.info dinotrace.txt dinotrace.pdf",
            env="conanbuild",
        )
        # ---- Authoritative staging: mirror the upstream install set ------
        copy(
            self,
            "dinotrace",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "bin"),
            keep_path=False,
        )
        copy(
            self,
            "dinotrace.info",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "share", "info"),
            keep_path=False,
        )
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        # ---- Evidence-only upstream `make install` trace -----------------
        # Run upstream's installer to the extent HMDFS allows and surface the
        # raw failure in the build log, but stage it OUTSIDE the package folder
        # and keep it non-fatal, so it can never contribute to (or break) the
        # package.  `rm -f dinotrace dinotrace.exe` first lets the
        # `dinotrace_exe` cp rule (defect 1 above) get past HMDFS's refusal to
        # overwrite, exposing the deeper install-sh defect (2).
        staging = os.path.join(self.build_folder, "install-staging")
        self.output.info("=== upstream `make install` trace (non-authoritative) ===")
        self.run(
            "rm -f dinotrace dinotrace.exe && "
            f"make install DESTDIR={shlex.quote(staging)}",
            ignore_errors=True,
            env="conanbuild",
        )
        self.output.info("=== end upstream `make install` trace ===")
        # ---- Loud verification: never silently ship an incomplete package -
        expected = {
            "bin/dinotrace": os.path.join(self.package_folder, "bin", "dinotrace"),
            "share/info/dinotrace.info": os.path.join(
                self.package_folder, "share", "info", "dinotrace.info"
            ),
        }
        missing = [rel for rel, path in expected.items() if not os.path.isfile(path)]
        if missing:
            raise ConanException(
                "dinotrace/9.4f packaging incomplete; missing required artifact(s): "
                + ", ".join(missing)
                + f" under {self.package_folder}"
            )
        self._remove_libtool_archives()

    def package_info(self):
        # CLI/application package: only bin/, no linkable library.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libs = []
        self.cpp_info.requires = ["motif::motif", "xorgproto::xorgproto"]
        self.cpp_info.set_property("cmake_file_name", "dinotrace")
        self.cpp_info.set_property("cmake_target_name", "dinotrace::dinotrace")
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))

    # ------------------------------------------------------------------
    # OHOS helpers (mirrors archives/m/motif/2.3.8)
    # ------------------------------------------------------------------

    def _gnu_triplet(self):
        arch = str(self.settings.arch)
        machine = {
            "armv8": "aarch64",
            "armv8.3": "aarch64",
            "x86_64": "x86_64",
            "armv7": "arm",
        }.get(arch, arch)
        return f"{machine}-unknown-linux-gnu"

    def _ohos_shell(self):
        for candidate in (
            os.environ.get("CONFIG_SHELL"),
            os.environ.get("SHELL"),
            shutil.which("sh"),
            "/system/bin/sh",
            "/bin/sh",
            "/usr/bin/sh",
            "/data/service/hnp/bin/bash",
        ):
            if candidate and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate
        return "/system/bin/sh"

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

    def _dependency_dirs(self, subdir):
        result = []
        for dependency in self.dependencies.host.values():
            path = os.path.join(dependency.package_folder, subdir)
            if os.path.isdir(path) and path not in result:
                result.append(path)
        return result

    def _dep_cppflags(self):
        return [f"-I{path}" for path in self._dependency_dirs("include")]

    def _dep_ldflags(self):
        flags = []
        for path in self._dependency_dirs("lib"):
            flags.append(f"-L{path}")
            flags.append(f"-Wl,-rpath-link,{path}")
        return flags

    def _patch_configure_runtime_shell(self):
        configure_path = os.path.join(self.source_folder, "configure")
        if not os.path.isfile(configure_path):
            return
        shell = self._ohos_shell()
        # E011: HMDFS ignores chmod and uses umask 077, which makes config.status
        # temp subdirs unwritable. Force umask 022.
        replace_in_file(
            self,
            configure_path,
            "umask 077",
            "umask 022",
            strict=False,
        )
        # /bin/sh does not exist on OHOS; repoint the shebang.
        for pattern in ("#! /bin/sh", "#!/bin/sh", "#! /bin/bash", "#!/bin/bash"):
            replace_in_file(
                self,
                configure_path,
                pattern,
                f"#!{shell}",
                strict=False,
            )

    def _patch_shell_scripts(self):
        # The generated top-level Makefile runs its recipes through
        # `SHELL = /bin/sh` (hard-coded, not @SHELL@); the helper scripts
        # install-sh / mkinstalldirs carry a /bin/sh shebang.  Repoint all of
        # them at the OHOS shell.
        shell = self._ohos_shell()
        makefile_in = os.path.join(self.source_folder, "Makefile.in")
        if os.path.isfile(makefile_in):
            replace_in_file(
                self,
                makefile_in,
                "SHELL = /bin/sh",
                f"SHELL = {shell}",
                strict=False,
            )
        for script in ("install-sh", "mkinstalldirs"):
            path = os.path.join(self.source_folder, script)
            if not os.path.isfile(path):
                continue
            for pattern in ("#! /bin/sh", "#!/bin/sh", "#! /bin/bash", "#!/bin/bash"):
                replace_in_file(self, path, pattern, f"#!{shell}", strict=False)

    def _run_upstream_tests(self):
        log_name = "upstream-test.log"
        # Make the just-built binary load its packaged Motif/X11 chain so the
        # upstream `test:` target actually executes the program and reaches the
        # X-init path (instead of dying in the dynamic linker with no rpath).
        lib_path = ":".join(self._dependency_dirs("lib"))
        script = (
            "{\n"
            f'  export LD_LIBRARY_PATH="{lib_path}:${{LD_LIBRARY_PATH:-}}"\n'
            '  echo "### upstream test census (dinotrace 9.4f) ###"\n'
            "  echo \"$(grep -nE '^(check|test):' Makefile.in)\"\n"
            "  echo '### make -n check ###'\n"
            "  if make -n check >/dev/null 2>&1; then\n"
            '    echo "check-target: PRESENT"\n'
            "    ( unset DISPLAY; timeout 300 make check ) 2>&1 ; echo \"CHECK_EXIT=$?\"\n"
            "  else\n"
            '    echo "check-target: ABSENT (upstream ships no check: target)"\n'
            "  fi\n"
            "  echo '### upstream `make test` verbatim (test: dinotrace_exe) ###'\n"
            "  ( unset DISPLAY; timeout 60 make test ) 2>&1 ; echo \"TEST_EXIT=$?\"\n"
            f"}} > {log_name} 2>&1\n"
        )
        self.run(script, ignore_errors=True, env="conanbuild")
        output = load(self, log_name)
        self.output.info("=== dinotrace 9.4f upstream test step (raw output) ===")
        for line in output.splitlines():
            self.output.info(f"[upstream-test] {line}")
        self.output.info("=== end dinotrace upstream test step ===")

    def _remove_libtool_archives(self):
        for lib_dir in (
            os.path.join(self.package_folder, "lib"),
            os.path.join(self.package_folder, "bin"),
        ):
            if not os.path.isdir(lib_dir):
                continue
            for entry in os.listdir(lib_dir):
                if entry.endswith(".la"):
                    os.remove(os.path.join(lib_dir, entry))
