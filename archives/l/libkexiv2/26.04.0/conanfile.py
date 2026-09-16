#!/usr/bin/env python3
"""Conan recipe for libkexiv2 26.04.0 on HarmonyOS PC.

libkexiv2 (KDE Gear) is the KExiv2 wrapper library around Exiv2: it exposes
EXIF/IPTC/XMP read/write helpers plus QImage-oriented conveniences on top of
libexiv2 and builds the shared library libKExiv2.so.

OHOS-specific adaptations:
  - No CMakeDeps generator is used. The dependencies are consumed through
    their own CMake package configs: qtbase is packaged with
    cmake_find_mode=none (its complete Qt6Config.cmake lives in the package),
    and the exiv2 package ships the upstream exiv2Config.cmake that defines
    the Exiv2::exiv2lib target this project links against, together with its
    transitive $<LINK_ONLY:EXPAT::EXPAT>/ZLIB::ZLIB closure (resolved through
    the prepended CMAKE_INCLUDE_PATH/CMAKE_LIBRARY_PATH entries).
    conan_cmakedeps_paths.cmake declares those prefix paths (libkcddb 26.04.3
    and kfilemetadata 6.28.0 precedents).
  - ECM_MODULE_PATH comes from the ecm package's own ECMConfig.cmake, which
    the prepended prefix path makes find_package(ECM CONFIG) pick up, so the
    KDE CMake modules (KDEInstallDirs/KDECMakeSettings/...) resolve.
  - The OHOS loader refuses to load a shared library through a symlink
    (knowledge E018/E511): the versioned soname chains shipped by the conan
    packages (libQt6Core.so.6 -> libQt6Core.so.6.11.1) are therefore
    materialised as regular-file copies in a private runtime-libs directory
    that is prepended to LD_LIBRARY_PATH. Without it both the configure step
    (ECM's ecm_query_qt runs qtpaths) and the upstream demo tools fail with
    "Error loading shared library ...". For the same reason the library built
    by this recipe gets an unversioned SONAME (CMAKE_PLATFORM_NO_VERSIONED_
    SONAME), so the package ships a single libKExiv2Qt6.so with no symlink
    chain, while still satisfying the CI L5a SONAME gate.
  - BUILD_TESTING=ON builds the 7 upstream demo tools under tests/. Upstream
    registers no ctest test (neither add_test() nor enable_testing() appears
    anywhere in the tree) and ships no test fixture, so those demo programs
    are the only upstream test entry point; build() executes all 7 of them
    against an embedded sample JPEG (R51).
"""
import base64
import glob
import json
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches

# The 7 programs under tests/ take an image path as their only argument and
# upstream ships no fixture of any kind. This is an 8x8 solid-grey JPEG
# (629 bytes) written by Qt6; it is materialised in the build folder so the
# upstream entry points can actually be executed.
_SAMPLE_JPEG_B64 = (
    "/9j/4AAQSkZJRgABAQEAZABkAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0a"
    "HBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIy"
    "MjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCAAIAAgDASIA"
    "AhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQA"
    "AAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3"
    "ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWm"
    "p6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEA"
    "AwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSEx"
    "BhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElK"
    "U1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3"
    "uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwAooooA"
    "/9k="
)

# Soname aliases of the conan dependencies that the project and its build-time
# Qt tools load at runtime (see the loader/symlink note in the docstring).
# exiv2 is linked as a static archive, expat is a shared library.
_DEPENDENCY_SONAME_ALIASES = ("libQt6Core.so.6", "libQt6Gui.so.6", "libexpat.so.1")


