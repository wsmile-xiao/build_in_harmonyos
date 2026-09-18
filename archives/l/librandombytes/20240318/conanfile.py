import os, shutil
from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.files import copy, get

class LibrandombytesConan(ConanFile):
    name = "librandombytes"
    version = "20240318"
    description = "DJBs librandombytes"
    homepage = "https://randombytes.cr.yp.to"
    license = "Unlicense"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}
    _CC_FLAGS = "-Wall -fPIC -fwrapv -Qunused-arguments -O -fvisibility=hidden"

    def source(self):
        local = os.environ.get("OHC_TARBALL")
        if local and os.path.isfile(local):
            import tarfile
            with tarfile.open(local, "r:gz") as tf:
                tf.extractall(self.source_folder)
            entries = [e for e in os.listdir(self.source_folder) if e not in (".", "..")]
            if len(entries) == 1 and os.path.isdir(os.path.join(self.source_folder, entries[0])):
                inner = os.path.join(self.source_folder, entries[0])
                for n in os.listdir(inner):
                    os.rename(os.path.join(inner, n), os.path.join(self.source_folder, n))
                shutil.rmtree(inner)
        else:
            get(self, strip_root=True, **self.conan_data["sources"][self.version][0])

    def _cc(self):
        conf = self.conf.get("tools.build:compiler_executables")
        cc = conf.get("c") if conf else None
        if not cc:
            raise ConanException("tools.build:compiler_executables.c missing")
        resolved = shutil.which(cc)
        if not resolved:
            raise ConanException("compiler not found: %s" % cc)
        return resolved

    def _prepend_compiler(self):
        cc = self._cc()
        line = "%s %s" % (cc, self._CC_FLAGS)
        path = os.path.join(self.source_folder, "compilers", "default")
        with open(path, encoding="utf-8") as f:
            content = f.read()
        if not content.startswith(line + "\n"):
            with open(path, "w", encoding="utf-8") as f:
                f.write(line + "\n" + content)

    def build(self):
        self._prepend_compiler()
        self.run("./configure --prefix=%s" % self.package_folder, cwd=self.source_folder)
        mf = os.path.join(self.source_folder, "build", "arm64", "Makefile")
        if os.path.isfile(mf):
            lines = open(mf, encoding="utf-8", errors="replace").read().splitlines(True)
            open(mf, "w", encoding="utf-8").writelines([ln for ln in lines if "openssl" not in ln])
        self.run("make", cwd=self.source_folder)
        if can_run(self):
            pkg = os.path.join(self.source_folder, "build", "arm64", "package")
            info = os.path.join(pkg, "bin", "randombytes-info")
            lib = os.path.join(pkg, "lib")
            old = os.environ.get("LD_LIBRARY_PATH", "")
            os.environ["LD_LIBRARY_PATH"] = lib + (os.pathsep + old if old else "")
            self.run(info)

    def package(self):
        pkg = os.path.join(self.source_folder, "build", "arm64", "package")
        copy(self, "randombytes.h", os.path.join(pkg, "include"), os.path.join(self.package_folder, "include"))
        lib_dst = os.path.join(self.package_folder, "lib")
        if self.options.shared:
            copy(self, "librandombytes.so*", os.path.join(pkg, "lib"), lib_dst)
            copy(self, "librandombytes-kernel.so*", os.path.join(pkg, "lib"), lib_dst)
        else:
            copy(self, "librandombytes.a", os.path.join(pkg, "lib"), lib_dst)
            copy(self, "librandombytes-kernel.a", os.path.join(pkg, "lib"), lib_dst)

    def package_info(self):
        self.cpp_info.libs = ["randombytes"]
