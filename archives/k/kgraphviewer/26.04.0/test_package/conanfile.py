#!/usr/bin/env python3
"""Conan test_package for kgraphviewer 26.04.0.

Two layers of consumer verification (upstream ships no tests; see the
NO_UPSTREAM_TESTS discovery record in manifest.yaml):

1. A C++ consumer binary that runs offscreen (QT_QPA_PLATFORM=offscreen):
   - loads the installed kgraphviewerpart KParts plugin via QPluginLoader
     and casts it to KParts::ReadOnlyPart (validates the vendored
     libKF6Parts.so.6 ABI and the plugin/link closure),
   - opens a local .dot file and waits for the KParts completed() signal,
     which for the InternalLibrary layout method covers the full
     in-process parse + graphviz layout pipeline,
   - additionally drives the graphviz C API directly (cgraph agread + gvc
     dot layout + plain render) to prove the FindGraphviz bridge link
     closure and the graphviz plugin config lookup via GVBINDIR.

2. OHOS-specific ELF assertions executed in this test() method with
   readelf against the installed package artifacts:
   - libkgraphviewer.so has a DT_SONAME (CMake has no Platform/HarmonyOS
     module; the recipe provides the SONAME flag explicitly),
   - no absolute or ..-prefixed DT_NEEDED entries in the shipped .so
     files (relocatable linking, CI L5b semantics),
   - libQt6PrintSupport is NOT among the DT_NEEDED entries (verifies the
     compiled-out printing subsystem on this platform),
   - the graphviz closure (libgvc) IS among the DT_NEEDED entries
     (verifies the E447 FindGraphviz cache-variable bridge actually
     linked the vendored graphviz libraries).
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment

# E537: keep in sync with the recipe's OHOS_E537_FIXUP_CMAKE.
OHOS_E537_FIXUP_CMAKE = r"""
# OHOS E537: relocatable linkage for soname-less published KF6 dependencies.
set(OHOS_SONAME_LESS_DEPS
    KF6::CoreAddons KF6::I18n KF6::ConfigCore KF6::ConfigGui
    KF6::ColorScheme KF6::GuiAddons KF6::WidgetsAddons KF6::Service
    KF6::ItemViews KF6::WindowSystem KF6::Codecs Qt6::Core5Compat
)
set(OHOS_SONAME_PROXIES "${CMAKE_BINARY_DIR}/ohos-soname-proxies")
macro(find_package)
  _find_package(${ARGV})
  ohos_relocatable_link_fixup()
endmacro()
function(ohos_relocatable_link_fixup)
  foreach(_t ${OHOS_SONAME_LESS_DEPS})
    if(NOT TARGET ${_t})
      continue()
    endif()
    get_target_property(_done ${_t} OHOS_SONAME_PROXY)
    if(_done)
      continue()
    endif()
    set_property(TARGET ${_t} PROPERTY OHOS_SONAME_PROXY TRUE)
    set(_loc "")
    foreach(_p IMPORTED_LOCATION_RELEASE IMPORTED_LOCATION)
      if(NOT _loc OR _loc STREQUAL "_loc-NOTFOUND")
        get_target_property(_loc ${_t} ${_p})
      endif()
    endforeach()
    if(_loc MATCHES "^/")
      get_filename_component(_b "${_loc}" NAME)
      set(_px "${OHOS_SONAME_PROXIES}/${_b}")
      set(_ok FALSE)
      if(EXISTS "${_px}")
        set(_ok TRUE)
      else()
        file(MAKE_DIRECTORY "${OHOS_SONAME_PROXIES}")
        find_program(OHOS_PATCHELF_EXE patchelf HINTS /data/service/hnp/bin)
        if(OHOS_PATCHELF_EXE)
          file(COPY_FILE "${_loc}" "${_px}")
          execute_process(
            COMMAND "${OHOS_PATCHELF_EXE}" --set-soname "${_b}" "${_px}"
            RESULT_VARIABLE _rc OUTPUT_QUIET ERROR_QUIET
          )
          if(_rc EQUAL 0)
            set(_ok TRUE)
          else()
            file(REMOVE "${_px}")
          endif()
        endif()
      endif()
      if(_ok)
        set_target_properties(${_t} PROPERTIES
          IMPORTED_LOCATION "${_px}"
          IMPORTED_LOCATION_RELEASE "${_px}")
      endif()
    endif()
  endforeach()
