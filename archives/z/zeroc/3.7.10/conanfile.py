from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.build import build_jobs
import os
import shutil
import subprocess


class ZerocIceConan(ConanFile):
    name = "zeroc"
    version = "3.7.10"
    description = "Ice (Internet Communications Engine) - ZeroC RPC framework, C++ edition"
    license = ("GPL-2.0-or-later", "Apache-2.0", "MIT")
    homepage = "https://github.com/zeroc-ice/ice"
    url = "https://github.com/zeroc-ice/ice"
    topics = ("zeroc", "ice", "rpc", "middleware")
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}
    requires = (
        "bzip2/1.0.8",
        "expat/2.8.2",
        "openssl/3.5.6",
        "lmdb/0.9.35",
        "libedit/20240817",
    )

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        # Make-based build: source and build tree are one and the same
        self.folders.source = "."
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Second source: ZeroC's mcpp fork (preprocessor used by slice2cpp;
        # the stock mcpp 2.7.2 tarball has a cyclic-include defect fixed in
        # this vendor tag)
        get(self, **self.conan_data["mcpp_source"], strip_root=True,
            destination=os.path.join(self.source_folder, "_mcpp"))
        apply_conandata_patches(self)

    def _build_prefix(self):
        """Directory that merges all dependency headers/libraries plus the
        locally built mcpp, mirroring the classic `<prefix>/include` +
        `<prefix>/lib` layout that the Ice makefiles expect through the
        MCPP_HOME/BZ2_HOME/EXPAT_HOME/LMDB_HOME variables."""
        return os.path.join(self.build_folder, "ohos-deps")

    def _merge_dep(self, dep_cf, prefix):
        dep_info = dep_cf.cpp_info
        for inc in dep_info.includedirs:
            copy(self, pattern="*", src=inc, dst=os.path.join(prefix, "include"), keep_path=True)
        for lib in dep_info.libdirs:
            for f in os.listdir(lib):
                fp = os.path.join(lib, f)
                if os.path.isfile(fp):
                    shutil.copy2(fp, os.path.join(prefix, "lib", f))

    def _materialize_aliases(self, folder):
        """HMDFS (HarmonyOS distributed fs) refuses to load libraries through
        symlinks (Permission denied) and does not support hard links. Replace
        every symlink with a real copy of its target."""
        for root, _, files in os.walk(folder):
            for name in files:
                p = os.path.join(root, name)
                if os.path.islink(p):
                    ref = os.readlink(p)
                    target = ref if os.path.isabs(ref) else os.path.join(root, ref)
                    if os.path.exists(target):
                        os.unlink(p)
                        shutil.copy2(target, p)

    def _make_common_flags(self, prefix):
        # The profile supplies the OHOS toolchain through
        # tools.build:compiler_executables (conan does not export it into the
        # build env), while make's builtin default would pick g++/cc
        compilers = self.conf.get("tools.build:compiler_executables") or {}
        cc = compilers.get("c", "clang")
        cxx = compilers.get("cpp", "clang++")
        configs = "shared" if self.options.shared else "static"
        return (
            f"make os=Linux CC={cc} CXX={cxx} lib-suffix= MCPP_HOME={prefix} "
            f"BZ2_HOME={prefix} "
            f"EXPAT_HOME={prefix} LMDB_HOME={prefix} CONFIGS={configs} "
            f"CPPFLAGS=\"-I{prefix}/include -Wno-deprecated-declarations "
            f"-Wno-deprecated-copy-with-user-provided-dtor\" "
            f"LDFLAGS=\"-L{prefix}/lib\" "
            f"icegridadmin_system_libs=\"-ledit -lncursesw\" "
            f"icestormadmin_system_libs=\"-ledit -lncursesw\""
        )

    def build(self):
        prefix = self._build_prefix()
        os.makedirs(os.path.join(prefix, "include"), exist_ok=True)
        os.makedirs(os.path.join(prefix, "lib"), exist_ok=True)

        # 1. Build the vendored mcpp preprocessor library first
        compilers = self.conf.get("tools.build:compiler_executables") or {}
        cc = compilers.get("c", "clang")
        mcpp_dir = os.path.join(self.source_folder, "_mcpp")
        self.run(f"make CC={cc} CFLAGS=-O2", cwd=mcpp_dir, env="conanbuild")
        shutil.copy2(os.path.join(mcpp_dir, "lib", "libmcpp.a"),
                     os.path.join(prefix, "lib", "libmcpp.a"))
        for h in ("mcpp_lib.h", "mcpp_out.h", "config.h"):
            src = os.path.join(mcpp_dir, h)
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(prefix, "include", h))

        # 2. Merge every conan dependency (direct + transitive, e.g. ncurses)
        #    into the merged prefix
        for _, dep in self.dependencies.items():
            self._merge_dep(dep, prefix)
        self._materialize_aliases(prefix)

        # 3. Build Ice C++ itself (verified command line; the two
        #    *_system_libs overrides are required so icegridadmin/icestormadmin
        #    link against libedit/ncursesw from the toolchain)
        make_cmd = f"{self._make_common_flags(prefix)} -j{build_jobs(self)} srcs"
        self.run(make_cmd, cwd=os.path.join(self.source_folder, "cpp"), env="conanbuild")

    def _sign_binaries(self):
        """OHOS requires device binaries to carry a valid signature. The SDK
        linker already embeds a .codesign section; if the platform signing
        tool is available and works, re-sign a clean build; otherwise leave
        the toolchain signature untouched (never ship an unsigned binary)."""
        sign_tool = shutil.which("binary-sign-tool")
        if not sign_tool:
            self.output.info("binary-sign-tool not found, keeping linker signatures")
            return
        objcopy = shutil.which("llvm-objcopy") or shutil.which("objcopy")
        targets = []
        for root, _, files in os.walk(self.package_folder):
            for f in files:
                p = os.path.join(root, f)
                if os.path.islink(p):
                    continue
                try:
                    with open(p, "rb") as fh:
                        if fh.read(4) == b"\x7fELF":
                            targets.append(p)
                except OSError:
                    pass
        if not targets:
            return
        # Probe on a disposable copy: strip + self-sign must both succeed
        # before we modify any real artifact.
        probe = os.path.join(self.build_folder, ".sign-probe")
        shutil.copy2(targets[0], probe)
        if objcopy:
            subprocess.run([objcopy, "--remove-section", ".codesign", probe],
                           capture_output=True)
        signed = subprocess.run([sign_tool, "selfSign", "-i", probe],
                                capture_output=True)
        if signed.returncode != 0:
            self.output.warning(f"binary-sign-tool selfSign failed, keeping "
                                f"toolchain signatures: {signed.stderr.decode(errors='replace')[:200]}")
            os.unlink(probe)
            return
        os.unlink(probe)
        for t in targets:
            if objcopy:
                subprocess.run([objcopy, "--remove-section", ".codesign", t],
                               capture_output=True)
            subprocess.run([sign_tool, "selfSign", "-i", t], capture_output=True)

    def package(self):
        prefix = self.package_folder
        cpp_dir = os.path.join(self.source_folder, "cpp")
        # Install with the exact same variable set used for the build so that
        # make re-derives identical library file names
        install_cmd = (
            f"{self._make_common_flags(self._build_prefix())} "
            f"-j{build_jobs(self)} install prefix={prefix}"
        )
        self.run(install_cmd, cwd=cpp_dir, env="conanbuild")

        # HMDFS: guarantee a symlink-free package layout (real files only)
        self._materialize_aliases(prefix)

        # drop upstream metadata files that do not belong into the package
        for junk in ("MANIFEST.txt", "CHANGES", "ICE_CONFIG_LICENSE"):
            p = os.path.join(prefix, junk)
            if os.path.isfile(p):
                os.unlink(p)

        self._sign_binaries()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "Ice")
        libs = [
            "Ice", "IceSSL", "IceDiscovery", "IceLocatorDiscovery",
            "IceBox", "Glacier2", "Glacier2CryptPermissionsVerifier",
            "IcePatch2", "IceStorm", "IceStormService", "IceGrid",
            "IceDB", "IceBridge", "IceXML",
        ]
        self.cpp_info.libs = libs
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = ["include"]
        # crypt() lives in musl libc (no -lcrypt needed); libedit/ncursesw are
        # consumed by the admin tools at build time, not required downstream;
        # openssl/bzip2 are statically linked into the Ice libraries.
