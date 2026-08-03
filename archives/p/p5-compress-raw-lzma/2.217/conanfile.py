import os
import shutil
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment
from conan.tools.files import copy, get, replace_in_file
from conan.tools.layout import basic_layout


class P5CompressRawLzmaConan(ConanFile):
    name = "p5-compress-raw-lzma"
    version = "2.217"
    description = "Perl XS bindings for liblzma compression"
    license = "perl_5"
    homepage = "https://metacpan.org/dist/Compress-Raw-Lzma"
    url = ""
    topics = ("perl", "cpan", "xs", "lzma", "xz")

    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv", "VirtualRunEnv"

    def layout(self):
        basic_layout(self, src_folder=".")

    def requirements(self):
        self.requires("perl/5.42.2")
        self.requires("xz/5.6.2")

    def build_requirements(self):
        self.tool_requires("perl/5.42.2")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        env = Environment()
        perl = Path(self.dependencies.host["perl"].package_folder)
        privlibs = sorted((perl / "lib" / "perl5").glob("5.*"))
        if not privlibs:
            raise ConanException("Cannot locate Perl privlib in perl/5.42.2 package")
        privlib = privlibs[-1]
        cores = sorted(privlib.glob("*/CORE"))
        if not cores:
            raise ConanException("Cannot locate Perl CORE headers in perl/5.42.2 package")
        archlib = cores[-1].parent

        xz = self.dependencies.host["xz"]
        env.define("CONAN_PERL_PRIVLIB", str(privlib))
        env.define("CONAN_PERL_ARCHLIB", str(archlib))
        env.define("PERL_SRC", str(archlib / "CORE"))
        env.define("XZ_INCLUDE", xz.cpp_info.includedirs[0])
        env.define("XZ_LIB", xz.cpp_info.libdirs[0])
        env.vars(self).save_script("p5_raw_lzma")

    def _find_exe(self, names, candidates):
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        for name in names:
            found = shutil.which(name)
            if found:
                return found
        return None

    def _cc(self):
        conf = self.conf.get("tools.build:compiler_executables", default={})
        configured = conf.get("c") if isinstance(conf, dict) else None
        return self._find_exe(
            ("clang", "cc"),
            (
                configured,
                "/storage/Users/currentUser/usr/local/bin/clang",
                "/data/service/hnp/bin/clang",
            ),
        )

    def _sign_elfs(self, root):
        if str(self.settings.os) != "OHOS":
            return
        signer = self._find_exe(
            ("binary-sign-tool",),
            (
                "/storage/Users/currentUser/usr/local/bin/binary-sign-tool",
                "/data/service/hnp/bin/binary-sign-tool",
            ),
        )
        objcopy = self._find_exe(
            ("llvm-objcopy",),
            (
                "/storage/Users/currentUser/usr/local/bin/llvm-objcopy",
                "/data/service/hnp/bin/llvm-objcopy",
            ),
        )
        if not signer or not objcopy:
            raise ConanException("OHOS ELF signing tools are required for Perl XS modules")
        for path in Path(root).rglob("*.so"):
            signed = str(path) + ".signed"
            self.run(f'"{objcopy}" --remove-section .codesign "{path}" 2>/dev/null || true')
            self.run(f'"{signer}" sign -inFile "{path}" -outFile "{signed}" -selfSign 1')
            os.replace(signed, path)

    def _makefile_pl(self, args=""):
        perl_args = (
            'PERL_LIB="$CONAN_PERL_PRIVLIB" '
            'PERL_ARCHLIB="$CONAN_PERL_ARCHLIB" '
            'PERL_INC="$PERL_SRC"'
        )
        command = f"perl Makefile.PL {perl_args} {args}".strip()
        self.run(command, cwd=self.source_folder, env=["conanbuild", "conanrun", "p5_raw_lzma"])

    def build(self):
        cc = self._cc()
        if not cc:
            raise ConanException("No usable C compiler found for ExtUtils::MakeMaker")
        xz = self.dependencies.host["xz"]
        config_in = os.path.join(self.source_folder, "config.in")
        replace_in_file(self, config_in, "INCLUDE         = /usr/local/include", f"INCLUDE         = {xz.cpp_info.includedirs[0]}")
        replace_in_file(self, config_in, "LIB             = /usr/local/lib", f"LIB             = {xz.cpp_info.libdirs[0]}")
        self._makefile_pl(f'CC="{cc}" LD="{cc}"')
        self.run("make -j1", cwd=self.source_folder, env=["conanbuild", "conanrun", "p5_raw_lzma"])
        self._sign_elfs(os.path.join(self.source_folder, "blib"))
        self.run("make test TEST_VERBOSE=1", cwd=self.source_folder, env=["conanbuild", "conanrun", "p5_raw_lzma"])

    def package(self):
        perl_lib = os.path.join(self.package_folder, "lib", "perl5")
        copy(self, "*", src=os.path.join(self.source_folder, "blib", "lib"), dst=perl_lib, keep_path=True)
        copy(self, "*", src=os.path.join(self.source_folder, "blib", "arch"), dst=perl_lib, keep_path=True)
        copy(self, "README", src=self.source_folder, dst=os.path.join(self.package_folder, "share", self.name))
        copy(self, "Changes", src=self.source_folder, dst=os.path.join(self.package_folder, "share", self.name))
        copy(self, "Makefile.PL", src=self.source_folder, dst=os.path.join(self.package_folder, "share", self.name))
        copy(self, "META.json", src=self.source_folder, dst=os.path.join(self.package_folder, "share", self.name))
        copy(self, "META.yml", src=self.source_folder, dst=os.path.join(self.package_folder, "share", self.name))
        copy(self, "config.in", src=self.source_folder, dst=os.path.join(self.package_folder, "share", self.name))
        copy(self, "*", src=os.path.join(self.source_folder, "t"), dst=os.path.join(self.package_folder, "share", self.name, "t"), keep_path=True)
        self._sign_elfs(perl_lib)

    def package_info(self):
        perl_lib = os.path.join(self.package_folder, "lib", "perl5")
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
        self.runenv_info.prepend_path("PERL5LIB", perl_lib)
        self.buildenv_info.prepend_path("PERL5LIB", perl_lib)
