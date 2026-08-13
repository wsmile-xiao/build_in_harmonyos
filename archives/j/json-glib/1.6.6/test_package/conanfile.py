import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("glib/2.84.0")

    def build(self):
        tmpdir = os.path.join(self.build_folder, ".tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir
        includes = []
        libdirs = []
        libs = []
        system_libs = []
        link_flags = []
        for _, dependency in self.dependencies.items():
            info = dependency.cpp_info
            includes.extend(info.includedirs)
            libdirs.extend(info.libdirs)
            libs.extend(info.libs)
            system_libs.extend(info.system_libs)
            link_flags.extend(info.sharedlinkflags)
            link_flags.extend(info.exelinkflags)

        include_flags = " ".join(f'-I"{path}"' for path in self._unique(includes))
        libdir_flags = " ".join(f'-L"{path}"' for path in self._unique(libdirs))
        lib_flags = " ".join(f"-l{name}" for name in self._unique(libs + system_libs))
        extra_link_flags = " ".join(self._unique(link_flags))
        executables = self.conf.get("tools.build:compiler_executables", default={}) or {}
        cc = executables.get("c")
        if not cc:
            raise ConanException("C compiler not found in tools.build:compiler_executables")
        test_source = os.path.join(self.source_folder, "test_json_glib.c")
        self.run(
            f'{cc} "{test_source}" -o test_json_glib '
            f"{include_flags} {libdir_flags} {lib_flags} {extra_link_flags}"
        )

    def test(self):
        if not can_run(self):
            self.output.info("non-runnable build: compile and link test completed")
            return
        libdirs = []
        for _, dependency in self.dependencies.items():
            libdirs.extend(dependency.cpp_info.libdirs)
        ld_library_path = ":".join(self._unique(libdirs))
        bash = os.environ.get("CONFIG_SHELL", "bash")
        self.run(
            f'{bash} -c \'LD_LIBRARY_PATH="{ld_library_path}:$LD_LIBRARY_PATH" '
            "./test_json_glib'",
            env="conanrun",
        )

    @staticmethod
    def _unique(items):
        seen = set()
        result = []
        for item in items:
            if item and item not in seen:
                seen.add(item)
                result.append(item)
        return result
