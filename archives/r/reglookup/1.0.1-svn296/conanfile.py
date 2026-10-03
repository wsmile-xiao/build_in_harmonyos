"""Build reglookup's SConstruct source set without an unavailable SCons tool."""

import os
import re
import shlex
import shutil
import stat
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class ReglookupConan(ConanFile):
    name = "reglookup"
    version = "1.0.1-svn296"
    package_type = "library"
    description = "Read-only Windows registry hive forensics tools and libregfi"
    license = "GPL-3.0-only"
    homepage = "https://code.google.com/archive/p/reglookup/"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("reglookup supports Linux and OHOS")
        if not self.options.shared:
            raise ConanInvalidConfiguration("reglookup publishes its shared libregfi ABI")

    def requirements(self):
        self.requires("talloc/2.4.4", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        source = dict(self.conan_data["sources"][self.version])
        local_archive = os.environ.get("REGLOOKUP_SOURCE_ARCHIVE")
        if local_archive:
            archive = Path(local_archive).resolve(strict=True)
            if not archive.is_file():
                raise ConanInvalidConfiguration("REGLOOKUP_SOURCE_ARCHIVE is not a file")
            source["url"] = archive.as_uri()
            source["filename"] = archive.name
        get(self, **source, strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()

    @staticmethod
    def _sign_elf(path):
        path = Path(path)
        signer = shutil.which("binary-sign-tool")
        readelf = shutil.which("llvm-readelf")
        objcopy = shutil.which("llvm-objcopy")
        if not path.is_file() or not all((signer, readelf, objcopy)):
            raise ConanInvalidConfiguration("missing ELF or OHOS signing tools")
        pending = path.with_name(path.name + ".reglookup-signing")
        signed = path.with_name(path.name + ".reglookup-signed")
        if pending.exists() or signed.exists():
            raise ConanInvalidConfiguration("stale reglookup signing sibling")
        try:
            shutil.copy2(path, pending)
            before = subprocess.run(
                [readelf, "-S", str(pending)], capture_output=True, text=True,
                check=True, timeout=10,
            ).stdout
            if re.search(r"\s\.codesign\s", before):
                subprocess.run(
                    [objcopy, "--remove-section", ".codesign", str(pending)],
                    check=True, timeout=10,
                )
            subprocess.run(
                [signer, "sign", "-inFile", str(pending), "-outFile", str(signed), "-selfSign", "1"],
                check=True, capture_output=True, timeout=40,
            )
            after = subprocess.run(
                [readelf, "-S", str(signed)], capture_output=True, text=True,
                check=True, timeout=10,
            ).stdout
            if len(re.findall(r"\s\.codesign\s", after)) != 1:
                raise ConanInvalidConfiguration("signed ELF lacks one .codesign section")
            signed.chmod(stat.S_IMODE(path.stat().st_mode) | stat.S_IXUSR)
            os.replace(signed, path)
        finally:
            for temporary in (pending, signed):
                if temporary.exists():
                    temporary.unlink()

    def _run(self, argv):
        self.run(shlex.join(str(arg) for arg in argv), env="conanbuild")

    def build(self):
        compiler_exes = self.conf.get("tools.build:compiler_executables", default={})
        cc = compiler_exes.get("c", "clang")
        ar = shutil.which("llvm-ar") or shutil.which("ar")
        if not ar:
            raise ConanInvalidConfiguration("llvm-ar or ar is required")
        talloc = self.dependencies["talloc"].cpp_info
        if not talloc.includedirs or not talloc.libdirs:
            raise ConanInvalidConfiguration("talloc must expose include and lib directories")
        inc = ["-I" + os.path.join(self.source_folder, "include")]
        inc += ["-I" + directory for directory in talloc.includedirs]
        lib_paths = ["-L" + directory for directory in talloc.libdirs]
        flags = ["-std=gnu99", "-D_FILE_OFFSET_BITS=64", '-DREGFI_VERSION="1.0.1.283"',
                 "-fPIC", "-O2", "-fvisibility=hidden"]
        output = Path(self.build_folder, "reglookup-stage")
        objects = output / "obj"
        objects.mkdir(parents=True, exist_ok=False)
        names = ("regfi", "winsec", "range_list", "lru_cache", "void_stack")
        built = []
        for name in names:
            source = Path(self.source_folder, "lib", name + ".c")
            target = objects / (name + ".o")
            self._run([cc, *flags, *inc, "-c", source, "-o", target])
            built.append(target)
        library = output / "libregfi.so.1.0.1"
        self._run([cc, "-shared", "-Wl,-soname,libregfi.so.1", "-o", library,
                   *built, *lib_paths, "-ltalloc", "-lm", "-lpthread"])
        self._run([ar, "rcs", output / "libregfi.a", *built])
        if str(self.settings.os) == "OHOS":
            self._sign_elf(library)
        for alias in ("libregfi.so.1", "libregfi.so"):
            shutil.copy2(library, output / alias)
        for name in ("reglookup", "reglookup-recover"):
            executable = output / name
            self._run([cc, *flags, *inc, Path(self.source_folder, "src", name + ".c"),
                       "-o", executable, "-L" + str(output), *lib_paths,
                       "-lregfi", "-ltalloc", "-lm", "-lpthread",
                       "-Wl,-rpath,$ORIGIN/../lib"])
            if str(self.settings.os) == "OHOS":
                self._sign_elf(executable)
        self.output.info("UPSTREAM_BUILD_PASS: libregfi and two upstream CLIs")

    def package(self):
        output = os.path.join(self.build_folder, "reglookup-stage")
        copy(self, "reglookup*", src=output, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "libregfi.*", src=output, dst=os.path.join(self.package_folder, "lib"))
        copy(self, "*.h", src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include", "regfi"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["regfi"]
        self.cpp_info.system_libs = ["m", "pthread"]
        self.cpp_info.includedirs = ["include/regfi"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