class Libkexiv2Conan(ConanFile):
    name = "libkexiv2"
    version = "26.04.0"
    description = "KDE wrapper around Exiv2 - picture metadata (EXIF/IPTC/XMP) for Qt"
    license = "BSD-3-Clause AND GPL-2.0-or-later"
    homepage = "https://invent.kde.org/graphics/libkexiv2"
    url = "https://download.kde.org/stable/release-service/26.04.0/src/libkexiv2-26.04.0.tar.xz"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    # The upstream test entry points: the 7 demo programs under tests/ with
    # their real command line ("<image>" is substituted with the sample
    # fixture). printtagslist ignores its arguments entirely, setxmpface takes
    # an <add|remove> operation before the image path.
    _upstream_demo_tools = (
        ("erasetag", ("<image>",)),
        ("loadfromba", ("<image>",)),
        ("printtagslist", ()),
        ("readimagewritexmpsidecar", ("<image>",)),
        ("setiptcpreview", ("<image>",)),
        ("setxmpface", ("add", "<image>")),
        ("usexmpsidecar", ("<image>",)),
    )

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1")
        self.requires("exiv2/0.28.7")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # tests/ is the only upstream test entry point (7 demo programs, no
        # add_test()/enable_testing()): build it so build() can run it.
        tc.variables["BUILD_TESTING"] = "ON"
        # The upstream project version and ABI version (top-level CMakeLists.txt:
        # project(libkexiv2 VERSION "5.1.0") and LIBKEXIV2_SO_VERSION "0").
        # ecm_setup_version() inside src/CMakeLists.txt is expected to publish
        # them as KEXIV2_VERSION/KEXIV2_SOVERSION, but with the ECM/CMake
        # combination used here the caller scope stays empty, so the project's
        # own set_target_properties() applies no VERSION/SOVERSION, CMake emits
        # no DT_SONAME and the CI L5a gate rejects the package ("缺少
        # DT_SONAME"). Supplying the values from the toolchain (which is loaded
        # before the project and is therefore visible in src/) restores them.
        tc.variables["KEXIV2_VERSION"] = "5.1.0"
        tc.variables["KEXIV2_SOVERSION"] = "0"
        # CMake has no Platform/HarmonyOS module, so
        # CMAKE_SHARED_LIBRARY_SONAME_<LANG>_FLAG stays empty and no -soname flag
        # would reach the linker. Provide it explicitly, and keep the SONAME
        # unversioned (Android precedent) so the package ships a single
        # libKExiv2Qt6.so instead of a symlink chain - the OHOS loader cannot
        # load libraries reached through a symlink (E018/E511).
        tc.variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = "TRUE"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        tc.generate()

        qtbase = self.dependencies.get("qtbase")
        exiv2 = self.dependencies.get("exiv2")
        ecm = self.dependencies.build.get("ecm")

        lines = []
        # Every host dependency (qtbase, exiv2 and their transitive expat/zlib)
        # must be reachable: exiv2Config.cmake resolves its static closure
        # through find_dependency(EXPAT)/find_dependency(ZLIB), which use CMake's
        # module mode and therefore need the include/lib dirs on the search
        # paths.
        for dep in self.dependencies.host.values():
            if dep and dep.package_folder:
                pkg = dep.package_folder
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{pkg}/lib/cmake")')
                lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{pkg}/lib")')
                lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{pkg}/include")')
        if ecm and ecm.package_folder:
            ecm_root = os.path.join(ecm.package_folder, "share", "ECM")
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_root}/cmake")')
            lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{ecm_root}/cmake")')
            lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{ecm_root}/modules")')
            lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{ecm_root}/find-modules")')
            lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{ecm_root}/kde-modules")')
            lines.append(f'list(PREPEND CMAKE_PROGRAM_PATH "{ecm.package_folder}/bin")')
        lines.append('list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        lines.append('list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        if qtbase:
            lines.append(f'set(CONAN_RUNTIME_LIB_DIRS "{qtbase.package_folder}/lib")')
        # CMAKE_FIND_PACKAGE_PREFER_CONFIG is deliberately left unset: the
        # exiv2 package ships an upstream exiv2Config.cmake whose static
        # closure is spelled $<LINK_ONLY:EXPAT::EXPAT>/$<LINK_ONLY:ZLIB::ZLIB>.
        # Those names come from CMake's module-mode FindEXPAT/FindZLIB; with
        # PREFER_CONFIG=ON the nested find_dependency(EXPAT) instead resolves
        # the conan expat-config.cmake, which only exports expat::expat and
        # leaves EXPAT::EXPAT undefined (exiv2Targets.cmake then fails at
        # generate time).
        with open(
            os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake"), "w"
        ) as handle:
            handle.write("\n".join(lines) + "\n")

    def build(self):
        apply_conandata_patches(self)
        runtime_dir = self._materialise_dependency_aliases()
        with self._runtime_env(runtime_dir).vars(self).apply():
            cmake = CMake(self)
            cmake.configure()
            cmake.build()
        self._run_upstream_demo_tools(runtime_dir)

    def _runtime_env(self, runtime_dir):
        runtime_env = Environment()
        runtime_env.prepend_path("LD_LIBRARY_PATH", runtime_dir)
        # KDE's single-dir layout keeps the built library next to the demo
        # programs in <build>/bin, and those programs carry no RPATH.
        for rel in ("bin", "lib"):
            runtime_env.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(self.build_folder, rel)
            )
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                runtime_env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
        if str(self.settings.os) == "OHOS":
            # Qt's build-time tools are OHOS binaries that need the sandbox
            # libc++_shared.so (kconfig 6.26.0 / libkcddb 26.04.3 precedent).
            runtime_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        return runtime_env

    def _materialise_dependency_aliases(self):
        """Copy the dependencies' soname aliases into a private runtime dir.

        The OHOS loader rejects shared libraries reached through a symlink, so
        the libQt6Core.so.6 -> libQt6Core.so.6.11.1 chain shipped by the qtbase
        package cannot be loaded as-is (E511 materialize-versioned-so-aliases).
        """
        runtime_dir = os.path.join(self.build_folder, "runtime-libs")
        os.makedirs(runtime_dir, exist_ok=True)
        search_dirs = [
            os.path.join(dep.package_folder, "lib")
            for dep in self.dependencies.values()
            if dep and dep.package_folder
        ]
        for name in _DEPENDENCY_SONAME_ALIASES:
            source = None
            for directory in search_dirs:
                candidate = os.path.join(directory, name)
                if os.path.isfile(candidate):
                    source = os.path.realpath(candidate)
                    break
            if source is None:
                raise ConanException(
                    f"shared library alias '{name}' not found in {search_dirs}"
                )
            shutil.copy2(source, os.path.join(runtime_dir, name))
            self.output.info(f"materialised shared library alias {name}")
        return runtime_dir

    def _run_upstream_demo_tools(self, runtime_dir):
        """Execute the 7 upstream demo programs (the only upstream entry point)."""
        qtbase = self.dependencies.get("qtbase")
        test_env = self._runtime_env(runtime_dir)
        test_env.define("QT_QPA_PLATFORM", "offscreen")
        if qtbase:
            test_env.prepend_path(
                "QT_PLUGIN_PATH", os.path.join(qtbase.package_folder, "plugins")
            )

        sample = os.path.join(self.build_folder, "upstream-sample.jpg")
        with open(sample, "wb") as handle:
            handle.write(base64.b64decode(_SAMPLE_JPEG_B64))

        results = []
        with test_env.vars(self).apply():
            # Upstream registers no ctest test at all; record that fact as the
            # inventory baseline before running the demo programs.
            ctest_rc = self.run(
                f'ctest --test-dir "{self.build_folder}" -N',
                cwd=self.build_folder,
                ignore_errors=True,
            )
            self.output.info(
                f"ctest registry probe exit_code={ctest_rc} "
                "(upstream ships no add_test()/enable_testing(): no test to run)"
            )
            for tool, argv_template in self._upstream_demo_tools:
                candidates = [
                    path
                    for path in glob.glob(
                        os.path.join(self.build_folder, "**", tool), recursive=True
                    )
                    if os.path.isfile(path) and not path.endswith(".cmake")
                ]
                if not candidates:
                    raise ConanException(
                        f"upstream demo tool '{tool}' was not built although "
                        "BUILD_TESTING=ON is set"
                    )
                binary = candidates[0]
                arguments = [
                    sample if arg == "<image>" else arg for arg in argv_template
                ]
                command = " ".join(f'"{item}"' for item in [binary] + arguments)
                rc = self.run(command, cwd=self.build_folder, ignore_errors=True)
                self.output.info(f"upstream demo tool {tool}: exit_code={rc}")
                results.append({"tool": tool, "command": command, "exit_code": rc})

        report = os.path.join(self.build_folder, "upstream_test_result.json")
        with open(report, "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "ctest_registered_tests": 0,
                    "ctest_note": "upstream has no add_test()/enable_testing()",
                    "demo_tools": results,
                    "total": len(results),
                    "passed": sum(1 for item in results if item["exit_code"] == 0),
                    "failed": sum(1 for item in results if item["exit_code"] != 0),
                    "skipped": 0,
                },
                handle,
                indent=2,
            )
        self.output.info(f"upstream test result: {report}")
        self.output.info(f"upstream sample fixture: {sample}")

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # The project installs its own KExiv2Qt6Config.cmake (find_dependency on
        # Qt6Core/Qt6Gui, plus Exiv2 for static builds); keep CMakeDeps from
        # shadowing it.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        # OUTPUT_NAME is set to ${LIBRARYFILE_NAME} (=KExiv2Qt6) by
        # src/CMakeLists.txt, overriding the earlier KF6KExiv2 value.
        self.cpp_info.libs = ["KExiv2Qt6"]
