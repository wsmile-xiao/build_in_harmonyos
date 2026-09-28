import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class LibpurpleConan(ConanFile):
    name = "libpurple"
    version = "2.14.14"
    description = "Core library for the Pidgin instant messaging client"
    license = "GPL-2.0-or-later"
    homepage = "https://pidgin.im/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("glib/2.84.0")
        self.requires("libxml2/2.15.3")
        # Pidgin's libpurple tests use Check and otherwise silently disappear.
        self.requires("check/0.15.2", visible=False)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if self.settings.os == "OHOS":
            # This bundled config.guess predates HarmonyOS and cannot identify
            # it as a native build host.
            tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.configure_args.extend([
            "--disable-gtkui",
            "--disable-consoleui",
            "--disable-plugins",
            "--with-dynamic-prpls=",
            "--disable-vv",
            "--disable-gstreamer",
            "--disable-meanwhile",
            "--disable-avahi",
            "--disable-nss",
            "--disable-gnutls",
            "--disable-dbus",
            "--disable-idn",
            "--disable-cyrus-sasl",
            "--disable-tcl",
            "--disable-tk",
            "--disable-perl",
            "--disable-mono",
            "--without-krb4",
            "--disable-nls",
        ])
        if not self.options.shared:
            tc.configure_args.extend(["--enable-static", "--disable-shared"])
        tc.generate()
        PkgConfigDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        # Conan's aggregate pcre2.pc lists both PCRE2 libraries. The
        # pcre2-posix libtool archive embeds an unusable //lib reference on
        # this profile; libpurple only needs the core pcre2-8 library.
        pcre2_pc = os.path.join(self.build_folder, "conan", "pcre2.pc")
        if os.path.isfile(pcre2_pc):
            with open(pcre2_pc, encoding="utf-8") as pc:
                contents = pc.read()
            with open(pcre2_pc, "w", encoding="utf-8") as pc:
                pc.write(contents.replace(" -lpcre2-posix", ""))

        pkg_config_dirs = [
            os.path.join(dep.package_folder, "lib", "pkgconfig")
            for dep in self.dependencies.host.values()
            if dep.package_folder
        ]
        pkg_config_dirs.append(os.path.join(self.build_folder, "conan"))
        existing = os.environ.get("PKG_CONFIG_PATH")
        if existing:
            pkg_config_dirs.append(existing)
        os.environ["PKG_CONFIG_PATH"] = os.pathsep.join(pkg_config_dirs)

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        runtime_lib_dirs = [
            os.path.join(dep.package_folder, "lib")
            for dep in self.dependencies.host.values()
            if dep.package_folder
        ]
        old_library_path = os.environ.get("LD_LIBRARY_PATH")
        old_temp = os.environ.get("TEMP")
        os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(
            runtime_lib_dirs + ([old_library_path] if old_library_path else [])
        )
        # Check prefers TEMP over TMPDIR/P_tmpdir; keep its IPC files inside
        # the writable Conan build directory on HarmonyOS.
        os.environ["TEMP"] = self.build_folder
        try:
            autotools.make(target="check", args=["-j1"])
        finally:
            if old_library_path is None:
                os.environ.pop("LD_LIBRARY_PATH", None)
            else:
                os.environ["LD_LIBRARY_PATH"] = old_library_path
            if old_temp is None:
                os.environ.pop("TEMP", None)
            else:
                os.environ["TEMP"] = old_temp

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["purple"]
        self.cpp_info.includedirs = ["include/libpurple"]
        self.cpp_info.set_property("cmake_file_name", "libpurple")
        self.cpp_info.set_property("cmake_target_name", "libpurple::libpurple")
