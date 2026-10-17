#!/usr/bin/env python3
from conan import ConanFile
from conan.tools.files import get, copy, save, load
import os
import tarfile
import stat

class PkgdiffConan(ConanFile):
    name = "pkgdiff"
    version = "1.8"
    description = "Package Changes Analyzer for Linux software packages"
    license = "GPL-2.0-only"
    homepage = "https://github.com/lvc/pkgdiff"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def source(self):
        local = os.environ.get("OHC_TARBALL")
        if local and os.path.isfile(local):
            with tarfile.open(local, "r:gz") as tf:
                tf.extractall(self.source_folder)
            entries = [e for e in os.listdir(self.source_folder) if e not in (".", "..")]
            if len(entries) == 1:
                inner = os.path.join(self.source_folder, entries[0])
                if os.path.isdir(inner):
                    for n in os.listdir(inner):
                        os.rename(os.path.join(inner, n), os.path.join(self.source_folder, n))
        else:
            get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        pass

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        moddir = os.path.join(self.package_folder, "share", "pkgdiff", "modules")
        os.makedirs(bindir, exist_ok=True)
        os.makedirs(moddir, exist_ok=True)
        src = load(self, os.path.join(self.source_folder, "pkgdiff.pl"))
        src = src.replace("#!/usr/bin/perl", "#!/usr/bin/env perl")
        src = src.replace("MODULES_INSTALL_PATH", "../share/pkgdiff")
        dst = os.path.join(bindir, "pkgdiff")
        save(self, dst, src)
        os.chmod(dst, os.stat(dst).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
        copy(self, "*", src=os.path.join(self.source_folder, "modules"), dst=moddir)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
