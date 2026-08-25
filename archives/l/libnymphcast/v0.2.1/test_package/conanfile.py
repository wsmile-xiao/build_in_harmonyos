import os
import subprocess

from conan import ConanFile
from conan.tools.build import cross_building


class LibnymphcastTestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "PkgConfigDeps", "VirtualRunEnv", "VirtualBuildEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _dep_includedirs(self):
        dirs = []
        for _r, d in self.dependencies.items():
            base = getattr(d, "package_folder", None) or ""
            # Root include dir covers <nymph/nymph.h> (nymphrpc declares
            # includedirs=["include/nymph"] but libnymphcast uses parent form).
            root_inc = os.path.join(base, "include")
            if os.path.isdir(root_inc) and root_inc not in dirs:
                dirs.append(root_inc)
            for p in d.cpp_info.includedirs:
                if not os.path.isabs(p) and base:
                    p = os.path.join(base, p)
                if os.path.isdir(p) and p not in dirs:
                    dirs.append(p)
        return dirs

    def _dep_libdirs(self):
        dirs = []
        for _r, d in self.dependencies.items():
            for p in d.cpp_info.libdirs:
                if os.path.isdir(p) and p not in dirs:
                    dirs.append(p)
        return dirs

    def _sdk_llvm_libdir(self, cc):
        """SDK llvm/lib dir that ships libxml2.so.16 (lld dependency).

        `clang++ -print-resource-dir` prints <sdk>/llvm/lib/clang/<ver>; the SDK
        llvm/lib dir is its grandparent, where lld's RUNPATH ($ORIGIN/../lib)
        points and libxml2.so.16 lives. Falls back to the known OHOS build-host
        SDK path if derivation fails.
        """
        try:
            res_dir = subprocess.check_output(
                [cc, "-print-resource-dir"], stderr=subprocess.DEVNULL, text=True
            ).strip()
            if res_dir:
                lib_dir = os.path.dirname(os.path.dirname(res_dir))
                if os.path.isfile(os.path.join(lib_dir, "libxml2.so.16")):
                    return lib_dir
        except (OSError, ValueError, subprocess.CalledProcessError):
            pass
        # Derivation unavailable: fall back to the fixed SDK llvm/lib layout of the
        # OHOS build host (WWR-06 documented deviation).
        return "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib"

    def build(self):
        inc_flags = " ".join("-I " + d for d in self._dep_includedirs())
        lib_flags = " ".join("-L " + d for d in self._dep_libdirs())

        cppstd = self.settings.get_safe("compiler.cppstd")
        std_flag = "-std=c++%s" % str(cppstd).replace("gnu", "") if cppstd else "-std=c++17"

        _comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = _comp_execs.get("cpp", "clang++")
        libs = "-lnymphcast -lnymphrpc -lPocoNet -lPocoUtil -lPocoFoundation -lPocoJSON -pthread"

        cmd = "%s %s test.cpp -o test_probe %s %s %s" % (
            cc, std_flag, inc_flags, lib_flags, libs
        )

        # CI (PR #6431) fails at link start: clang's internal lld cannot load its
        # dependency libxml2.so.16 ("Error loading shared library libxml2.so.16
        # (needed by .../llvm/bin/lld)" / "linker command failed due to signal").
        # The CI loader does not resolve lld's DT_RUNPATH ($ORIGIN/../lib) into the
        # SDK llvm/lib dir (the local device loader does, so local probes pass).
        # Recipe-level fallback (user decision): prepend the SDK llvm/lib dir to
        # LD_LIBRARY_PATH for this link only, derived from the compiler resource dir
        # instead of hardcoding the SDK absolute path (WWR-06).
        sdk_llvm_lib = self._sdk_llvm_libdir(cc)
        _existing_ld = os.environ.get("LD_LIBRARY_PATH")
        ld_library_path = sdk_llvm_lib
        if _existing_ld:
            ld_library_path += os.pathsep + _existing_ld
        cmd = 'export LD_LIBRARY_PATH="%s"; %s' % (ld_library_path, cmd)
        self.run(cmd)

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: only compile+link verified")
            return
        _comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc_dir = os.path.dirname(_comp_execs.get("cpp", "clang++"))
        bash = os.environ.get("CONFIG_SHELL") or (os.path.join(cc_dir, "bash") if cc_dir else "bash")
        libdirs = []
        for _r, d in self.dependencies.items():
            libdirs += d.cpp_info.libdirs
        ldpath = os.pathsep.join(dict.fromkeys(libdirs))
        cmd = "%s -c 'export LD_LIBRARY_PATH=\"%s${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}\"; ./test_probe'" % (
            bash, ldpath
        )
        self.run(cmd, env="conanrun")
