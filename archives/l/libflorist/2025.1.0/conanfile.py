#!/usr/bin/env python3
"""Conan recipe for libflorist 2025.1.0 -- FLORIST, the POSIX.5 Ada bindings.

Upstream
--------
AdaCore/florist, i.e. the FSU implementation of IEEE STD 1003.5 (POSIX.5),
1003.5b and parts of 1003.5c, maintained for use with GNAT.  2025.1.0 is the
AdaCore "25.1" release; see conandata.yml for the commit-pinned source URL and
the evidence that ties it to that release.

Build system
------------
Autotools: a generated `configure` plus a hand-written `Makefile.in` whose
`floristlib-%` target drives **gprbuild** (`gprbuild -p ... -Pflorist`), plus
two C generator programs that emit Ada specs into `gensrc/`:

    c-posix          -> gensrc/posix.ads, posix-limits.ads,
                        posix-options.ads, posix-c.ads
    c-posix-signals  -> gensrc/posix-implementation-ok_signals.ads

and `gnatprep` to expand the two `*.gpb` templates
(`libsrc/posix-implementation.gpb`,
 `libsrc/threads/posix-timers-extensions.gpb`).

Ada toolchain
-------------
The only Ada toolchain published in ohpcd is `gcc-ada/9.5.0`, and its
assembler/linker come from `binutils/2.46.0`; both are OHOS/armv8 binaries.
There is therefore NO Linux cross compiler for Ada and this recipe can only be
built NATIVELY on OHOS (build == host):

    -pr:h=<ohos-aarch64> -pr:b=<ohos-aarch64>

A cross build is rejected in validate().

gcc-ada ships gnatmake / gnatbind / gnatlink / gnatchop / gnatclean / gnatls
but **neither gprbuild/gprinstall nor gnatprep**.  This recipe accordingly:

  * builds the library with a direct `gnatmake` invocation instead of
    gprbuild, and installs with an explicit layout that reproduces upstream's
    documented prefix layout (`<prefix>/floristlib/*` plus
    `<prefix>/share/gpr/florist.gpr`, see upstream README), and
  * ships a minimal `gnatprep` stand-in (tools/gnatprep-shim.py).

Platform findings (all reproduced locally on an OHOS/aarch64 worker).  Only one
of them needs a patch; the others are handled inside this recipe:

  E007   The bundled config.guess/config.sub know nothing about HarmonyOS, so
         `--host=aarch64-unknown-linux-ohos` is rejected and a configure run
         that relies on auto-detection aborts with "cannot guess build type".
         NOT triggered here: this configure never calls config.guess for the
         triple, because both triples are passed explicitly (see E064 below),
         so no config.guess/config.sub patch is shipped.
  E064   configure compiles and RUNS a conftest; OHOS refuses to exec an
         unsigned ELF, so configure dies with "cannot run C compiled
         programs".  Exporting cross_compiling=yes is not enough (AC_PROG_CC
         recomputes it), so `--build` and `--host` are given DIFFERENT triples
         to make autoconf take the canonical cross path.  Same lever as
         archives/l/libncursesada and archives/a/abiword-plugin-openwriter.
  HMDFS  `configure`/`config.status` create their temp directory with
         `umask 077`, which on HMDFS yields a directory that cannot be written
         to ("can't create ./confXXXXXX/subs1.awk: Permission denied").
         Handled by the `mktemp` shim in tools/ (no patch; the generated
         configure is left byte-identical to upstream, per R6).
  musl   `sigismember()` returns 0 (not glibc's -1) for out-of-range signals,
         so both generators concluded the signal range was invalid and emitted
         a negative count (`NSIGS : constant := -2`), which made the generated
         `posix-signals.ads` invalid Ada.
         -> patches/0001-musl-signal-range.patch (the only patch in this recipe)
  stdio  The two C generators must be linked **statically**.  A dynamically
         linked gcc-ada binary segfaults on the first stdio `stderr` access on
         this runtime (raw write(2) is fine); `-static` works.
"""
import glob
import os
import shlex
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.layout import basic_layout

