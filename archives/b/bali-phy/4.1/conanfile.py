#!/usr/bin/env python3
"""Conan recipe - bali-phy 4.1 (Meson application, the \x27bali-phy\x27 executable + tools).

HarmonyOS PC adaptation notes
------------------------------
* build system : Meson (>=1.1, C++20). Dependencies: Boost
  (program_options/random/system/chrono + header-only JSON), Eigen3, fmt
  (shared on ohpcd), cereal (header-only). range-v3 is NOT required: the
  upstream meson.build falls back to its internal vendored copy when the
  system header is not found (this recipe does not add it to the include
  path, so the upstream internal copy is used, matching upstream default).
* Boost header gap : no ohpcd boost package exports Boost::json (the
  boost/json headers are not installed by any curated boost recipe) and
  bali-phy hard-requires <boost/json.hpp> as well as <boost/convert.hpp>,
  <boost/rational.hpp> and <boost/compute/detail/sha1.hpp> (boost/uuid is
  a transitive dependency of convert/compute). This recipe therefore
  vendors the missing header-only implementations - Boost.JSON plus
  boost/uuid, boost/convert, boost/rational and boost/compute - in
  patches/boost-extra (boost 1.91, BSL-1.0, 183 headers, all verbatim
  upstream, no OHOS/musl edits) and compiles the official header-only
  instantiation (<boost/json/src.hpp> in exactly one TU) via patch 0001
  (src/bali-phy/boost-json-src.cc). No boost recipe is modified.
* meson Boost resolution : meson resolves boost by scanning a root dir for
  headers + libraries. A minimal staging bundle (build_folder/boost-bundle)
  overlays the vendored boost/json headers and the header-only boost/system
  module on the compiled boost .so files so all five requested modules
  (program_options/random/system/chrono/json) resolve; the real boost
  include dir is added through cpp_args.
* runtime : the shared boost/fmt libraries are copied into the package
  lib/ and the binaries get a $ORIGIN/../lib DT_RUNPATH so installed
  executables are self-contained. The 29 builtins shared modules installed
  to lib/bali-phy/ are OHOS-signed so dlopen works.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, save
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain

# Compiled boost libraries the bali-phy link needs at runtime (meson
# modules program_options/chrono/random plus the program_options
# transitive dependency container). system is header-only; the missing
# json/uuid/convert/rational/compute headers are vendored.
_BOOST_RUNTIME_LIBS = (
    "libboost_program_options.so",
    "libboost_chrono.so",
    "libboost_random.so",
    "libboost_container.so",
)


class BaliPhyConan(ConanFile):
    name = "bali-phy"
    version = "4.1"
    description = "BAli-Phy - joint Bayesian estimation of alignment and phylogeny"
    license = "GPL-2.0"
    homepage = "https://www.bali-phy.org/"
    url = "https://github.com/bredelings/BAli-Phy"
    topics = ("phylogenetics", "bayesian", "mcmc", "alignment", "bioinformatics")
    settings = "os", "compiler", "build_type", "arch"
    package_type = "application"
    exports_sources = "patches/**"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # boost 1.91.0.1.1 ships the compiled chrono/random/program_options
        # libs for OHOS; system is header-only; json/uuid/convert/rational/
        # compute headers are vendored (patches/boost-extra, verbatim).
        self.requires("boost/1.91.0.1.1", transitive_headers=True, transitive_libs=True)
        self.requires("eigen/3.4.1")
        self.requires("fmt/8.1.1", transitive_headers=True, transitive_libs=True)
        self.requires("cereal/1.3.2")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        PkgConfigDeps(self).generate()
        self._stage_boost_bundle()
        self._write_eigen3_pc()

        tc = MesonToolchain(self)
        tc.cpp_std = "c++20"
        tc.project_options["wrap_mode"] = "nodownload"
        tc.project_options["default_library"] = "static"
        boost = self.dependencies["boost"]
        tc.cpp_args.append("-I" + os.path.join(boost.package_folder, "include"))
        # self-contained installed executables (bin -> ../lib has the copied
        # boost/fmt .so); dlopen\x27d builtins inherit the executable DT_RUNPATH.
        tc.cpp_link_args.append("-Wl,-rpath,$ORIGIN/../lib")
        tc.properties["boost_root"] = [self._boost_bundle_dir()]
        tc.generate()
        self._inject_meson_binaries()

    def _boost_bundle_dir(self):
        return os.path.join(self.build_folder, "boost-bundle")

    def _stage_boost_bundle(self):
        boost = self.dependencies["boost"]
        boost_pkg = boost.package_folder
        staging = self._boost_bundle_dir()
        for sub in ("include/boost", "lib"):
            os.makedirs(os.path.join(staging, sub), exist_ok=True)
        shutil.copy(
            os.path.join(boost_pkg, "include", "boost", "version.hpp"),
            os.path.join(staging, "include", "boost", "version.hpp"),
        )
        extra_src = os.path.join(self.export_sources_folder, "patches", "boost-extra", "boost")
        for name in sorted(os.listdir(extra_src)):
            src = os.path.join(extra_src, name)
            dst = os.path.join(staging, "include", "boost", name)
            if os.path.isdir(src):
                shutil.copytree(src, dst)
            else:
                shutil.copy(src, dst)
        shutil.copytree(
            os.path.join(boost_pkg, "include", "boost", "system"),
            os.path.join(staging, "include", "boost", "system"),
        )
        for lib in _BOOST_RUNTIME_LIBS:
            shutil.copy(os.path.join(boost_pkg, "lib", lib), os.path.join(staging, "lib", lib))

    def _write_eigen3_pc(self):
        # meson asks pkg-config for \x27eigen3\x27; PkgConfigDeps only emits
        # \x27eigen\x27 (the conan package name). Emit a minimal eigen3.pc.
        eigen = self.dependencies["eigen"]
        pc = """prefix=%s
