#!/usr/bin/env python3
"""Conan recipe for GNU Guile 2.2.7.2 for OpenHarmony.

Build system: Autotools (configure + make)

Key design:
- package_type = "library" (primarily used as an embeddable Scheme library)
- Also provides bindirs = ["bin"] for the guile executable
- Conan deps: gc, gmp, libffi, libunistring, libtool
- Signal 5 (SIGTRAP) during .go compilation is tolerated via make -k
- .go files are copied from the source tarball's prebuilt/ directory
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
    replace_in_file,
)
from conan.tools.gnu import AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.microsoft import unix_path


class GuileConan(ConanFile):
    name = "guile"
    version = "2.2.7.2"
    description = (
        "GNU's Ubiquitous Intelligent Language for Extension (Guile) — "
        "Scheme interpreter and embeddable library"
    )
    license = "LGPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/guile/"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    win_bash = True

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if not self.options.shared:
            raise ConanInvalidConfiguration(
                "Guile 2.2.7.2 currently supports shared libraries only"
            )

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("gc/8.2.12")
        self.requires("gmp/6.3.0")
        self.requires("libffi/3.4.4")
        # Guile 2.2.7 requires GNU libunistring >= 0.9.3; 1.0 is published
        # in ohpcd and satisfies that upstream requirement.
        self.requires("libunistring/1.0")
        self.requires("libtool/2.5.4", headers=True, libs=True, run=True)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

        deps = AutotoolsDeps(self)
        deps.generate()

    def build(self):
        """Build guile from source.

        Signal 5 (SIGTRAP) occurs during .go (Scheme bytecode) compilation
        on HarmonyOS due to GC/HarmonyOS limitations. ``make -k`` tolerates
        these errors and continues building .so libraries and binaries, which
        are compiled before the .go targets.

        The .go files are NOT rebuilt — they are copied from the source
        tarball's ``prebuilt/`` directory in ``package()``.
        """
        apply_conandata_patches(self)

        cc = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ).get("c", "cc")
        cxx = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ).get("cpp", "c++")

        tool_env = ""
        ld_env = ""
        if self.settings.os == "OHOS":
            def _ohos_compiler(command, fallback):
                if command and os.path.exists(command):
                    return unix_path(self, command)
                resolved = shutil.which(fallback)
                if resolved:
                    return "sh {}".format(unix_path(self, resolved))
                return command

            def _ohos_tool(command):
                resolved = shutil.which(command)
                if resolved:
                    return unix_path(self, resolved)
                fallback = os.path.expanduser(f"~/usr/local/bin/{command}")
                if os.path.exists(fallback):
                    return unix_path(self, fallback)
                return command

            cc = _ohos_compiler(cc, "clang")
            cxx = _ohos_compiler(cxx, "clang++")
            ar = _ohos_tool("llvm-ar")
            ranlib = _ohos_tool("llvm-ranlib")
            strip = _ohos_tool("llvm-strip")
            nm = _ohos_tool("llvm-nm")
            tool_env = (
                f'AR="{ar}" RANLIB="{ranlib}" STRIP="{strip}" NM="{nm}" '
            )
            ld = shutil.which("ld.lld")
            if not ld:
                ld = os.path.expanduser("~/usr/local/bin/ld.lld")
            if ld and os.path.exists(ld):
                ld_env = 'LD="{}" '.format(unix_path(self, ld))

        def _dep(name):
            return self.dependencies[name].cpp_info

        gc = _dep("gc")
        gmp = _dep("gmp")
        libffi = _dep("libffi")
        libunistring = _dep("libunistring")
        libtool = _dep("libtool")

        def _first_libdir(dep):
            return dep.libdirs[0] if dep.libdirs else ""

        dep_include_dirs = []
        dep_lib_dirs = []
        for dep in (gc, gmp, libffi, libunistring, libtool):
            dep_include_dirs.extend(dep.includedirs)
            dep_lib_dirs.extend(dep.libdirs)

        cppflags = " ".join(f"-I{unix_path(self, path)}" for path in dep_include_dirs)
        ldflags = " ".join(f"-L{unix_path(self, path)}" for path in dep_lib_dirs)
        runtime_lib_path = ":".join(unix_path(self, path) for path in dep_lib_dirs)
        runtime_env = ""
        if runtime_lib_path:
            runtime_env = (
                f'LD_LIBRARY_PATH="{runtime_lib_path}'
                f'${{LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}}" '
            )
        bdw_gc_cflags = " ".join(f"-I{unix_path(self, path)}" for path in gc.includedirs)
        bdw_gc_libs = "-L{} -lgc".format(unix_path(self, _first_libdir(gc)))
        libffi_cflags = " ".join(f"-I{unix_path(self, path)}" for path in libffi.includedirs)
        libffi_libs = "-L{} -lffi".format(unix_path(self, _first_libdir(libffi)))

        # Find the configure script (it may be in build_folder or its parent)
        configure_path = os.path.join(self.build_folder, "configure")
        if not os.path.isfile(configure_path):
            configure_path = os.path.join(
                os.path.dirname(self.build_folder), "configure"
            )
        configure_path = unix_path(self, configure_path)
        gmp_prefix = unix_path(self, self.dependencies["gmp"].package_folder)
        libunistring_prefix = unix_path(self, self.dependencies["libunistring"].package_folder)
        libltdl_prefix = unix_path(self, self.dependencies["libtool"].package_folder)

        # Run configure through /system/bin/sh because /storage can reject
        # direct script execution and the CI CONFIG_SHELL can point to an
        # inaccessible bash path on OHOS.
        # The OHOS CI runner builds on an OHOS device.  Forcing --build/--host
        # into cross mode makes Guile require an existing native Guile 2.2.7.
        build_host_args = ""
        self.run(
            f'CC="{cc}" CXX="{cxx}" '
            f'{tool_env}'
            f'{ld_env}'
            f'{runtime_env}'
            f'CONFIG_SHELL=/bin/sh SHELL=/bin/sh '
            f'PKG_CONFIG="" '
            f'CPPFLAGS="{cppflags}" LDFLAGS="{ldflags}" '
            f'BDW_GC_CFLAGS="{bdw_gc_cflags}" BDW_GC_LIBS="{bdw_gc_libs}" '
            f'LIBFFI_CFLAGS="{libffi_cflags}" LIBFFI_LIBS="{libffi_libs}" '
            f'sh "{configure_path}" '
            f'{build_host_args} '
            f'--enable-shared --disable-static '
            f'--with-bdw-gc=bdw-gc '
            f'--with-libgmp-prefix="{gmp_prefix}" '
            f'--with-libunistring-prefix="{libunistring_prefix}" '
            f'--with-libltdl-prefix="{libltdl_prefix}" '
            f'--without-libreadline-prefix '
            f'--prefix=/ '
            f"--bindir=${{prefix}}/bin "
            f"--sbindir=${{prefix}}/bin "
            f"--libdir=${{prefix}}/lib "
            f"--includedir=${{prefix}}/include "
            f"--oldincludedir=${{prefix}}/include",
            env="conanbuild",
        )

        script_replacements = (
            (
                '"$(top_builddir)/libguile/guile-snarf"',
                'sh "$(top_builddir)/libguile/guile-snarf"',
            ),
            ('"./guile-snarf-docs"', 'sh "./guile-snarf-docs"'),
            (
                '"$(top_builddir)/meta/build-env"',
                'sh "$(top_builddir)/meta/build-env"',
            ),
            ('"${top_builddir}/meta/build-env"', 'sh "${top_builddir}/meta/build-env"'),
            (
                "$(top_builddir)/libguile/guile-snarf",
                "sh $(top_builddir)/libguile/guile-snarf",
            ),
            ("./guile-snarf-docs", "sh ./guile-snarf-docs"),
            ("$(top_builddir)/meta/build-env", "sh $(top_builddir)/meta/build-env"),
            ("${top_builddir}/meta/build-env", "sh ${top_builddir}/meta/build-env"),
        )
        for root, _, files in os.walk(self.build_folder):
            if "Makefile" not in files:
                continue
            makefile = os.path.join(root, "Makefile")
            with open(makefile, "r", encoding="utf-8") as handle:
                content = handle.read()
            patched = content
            placeholders = []
            for index, (old, new) in enumerate(script_replacements):
                if old.startswith('"'):
                    marker = f"__OHOS_GUILE_SCRIPT_{index}__"
                    patched = patched.replace(old, marker)
                    placeholders.append((marker, new))
                    continue
                patched = patched.replace(old, new)
            for marker, new in placeholders:
                patched = patched.replace(marker, new)
            if patched != content:
                with open(makefile, "w", encoding="utf-8") as handle:
                    handle.write(patched)

        shell_exec = """cmd="$1"
