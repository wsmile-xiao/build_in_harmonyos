import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building
from conan.tools.env import VirtualBuildEnv

# Standard bash location on OHOS CI workers (knowledge E325). Last-resort
# candidate only; user-specific paths must never be hardcoded here.
_HNP_BASH = "/data/service/hnp/bin/bash"


class MimicTestConan(ConanFile):
    """Consumer test for mimic/1.3.0.1.

    Compiles test.c against the *installed package* (include/ttsmimic +
    lib/libttsmimic*.a + share/mimic/voices), links the real static
    archives, and — because this build machine is itself the OHOS
    aarch64 target — executes a full text-to-speech synthesis natively.

    Also runs the HarmonyOS-specific artifact checks (ELF64/AArch64/
    NEEDED/RPATH) via llvm-readelf from the toolchain; see test_ohos.sh.
    """

    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # compiler from Conan conf (R33): never bare env vars
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang")
        if os.path.isfile(cc):
            cc_bin = cc
        else:
            cc_bin = shutil.which(os.path.basename(cc)) or cc

        # locate the installed package via the dependency graph
        pkg = None
        for _, dep in self.dependencies.items():
            if dep.ref.name == "mimic":
                pkg = dep
        if pkg is None:
            raise AssertionError("mimic dependency not found in graph")

        incdir = pkg.cpp_info.includedirs[0]
        libdir = pkg.cpp_info.libdirs[0]
        voice = os.path.join(pkg.package_folder, "share", "mimic",
                             "voices", "cmu_us_slt_hts.htsvoice")
        if not os.path.isfile(voice):
            raise AssertionError("packaged voice file not found: " + voice)

        # link every packaged static archive (same set as mimic.pc Libs)
        libs = " ".join("-l{}".format(l) for l in pkg.cpp_info.libs)

        # pcre2 is a transitive link dependency (mimic.pc Requires it):
        # add its libdir from the dependency graph.
        ldpaths = [libdir]
        for _, dep in self.dependencies.items():
            if dep.ref.name == "pcre2":
                for d in dep.cpp_info.libdirs:
                    ldpaths.append(d if os.path.isabs(d)
                                   else os.path.join(dep.package_folder, d))

        self.run(
            f'"{cc_bin}" -O1 -g '
            f'-I"{incdir}" "{self.source_folder}/test.c" '
            f'-L' + " -L".join('"' + l + '"' for l in ldpaths) +
            f' {libs} -lpcre2-8 -lm '
            f'-o "{self.build_folder}/test_mimic"',
            env="conanbuild",
        )
        self.output.info("built test_mimic against installed package")

    def test(self):
        pkg = None
        for _, dep in self.dependencies.items():
            if dep.ref.name == "mimic":
                pkg = dep
        voices = os.path.join(pkg.package_folder, "share", "mimic", "voices")
        if not os.path.isfile(os.path.join(voices, "cmu_us_slt_hts.htsvoice")):
            raise AssertionError("packaged voice file not found: " + voices)
        binpath = os.path.join(self.build_folder, "test_mimic")

        if cross_building(self):
            self.output.info("cross-building: compile+link check only")
            return
        # this CI machine is the OHOS aarch64 target itself: real run
        # of the full TTS pipeline (text -> HTS -> WAV). The test chdirs
        # into the voices dir (HTS engine resolves the .htsvoice
        # relative to the CWD at synthesis time).
        self.run(f'"{binpath}" "{voices}"', env="conanrun",
                 cwd=self.build_folder)

        # HarmonyOS-specific artifact checks on the installed package
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang")
        cc_bin = cc if os.path.isfile(cc) else (shutil.which(os.path.basename(cc)) or cc)
        bindir = os.path.dirname(cc_bin)
        readelf = os.path.join(bindir, "llvm-readelf")
        if not os.path.isfile(readelf):
            readelf = shutil.which("llvm-readelf") or shutil.which("readelf")

        # Resolve a usable bash: (1) Conan build environment — profile
        # [buildenv] (CONFIG_SHELL/SHELL/PATH) + tool_requires buildenv_info,
        # exactly what the conanbuild env script exports; (2) the ambient
        # process environment; (3) any bash on the composed PATH; (4) the
        # standard OHOS worker location. Never hardcode user-specific paths,
        # and fail loudly when nothing resolves instead of picking a missing
        # path ("inaccessible or not found").
        build_env = VirtualBuildEnv(self).vars()
        candidates = [
            build_env.get("CONFIG_SHELL"),
            build_env.get("SHELL"),
            os.environ.get("CONFIG_SHELL"),
            os.environ.get("SHELL"),
        ]
        search_path = (build_env.get("PATH") or os.environ.get("PATH") or "")
        candidates += [os.path.join(pdir, "bash")
                       for pdir in search_path.split(os.pathsep) if pdir]
        candidates += [_HNP_BASH]

        bash = None
        tried = []
        for candidate in candidates:
            if not candidate or candidate in tried:
                continue
            tried.append(candidate)
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                bash = candidate
                break
        if bash is None:
            raise ConanException(
                "no usable bash found to run test_ohos.sh; tried: "
                + ", ".join(tried)
                + ". Set CONFIG_SHELL/SHELL or extend PATH in the profile "
                  "[buildenv] (e.g. CONFIG_SHELL=/data/service/hnp/bin/bash)."
            )
        self.output.info(f"test_ohos.sh shell: {bash}")

        cmd = (
            f'MIMIC_LIBDIR="{pkg.cpp_info.libdirs[0]}" '
            f'MIMIC_TESTBIN="{binpath}" '
            f'MIMIC_READELF="{readelf}" '
            f'"{bash}" "{self.source_folder}/test_ohos.sh"'
        )
        self.run(cmd, cwd=self.build_folder)
