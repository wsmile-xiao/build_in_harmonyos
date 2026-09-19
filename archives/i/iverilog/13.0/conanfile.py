#!/usr/bin/env python3
"""Conan recipe for Icarus Verilog 13.0 — autotools, OHOS aarch64."""
import os
import platform
import shutil
import tempfile

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run, cross_building
from conan.tools.files import (apply_conandata_patches, copy, export_conandata_patches, get,
                                save)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class IverilogConan(ConanFile):
    name = "iverilog"
    version = "13.0"
    description = "Icarus Verilog — Verilog simulation and synthesis tool"
    license = "GPL-2.0-or-later"
    homepage = "https://steveicarus.github.io/iverilog/"
    url = "https://github.com/steveicarus/iverilog"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    options = {
        "with_readline": [True, False],
        "with_zlib": [True, False],
        "with_bz2": [True, False],
    }
    default_options = {
        "with_readline": True,
        # The registry zlib/bzip2 ship static-only and the zlib archive is not PIC, so the
        # VPI modules (system.vpi) cannot link them ("z_errmsg ... recompile with -fPIC").
        # Keep the options available but off by default until a PIC/shared build exists.
        "with_zlib": False,
        "with_bz2": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        if self.options.with_readline:
            self.requires("readline/8.3")
        if self.options.with_zlib:
            self.requires("zlib/1.3.1")
        if self.options.with_bz2:
            self.requires("bzip2/1.0.8")

    def build_requirements(self):
        # Codegen tools (parser/lexer/keyword table). The registry ships OHOS (aarch64)
        # binaries, which is what native CI (real aarch64 machine) consumes. On an x86_64
        # build host -- including the WSL workflow where host and build profiles are both
        # the OHOS cross profile and Conan reports no cross build -- use host tools from PATH.
        machine = platform.machine().lower()
        if not cross_building(self) and machine in ("aarch64", "arm64"):
            self.tool_requires("bison/3.8.2")
            self.tool_requires("flex/2.6.4")
            self.tool_requires("gperf/3.3")
        else:
            missing = [t for t in ("bison", "flex", "gperf", "m4")
                       if shutil.which(t) is None]
            if missing:
                raise ConanInvalidConfiguration(
                    "Cross build on a non-aarch64 host needs host codegen tools on PATH: "
                    + ", ".join(missing)
                    + " (registry ships OHOS aarch64 binaries only)")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Generate the dependency env first, then override LIBS in the toolchain env.
        # iverilog's AX_PROG_CC_FOR_BUILD sanity link uses the global LIBS, which would
        # otherwise carry target (aarch64) libs into the native build-compiler check and fail.
        # CPPFLAGS/LDFLAGS stay, so configure's AC_CHECK_LIB still finds the target libs.
        AutotoolsDeps(self).generate()
        tc = AutotoolsToolchain(self)
        # iverilog's AX_PROG_CC_FOR_BUILD sanity check and dosify build link the *native*
        # build compiler with the global LIBS (which carries our target aarch64 libs) and
        # fail. Reset LIBS on the configure command line; AC_CHECK_LIB still finds the
        # target libs through the CPPFLAGS/LDFLAGS injected by AutotoolsDeps and appends
        # the -l flags it actually needs.
        tc.configure_args.append("LIBS=")
        # The OHOS worker's config.guess compiles a dummy.c inside a sandboxed tmp dir
        # and hits "Permission denied", so configure aborts with "cannot guess build
        # type". Specify both triples explicitly so config.guess is never consulted:
        #   * CI native (real aarch64): build == host == aarch64-linux-ohos -> native;
        #   * WSL (x86_64 host, armv8 target, same profile so Conan reports no cross):
        #     build=x86_64-pc-linux-gnu, host=aarch64-linux-ohos -> cross (otherwise
        #     configure would try to RUN aarch64 test programs on x86_64).
        if self.settings.os == "OHOS":
            def _triple(machine):
                if machine in ("aarch64", "arm64"):
                    return "aarch64-linux-ohos"
                return "x86_64-pc-linux-gnu"

            host_machine = {"armv8": "aarch64", "x86_64": "x86_64", "x86": "x86"}.get(
                str(self.settings.arch), "aarch64")
            for flag, triple in (("--build=", _triple(platform.machine().lower())),
                                 ("--host=", _triple(host_machine))):
                if not any(a.startswith(flag) for a in tc.configure_args):
                    tc.configure_args.append(flag + triple)
            ac_tmp = os.path.join(tempfile.gettempdir(), "iverilog-ac-tmp")
            os.makedirs(ac_tmp, exist_ok=True)
            tc.environment().define("TMPDIR", ac_tmp)
        # iverilog has no --with-zlib/--with-bz2 switches and auto-detects them via
        # AC_CHECK_LIB. zlib is provided by the OHOS sysroot as a shared, PIC libz.so
        # (the registry zlib is static and not PIC, so it must not be pulled in); bzip2
        # is not in the sysroot at all, so keep that probe off.
        if not self.options.with_bz2:
            tc.configure_args += ["ac_cv_lib_bz2_BZ2_bzdopen=no",
                                  "ac_cv_header_bzlib_h=no"]
        tc.generate()

    def _fix_autoconf_tmpdir(self):
        # E114 (same workaround as archives/a/abiword-plugin-docbook): the HarmonyOS
        # security framework blocks child processes from writing into the ./confXXXXXX
        # temp dir that config.status creates via AS_TMPDIR (and into TMPDIR while
        # compiling conftest): "Permission denied" on subs1.awk / dummy.c. Pre-create a
        # writable dir, point TMPDIR at it and redirect configure's embedded config.status
        # template ac_tmp to it. Also drop the trap that would delete the shared dir.
        fixed_tmp = os.path.join(tempfile.gettempdir(), "iverilog-ac-tmp")
        os.makedirs(fixed_tmp, exist_ok=True)
        os.environ["TMPDIR"] = fixed_tmp
        cfg_path = os.path.join(self.source_folder, "configure")
        if not os.path.exists(cfg_path):
            raise ConanException("E114: configure not found at %s" % cfg_path)
        with open(cfg_path, "r", encoding="utf-8") as fh:
            cfg = fh.read()
        if "ac_tmp=$tmp" not in cfg:
            raise ConanException(
                "E114: ac_tmp=$tmp pattern not found in configure; autoconf template changed")
        cfg = cfg.replace("ac_tmp=$tmp", "ac_tmp=%s" % fixed_tmp)
        old_trap = '{ test ! -d "$ac_tmp" || rm -fr "$ac_tmp"; } && exit $exit_status'
        if old_trap in cfg:
            cfg = cfg.replace(old_trap, "exit $exit_status")
        with open(cfg_path, "w", encoding="utf-8") as fh:
            fh.write(cfg)
        os.chmod(cfg_path, 0o755)
        self.output.info("  [ok] E114: configure ac_tmp -> %s (+TMPDIR)" % fixed_tmp)

    def build(self):
        apply_conandata_patches(self)
        if self.settings.os == "OHOS":
            self._fix_autoconf_tmpdir()
        autotools = Autotools(self)
        autotools.configure()
        # Conan joins make args with spaces and runs through the shell, so the LIBS value
        # must have its spaces escaped to stay a single make argument; otherwise the
        # sub-make for vpi only sees -lreadline and system.vpi fails to dlopen with
        # "gzclose: symbol not found".
        libs_arg = "LIBS=" + self._static_libs().replace(" ", "\\ ")
        autotools.make(args=["-j1", libs_arg])
        # Upstream smoke test (compiles+runs examples/hello.vl). Only on a machine that
        # can execute the target binaries; skipped for cross builds and skip_test profiles.
        if can_run(self) and not self.conf.get("tools.build:skip_test", default=False):
            autotools.make(target="check", args=["-j1", libs_arg])

    def _run_ivtest(self):
        # Run the bundled upstream regression suite (ivtest) with its Python driver.
        # The driver invokes plain `iverilog`/`vvp`, so wrap the installed (relocated)
        # binaries with the module base path and prepend the wrappers to PATH.
        pkg = self.package_folder.replace("\\", "/")
        tools = os.path.join(self.build_folder, "ivtest-tools")
        os.makedirs(tools, exist_ok=True)
        save(self, os.path.join(tools, "iverilog"),
             '#!/bin/sh\nexec "%s/bin/iverilog" -B "%s/lib/ivl" "$@"\n' % (pkg, pkg))
        save(self, os.path.join(tools, "vvp"),
             '#!/bin/sh\nexec "%s/bin/vvp" "$@"\n' % pkg)
        for name in ("iverilog", "vvp"):
            os.chmod(os.path.join(tools, name), 0o755)
        ivtest = os.path.join(self.source_folder, "ivtest")
        # The Python driver consumes the JSON list regress-vvp.list (the other *.list files
        # are for the perl drivers). Skip cases whose JSON asks for -lxt/-lxt2/-fst: those
        # waveform writers are compiled only when BOTH zlib and bzip2 are present, and the
        # OHOS sysroot has no bzip2 (registry bzip2 is static and not PIC, so it cannot be
        # linked into the shared VPI modules).
        import json
        out_list = os.path.join(self.build_folder, "regress-vvp-ohos.list")
        skipped = []
        src_list = os.path.join(ivtest, "regress-vvp.list")
        with open(src_list, "r", encoding="utf-8") as src, \
                open(out_list, "w", encoding="utf-8") as dst:
            for line in src:
                s = line.strip()
                if s and not s.startswith("#"):
                    parts = s.split()
                    try:
                        data = json.load(open(os.path.join(ivtest, parts[1]), encoding="utf-8"))
                    except (OSError, ValueError, IndexError):
                        data = {}
                    if any(a in ("-lxt", "-lxt2", "-fst")
                           for a in (data.get("vvp-args-extended") or [])):
                        skipped.append(parts[0])
                        continue
                dst.write(line)
        self.output.info("  [ivtest] upstream regression suite (Python driver); skipping "
                         "bzip2-dependent waveform cases: %s" % (", ".join(skipped) or "none"))
        # The driver calls plain `iverilog`/`vvp` by name, and PATH changes do not reliably
        # reach the processes it spawns on the CI worker; point it at absolute wrapper paths
        # instead (build-time patch of the test-harness copy only, never the upstream repo).
        run_ivl = os.path.join(ivtest, "run_ivl.py")
        with open(run_ivl, "r", encoding="utf-8") as fh:
            txt = fh.read()
        q = "'"
        txt = txt.replace('"iverilog"+cfg[' + q + 'suffix' + q + ']',
                          '"%s"' % os.path.join(tools, "iverilog"))
        txt = txt.replace('"iverilog"+suffix', '"%s"' % os.path.join(tools, "iverilog"))
        txt = txt.replace('"vvp"+cfg[' + q + 'suffix' + q + ']',
                          '"%s"' % os.path.join(tools, "vvp"))
        with open(run_ivl, "w", encoding="utf-8") as fh:
            fh.write(txt)
        cmd = 'python3 vvp_reg.py "%s"' % out_list
        self.run(cmd, cwd=ivtest)

    def _static_libs(self):
        # The registry readline/ncurses are static-only and configure's `-lreadline` probe
        # cannot resolve readline's ncurses symbols with the empty LIBS we need for
        # iverilog's native build-compiler check. Pin the static link order for every
        # make invocation (build, check and install all re-link the final executables).
        libs = []
        if self.options.with_readline:
            libs += ["-lreadline", "-lhistory"]
        if self.options.with_bz2:
            libs.append("-lbz2")
        # zlib from the OHOS sysroot (shared libz.so); required by the LXT/FST waveform
        # writers in the VPI modules and by vvp itself.
        libs.append("-lz")
        if self.options.with_readline:
            libs += ["-lformw", "-lmenuw", "-lpanelw", "-lncursesw"]
        libs.append("-lpthread")
        return " ".join(libs)

    def package(self):
        autotools = Autotools(self)
        # `make install` depends on `all` and re-links vvp, so it needs the same LIBS.
        autotools.install(args=["LIBS=" + self._static_libs().replace(" ", "\\ ")])
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # Upstream regression suite (ivtest): run against the installed package on a
        # machine that can execute the target binaries (native CI). Any failure fails
        # conan create, so a green CI means every listed case passed.
        if can_run(self) and not self.conf.get("tools.build:skip_test", default=False):
            self._run_ivtest()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
