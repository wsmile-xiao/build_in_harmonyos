from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get, patch, export_conandata_patches
import os


class JpegArchiveConan(ConanFile):
    name = "jpeg-archive"
    version = "2.2.0"
    package_type = "application"
    license = "MIT"
    homepage = "https://github.com/danielgtaylor/jpeg-archive"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    description = "Utilities for archiving and comparing JPEG images"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("jpeg-archive supports Linux/OHOS only")
        if self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("jpeg-archive is adapted for armv8 only")

    def requirements(self):
        self.requires("mozjpeg/4.1.1")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        for p in self.conan_data.get("patches", {}).get(self.version, []):
            patch(self, patch_file=p["patch_file"])

    def _mozjpeg_prefix(self):
        return self.dependencies["mozjpeg"].package_folder

    def _make_vars(self):
        # 上游 Makefile 用 `uname -s` 选平台，OHOS 落入 Windows/else 分支，
        # 误用 `-I../mozjpeg` 和 `../mozjpeg/libjpeg.a`。强制 UNAME_S=Linux
        # 走 Linux 分支，让 MOZJPEG_PREFIX 正确驱动 -I 和 LIBJPEG。
        return (
            f"CC=clang UNAME_S=Linux "
            f"MOZJPEG_PREFIX={self._mozjpeg_prefix()}"
        )

    def build(self):
        jobs = os.cpu_count() or 1
        self.run(f"make {self._make_vars()} -j{jobs}", env="conanbuild")

    def package(self):
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        prefix = self.package_folder
        self.run(
            f"make install PREFIX={prefix} {self._make_vars()}",
            env="conanbuild",
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
