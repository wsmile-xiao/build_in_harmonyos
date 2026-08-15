import os
import subprocess

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.env import VirtualRunEnv


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        VirtualRunEnv(self).generate()

    def build(self):
        includes = []
        libdirs = []
        tested_libs = []
        dependency_libs = []
        system_libs = []
        tested_ref = self.dependencies["usbredir"].ref
        for _ref, dependency in self.dependencies.items():
            info = dependency.cpp_info
            includes.extend(info.includedirs)
            libdirs.extend(info.libdirs)
            if dependency.ref == tested_ref:
                tested_libs.extend(info.libs)
            else:
                dependency_libs.extend(info.libs)
            system_libs.extend(info.system_libs)

        def unique(items):
            seen = set()
            result = []
            for item in items:
                if item and item not in seen:
                    seen.add(item)
                    result.append(item)
            return result

        include_flags = " ".join(f'-I"{path}"' for path in unique(includes))
        libdir_flags = " ".join(f'-L"{path}"' for path in unique(libdirs))
        lib_flags = " ".join(
            f"-l{name}" for name in unique(tested_libs + dependency_libs + system_libs)
        )
        executables = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = executables.get("c") or os.environ.get("CC") or "cc"
        test_source = os.path.join(self.source_folder, "test_usbredir.c")
        test_binary = os.path.join(self.build_folder, "test_usbredir")
        self.run(
            f'{cc} "{test_source}" -o "{test_binary}" '
            f"{include_flags} {libdir_flags} {lib_flags}"
        )

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: compile and link test completed")
            return
        binary = os.path.join(self.build_folder, "test_usbredir")
        self._sign_if_needed(binary)
        self.run(binary, env="conanrun")

    def _sign_if_needed(self, binary):
        if str(self.settings.os) != "OHOS":
            return
        signer = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if not (os.path.isfile(signer) and os.path.isfile(objcopy)):
            return
        subprocess.run([objcopy, "--remove-section", ".codesign", binary], check=False)
        signed = binary + ".signed"
        subprocess.run(
            [signer, "sign", "-inFile", binary, "-outFile", signed, "-selfSign", "1"],
            check=True,
        )
        os.replace(signed, binary)
        os.chmod(binary, 0o755)
