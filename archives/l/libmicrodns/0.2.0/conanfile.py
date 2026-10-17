"""Conan recipe — libmicrodns 0.2.0 (Meson build).

libmicrodns is a minimal mDNS/DNS-SD resolver library from VideoLAN
(used by VLC for network service discovery). Pure C99, no external
dependencies on POSIX targets; on Windows it links the ws2_32 and
iphlpapi system libraries.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class LibmicrodnsConan(ConanFile):
    name = "libmicrodns"
    version = "0.2.0"
    description = "Minimal mDNS/DNS-SD resolver library from VideoLAN (used by VLC for service discovery)"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/videolabs/libmicrodns"
    url = "https://github.com/videolabs/libmicrodns"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        # Upstream supports Linux/macOS/Windows/Android; OHOS is the
        # adaptation target and shares the POSIX code path with Linux.
        if self.settings.os not in ("Linux", "OHOS", "Windows", "Macos", "FreeBSD", "Android"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        toolchain = MesonToolchain(self)
        toolchain.project_options["default_library"] = "shared" if self.options.shared else "static"
        # Keep the upstream unittest in the build (it runs in build() when
        # the target binaries can execute); examples are not packaged.
        toolchain.project_options["tests"] = "enabled"
        toolchain.project_options["examples"] = "disabled"
        if self.settings.os == "OHOS":
            # The generic `lld` driver depends on libxml2.so.16, which is
            # not on the dynamic linker search path on HarmonyOS workers;
            # `ld.lld` is self-contained (same workaround as cairomm 1.16.2).
            ld_lld = "/data/service/hnp/bin/ld.lld"
            if os.path.isfile(ld_lld):
                toolchain.c_link_args.append(f"-fuse-ld={ld_lld}")
                toolchain.cpp_link_args.append(f"-fuse-ld={ld_lld}")
        toolchain.generate()
        if self.settings.os == "OHOS":
            self._inject_meson_tools()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()
        # The upstream unittest must run wherever the target binaries can
        # execute (HarmonyOS PC CI workers are native aarch64 OHOS hosts).
        if not cross_building(self) and not self.conf.get("tools.build:skip_test", default=False):
            meson.test()

    def package(self):
        Meson(self).install()
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # meson library('microdns', ...) -> libmicrodns.a / libmicrodns.so
        self.cpp_info.libs = ["microdns"]
        self.cpp_info.set_property("pkg_config_name", "microdns")
        if self.settings.os == "Windows":
            # Same system libraries the meson build links on Windows.
            self.cpp_info.system_libs = ["ws2_32", "iphlpapi"]

    def _inject_meson_tools(self):
        """Inject ar/ranlib/ld into the Meson machine files (OHOS).

        On HarmonyOS the LLVM bin dir is not on PATH by default, so Meson
        cannot locate llvm-ar / llvm-ranlib for static archives (same
        workaround as cairomm 1.16.2).
        """
        for filename in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            machine_file = os.path.join(self.generators_folder, filename)
            if not os.path.isfile(machine_file):
                continue
            compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
            cc = compilers.get("c") or ""
            bindir = os.path.dirname(cc) if cc and os.path.sep in cc else ""
            ar = ranlib = ld = None
            for directory in (bindir, "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin"):
                candidate = os.path.join(directory, "llvm-ar")
                if not ar and os.path.isfile(candidate):
                    ar = candidate
                candidate = os.path.join(directory, "llvm-ranlib")
                if not ranlib and os.path.isfile(candidate):
                    ranlib = candidate
                candidate = os.path.join(directory, "ld.lld")
                if not ld and os.path.isfile(candidate):
                    ld = candidate
            with open(machine_file, encoding="utf-8") as handle:
                content = handle.read()
            if "[binaries]" not in content:
                continue
            insert = []
            if ar and "\nar =" not in content:
                insert.append(f"ar = '{ar}'")
            if ranlib and "\nranlib =" not in content:
                insert.append(f"ranlib = '{ranlib}'")
            if ld and "\nld =" not in content:
                insert.append(f"ld = '{ld}'")
            if insert:
                content = content.replace("[binaries]\n", "[binaries]\n" + "\n".join(insert) + "\n", 1)
                with open(machine_file, "w", encoding="utf-8") as handle:
                    handle.write(content)
