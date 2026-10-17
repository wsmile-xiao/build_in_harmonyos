#!/usr/bin/env python3
"""Conan recipe — devil 1.8.0.40.g6f3d5e9b (DevIL, CMake build).

Upstream: https://github.com/DentonW/DevIL pinned to commit
6f3d5e9bc5d173f56060fc8e14bed35c8edcfdcc (tag v1.8.0 + 40 commits, 2021-08-29).
The CMake project lives in the DevIL/ subdirectory of the archive; conandata
sources are extracted there directly so the source folder is the project root.

OHOS adaptations:
  - CMAKE_POLICY_VERSION_MINIMUM=3.5: upstream cmake_minimum_required(2.6/2.8)
    is rejected by device CMake >= 4 (same approach as leptonica/1.87.0).
  - CMAKE_SYSTEM_NAME=Linux: without it CMake falls back to the generic
    platform module, which silently drops shared-library SOVERSION/SONAME
    handling (libIL.so built with no DT_SONAME cannot be loaded).
  - src-ILUT excluded via patch: it hard-requires OpenGL/GLUT
    (find_package(... REQUIRED)); no desktop GL stack exists on OHOS.
    IL and ILU are still built (both SOVERSION 1).
  - PNG/JPEG are wired through DevIL's upstream-supported "custom location"
    variables (src-IL/CMakeLists.txt: set IL_PNG_LIB/IL_JPEG_LIB=ON plus
    PNG_INCLUDE_DIRS/PNG_LIBRARIES and JPEG_INCLUDE_DIRS/JPEG_LIBRARIES).
    This bypasses host find_package probing and links the Conan packages
    by absolute path. All other optional formats (TIFF, Jasper, MNG, LCMS2,
    OpenEXR, NVTT, Squish) keep upstream's optional find_package probing and
    are auto-disabled (IL_NO_*) when not found.
  - ELF signing: the OHOS dynamic loader rejects unsigned shared objects
    with "Error loading shared library ..." at load time (verified on the
    device). Every .so produced by the build (and every test executable)
    is therefore self-signed with binary-sign-tool before it is executed
    or packaged, mirroring libpng/1.6.58.2.
  - Upstream official test entry (.travis.yml at the repo root):
    `cmake DevIL && make all UnitTest benchmark`. Both upstream test
    targets are built AND executed in build():
      * benchmark against the upstream test image
        test/UnitTest/Data/Logo.png (upstream's own data/DevIL_logo.jpg is
        a 0-byte file at this commit; the run fails unless the DevIL error
        stack stays empty, because benchmark.c always exits 0);
      * UnitTest, the cppunit assertion suite (9 active tests), built
        against cppunit/1.15.1 (test_requires — kept out of devil's
        consumer closure) with a small include-wiring patch (0003) and
        executed: PASS = cppunit prints "OK (9)" and exits 0. The upstream
        suite hardcodes Windows-style relative paths (".\\Data\\Logo.png");
        on POSIX these are single literal filenames, so the run directory
        materializes files under exactly those names pointing at the
        upstream test data.
"""
import glob
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, load
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class DevilConan(ConanFile):
    name = "devil"
    version = "1.8.0.40.g6f3d5e9b"
    description = "Developer's Image Library (DevIL): open source image loading and processing"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/DentonW/DevIL"
    url = ""  # CI fills this

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("zlib/1.3.2")
        self.requires("libpng/1.6.58.2")
        self.requires("libjpeg/10")
        # Upstream official test entry (.travis.yml): make all UnitTest
        # benchmark. cppunit is only needed to build and run the upstream
        # UnitTest suite in build(); test_requires keeps it out of devil's
        # consumer closure (consumers never link or download cppunit).
        self.test_requires("cppunit/1.15.1")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"devil is only supported on Linux/OHOS, not {self.settings.os}")
        if not self.options.shared:
            raise ConanInvalidConfiguration(
                "static build not supported: upstream src-ILU/CMakeLists.txt "
                "hardcodes add_library(ILU SHARED ...)")

    def layout(self):
        # The archive strips to a tree whose CMake project is the DevIL/
        # subdirectory; extract the sources into src/DevIL so the source
        # folder is the CMake project root.
        cmake_layout(self, src_folder="src/DevIL")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True,
            destination=os.path.dirname(self.source_folder))

    def _dep_artifacts(self, dep_name):
        """Return (include_dir, first_lib_abs_path) of a direct dependency."""
        dep = self.dependencies[dep_name]
        include_dir = None
        for inc in dep.cpp_info.includedirs:
            if os.path.isdir(inc):
                include_dir = inc
                break
        lib_path = None
        for lib in dep.cpp_info.libs:
            for libdir in dep.cpp_info.libdirs:
                for ext in (".so", ".a"):
                    candidate = os.path.join(libdir, "lib%s%s" % (lib, ext))
                    if os.path.isfile(candidate):
                        lib_path = candidate
                        break
                if lib_path:
                    break
            if lib_path:
                break
        if not include_dir or not lib_path:
            raise ConanException(
                f"could not resolve artifacts of dependency {dep_name}: "
                f"include_dir={include_dir}, lib={lib_path}")
        return include_dir, lib_path

    def _ohos_enabled(self):
        return str(self.settings.os) == "OHOS"

    def _tool_in_compiler_dir(self, tool):
        """Resolve a binutils-style tool next to the configured compiler."""
        executables = self.conf.get("tools.build:compiler_executables",
                                    default={}, check_type=dict)
        for key in ("cpp", "c"):
            compiler = executables.get(key)
            if not compiler:
                continue
            compiler_dir = os.path.dirname(compiler)
            for candidate in (os.path.join(compiler_dir, tool),
                              os.path.join(compiler_dir, "llvm-" + tool)):
                if os.path.isfile(candidate):
                    return candidate
        return shutil.which(tool)

    def _signer_tool(self):
        signer = self._tool_in_compiler_dir("binary-sign-tool")
        if not signer:
            raise ConanException(
                "binary-sign-tool not found: required on OHOS because the "
                "dynamic loader rejects unsigned shared objects")
        return signer

    def _sign_elf(self, path):
        """Self-sign an ELF in place (OHOS loader requirement).

        Freshly built ELFs carry no .codesign section; files that were
        signed before (e.g. build-tree libraries copied into the package by
        cmake.install()) have the stale section removed first so the tool
        signs the current contents.
        """
        if not self._ohos_enabled() or not os.path.isfile(path):
            return
        signer = self._signer_tool()
        readelf = self._tool_in_compiler_dir("readelf")
        objcopy = self._tool_in_compiler_dir("objcopy")
        tmp = "%s.signing-%s" % (path, os.getpid())
        shutil.copy2(path, tmp)
        try:
            if readelf and objcopy:
                sections = subprocess.run([readelf, "-S", tmp],
                                          capture_output=True, text=True,
                                          check=True).stdout
                if ".codesign" in sections:
                    subprocess.run([objcopy, "--remove-section",
                                    ".codesign", tmp], check=True)
            subprocess.run([signer, "sign", "-inFile", tmp, "-outFile", tmp,
                            "-selfSign", "1"], check=True)
            if readelf:
                sections = subprocess.run([readelf, "-S", tmp],
                                          capture_output=True, text=True,
                                          check=True).stdout
                if ".codesign" not in sections:
                    raise ConanException(
                        f"signer did not add .codesign: {path}")
            os.replace(tmp, path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    def _sign_shared_libs(self, lib_dir):
        if not self._ohos_enabled() or not os.path.isdir(lib_dir):
            return
        for name in sorted(os.listdir(lib_dir)):
            if ".so" in name:
                self._sign_elf(os.path.join(lib_dir, name))

    def generate(self):
        tc = CMakeToolchain(self)
        # CMAKE_POLICY_VERSION_MINIMUM must be in place when cmake STARTS:
        # it is set both here (toolchain) and in the environment (build()).
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # Upstream declares cmake_minimum_required(2.6/2.8); device CMake 4.x
        # refuses anything < 3.5 without this override.
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        # Upstream default: shared libIL.so.1 / libILU.so.1 (SOVERSION 1).
        # Note src-ILU hardcodes add_library(ILU SHARED ...), so a static
        # build is not possible without further upstream surgery (validate()
        # rejects shared=False).
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        # Wire libpng/libjpeg via DevIL's custom-location variables instead
        # of host find_package probing (deterministic, no system pollution).
        tc.variables["IL_PNG_LIB"] = True
        tc.variables["IL_JPEG_LIB"] = True
        png_inc, png_lib = self._dep_artifacts("libpng")
        jpg_inc, jpg_lib = self._dep_artifacts("libjpeg")
        tc.variables["PNG_INCLUDE_DIRS"] = png_inc
        tc.variables["PNG_LIBRARIES"] = png_lib
        tc.variables["JPEG_INCLUDE_DIRS"] = jpg_inc
        tc.variables["JPEG_LIBRARIES"] = jpg_lib
        # The upstream UnitTest target finds cppunit through its own
        # Findcppunit module (test/UnitTest/cmake); feeding the module the
        # resolved conan artifacts keeps the search deterministic.
        cppunit = self.dependencies.get("cppunit")
        if cppunit is None:
            raise ConanException(
                "cppunit test_require is not visible in generate(); "
                "cannot wire the upstream UnitTest suite")
        cppunit_inc, cppunit_lib = self._dep_artifacts("cppunit")
        tc.variables["CPPUNIT_INCLUDE_DIR"] = cppunit_inc
        tc.variables["CPPUNIT_LIBRARY"] = cppunit_lib
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # CMAKE_POLICY_VERSION_MINIMUM must be in place when cmake STARTS: the
        # toolchain file (which also sets it) is loaded only at project(),
        # after the top-level cmake_minimum_required(2.6) is parsed and
        # rejected by CMake >= 4. The environment variable is honored from
        # startup (verified with the device CMake 4.1.2).
        env = Environment()
        env.define("CMAKE_POLICY_VERSION_MINIMUM", "3.5")
        with env.vars(self).apply():
            cmake.configure()
            cmake.build()
        lib_dir = os.path.join(self.build_folder, "lib", "x64")
        # The OHOS loader refuses unsigned shared objects; sign before any
        # test executable loads them.
        self._sign_shared_libs(lib_dir)
        # Upstream official test entry (.travis.yml): make all UnitTest
        # benchmark. Both targets are built and executed below.
        self._run_upstream_benchmark(lib_dir)
        self._run_upstream_unittest(lib_dir)

    def _runtime_lib_path(self, lib_dir):
        lib_paths = [lib_dir]
        for dep in self.dependencies.values():
            lib_paths.extend(libdir for libdir in dep.cpp_info.libdirs
                             if os.path.isdir(libdir))
        return ":".join(lib_paths)

    def _run_upstream_benchmark(self, lib_dir):
        cmake = CMake(self)
        cmake.build(target="benchmark")
        candidates = [p for p in glob.glob(os.path.join(self.build_folder,
                                                        "**", "benchmark"),
                                           recursive=True) if os.path.isfile(p)]
        if not candidates:
            raise ConanException("upstream benchmark binary not found in build tree")
        # NOTE: upstream's own sample data/DevIL_logo.jpg is a 0-byte file at
        # the pinned commit (empty blob in the DevIL repository). Feeding an
        # empty file to libjpeg drives DevIL's error path, which double-destroys
        # the jpeg struct (upstream defect) and corrupts the heap. Use the
        # upstream test image test/UnitTest/Data/Logo.png instead.
        logo = os.path.join(self.source_folder, "test", "UnitTest", "Data", "Logo.png")
        if not os.path.isfile(logo) or os.path.getsize(logo) == 0:
            raise ConanException(f"upstream test image missing or empty: {logo}")
        self._sign_elf(candidates[0])
        out_file = os.path.join(self.build_folder, "upstream_benchmark.out")
        # benchmark.c always exits 0; it prints the error stack ("Error: ...")
        # when loads failed, so the output must be inspected, not just the rc.
        # The build-tree binary resolves libIL/libILU via its CMake build rpath;
        # the transitive conan deps (libpng/zlib) need LD_LIBRARY_PATH, which is
        # set inline for this single invocation.
        self.run('LD_LIBRARY_PATH="%s" "%s" "%s" > "%s" 2>&1'
                 % (self._runtime_lib_path(lib_dir), candidates[0], logo,
                    out_file))
        content = load(self, out_file)
        self.output.info(content.strip())
        if "Error:" in content:
            raise ConanException(
                "upstream benchmark reported DevIL errors (see upstream_benchmark.out in build tree)")
        self.output.info("UPSTREAM BENCHMARK PASSED: 20x ilLoadImage with empty error stack")

    def _materialize_upstream_test_data(self, run_dir):
        """Make the upstream suite's Windows-style relative paths resolvable.

        The cppunit tests load ".\\Data\\Logo.png" (and ".\\Data\\Cardinal.gif")
        — on POSIX that string is a single literal filename, so materialize
        exactly those names in the run directory pointing at the real
        upstream test images. Saves from the suite land next to them as
        files named ".\\results\\*.bmp" (also literal names).
        """
        data_dir = os.path.join(self.source_folder, "test", "UnitTest", "Data")
        wanted = {
            ".\\Data\\Logo.png": os.path.join(data_dir, "Logo.png"),
            ".\\Data\\Cardinal.gif": os.path.join(data_dir, "Cardinal.gif"),
        }
        os.makedirs(run_dir, exist_ok=True)
        for literal, target in wanted.items():
            if not os.path.isfile(target):
                raise ConanException(f"upstream test data missing: {target}")
            link = os.path.join(run_dir, literal)
            if os.path.lexists(link):
                os.unlink(link)
            try:
                os.symlink(target, link)
            except OSError:
                shutil.copy2(target, link)

    def _run_upstream_unittest(self, lib_dir):
        cmake = CMake(self)
        cmake.build(target="UnitTest")
        candidates = [p for p in glob.glob(os.path.join(self.build_folder,
                                                        "**", "UnitTest"),
                                           recursive=True) if os.path.isfile(p)]
        if not candidates:
            raise ConanException(
                "upstream UnitTest binary not found in build tree (cppunit missing?)")
        self._sign_elf(candidates[0])
        run_dir = os.path.join(self.build_folder, "upstream_unittest_run")
        self._materialize_upstream_test_data(run_dir)
        out_file = os.path.join(run_dir, "upstream_unittest.out")
        self.run('cd "%s" && LD_LIBRARY_PATH="%s" "%s" > "%s" 2>&1'
                 % (run_dir, self._runtime_lib_path(lib_dir), candidates[0],
                    out_file))
        content = load(self, out_file)
        self.output.info(content.strip())
        import re
        match = re.search(r"OK \((\d+)\)", content)
        if not match:
            raise ConanException(
                "upstream cppunit UnitTest suite FAILED (no 'OK (n)' in output, "
                "see upstream_unittest.out in the build tree)")
        self.output.info(
            "UPSTREAM UNITTEST PASSED: cppunit reports OK (%s tests)" % match.group(1))

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"))
        # cmake.install() copies the (already signed) build-tree libraries;
        # sign defensively in the package folder so every shipped .so carries
        # a valid .codesign section (stale sections are refreshed in place).
        self._sign_shared_libs(os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["IL", "ILU"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
