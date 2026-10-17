"""libpinyin 2.10.3 for HarmonyOS PC (CMake with Berkeley DB backend)."""

import hashlib
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    download,
    export_conandata_patches,
    get,
    unzip,
)


MODEL_NAME = "model20.text.tar.gz"
MODEL_SHA256 = "59c68e89d43ff85f5a309489499cbcde282d2b04bd91888734884b7defcb1155"
MODEL_URL = "https://downloads.sourceforge.net/project/libpinyin/models/model20.text.tar.gz"


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class LibpinyinConan(ConanFile):
    name = "libpinyin"
    version = "2.10.3"
    description = "Chinese pinyin input method engine"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/libpinyin/libpinyin"
    url = "https://github.com/libpinyin/libpinyin"
    topics = ("pinyin", "input-method", "i18n", "chinese")
    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("glib/2.88.3")
        self.requires("berkeley-db/4.8.30")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def layout(self):
        cmake_layout(self)

    def source(self):
        archive = os.environ.get("LIBPINYIN_SOURCE_ARCHIVE")
        if archive:
            if not os.path.isfile(archive) or _sha256(archive) != self.conan_data["sources"]["sha256"]:
                raise ConanException("LIBPINYIN_SOURCE_ARCHIVE has the wrong SHA-256")
            unzip(self, archive, strip_root=True)
        else:
            get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = True
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"

        # The upstream FindGLIB2 module uses old-style variables, whereas the
        # Conan dependency is exposed as a CMake config target.
        glib = self.dependencies["glib"].cpp_info
        glib_includes = list(glib.includedirs)
        for component in glib.components.values():
            glib_includes.extend(component.includedirs)
        tc.variables["GLIB2_INCLUDE_DIR"] = ";".join(dict.fromkeys(glib_includes))
        tc.variables["GLIB2_LIBRARIES"] = "glib2::glib2"

        # The Berkeley DB finder needs the actual archive path because the
        # upstream link rule appends DB_LIBRARIES as a raw linker argument.
        bdb = self.dependencies["berkeley-db"].cpp_info
        bdb_includes = list(bdb.includedirs)
        for component in bdb.components.values():
            bdb_includes.extend(component.includedirs)
        tc.variables["DB_INCLUDE_DIR"] = ";".join(dict.fromkeys(bdb_includes))
        tc.variables["DB_LIBRARY"] = os.path.join(
            bdb.libdirs[0], "lib" + (bdb.libs or ["db"])[0] + ".a"
        )
        tc.generate()

    def _ensure_model(self):
        data_dir = os.path.join(self.build_folder, "data")
        os.makedirs(data_dir, exist_ok=True)
        target = os.path.join(data_dir, MODEL_NAME)
        if os.path.isfile(target) and _sha256(target) == MODEL_SHA256:
            return

        # An explicitly supplied archive supports offline device builds. It
        # must have the same bytes as the public SourceForge release.
        supplied = os.environ.get("LIBPINYIN_MODEL20_ARCHIVE")
        if supplied:
            if not os.path.isfile(supplied) or _sha256(supplied) != MODEL_SHA256:
                raise ConanException("LIBPINYIN_MODEL20_ARCHIVE has the wrong SHA-256")
            shutil.copyfile(supplied, target)
        else:
            if os.path.exists(target):
                os.remove(target)
            download(self, MODEL_URL, target, sha256=MODEL_SHA256)
        if _sha256(target) != MODEL_SHA256:
            raise ConanException("model20 archive failed SHA-256 verification")

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})

        # Upstream generators are launched from data/ but record a relative
        # DT_NEEDED path to the just-built libpinyin.so from another depth.
        build_root = os.path.dirname(self.build_folder)
        src_link = os.path.join(build_root, "src")
        if not os.path.lexists(src_link):
            os.symlink(os.path.join(self.build_folder, "src"), src_link)

        glib = self.dependencies["glib"].cpp_info
        libdirs = list(glib.libdirs)
        for component in glib.components.values():
            libdirs.extend(component.libdirs)
        old_path = os.environ.get("LD_LIBRARY_PATH", "")
        os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(
            list(dict.fromkeys(libdirs)) + ([old_path] if old_path else [])
        )
        try:
            self._ensure_model()
            cmake.build()
            # Run every test registered by the upstream CMake build, including
            # the punctuation test added by the parity patch.
            cmake.test()
        finally:
            if old_path:
                os.environ["LD_LIBRARY_PATH"] = old_path
            else:
                os.environ.pop("LD_LIBRARY_PATH", None)

    def package(self):
        CMake(self).install()
        build_data = os.path.join(self.build_folder, "data")
        package_data = os.path.join(self.package_folder, "share", "libpinyin", "data")
        os.makedirs(package_data, exist_ok=True)
        for name in sorted(os.listdir(build_data)):
            if name.endswith(".bin") or name == "table.conf":
                source = os.path.join(build_data, name)
                if os.path.isfile(source):
                    shutil.copy2(source, os.path.join(package_data, name))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "libpinyin")
        self.cpp_info.set_property("cmake_target_name", "libpinyin")
        includes = ["include"]
        root = os.path.join(self.package_folder, "include")
        if os.path.isdir(root):
            includes.extend(
                "include/" + name for name in sorted(os.listdir(root))
                if name.startswith("libpinyin")
            )
        glib = self.dependencies["glib"].cpp_info
        for component in [glib] + list(glib.components.values()):
            includes.extend(component.includedirs)
        self.cpp_info.includedirs = includes
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = ["pinyin"]