includedir=${prefix}/include/eigen3

Name: eigen3
Description: Eigen C++ template library
Version: %s
Cflags: -I${includedir}
""" % (eigen.package_folder, eigen.ref.version)
        save(self, os.path.join(self.generators_folder, "eigen3.pc"), pc)

    def _inject_meson_binaries(self):
        # OHOS conan 2.29.1 MesonToolchain does not emit ar/ranlib and the
        # pkg-config binary; inject them (same pattern as cairo-gobject).
        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if not os.path.isfile(native_file):
            return
        with open(native_file, encoding="utf-8") as handle:
            content = handle.read()
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c") or ""
        cpp = compilers.get("cpp") or ""
        bindir = os.path.dirname(cpp) if os.path.sep in cpp else ""
        ar = compilers.get("ar") or (os.path.join(bindir, "llvm-ar") if bindir else "")
        ranlib = compilers.get("ranlib") or (os.path.join(bindir, "llvm-ranlib") if bindir else "")
        pkg_config = shutil.which("pkg-config") or shutil.which("pkgconf") or ""
        entries = []
        nl = chr(10)
        if cc and nl + "c =" not in content:
            entries.append("c = \x27%s\x27" % cc)
        if cpp and nl + "cpp =" not in content:
            entries.append("cpp = \x27%s\x27" % cpp)
        if ar and nl + "ar =" not in content:
            entries.append("ar = \x27%s\x27" % ar)
        if ranlib and nl + "ranlib =" not in content:
            entries.append("ranlib = \x27%s\x27" % ranlib)
        if pkg_config and nl + "pkg-config =" not in content:
            entries.append("pkg-config = \x27%s\x27" % pkg_config)
        if entries and "[binaries]" in content:
            content = content.replace("[binaries]" + nl, "[binaries]" + nl + nl.join(entries) + nl, 1)
        with open(native_file, "w", encoding="utf-8") as handle:
            handle.write(content)

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()
        self._smoke_test()
        self._run_upstream_tests()

    def _shared_lib_env(self):
        boost_lib = os.path.join(self.dependencies["boost"].package_folder, "lib")
        fmt_lib = os.path.join(self.dependencies["fmt"].package_folder, "lib")
        return boost_lib, fmt_lib

    def _apply_runtime_env(self):
        boost_lib, fmt_lib = self._shared_lib_env()
        old = os.environ.get("LD_LIBRARY_PATH")
        os.environ["LD_LIBRARY_PATH"] = boost_lib + os.pathsep + fmt_lib + (os.pathsep + old if old else "")
        return old

    def _restore_env(self, old):
        if old is None:
            os.environ.pop("LD_LIBRARY_PATH", None)
        else:
            os.environ["LD_LIBRARY_PATH"] = old

    def _smoke_test(self):
        bp = os.path.join(self.build_folder, "src", "bali-phy", "bali-phy")
        if not os.path.isfile(bp):
            raise ConanException("bali-phy: built binary not found: %s" % bp)
        old = self._apply_runtime_env()
        try:
            self.run("%s --version" % bp)
            self.run("%s --help" % bp)
        finally:
            self._restore_env(old)

    def _run_upstream_tests(self):
        # Official upstream entry point: ninja -C build test (meson test,
        # ~218 tests incl. the tests/run-tests.py testsuite).
        #
        # Run with --num-processes 2 to match the upstream GitHub Actions
        # CI runner (2 cores).  The device has 12 cores: at default
        # parallelism the two long 5d MCMC analysis tests (upstream per-test
        # timeout: 300 s) starve under CPU contention and time out even
        # though they pass individually (each ~11-18 s).  All 218 tests are
        # still executed; 2-process load matches upstream CI and gives a
        # clean 218/218 pass.
        #
        # TEST_QUALITY_SPEC layer-1 gate: a failing upstream test must fail
        # the conan create.  self.run() raises on a non-zero exit code, so
        # meson test failures propagate and the build fails.  The two
        # xfail-marked upstream tests still run (meson does not set
        # should_fail for them).
        old = self._apply_runtime_env()
        try:
            self.run("meson test --print-errorlogs --num-processes 2 -C %s" % self.build_folder)
        finally:
            self._restore_env(old)

    def package(self):
        Meson(self).install()
        libdir = os.path.join(self.package_folder, "lib")
        os.makedirs(libdir, exist_ok=True)
        self._copy_runtime_libs(libdir)
        self._sign_ohos_runtime_tree()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def _copy_runtime_libs(self, libdir):
        boost = self.dependencies["boost"]
        for lib in _BOOST_RUNTIME_LIBS:
            shutil.copy(os.path.join(boost.package_folder, "lib", lib),
                        os.path.join(libdir, lib))
        fmt = self.dependencies["fmt"]
        fmt_src = os.path.join(fmt.package_folder, "lib")
        shutil.copy(os.path.join(fmt_src, "libfmt.so.8.1.1"),
                    os.path.join(libdir, "libfmt.so.8.1.1"))
        os.symlink("libfmt.so.8.1.1", os.path.join(libdir, "libfmt.so.8"))
        os.symlink("libfmt.so.8", os.path.join(libdir, "libfmt.so"))

    def _find_ohos_tool(self, name):
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        compiler_dir = os.path.dirname(compilers.get("cpp", ""))
        candidates = [
            os.path.join(compiler_dir, name) if compiler_dir else "",
            shutil.which(name) or "",
        ]
        return next((path for path in candidates if os.path.isfile(path)), "")

    def _sign_ohos_runtime_tree(self):
        if self.settings.os != "OHOS":
            return
        objcopy = self._find_ohos_tool("llvm-objcopy")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            self.output.warning("bali-phy: OHOS signing tools unavailable; builtins .so left unsigned")
            return
        builtins_dir = os.path.join(self.package_folder, "lib", "bali-phy")
        if not os.path.isdir(builtins_dir):
            return
        for name in sorted(os.listdir(builtins_dir)):
            candidate = os.path.join(builtins_dir, name)
            if os.path.islink(candidate) or not os.path.isfile(candidate):
                continue
            with open(candidate, "rb") as binary:
                if binary.read(4) != b"\x7fELF":
                    continue
            self._sign_elf(candidate, objcopy, signer)

    def _sign_elf(self, path, objcopy, signer):
        original_mode = os.stat(path).st_mode
        temporary = path + ".signing"
        try:
            shutil.copy2(path, temporary)
            self.run("\"%s\" --remove-section .codesign \"%s\"" % (objcopy, temporary))
            self.run("\"%s\" sign -inFile \"%s\" -outFile \"%s\" -selfSign 1" % (signer, temporary, temporary))
            os.chmod(temporary, original_mode)
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.remove(temporary)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        bindir = os.path.join(self.package_folder, "bin")
        self.buildenv_info.append_path("PATH", bindir)
        self.runenv_info.append_path("PATH", bindir)
        self.runenv_info.append_path("LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib"))
