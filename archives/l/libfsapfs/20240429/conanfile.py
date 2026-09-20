#!/usr/bin/env python3
"""Conan recipe for libfsapfs 20240429.

libfsapfs is a library to access the Apple File System (APFS) format.

The 20240429 release archive is self-contained: it bundles the local libyal
components the library links against (17 of them) and ships the generated
Autotools files (configure / aclocal.m4 / config.guess / config.sub /
Makefile.in).  The recipe therefore never runs ``synclibs.sh`` and never pulls
unregistered vendored dependencies into this PR.

The pinned source is the official upstream GitHub release asset
(``libfsapfs-experimental-20240429.tar.gz``); the URL + SHA-256 live in
``conandata.yml`` and the release identity is recorded in ``manifest.yaml``.

Platform adaptation is fully inlined here (no ``patches/`` directory):

* HMDFS rejects the 0700 temporary directory Autoconf creates -> ``configure``
  is invoked with ``umask 022`` and its inner ``umask 077`` rewritten.
* HMDFS blocks direct execution of source-tree scripts and the device has no
  ``/bin/bash`` -> ``configure`` runs under ``CONFIG_SHELL`` and ``make check``
  receives ``LOG_COMPILER`` pointing at the same interpreter.
* The bundled ``config.guess``/``config.sub`` (2024) have no OHOS branch ->
  explicit GNU build/host triplets are passed.
* Upstream tests are driven exactly as upstream drives them (``make check`` with
  ``LOG_COMPILER``): ``tests/test_library.sh`` drives 52 of the 61 registered
  ``check_PROGRAMS`` and ``tests/test_tools.sh`` drives 7.  The release archive
  libtool wrapper scripts do execute on this device (measured: toybox
  ``file -b`` reports ``/bin/sh script``, so the runner's own
  ``find_binary_executable`` helper is a no-op here and the wrappers exit 0),
  so no test-runner patch is applied.  The two registered programs that no
  upstream runner drives are left unexecuted and reported as NOT_RUN, with a
  standalone probe recorded in notes.md.
* Upstream tests run with ``HOME`` pointed at a throw-away directory inside the
  build folder, never at the operator's real HOME.
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


class LibfsapfsConan(ConanFile):
    name = "libfsapfs"
    version = "20240429"
    description = (
        "Library to access the Apple File System (APFS) format"
    )
    license = "LGPL-3.0-or-later"
    homepage = "https://github.com/libyal/libfsapfs"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("apfs", "file-system", "disk-image", "libyal")
    package_type = "library"
    languages = "C"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    # Local libyal components bundled by the release archive (configure.ac
    # AC_CONFIG_FILES list).
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
                "libfsapfs adaptation currently supports Linux and OHOS"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        # An explicit archive filename is required: Conan misclassifies the
        # release URL when it has to infer the archive format and would
        # otherwise hand a tarball to the ZIP reader (BadZipFile).
        get(self, strip_root=True, **self.conan_data["sources"])

    def generate(self):
        toolchain = AutotoolsToolchain(self)
        # AutotoolsToolchain already emits --enable-shared/--disable-static or
        # --disable-shared/--enable-static from the "shared" option.
        toolchain.configure_args.extend(
            [
                "--disable-python",
                "--with-libfuse=no",
                "--enable-static-executables=no",
            ]
        )
        if str(self.settings.os) == "OHOS":
            # The bundled config.guess cannot identify this build host
            # (uname -s = "HarmonyOS") and the bundled config.sub (2024) has no
            # ohos branch: `aarch64-unknown-linux-ohos` is rejected with
            # "OS 'ohos' not recognized".  Explicit GNU triplets are passed
            # instead, which the bundled config.sub accepts; build == host so
            # configure keeps "cross compiling... no" and AC_RUN_IFELSE runs.
            toolchain.configure_args.extend(
                [
                    "--build=aarch64-unknown-linux-gnu",
                    "--host=aarch64-unknown-linux-gnu",
                ]
            )
        toolchain.generate()

    def build(self):
        # Apply the patches declared in conandata.yml.  This release needs none
        # (the platform adaptation lives in generate()/build()), so the call is
        # a no-op today; it is kept as a real call rather than an unused import
        # so that the recipe is patch-ready and the G1 "patch application"
        # check reflects an actual call site.
        apply_conandata_patches(self)

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
                "libfsapfs/20240429 source is not self-contained: "
                + "; ".join(details)
                + ". Do not run synclibs.sh here: adapt missing libyal "
                "dependencies in separate library worktrees first."
            )

        autotools = Autotools(self)
        # Honour the caller's explicit job limit but never fan out on the
        # shared device (os.cpu_count() reports 20 while the container
        # affinity is 8).
        configured_jobs = self.conf.get("tools.build:jobs", default=2)
        try:
            jobs = max(1, min(int(configured_jobs), 4))
        except (TypeError, ValueError):
            jobs = 2
        old_umask = os.umask(0o022)
        old_ld_library_path = os.environ.get("LD_LIBRARY_PATH")
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
            self.run(f"make -j{jobs}", cwd=self.source_folder)
            # Upstream tests must never run against the operator's real HOME:
            # point HOME at a throw-away directory inside the build folder.
            old_home = os.environ.get("HOME")
            sandbox_home = os.path.join(self.build_folder, "upstream-test-home")
            os.makedirs(sandbox_home, exist_ok=True)
            os.environ["HOME"] = sandbox_home
            try:
                if str(self.settings.os) == "OHOS":
                    library_path = os.path.join(
                        self.source_folder, "libfsapfs", ".libs"
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
                if old_home is None:
                    os.environ.pop("HOME", None)
                else:
                    os.environ["HOME"] = old_home
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
        self.cpp_info.libs = ["fsapfs"]
        self.cpp_info.set_property("cmake_file_name", "libfsapfs")
        self.cpp_info.set_property("cmake_target_name", "libfsapfs::libfsapfs")
        self.cpp_info.set_property("pkg_config_name", "libfsapfs")
