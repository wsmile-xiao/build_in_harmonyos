"""libspnav 1.2, with its AF_UNIX backend for HarmonyOS PC."""

import os
import shlex
import shutil
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import copy, get, save
from conan.tools.layout import basic_layout


class LibspnavConan(ConanFile):
    name = "libspnav"
    version = "1.2"
    package_type = "library"
    description = "AF_UNIX client library for 6-DoF input devices"
    homepage = "https://github.com/FreeSpacenav/libspnav"
    license = "BSD-3-Clause"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def layout(self):
        # configure writes Makefile and src/spnav_config.h beside the sources.
        basic_layout(self, build_folder=".")

    def source(self):
        source = dict(self.conan_data["sources"][self.version])
        local_archive = os.environ.get("LIBSPNAV_SOURCE_ARCHIVE")
        if local_archive:
            archive = Path(local_archive).resolve(strict=True)
            if not archive.is_file():
                raise ConanInvalidConfiguration("local source archive is not a file")
            source["url"] = archive.as_uri()
            source["filename"] = archive.name
        get(self, **source, strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()

    @staticmethod
    def _sign_elf(path):
        signer = shutil.which("binary-sign-tool")
        readelf = shutil.which("llvm-readelf") or shutil.which("readelf")
        if not signer or not readelf:
            raise ConanInvalidConfiguration("OHOS ELF signer/readelf missing")
        original = Path(path)
        pending = original.with_name(original.name + ".spnav-signing")
        signed = original.with_name(original.name + ".spnav-signed")
        if pending.exists() or signed.exists():
            raise ConanInvalidConfiguration("stale signing sibling")
        try:
            shutil.copy2(original, pending)
            subprocess.run([signer, "sign", "-inFile", str(pending),
                            "-outFile", str(signed), "-selfSign", "1"],
                           check=True, capture_output=True, text=True, timeout=40)
            sections = subprocess.run([readelf, "-S", str(signed)], check=True,
                                      capture_output=True, text=True, timeout=20)
            if ".codesign" not in sections.stdout:
                raise ConanException("signed shared library has no .codesign")
            os.chmod(signed, original.stat().st_mode)
            os.replace(signed, original)
        finally:
            for temporary in (pending, signed):
                if temporary.exists():
                    temporary.unlink()

    def build(self):
        executables = self.conf.get("tools.build:compiler_executables", default={})
        cc = executables.get("c", "clang")
        ar = executables.get("ar", "llvm-ar")
        shell = os.environ.get("CONFIG_SHELL", "/bin/sh")
        # The proprietary-driver bridge needs X11, unavailable on OHOS PC.
        # The native spacenavd AF_UNIX protocol remains enabled.
        self.run("{} ./configure --prefix=/ --disable-x11 --disable-debug".format(
            shlex.quote(shell)))
        self.run("make -j1 CC={} AR={}".format(shlex.quote(cc), shlex.quote(ar)))
        # This release has no registered test target. Validate the installed
        # AF_UNIX API through test_package instead of inventing upstream N.
        self.output.info("UPSTREAM_0_OF_0_NO_REGISTERED_SUITE")

    def package(self):
        include = os.path.join(self.package_folder, "include")
        lib = os.path.join(self.package_folder, "lib")
        for header in ("spnav.h", "spnav_magellan.h", "spnav_config.h"):
            copy(self, header, os.path.join(self.build_folder, "src"), include)
        if self.options.shared:
            copy(self, "libspnav.so.0.4", self.build_folder, lib)
            if str(self.settings.os) == "OHOS":
                self._sign_elf(os.path.join(lib, "libspnav.so.0.4"))
            os.symlink("libspnav.so.0.4", os.path.join(lib, "libspnav.so.0"))
            os.symlink("libspnav.so.0", os.path.join(lib, "libspnav.so"))
        else:
            copy(self, "libspnav.a", self.build_folder, lib)
        copy(self, "LICENSE", self.source_folder,
             os.path.join(self.package_folder, "licenses"))
        save(self, os.path.join(lib, "pkgconfig", "spnav.pc"),
             "prefix=${pcfiledir}/../..\n"
             "libdir=${prefix}/lib\n"
             "includedir=${prefix}/include\n"
             "Name: libspnav\n"
             "Description: 6-DoF device client library\n"
             "Version: 1.2\n"
             "Libs: -L${libdir} -lspnav -lm\n"
             "Cflags: -I${includedir}\n")

    def package_info(self):
        self.cpp_info.libs = ["spnav"]
        self.cpp_info.system_libs = ["m"]
        self.cpp_info.set_property("pkg_config_name", "spnav")
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib"))
