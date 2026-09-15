#!/usr/bin/env python3
"""Conan recipe for libopendbx 1.4.6 — OpenDBX C database abstraction library.

Upstream project "opendbx" builds libopendbx (C API), libopendbxplus (C++
wrapper) and the sqlite3 backend plugin from one autotools tree. This recipe
builds the full tree with the sqlite3 backend, runs the upstream regression
suite (odbxtest + odbxplustest) against ref/sqlite3.ref, and packages the
C library plus the sqlite3 backend plugin.
"""
import glob as _glob
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibopendbxConan(ConanFile):
    name = "libopendbx"
    version = "1.4.6"
    description = "OpenDBX: lightweight but extensible database access library (C API)"
    license = "LGPL-2.0-or-later"
    homepage = "https://linuxnetworks.de/doc/index.php/OpenDBX"
    url = ""
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    exports_sources = "patches/*"

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("libopendbx supports Linux/OHOS only")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def requirements(self):
        self.requires("sqlite3/3.49.1")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)
        # In-source build: the bundled 2002-era autotools Makefiles use
        # relative include paths (-I../../lib) that break under VPATH.
        self.folders.source = "."
        self.folders.build = "."

    def source(self):
        # Primary source first; on failure fall back to the byte-identical
        # mirror (same SHA-256, verified). Patches are applied exactly once
        # after any successful fetch path (mirror fallback must not skip it).
        sources = dict(self.conan_data["sources"])
        mirror_urls = sources.pop("mirror_urls", [])
        mirror_sha256 = sources.pop("mirror_sha256", None)
        fetched = False
        try:
            get(self, **sources, strip_root=True)
            fetched = True
        except Exception as error:
            if not mirror_urls or not mirror_sha256:
                raise
            self.output.warning(f"Primary source failed ({error}); trying verified mirrors")
            for mirror_url in mirror_urls:
                try:
                    get(self, url=mirror_url, sha256=mirror_sha256, strip_root=True)
                    fetched = True
                    break
                except Exception as mirror_error:
                    self.output.warning(f"Mirror source failed ({mirror_error}): {mirror_url}")
            if not fetched:
                raise
        apply_conandata_patches(self)
        # OHOS sandbox: autoconf's config.status creates its ./confXXXXXX
        # temp dir with umask 077 (0700); the sandboxed subprocess then
        # cannot read subs1.awk -> "Permission denied" -> "could not setup
        # config files machinery". Patch the configure script (config.status
        # is generated from it) to keep the temp dir accessible
        # (remind/06.02.08 precedent, proven green on this CI).
        configure = os.path.join(self.source_folder, "configure")
        if os.path.isfile(configure):
            replace_in_file(self, configure, "umask 077 && mktemp", "umask 002 && mktemp")
            replace_in_file(self, configure, "umask 077 && mkdir", "umask 002 && mkdir")
        # Upstream links the regression binaries with -static; on OHOS/bionic
        # a fully static binary cannot dlopen the sqlite3 backend plugin
        # (odbxtest exits with ODBX_ERR_NOTEXIST). Drop -static so the tests
        # link dynamically and can load the .so backend (build() regression).
        makefile_am = os.path.join(self.source_folder, "test", "Makefile.am")
        if os.path.isfile(makefile_am):
            replace_in_file(self, makefile_am, "odbxtest_LDFLAGS = -static", "odbxtest_LDFLAGS =")
            replace_in_file(self, makefile_am, "odbxplustest_LDFLAGS = -static", "odbxplustest_LDFLAGS =")

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--with-backends=sqlite3",
            "--disable-utils",
            # rpl_malloc: cross-compiling AC_FUNC_MALLOC cannot run its
            # malloc(0) probe, defaults to no -> config.h #defines
            # malloc rpl_malloc, breaking libc++ headers and std::realloc.
            # Pin the cache vars to yes (gnu-chess/speech-dispatcher
            # precedent; malloc(0) non-null holds on bionic/musl).
            "ac_cv_func_malloc_0_nonnull=yes",
            "ac_cv_func_realloc_0_nonnull=yes",
        ])
        if str(self.settings.os) == "OHOS":
            tc.configure_args.extend([
                "--build=aarch64-unknown-linux-gnu",
                # NB: the vendor slot must be non-empty. Autoconf splits
                # CPU-VENDOR-OS, so `aarch64-linux-ohos` yields host_os=ohos
                # and libtool's `case $host_os in linux*)` misses it ->
                # dynamic_linker=no -> static-only build (no .so backend
                # plugin). `aarch64-unknown-linux-ohos` yields host_os=
                # linux-ohos which matches the Linux-ELF branch and enables
                # shared libraries.
                "--host=aarch64-unknown-linux-ohos",
            ])
        # Inject the sqlite3 dependency into the autotools build: configure
        # checks for sqlite3.h and the sqlite3 backend links libsqlite3.
        # AutotoolsToolchain does not aggregate dependency cpp_info, so add
        # the include/lib paths explicitly (absolute, see gdal precedent).
        dep = self.dependencies["sqlite3"]
        inc = os.path.join(dep.package_folder, dep.cpp_info.includedirs[0])
        lib = os.path.join(dep.package_folder, dep.cpp_info.libdirs[0])
        tc.extra_cflags.append(f"-I{inc}")
        tc.extra_cxxflags.append(f"-I{inc}")
        # OHOS clang defaults to C++17; upstream api header uses pre-C++17
        # dynamic exception specs (throw(std::exception)) which are errors
        # in C++17. Downgrade the diagnostic so the old code compiles
        # (freeimage/aiksaurus precedent; no source changes needed).
        tc.extra_cxxflags.append("-Wno-dynamic-exception-spec")
        tc.extra_ldflags.append(f"-L{lib}")
        # OHOS: libtool's C++ shared-library probe (and the final .so links)
        # need to resolve libc++ from the SDK llvm/lib — it is only on
        # LD_LIBRARY_PATH (runtime), not in the linker search path, so the
        # probe fails and libtool decides "no shared libraries" (static-only
        # .a). Add -L so shared libs (libopendbx.so / backend plugin /
        # libopendbxplus.so) are actually built (utf8proc precedent).
        if str(self.settings.os) == "OHOS":
            sdk_llvm_libs = sorted(
                _glob.glob("/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib")
            )
            if sdk_llvm_libs:
                tc.extra_ldflags.append(f"-L{sdk_llvm_libs[-1]}")
            else:
                self.output.warning("OHOS SDK llvm/lib not found; shared libs may not build")
        tc.generate()

    def build(self):
        # Patches are applied in source() after the fetch (see mirror fallback).
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        self._run_upstream_regression()

    def _run_upstream_regression(self):
        """Run the upstream regression binaries (odbxtest + odbxplustest)
        against the sqlite3 backend and require output identical to
        test/ref/sqlite3.ref (the upstream's own verification method)."""
        # Binaries and the backend plugin land in the BUILD folder
        # (in-source copy); the reference output lives in the source tree.
        root = self.build_folder
        backend = os.path.join(root, "backends", "sqlite3", ".libs", "libsqlite3backend.so")
        testdir = os.path.join(root, "regression-run")
        os.makedirs(testdir, exist_ok=True)
        ref = os.path.join(self.source_folder, "test", "ref", "sqlite3.ref")
        with open(ref, "r", encoding="utf-8", errors="replace") as f:
            want = [line.rstrip() for line in f.read().splitlines()]
        for app in ("odbxtest", "odbxplustest"):
            app_path = os.path.join(root, "test", app)
            out = os.path.join(testdir, app + ".out")
            err = os.path.join(testdir, app + ".err")
            # ConanFile.run(): failure raises by default; no `check` kwarg.
            try:
                self.run(
                    f"'{app_path}' -b '{backend}' -h . -d odbx.sq3 > '{out}' 2> '{err}'",
                    cwd=testdir,
                )
            except ConanException:
                detail = ""
                if os.path.isfile(err):
                    with open(err, "r", encoding="utf-8", errors="replace") as f:
                        detail = f.read().strip()
                raise ConanException(
                    f"upstream regression {app} failed; stderr:\n{detail or '(empty)'}"
                )
            with open(out, "r", encoding="utf-8", errors="replace") as f:
                got = [line.rstrip() for line in f.read().splitlines()]
            if got != want:
                raise ConanException(
                    f"upstream regression {app}: output differs from test/ref/sqlite3.ref "
                    f"({len(got)} vs {len(want)} lines); see {err}"
                )
            self.output.info(f"upstream regression {app}: PASS (output matches ref/sqlite3.ref)")

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # Keep only the C-library artifacts: libopendbx, the sqlite3 backend
        # plugin, the C headers (odbx.h, opendbx/api.h) and opendbx.pc. The
        # C++ wrapper library and header belong to the libopendbxplus package.
        lib_dir = os.path.join(self.package_folder, "lib")
        for name in list(os.listdir(lib_dir)):
            if name.startswith("libopendbxplus"):
                _remove_tree(os.path.join(lib_dir, name))
        # Libtool .la wrappers are not needed at runtime.
        for _la in _glob.glob(os.path.join(lib_dir, "**", "*.la"), recursive=True):
            os.remove(_la)
        # opendbxplus.pc and the C++ header belong to the libopendbxplus package.
        pc = os.path.join(lib_dir, "pkgconfig", "opendbxplus.pc")
        if os.path.exists(pc):
            os.remove(pc)
        cpp_header = os.path.join(self.package_folder, "include", "opendbx", "api")
        if os.path.exists(cpp_header):
            os.remove(cpp_header)

    def package_info(self):
        self.cpp_info.libs = ["opendbx"]
        self.cpp_info.includedirs = ["include"]
        # The sqlite3 backend plugin is installed at lib/opendbx/; consumers
        # load it at runtime by path (OpenDBX supports backend paths directly).
        self.cpp_info.libdirs = ["lib", "lib/opendbx"]


def _remove_tree(path):
    if os.path.isdir(path):
        import shutil as _shutil
        _shutil.rmtree(path)
    else:
        os.remove(path)
