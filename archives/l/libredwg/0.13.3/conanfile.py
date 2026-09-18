import os
from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import Environment
from conan.tools.files import copy, get, replace_in_file, rmdir
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

class LibredwgConan(ConanFile):
    name = "libredwg"
    version = "0.13.3"
    description = "GNU LibreDWG DWG file format library"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/libredwg/"
    url = "https://ftp.gnu.org/gnu/libredwg/"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self)

    def source(self):
        local = os.environ.get("OHC_TARBALL")
        if local and os.path.isfile(local):
            import tarfile, shutil
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

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args = [
            a for a in tc.configure_args
            if not a.startswith("--host=") and not a.startswith("--build=")
        ]
        tc.configure_args.extend([
            "--build=aarch64-unknown-linux-gnu",
            "--host=aarch64-unknown-linux-gnu",
            "--disable-python",
            "--disable-bindings",
            "--disable-werror",
            "--disable-Werror",
            "--enable-debug",
        ])
        if self.options.shared:
            tc.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            tc.configure_args.extend(["--enable-static", "--disable-shared"])
        if self.options.get_safe("fPIC"):
            tc.extra_cflags.append("-fPIC")
        tc.generate()
        env = Environment()
        env.define("MAKEINFO", "true")
        env.vars(self).save_script("libredwg_makeinfo")

    def build(self):
        replace_in_file(
            self,
            os.path.join(self.source_folder, "configure"),
            "umask 077",
            "umask 022",
        )
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-C", "src", "-j4"])
        if can_run(self):
            for root in (self.source_folder, self.build_folder):
                ut = os.path.join(root, "test", "unit-testing", "assocarraymodifyactionbody.c")
                if os.path.isfile(ut):
                    txt = open(ut, encoding="utf-8", errors="replace").read()
                    txt2 = txt.replace("itemloc1", "itemloc[0]").replace("itemloc2", "itemloc[1]").replace("itemloc3", "itemloc[2]")
                    if txt2 != txt:
                        open(ut, "w", encoding="utf-8").write(txt2)
            autotools.make(args=["-C", "test/unit-testing", "-j4"])
            autotools.make(target="check", args=["-C", "test/unit-testing"])

    def package(self):
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(
            self,
            "dwg.h",
            os.path.join(self.source_folder, "include"),
            os.path.join(self.package_folder, "include"),
        )
        copy(
            self,
            "dwg_api.h",
            os.path.join(self.source_folder, "include"),
            os.path.join(self.package_folder, "include"),
        )
        lib_src = os.path.join(self.build_folder, "src", ".libs")
        lib_dst = os.path.join(self.package_folder, "lib")
        if self.options.shared:
            copy(self, "libredwg.so*", lib_src, lib_dst)
        else:
            copy(self, "libredwg.a", lib_src, lib_dst)
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        self.cpp_info.libs = ["redwg"]
        self.cpp_info.system_libs = ["m"]
