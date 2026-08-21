"""gbdk-2020: Game Boy / SMS / NES development kit.

The top-level Makefile injects the whole SDCC toolchain from $SDCCDIR
(cc1/sdcpp/sdar/sdasgb/sdldgb/packihx...) to compile target ROMs — this
is the real lib-to-lib linkage with our adapted sdcc 4.6.0 (path C
multi-lib batch).
"""
import os
import shutil
from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.files import copy, get


class Gbdk2020Conan(ConanFile):
    name = "gbdk-2020"
    version = "4.5.0"
    package_type = "static-library"
    license = "MIT"
    homepage = "https://github.com/gbdk-2020/gbdk-2020"
    url = "https://github.com/gbdk-2020/gbdk-2020"
    description = "Game Boy / SMS / NES development kit (SDCC-based toolchain)"
    settings = "os", "arch", "compiler", "build_type"
    generators = "PkgConfigDeps"

    def requirements(self):
        # gbdk's Makefile injects the whole SDCC toolchain via $SDCCDIR
        # (cc1/sdcpp/sdar/sdasgb/sdldgb/packihx...) to compile target ROMs
        self.requires("sdcc/4.6.0")

    def source(self):
        get(self, **self.conan_data["sources"][self.version],
            strip_root=True)

    def build(self):
        sdcc = self.dependencies["sdcc"]
        # SDCCDIR must point at the sdcc package root (bin/ + libexec/ inside)
        # — inject as command-prefix vars (env= list did not reach the
        # recursive make: "Makefile:362: *** SDCCDIR is undefined.")
        sdccbin = os.path.join(sdcc.package_folder, "bin")
        env_prefix = (f"SDCCDIR='{sdcc.package_folder}' "
                      f"PATH='{sdccbin}{os.pathsep}{os.environ.get('PATH', '')}'")
        tid = os.path.join(self.build_folder, "gbdk-install")
        # host tools (lcc/png2asset/bankpack/...) — Makefile hardcodes
        # CC=$(TOOLSPREFIX)gcc, OHOS has no gcc → use clang;
        # TARGETSTRIP=/bin/true: stripped ELF fails to exec on OHOS
        # (code-signing policy — "Operation not permitted", sdcc same fix)
        self.run(
            f"{env_prefix} make -j1 gbdk-support-build gbdk-support-install "
            f"TARGETDIR={tid} "
            "CC=/data/service/hnp/bin/clang CXX=/data/service/hnp/bin/clang++ "
            "TARGETSTRIP=/bin/true",
            cwd=self.source_folder)
        # target libs — gbdk-lib/Makefile.common sets
        # SCC=$(SDCCDIR)/bin/sdcc and CC=$(SCC): must compile with SDCC
        # (NOT clang — SDCC-only flags -msm83/--max-allocs-per-node);
        # gbdk-lib-build runs check-SDCCDIR, SDCCDIR injected above.
        # PORTS limited to sm83+z80: mos6502 (NES) uses the NONBANKED
        # extension (__nonbanked) from gbdk's patched SDCC — stock sdcc
        # 4.6.0 rejects it (atoi.c:10 syntax error), GB/SMS cores pass.
        self.run(
            f"{env_prefix} make -j1 gbdk-lib-build gbdk-lib-install "
            f"TARGETDIR={tid} PORTS=\"sm83 z80\"",
            cwd=self.source_folder)
        # copy the SDCC bins (from $SDCCDIR) into the gbdk build dir so
        # the packaged lcc finds sdcc/sdasgb/sdldgb/cc1 at runtime
        self.run(
            f"{env_prefix} make -j1 sdcc-install TARGETDIR={tid}",
            cwd=self.source_folder)

    def package(self):
        # build output lands in build/gbdk (bin/lib/include/share)
        bdir = os.path.join(self.build_folder, "gbdk")
        if not os.path.isdir(bdir):
            bdir = os.path.join(self.source_folder, "build", "gbdk")
        if not os.path.isdir(bdir):
            raise Exception(f"gbdk build dir missing: {bdir}")
        for entry in ("bin", "lib", "include", "share", "libexec"):
            s = os.path.join(bdir, entry)
            if os.path.isdir(s):
                copy(self, "*", src=s,
                     dst=os.path.join(self.package_folder, entry))

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.env_info.PATH.append(os.path.join(self.package_folder, "bin"))
