"""Actual upstream 1.6.0; repair identity 1.6.0.2, never an invented tag."""
import json
import os
from pathlib import Path
import shlex
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMakeToolchain, cmake_layout
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class LibwebpConan(ConanFile):
    name = "libwebp"
    version = "1.6.0.2"
    description = "WebP image codec with complete original FuzzTest validation"
    license = "BSD-3-Clause"
    homepage = "https://github.com/webmproject/libwebp"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    exports_sources = "sign_link.py", "run_original_tests.py"

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("This tested recipe requires the native POSIX upstream harness")
        if not can_run(self):
            raise ConanInvalidConfiguration("Complete original tests require a runnable target, not a cross-build-only PASS")

    def layout(self):
        cmake_layout(self, src_folder=".")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        for name, spec in self.conan_data["test_sources"].items():
            get(self, **spec, destination=os.path.join(self.source_folder, "upstream-test-sources", name))
        # Execute the original libwebp patch, unchanged, in its intended cwd.
        script = os.path.join(self.source_folder, "tests", "fuzzer", "patch.sh")
        self.run("sh " + shlex.quote(script), cwd=os.path.join(self.source_folder, "upstream-test-sources", "fuzztest"))
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            # CMake's generic HarmonyOS rules lack ELF SONAME/runtime flags.
            for language in ("C", "CXX"):
                tc.variables["CMAKE_SHARED_LIBRARY_SONAME_" + language + "_FLAG"] = "-Wl,-soname,"
                tc.variables["CMAKE_SHARED_LIBRARY_RUNTIME_" + language + "_FLAG"] = "-Wl,-rpath,"
                tc.variables["CMAKE_SHARED_LIBRARY_RUNTIME_" + language + "_FLAG_SEP"] = ":"
                tc.variables["CMAKE_SHARED_LIBRARY_RPATH_LINK_" + language + "_FLAG"] = "-Wl,-rpath-link,"
            tc.variables["CMAKE_BUILD_RPATH_USE_ORIGIN"] = True
        self._compiler_paths = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        tools = {key: shutil.which(name) for key, name in (("readelf", "llvm-readelf"), ("objcopy", "llvm-objcopy"), ("signer", "binary-sign-tool"))}
        if self.settings.os == "OHOS" and not all(tools.values()):
            raise ConanInvalidConfiguration("Native signing tools must be present in the declared build environment")
        config = dict(root=str(Path(self.build_folder).resolve()), ohos=self.settings.os == "OHOS", **tools)
        path = Path(self.generators_folder) / "signing-tools.json"
        path.write_text(json.dumps(config), encoding="utf-8")
        wrappers = {}
        shell = shutil.which("sh")
        if not shell:
            raise ConanInvalidConfiguration("Missing real POSIX shell")
        for name, language in (("cc", "c"), ("cxx", "cpp")):
            real = self._compiler_paths.get(language) or shutil.which("clang" if language == "c" else "clang++")
            if not real:
                raise ConanInvalidConfiguration("Missing real " + language + " compiler")
            wrapper = Path(self.generators_folder) / name
            script = Path(self.source_folder) / "sign_link.py"
            wrapper.write_text("#!" + shell + "\nexec " + " ".join(shlex.quote(v) for v in (sys.executable, str(script), str(path), real)) + " \"$@\"\n", encoding="utf-8")
            wrapper.chmod(0o755)
            wrappers[language] = str(wrapper)
        self._native_compilers = wrappers
        # The official CompilersBlock emits unconditional normal variables;
        # command-line -D compiler cache entries alone would not override it.
        tc.blocks["compilers"].values["compilers"].update(
            {"C": wrappers["c"], "CXX": wrappers["cpp"]})
        tc.generate()

    def _definitions(self, tests):
        compilers = {k: str(Path(self.generators_folder) / v) for k, v in (("c", "cc"), ("cpp", "cxx"))}
        values = {
            "CMAKE_C_COMPILER": compilers["c"], "CMAKE_CXX_COMPILER": compilers["cpp"],
            "CMAKE_BUILD_TYPE": str(self.settings.build_type), "CMAKE_INSTALL_LIBDIR": "lib",
            "BUILD_SHARED_LIBS:BOOL": "ON" if self.options.shared else "OFF",
            "WEBP_BUILD_FUZZTEST:BOOL": "ON" if tests else "OFF",
            "WEBP_BUILD_LIBWEBPMUX:BOOL": "ON", "WEBP_BUILD_WEBPINFO:BOOL": "ON" if tests else "OFF",
            "CMAKE_POLICY_VERSION_MINIMUM": "3.10", "CMAKE_EXPORT_COMPILE_COMMANDS:BOOL": "ON",
        }
        for name in ("CWEBP", "DWEBP", "GIF2WEBP", "IMG2WEBP", "VWEBP", "WEBPMUX", "ANIM_UTILS", "EXTRAS"):
            values["WEBP_BUILD_" + name + ":BOOL"] = "OFF"
        if tests:
            for name in self.conan_data["test_sources"]:
                values["FETCHCONTENT_SOURCE_DIR_" + name.upper() + ":PATH"] = str(Path(self.source_folder) / "upstream-test-sources" / name)
            values["FETCHCONTENT_FULLY_DISCONNECTED:BOOL"] = "ON"
        probe = Path(self.build_folder) / "soname-symlink-probe"
        try:
            os.symlink("nonexistent-probe-target", probe)
        except OSError:
            values["CMAKE_PLATFORM_NO_VERSIONED_SONAME:BOOL"] = "ON"
        else:
            probe.unlink()
        return " ".join(shlex.quote("-D" + k + "=" + v) for k, v in values.items())

    def _cmake(self, tests):
        bdir = Path(self.build_folder) / ("upstream-build" if tests else "package-build")
        toolchain = Path(self.generators_folder) / "conan_toolchain.cmake"
        self.run("cmake -S " + shlex.quote(self.source_folder) + " -B " + shlex.quote(str(bdir)) + " -G 'Unix Makefiles' -DCMAKE_TOOLCHAIN_FILE=" + shlex.quote(str(toolchain)) + " " + self._definitions(tests))
        self.run("cmake --build " + shlex.quote(str(bdir)) + " --parallel 1")
        return bdir

    def build(self):
        self._cmake(False)
        bdir = self._cmake(True)
        script = Path(self.source_folder) / "run_original_tests.py"
        self.run(" ".join(shlex.quote(str(x)) for x in (sys.executable, script, self.source_folder, bdir)))

    def package(self):
        bdir = Path(self.build_folder) / "package-build"
        self.run("cmake --install " + shlex.quote(str(bdir)) + " --prefix " + shlex.quote(self.package_folder))
        config = Path(self.generators_folder) / "signing-tools.json"
        script = Path(self.source_folder) / "sign_link.py"
        for path in sorted((Path(self.package_folder) / "lib").glob("*.so*")):
            if path.is_file() and not path.is_symlink():
                self.run(" ".join(shlex.quote(str(x)) for x in (sys.executable, script, config, "--sign-package", self.package_folder, path)))
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "WebP")
        for name, libs, requires in (
                ("sharpyuv", ["sharpyuv"], []),
                ("webp", ["webp"], ["sharpyuv"]),
                ("webpdecoder", ["webpdecoder"], ["sharpyuv"]),
                ("webpdemux", ["webpdemux"], ["webp"]),
                ("webpmux", ["webpmux"], ["webp"])):
            component = self.cpp_info.components[name]
            component.libs = libs
            component.requires = requires
            component.set_property("cmake_target_name", "WebP::" + name)
            component.set_property("pkg_config_name", "lib" + name)
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.components["webp"].system_libs = ["m", "pthread"]
