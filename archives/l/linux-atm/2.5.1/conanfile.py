from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LinuxAtmConan(ConanFile):
    name = "linux-atm"
    version = "2.5.1"
    description = ("ATM on Linux user-space tools (atmsigd, atmarpd, ilmid, zeppelin, "
                   "lecs, mpcd, br2684ctl, atmdump, saaldump, atmaddr, ...) and the "
                   "libatm / libsaal libraries")
    license = "GPL-2.0-or-later"
    homepage = "https://linux-atm.sourceforge.net/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if self.options.shared:
            tc.configure_args.append("--enable-shared")
            tc.configure_args.append("--disable-static")
        else:
            tc.configure_args.append("--disable-shared")
            tc.configure_args.append("--enable-static")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        # qgen is a build-time tool and is not parallel-safe: its flex output
        # ql_l.c includes the bison-generated ql_y.h without a make dependency,
        # so -jN races intermittently.  linux-atm is small; build serially.
        autotools.make(args=["-j1"])
        # L1 upstream tests: src/q2931 declares check_PROGRAMS = q.test (the
        # message-table collision check).  `make check` builds the generated
        # q.test.c and runs it; patches 0021-0023 fix the upstream build wiring
        # and the generator's check arrays so the case is really executed.
        autotools.make(target="check", args=["-j1"])

    def package(self):
        Autotools(self).install()

    def package_info(self):
        self.cpp_info.libs = ["atm"]
        self.cpp_info.bindirs = ["bin", "sbin"]