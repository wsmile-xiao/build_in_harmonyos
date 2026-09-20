#!/usr/bin/env python3
"""Conan recipe for libfvde 20240502 — Autotools (configure + make).

libfvde is a C library to access FileVault Drive Encryption (FVDE) encrypted
volumes, shipped with the fvdeinfo/fvdemount command line tools.  It belongs to
the libyal family, so the HarmonyOS/OHOS handling mirrors the merged siblings
(libbde/20240502 — same release wave — and libfsntfs/20251028):

* E007: the release tarball ships pre-generated Autotools files
  (``configure``/``aclocal.m4``/``Makefile.in``) whose ``config.guess`` does not
  know HarmonyOS.  Explicit GNU build/host triplets are passed instead of
  re-running ``autoreconf`` (the device has automake through harmonybrew, the CI
  worker does not — see SKILL.md §"设备 PATH 含 ~/.harmonybrew/bin").
* E011: HMDFS ignores chmod and autoconf creates its ``confXXXXXX`` scratch
  directory with ``umask 077``; the build runs with ``umask 022`` and the
  shipped ``configure`` script is patched in place.
* E087/E330: the upstream test drivers are shell scripts (HMDFS refuses direct
  exec of scripts, so they are started through the interpreter) and libtool
  test targets are wrapper scripts whose real ELF lives in ``.libs``.
* Stale shipped ``common/config.h``: the tarball contains a ``config.h``
  generated on the maintainer machine *with* OpenSSL (``HAVE_LIBCRYPTO`` /
  ``HAVE_OPENSSL_EVP_H`` defined).  ``common/common.h`` does
  ``#include "config.h"`` (quoted), which resolves to the source-tree copy
  first, so the recipe configures with ``--with-openssl=no`` and builds
  in-source: the fresh configure output overwrites the stale header and
  libhmac/libcaes fall back to their bundled self-contained implementations
  (identical choice and evidence as libbde/20240502).

Upstream tests (``tests/Makefile.am`` @ 20240502): 27 ``check_PROGRAMS``
(``fvde_test_*`` C programs) plus 3 automake ``TESTS`` shell drivers
(``test_library.sh``, ``test_tools.sh``, ``test_fvdeinfo.sh``).  ``make check``
runs inside ``build()``; ``test_fvdeinfo.sh`` ends in SKIP (exit 77) by upstream
design because the release tarball ships no ``tests/input`` fixtures.
Python binding tests are switched off with ``--disable-python`` so
``TESTS_PYFVDE`` is not registered.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibfvdeConan(ConanFile):
    name = "libfvde"
    version = "20240502"
    description = (
        "Library to access the FileVault Drive Encryption (FVDE) format"
    )
    license = "LGPL-3.0-or-later"
    homepage = "https://github.com/libyal/libfvde"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    # Bundled (vendored) libyal components that ship inside the release tarball.
    # They are *not* separate Conan requirements: the tarball is a
    # self-contained release archive, so no synclibs.sh / unregistered
    # dependency may be pulled into this PR (one library per branch).
    _LOCAL_LIBS = (
        "libbfio",
        "libcaes",
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
        "libfguid",
        "libfplist",
        "libfvalue",
        "libhmac",
        "libuna",
    )

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
                "libfvde adaptation currently supports Linux and OHOS"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        toolchain = AutotoolsToolchain(self)
        toolchain.configure_args.extend(
            [
                "--disable-python",
                "--with-libfuse=no",
                "--enable-static-executables=no",
                # Keep the bundled self-contained libhmac/libcaes implementations:
                # the release tarball ships a stale common/config.h generated
                # with OpenSSL on the maintainer machine, and a link against a
                # host libcrypto is neither required nor desirable here.
                "--with-openssl=no",
            ]
        )
        if self.options.shared:
            toolchain.configure_args.append("--enable-shared")
            toolchain.configure_args.append("--disable-static")
        else:
            toolchain.configure_args.append("--disable-shared")
            toolchain.configure_args.append("--enable-static")
        if str(self.settings.os) == "OHOS":
            # The bundled config.guess/config.sub predate HarmonyOS; pin the
            # triplets instead of patching (regenerating) the Autotools files.
            toolchain.configure_args.extend(
                [
                    "--build=aarch64-unknown-linux-gnu",
                    "--host=aarch64-unknown-linux-gnu",
                ]
            )
        toolchain.generate()

    def _patch_ohos_test_runner(self):
        """Resolve libtool wrapper scripts to their real ELF in ``.libs``.

        On OHOS the HMDFS test tree keeps the libtool wrapper as the test
        target; ``test_runner.sh`` then cannot execute it.  Both dispatch
        branches (the readlink_f one and the default one) are redirected to
        ``<dir>/.libs/<name>``.  The replacement count is asserted so a future
        upstream layout change fails loudly instead of silently dropping the
        workaround.
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
                "unexpected libfvde test_runner.sh layout; "
                "cannot apply OHOS libtool executable workaround"
            )
        test_runner = test_runner.replace(needle, replacement, 2)

        default_runner = "\telse\n\t\tif ! test -x \"${TEST_EXECUTABLE}\";"
        default_runner_replacement = (
            "\telse\n"
            "\t\tTEST_EXECUTABLE=$( find_binary_executable "
            "\"${TEST_EXECUTABLE}\" );\n"
            "\t\tif ! test -x \"${TEST_EXECUTABLE}\";"
        )
        if test_runner.count(default_runner) != 2:
            raise ConanInvalidConfiguration(
                "unexpected libfvde test_runner.sh execution layout; "
                "cannot apply OHOS test dispatch workaround"
            )
        test_runner = test_runner.replace(
            default_runner, default_runner_replacement, 2
        )

        with open(test_runner_path, "w", encoding="utf-8") as test_runner_file:
            test_runner_file.write(test_runner)

    def _check_self_contained_source(self):
        missing_dirs = [
            name for name in self._LOCAL_LIBS
            if not os.path.isdir(os.path.join(self.source_folder, name))
        ]
        generated_files = (
            "configure",
            "aclocal.m4",
            "config.guess",
            "config.sub",
            "Makefile.in",
        )
        missing_files = [
            name for name in generated_files
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
                "libfvde/20240502 source is not self-contained: "
                + "; ".join(details)
                + ". Do not run synclibs.sh here: adapt missing libyal "
                "dependencies in separate library worktrees first."
            )

    def build(self):
        apply_conandata_patches(self)
        self._check_self_contained_source()

        autotools = Autotools(self)
        old_umask = os.umask(0o022)
        old_ld_library_path = os.environ.get("LD_LIBRARY_PATH")
        try:
            config_shell = (
                os.environ.get("CONFIG_SHELL")
                or shutil.which("bash")
                or shutil.which("sh")
                or "/bin/sh"
            )
            if str(self.settings.os) == "OHOS":
                # HMDFS rejects the 0700 scratch directory of Autoconf and
                # blocks direct script execution: patch the shipped script and
                # drive it through the interpreter explicitly.
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
            self.run("make -j1", cwd=self.source_folder)
            if str(self.settings.os) == "OHOS":
                self._patch_ohos_test_runner()
                library_path = os.path.join(
                    self.source_folder, "libfvde", ".libs"
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
            else:
                self.run("make -j1 check", cwd=self.source_folder)
        finally:
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
        for license_file in ("COPYING", "COPYING.LESSER"):
            license_path = os.path.join(self.source_folder, license_file)
            if os.path.isfile(license_path):
                copy(
                    self,
                    license_file,
                    src=self.source_folder,
                    dst=os.path.join(self.package_folder, "licenses"),
                )

    def package_info(self):
        self.cpp_info.libs = ["fvde"]
        self.cpp_info.set_property("cmake_file_name", "libfvde")
        self.cpp_info.set_property("cmake_target_name", "libfvde::libfvde")
        self.cpp_info.set_property("pkg_config_name", "libfvde")