# configure switches that make autoconf take the cross path (E064).  The exact
# triples matter only in that they must DIFFER from each other.
_CONFIGURE_CROSS_ARGS = (
    "--build=x86_64-unknown-linux-gnu "
    "--host=aarch64-unknown-linux-ohos "
    "cross_compiling=yes "
    "ac_cv_c_compile_works=yes "
    "ac_cv_prog_cc_cross=yes"
)

# Upstream florist.gpr Ada switches for the default (Production) build:
#   Ada_Flags := ("-O2", "-gnatp", "-gnat95");
# Upstream additionally applies GNAT_Flags (Ada_Flags & "-gnatg") to four units
# (posix-signals, posix-implementation, posix-supplement_to_ada_io,
# posix-unsafe_process_primitives).  "-gnatg" only suppresses style/portability
# diagnostics for GNAT-internal units and is accepted by neither the gnat95
# profile nor the plain gnatmake driver, so every unit is compiled with the
# common flags below.
_ADAPFLAGS = "-gnat95 -gnatp -O2"

# Install layout, matching upstream's gprinstall invocation
# (--sources-subdir/floristlib --lib-subdir/floristlib) and its README.
_SOURCES_SUBDIR = "floristlib"
_GPR_SUBDIR = os.path.join("share", "gpr")


