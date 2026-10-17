#!/usr/bin/env python3
"""Conan recipe for libfshfs 20260130.

libfshfs is a library to access the Apple HFS and HFS+ file system formats.

The 20260130 release archive is self-contained: it bundles the local libyal
components the library links against and ships the generated Autotools files
(configure / aclocal.m4 / config.guess / config.sub / Makefile.in).  The
recipe therefore never runs ``synclibs.sh`` and never pulls unregistered
vendored dependencies into this PR.

The upstream GitHub release asset for this version is no longer published
(the repository only offers 20260802 / 20260826 today), so the pinned source is
the Debian orig tarball mirror of the same upstream deployment; the release
identity was verified byte-for-byte against upstream commit
dd100d2ae96b12fe07d7082e94c5ed29319d280e (2026-01-30, the commit whose
``configure.ac`` reports ``AC_INIT([libfshfs], [20260130])``).  The source URL
and SHA-256 live in ``conandata.yml``; tag/commit provenance is recorded in
``manifest.yaml``.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibfshfsConan(ConanFile):
    name = "libfshfs"
    version = "20260130"
    description = (
        "Library to access the Apple HFS and HFS+ file system formats"
    )
    license = "LGPL-3.0-or-later"
    homepage = "https://github.com/libyal/libfshfs"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("hfs", "hfs-plus", "file-system", "libyal", "forensics")
    package_type = "library"
    languages = "C"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    # Local libyal components bundled by the release archive (configure.ac).
    _LOCAL_LIBS = (
        "libbfio",
        "libcdata",
        "libcerror",
        "libcfile",
        "libclocale",
        "libcnotify",
        "libcpath",
        "libcsplit",
        "libcthreads",
        "libfcache",
        "libfdata",
        "libfdatetime",
        "libfguid",
        "libfmos",
        "libhmac",
        "libuna",
    )
    # Generated Autotools files that only the release archive ships.
    _GENERATED_FILES = (
        "configure",
        "aclocal.m4",
        "config.guess",
        "config.sub",
        "Makefile.in",
    )
    # Tests registered in tests/Makefile.am check_PROGRAMS that upstream's
    # tests/test_tools.sh does not dispatch at this release (both runner lists
    # are empty strings there).  They are still built by ``make check``.
    _TOOLS_TEST_PROGRAMS = (
        "info_handle",
        "mount_path_string",
        "output",
        "signal",
    )
    # Device is shared: os.cpu_count() reports 20 while the container affinity
    # is 8, so every build step pins its own parallelism explicitly.
    _MAKE_JOBS = "2"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        os_name = str(self.settings.os)
        if os_name not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libfshfs adaptation currently supports Linux and OHOS"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        # An explicit archive filename is required: Conan misclassifies the
        # Debian URL when it has to infer the archive format and would
        # otherwise hand a tarball to the ZIP reader (BadZipFile).
        get(
            self,
            filename="libfshfs_20260130.orig.tar.gz",
            strip_root=True,
            **self.conan_data["sources"],
        )

    def generate(self):
        toolchain = AutotoolsToolchain(self)
        # AutotoolsToolchain already emits --enable-shared/--disable-static or
        # --disable-shared/--enable-static from the "shared" option.
        toolchain.configure_args.extend(
            [
                # pyfshfs (the optional Python binding) is out of scope and
                # would need python-config for the OHOS target.
                "--disable-python",
                # fshfsmount is the only libfuse consumer; the OHOS image has
                # no fuse development files.
                "--with-libfuse=no",
                "--enable-static-executables=no",
            ]
        )
        if str(self.settings.os) == "OHOS":
            # The bundled config.guess (2024-07-27) cannot identify this build
            # host (uname -s = "HarmonyOS"); the triplets are passed explicitly
            # and the bundled config.sub accepts aarch64-unknown-linux-ohos.
            toolchain.configure_args.extend(
                [
                    "--build=aarch64-unknown-linux-ohos",
                    "--host=aarch64-unknown-linux-ohos",
                ]
            )
        toolchain.generate()

    def _patch_ohos_test_runner(self):
        """Resolve libtool wrapper scripts to their .libs ELF binaries.

        HMDFS refuses to execute shell scripts from the source tree, and the
        upstream tests/test_runner.sh runs the check_PROGRAMS libtool wrapper
        scripts directly.  The two insertions below reuse the upstream
        ``find_binary_executable`` helper (which already knows the
        ``<dir>/.libs/<name>`` layout) for the plain (non valgrind/gdb/asan)
        execution paths; no test semantics are changed.
        """
        test_runner_path = os.path.join(
            self.source_folder, "tests", "test_runner.sh"
        )
        with open(test_runner_path, encoding="utf-8") as test_runner_file:
            test_runner = test_runner_file.read()

        needle = "TEST_EXECUTABLE=$( readlink_f \"${TEST_EXECUTABLE}\" );"
        replacement = (
            needle
            + "\n\n"
            + "\tlocal TEST_EXECUTABLE_BASENAME=`basename "
            + "${TEST_EXECUTABLE}`;"
            + "\n"
            + "\tlocal TEST_EXECUTABLE_DIRNAME=`dirname "
            + "${TEST_EXECUTABLE}`;"
            + "\n"
            + "\tlocal LIBTOOL_EXECUTABLE=\"${TEST_EXECUTABLE_DIRNAME}/.libs/"
            + "${TEST_EXECUTABLE_BASENAME}\";"
            + "\n"
            + "\tif test -x \"${LIBTOOL_EXECUTABLE}\";"
            + "\n"
            + "\tthen"
            + "\n"
            + "\t\tTEST_EXECUTABLE=\"${LIBTOOL_EXECUTABLE}\";"
            + "\n"
            + "\tfi;"
        )
        if test_runner.count(needle) != 2:
            raise ConanInvalidConfiguration(
                "unexpected libfshfs test_runner.sh layout; "
                "cannot apply OHOS libtool executable workaround"
            )
        test_runner = test_runner.replace(needle, replacement, 2)

        default_runner = (
            "\telse\n"
            "\t\tif ! test -x \"${TEST_EXECUTABLE}\";"
        )
        default_runner_replacement = (
            "\telse\n"
            "\t\tTEST_EXECUTABLE=$( find_binary_executable "
            "\"${TEST_EXECUTABLE}\" );\n"
            "\t\tif ! test -x \"${TEST_EXECUTABLE}\";"
        )
        if test_runner.count(default_runner) != 2:
            raise ConanInvalidConfiguration(
                "unexpected libfshfs test_runner.sh execution layout; "
                "cannot apply OHOS test dispatch workaround"
            )
        test_runner = test_runner.replace(
            default_runner, default_runner_replacement, 2
        )

        with open(test_runner_path, "w", encoding="utf-8") as test_runner_file:
            test_runner_file.write(test_runner)

    def _upstream_tools_runner_is_empty(self):
        test_tools_path = os.path.join(
            self.source_folder, "tests", "test_tools.sh"
        )
        with open(test_tools_path, encoding="utf-8") as test_tools_file:
            test_tools = test_tools_file.read()
        return (
            'TOOLS_TESTS="";' in test_tools
            and 'TOOLS_TESTS_WITH_INPUT="";' in test_tools
        )

    def _run_registered_tools_tests(self, config_shell):
        """Run the four registered tools programs through upstream's harness.

        The 20260130 release leaves ``TOOLS_TESTS`` and
        ``TOOLS_TESTS_WITH_INPUT`` empty in tests/test_tools.sh, so
        ``make check`` builds the four ``fshfs_test_tools_*`` programs
        (tests/Makefile.am check_PROGRAMS) without ever dispatching them.
        They are executed here with the same upstream
        ``run_test_with_arguments`` helper that tests/test_library.sh uses, so
        the registered program count is fully covered; the dispatch is skipped
        automatically if a future release fills the upstream lists.
        """
        if not self._upstream_tools_runner_is_empty():
            self.output.info(
                "upstream tests/test_tools.sh dispatches its tools programs; "
                "no extra dispatch needed"
            )
            return

        dispatch_script = os.path.join(
            self.build_folder, "ohos_registered_tools_tests.sh"
        )
        programs = " ".join(self._TOOLS_TEST_PROGRAMS)
        with open(dispatch_script, "w", encoding="utf-8") as script_file:
            script_file.write(
                "#!/bin/sh\n"
                # No `set -u`: upstream tests/test_runner.sh reads several
                # optional variables (CHECK_WITH_ASAN, CHECK_WITH_GDB, ...)
                # without defaulting them.
                'cd "$1" || exit 1\n'
                ". ./test_runner.sh\n"
                "rc=0\n"
                "for name in " + programs + "; do\n"
                '\trun_test_with_arguments "Testing: tools_${name}" '
                '"./fshfs_test_tools_${name}" || rc=1\n'
                "done\n"
                "exit $rc\n"
            )
        self.output.info(
            "upstream tests/test_tools.sh leaves both runner lists empty; "
            "dispatching registered tools programs: " + programs
        )
        self.run(
            f'"{config_shell}" "{dispatch_script}" '
            f'"{os.path.join(self.source_folder, "tests")}"'
        )

    def build(self):
        # Release-archive closure check: refuse to build a partial source tree
        # (e.g. a git checkout) instead of silently bootstrapping it.
        missing_dirs = [
            name for name in self._LOCAL_LIBS
            if not os.path.isdir(os.path.join(self.source_folder, name))
        ]
        missing_files = [
            name for name in self._GENERATED_FILES
            if not os.path.isfile(os.path.join(self.source_folder, name))
        ]
        if missing_dirs or missing_files:
            details = []
            if missing_dirs:
                details.append(
                    "bundled libyal directories: " + ", ".join(missing_dirs)
                )
            if missing_files:
                details.append(
                    "generated Autotools files: " + ", ".join(missing_files)
                )
            raise ConanInvalidConfiguration(
                "libfshfs/20260130 source is not self-contained: "
                + "; ".join(details)
                + ". Do not run synclibs.sh here: adapt missing libyal "
                "dependencies in separate library worktrees first."
            )

        autotools = Autotools(self)
        old_umask = os.umask(0o022)
        old_ld_library_path = os.environ.get("LD_LIBRARY_PATH")
        old_home = os.environ.get("HOME")
        try:
            config_shell = os.environ.get(
                "CONFIG_SHELL", "/data/service/hnp/bin/bash"
            )
            if str(self.settings.os) == "OHOS":
                # HMDFS rejects the 0700 temporary directory created by
                # Autoconf, and the device also blocks direct script exec.
                configure_path = os.path.join(self.source_folder, "configure")
                with open(configure_path, encoding="utf-8") as configure_file:
                    configure_text = configure_file.read()
                if "umask 077" in configure_text:
                    with open(
                        configure_path, "w", encoding="utf-8"
                    ) as configure_file:
                        configure_file.write(
                            configure_text.replace("umask 077", "umask 022")
                        )
                os.chmod(configure_path, 0o755)
                self.run(
                    f'"{config_shell}" "{configure_path}" '
                    f"{autotools._configure_args}",
                    cwd=self.source_folder,
                )
            else:
                autotools.configure()
            self.run(f"make -j{self._MAKE_JOBS}", cwd=self.source_folder)
            # Upstream tests must never run against the operator's real HOME:
            # point HOME at a throw-away directory inside the build folder.
            sandbox_home = os.path.join(self.build_folder, "upstream-test-home")
            os.makedirs(sandbox_home, exist_ok=True)
            os.environ["HOME"] = sandbox_home
            if str(self.settings.os) == "OHOS":
                self._patch_ohos_test_runner()
                library_path = os.path.join(
                    self.source_folder, "libfshfs", ".libs"
                )
                if old_ld_library_path:
                    os.environ["LD_LIBRARY_PATH"] = (
                        library_path + os.pathsep + old_ld_library_path
                    )
                else:
                    os.environ["LD_LIBRARY_PATH"] = library_path
                self.run(
                    f'make -j1 check LOG_COMPILER="{config_shell}"',
                    cwd=self.source_folder,
                )
                self._run_registered_tools_tests(config_shell)
            else:
                self.run("make -j1 check", cwd=self.source_folder)
        finally:
            if old_home is None:
                os.environ.pop("HOME", None)
            else:
                os.environ["HOME"] = old_home
            if old_ld_library_path is None:
                os.environ.pop("LD_LIBRARY_PATH", None)
            else:
                os.environ["LD_LIBRARY_PATH"] = old_ld_library_path
            os.umask(old_umask)

    def package(self):
        self.run(
            f'make install DESTDIR="{self.package_folder}"',
            cwd=self.source_folder,
        )
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        copy(
            self,
            "COPYING.LESSER",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["fshfs"]
        # HFS+ decmpfs (deflate) support is auto-detected by the release
        # configure.ac: the OHOS SDK sysroot ships libz.so and the OHOS rootfs
        # resolves it at runtime, so the built shared library carries
        # DT_NEEDED libz.so.  Declaring it as a system library keeps static
        # consumers linkable as well.
        self.cpp_info.system_libs = ["z"]
        self.cpp_info.set_property("cmake_file_name", "libfshfs")
        self.cpp_info.set_property("cmake_target_name", "libfshfs::libfshfs")
        self.cpp_info.set_property("pkg_config_name", "libfshfs")
