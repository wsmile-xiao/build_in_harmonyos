import os
import shutil
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class P5CompressRawBzip2Conan(ConanFile):
    name = "p5-compress-raw-bzip2"
    version = "2.217"
    description = "Perl XS bindings for bzip2 compression"
    license = "perl_5"
    homepage = "https://metacpan.org/dist/Compress-Raw-Bzip2"
    url = ""
    topics = ("perl", "cpan", "xs", "bzip2")

    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv", "VirtualRunEnv"

    def layout(self):
        basic_layout(self, src_folder=".")

    def requirements(self):
        self.requires("perl/5.42.2")
        self.requires("bzip2/1.0.8")

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

        bzip2 = self.dependencies.host["bzip2"]
        env.define("CONAN_PERL_PRIVLIB", str(privlib))
        env.define("CONAN_PERL_ARCHLIB", str(archlib))
        env.define("PERL_SRC", str(archlib / "CORE"))
        env.define("BUILD_BZIP2", "0")
        env.define("BZIP2_INCLUDE", bzip2.cpp_info.includedirs[0])
        env.define("BZIP2_LIB", bzip2.cpp_info.libdirs[0])
        env.vars(self).save_script("p5_raw_bzip2")

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
        self.run(command, cwd=self.source_folder, env=["conanbuild", "conanrun", "p5_raw_bzip2"])

    def build(self):
        cc = self._cc()
        if not cc:
            raise ConanException("No usable C compiler found for ExtUtils::MakeMaker")
        self._makefile_pl(f'CC="{cc}" LD="{cc}"')
        self.run("make -j1", cwd=self.source_folder, env=["conanbuild", "conanrun", "p5_raw_bzip2"])
        self._sign_elfs(os.path.join(self.source_folder, "blib"))
        self.run("make test TEST_VERBOSE=1", cwd=self.source_folder, env=["conanbuild", "conanrun", "p5_raw_bzip2"])

    def package(self):
        perl_lib = os.path.join(self.package_folder, "lib", "perl5")
        copy(self, "*", src=os.path.join(self.source_folder, "blib", "lib"), dst=perl_lib, keep_path=True)
        copy(self, "*", src=os.path.join(self.source_folder, "blib", "arch"), dst=perl_lib, keep_path=True)
        copy(self, "README", src=self.source_folder, dst=os.path.join(self.package_folder, "share", self.name))
        copy(self, "Changes", src=self.source_folder, dst=os.path.join(self.package_folder, "share", self.name))
        copy(self, "Makefile.PL", src=self.source_folder, dst=os.path.join(self.package_folder, "share", self.name))
        copy(self, "META.json", src=self.source_folder, dst=os.path.join(self.package_folder, "share", self.name))
        copy(self, "META.yml", src=self.source_folder, dst=os.path.join(self.package_folder, "share", self.name))
        copy(self, "*", src=os.path.join(self.source_folder, "t"), dst=os.path.join(self.package_folder, "share", self.name, "t"), keep_path=True)
        self._sign_elfs(perl_lib)

    def package_info(self):
        perl_lib = os.path.join(self.package_folder, "lib", "perl5")
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
        self.runenv_info.prepend_path("PERL5LIB", perl_lib)
        self.buildenv_info.prepend_path("PERL5LIB", perl_lib)
