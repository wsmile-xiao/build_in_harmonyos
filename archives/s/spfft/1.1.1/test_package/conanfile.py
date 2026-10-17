import os
import shutil

from conan import ConanFile
from conan.tools.layout import basic_layout


class SpfftTestConan(ConanFile):
    """Consumer test: compile, link and run a real 2x2x2 C2C round trip
    against the packaged SpFFT headers and library."""

    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv", "VirtualBuildEnv"
    test_type = "explicit"
    exports_sources = "test_spfft.c"

    def requirements(self):
        self.requires(self.tested_reference_str)

    @property
    def _is_ohos(self):
        return str(self.settings.os) == "OHOS"

    def layout(self):
        basic_layout(self)

    def build(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = (compilers or {}).get("c") or "clang"
        cpp = self.dependencies["spfft"].cpp_info.aggregated_components()
        includes = " ".join(f'-I"{p}"' for p in cpp.includedirs)
        libdirs = " ".join(f'-L"{p}"' for p in cpp.libdirs)
        libs = " ".join(f"-l{name}" for name in cpp.libs)
        system = " ".join(f"-l{name}" for name in cpp.system_libs)
        source = os.path.join(self.source_folder, "test_spfft.c")
        binary = os.path.join(self.build_folder, "test_spfft")
        cmd = (f'"{cc}" {includes} "{source}" -o "{binary}" {libdirs} '
               f'{libs} {system} -lm')
        self.run(cmd, env="conanbuild")
        if self._is_ohos:
            # HarmonyOS PC refuses to execute unsigned ELF binaries.
            import subprocess
            signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
            subprocess.run([signer, "sign", "-inFile", binary,
                            "-outFile", binary + ".signed", "-selfSign", "1"],
                           check=True)
            os.replace(binary + ".signed", binary)
            os.chmod(binary, 0o755)

    def test(self):
        binary = os.path.join(self.build_folder, "test_spfft")
        # OHOS: /system/bin/sh cannot exec ELF binaries; wrap with bash.
        # Direct exec: the device shell execs the signed ELF fine, while
        # the hnp bash wrapper ENOEXECs it (measured 2026-09-25).
        self.run(f'"{binary}"', env="conanrun")
