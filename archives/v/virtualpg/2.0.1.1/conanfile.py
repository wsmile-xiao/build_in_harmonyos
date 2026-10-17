#!/usr/bin/env python3
"""Conan recipe for VirtualPG 2.0.1."""

import glob
import json
import os
import shutil
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import load_toolchain_args
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rm,
    save,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class VirtualpgConan(ConanFile):
    name = "virtualpg"
    version = "2.0.1.1"
    description = "SQLite virtual table extension for accessing PostgreSQL tables"
    license = "MPL-1.1 OR GPL-2.0-or-later OR LGPL-2.1-or-later"
    homepage = "https://www.gaia-gis.it/fossil/virtualpg/index"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"VirtualPG supports Linux and OHOS, not {self.settings.os}"
            )
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires(
            "sqlite3/3.49.1",
            transitive_headers=True,
            transitive_libs=True,
        )
        self.requires(
            "libpq/18.1",
            transitive_headers=True,
            transitive_libs=True,
        )

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(
            self,
            **self.conan_data["sources"],
            filename="virtualpg-2.0.1.tar.gz",
            strip_root=True,
        )

    def generate(self):
        VirtualBuildEnv(self).generate()
        AutotoolsDeps(self).generate()

        tmpdir = os.path.join(self.build_folder, ".tmp")
        os.makedirs(tmpdir, exist_ok=True)
        shell = self._build_shell()
        environment = Environment()
        environment.define_path("TMPDIR", tmpdir)
        environment.define_path("CONFIG_SHELL", shell)
        environment.define_path("SHELL", shell)
        # Upstream replaces LDFLAGS with pg_config's libdir while probing libpq.
        environment.define("LIBS", "")
        if str(self.settings.os) == "OHOS":
            environment.define("MKDIR_P", "/system/bin/mkdir -p")
        environment.vars(self).save_script("virtualpg_build_env")

        tc = AutotoolsToolchain(self)
        tc.configure_args.append(f"--with-pgconfig={self._pg_config_path()}")
        # R25/R26: prepend the shared libsqlite3.so directory to LDFLAGS so configure's
        # AC_CHECK_LIB(pq/sqlite3) links resolve -lsqlite3 to the shared object
        # (single runtime copy via the dynamic loader) instead of the dependency's
        # static archive. -rpath-link records the search path for the dynamic loader
        # in case configure tries to run a linked conftest.
        #
        # R26 fix: inject via tc.extra_ldflags (merged into the toolchain's LDFLAGS by
        # AutotoolsToolchain) instead of tc.configure_args.append('LDFLAGS=...'). The
        # latter appends a SECOND 'LDFLAGS=' assignment to the configure command line;
        # shell processes trailing 'VAR=val' assignments by overwriting earlier ones, so
        # R25's value replaced AutotoolsToolchain's own LDFLAGS (which carries
        # AutotoolsDeps' --sysroot/runtime search paths). sqlite3's AC_CHECK_LIB probe
        # then linked conftest with no sysroot -> could not find libc/libsqlite3 runtime
        # deps -> 'checking for sqlite3_prepare_v2 in -lsqlite3... no' -> configure
        # fatal. This is the same class of bug as R8 (pq probe): upstream's
        # `LDFLAGS="$PG_LDFLAGS"` replacement vs R25's command-line override. extra_ldflags
        # is appended to the existing LDFLAGS, preserving sysroot/runtime.
        sqlite_shared_dir = self._sqlite_shared_dir()
        # R33 fix: do NOT wrap paths in literal double quotes here. Conan's
        # save_sh() runs value.replace('"', '\\"') on the whole LDFLAGS string,
        # so a manually-added '"' becomes '\"' — lld then sees
        # -L\"/storage/.../sqlite3-shared\" and treats '\"' as path characters,
        # the directory does not exist, -l:libsqlite3.so fails to resolve, and
        # configure's earliest AC_PROG_CC probe dies with
        # "C compiler cannot create executables". The HMBS preflight paths contain
        # no spaces, so unquoted -L/-rpath-link values are safe and lld finds
        # libsqlite3.so in sqlite_shared_dir.
        tc.extra_ldflags.append(f'-L{sqlite_shared_dir}')
        tc.extra_ldflags.append(f'-Wl,-rpath-link,{sqlite_shared_dir}')
        # R35: drop the LDFLAGS-injected -l:libsqlite3.so / --no-as-needed entirely.
        # R32 put -l:libsqlite3.so in extra_ldflags (merged into LDFLAGS); the true
        # machine proved lld 15 does NOT NEEDED libsqlite3.so from -l:NAME, so the
        # resulting libvirtualpg.so had no NEEDED libsqlite3.so and test_package failed
        # with 20+ undefined sqlite3_* references. R34 replaced -l: with -Wl,--no-as-needed
        # (still in extra_ldflags), but libtool expands $(LDFLAGS) AFTER $(LIBS) in its
        # link command, so --no-as-needed ended up AFTER -lsqlite3 and had no effect.
        #
        # R35 moves the --no-as-needed + -lsqlite3 injection OUT of LDFLAGS and into
        # la_LDFLAGS in _make_args(), where libtool parses it token-by-token but the
        # flags appear in the correct command-line position (la_LDFLAGS expands BEFORE
        # $(LIBS) in libtool's link command, so --no-as-needed is active when lld
        # processes the la_LDFLAGS -lsqlite3, and remains active when $(LIBS)'s bare
        # -lsqlite3 is processed next). See _make_args() for the la_LDFLAGS construction.
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        self._build_pg_config_query()
        # R25: build a shared libsqlite3.so from the dependency's static archive so
        # every -lsqlite3 link (upstream Makefile's $(LIBS), the Conan consumer
        # test, and any downstream consumer) NEEDED the same shared object. The
        # HarmonyOS dynamic loader deduplicates a NEEDED .so to one in-process copy,
        # which is the only way to give libvirtualpg.so and the consumer executable
        # a single sqlite3 implementation. Two privately-inlined copies of the
        # amalgamation (one in the .so via $(LIBS), one in the executable via
        # -lsqlite3) each carry their own runtime global state (mutex allocator,
        # per-process counters); the .so's copy walks db->mutex through its own
        # implementation on a pointer handed out by the executable's copy -> SIGSEGV.
        # Linker flags that force the .so to export its copy, or the executable to
        # export its copy to the .so's PLT, all failed across R1-R24 (HarmonyOS
        # loader does not resolve a .so's PLT against the executable's .dynsym;
        # ld.lld's isExported is gated by isUsedInRegularObj, which no flag, version
        # script, or source anchor set for consumer-only symbols). A single shared
        # library sidesteps all of that: there is exactly one sqlite3 symbol table
        # in the process, loaded once by the dynamic loader.
        self._build_sqlite3_shared()

        autotools = Autotools(self)
        configure_args = load_toolchain_args(self.generators_folder).get(
            "configure_args", ""
        )
        configure = os.path.join(self.source_folder, "configure")
        self.run(f'"{self._build_shell()}" "{configure}" {configure_args}')
        autotools.make(args=self._make_args())
        autotools.make(target="check", args=self._make_args())
        # HMBS machine-evidence gate: `make check` ran to completion on the real
        # machine above. The upstream release registers zero Automake TESTS
        # (audited tarball: no tests/ dir, no TESTS/check_PROGRAMS/check-local in
        # Makefile.am, no test framework in configure.ac), so report the honest
        # no_tests result rather than a fabricated pass count.
        self.output.info(
            'HMBS_UPSTREAM_TEST_RESULT='
            + json.dumps(
                {
                    "status": "no_tests",
                    "framework": "autotools",
                    "command": "make check -j1",
                    "discovered": 0,
                    "executed": 0,
                    "passed": 0,
                    "failed": 0,
                    "skipped": 0,
                    "reason": (
                        "virtualpg 2.0.1 upstream tarball audited "
                        "(sha256 be2aebeb8c9ff274382085f51d422e823858bca4f6bc2fa90"
                        "9816464c6a1e08b): Makefile.am declares only "
                        "lib_LTLIBRARIES (libvirtualpg.la, mod_virtualpg.la) with "
                        "no TESTS/check_PROGRAMS/check-local targets; tarball "
                        "contains no tests/ directory or test source files; "
                        "configure.ac has no test framework; make check executes "
                        "Automake's empty check target and exits 0 with zero cases"
                    ),
                }
            )
        )

    def _sqlite_shared_dir(self):
        return os.path.join(self.build_folder, "sqlite3-shared")

    def _sqlite3_shared_path(self):
        return os.path.join(self._sqlite_shared_dir(), "libsqlite3.so")

    def _build_sqlite3_shared(self):
        """Build a shared libsqlite3.so from the official sqlite3 amalgamation.

        The sqlite3/3.49.1 dependency ships only a static libsqlite3.a. Every
        -lsqlite3 link of that archive privately inlines a complete sqlite3
        implementation, and two inlined copies in one process (libvirtualpg.so +
        the consumer) carry divergent runtime global state that crashes the
        SQLite mutex subsystem. Wrapping the amalgamation into a shared object
        once, and making every -lsqlite3 link NEEDED it, leaves the dynamic
        loader as the sole owner of sqlite3 in the process.

        R54: R51-R53 tried to reuse the ohpcd static archive's amalgamation
        member (pure-Python ar extraction + direct link + st_other visibility
        rewrite). The true machine proved that member is useless for a shared
        object: the conan-center CMake build compiles it WITHOUT -fPIC (static
        libraries need no PIC), so lld rejects every aarch64 GOT-generating
        relocation ("recompile with -fPIC"), and it is also compiled with
        -fvisibility=hidden (R53), so its symbols could not be exported anyway.
        Extraction is abandoned entirely: this recipe downloads the official
        sqlite3 3.49.1 amalgamation source (conandata sqlite3_sources, mirror
        first, sha256 pinned) and compiles sqlite3.c itself with -fPIC and
        default visibility, which satisfies both the PIC relocation requirement
        and the STV_DEFAULT export requirement in one step. No force-export
        flags, no ar parsing, no ELF rewriting.
        """
        if self.options.shared is False:
            return
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        compiler = compiler_executables.get("c")
        if not compiler:
            raise ConanException(
                "tools.build:compiler_executables must define the C compiler"
            )
        out_dir = self._sqlite_shared_dir()
        os.makedirs(out_dir, exist_ok=True)
        shared = self._sqlite3_shared_path()
        # R54: fetch the official amalgamation zip (mirror first, official URL
        # last; both sha256-verified to 6cebd1d8...) and extract sqlite3.c +
        # sqlite3.h into a source subdir.
        src_dir = os.path.join(out_dir, "sqlite3-src")
        get(
            self,
            **self.conan_data["sqlite3_sources"],
            destination=src_dir,
            strip_root=True,
        )
        sqlite3_c = os.path.join(src_dir, "sqlite3.c")
        if not os.path.isfile(sqlite3_c):
            raise ConanException(
                f"sqlite3 amalgamation is missing sqlite3.c at {sqlite3_c}"
            )
        # R54: compile the amalgamation ourselves. -fPIC makes the object
        # linkable into a shared object on aarch64 (the ohpcd archive member is
        # non-PIC, R54 log); no -fvisibility=hidden, so every sqlite3_* is
        # STV_DEFAULT and lld -shared exports it by default (the same mechanism
        # that exports libvirtualpg.so's own symbols).
        object_file = os.path.join(out_dir, "sqlite3.o")
        self.run(
            f'"{compiler}" -c -fPIC -O2 -DSQLITE_THREADSAFE=1 '
            f'"{sqlite3_c}" -o "{object_file}"'
        )
        # -ldl: the amalgamation uses dlopen/dlsym for sqlite3_load_extension,
        # and ld.lld --no-allow-shlib-undefined at the consumer link requires
        # those references to be satisfied here.
        self.run(
            f'"{compiler}" -shared -fPIC "{object_file}" -ldl '
            f'-Wl,-soname,libsqlite3.so -o "{shared}"'
        )
        if not os.path.isfile(shared):
            raise ConanException(f"failed to build shared libsqlite3.so at {shared}")
        # R54 diagnostic: the consumer-only APIs must be visible in .dynsym
        # (R50-R53's repeated failure marker; must NOT print R54_DIAG now).
        # llvm-readelf sits next to clang in the toolchain dir; fall back to PATH.
        readelf = os.path.join(os.path.dirname(compiler), "llvm-readelf")
        if not os.path.isfile(readelf):
            readelf = "llvm-readelf"
        self.run(
            f'"{readelf}" --dyn-syms "{shared}" | grep -E '
            f'"sqlite3_open|sqlite3_close|sqlite3_create_module_v2" '
            f'|| echo "R54_DIAG: dynsym lacks sqlite3_open/close/create_module_v2"'
        )
        self.run(f'"{readelf}" --dyn-syms "{shared}" | head -3')

    def package(self):
        Autotools(self).install(args=self._make_args())
        libdir = os.path.join(self.package_folder, "lib")
        rm(self, "*.la", libdir)
        # R25: install the shared libsqlite3.so built in build() so downstream
        # consumers (test_package and real dependents) can link -lsqlite3 against
        # the shared object and load exactly one sqlite3 copy via the dynamic loader.
        if self.options.shared is not False:
            shared = self._sqlite3_shared_path()
            if os.path.isfile(shared):
                copy(
                    self,
                    "libsqlite3.so",
                    src=self._sqlite_shared_dir(),
                    dst=libdir,
                    keep_path=False,
                )
            else:
                raise ConanException(
                    "shared build is missing the expected libsqlite3.so"
                )
        if not self.options.shared:
            rm(self, "mod_virtualpg.a", libdir)
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        self._make_pkg_config_relocatable()
        self._validate_package_artifacts()

    def package_info(self):
        self.cpp_info.libs = ["virtualpg"]
        self.cpp_info.requires = ["sqlite3::sqlite3", "libpq::libpq"]
        self.cpp_info.system_libs = ["m"]
        self.cpp_info.set_property("cmake_file_name", "virtualpg")
        self.cpp_info.set_property("cmake_target_name", "virtualpg::virtualpg")
        self.cpp_info.set_property("pkg_config_name", "virtualpg")

    def _build_shell(self):
        if str(self.settings.os) == "OHOS":
            return "/system/bin/sh"
        shell = os.environ.get("CONFIG_SHELL") or shutil.which("sh")
        if not shell:
            raise ConanException("no POSIX shell is available to run configure")
        return shell

    def _pg_config_path(self):
        return os.path.join(self.build_folder, "pg_config_conan")

    def _build_pg_config_query(self):
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        compiler = compiler_executables.get("c")
        if not compiler:
            raise ConanException(
                "tools.build:compiler_executables must define the C compiler"
            )

        dependency = self.dependencies["libpq"]
        include_dir = dependency.cpp_info.includedirs[0]
        library_dir = dependency.cpp_info.libdirs[0]
        source = os.path.join(self.build_folder, "pg_config_conan.c")
        program = """#include <stdio.h>
#include <string.h>

int main(int argc, char **argv)
{
    if (argc != 2) {
        return 2;
    }
    if (strcmp(argv[1], "--includedir") == 0) {
        puts("%s");
        return 0;
    }
    if (strcmp(argv[1], "--libdir") == 0) {
        puts("%s");
        return 0;
    }
    if (strcmp(argv[1], "--version") == 0) {
        puts("18.1");
        return 0;
    }
    return 1;
}
""" % (self._c_string(include_dir), self._c_string(library_dir))
        save(self, source, program)
        self.run(
            f'"{compiler}" -std=c11 -O2 "{source}" '
            f'-o "{self._pg_config_path()}"'
        )

    @staticmethod
    def _c_string(value):
        return value.replace("\\", "\\\\").replace('"', '\\"')

    def _make_args(self):
        args = ["-j1"]
        if str(self.settings.os) == "OHOS" and self.options.shared:
            # R25/R27/R28/R31: every attempt to pass libsqlite3.so to lld through
            # la_LDFLAGS failed on the true machine:
            #   R27 bare -l:libsqlite3.so -> libtool's -l* parser intercepted it
            #   (ltmain searches libdirs for libNAME.la/.so/.a; NAME=":libsqlite3.so"
            #   matches nothing, libtool dropped the flag).
            #   R28 bare .so full path -> libtool's link mode classifies it as neither
            #   linker_flags (-Wl/-l/-L) nor objects (.la/.o/source), drops it.
            #   R30 -Wl,<path> -> libtool forwarded it but lld 15 does NOT treat a bare
            #   .so path argument as a link INPUT file (unlike GNU ld): no NEEDED, no
            #   dynsym import.
            #   R31 -Wl,-l:libsqlite3.so -> libtool's -Wl,* branch still re-routes the
            #   colon-form -l: token through its -l* glob (matching -l:*), re-routing to
            #   deplibs where libtool searches for lib:libsqlite3.so.la (no match) and
            #   drops it. R15 notes line 364 claimed "-l in -Wl, is not caught by -l*" —
            #   that holds for bare -lNAME but NOT for the colon form -l:NAME.
            # R32 moves the -l:libsqlite3.so injection OUT of la_LDFLAGS entirely and
            # into LDFLAGS via tc.extra_ldflags in generate(). libtool expands $(LDFLAGS)
            # as a make variable into a bare string passed to the underlying linker
            # WITHOUT token-level parsing — libtool does not re-route -l* inside an
            # already-expanded variable value. So -l:libsqlite3.so reaches lld verbatim,
            # lld searches -L<shared_dir> (prepended to LDFLAGS in generate()) for the
            # verbatim name libsqlite3.so, finds _build_sqlite3_shared()'s output,
            # records SONAME libsqlite3.so in the output NEEDED segment, and imports every
            # sqlite3_* .dynsym symbol. Because LDFLAGS expands before $(LIBS) in libtool's
            # link command, lld NEEDEDs libsqlite3.so first; when $(LIBS)'s bare -lsqlite3
            # is processed next every sqlite3_* is already sourced from the NEEDED library
            # and lld does not lazy-pull the dependency's static archive (no inlined second
            # copy). la_LDFLAGS here keeps only -L/-rpath-link (so lld can locate the .so
            # for the NEEDED lookup and the dynamic loader finds it at runtime via the
            # installed copy) and -no-undefined (every sqlite3_* PLT resolves against the
            # NEEDED libsqlite3.so at link time, so ld.lld's --no-allow-shlib-undefined
            # check passes for both the build link and any downstream consumer).
            # R29: the la_LDFLAGS value must CLOSE its opening double quote.
            # Conan Autotools.make() joins args with spaces and runs them under
            # `/bin/sh -c "<joined>"`; an unclosed `"` made toybox's quote state
            # machine swallow the next arg's single-quoted block too, aborting at
            # the compile stage with `/system/bin/sh: no closing quote` before any
            # link ran. The closing `"` is appended to the token tail so make
            # receives VAR="<value>" as one argv slot.
            shared_dir = self._sqlite_shared_dir()
            args.extend(
                (
                    f'libvirtualpg_la_LDFLAGS="-avoid-version -no-undefined '
                    f'-L{shared_dir} -Wl,-rpath-link,{shared_dir} '
                    f'-Wl,--no-as-needed -Wl,-lsqlite3"',
                    "mod_virtualpg_la_LDFLAGS='-module -avoid-version "
                    "-no-undefined $(PG_LDFLAGS) $(PG_LIB)'",
                )
            )
        return args

    def _make_pkg_config_relocatable(self):
        pc_file = Path(self.package_folder, "lib", "pkgconfig", "virtualpg.pc")
        if not pc_file.is_file():
            raise ConanException("upstream install did not produce virtualpg.pc")

        lines = pc_file.read_text(encoding="utf-8").splitlines()
        prefix_lines = [
            index for index, line in enumerate(lines) if line.startswith("prefix=")
        ]
        if len(prefix_lines) != 1:
            raise ConanException(
                "virtualpg.pc must contain exactly one prefix assignment"
            )
        lines[prefix_lines[0]] = "prefix=${pcfiledir}/../.."
        libs_index = next(
            (index for index, line in enumerate(lines) if line.startswith("Libs:")),
            None,
        )
        if libs_index is None:
            raise ConanException("virtualpg.pc does not declare Libs")
        lines.insert(libs_index, "Requires: sqlite3 libpq")
        pc_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _validate_package_artifacts(self):
        include = os.path.join(self.package_folder, "include", "virtualpg.h")
        if not os.path.isfile(include):
            raise ConanException("package is missing include/virtualpg.h")

        libdir = os.path.join(self.package_folder, "lib")
        if glob.glob(os.path.join(libdir, "*.la")):
            raise ConanException("package contains non-relocatable Libtool archives")
        if self.options.shared:
            if glob.glob(os.path.join(libdir, "*.a")):
                raise ConanException("shared package unexpectedly contains archives")
            for stem in ("libvirtualpg", "mod_virtualpg"):
                expected = f"{stem}.so"
                path = os.path.join(libdir, expected)
                if not os.path.isfile(path):
                    raise ConanException(f"package is missing lib/{expected}")
                if str(self.settings.os) == "OHOS":
                    matches = glob.glob(os.path.join(libdir, f"{stem}.so*"))
                    if [os.path.basename(item) for item in matches] != [expected]:
                        raise ConanException(
                            f"OHOS shared package must contain only {expected}: {matches}"
                        )
            # R25: the shared libsqlite3.so we install for the single-runtime-copy
            # layout is the only other .so permitted in a shared package.
            extra_shared = sorted(
                os.path.basename(item)
                for item in glob.glob(os.path.join(libdir, "*.so"))
                if os.path.basename(item) not in ("libvirtualpg.so", "mod_virtualpg.so")
            )
            if extra_shared != ["libsqlite3.so"]:
                raise ConanException(
                    f"shared package may only add libsqlite3.so, found: {extra_shared}"
                )
        else:
            static_library = os.path.join(libdir, "libvirtualpg.a")
            if not os.path.isfile(static_library):
                raise ConanException("static package is missing lib/libvirtualpg.a")
            archives = sorted(
                os.path.basename(path)
                for path in glob.glob(os.path.join(libdir, "*.a"))
            )
            if archives != ["libvirtualpg.a"]:
                raise ConanException(
                    f"static package must contain only libvirtualpg.a: {archives}"
                )
            if glob.glob(os.path.join(libdir, "*.so*")):
                raise ConanException("static package unexpectedly contains shared objects")