class LibFloristConan(ConanFile):
    name = "libflorist"
    version = "2025.1.0"
    description = ("FLORIST -- implementation of the IEEE 1003.5 (POSIX.5), "
                   "1003.5b and parts of 1003.5c Ada bindings for GNAT")
    license = "GPL-2.0-or-later WITH GCC-exception-2.0"
    homepage = "https://github.com/AdaCore/florist"
    url = ""
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}
    exports_sources = ("conandata.yml", "patches/*", "tools/*")

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libflorist is supported on Linux/OHOS only")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")
        if self.options.shared:
            raise ConanInvalidConfiguration(
                "libflorist is static-only on OHOS: gcc-ada installs the Ada "
                "runtime as NON-PIC static archives (adalib/libgnat.a), which "
                "cannot be linked into a shared object. Use shared=False.")
        if cross_building(self):
            raise ConanInvalidConfiguration(
                "libflorist requires a NATIVE OHOS build: the only Ada "
                "toolchain published in ohpcd (gcc-ada/9.5.0) and its "
                "binutils/2.46.0 are OHOS/armv8 binaries, so no Linux cross "
                "compiler exists. Use -pr:h=<ohos-aarch64> -pr:b=<ohos-aarch64>")

    def layout(self):
        basic_layout(self)

    def build_requirements(self):
        self.tool_requires("gcc-ada/9.5.0")
        self.tool_requires("binutils/2.46.0")

    # ------------------------------------------------------------------ tools
    def _dep_bindir(self, name):
        """Package bin/ directory of a build requirement."""
        dep = self.dependencies.build.get(name)
        if dep is None or not dep.package_folder:
            return ""
        for candidate in list(dep.cpp_info.bindirs or []) + ["bin"]:
            path = os.path.join(dep.package_folder, candidate)
            if os.path.isdir(path):
                return path
        return ""

    def _tool(self, name):
        """Absolute path of an Ada toolchain program, else a PATH lookup."""
        bindir = self._dep_bindir("gcc-ada")
        path = os.path.join(bindir, name) if bindir else ""
        if path and os.path.isfile(path):
            return path
        return shutil.which(name) or name

    def _ada_root(self):
        """Directory holding adainclude/ and adalib/ for the GNAT runtime."""
        bindir = self._dep_bindir("gcc-ada")
        if not bindir:
            return ""
        folder = os.path.dirname(bindir)
        found = sorted(glob.glob(os.path.join(folder, "lib", "gcc", "*", "*")))
        for root in found:
            if os.path.isdir(os.path.join(root, "adainclude")):
                return root
        return ""

    def _recipe_tool(self, name):
        """Absolute path of a helper shipped in this recipe's tools/ directory.

        `self.recipe_folder` does not point at the exported sources on every
        Conan code path, so the candidates are probed in order and a missing
        helper is a hard error (silently skipping it produced a confusing
        configure failure once already).
        """
        candidates = []
        for folder in (self.export_sources_folder, self.recipe_folder,
                       self.source_folder):
            if folder:
                candidates.append(os.path.join(folder, "tools", name))
        here = os.path.dirname(os.path.abspath(__file__))
        candidates.append(os.path.join(here, "tools", name))
        for path in candidates:
            if path and os.path.isfile(path):
                return path
        raise ConanInvalidConfiguration(
            "recipe helper tools/{} not found (searched: {})".format(
                name, ", ".join(candidates)))

    # --------------------------------------------------------------- generate
    def generate(self):
        # gcc-ada exports ADA_INCLUDE_PATH / ADA_OBJECTS_PATH / GCC_EXEC_PREFIX
        # through buildenv_info; they only materialise once VirtualBuildEnv is
        # generated.  Without them gnatmake reports
        # "fatal error, run-time library not installed correctly".
        VirtualBuildEnv(self).generate()

        env = Environment()
        gcc = self._tool("gcc")
        env.define("CC", gcc)
        env.define("CXX", self._tool("g++"))
        # Pin CPP to the SAME driver as CC: left to autoconf, AC_PROG_CPP can
        # settle on the host /lib/cpp, which cannot find cc1 under our
        # GCC_EXEC_PREFIX.
        env.define("CPP", "{} -E".format(gcc))
        # gcc resolves `as`/`ld` through PATH; /usr/bin/as cannot assemble for
        # the OHOS target, and the worker's own binutils live in
        # /data/service/hnp/bin, so put both toolchain directories first.
        for bindir in (self._dep_bindir("binutils"), "/data/service/hnp/bin"):
            if bindir:
                env.prepend_path("PATH", bindir)
        bindir = self._dep_bindir("gcc-ada")
        if bindir:
            env.prepend_path("PATH", bindir)

        ada_root = self._ada_root()
        if ada_root:
            env.define("ADA_INCLUDE_PATH", os.path.join(ada_root, "adainclude"))
            env.define("ADA_OBJECTS_PATH", os.path.join(ada_root, "adalib"))
        if bindir:
            folder = os.path.dirname(bindir)
            env.define("GCC_EXEC_PREFIX", os.path.join(folder, "lib", "gcc") + os.sep)

        # E114/HMDFS: subprocesses must not create files in the default tmpdir.
        tmp = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmp, exist_ok=True)
        for name in ("TMPDIR", "TMP", "TEMP"):
            env.define(name, tmp)
        # The CI profile injects CONFIG_SHELL/SHELL pointing at the HNP bash,
        # whose getcwd() misbehaves on HMDFS and makes autoconf write a garbage
        # srcdir.  An env var defined here wins over the profile [buildenv].
        env.define("CONFIG_SHELL", "/bin/sh")
        env.define("SHELL", "/bin/sh")

        # HMDFS: autoconf creates its scratch dir under `umask 077`, which on
        # HMDFS is not writable, so config.status dies with
        # "can't create ./confXXXXXX/subs1.awk: Permission denied".  A `mktemp`
        # shim placed FIRST on PATH makes that directory writable without
        # editing the generated configure (R6).
        shim_bindir = os.path.join(self.generators_folder, "florist-shims")
        os.makedirs(shim_bindir, exist_ok=True)
        shim_path = os.path.join(shim_bindir, "mktemp")
        shutil.copy2(self._recipe_tool("mktemp"), shim_path)
        os.chmod(shim_path, 0o755)
        env.prepend_path("PATH", shim_bindir)
        env.vars(self).save_script("florist_buildenv")

    def _build_env(self):
        return ["conanbuild", "florist_buildenv"]

    # ----------------------------------------------------------------- source
    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ------------------------------------------------------------ C generators
    def _find_sdk_tool(self, name):
        """Locate an OHOS SDK tool (llvm-objcopy / binary-sign-tool)."""
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        compiler_dir = os.path.dirname(compilers.get("cpp", ""))
        candidates = [
            os.path.join(compiler_dir, name) if compiler_dir else "",
            os.path.join("/data/service/hnp/bin", name),
            shutil.which(name) or "",
        ]
        return next((p for p in candidates if p and os.path.isfile(p)), "")

    def _sign_executable(self, path):
        """Sign an ELF in place so OHOS will execute it (E489/E517).

        `path` must be absolute: this recipe runs from Conan's own working
        directory, so a bare name would be resolved against the wrong folder.

        Without this, running a freshly linked binary fails with
        "./c-posix: Permission denied" (rc=126).
        """
        objcopy = self._find_sdk_tool("llvm-objcopy")
        signer = self._find_sdk_tool("binary-sign-tool")
        if not objcopy or not signer:
            raise ConanInvalidConfiguration(
                "executing the C generators on OHOS requires llvm-objcopy and "
                "binary-sign-tool")
        path = os.path.abspath(path)
        if not os.path.isfile(path):
            raise ConanInvalidConfiguration(
                "cannot sign missing executable: {}".format(path))
        mode = os.stat(path).st_mode
        self.run('"{}" --remove-section .codesign "{}"'.format(objcopy, path),
                 cwd=self.source_folder, env=self._build_env())
        self.run('"{}" sign -inFile "{}" -outFile "{}" -selfSign 1'.format(
            signer, path, path), cwd=self.source_folder, env=self._build_env())
        os.chmod(path, mode)

    def _build_c_generators(self):
        """Compile c-posix / c-posix-signals.

        They are linked statically on purpose: a dynamically linked gcc-ada
        binary segfaults on the first stdio `stderr` access on this runtime,
        while `-static` runs correctly.
        """
        for program in ("c-posix", "c-posix-signals"):
            extra = ""
            libs = ""
            if program == "c-posix":
                extra = (' -DVERSION=\\"{v}\\" -DLIBS=\\"-lpthread\\"'
                         .format(v=self.version))
                libs = "-lpthread"
            self.run(
                '{} -O2 -static -DGENDIR=\\"gensrc\\"{extra} '
                '-o {prog} {prog}.c {libs}'.format(
                    shlex.quote(self._tool("gcc")), extra=extra,
                    prog=program, libs=libs),
                cwd=self.source_folder, env=self._build_env())
            target = os.path.join(self.source_folder, program)
            if not os.path.isfile(target):
                raise ConanInvalidConfiguration(
                    "failed to build C generator {}".format(program))
            self._sign_executable(target)

    # ---------------------------------------------------------------- configure
    def _run_configure(self):
        # configure is run IN-SOURCE: upstream's Makefile builds gensrc/, obj/
        # and lib/ relative to the source tree.
        self.run(
            'CONFIG_SHELL=/bin/sh SHELL=/bin/sh "{}" {}'.format(
                os.path.join(self.source_folder, "configure"),
                _CONFIGURE_CROSS_ARGS),
            cwd=self.source_folder, env=self._build_env())

    # ---------------------------------------------------------- generated Ada
    def _generate_ada_sources(self):
        gensrc = os.path.join(self.source_folder, "gensrc")
        os.makedirs(os.path.join(gensrc, "threads"), exist_ok=True)

        # 1. c-posix writes its four specs relative to GENDIR, so the cwd must
        #    be the source root.
        self.run("./c-posix > c-posix.log 2>&1", cwd=self.source_folder,
                 env=self._build_env())
        # 2. c-posix-signals emits posix-implementation-ok_signals.ads.
        self.run("./c-posix-signals -nodefaults > c-posix-signals.log 2>&1",
                 cwd=self.source_folder, env=self._build_env())
        # 3. gnatprep over the two templates (gcc-ada ships no gnatprep).
        #    The shim is located via _recipe_tool(): exports_sources lands the
        #    tools/ directory under Conan's export_source folder, not under
        #    self.recipe_folder.
        shim = self._recipe_tool("gnatprep-shim.py")
        gnatprep_config = os.path.join(self.source_folder, "gnatprep.config")
        if not os.path.isfile(gnatprep_config):
            raise ConanInvalidConfiguration(
                "configure did not produce gnatprep.config")
        for src, dst in (
                ("libsrc/posix-implementation.gpb",
                 "gensrc/posix-implementation.adb"),
                ("libsrc/threads/posix-timers-extensions.gpb",
                 "gensrc/threads/posix-timers-extensions.adb")):
            self.run(
                '{} "{}" "{}" "{}" "{}" -c -r'.format(
                    shlex.quote(sys.executable or "python3"), shim,
                    os.path.join(self.source_folder, src),
                    os.path.join(self.source_folder, dst),
                    gnatprep_config),
                cwd=self.source_folder, env=self._build_env())
            if not os.path.isfile(os.path.join(self.source_folder, dst)):
                raise ConanInvalidConfiguration(
                    "gnatprep shim did not produce {}".format(dst))

    # ------------------------------------------------------------------- build
    def build(self):
        apply_conandata_patches(self)
        # Order matters and mirrors upstream's Makefile: the C generators
        # `#include "confsrc/pconfig.h"`, which is produced BY configure
        # (`c-posix: c-posix.c confsrc/config.h confsrc/pconfig.h`), so
        # configure must run first.
        self._run_configure()
        self._build_c_generators()
        self._generate_ada_sources()
        self._compile_florist()
        self._archive_library()
        self._build_and_run_upstream_tests()

    def _ada_include_flags(self):
        return ("-Ilibsrc -Ilibsrc/threads -Igensrc -Igensrc/threads "
                "-Iconfsrc")

    def _ada_units(self):
        units = []
        for pattern in ("libsrc/*.adb", "libsrc/threads/*.adb",
                        "gensrc/*.adb", "gensrc/threads/*.adb",
                        "confsrc/*.adb"):
            units.extend(sorted(os.path.basename(path) for path in
                                glob.glob(os.path.join(self.source_folder,
                                                       pattern))))
        return units

    def _compile_florist(self):
        """Compile every Florist unit with gnatmake (gprbuild substitute)."""
        units = self._ada_units()
        if not units:
            raise ConanInvalidConfiguration("no Ada units found to compile")
        objdir = os.path.join(self.source_folder, "obj")
        shutil.rmtree(objdir, ignore_errors=True)
        os.makedirs(objdir, exist_ok=True)
        # -Dobj keeps the object/ALI tree in one place so package() can mirror
        # it; -gnatp matches upstream's GNAT_Flags (-O2 -gnatp -gnat95).
        self.run(
            '{} -c -f {flags} -Dobj {incs} {units}'.format(
                shlex.quote(self._tool("gnatmake")),
                flags=_ADAPFLAGS,
                incs=self._ada_include_flags(),
                units=" ".join(shlex.quote(u) for u in units)),
            cwd=self.source_folder, env=self._build_env())
        self._compile_c_units(objdir)

    def _compile_c_units(self, objdir):
        """Compile the C units that belong to the library.

        florist.gpr declares `for Languages use ("C", "Ada")`, so
        libsrc/posix-macros.c (fetch_errno/store_errno, wifexited, s_isdir, ...)
        and libsrc/posix-macros-sockets.c (c_ntohl/c_htonl, ...) are part of
        the library.  gnatmake handles only Ada, so the compiler driver (never
        a bare $CC shell variable, R33) is invoked explicitly for them; without
        this the final link fails with
            undefined reference to `store_errno' / `fetch_errno'
        """
        cc = self._tool("gcc")
        confsrc = os.path.join(self.source_folder, "confsrc")
        for source in ("libsrc/posix-macros.c", "libsrc/posix-macros-sockets.c"):
            obj = os.path.join(
                objdir, os.path.basename(source)[:-2] + ".o")
            self.run(
                '{} -c -O2 -fPIC -I{} -I{} -o {} {}'.format(
                    shlex.quote(cc),
                    shlex.quote(os.path.join(self.source_folder, "libsrc")),
                    shlex.quote(confsrc), shlex.quote(obj),
                    shlex.quote(source)),
                cwd=self.source_folder, env=self._build_env())
            if not os.path.isfile(obj):
                raise ConanInvalidConfiguration(
                    "failed to compile library C unit {}".format(source))

    def _archive_library(self):
        objdir = os.path.join(self.source_folder, "obj")
        objects = sorted(glob.glob(os.path.join(objdir, "*.o")))
        if not objects:
            raise ConanInvalidConfiguration(
                "Ada compilation produced no object files")
        libdir = os.path.join(self.source_folder, "lib")
        os.makedirs(libdir, exist_ok=True)
        archive = os.path.join(libdir, "libflorist.a")
        if os.path.exists(archive):
            os.remove(archive)
        self.run(
            '{} rcs {} {}'.format(
                shlex.quote(self._tool("ar") or "ar"),
                shlex.quote(archive),
                " ".join(shlex.quote(o) for o in objects)),
            cwd=self.source_folder, env=self._build_env())

    # ----------------------------------------------------------- upstream tests
    def _upstream_test_names(self, tests_dir):
        """Test programs listed by tests/Makefile (TESTS + SPECIAL_TESTS).

        Make resolves the (backslash-continued) variable definitions itself:
        a tiny helper makefile appended with -f writes both variables to a
        file.  Re-implementing makefile parsing here is not worth the risk --
        a hand-rolled parser once leaked the literal token "SPECIAL_TESTS="
        into the target list and make then misparsed the whole makefile as
        options/targets.
        """
        helper = os.path.join(self.build_folder, "florist-print-tests.mk")
        listing = os.path.join(self.build_folder, "florist-tests-raw.txt")
        with open(helper, "w") as handle:
            handle.write(
                "print-florist-tests:\n"
                "\t@printf '%s\\n' $(TESTS) $(SPECIAL_TESTS) > \"{}\"\n"
                .format(listing))
        self.run(
            'make -f Makefile -f "{}" print-florist-tests'.format(helper),
            cwd=tests_dir, env=self._build_env())
        names = []
        if os.path.isfile(listing):
            with open(listing, "r", errors="replace") as handle:
                for token in handle.read().split():
                    if token and token not in names:
                        names.append(token)
        return names

    def _build_and_run_upstream_tests(self):
        """Build and run the upstream POSIX.5b validation suite (R51 step 2).

        tests/Makefile compiles each listed test with gnatmake against
        ../lib/libflorist.a.  Running them needs two OHOS-specific extras that
        upstream's own run_tests_1 knows nothing about -- signing (OHOS refuses
        unsigned ELF) and a PTY on stderr (tests/README: "Some tests require
        that the standard error file be a terminal") -- so the run is driven by
        tools/run_upstream_tests.py, which also writes the machine-readable
        result table used as R51 evidence.

        Assertion failures are recorded, not fatal: they are platform
        observations to be explained in notes.md / the test report.  A missing
        suite or a suite that links nothing is a real error.
        """
        tests_dir = os.path.join(self.source_folder, "tests")
        if not os.path.isdir(tests_dir):
            raise ConanInvalidConfiguration(
                "upstream tests/ directory is missing from the source tree")
        names = self._upstream_test_names(tests_dir)
        if not names:
            raise ConanInvalidConfiguration(
                "no upstream tests listed in tests/Makefile")
        self.output.info("  upstream test entries listed: {}".format(len(names)))

        names_file = os.path.join(self.build_folder, "upstream-tests.txt")
        with open(names_file, "w") as handle:
            handle.write("\n".join(names) + "\n")

        # tests/Makefile compiles every test in one go; the archive must be at
        # ../lib/libflorist.a, which _archive_library() already produced.
        self.run(
            'make -f Makefile {}'.format(
                " ".join(shlex.quote(n) for n in names)),
            cwd=tests_dir, env=self._build_env())

        run_dir = os.path.join(tests_dir, "test.dir")
        if not os.path.isdir(run_dir):
            os.makedirs(run_dir, exist_ok=True)
            # Some tests rely on the `bin -> ..` symlink that upstream's
            # `test.dir` target creates.
            link = os.path.join(run_dir, "bin")
            if not os.path.exists(link):
                try:
                    os.symlink(os.path.pardir, link)
                except OSError:
                    pass

        results = os.path.join(self.build_folder, "upstream-results.txt")
        self.run(
            '{} "{}" --tests-dir "{}" --names "{}" --run-dir "{}" '
            '--timeout 45 --results "{}"'.format(
                shlex.quote(sys.executable or "python3"),
                shlex.quote(self._recipe_tool("run_upstream_tests.py")),
                shlex.quote(tests_dir), shlex.quote(names_file),
                shlex.quote(run_dir), shlex.quote(results)),
            cwd=self.build_folder, env=self._build_env())

        if os.path.isfile(results):
            with open(results, "r", errors="replace") as handle:
                table = handle.read()
            executed = sum(1 for line in table.splitlines()
                           if line.split()[-1] != "NOT_LINKED")
            passed = sum(1 for line in table.splitlines()
                         if line.endswith(" PASS"))
            self.output.info(
                "  upstream tests: {}/{} executed, {} passed".format(
                    executed, len(names), passed))

    # ----------------------------------------------------------------- package
    def package(self):
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # Installed exactly where upstream's own documentation tells consumers
        # to look: <prefix>/floristlib (sources + ALI + static library) and
        # <prefix>/share/gpr/florist.gpr.
        dst = os.path.join(self.package_folder, _SOURCES_SUBDIR)
        os.makedirs(dst, exist_ok=True)
        for pattern in ("*.ads", "*.adb", "*.ali", "*.a"):
            for root in ("libsrc", "libsrc/threads", "gensrc",
                         "gensrc/threads", "confsrc", "obj", "lib"):
                source = os.path.join(self.source_folder, root)
                if os.path.isdir(source):
                    copy(self, pattern, src=source, dst=dst, keep_path=False)
        self._install_gpr()

    def _install_gpr(self):
        """Install a florist.gpr usable from the packaged prefix.

        Upstream's project file points Source_Dirs at the build tree
        (libsrc/gensrc/confsrc), which does not exist once installed, so the
        installed copy is retargeted at the flat floristlib directory.

        The .gpr lives in <prefix>/share/gpr while the specs and libflorist.a
        live in <prefix>/floristlib — a sibling directory.  GPR resolves
        relative directories against the directory CONTAINING the project
        file, so the paths must ascend out of share/gpr (the same convention
        the libgmpada recipe uses in its _rewrite_gpr()).
        """
        gpr_dir = os.path.join(self.package_folder, _GPR_SUBDIR)
        os.makedirs(gpr_dir, exist_ok=True)
        # From <prefix>/share/gpr, "../.." is <prefix>.
        lib_rel = os.path.join(os.pardir, os.pardir, _SOURCES_SUBDIR)
        content = (
            "library project Florist is\n"
            "\n"
            "   for Library_Name use \"florist\";\n"
            "   for Languages use (\"C\", \"Ada\");\n"
            "\n"
            "   for Source_Dirs use (\"{lib}\");\n"
            "   for Object_Dir use \"{lib}\";\n"
            "   for Library_Dir use \"{lib}\";\n"
            "\n"
            "   for Library_Kind use \"static\";\n"
            "end Florist;\n").format(lib=lib_rel)
        with open(os.path.join(gpr_dir, "florist.gpr"), "w") as handle:
            handle.write(content)
        # Keep the upstream project file alongside it for reference.
        upstream = os.path.join(self.source_folder, "florist.gpr")
        if os.path.isfile(upstream):
            shutil.copy2(upstream,
                         os.path.join(gpr_dir, "florist.gpr.upstream"))

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "libflorist")
        self.cpp_info.libs = ["florist"]
        self.cpp_info.includedirs = [_SOURCES_SUBDIR]
        self.cpp_info.libdirs = [_SOURCES_SUBDIR]
        self.cpp_info.bindirs = []
        adalib = os.path.join(self.package_folder, _SOURCES_SUBDIR)
        for info in (self.buildenv_info, self.runenv_info):
            info.prepend_path("ADA_INCLUDE_PATH", adalib)
            info.prepend_path("ADA_OBJECTS_PATH", adalib)