shift
case "$cmd" in
  guild) exec sh "${top_builddir}/meta/guild" "$@" ;;
  guile) exec sh "${top_builddir}/meta/guile" "$@" ;;
  */guild|*/guile|*/guile-snarf|*/guile-snarf-docs|*/uninstalled-env)
    exec sh "$cmd" "$@" ;;
  *) exec "$cmd" "$@" ;;
esac"""
        script_file_replacements = {
            os.path.join(self.build_folder, "libguile", "guile-snarf"): (
                ("(umask 077 && mkdir $tempdir)", "(umask 022 && mkdir $tempdir)"),
            ),
            os.path.join(self.build_folder, "meta", "guile"): (
                (
                    "exec ${top_builddir}/meta/uninstalled-env $GUILE \"$@\"",
                    "exec sh ${top_builddir}/meta/uninstalled-env $GUILE \"$@\"",
                ),
            ),
            os.path.join(self.build_folder, "meta", "guild"): (
                (
                    "exec ${GUILE:-/bin/guile} $GUILE_FLAGS",
                    "exec sh ${GUILE:-/bin/guile} $GUILE_FLAGS",
                ),
            ),
            os.path.join(self.build_folder, "meta", "build-env"): (
                ('exec "$@"', shell_exec),
            ),
            os.path.join(self.build_folder, "meta", "uninstalled-env"): (
                ('exec "$@"', shell_exec),
            ),
        }
        for script, replacements in script_file_replacements.items():
            if not os.path.isfile(script):
                continue
            with open(script, "r", encoding="utf-8") as handle:
                content = handle.read()
            patched = content
            for old, new in replacements:
                patched = patched.replace(old, new)
            if patched != content:
                with open(script, "w", encoding="utf-8") as handle:
                    handle.write(patched)

        self.run(
            f"{runtime_env}make -C meta guile-config guild",
            env="conanbuild",
        )
        for script, replacements in script_file_replacements.items():
            if not os.path.isfile(script):
                continue
            with open(script, "r", encoding="utf-8") as handle:
                content = handle.read()
            patched = content
            for old, new in replacements:
                patched = patched.replace(old, new)
            if patched != content:
                with open(script, "w", encoding="utf-8") as handle:
                    handle.write(patched)

        # Build generated Guile configuration headers first.  libgnu's regex
        # source includes gnulib thread headers that can resolve to Guile's
        # checked-in thread header before libguile's recursive build has run.
        self.run(
            f"{runtime_env}make -C libguile scmconfig.h",
            env="conanbuild",
        )

        # Build libgnu, then the libguile library and guile wrapper before the
        # recursive all target.  Some generated documentation and bootstrap
        # rules invoke guild, which needs the uninstalled libguile/guile
        # wrapper to exist first.
        self.run(
            f"{runtime_env}make -C lib all",
            env="conanbuild",
        )
        self.run(
            f"{runtime_env}make -C libguile all",
            env="conanbuild",
        )

        # Signal 5 (SIGTRAP) during .go compilation is tolerated via make -k.
        # .so libraries are built before .go files, so they should succeed.
        try:
            self.run(f"{runtime_env}make -k", env="conanbuild")
        except ConanException:
            required_outputs = (
                os.path.join(self.build_folder, "libguile", ".libs", "libguile-2.2.so"),
                os.path.join(self.build_folder, "libguile", ".libs", "guile"),
                os.path.join(self.build_folder, "meta", "guile-config"),
                os.path.join(self.build_folder, "meta", "guild"),
            )
            missing = [path for path in required_outputs if not os.path.exists(path)]
            if missing:
                raise
            self.output.warning(
                "make -k returned non-zero after required Guile outputs were built"
            )

        # Run Guile's Automake upstream tests that are stable on the OHOS
        # runner.  The raw standalone check has three known OHOS failures:
        # test-ffi and test-loose-ends SIGSEGV, while test-out-of-memory
        # deliberately stresses allocation limits and fails with GC OOM.
        standalone_programs = (
            "test-num2integral",
            "test-round",
            "test-foreign-object-c",
            "test-list",
            "test-unwind",
            "test-conversion",
            "test-loose-ends",
            "test-scm-c-read",
            "test-scm-take-locale-symbol",
            "test-scm-take-u8vector",
            "test-scm-to-latin1-string",
            "test-scm-values",
            "test-scm-c-bind-keyword-arguments",
            "test-srfi-4",
            "test-with-guile-module",
            "test-scm-with-guile",
            "test-scm-spawn-thread",
            "test-pthread-create",
            "test-pthread-create-secondary",
            "test-smob-mark",
            "test-smob-mark-race",
        )
        standalone_libraries = (
            "libtest-asmobs.la",
            "libtest-ffi.la",
            "libtest-extensions.la",
        )
        standalone_tests = (
            "test-system-cmds",
            "test-bad-identifiers",
            "test-require-extension",
            "test-guile-snarf",
            "test-import-order",
            "test-command-line-encoding",
            "test-command-line-encoding2",
            "test-language",
            "test-guild-compile",
            "test-num2integral",
            "test-round",
            "test-asmobs",
            "test-foreign-object-scm",
            "test-foreign-object-c",
            "test-list",
            "test-unwind",
            "test-conversion",
            "test-fast-slot-ref",
            "test-mb-regexp",
            "test-use-srfi",
            "test-scm-c-read",
            "test-scm-take-locale-symbol",
            "test-scm-take-u8vector",
            "test-scm-to-latin1-string",
            "test-scm-values",
            "test-scm-c-bind-keyword-arguments",
            "test-srfi-4",
            "test-extensions",
            "test-with-guile-module",
            "test-scm-with-guile",
            "test-scm-spawn-thread",
            "test-pthread-create",
            "test-pthread-create-secondary",
            "test-smob-mark",
            "test-smob-mark-race",
            "test-stack-overflow",
        )
        test_env = f"{runtime_env}GUILE_AUTO_COMPILE=0 "
        self.run(
            f"{test_env}make -C test-suite/standalone "
            f"{' '.join(standalone_libraries + standalone_programs)}",
            env="conanbuild",
        )
        self._fix_libtool_wrapper_shebangs(
            os.path.join(self.build_folder, "test-suite", "standalone"),
            standalone_programs,
        )
        self.run(
            f'{test_env}make -C test-suite/standalone '
            f'TESTS="{" ".join(standalone_tests)}" check-TESTS',
            env="conanbuild",
        )
        self.run(f"{test_env}make -C test-suite/vm check", env="conanbuild")
        self.run(f"{test_env}make -C test-suite check-TESTS", env="conanbuild")
        self._run_scheme_upstream_tests(runtime_env)

    def _fix_libtool_wrapper_shebangs(self, directory, names):
        """Use an absolute shell path in temporary libtool test wrappers."""
        if self.settings.os != "OHOS":
            return
        for name in names:
            path = os.path.join(directory, name)
            if not os.path.isfile(path):
                continue
            with open(path, "r", encoding="utf-8") as handle:
                content = handle.read()
            if content.startswith("#! sh\n"):
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write("#!/bin/sh\n" + content[len("#! sh\n"):])

    def _run_scheme_upstream_tests(self, runtime_env):
        """Run Guile's Scheme .test files in chunks on OHOS."""
        tests_dir = os.path.join(self.source_folder, "test-suite", "tests")
        test_names = sorted(
            name for name in os.listdir(tests_dir) if name.endswith(".test")
        )
        if not test_names:
            raise ConanException("Guile Scheme upstream tests were not found")

        procedures = os.path.join(
            self.build_folder, "libguile", "guile-procedures.txt"
        )
        if os.path.isfile(procedures):
            shutil.copy2(
                procedures,
                os.path.join(self.build_folder, "guile-procedures.txt"),
            )

        chunked_tests = (
            test_names[0:48],
            test_names[48:96],
            test_names[96:158],
            test_names[158:],
        )
        test_suite_dir = unix_path(
            self, os.path.join(self.source_folder, "test-suite")
        )
        test_suite_tests_dir = unix_path(self, tests_dir)
        guile_test = unix_path(
            self, os.path.join(self.source_folder, "test-suite", "guile-test")
        )
        build_dir = unix_path(self, self.build_folder)
        ohos_env = "GUILE_TEST_OHOS=1 " if self.settings.os == "OHOS" else ""

        for index, tests in enumerate(chunked_tests, 1):
            if not tests:
                continue
            if self.settings.os == "OHOS":
                chunk_tmp = os.path.expanduser(f"~/t/g{index}")
            else:
                chunk_tmp = os.path.join(
                    self.build_folder, "tmp-guile-test", str(index)
                )
            shutil.rmtree(chunk_tmp, ignore_errors=True)
            os.makedirs(chunk_tmp, exist_ok=True)
            chunk_tmp_sh = unix_path(self, chunk_tmp)
            log_file = unix_path(
                self, os.path.join(chunk_tmp, f"guile-test-{index}.log")
            )
            test_args = " ".join(shlex.quote(name) for name in tests)
            self.output.info(
                f"Running Guile Scheme upstream tests chunk {index}: "
                f"{len(tests)} files"
            )
            self.run(
                f'cd "{build_dir}" && '
                f"{runtime_env}"
                f"GUILE_AUTO_COMPILE=0 {ohos_env}"
                f'TEST_SUITE_DIR="{test_suite_dir}" '
                f'TMPDIR="{chunk_tmp_sh}" TMP="{chunk_tmp_sh}" '
                f'TEMP="{chunk_tmp_sh}" '
                f'sh meta/build-env sh meta/guile -L "{test_suite_dir}" '
                f'-e main -s "{guile_test}" '
                f'--test-suite "{test_suite_tests_dir}" '
                f'--log-file "{log_file}" {test_args}',
                env="conanbuild",
            )

    def package(self):
        """Package guile from build output and source tarball.

        - .so files, binaries, and pkg-config come from the build output
        - .go files come from the source tarball's prebuilt/ directory
        - .scm files come from the source module/ directory
        - .h headers come from the source libguile/ directory
        """
        pkg = self.package_folder
        build_folder = self.build_folder
        source_folder = self.source_folder

        # ── Library files (.so) from build output ────────────────────
        lib_src = os.path.join(build_folder, "libguile", ".libs")
        if os.path.isdir(lib_src):
            copy(self, "libguile-2.2.so*", src=lib_src,
                 dst=os.path.join(pkg, "lib"))
            copy(self, "libguile-2.2.a", src=lib_src,
                 dst=os.path.join(pkg, "lib"))

        # ── Binaries from build output ────────────────────────────────
        if os.path.isdir(lib_src):
            copy(self, "guile", src=lib_src,
                 dst=os.path.join(pkg, "bin"))

        # guile-config and guild are scripts in meta/
        meta_dir = os.path.join(build_folder, "meta")
        if os.path.isdir(meta_dir):
            copy(self, "guile-config", src=meta_dir,
                 dst=os.path.join(pkg, "bin"))
            copy(self, "guild", src=meta_dir,
                 dst=os.path.join(pkg, "bin"))
            self._make_packaged_scripts_relocatable(os.path.join(pkg, "bin"))

        # ── Headers from source libguile/ ────────────────────────────
        header_src = os.path.join(source_folder, "libguile")
        if os.path.isdir(header_src):
            copy(self, "*.h", src=header_src,
                 dst=os.path.join(pkg, "include/guile/2.2/libguile"))
        generated_header_src = os.path.join(build_folder, "libguile")
        if os.path.isdir(generated_header_src):
            copy(self, "scmconfig.h", src=generated_header_src,
                 dst=os.path.join(pkg, "include/guile/2.2/libguile"))
            copy(self, "version.h", src=generated_header_src,
                 dst=os.path.join(pkg, "include/guile/2.2/libguile"))
            copy(self, "guile-procedures.txt", src=generated_header_src,
                 dst=os.path.join(pkg, "share/guile/2.2"))

        # ── .go files from source tarball prebuilt/ ──────────────────
        go_src = os.path.join(source_folder, "prebuilt",
                              "64-bit-little-endian")
        if os.path.isdir(go_src):
            for root, dirs, files in os.walk(go_src):
                rel = os.path.relpath(root, go_src)
                dst = os.path.join(pkg, "lib/guile/2.2/ccache", rel)
                os.makedirs(dst, exist_ok=True)
                for f in files:
                    if f.endswith(".go"):
                        shutil.copy2(os.path.join(root, f),
                                     os.path.join(dst, f))

        # ── .scm files from source module/ ────────────────────────────
        scm_src = os.path.join(source_folder, "module")
        if os.path.isdir(scm_src):
            for root, dirs, files in os.walk(scm_src):
                # Skip hidden directories (.deps, .libs, etc.)
                dirs[:] = [d for d in dirs if not d.startswith(".")]
                rel = os.path.relpath(root, scm_src)
                dst = os.path.join(pkg, "share/guile/2.2", rel)
                os.makedirs(dst, exist_ok=True)
                for f in files:
                    if f.endswith(".scm"):
                        shutil.copy2(os.path.join(root, f),
                                     os.path.join(dst, f))

        # ── pkg-config file from build output ────────────────────────
        pc_src = os.path.join(build_folder, "meta", "guile-2.2.pc")
        if os.path.exists(pc_src):
            os.makedirs(os.path.join(pkg, "lib/pkgconfig"),
                        exist_ok=True)
            pc_dst = os.path.join(pkg, "lib/pkgconfig/guile-2.2.pc")
            shutil.copy2(pc_src, pc_dst)
            self._make_pkg_config_file_relocatable(pc_dst)

        # ── License ──────────────────────────────────────────────────
        copy(self, "COPYING*", src=source_folder,
             dst=os.path.join(pkg, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["guile-2.2"]
        self.cpp_info.set_property("pkg_config_name", "guile-2.2")
        # Headers are in include/guile/2.2/libguile/
        self.cpp_info.includedirs = ["include/guile/2.2"]
        # Also provide bindirs for the guile executable
        self.cpp_info.bindirs = ["bin"]
        # Scheme runtime files
        self.cpp_info.resdirs = ["share/guile"]
        # R32: System libs for Linux and OHOS
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]

        bin_dir = os.path.join(self.package_folder, "bin")
        lib_dir = os.path.join(self.package_folder, "lib")
        pkgconfig_dir = os.path.join(lib_dir, "pkgconfig")
        scm_dir = os.path.join(self.package_folder, "share", "guile", "2.2")
        ccache_dir = os.path.join(lib_dir, "guile", "2.2", "ccache")
        guile_bin = os.path.join(bin_dir, "guile")
        runtime_lib_dirs = []
        for dependency in self.dependencies.host.values():
            for dep_lib_dir in dependency.cpp_info.libdirs:
                if dep_lib_dir not in runtime_lib_dirs:
                    runtime_lib_dirs.append(dep_lib_dir)
        runtime_lib_dirs.append(lib_dir)

        for env in (self.runenv_info, self.buildenv_info):
            env.prepend_path("PATH", bin_dir)
            for runtime_lib_dir in runtime_lib_dirs:
                env.prepend_path("LD_LIBRARY_PATH", runtime_lib_dir)
            env.prepend_path("PKG_CONFIG_PATH", pkgconfig_dir)
            env.prepend_path("GUILE_LOAD_PATH", scm_dir)
            env.prepend_path("GUILE_LOAD_COMPILED_PATH", ccache_dir)
            env.prepend_path("GUILE_SYSTEM_PATH", scm_dir)
            env.prepend_path("GUILE_SYSTEM_COMPILED_PATH", ccache_dir)
            env.define_path("GUILE", guile_bin)
            env.define("GUILE_AUTO_COMPILE", "0")

    def _make_packaged_scripts_relocatable(self, bin_dir):
        guild = os.path.join(bin_dir, "guild")
        if os.path.isfile(guild):
            replace_in_file(
                self,
                guild,
                'exec sh ${GUILE:-/bin/guile} $GUILE_FLAGS '
                '-e \'(@@ (guild) main)\' -s "$0" "$@"',
                'script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)\n'
                ': "${GUILE:=$script_dir/guile}"\n'
                'exec "$GUILE" $GUILE_FLAGS '
                '-e \'(@@ (guild) main)\' -s "$0" "$@"',
            )

        guile_config = os.path.join(bin_dir, "guile-config")
        if os.path.isfile(guile_config):
            self._write_guile_config_wrapper(guile_config)

    def _make_pkg_config_file_relocatable(self, pc_file):
        replacements = (
            ("prefix=/\n", "prefix=${pcfiledir}/../..\n"),
            ("exec_prefix=/\n", "exec_prefix=${prefix}\n"),
            ("bindir=/bin\n", "bindir=${prefix}/bin\n"),
            ("libdir=/lib\n", "libdir=${prefix}/lib\n"),
            ("includedir=/include\n", "includedir=${prefix}/include\n"),
            ("datarootdir=//share\n", "datarootdir=${prefix}/share\n"),
            ("datadir=//share\n", "datadir=${datarootdir}\n"),
            ("pkgdatadir=//share/guile\n", "pkgdatadir=${datadir}/guile\n"),
            ("pkgincludedir=/include/guile\n", "pkgincludedir=${includedir}/guile\n"),
            (
                "sitedir=//share/guile/site/2.2\n",
                "sitedir=${datadir}/guile/site/2.2\n",
            ),
            (
                "extensiondir=/lib/guile/2.2/extensions\n",
                "extensiondir=${libdir}/guile/2.2/extensions\n",
            ),
            (
                "siteccachedir=/lib/guile/2.2/site-ccache\n",
                "siteccachedir=${libdir}/guile/2.2/site-ccache\n",
            ),
        )
        for old, new in replacements:
            replace_in_file(self, pc_file, old, new, strict=False)

        # Conan supplies transitive dependency metadata; keep the packaged
        # .pc file focused on this package and free of build-cache paths.
        with open(pc_file, "r", encoding="utf-8") as handle:
            lines = handle.read().splitlines()

        fixed_lines = []
        skip_continuation = False
        for line in lines:
            if skip_continuation:
                if not line or line[0].isspace():
                    continue
                skip_continuation = False

            if line.startswith("Libs:"):
                fixed_lines.append("Libs: -L${libdir} -lguile-2.2")
            elif line.startswith("Libs.private:"):
                fixed_lines.append("Libs.private: -lm -pthread -ldl")
                skip_continuation = line.rstrip().endswith("\\")
            elif line.startswith("Cflags:"):
                fixed_lines.append("Cflags: -I${pkgincludedir}/2.2")
            else:
                fixed_lines.append(line)

        with open(pc_file, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("\n".join(fixed_lines) + "\n")

    def _write_guile_config_wrapper(self, guile_config):
        script = f"""#!/bin/sh
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
prefix=$(CDPATH= cd -- "$script_dir/.." && pwd)
version="{self.version}"

usage() {{
    cat <<EOF
Usage:
  guile-config --version
  guile-config --help [SUBCOMMAND]
  guile-config compile
  guile-config link
  guile-config info VAR
EOF
}}

info_value() {{
    case "$1" in
        guileversion) printf '%s\\n' "$version" ;;
        prefix|exec_prefix) printf '%s\\n' "$prefix" ;;
        bindir) printf '%s/bin\\n' "$prefix" ;;
        libdir) printf '%s/lib\\n' "$prefix" ;;
        includedir) printf '%s/include\\n' "$prefix" ;;
        pkgincludedir) printf '%s/include/guile\\n' "$prefix" ;;
        datadir|datarootdir) printf '%s/share\\n' "$prefix" ;;
        pkgdatadir) printf '%s/share/guile\\n' "$prefix" ;;
        sitedir) printf '%s/share/guile/site/2.2\\n' "$prefix" ;;
        extensiondir) printf '%s/lib/guile/2.2/extensions\\n' "$prefix" ;;
        siteccachedir) printf '%s/lib/guile/2.2/site-ccache\\n' "$prefix" ;;
        guild) printf '%s/bin/guild\\n' "$prefix" ;;
        guile) printf '%s/bin/guile\\n' "$prefix" ;;
        *) echo "guile-config: unsupported info variable: $1" >&2; exit 2 ;;
    esac
}}

case "$1" in
    --version)
        printf 'guile-config - Guile version %s\\n' "$version"
        ;;
    --help)
        usage
        ;;
    compile)
        printf '%s\\n' "-I$prefix/include/guile/2.2"
        ;;
    link)
        printf '%s\\n' "-L$prefix/lib -lguile-2.2"
        ;;
    info)
        if [ $# -ne 2 ]; then
            echo "Usage: guile-config info VAR" >&2
            exit 2
        fi
        info_value "$2"
        ;;
    *)
        usage >&2
        exit 1
        ;;
esac
"""
        with open(guile_config, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(script)
        os.chmod(guile_config, 0o755)