endfunction()
"""


class KgraphviewerTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()
        self._write_cmake_paths()

    def _tested_package(self):
        name = self.tested_reference_str.split("/")[0]
        return self.dependencies.get(name)

    def _write_cmake_paths(self):
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        pkg = self._tested_package()
        if pkg:
            # The tested package ships KF6PartsConfig.cmake (vendored
            # kparts) and KGraphViewerPartConfig.cmake under lib/cmake and
            # provides the kgraphviewer library under lib.
            lines.extend(
                [
                    f'list(PREPEND CMAKE_PREFIX_PATH '
                    f'"{pkg.package_folder}/lib/cmake")',
                    f'list(PREPEND CMAKE_LIBRARY_PATH '
                    f'"{pkg.package_folder}/lib")',
                    f'list(PREPEND CMAKE_INCLUDE_PATH '
                    f'"{pkg.package_folder}/include")',
                ]
            )
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lines.extend(
                    [
                        f'list(PREPEND CMAKE_PREFIX_PATH '
                        f'"{dep.package_folder}/lib/cmake")',
                        f'list(PREPEND CMAKE_LIBRARY_PATH '
                        f'"{dep.package_folder}/lib")',
                        f'list(PREPEND CMAKE_INCLUDE_PATH '
                        f'"{dep.package_folder}/include")',
                    ]
                )
        lines.append(
            'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")'
        )
        lines.append(
            'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")'
        )
        # E537 relocatable link: same find_package hook as the recipe (see
        # conanfile.py OHOS_E537_FIXUP_CMAKE) so the soname-less published
        # KF6/Qt5Compat dependency locations resolve through private
        # soname-stamped proxy copies instead of leaking absolute cache
        # paths into the test binary's DT_NEEDED.
        lines.append(
            OHOS_E537_FIXUP_CMAKE
        )
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        # E132: the OHOS SDK lld needs libxml2.so.16 from the SDK's
        # llvm/lib directory at link time (must not clobber other hosts).
        env = Environment()
        llvm_glob = os.path.join(
            "/data", "service", "hnp", "ohos-sdk.org"
        )
        if os.path.isdir(llvm_glob):
            for base in sorted(os.listdir(llvm_glob)):
                llvm_lib = os.path.join(
                    llvm_glob, base, "ohos", "native", "llvm", "lib"
                )
                if os.path.isdir(llvm_lib):
                    env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
        with env.vars(self).apply():
            cmake = CMake(self)
            cmake.configure()
            cmake.build()

    def _readelf_output(self, readelf, path):
        out = subprocess.run(
            [readelf, "-d", path],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if out.returncode != 0:
            raise Exception(
                "readelf -d {} failed: {}".format(path, out.stderr.strip())
            )
        return out.stdout

    def _elf_assertions(self, pkg):
        libdir = os.path.join(pkg.package_folder, "lib")
        readelf = shutil.which("readelf") or shutil.which("llvm-readelf")
        if not readelf:
            self.output.error("readelf not found for ELF assertions")
            return False
        failures = []

        def needed(path):
            entries = []
            soname = None
            for line in self._readelf_output(readelf, path).splitlines():
                if "(NEEDED)" in line:
                    entries.append(line.split("[")[-1].rstrip("]"))
                if "(SONAME)" in line:
                    soname = line.split("[")[-1].rstrip("]")
            return entries, soname

        # 1. DT_SONAME present on the shipped shared library (CI L5a
        #    semantics; requires the manual SONAME flag on HarmonyOS).
        main_lib = os.path.join(libdir, "libkgraphviewer.so.0")
        if not os.path.isfile(main_lib):
            failures.append("missing libkgraphviewer.so.0 in package lib/")
        else:
            entries, soname = needed(main_lib)
            if not soname or soname.startswith("/") or ".." in soname:
                failures.append(
                    "libkgraphviewer.so.0 DT_SONAME bad: {!r}".format(soname)
                )
            # 2. No absolute / ..-prefixed DT_NEEDED (relocatability).
            for e in entries:
                if e.startswith("/") or e.startswith("../"):
                    failures.append(
                        "libkgraphviewer.so.0 absolute DT_NEEDED: " + e
                    )
            # 3. Printing subsystem compiled out on OHOS.
            if any(e.startswith("libQt6PrintSupport") for e in entries):
                failures.append(
                    "libkgraphviewer.so.0 still NEEDs libQt6PrintSupport"
                )
            # 4. Graphviz closure actually linked (E447 bridge).
            if not any(e.startswith("libgvc.so") for e in entries):
                failures.append(
                    "libkgraphviewer.so.0 does not NEED libgvc.so (graphviz "
                    "bridge not linked)"
                )

        # 5. Vendored KParts shipped and relocatable.
        kparts_lib = os.path.join(libdir, "libKF6Parts.so.6")
        if not os.path.isfile(kparts_lib):
            failures.append("vendored libKF6Parts.so.6 missing from package")
        else:
            entries, soname = needed(kparts_lib)
            if not soname or soname.startswith("/") or ".." in soname:
                failures.append(
                    "libKF6Parts.so.6 DT_SONAME bad: {!r}".format(soname)
                )
            for e in entries:
                if e.startswith("/") or e.startswith("../"):
                    failures.append(
                        "libKF6Parts.so.6 absolute DT_NEEDED: " + e
                    )

        part = os.path.join(
            libdir, "plugins", "kf6", "parts", "kgraphviewerpart.so"
        )
        if not os.path.isfile(part):
            failures.append("kgraphviewerpart.so plugin missing from package")

        for f in failures:
            self.output.error("OHOS ELF assertion FAILED: " + f)
        if not failures:
            self.output.info(
                "OHOS ELF assertions passed: DT_SONAME present, no absolute "
                "DT_NEEDED, no Qt6PrintSupport, graphviz closure linked, "
                "vendored libKF6Parts.so.6 + plugin shipped"
            )
        return not failures

    def test(self):
        pkg = self._tested_package()
        if not pkg:
            raise Exception("tested package not in the dependency graph")

        elf_ok = self._elf_assertions(pkg)

        test_home = os.path.join(self.build_folder, "test-home")
        xdg_runtime = os.path.join(self.build_folder, "xdg-runtime")
        os.makedirs(test_home, exist_ok=True)
        os.makedirs(xdg_runtime, exist_ok=True)
        os.chmod(xdg_runtime, 0o700)

        # OHOS runtime preparation (deterministic, applied directly to the
        # process environment so the smoke, ctest and the explicit test run
        # all inherit it):
        #  - LD_LIBRARY_PATH covers every dependency libdir plus the tested
        #    package and /system/lib64 (E132-style libc++_shared priority);
        #  - the published kconfig package records a cwd-relative DT_NEEDED
        #    (../../bin/libKF6ConfigCore.so) in libKF6ConfigGui.so, so the
        #    consumer runs from <build>/ohos-runtime/cwd/x with
        #    <build>/ohos-runtime/bin holding symlinks to every dependency
        #    library file;
        #  - QT_PLUGIN_PATH exposes the Qt platform plugins (offscreen).
        lib_dirs = [
            os.path.join(p.package_folder, "lib")
            for p in self.dependencies.values()
            if p.package_folder
        ]
        lib_dirs.append(os.path.join(pkg.package_folder, "lib"))
        lib_dirs.append("/system/lib64")

        runtime_bin = os.path.join(self.build_folder, "ohos-runtime", "bin")
        runtime_cwd = os.path.join(
            self.build_folder, "ohos-runtime", "cwd", "x"
        )
        os.makedirs(runtime_bin, exist_ok=True)
        os.makedirs(runtime_cwd, exist_ok=True)
        for d in lib_dirs[:-1]:
            if not os.path.isdir(d):
                continue
            for f in os.listdir(d):
                if f.startswith("lib") and ".so" in f:
                    dst = os.path.join(runtime_bin, f)
                    if not os.path.lexists(dst):
                        try:
                            os.symlink(os.path.join(d, f), dst)
                        except OSError:
                            pass

        ld_path = ":".join(lib_dirs + [runtime_bin])
        os.environ["LD_LIBRARY_PATH"] = ld_path
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        os.environ["QT_PLUGIN_PATH"] = ":".join(
            os.path.join(p.package_folder, "plugins")
            for p in self.dependencies.values()
            if p.package_folder
            and os.path.isdir(os.path.join(p.package_folder, "plugins"))
        )
        gv = self.dependencies.get("graphviz")
        if gv and gv.package_folder:
            os.environ["GVBINDIR"] = os.path.join(
                gv.package_folder, "lib", "graphviz"
            )
        os.environ["KGV_PART_PLUGIN"] = os.path.join(
            pkg.package_folder,
            "lib",
            "plugins",
            "kf6",
            "parts",
            "kgraphviewerpart.so",
        )
        os.environ["HOME"] = test_home
        os.environ["XDG_RUNTIME_DIR"] = xdg_runtime
        os.environ["XDG_CACHE_HOME"] = os.path.join(test_home, ".cache")
        os.environ["XDG_CONFIG_HOME"] = os.path.join(test_home, ".config")
        os.environ["XDG_DATA_HOME"] = os.path.join(
            test_home, ".local", "share"
        )

        # L2-style app smoke: the installed binary must answer --version
        # offscreen (this also covers QApplication construction on OHOS).
        bindir = os.path.join(pkg.package_folder, "bin")
        app = os.path.join(bindir, "kgraphviewer")
        smoke_ok = False
        if os.path.isfile(app):
            ret = self.run(
                "{} --version".format(app),
                cwd=runtime_cwd,
                ignore_errors=True,
            )
            smoke_ok = ret == 0
            self.output.info(
                "kgraphviewer --version smoke: rc={} ({})".format(
                    ret, "ok" if smoke_ok else "FAILED"
                )
            )
        else:
            self.output.error("kgraphviewer binary missing in package bin/")

        cmake = CMake(self)
        cmake.test()
        # L0d: run the test binary explicitly as well (the CTest
        # wrapper above is not detected as a self.run() call). The path
        # must be absolute: the command runs from the ohos-runtime cwd.
        test_bin = os.path.abspath(
            os.path.join(self.cpp.build.bindirs[0], "test_kgraphviewer")
        )
        ret = self.run(
            test_bin,
            cwd=runtime_cwd,
            ignore_errors=True,
        )
        self.output.info(
            "test_kgraphviewer in-process test rc={} ({})".format(
                ret, "ok" if ret == 0 else "FAILED"
            )
        )
        if elf_ok and smoke_ok and ret == 0:
            self.output.info("kgraphviewer test_package: ALL PASSED")
        else:
            raise Exception(
                "kgraphviewer test_package FAILED (elf_ok={} smoke_ok={})".format(
                    elf_ok, smoke_ok
                )
            )
